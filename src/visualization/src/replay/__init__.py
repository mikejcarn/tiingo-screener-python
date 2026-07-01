"""
Bar-by-bar replay mode.

    python app.py --replay --ticker AAPL --timeframe daily --ind-conf 0

Controls
--------
← / →            step backward / forward one bar
Shift+← / →      jump 20 bars at a time
Home / End        jump to bar 0 / last bar
Space             toggle play / pause
f / Backspace     toggle auto-fit (default on; press to free-zoom, press again to snap back)
↑ / ↓  or  , / . faster / slower (step interval ± 0.1 s; topbar shows multiplier)
/                reset to normal speed (1.0x)
Type a number + Enter   jump to that bar index (uses chart search box)
Ctrl+C            exit

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
from src.visualization.src.replay.event_log import AnchorEvent, simulate_qqemod_avwap, active_at, precompute_live_anchors
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
    'aVWAP_valley_q',
    'aVWAP_peak_q',
)

# Segment-based indicator columns — handled by Track 4; excluded from progressive reveal
_SEGMENT_COLS = frozenset({
    'Liquidity', 'Liquidity_Level',
    'FVG', 'FVG_High', 'FVG_Low', 'FVG_Mitigated_Index',
    'OB', 'OB_High', 'OB_Low', 'OB_Mitigated_Index',
})
# BoS/CHoCH columns use numeric suffixes (e.g. BoS_25, CHoCH_25) — matched by regex
_BOS_CHOCH_COL_RE = re.compile(
    r'^(BoS|CHoCH|BoS_CHoCH_Price|BoS_CHoCH_Break_Index)_(\d+)$'
)

_BASE_SPEED = 0.3  # seconds/bar at 1x — matches default state['speed']
_EMPTY_SEG = pd.DataFrame(columns=['time', 'value'])


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_for_replay(ticker: str, timeframe: str, ind_conf: str) -> Optional[pd.DataFrame]:
    """
    Load OHLCV data for replay, then compute indicators in memory.

    Lookup order:
      1. data/tickers/ buffer — most recent CSV for this ticker+timeframe
      2. Tiingo API           — live fetch if no buffer CSV found

    The indicator buffer is never used: indicators are always computed fresh
    from raw OHLCV so replay works for any ticker without running --ind first.
    """
    from src.core.globals import TICKERS_DIR, API_KEY
    from src.tickers.tickers import fetch_ticker
    from src.indicators.indicators import get_indicators, load_indicator_config
    from pathlib import Path

    timeframe_dir = Path(TICKERS_DIR)
    pattern = f"{ticker}_{timeframe}_*.csv"
    candidates = sorted(timeframe_dir.glob(pattern))

    if candidates:
        latest = candidates[-1]
        print(f"  Loading from tickers buffer: {latest.name}")
        raw_df = pd.read_csv(latest)
    else:
        print(f"  No tickers buffer found for {ticker}/{timeframe} — fetching from API...")
        raw_df = fetch_ticker(timeframe=timeframe, ticker=ticker, api_key=API_KEY)
        if raw_df is None or raw_df.empty:
            print(f"  Error: could not fetch {ticker}/{timeframe}")
            return None

    config_result = load_indicator_config(ind_conf, timeframe)
    if config_result is None:
        print(f"  Warning: no indicator config for ind_conf={ind_conf}/{timeframe} — replaying raw OHLCV only")
    else:
        ind_config, ind_params = config_result
        if ind_config and ind_params:
            print(f"  Computing indicators (ind_conf={ind_conf})...")
            raw_df = get_indicators(raw_df, ind_config, ind_params)

    # Stamp attrs so prepare_dataframe can read the timeframe.
    # fetch_ticker sets this automatically; the tickers buffer CSV path does not.
    raw_df.attrs['timeframe'] = timeframe
    raw_df.attrs['ticker'] = ticker

    return raw_df


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def start_replay(ticker: str, timeframe: str, ind_conf: str):
    """Fetch/load OHLCV, compute indicators in memory, and launch bar-by-bar replay."""
    timeframe = _TIMEFRAME_MAP.get(timeframe, timeframe)

    print(f"\nReplay: {ticker} / {timeframe} / ind_conf={ind_conf}")
    print("Controls: ← → step | Shift+←→ jump 20 | Home/End start/end | Space play/pause | , . speed\n")

    raw_df = _load_for_replay(ticker, timeframe, ind_conf)
    if raw_df is None or raw_df.empty:
        return
    # No padding — the "current bar" is always the last bar in the slice.
    prepared_df, tf = prepare_dataframe(raw_df, show_volume=False, padding_ratio=0)

    n_total = len(prepared_df)
    if n_total == 0:
        print("No data to replay.")
        return

    colors = get_color_palette()

    # Build historical data for indicators that need recomputation.
    # Done before chart creation so slot line counts are known.
    qqemod_data       = _build_qqemod_data(raw_df, ind_conf, timeframe, colors)
    pmm_data          = _build_pmm_data(raw_df, ind_conf, timeframe, colors)
    anchor_score_data = _build_anchor_score_data(raw_df, ind_conf, timeframe, colors)

    chart = Chart(inner_width=1.0, inner_height=1.0, maximize=True)
    chart.name = '0'
    configure_base_chart(prepared_df, chart, show_volume=False)

    chart.topbar.textbox('ticker', ticker)
    chart.topbar.textbox('timeframe', str(tf))
    chart.topbar.textbox('ind_conf', str(ind_conf))
    chart.topbar.textbox('bar', f'0/{n_total - 1}')
    chart.topbar.textbox('speed', '1.0x')
    chart.topbar.button('auto_fit', 'FIT: ON', align='left', separator=True,
                        func=lambda: _toggle_auto_fit(chart, state))

    registry = _build_line_registry(chart, prepared_df, colors)

    if qqemod_data is not None:
        _create_qqemod_slot_lines(chart, qqemod_data, colors)
    if pmm_data is not None:
        _create_pmm_slot_lines(chart, pmm_data, colors)
    if anchor_score_data is not None:
        _create_anchor_score_slot_lines(chart, anchor_score_data, colors)

    # Track 4: segment indicators
    bos_choch_data = _build_bos_choch_data(chart, raw_df, colors)
    fvg_data       = _build_fvg_data(chart, raw_df, colors)
    ob_data        = _build_ob_data(chart, raw_df, colors)
    liquidity_data = _build_liquidity_data(chart, raw_df, colors)

    # All mutable replay state lives here so ticker switching can update it in-place.
    state = {
        'n': 0,
        'playing': False,
        'speed': 0.3,
        'auto_fit': True,
        'prepared_df': prepared_df,
        'n_total': n_total,
        'registry': registry,
        'qqemod': qqemod_data,
        'pmm': pmm_data,
        'anchor_score': anchor_score_data,
        'bos_choch': bos_choch_data,
        'fvg':       fvg_data,
        'ob':        ob_data,
        'liquidity': liquidity_data,
        # session config — needed by _on_bar_search for arbitrary ticker loading
        'ind_conf': ind_conf,
        'timeframe': timeframe,
        'colors': colors,
    }

    chart.hotkey('ctrl', 'c', lambda _=None: sys.exit(1))
    chart.hotkey(None, 'ArrowLeft',   lambda _=None: _step(chart, state, -1))
    chart.hotkey(None, 'ArrowRight',  lambda _=None: _step(chart, state, +1))
    chart.hotkey('shift', 'ArrowLeft',  lambda _=None: _step(chart, state, -20))
    chart.hotkey('shift', 'ArrowRight', lambda _=None: _step(chart, state, +20))
    chart.hotkey(None, 'Home', lambda _=None: _jump(chart, state, 0))
    chart.hotkey(None, 'End',  lambda _=None: _jump(chart, state, state['n_total'] - 1))
    chart.hotkey(None, ' ',          lambda _=None: _toggle_play(state))
    chart.hotkey(None, 'Backspace',  lambda _=None: _toggle_auto_fit(chart, state))
    chart.hotkey(None, ',',          lambda _=None: _adjust_speed(state, chart, +0.1))
    chart.hotkey(None, '.',          lambda _=None: _adjust_speed(state, chart, -0.1))
    chart.hotkey(None, 'ArrowUp',    lambda _=None: _adjust_speed(state, chart, -0.1))
    chart.hotkey(None, 'ArrowDown',  lambda _=None: _adjust_speed(state, chart, +0.1))
    chart.hotkey(None, '/',          lambda _=None: _reset_speed(state, chart))

    chart.events.search += lambda c, value: _on_bar_search(chart, state, value)

    _render(chart, prepared_df, registry, state, state['n'])

    threading.Thread(target=_play_loop, args=(chart, state), daemon=True).start()

    chart.show(block=True)


# ---------------------------------------------------------------------------
# QQEMOD historical data (Track 2)
# ---------------------------------------------------------------------------

def _ensure_qqemod_zone_cols(raw_df: pd.DataFrame, ind_conf: str, timeframe: str) -> pd.DataFrame:
    """
    Compute QQEMOD zone label columns in memory if they are not already in raw_df.

    Uses the standalone QQEMOD params from ind_conf when available (so zone boundaries
    match any configured indicator), otherwise falls back to calculate_qqemod defaults.
    The resulting columns (QQE1_Above_Upper, QQE1_Below_Lower, etc.) are added directly
    to a copy of raw_df and returned.
    """
    from src.indicators.indicators_list.QQEMOD import calculate_qqemod

    qqemod_params = {}
    try:
        from src.indicators.indicators import load_indicator_config
        result = load_indicator_config(ind_conf, timeframe)
        if result:
            _, params = result
            qqemod_params = params.get('QQEMOD', {}) or {}
    except Exception:
        pass

    print(f"  QQEMOD zone labels not in data — computing on the fly (params: {qqemod_params or 'defaults'})")

    # calculate_qqemod expects a 'Close' column (title case)
    work = raw_df.copy()
    if 'Close' not in work.columns and 'close' in work.columns:
        work = work.rename(columns={'close': 'Close'})

    try:
        zone_dict = calculate_qqemod(work, **qqemod_params)
    except Exception as e:
        print(f"  Warning: QQEMOD computation failed: {e}")
        return raw_df

    result = raw_df.copy()
    for col in ('QQE1_Above_Upper', 'QQE1_Below_Lower',
                'QQE2_Above_Threshold', 'QQE2_Below_Threshold', 'QQE2_Above_TL'):
        if col in zone_dict:
            result[col] = zone_dict[col].values if hasattr(zone_dict[col], 'values') else zone_dict[col]
    return result


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

    # Ensure zone-label columns exist — compute QQEMOD on the fly if missing.
    # This removes the requirement to have QQEMOD enabled as a standalone indicator.
    zone_col = f'QQE1_Above_Upper_c{cfg_idx}'
    if zone_col not in raw_df.columns:
        zone_col = 'QQE1_Above_Upper'
    if zone_col not in raw_df.columns:
        raw_df = _ensure_qqemod_zone_cols(raw_df, ind_conf, timeframe)
        zone_col = 'QQE1_Above_Upper'
        if zone_col not in raw_df.columns:
            print("  QQEMOD historical mode: could not compute zone labels")
            return None
        cfg_idx = 0  # freshly computed columns have no suffix

    print(f"  QQEMOD historical mode: cfg_idx={cfg_idx}, max_anchors={max_anchors}, enabled={[k for k,v in enabled.items() if v]}")

    # Forward simulation — driven by ind_conf, not CSV column presence
    events = simulate_qqemod_avwap(raw_df, cfg_idx=cfg_idx, max_anchors=max_anchors, enabled=enabled)
    print(f"  Anchor events simulated: {len(events)}")

    # Precompute VWAP paths from raw price data for every anchor bar in events
    cum_tpv, cum_vol = build_cumulative_arrays(raw_df)
    anchor_bars = list({e.anchor_bar for e in events})
    paths = precompute_vwap_paths(anchor_bars, cum_tpv, cum_vol)

    # Date array aligned to raw_df rows (for VWAP series time column)
    if 'date' in raw_df.columns:
        dates = raw_df['date'].values
    elif raw_df.index.name == 'date':
        dates = raw_df.index.astype(str).values
    else:
        dates = np.arange(len(raw_df)).astype(str)

    # Precompute live (floating) anchor arrays — one per bar, for active zones
    live_bear, live_bull = precompute_live_anchors(raw_df, cfg_idx=cfg_idx)

    # Add VWAP paths for any live anchor bars not already in paths
    live_anchor_bars = set()
    if enabled.get('bear_dot') or enabled.get('bear'):
        live_anchor_bars.update(int(b) for b in live_bear if b >= 0)
    if enabled.get('bull_dot') or enabled.get('bull'):
        live_anchor_bars.update(int(b) for b in live_bull if b >= 0)
    new_bars = list(live_anchor_bars - set(paths.keys()))
    if new_bars:
        paths.update(precompute_vwap_paths(new_bars, cum_tpv, cum_vol))

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
        'live_bear': live_bear,
        'live_bull': live_bull,
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

    # Live floating anchor — only shown when the matching solid line type is enabled.
    # bear_dot/bull_dot (dotted handoffs) don't get a live anchor so they can't be
    # mistaken for committed solid lines from other indicators.
    directions = qqemod_data['directions']
    if 'bear' in directions:
        slots['_live_bear'] = chart.create_line(
            price_line=False, price_label=False,
            color=colors['teal'], width=2, style='solid')
    if 'bull' in directions:
        slots['_live_bull'] = chart.create_line(
            price_line=False, price_label=False,
            color=colors['red'], width=2, style='solid')

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
        ind_list, params = result
        if 'aVWAP' not in ind_list:
            return None
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
    if 'date' in raw_df.columns:
        dates = raw_df['date'].values
    elif raw_df.index.name == 'date':
        dates = raw_df.index.astype(str).values
    else:
        dates = np.arange(len(raw_df)).astype(str)

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


# ---------------------------------------------------------------------------
# aVWAP anchor score historical recomputation
# ---------------------------------------------------------------------------

def _load_anchor_score_params(ind_conf: str, timeframe: str) -> Optional[dict]:
    try:
        from src.indicators.indicators import load_indicator_config
        result = load_indicator_config(ind_conf, timeframe)
        if not result:
            return None
        ind_list, params = result
        if 'aVWAP_anchor_score' not in ind_list:
            return None
        p = params.get('aVWAP_anchor_score')
        return p if p else None
    except Exception as e:
        print(f"  Warning: could not load anchor score params: {e}")
        return None


def _build_anchor_score_data(raw_df: pd.DataFrame, ind_conf: str, timeframe: str, colors: dict) -> Optional[dict]:
    params = _load_anchor_score_params(ind_conf, timeframe)
    if params is None:
        return None

    include_valleys = bool(params.get('valleys', True))
    include_peaks   = bool(params.get('peaks', False))
    if not include_valleys and not include_peaks:
        return None

    max_anchors = params.get('max_anchors') or 10

    high  = raw_df['high'].values  if 'high'  in raw_df.columns else raw_df['High'].values
    low   = raw_df['low'].values   if 'low'   in raw_df.columns else raw_df['Low'].values
    close = raw_df['close'].values if 'close' in raw_df.columns else raw_df['Close'].values

    # ATR is backward-looking — safe to precompute on full array
    atr_period = int(params.get('atr_period', 14))
    prev_close = pd.Series(close).shift(1).values
    tr  = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    atr = pd.Series(tr).rolling(atr_period).mean().values

    cum_tpv, cum_vol = build_cumulative_arrays(raw_df)

    if 'date' in raw_df.columns:
        dates = raw_df['date'].values
    elif raw_df.index.name == 'date':
        dates = raw_df.index.astype(str).values
    else:
        dates = np.arange(len(raw_df)).astype(str)

    directions = (['valley'] if include_valleys else []) + (['peak'] if include_peaks else [])
    print(f"  aVWAP_anchor_score historical mode: max_anchors={max_anchors}, types={directions}")

    return {
        'low_vals':  low,
        'high_vals': high,
        'close_vals': close,
        'atr':       atr,
        'cum_tpv':   cum_tpv,
        'cum_vol':   cum_vol,
        'dates':     dates,
        'max_anchors': int(max_anchors),
        'params':    params,
        'include_valleys': include_valleys,
        'include_peaks':   include_peaks,
        'slots': {},
    }


def _create_anchor_score_slot_lines(chart: Chart, data: dict, colors: dict) -> None:
    max_anchors = data['max_anchors']
    slots = {}
    if data['include_valleys']:
        slots['valley'] = [
            chart.create_line(price_line=False, price_label=False,
                              color=colors['teal_trans_3'], width=2, style='solid')
            for _ in range(max_anchors)
        ]
    if data['include_peaks']:
        slots['peak'] = [
            chart.create_line(price_line=False, price_label=False,
                              color=colors['red_trans_3'], width=2, style='solid')
            for _ in range(max_anchors)
        ]
    data['slots'] = slots


def _render_anchor_score_slots(data: dict, n: int) -> None:
    from scipy.signal import find_peaks
    from src.indicators.indicators_list.aVWAP_anchor_score import (
        _isolation_window, _reversal_sharpness, _percentile_rank,
    )

    params      = data['params']
    low_vals    = data['low_vals']
    high_vals   = data['high_vals']
    close_vals  = data['close_vals']
    atr         = data['atr']
    cum_tpv     = data['cum_tpv']
    cum_vol     = data['cum_vol']
    dates       = data['dates']
    max_anchors = data['max_anchors']
    slots       = data['slots']

    min_spacing  = int(params.get('min_swing_spacing', 5))
    iso_max      = int(params.get('isolation_max_bars', 200))
    sharp_before = int(params.get('sharpness_bars_before', 10))
    sharp_after  = int(params.get('sharpness_bars_after', 10))
    w_prom       = float(params.get('w_prominence', 1.0))
    w_iso        = float(params.get('w_isolation', 1.0))
    w_sharp      = float(params.get('w_sharpness', 1.0))
    min_score_pct  = params.get('min_score_pct')
    max_atr_dist   = params.get('max_atr_distance')
    max_possible   = w_prom + w_iso + w_sharp

    current_close = close_vals[n]
    current_atr   = atr[n] if not np.isnan(atr[n]) else 0.0
    proximity_active = (max_atr_dist is not None and current_atr > 0
                        and not np.isnan(current_close))

    _empty = pd.DataFrame(columns=['time', 'value'])

    def score_candidates(values, mode):
        if n < min_spacing:
            return []
        search = -values[:n + 1] if mode == 'valley' else values[:n + 1]
        cand_idx, props = find_peaks(search, distance=min_spacing, prominence=(None, None))
        if len(cand_idx) == 0:
            return []

        sign = 1 if mode == 'valley' else -1
        rows = []
        for idx, prom in zip(cand_idx, props['prominences']):
            atr_val = atr[idx]
            if np.isnan(atr_val) or atr_val == 0:
                continue
            iso   = _isolation_window(values[:n + 1], idx, iso_max, mode)
            sharp = _reversal_sharpness(close_vals[:n + 1], idx, atr_val,
                                        sharp_before, sharp_after, sign)
            rows.append({'idx': int(idx), 'prom': prom / atr_val,
                         'iso': iso, 'sharp': sharp})
        if not rows:
            return []

        prom_pct  = _percentile_rank(np.array([r['prom']  for r in rows]))
        iso_pct   = _percentile_rank(np.array([r['iso']   for r in rows]))
        sharp_pct = _percentile_rank(np.array([r['sharp'] for r in rows]))
        for i, r in enumerate(rows):
            r['score'] = w_prom * prom_pct[i] + w_iso * iso_pct[i] + w_sharp * sharp_pct[i]

        rows = sorted(rows, key=lambda r: r['score'], reverse=True)

        if min_score_pct is not None:
            rows = [r for r in rows if r['score'] >= min_score_pct * max_possible]

        if proximity_active:
            filtered = []
            for r in rows:
                a = r['idx']
                base_tpv = cum_tpv[a - 1] if a > 0 else 0.0
                base_vol = cum_vol[a - 1] if a > 0 else 0.0
                seg_vol  = cum_vol[n] - base_vol
                if seg_vol <= 0:
                    continue
                vwap_now = (cum_tpv[n] - base_tpv) / seg_vol
                if abs(vwap_now - current_close) / current_atr <= max_atr_dist:
                    filtered.append(r)
            rows = filtered

        return rows[:max_anchors]

    for mode, slot_key, values in (
        ('valley', 'valley', low_vals),
        ('peak',   'peak',   high_vals),
    ):
        if slot_key not in slots:
            continue
        anchors = score_candidates(values, mode)
        for i, line in enumerate(slots[slot_key]):
            if i < len(anchors):
                line.set(_inline_vwap_df(anchors[i]['idx'], n, cum_tpv, cum_vol, dates))
            else:
                line.set(_empty)


def _load_qqemod_params(ind_conf: str, timeframe: str) -> Optional[dict]:
    """
    Load QQEMOD_params from the indicator config for the given timeframe.
    Returns None if aVWAP is not in the active indicator list, or QQEMOD is not enabled within it.
    """
    try:
        from src.indicators.indicators import load_indicator_config
        result = load_indicator_config(ind_conf, timeframe)
        if not result:
            return None
        ind_list, params = result
        if 'aVWAP' not in ind_list:
            return None
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
        if direction.startswith('_live'):
            continue  # handled separately below
        active = active_at(events, n, direction)
        for idx, line in enumerate(slot_lines):
            if idx < len(active):
                ev = active[idx]
                df_v = get_vwap_df(ev.anchor_bar, n, paths, dates)
                line.set(df_v)
            else:
                line.set(_empty)

    # Live floating anchors — visible during an active zone before it closes
    live_bear = qqemod.get('live_bear')
    live_bull = qqemod.get('live_bull')
    if '_live_bear' in slots and live_bear is not None and n < len(live_bear):
        bar = int(live_bear[n])
        slots['_live_bear'].set(get_vwap_df(bar, n, paths, dates) if bar >= 0 else _empty)
    if '_live_bull' in slots and live_bull is not None and n < len(live_bull):
        bar = int(live_bull[n])
        slots['_live_bull'].set(get_vwap_df(bar, n, paths, dates) if bar >= 0 else _empty)


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

        # Skip columns recomputed historically or handled by Track 4
        if (any(col.startswith(p) for p in _RECOMPUTED_PREFIXES)
                or col in _SEGMENT_COLS
                or _BOS_CHOCH_COL_RE.match(col)):
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
                           and not any(c.startswith(p) for p in _RECOMPUTED_PREFIXES)
                           and c not in _SEGMENT_COLS
                           and not _BOS_CHOCH_COL_RE.match(c))
    print(f"  Track 1 registry: {len(registry)} lines for {n_indicator_cols} indicator columns")
    return registry


# ---------------------------------------------------------------------------
# Segment indicator data (Track 4: BoS/CHoCH, FVG, OB, Liquidity)
# ---------------------------------------------------------------------------

def _build_bos_choch_data(chart, raw_df, colors):
    """Extract BoS/CHoCH events across all swing lengths and pre-create slot Lines.
    Returns None if no BoS_N columns are present."""
    swing_lengths = sorted(
        int(m.group(2))
        for col in raw_df.columns
        for m in [_BOS_CHOCH_COL_RE.match(col)]
        if m and m.group(1) == 'BoS'
    )
    if not swing_lengths:
        return None

    dates  = raw_df['date'].values if 'date' in raw_df.columns else raw_df.index.astype(str).values
    n_bars = len(raw_df)
    events = {'bos_bull': [], 'bos_bear': [], 'choch_bull': [], 'choch_bear': []}

    for sl in swing_lengths:
        bos_col   = f'BoS_{sl}'
        choch_col = f'CHoCH_{sl}'
        price_col = f'BoS_CHoCH_Price_{sl}'
        break_col = f'BoS_CHoCH_Break_Index_{sl}'
        if any(c not in raw_df.columns for c in [bos_col, choch_col, price_col, break_col]):
            continue

        bos_vals   = raw_df[bos_col].values
        choch_vals = raw_df[choch_col].values
        prices     = raw_df[price_col].values
        break_idxs = raw_df[break_col].values

        for i in range(n_bars):
            b, c = bos_vals[i], choch_vals[i]
            if b == 0 and c == 0:
                continue
            price = prices[i]
            if pd.isna(price):
                continue
            bi  = break_idxs[i]
            end = int(bi) if not pd.isna(bi) and bi > 0 else n_bars - 1
            end = min(end, n_bars - 1)
            ev  = {'start_bar': i, 'end_bar': end, 'price': float(price)}
            if b != 0:
                events['bos_bull' if b > 0 else 'bos_bear'].append(ev)
            else:
                events['choch_bull' if c > 0 else 'choch_bear'].append(ev)

    # Sort by start_bar so the "last N" slot selection picks the most recent
    for key in events:
        events[key].sort(key=lambda e: e['start_bar'])

    def _lines(color, count):
        return [chart.create_line(price_line=False, price_label=False,
                                  color=color, width=1, style='solid')
                for _ in range(count)]

    slots = {
        'bos_bull':   _lines(colors['teal_trans_2'], 10),
        'bos_bear':   _lines(colors['red_trans_2'],  10),
        'choch_bull': _lines(colors['aqua'],          6),
        'choch_bear': _lines(colors['red_dark'],      6),
    }
    return {'events': events, 'slots': slots, 'dates': dates}


def _build_fvg_data(chart, raw_df, colors):
    """Extract FVG events and pre-create slot Lines. Returns None if not present."""
    required = ['FVG', 'FVG_High', 'FVG_Low', 'FVG_Mitigated_Index']
    if any(c not in raw_df.columns for c in required):
        return None

    dates    = raw_df['date'].values if 'date' in raw_df.columns else raw_df.index.astype(str).values
    n_bars   = len(raw_df)
    fvg_vals = raw_df['FVG'].values
    fvg_high = raw_df['FVG_High'].values
    fvg_low  = raw_df['FVG_Low'].values
    mit_idxs = raw_df['FVG_Mitigated_Index'].values

    events = {'bull': [], 'bear': []}
    for i in range(n_bars):
        v = fvg_vals[i]
        if v == 0:
            continue
        price = fvg_high[i] if v > 0 else fvg_low[i]
        if pd.isna(price):
            continue
        mi  = mit_idxs[i]
        end = int(mi) if not pd.isna(mi) and mi > 0 else n_bars - 1
        end = min(end, n_bars - 1)
        events['bull' if v > 0 else 'bear'].append(
            {'start_bar': i, 'end_bar': end, 'price': float(price)})

    def _lines(color, count):
        return [chart.create_line(price_line=False, price_label=False,
                                  color=color, width=1, style='dashed')
                for _ in range(count)]

    slots = {
        'bull': _lines(colors['teal_trans_3'], 13),
        'bear': _lines(colors['red_trans_3'],  13),
    }
    return {'events': events, 'slots': slots, 'dates': dates}


def _build_ob_data(chart, raw_df, colors):
    """Extract OB events and pre-create slot Lines. Returns None if not present."""
    required = ['OB', 'OB_High', 'OB_Low']
    if any(c not in raw_df.columns for c in required):
        return None

    dates   = raw_df['date'].values if 'date' in raw_df.columns else raw_df.index.astype(str).values
    n_bars  = len(raw_df)
    ob_vals = raw_df['OB'].values
    ob_high = raw_df['OB_High'].values
    ob_low  = raw_df['OB_Low'].values
    has_mit = 'OB_Mitigated_Index' in raw_df.columns
    mit_idxs = raw_df['OB_Mitigated_Index'].values if has_mit else None

    events = {'bull': [], 'bear': []}
    for i in range(n_bars):
        v = ob_vals[i]
        if v == 0:
            continue
        price = (ob_high[i] + ob_low[i]) / 2.0
        if pd.isna(price):
            continue
        mi  = mit_idxs[i] if mit_idxs is not None else None
        end = int(mi) if mi is not None and not pd.isna(mi) and mi > 0 else n_bars - 1
        end = min(end, n_bars - 1)
        events['bull' if v > 0 else 'bear'].append(
            {'start_bar': i, 'end_bar': end, 'price': float(price)})

    def _lines(color, count):
        return [chart.create_line(price_line=False, price_label=False,
                                  color=color, width=10, style='solid')
                for _ in range(count)]

    slots = {
        'bull': _lines(colors['teal_OB'], 8),
        'bear': _lines(colors['red_OB'],  8),
    }
    return {'events': events, 'slots': slots, 'dates': dates}


def _build_liquidity_data(chart, raw_df, colors):
    """Extract Liquidity events and pre-create slot Lines. Returns None if not present."""
    if not all(c in raw_df.columns for c in ['Liquidity', 'Liquidity_Level']):
        return None

    dates    = raw_df['date'].values if 'date' in raw_df.columns else raw_df.index.astype(str).values
    n_bars   = len(raw_df)
    liq_vals = raw_df['Liquidity'].values
    liq_lvls = raw_df['Liquidity_Level'].values

    events = []
    for i in range(n_bars):
        if liq_vals[i] == 0:
            continue
        price = liq_lvls[i]
        if pd.isna(price) or price == 0:
            continue
        # Liquidity has no mitigation index — line extends to current bar
        events.append({'start_bar': i, 'end_bar': n_bars - 1, 'price': float(price)})

    slots = [chart.create_line(price_line=False, price_label=False,
                               color=colors['orange_liquidity'], width=1, style='solid')
             for _ in range(25)]
    return {'events': events, 'slots': slots, 'dates': dates}


def _render_segment_slots(seg_data, n):
    """Update all slots for one segment indicator at bar n."""
    if seg_data is None:
        return
    dates = seg_data['dates']

    def _update_pool(event_list, slot_list):
        active = [e for e in event_list if e['start_bar'] <= n]
        active = active[-len(slot_list):]
        for i, slot in enumerate(slot_list):
            if i < len(active):
                ev      = active[i]
                end_bar = min(ev['end_bar'], n)
                try:
                    slot.set(pd.DataFrame({
                        'time':  [str(dates[ev['start_bar']]), str(dates[end_bar])],
                        'value': [ev['price'], ev['price']],
                    }))
                except Exception:
                    pass
            else:
                try:
                    slot.set(_EMPTY_SEG)
                except Exception:
                    pass

    events = seg_data['events']
    slots  = seg_data['slots']

    if isinstance(events, dict):
        for key, ev_list in events.items():
            if key in slots:
                _update_pool(ev_list, slots[key])
    else:
        _update_pool(events, slots)


# ---------------------------------------------------------------------------
# Ticker switching
# ---------------------------------------------------------------------------

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
    if state.get('anchor_score'):
        _render_anchor_score_slots(state['anchor_score'], n)

    # Segment indicators (Track 4)
    _render_segment_slots(state.get('bos_choch'), n)
    _render_segment_slots(state.get('fvg'), n)
    _render_segment_slots(state.get('ob'), n)
    _render_segment_slots(state.get('liquidity'), n)

    if state.get('auto_fit', True):
        chart.fit()

    try:
        chart.topbar['bar'].set(f'{n}/{len(df) - 1}')
    except Exception:
        pass


def _step(chart, state, delta):
    """Step backward (delta < 0) or forward (delta > 0) by |delta| bars."""
    n_total = state['n_total']
    target = max(0, min(state['n'] + delta, n_total - 1))
    if target != state['n']:
        state['n'] = target
        _render(chart, state['prepared_df'], state['registry'], state, target)


def _jump(chart, state, target):
    """Jump directly to a specific bar index."""
    target = max(0, min(target, state['n_total'] - 1))
    state['n'] = target
    _render(chart, state['prepared_df'], state['registry'], state, target)


def _on_bar_search(chart, state, value):
    """
    Called when the user types in the chart search box.
    - Number  → jump to that bar index
    - Letters → load that ticker from the tickers buffer
    """
    value = value.strip().upper()
    if not value:
        return

    # Try bar-number jump first
    try:
        target = int(value)
        _jump(chart, state, target)
        print(f"[Replay] Jumped to bar {state['n']}/{state['n_total'] - 1}")
        return
    except ValueError:
        pass

    # Otherwise treat as a ticker symbol — load it directly
    ind_conf  = state.get('ind_conf', '0')
    timeframe = state.get('timeframe', 'daily')
    colors    = state.get('colors', get_color_palette())
    _load_ticker_by_name(chart, state, value, ind_conf, timeframe, colors)


def _load_ticker_by_name(chart: Chart, state: dict, ticker: str,
                         ind_conf: str, timeframe: str, colors: dict) -> None:
    """Load an arbitrary ticker from the tickers buffer and restart replay at bar 0."""
    state['playing'] = False
    print(f"\n[Replay] Loading {ticker} ...")

    try:
        raw_df = _load_for_replay(ticker, timeframe, ind_conf)
    except Exception as e:
        print(f"  Could not load {ticker}: {e}")
        return

    if raw_df is None or raw_df.empty:
        print(f"  No data for {ticker} — not found in tickers buffer")
        return

    try:
        prepared_df, _ = prepare_dataframe(raw_df, show_volume=False, padding_ratio=0)
        n_total = len(prepared_df)
        if n_total == 0:
            return

        _empty = pd.DataFrame(columns=['time', 'value'])
        for line in state['registry'].values():
            try:
                line.set(_empty)
            except Exception:
                pass

        new_registry      = _build_line_registry(chart, prepared_df, colors)
        new_qqemod        = _build_qqemod_data(raw_df, ind_conf, timeframe, colors)
        new_pmm           = _build_pmm_data(raw_df, ind_conf, timeframe, colors)
        new_anchor_score  = _build_anchor_score_data(raw_df, ind_conf, timeframe, colors)
        new_bos_choch     = _build_bos_choch_data(chart, raw_df, colors)
        new_fvg           = _build_fvg_data(chart, raw_df, colors)
        new_ob            = _build_ob_data(chart, raw_df, colors)
        new_liquidity     = _build_liquidity_data(chart, raw_df, colors)

        if new_qqemod is not None and state.get('qqemod') and state['qqemod'].get('slots'):
            new_qqemod['slots'] = state['qqemod']['slots']
        if new_pmm is not None and state.get('pmm') and state['pmm'].get('slots'):
            new_pmm['slots'] = state['pmm']['slots']
        if new_anchor_score is not None and state.get('anchor_score') and state['anchor_score'].get('slots'):
            new_anchor_score['slots'] = state['anchor_score']['slots']
        if new_bos_choch is not None and state.get('bos_choch') and state['bos_choch'].get('slots'):
            new_bos_choch['slots'] = state['bos_choch']['slots']
        if new_fvg is not None and state.get('fvg') and state['fvg'].get('slots'):
            new_fvg['slots'] = state['fvg']['slots']
        if new_ob is not None and state.get('ob') and state['ob'].get('slots'):
            new_ob['slots'] = state['ob']['slots']
        if new_liquidity is not None and state.get('liquidity') and state['liquidity'].get('slots'):
            new_liquidity['slots'] = state['liquidity']['slots']

        state['prepared_df']  = prepared_df
        state['n_total']      = n_total
        state['registry']     = new_registry
        state['qqemod']       = new_qqemod
        state['pmm']          = new_pmm
        state['anchor_score'] = new_anchor_score
        state['bos_choch']    = new_bos_choch
        state['fvg']          = new_fvg
        state['ob']           = new_ob
        state['liquidity']    = new_liquidity
        state['n']            = 0

        try:
            chart.topbar['ticker'].set(ticker)
            chart.topbar['bar'].set(f'0/{n_total - 1}')
        except Exception:
            pass

        _render(chart, prepared_df, new_registry, state, 0)
        print(f"[Replay] {ticker}  ({n_total} bars)")

    except Exception as e:
        print(f"  Error loading {ticker}: {e}")


def _toggle_auto_fit(chart, state):
    """Toggle auto-fit mode."""
    state['auto_fit'] = not state['auto_fit']
    try:
        chart.topbar['auto_fit'].set('FIT: ON' if state['auto_fit'] else 'FIT: OFF')
    except Exception:
        pass
    if state['auto_fit']:
        chart.fit()


def _toggle_play(state):
    """Toggle play / pause."""
    state['playing'] = not state['playing']
    label = 'Playing' if state['playing'] else 'Paused'
    print(f"[Replay] {label}  bar {state['n']}/{state['n_total'] - 1}  {state['speed']:.2f}s/bar")


def _adjust_speed(state, chart, delta):
    """Change step interval, clamped to [0.05, 2.0] seconds."""
    state['speed'] = max(0.05, min(state['speed'] + delta, 2.0))
    multiplier = _BASE_SPEED / state['speed']
    try:
        chart.topbar['speed'].set(f'{multiplier:.1f}x')
    except Exception:
        pass
    print(f"[Replay] Speed: {state['speed']:.2f} s/bar  ({multiplier:.1f}x)")


def _reset_speed(state, chart):
    """Reset step interval to default (1.0x)."""
    state['speed'] = _BASE_SPEED
    try:
        chart.topbar['speed'].set('1.0x')
    except Exception:
        pass
    print(f"[Replay] Speed reset to 1.0x")


def _play_loop(chart, state):
    """Background thread: advance one bar per interval while playing."""
    while True:
        if state['playing']:
            n = state['n']
            n_total = state['n_total']
            if n >= n_total - 1:
                state['playing'] = False
                print("[Replay] Reached end of data — paused")
            else:
                state['n'] = n + 1
                _render(chart, state['prepared_df'], state['registry'], state, n + 1)
                time.sleep(state['speed'])
        else:
            time.sleep(0.05)
