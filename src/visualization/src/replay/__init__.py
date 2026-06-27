"""
Bar-by-bar replay mode.

    python app.py --replay --ticker AAPL --timeframe daily --ind-conf 0

Controls
--------
← / →        step backward / forward one bar
Shift+← / →  jump 20 bars at a time
Home / End    jump to bar 0 / last bar
Space         toggle play / pause
f             toggle auto-fit (default on; press to free-zoom, press again to snap back)
, / .         slower / faster (step interval ± 0.1 s)
Type a number + Enter   jump to that bar index (uses chart search box)
Ctrl+C        exit

Rendering
---------
Two approaches, chosen per indicator family:

Progressive reveal (no lookahead in the indicator itself):
    Slice prepared_df.iloc[:n+1] and call line.set(). The pre-computed CSV value
    at each bar is already historically accurate. SMA, Supertrend, peaks/valleys
    aVWAP, BoS/CHoCH aVWAP all work this way.

Historical recomputation (indicator has lookahead in the CSV):
    Ignore the pre-computed CSV column. Recompute what would have been visible at
    bar N using only data up to bar N.

    QQEMOD_aVWAP — uses an Anchor Event Log (src/visualization/src/replay/).
        Each anchor is committed when its zone closes (the opposite zone starts),
        because argmin/argmax within a zone can't be finalised until the zone ends.
        max_anchors trimming is applied rolling bar-by-bar, not on the full dataset.

    price_maxima_minima — greedy recomputation each step.
        Runs greedy_extrema(data[:n+1]) at every bar. O(N × max_anchors) per step,
        which is fast enough (~10k numpy ops). The set of selected anchors updates
        naturally as new price extremes are revealed.

Segment-based indicators (FVG, OB, BoS/CHoCH, Liquidity, divergences) are not
supported — they require two-point segments that change shape per step.
"""
import re
import sys
import time
import threading
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from lightweight_charts import Chart

from src.visualization.src.color_palette import get_color_palette
from src.visualization.src.charts import prepare_dataframe, configure_base_chart
from src.visualization.src.indicator_visualizations import (
    _cfg_idx, _ensure_time_col, _line_set_df,
)
from src.visualization.src.subcharts import _load_indicator_data
from src.visualization.src.replay.event_log import AnchorEvent, simulate_qqemod_avwap, active_at
from src.visualization.src.replay.vwap import build_cumulative_arrays, precompute_vwap_paths, get_vwap_df

_TIMEFRAME_MAP = {
    'd': 'daily', 'w': 'weekly',
    '4h': '4hour', 'h': '1hour', '5min': '5min',
}

_OHLCV_COLS = frozenset({'date', 'time', 'index', 'open', 'high', 'low', 'close', 'volume'})

# CSV column prefixes that are recomputed historically — skip in progressive reveal
_RECOMPUTED_PREFIXES = (
    'aVWAP_QQEMOD_bear_dot_',
    'aVWAP_QQEMOD_bull_dot_',
    'aVWAP_QQEMOD_bear_c',
    'aVWAP_QQEMOD_bull_c',
    'aVWAP_price_maxima_minima_valley_',
    'aVWAP_price_maxima_minima_peak_',
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def start_replay(ticker: str, timeframe: str, ind_conf: str):
    """Load indicator CSV and launch bar-by-bar replay."""
    timeframe = _TIMEFRAME_MAP.get(timeframe, timeframe)
    print(f"\nReplay: {ticker} / {timeframe} / ind_conf={ind_conf}")
    print("Controls: ← → step | Shift+←→ jump 20 | Home/End start/end | Space play/pause | , . speed\n")

    raw_df = _load_indicator_data(ticker, timeframe=timeframe, ind_conf=ind_conf)
    # No padding — the "current bar" is always the last bar in the slice.
    prepared_df, tf = prepare_dataframe(raw_df, show_volume=False, padding_ratio=0)

    n_total = len(prepared_df)
    if n_total == 0:
        print("No data to replay.")
        return

    colors = get_color_palette()

    # Build historical data for indicators that need recomputation.
    # Done before chart creation so slot line counts are known.
    qqemod_data = _build_qqemod_data(raw_df, ind_conf, timeframe, colors)
    pmm_data = _build_pmm_data(raw_df, ind_conf, timeframe, colors)

    chart = Chart(inner_width=1.0, inner_height=1.0, maximize=True)
    chart.name = '0'
    configure_base_chart(prepared_df, chart, show_volume=False)

    chart.topbar.textbox('ticker', ticker)
    chart.topbar.textbox('timeframe', str(tf))
    chart.topbar.textbox('ind_conf', str(ind_conf))
    chart.topbar.textbox('bar', f'0/{n_total - 1}')
    chart.topbar.button('auto_fit', 'FIT: ON', align='left', separator=True,
                        func=lambda: _toggle_auto_fit(chart, state))

    registry = _build_line_registry(chart, prepared_df, colors)

    if qqemod_data is not None:
        _create_qqemod_slot_lines(chart, qqemod_data, colors)
    if pmm_data is not None:
        _create_pmm_slot_lines(chart, pmm_data, colors)

    state = {
        'n': 0,
        'playing': False,
        'speed': 0.3,
        'auto_fit': True,
        'qqemod': qqemod_data,
        'pmm': pmm_data,
    }

    chart.hotkey('ctrl', 'c', lambda _=None: sys.exit(1))
    chart.hotkey(None, 'ArrowLeft',
                 lambda _=None: _step(chart, prepared_df, registry, state, -1, n_total))
    chart.hotkey(None, 'ArrowRight',
                 lambda _=None: _step(chart, prepared_df, registry, state, +1, n_total))
    chart.hotkey('shift', 'ArrowLeft',
                 lambda _=None: _step(chart, prepared_df, registry, state, -20, n_total))
    chart.hotkey('shift', 'ArrowRight',
                 lambda _=None: _step(chart, prepared_df, registry, state, +20, n_total))
    chart.hotkey(None, 'Home',
                 lambda _=None: _jump(chart, prepared_df, registry, state, 0))
    chart.hotkey(None, 'End',
                 lambda _=None: _jump(chart, prepared_df, registry, state, n_total - 1))
    chart.hotkey(None, ' ', lambda _=None: _toggle_play(state, n_total))
    chart.hotkey(None, 'f', lambda _=None: _toggle_auto_fit(chart, state))
    chart.hotkey(None, ',', lambda _=None: _adjust_speed(state, +0.1))
    chart.hotkey(None, '.', lambda _=None: _adjust_speed(state, -0.1))

    chart.events.search += lambda c, value: _on_bar_search(
        chart, prepared_df, registry, state, n_total, value
    )

    _render(chart, prepared_df, registry, state, state['n'])

    threading.Thread(
        target=_play_loop,
        args=(chart, prepared_df, registry, state, n_total),
        daemon=True,
    ).start()

    chart.show(block=True)


# ---------------------------------------------------------------------------
# QQEMOD historical data (Track 2)
# ---------------------------------------------------------------------------

def _build_qqemod_data(raw_df: pd.DataFrame, ind_conf: str, timeframe: str, colors: dict) -> Optional[dict]:
    """
    Build the QQEMOD historical anchor event log and VWAP paths.

    Reads QQEMOD_params from ind_conf to determine which anchor types to simulate —
    does NOT infer from pre-computed CSV columns. This means the replay reflects the
    current config even if the CSV was generated with an older config.

    Returns None if QQEMOD aVWAP is not enabled in the ind_conf.
    """
    # Load QQEMOD_params from ind_conf — this is the source of truth
    qqemod_params = _load_qqemod_params(ind_conf, timeframe)
    if qqemod_params is None:
        return None

    max_anchors = qqemod_params.get('max_anchors', qqemod_params.get('max_aVWAPs', 5))
    if max_anchors is not None:
        max_anchors = int(max_anchors)

    # Map QQEMOD_params flags → simulation direction keys
    enabled = {
        'bear_dot': bool(qqemod_params.get('peak_to_peak', False)),
        'bull_dot': bool(qqemod_params.get('valley_to_valley', False)),
        'bear':     bool(qqemod_params.get('peak_to_valley', False)),
        'bull':     bool(qqemod_params.get('valley_to_peak', False)),
    }

    if not any(enabled.values()):
        return None

    # Detect cfg_idx from CSV column names (usually 0); fall back to 0
    cfg_idx = 0
    for col in raw_df.columns:
        m = re.search(r'aVWAP_QQEMOD_\w+_c(\d+)_', col)
        if m:
            cfg_idx = int(m.group(1))
            break

    # Check that zone-label columns exist (needed for simulation)
    zone_col = f'QQE1_Above_Upper_c{cfg_idx}'
    if zone_col not in raw_df.columns:
        zone_col = 'QQE1_Above_Upper'
    if zone_col not in raw_df.columns:
        print("  QQEMOD historical mode: zone label columns not found in CSV — run --ind first")
        return None

    print(f"  QQEMOD historical mode: cfg_idx={cfg_idx}, max_anchors={max_anchors}, enabled={[k for k,v in enabled.items() if v]}")

    # Forward simulation — driven by ind_conf, not CSV column presence
    events = simulate_qqemod_avwap(raw_df, cfg_idx=cfg_idx, max_anchors=max_anchors, enabled=enabled)
    print(f"  Anchor events simulated: {len(events)}")

    # Precompute VWAP paths from raw price data for every anchor bar in events
    cum_tpv, cum_vol = build_cumulative_arrays(raw_df)
    anchor_bars = list({e.anchor_bar for e in events})
    paths = precompute_vwap_paths(anchor_bars, cum_tpv, cum_vol)

    # Date array aligned to raw_df rows (for VWAP series time column)
    dates = raw_df['date'].values if 'date' in raw_df.columns else np.arange(len(raw_df)).astype(str)

    directions_present = [d for d, v in enabled.items() if v]

    return {
        'events': events,
        'paths': paths,
        'dates': dates,
        'max_anchors': max_anchors,
        'cfg_idx': cfg_idx,
        'directions': directions_present,
        'slots': {},
        'colors': colors,
    }


def _create_qqemod_slot_lines(chart: Chart, qqemod_data: dict, colors: dict) -> None:
    """Pre-allocate one Line per (direction, slot_idx) pair in the chart."""
    max_anchors = qqemod_data['max_anchors'] or 10
    style_map = {
        'bear_dot': (colors['teal'], 1, 'dotted'),
        'bull_dot': (colors['red'], 1, 'dotted'),
        'bear':     (colors['teal'], 2, 'solid'),
        'bull':     (colors['red'], 2, 'solid'),
    }
    slots: Dict[str, list] = {}
    for direction in qqemod_data['directions']:
        color, width, style = style_map.get(direction, (colors['gray_trans'], 1, 'solid'))
        slots[direction] = [
            chart.create_line(price_line=False, price_label=False,
                              color=color, width=width, style=style)
            for _ in range(max_anchors)
        ]
    qqemod_data['slots'] = slots


# ---------------------------------------------------------------------------
# price_maxima_minima historical recomputation
# ---------------------------------------------------------------------------

def _greedy_extrema(values: np.ndarray, mode: str, n_anchors: int, spacing: int) -> list:
    """
    Greedy price extrema selection with minimum spacing between anchors.
    Mirrors aVWAP.py's greedy_extrema exactly so replay matches indicator output.
    """
    mask = np.ones(len(values), dtype=bool)
    selected = []
    for _ in range(n_anchors):
        available = np.where(mask)[0]
        if not len(available):
            break
        rel = int(np.argmin(values[available])) if mode == 'valley' else int(np.argmax(values[available]))
        idx = int(available[rel])
        selected.append(idx)
        mask[max(0, idx - spacing): min(len(values), idx + spacing + 1)] = False
    return selected


def _inline_vwap_df(anchor: int, replay_bar: int,
                    cum_tpv: np.ndarray, cum_vol: np.ndarray,
                    dates: np.ndarray) -> pd.DataFrame:
    """VWAP series from anchor to replay_bar using precomputed cumulative arrays."""
    if anchor > replay_bar:
        return pd.DataFrame(columns=['time', 'value'])
    base_tpv = cum_tpv[anchor - 1] if anchor > 0 else 0.0
    base_vol = cum_vol[anchor - 1] if anchor > 0 else 0.0
    seg_tpv = cum_tpv[anchor: replay_bar + 1] - base_tpv
    seg_vol = cum_vol[anchor: replay_bar + 1] - base_vol
    with np.errstate(divide='ignore', invalid='ignore'):
        values = np.where(seg_vol > 0, seg_tpv / seg_vol, np.nan)
    return pd.DataFrame({'time': dates[anchor: replay_bar + 1], 'value': values})


def _load_pmm_params(ind_conf: str, timeframe: str) -> Optional[dict]:
    """Load price_maxima_minima params from ind_conf if enabled."""
    try:
        from src.indicators.indicators import load_indicator_config
        result = load_indicator_config(ind_conf, timeframe)
        if not result:
            return None
        _, params = result
        avwap_p = params.get('aVWAP', {})
        if not avwap_p.get('price_maxima_minima', False):
            return None
        raw = avwap_p.get('price_maxima_minima_params', {})
        # params may be a list of configs; use first one
        return (raw[0] if isinstance(raw, list) else raw) or {}
    except Exception as e:
        print(f"  Warning: could not load pmm params: {e}")
        return None


def _build_pmm_data(raw_df: pd.DataFrame, ind_conf: str, timeframe: str, colors: dict) -> Optional[dict]:
    """
    Build price_maxima_minima historical recomputation data.

    At each replay step, greedy_extrema(data[:n+1]) is called to find the current
    top-N price extremes. No precomputed anchor set — the selection updates naturally
    as new bars reveal new extremes.
    """
    pmm_params = _load_pmm_params(ind_conf, timeframe)
    if pmm_params is None:
        return None

    max_anchors = int(pmm_params.get('max_anchors') or 5)
    spacing = int(pmm_params.get('min_swing_spacing', 30))
    include_valleys = bool(pmm_params.get('valleys', True))
    include_peaks = bool(pmm_params.get('peaks', False))

    if not include_valleys and not include_peaks:
        return None

    cum_tpv, cum_vol = build_cumulative_arrays(raw_df)
    low_vals = raw_df['low'].values if 'low' in raw_df.columns else raw_df['Low'].values
    high_vals = raw_df['high'].values if 'high' in raw_df.columns else raw_df['High'].values
    dates = raw_df['date'].values if 'date' in raw_df.columns else np.arange(len(raw_df)).astype(str)

    directions = (['valley'] if include_valleys else []) + (['peak'] if include_peaks else [])
    print(f"  price_maxima_minima historical mode: max_anchors={max_anchors}, spacing={spacing}, types={directions}")

    return {
        'low_vals': low_vals,
        'high_vals': high_vals,
        'cum_tpv': cum_tpv,
        'cum_vol': cum_vol,
        'dates': dates,
        'max_anchors': max_anchors,
        'spacing': spacing,
        'include_valleys': include_valleys,
        'include_peaks': include_peaks,
        'slots': {},
    }


def _create_pmm_slot_lines(chart: Chart, pmm_data: dict, colors: dict) -> None:
    """Pre-allocate one Line per (direction, slot_idx) for price_maxima_minima."""
    max_anchors = pmm_data['max_anchors']
    slots = {}
    if pmm_data['include_valleys']:
        slots['valley'] = [
            chart.create_line(price_line=False, price_label=False,
                              color=colors['teal'], width=2, style='solid')
            for _ in range(max_anchors)
        ]
    if pmm_data['include_peaks']:
        slots['peak'] = [
            chart.create_line(price_line=False, price_label=False,
                              color=colors['red'], width=2, style='solid')
            for _ in range(max_anchors)
        ]
    pmm_data['slots'] = slots


def _render_pmm_slots(pmm: dict, n: int) -> None:
    """Recompute greedy extrema on data[:n+1] and update slot lines."""
    cum_tpv = pmm['cum_tpv']
    cum_vol = pmm['cum_vol']
    dates = pmm['dates']
    spacing = pmm['spacing']
    max_anchors = pmm['max_anchors']
    _empty = pd.DataFrame(columns=['time', 'value'])

    if pmm['include_valleys'] and 'valley' in pmm['slots']:
        anchors = _greedy_extrema(pmm['low_vals'][:n + 1], 'valley', max_anchors, spacing)
        for i, line in enumerate(pmm['slots']['valley']):
            line.set(_inline_vwap_df(anchors[i], n, cum_tpv, cum_vol, dates) if i < len(anchors) else _empty)

    if pmm['include_peaks'] and 'peak' in pmm['slots']:
        anchors = _greedy_extrema(pmm['high_vals'][:n + 1], 'peak', max_anchors, spacing)
        for i, line in enumerate(pmm['slots']['peak']):
            line.set(_inline_vwap_df(anchors[i], n, cum_tpv, cum_vol, dates) if i < len(anchors) else _empty)


def _load_qqemod_params(ind_conf: str, timeframe: str) -> Optional[dict]:
    """
    Load QQEMOD_params from the indicator config for the given timeframe.
    Returns None if aVWAP is not configured or QQEMOD is not enabled within it.
    """
    try:
        from src.indicators.indicators import load_indicator_config
        result = load_indicator_config(ind_conf, timeframe)
        if not result:
            return None
        _, params = result
        avwap_p = params.get('aVWAP', {})
        if not avwap_p.get('QQEMOD', False):
            return None
        qqp = avwap_p.get('QQEMOD_params', {})
        return qqp if qqp else None
    except Exception as e:
        print(f"  Warning: could not load ind_conf {ind_conf} / {timeframe}: {e}")
        return None


def _render_qqemod_slots(qqemod: dict, n: int) -> None:
    """Update Track 2 slot Lines at replay bar n."""
    events: List[AnchorEvent] = qqemod['events']
    paths = qqemod['paths']
    dates = qqemod['dates']
    slots = qqemod['slots']

    _empty = pd.DataFrame(columns=['time', 'value'])

    for direction, slot_lines in slots.items():
        active = active_at(events, n, direction)
        for idx, line in enumerate(slot_lines):
            if idx < len(active):
                ev = active[idx]
                df_v = get_vwap_df(ev.anchor_bar, n, paths, dates)
                line.set(df_v)
            else:
                line.set(_empty)


# ---------------------------------------------------------------------------
# Track 1 line registry
# ---------------------------------------------------------------------------

def _build_line_registry(chart: Chart, df: pd.DataFrame, colors: dict) -> dict:
    """
    Pre-create one lightweight-charts Line per standard indicator column.
    Returns {col_name: Line}.

    QQEMOD_aVWAP columns are deliberately excluded — they are handled by Track 2
    (_render_qqemod_slots) using historically accurate anchor events instead of the
    full-dataset progressive-reveal approach.
    """
    registry = {}

    def _make(col, color, width, style='solid'):
        line = chart.create_line(
            price_line=False, price_label=False,
            color=color, width=width, style=style,
        )
        registry[col] = line

    def _w(cfg):
        return 2 if cfg == 0 else 1

    def _s(cfg):
        return 'solid' if cfg == 0 else 'dotted'

    for col in df.columns:
        if col in _OHLCV_COLS:
            continue

        # Skip columns recomputed historically — handled separately
        if any(col.startswith(p) for p in _RECOMPUTED_PREFIXES):
            continue

        cfg = _cfg_idx(col)

        # Pinch
        if col.startswith('aVWAP_pinch_peak_'):
            _make(col, colors['red_trans_3'], 1, 'solid')
        elif col.startswith('aVWAP_pinch_valley_'):
            _make(col, colors['teal_trans_3'], 1, 'solid')
        elif col.startswith('aVWAP_pinch_above_'):
            _make(col, colors['teal_trans_2'], 1, 'dotted')
        elif col.startswith('aVWAP_pinch_below_'):
            _make(col, colors['red_trans_2'], 1, 'dotted')

        # Peaks / valleys
        elif col.startswith('aVWAP_peak_'):
            _make(col, colors['red_trans_3'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_valley_'):
            _make(col, colors['teal_trans_3'], _w(cfg), _s(cfg))

        # Anchor score
        elif col.startswith('aVWAP_valley_q') or col.startswith('aVWAP_peak_q'):
            _make(col, colors['teal_trans_3'] if 'valley' in col else colors['red_trans_3'],
                  _w(cfg), _s(cfg))

        # BoS / CHoCH aVWAPs
        elif col.startswith('aVWAP_BoS_CHoCH_bear_'):
            _make(col, colors['red'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_BoS_CHoCH_bull_'):
            _make(col, colors['teal'], _w(cfg), _s(cfg))

        # OB aVWAPs
        elif col.startswith('aVWAP_OB_bull_'):
            _make(col, colors['aqua'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_OB_bear_'):
            _make(col, colors['red_dark'], _w(cfg), _s(cfg))

        # Gaps
        elif col.startswith('Gap_Up_aVWAP_'):
            _make(col, colors['teal_trans_2'], _w(cfg), _s(cfg))
        elif col.startswith('Gap_Down_aVWAP_'):
            _make(col, colors['red_trans_2'], _w(cfg), _s(cfg))

        # Average aVWAPs
        elif col.startswith('Peaks_Valleys_avg'):
            mc = [c for c in df.columns if c.startswith('Peaks_Valleys_avg')]
            _make(col, colors['orange_aVWAP'], 4 if (col == 'Peaks_Valleys_avg' and len(mc) > 1) else 2, 'solid')
        elif col.startswith('Peaks_avg'):
            mc = [c for c in df.columns if c.startswith('Peaks_avg')]
            _make(col, colors['red'], 4 if (col == 'Peaks_avg' and len(mc) > 1) else 2, 'solid')
        elif col.startswith('Valleys_avg'):
            mc = [c for c in df.columns if c.startswith('Valleys_avg')]
            _make(col, colors['teal'], 4 if (col == 'Valleys_avg' and len(mc) > 1) else 2, 'solid')
        elif col.startswith('OB_avg'):
            mc = [c for c in df.columns if c.startswith('OB_avg')]
            _make(col, colors['orange_aVWAP'], 3 if (col == 'OB_avg' and len(mc) > 1) else 1.5, 'dashed')
        elif col.startswith('Gaps_avg'):
            mc = [c for c in df.columns if c.startswith('Gaps_avg')]
            _make(col, colors['orange_aVWAP'], 4 if (col == 'Gaps_avg' and len(mc) > 1) else 2, 'dotted')
        elif col.startswith('BoS_CHoCH_avg'):
            mc = [c for c in df.columns if c.startswith('BoS_CHoCH_avg')]
            _make(col, colors['orange_aVWAP'], 3 if (col == 'BoS_CHoCH_avg' and len(mc) > 1) else 1.5, 'large_dashed')
        elif col.startswith('QQEMOD_avg'):
            mc = [c for c in df.columns if c.startswith('QQEMOD_avg')]
            _make(col, colors['orange_aVWAP'], 3 if (col == 'QQEMOD_avg' and len(mc) > 1) else 1.5, 'solid')
        elif col.startswith('All_avg'):
            mc = [c for c in df.columns if c.startswith('All_avg')]
            _make(col, colors['gray_trans'], 5 if (col == 'All_avg' and len(mc) > 1) else 3, 'solid')

        # SMA
        elif col.startswith('SMA_'):
            try:
                period = int(col.split('_')[1])
            except Exception:
                period = 0
            w = (1 if period <= 10 else
                 2 if period <= 50 else
                 3 if period <= 100 else
                 4 if period <= 200 else 5)
            _make(col, colors['blue_SMA'], w)

        # Supertrend (upper/lower drawn individually; active line is synthetic)
        elif col == 'Supertrend_Upper':
            _make(col, colors['orange'], 1)
        elif col == 'Supertrend_Lower':
            _make(col, colors['orange'], 1)

    # Synthetic Supertrend active line
    if all(c in df.columns for c in ('Supertrend_Upper', 'Supertrend_Lower', 'Supertrend_Direction')):
        registry['_Supertrend_Active'] = chart.create_line(
            price_line=False, price_label=False,
            color=colors['black'], width=2,
        )

    n_indicator_cols = sum(1 for c in df.columns if c not in _OHLCV_COLS
                           and not any(c.startswith(p) for p in _RECOMPUTED_PREFIXES))
    print(f"  Track 1 registry: {len(registry)} lines for {n_indicator_cols} indicator columns")
    return registry


# ---------------------------------------------------------------------------
# Render / step / play
# ---------------------------------------------------------------------------

def _render(chart: Chart, df: pd.DataFrame, registry: dict, state: dict, n: int) -> None:
    """Slice df to bar n and update chart + all registered lines."""
    s = df.iloc[: n + 1]
    chart.set(s)
    s_t = _ensure_time_col(s)

    for col, line in registry.items():
        if col == '_Supertrend_Active':
            if all(c in s_t.columns for c in ('Supertrend_Upper', 'Supertrend_Lower', 'Supertrend_Direction')):
                active = np.where(
                    s_t['Supertrend_Direction'] == -1,
                    s_t['Supertrend_Lower'],
                    s_t['Supertrend_Upper'],
                )
                line.set(pd.DataFrame({'time': s_t['time'], 'value': active}))
        elif col in s.columns:
            line.set(_line_set_df(s, col))

    # Historically recomputed indicators
    if state.get('qqemod'):
        _render_qqemod_slots(state['qqemod'], n)
    if state.get('pmm'):
        _render_pmm_slots(state['pmm'], n)

    if state.get('auto_fit', True):
        chart.fit()

    try:
        chart.topbar['bar'].set(f'{n}/{len(df) - 1}')
    except Exception:
        pass


def _step(chart, df, registry, state, delta, n_total):
    """Step backward (delta < 0) or forward (delta > 0) by |delta| bars."""
    target = max(0, min(state['n'] + delta, n_total - 1))
    if target != state['n']:
        state['n'] = target
        _render(chart, df, registry, state, target)


def _jump(chart, df, registry, state, target):
    """Jump directly to a specific bar index."""
    target = max(0, min(target, len(df) - 1))
    state['n'] = target
    _render(chart, df, registry, state, target)


def _on_bar_search(chart, df, registry, state, n_total, value):
    """Called when the user types in the chart search box. Jumps to a bar number."""
    value = value.strip()
    try:
        target = int(value)
    except ValueError:
        print(f"[Replay] Type a bar number (0–{n_total - 1}) to jump — got '{value}'")
        return
    _jump(chart, df, registry, state, target)
    print(f"[Replay] Jumped to bar {state['n']}/{n_total - 1}")


def _toggle_auto_fit(chart, state):
    """Toggle auto-fit mode."""
    state['auto_fit'] = not state['auto_fit']
    try:
        chart.topbar['auto_fit'].set('FIT: ON' if state['auto_fit'] else 'FIT: OFF')
    except Exception:
        pass
    if state['auto_fit']:
        chart.fit()


def _toggle_play(state, n_total):
    """Toggle play / pause."""
    state['playing'] = not state['playing']
    label = 'Playing' if state['playing'] else 'Paused'
    print(f"[Replay] {label}  bar {state['n']}/{n_total - 1}  {state['speed']:.2f}s/bar")


def _adjust_speed(state, delta):
    """Change step interval, clamped to [0.05, 2.0] seconds."""
    state['speed'] = max(0.05, min(state['speed'] + delta, 2.0))
    print(f"[Replay] Speed: {state['speed']:.2f} s/bar  ({1 / state['speed']:.1f} bars/sec)")


def _play_loop(chart, df, registry, state, n_total):
    """Background thread: advance one bar per interval while playing."""
    while True:
        if state['playing']:
            n = state['n']
            if n >= n_total - 1:
                state['playing'] = False
                print("[Replay] Reached end of data — paused")
            else:
                state['n'] = n + 1
                _render(chart, df, registry, state, n + 1)
                time.sleep(state['speed'])
        else:
            time.sleep(0.05)
