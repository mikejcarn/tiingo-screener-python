"""
Export the replay dataset as a self-contained interactive HTML file.

All data (OHLCV + Track 1 indicators + OB segments + QQEMOD aVWAPs) is
embedded as JSON; the lightweight-charts v4 library JS is embedded inline
so the file works offline with no dependencies.
"""

import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Column classification (mirrors replay/__init__.py constants)
# ---------------------------------------------------------------------------

_OHLCV_COLS = frozenset({'date', 'time', 'index', 'open', 'high', 'low', 'close', 'volume', 'color'})

# Columns excluded from Track 1 (CSV lookahead): handled by dedicated extractors.
_RECOMPUTED_PREFIXES = (
    'aVWAP_QQEMOD_bear_dot_',
    'aVWAP_QQEMOD_bull_dot_',
    'aVWAP_QQEMOD_bear_c',
    'aVWAP_QQEMOD_bull_c',
    'aVWAP_price_maxima_minima_valley_',
    'aVWAP_price_maxima_minima_peak_',
    'aVWAP_OB_bull_',
    'aVWAP_OB_bear_',
    'aVWAP_BoS_bull_',
    'aVWAP_BoS_bear_',
    'aVWAP_CHoCH_bull_',
    'aVWAP_CHoCH_bear_',
    'aVWAP_peak_c',
    'aVWAP_valley_c',
)

_SEGMENT_COLS = frozenset({
    'Liquidity', 'Liquidity_Level',
    'FVG', 'FVG_High', 'FVG_Low', 'FVG_Mitigated_Index',
    'OB', 'OB_High', 'OB_Low', 'OB_Mitigated_Index',
})

_BOS_CHOCH_COL_RE = re.compile(
    r'^(BoS|CHoCH|BoS_CHoCH_Price|BoS_CHoCH_Break_Index)_(\d+)$'
)


def _cfg_idx(col):
    m = re.search(r'_c(\d+)_', col)
    return int(m.group(1)) if m else 0


def _is_track1(col):
    return (col not in _OHLCV_COLS
            and not any(col.startswith(p) for p in _RECOMPUTED_PREFIXES)
            and col not in _SEGMENT_COLS
            and not _BOS_CHOCH_COL_RE.match(col))


# ---------------------------------------------------------------------------
# Color mapping  (mirrors _build_line_registry logic)
# ---------------------------------------------------------------------------

def _col_styles(df, colors):
    """Return {col: {color, width, style}} for all Track 1 indicator columns."""
    styles = {}

    def _add(col, color, width, style='solid'):
        styles[col] = {'color': color, 'width': int(width) if width == int(width) else width, 'style': style}

    def _w(cfg): return 2 if cfg == 0 else 1
    def _s(cfg): return 'solid' if cfg == 0 else 'dotted'

    for col in df.columns:
        if not _is_track1(col):
            continue
        cfg = _cfg_idx(col)

        if col.startswith('aVWAP_pinch_peak_'):
            _add(col, colors['red_trans_3'], 1)
        elif col.startswith('aVWAP_pinch_valley_'):
            _add(col, colors['teal_trans_3'], 1)
        elif col.startswith('aVWAP_pinch_above_'):
            _add(col, colors['teal_trans_2'], 1, 'dotted')
        elif col.startswith('aVWAP_pinch_below_'):
            _add(col, colors['red_trans_2'], 1, 'dotted')
        elif col.startswith('aVWAP_peak_'):
            _add(col, colors['red_trans_3'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_valley_'):
            _add(col, colors['teal_trans_3'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_BoS_bear_'):
            _add(col, colors['red_trans_3'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_BoS_bull_'):
            _add(col, colors['teal_trans_3'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_CHoCH_bear_'):
            _add(col, colors['red_trans_2'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_CHoCH_bull_'):
            _add(col, colors['teal_trans_2'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_OB_bull_ghost_'):
            _add(col, colors['teal_OB_ghost'], 1)
        elif col.startswith('aVWAP_OB_bear_ghost_'):
            _add(col, colors['red_OB_ghost'], 1)
        elif col.startswith('aVWAP_OB_bull_'):
            _add(col, colors['teal_OB'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_OB_bear_'):
            _add(col, colors['red_OB'], _w(cfg), _s(cfg))
        elif col.startswith('Gap_Up_aVWAP_'):
            _add(col, colors['teal_trans_2'], _w(cfg), _s(cfg))
        elif col.startswith('Gap_Down_aVWAP_'):
            _add(col, colors['red_trans_2'], _w(cfg), _s(cfg))
        elif col.startswith('Peaks_Valleys_avg'):
            mc = [c for c in df.columns if c.startswith('Peaks_Valleys_avg')]
            _add(col, colors['orange_aVWAP'], 4 if (col == 'Peaks_Valleys_avg' and len(mc) > 1) else 2)
        elif col.startswith('Peaks_avg'):
            mc = [c for c in df.columns if c.startswith('Peaks_avg')]
            _add(col, colors['red'], 4 if (col == 'Peaks_avg' and len(mc) > 1) else 2)
        elif col.startswith('Valleys_avg'):
            mc = [c for c in df.columns if c.startswith('Valleys_avg')]
            _add(col, colors['teal'], 4 if (col == 'Valleys_avg' and len(mc) > 1) else 2)
        elif col.startswith('OB_avg'):
            mc = [c for c in df.columns if c.startswith('OB_avg')]
            _add(col, colors['orange_aVWAP'], 3 if (col == 'OB_avg' and len(mc) > 1) else 2, 'dashed')
        elif col.startswith('Gaps_avg'):
            mc = [c for c in df.columns if c.startswith('Gaps_avg')]
            _add(col, colors['orange_aVWAP'], 4 if (col == 'Gaps_avg' and len(mc) > 1) else 2, 'dotted')
        elif col.startswith('BoS_CHoCH_avg'):
            mc = [c for c in df.columns if c.startswith('BoS_CHoCH_avg')]
            _add(col, colors['orange_aVWAP'], 3 if (col == 'BoS_CHoCH_avg' and len(mc) > 1) else 2, 'large_dashed')
        elif col.startswith('QQEMOD_avg'):
            mc = [c for c in df.columns if c.startswith('QQEMOD_avg')]
            _add(col, colors['orange_aVWAP'], 3 if (col == 'QQEMOD_avg' and len(mc) > 1) else 2)
        elif col.startswith('All_avg'):
            mc = [c for c in df.columns if c.startswith('All_avg')]
            _add(col, colors['gray_trans'], 5 if (col == 'All_avg' and len(mc) > 1) else 3)
        elif col.startswith('SMA_'):
            try:
                period = int(col.split('_')[1])
            except Exception:
                period = 0
            w = (1 if period <= 10 else 2 if period <= 50 else 3 if period <= 100 else 4 if period <= 200 else 5)
            _add(col, colors['blue_SMA'], w)
        elif col == 'Supertrend_Upper':
            _add(col, colors['orange'], 1)
        elif col == 'Supertrend_Lower':
            _add(col, colors['orange'], 1)

    # Synthetic Supertrend active line
    if all(c in df.columns for c in ('Supertrend_Upper', 'Supertrend_Lower', 'Supertrend_Direction')):
        styles['_Supertrend_Active'] = {'color': colors['black'], 'width': 2, 'style': 'solid'}

    return styles


# ---------------------------------------------------------------------------
# Data serialisation helpers
# ---------------------------------------------------------------------------

def _to_unix(ts):
    try:
        return int(pd.Timestamp(ts).timestamp())
    except Exception:
        return 0


def _safe_float(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (f != f) else f  # NaN → None
    except Exception:
        return None


def _build_data(prepared_df, col_styles):
    """Serialise prepared_df into a list of bar dicts with all indicator values inline."""
    track1_cols = [c for c in col_styles if c != '_Supertrend_Active' and c in prepared_df.columns]
    has_supertrend = '_Supertrend_Active' in col_styles
    has_volume = 'volume' in prepared_df.columns

    # Per-bar candle color column (from the candle_colors indicator — supports full palette)
    has_color_col = 'color' in prepared_df.columns

    # Fallback: QQEMOD zone column (2-color) when candle_colors was not run
    zone_col = None
    if not has_color_col:
        zone_col = next(
            (c for c in prepared_df.columns if re.search(r'QQE1_Above_Upper', c)),
            None
        )

    bars = []
    for row in prepared_df.itertuples(index=False):
        bar = {
            'time':  _to_unix(row.date),
            'open':  _safe_float(row.open),
            'high':  _safe_float(row.high),
            'low':   _safe_float(row.low),
            'close': _safe_float(row.close),
        }
        if has_volume:
            bar['v'] = _safe_float(getattr(row, 'volume', None))
        if has_color_col:
            raw_clr = getattr(row, 'color', None)
            # Store as 'c'; None / NaN / non-string falls back to zone coloring in JS
            bar['c'] = raw_clr if isinstance(raw_clr, str) and raw_clr else None
        elif zone_col:
            zone_val = getattr(row, zone_col, None)
            bar['z'] = 1 if (zone_val and not pd.isna(zone_val)) else 0

        for col in track1_cols:
            bar[col] = _safe_float(getattr(row, col, None))

        if has_supertrend:
            try:
                direction = getattr(row, 'Supertrend_Direction', 1)
                upper = _safe_float(getattr(row, 'Supertrend_Upper', None))
                lower = _safe_float(getattr(row, 'Supertrend_Lower', None))
                bar['_Supertrend_Active'] = lower if (direction and direction >= 0) else upper
            except Exception:
                bar['_Supertrend_Active'] = None

        bars.append(bar)
    return bars


# ---------------------------------------------------------------------------
# OB extraction  (mirrors _build_ob_data without chart slot creation)
# ---------------------------------------------------------------------------

def _extract_ob_events(raw_df, ind_conf, timeframe, colors):
    """Extract OB events with visibility metadata for HTML serialisation."""
    from src.visualization.src.replay import _load_ob_params
    ob_params = _load_ob_params(ind_conf, timeframe)
    if ob_params is None:
        return None

    periods         = ob_params.get('periods',         20)
    max_mitigated   = ob_params.get('max_mitigated',   10)
    max_unmitigated = ob_params.get('max_unmitigated', None)
    per_side        = ob_params.get('per_side',        True)

    from smartmoneyconcepts import smc as _smc
    col_lower = {c.lower(): c for c in raw_df.columns}
    needed = ['open', 'high', 'low', 'close', 'volume']
    if not all(k in col_lower for k in needed):
        return None

    ohlcv = raw_df[[col_lower[k] for k in needed]].copy()
    ohlcv.columns = needed

    try:
        swing_hl = _smc.swing_highs_lows(ohlcv, swing_length=periods)
        result   = _smc.ob(ohlcv, swing_hl, close_mitigation=False)
    except Exception:
        return None

    n_bars = len(raw_df)
    n_res  = len(result)

    ob_col  = result['OB'].values             if 'OB'             in result.columns else None
    top_col = result['Top'].values            if 'Top'            in result.columns else None
    bot_col = result['Bottom'].values         if 'Bottom'         in result.columns else None
    mit_col = result['MitigatedIndex'].values if 'MitigatedIndex' in result.columns else None

    if ob_col is None or top_col is None or bot_col is None:
        return None

    raw_events = {'bull': [], 'bear': []}
    for i in range(min(n_bars, n_res)):
        v = ob_col[i]
        if v == 0 or pd.isna(v):
            continue
        price = (top_col[i] + bot_col[i]) / 2.0
        if pd.isna(price):
            continue
        mi  = mit_col[i] if mit_col is not None else None
        end = int(mi) if mi is not None and not pd.isna(mi) and mi > 0 else n_bars - 1
        end = min(end, n_bars - 1)
        raw_events['bull' if v > 0 else 'bear'].append(
            {'start_bar': i, 'end_bar': end, 'price': float(price),
             'is_mitigated': end < n_bars - 1})

    if not any(raw_events.values()):
        return None

    # Compute visible_from for each event
    if 'HighLow' in swing_hl.columns:
        hl_vals    = swing_hl['HighLow'].values
        sh_indices = np.where(hl_vals == 1)[0]
        sl_indices = np.where(hl_vals == -1)[0]
        high_arr   = ohlcv['high'].values
        low_arr    = ohlcv['low'].values
        close_arr  = ohlcv['close'].values

        for direction, ev_list in raw_events.items():
            is_bull     = (direction == 'bull')
            ref_indices = sh_indices if is_bull else sl_indices
            level_arr   = high_arr   if is_bull else low_arr

            for ev in ev_list:
                ob_idx = ev['start_bar']
                pos    = np.searchsorted(ref_indices, ob_idx, side='left') - 1
                if pos < 0:
                    continue
                sh_bar   = int(ref_indices[pos])
                sh_level = float(level_arr[sh_bar])
                close_idx = n_bars - 1
                for j in range(sh_bar + 1, n_bars):
                    if (is_bull and close_arr[j] > sh_level) or \
                       (not is_bull and close_arr[j] < sh_level):
                        close_idx = j
                        break
                ev['visible_from'] = max(close_idx, sh_bar + periods)

    def _displace(ev_list, cap):
        evs = sorted(ev_list, key=lambda e: e['start_bar'])
        for i, ev in enumerate(evs):
            if i + cap < len(evs):
                ev['displaced_at'] = evs[i + cap]['start_bar']

    if max_unmitigated is not None:
        if per_side:
            _displace([ev for ev in raw_events['bull'] if not ev['is_mitigated']], max_unmitigated)
            _displace([ev for ev in raw_events['bear'] if not ev['is_mitigated']], max_unmitigated)
        else:
            _displace([ev for ev in (raw_events['bull'] + raw_events['bear'])
                       if not ev['is_mitigated']], max_unmitigated)

    if max_mitigated is not None and max_mitigated > 0:
        if per_side:
            _displace([ev for ev in raw_events['bull'] if ev['is_mitigated']], max_mitigated)
            _displace([ev for ev in raw_events['bear'] if ev['is_mitigated']], max_mitigated)
        else:
            _displace([ev for ev in (raw_events['bull'] + raw_events['bear'])
                       if ev['is_mitigated']], max_mitigated)

    all_events = []
    for direction in ('bull', 'bear'):
        for ev in raw_events[direction]:
            e = {
                'dir': direction,
                's':   ev['start_bar'],
                'e':   ev['end_bar'],
                'p':   ev['price'],
                'm':   ev['is_mitigated'],
            }
            if 'visible_from' in ev:
                e['vf'] = ev['visible_from']
            if 'displaced_at' in ev:
                e['da'] = ev['displaced_at']
            all_events.append(e)

    return {
        'events':    all_events,
        'max_mit':   max_mitigated if max_mitigated is not None else -1,
        'bull_clr':  colors['teal_OB'],
        'bear_clr':  colors['red_OB'],
    }


# ---------------------------------------------------------------------------
# QQEMOD extraction  (reuses _build_qqemod_data which needs no chart object)
# ---------------------------------------------------------------------------

def _extract_qqemod_events(raw_df, ind_conf, timeframe, colors):
    """Extract QQEMOD anchor events and precomputed VWAP paths for HTML serialisation."""
    from src.visualization.src.replay import _build_qqemod_data
    try:
        data = _build_qqemod_data(raw_df, ind_conf, timeframe, colors)
    except Exception as e:
        print(f"  Warning: QQEMOD data build failed: {e}")
        return None
    if data is None:
        return None

    events     = data['events']
    paths      = data['paths']
    live_bear  = data.get('live_bear')
    live_bull  = data.get('live_bull')
    directions = data['directions']

    # direction → (color, lineWidth, lineStyle int)
    style_map = {
        'bear_dot': (colors['teal'], 1, 1),
        'bull_dot': (colors['red'],  1, 1),
        'bear':     (colors['teal'], 2, 0),
        'bull':     (colors['red'],  2, 0),
    }

    anchors = []
    for ev in events:
        ab = ev.anchor_bar
        if ab not in paths:
            continue
        raw_path = paths[ab]
        vals = [None if (isinstance(v, float) and v != v) else _safe_float(v)
                for v in raw_path]
        color, width, ls = style_map.get(ev.direction, (colors['gray_trans'], 1, 0))
        anchors.append({
            'dir':  ev.direction,
            'add':  ev.add_bar,
            'rem':  ev.remove_bar,   # None → null in JSON
            'ab':   ab,
            'vals': vals,
            'clr':  color,
            'w':    width,
            'ls':   ls,
        })

    result = {'anchors': anchors}

    # Per-bar zone array for candle coloring: 1=bull/teal, 0=bear/red, None=neutral.
    # Derived from live_bear/live_bull which _build_qqemod_data always returns,
    # even when zone columns are absent from the CSV (it recomputes them on the fly).
    if live_bear is not None and live_bull is not None:
        zone = []
        for b, bl in zip(live_bear, live_bull):
            if int(bl) >= 0:
                zone.append(1)
            elif int(b) >= 0:
                zone.append(0)
            else:
                zone.append(None)
        result['zone'] = zone

    # Live floating anchor arrays (solid bear/bull only — dotted don't have live lines)
    committed_bars = {a['ab'] for a in anchors}
    live_extra = set()

    if live_bear is not None and 'bear' in directions:
        arr = [int(v) for v in live_bear]
        result['live_bear'] = arr
        result['live_bear_clr'] = colors['teal']
        live_extra.update(b for b in arr if b >= 0)

    if live_bull is not None and 'bull' in directions:
        arr = [int(v) for v in live_bull]
        result['live_bull'] = arr
        result['live_bull_clr'] = colors['red']
        live_extra.update(b for b in arr if b >= 0)

    # Shared path lookup for live-only anchor bars (not already in committed events)
    extra_bars = live_extra - committed_bars
    if extra_bars:
        shared = {}
        for ab in extra_bars:
            if ab in paths:
                rp = paths[ab]
                shared[str(ab)] = [None if (isinstance(v, float) and v != v) else _safe_float(v)
                                    for v in rp]
        if shared:
            result['live_paths'] = shared

    return result


# ---------------------------------------------------------------------------
# PMM aVWAP extraction  (historical recomputation — same as _build_pmm_data)
# ---------------------------------------------------------------------------

def _extract_pmm_events(raw_df, ind_conf, timeframe):
    """Pre-compute greedy_extrema slot assignments for every bar.

    At each bar n we record which anchor occupies each slot (valley 0..k, peak 0..k).
    This mirrors _build_pmm_data / _render_pmm_slots in replay/__init__.py exactly,
    so the HTML shows the same evolving anchors as --replay.
    """
    from src.visualization.src.replay import _load_pmm_params, _greedy_extrema
    from src.visualization.src.replay.vwap import build_cumulative_arrays

    pmm_params = _load_pmm_params(ind_conf, timeframe)
    if pmm_params is None:
        return None

    max_anchors     = int(pmm_params.get('max_anchors') or 5)
    spacing         = int(pmm_params.get('min_swing_spacing', 30))
    include_valleys = bool(pmm_params.get('valleys', True))
    include_peaks   = bool(pmm_params.get('peaks',   False))

    if not include_valleys and not include_peaks:
        return None

    cum_tpv, cum_vol = build_cumulative_arrays(raw_df)
    low_vals  = raw_df['low'].values  if 'low'  in raw_df.columns else raw_df['Low'].values
    high_vals = raw_df['high'].values if 'high' in raw_df.columns else raw_df['High'].values
    n_bars = len(raw_df)

    direction_results = {}
    all_anchor_bars   = set()

    for direction, include, src_vals in [
        ('valley', include_valleys, low_vals),
        ('peak',   include_peaks,   high_vals),
    ]:
        if not include:
            continue
        # slots[slot_idx][bar_n] = anchor bar index at that bar, -1 if empty
        slots = [[-1] * n_bars for _ in range(max_anchors)]

        for n in range(n_bars):
            anchors = _greedy_extrema(src_vals[:n + 1], direction, max_anchors, spacing)
            for i, ab in enumerate(anchors):
                slots[i][n] = int(ab)
                all_anchor_bars.add(int(ab))

        direction_results[direction] = {'slots': slots}

    if not direction_results:
        return None

    # Trim each VWAP path to the last bar it's actually used (saves JSON space)
    last_used: dict = {}
    for side in direction_results.values():
        for slot_arr in side['slots']:
            for n, ab in enumerate(slot_arr):
                if ab >= 0:
                    last_used[ab] = max(last_used.get(ab, 0), n)

    # Build shared VWAP path lookup  (key = anchor bar index)
    paths: dict = {}
    for ab in all_anchor_bars:
        base_tpv = cum_tpv[ab - 1] if ab > 0 else 0.0
        base_vol = cum_vol[ab - 1] if ab > 0 else 0.0
        end_n    = last_used.get(ab, n_bars - 1)
        seg_tpv  = cum_tpv[ab:end_n + 1] - base_tpv
        seg_vol  = cum_vol[ab:end_n + 1] - base_vol
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = np.where(seg_vol > 0, seg_tpv / seg_vol, np.nan)
        paths[ab] = [None if (isinstance(v, float) and v != v) else float(v) for v in vals]

    return {**direction_results, 'paths': paths}


# ---------------------------------------------------------------------------
# FVG extraction
# ---------------------------------------------------------------------------

def _extract_fvg_events(raw_df, ind_conf, timeframe, colors):
    """Extract FVG events for HTML serialisation (mirrors _build_fvg_data)."""
    from src.visualization.src.replay import _load_fvg_params
    fvg_params = _load_fvg_params(ind_conf, timeframe)
    if fvg_params is None:
        return None

    max_mitigated   = fvg_params.get('max_mitigated',   10)
    max_unmitigated = fvg_params.get('max_unmitigated', None)
    join_consecutive = fvg_params.get('join_consecutive', False)

    from smartmoneyconcepts import smc as _smc
    col_lower = {c.lower(): c for c in raw_df.columns}
    needed = ['open', 'high', 'low', 'close', 'volume']
    if not all(k in col_lower for k in needed):
        return None

    ohlcv = raw_df[[col_lower[k] for k in needed]].copy()
    ohlcv.columns = needed

    try:
        result = _smc.fvg(ohlcv, join_consecutive=join_consecutive)
    except Exception:
        return None

    n_bars = len(raw_df)
    n_res  = len(result)

    fvg_col = result['FVG'].values            if 'FVG'            in result.columns else None
    top_col = result['Top'].values            if 'Top'            in result.columns else None
    bot_col = result['Bottom'].values         if 'Bottom'         in result.columns else None
    mit_col = result['MitigatedIndex'].values if 'MitigatedIndex' in result.columns else None

    if fvg_col is None or top_col is None or bot_col is None:
        return None

    raw_events = {'bull': [], 'bear': []}
    for i in range(min(n_bars, n_res)):
        v = fvg_col[i]
        if v == 0 or pd.isna(v):
            continue
        # FVG uses the outer edge (top for bull, bottom for bear) as the line level
        price = top_col[i] if v > 0 else bot_col[i]
        if pd.isna(price):
            continue
        mi  = mit_col[i] if mit_col is not None else None
        end = int(mi) if mi is not None and not pd.isna(mi) and mi > 0 else n_bars - 1
        end = min(end, n_bars - 1)
        raw_events['bull' if v > 0 else 'bear'].append(
            {'start_bar': i, 'end_bar': end, 'price': float(price),
             'is_mitigated': end < n_bars - 1})

    if not any(raw_events.values()):
        return None

    if max_unmitigated is not None:
        perm = sorted([ev for ev in (raw_events['bull'] + raw_events['bear'])
                       if not ev['is_mitigated']], key=lambda e: e['start_bar'])
        for i, ev in enumerate(perm):
            if i + max_unmitigated < len(perm):
                ev['displaced_at'] = perm[i + max_unmitigated]['start_bar']

    if max_mitigated is not None and max_mitigated > 0:
        mit = sorted([ev for ev in (raw_events['bull'] + raw_events['bear'])
                      if ev['is_mitigated']], key=lambda e: e['start_bar'])
        for i, ev in enumerate(mit):
            if i + max_mitigated < len(mit):
                ev['displaced_at'] = mit[i + max_mitigated]['start_bar']

    all_events = []
    for direction in ('bull', 'bear'):
        for ev in raw_events[direction]:
            e = {'dir': direction, 's': ev['start_bar'], 'e': ev['end_bar'],
                 'p': ev['price'], 'm': ev['is_mitigated']}
            if 'displaced_at' in ev:
                e['da'] = ev['displaced_at']
            all_events.append(e)

    return {
        'events':   all_events,
        'max_mit':  max_mitigated if max_mitigated is not None else -1,
        'bull_clr': colors['teal_trans_3'],
        'bear_clr': colors['red_trans_3'],
        'ls':       2,  # dashed
    }


# ---------------------------------------------------------------------------
# BoS/CHoCH extraction
# ---------------------------------------------------------------------------

def _extract_bos_choch_events(raw_df, colors):
    """Extract BoS/CHoCH events from CSV columns (mirrors _build_bos_choch_data)."""
    swing_lengths = sorted(
        int(m.group(2))
        for col in raw_df.columns
        for m in [_BOS_CHOCH_COL_RE.match(col)]
        if m and m.group(1) == 'BoS'
    )
    if not swing_lengths:
        return None

    n_bars = len(raw_df)
    raw_events = {'bos_bull': [], 'bos_bear': [], 'choch_bull': [], 'choch_bear': []}

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
            ev  = {'s': i, 'e': end, 'p': float(price)}
            if b != 0:
                raw_events['bos_bull' if b > 0 else 'bos_bear'].append(ev)
            else:
                raw_events['choch_bull' if c > 0 else 'choch_bear'].append(ev)

    if not any(raw_events.values()):
        return None

    color_map = {
        'bos_bull':   colors['teal_trans_2'],
        'bos_bear':   colors['red_trans_2'],
        'choch_bull': colors['aqua'],
        'choch_bear': colors['red_dark'],
    }

    all_events = []
    for direction, ev_list in raw_events.items():
        for ev in ev_list:
            all_events.append({**ev, 'dir': direction, 'clr': color_map[direction]})

    return {'events': all_events}


# ---------------------------------------------------------------------------
# Liquidity extraction
# ---------------------------------------------------------------------------

def _extract_liquidity_events(raw_df, ind_conf, timeframe, colors):
    """Extract liquidity events for HTML serialisation (mirrors _build_liquidity_data)."""
    from src.visualization.src.replay import _load_liquidity_params
    liq_params = _load_liquidity_params(ind_conf, timeframe)
    if liq_params is None:
        return None

    swing_length  = liq_params.get('swing_length',  25)
    range_percent = liq_params.get('range_percent', 0.1)
    max_swept     = liq_params.get('max_swept',     10)
    max_unswept   = liq_params.get('max_unswept',   None)
    extend_lines  = liq_params.get('extend_lines',  False)

    from smartmoneyconcepts import smc as _smc
    col_lower = {c.lower(): c for c in raw_df.columns}
    needed = ['open', 'high', 'low', 'close', 'volume']
    if not all(k in col_lower for k in needed):
        return None

    ohlcv = raw_df[[col_lower[k] for k in needed]].copy()
    ohlcv.columns = needed

    try:
        swing_hl = _smc.swing_highs_lows(ohlcv, swing_length=swing_length)
        result   = _smc.liquidity(ohlcv, swing_hl, range_percent=range_percent)
    except Exception:
        return None

    n_bars = len(raw_df)
    n_res  = len(result)

    liq_col   = result['Liquidity'].values if 'Liquidity' in result.columns else None
    level_col = result['Level'].values     if 'Level'     in result.columns else None
    end_col   = result['End'].values       if 'End'       in result.columns else None
    swept_col = result['Swept'].values     if 'Swept'     in result.columns else None

    if liq_col is None or level_col is None:
        return None

    raw_events = {'bull': [], 'bear': []}
    for i in range(min(n_bars, n_res)):
        v = liq_col[i]
        if v == 0 or pd.isna(v):
            continue
        price = level_col[i]
        if pd.isna(price) or price == 0:
            continue
        sw  = swept_col[i] if swept_col is not None else None
        end = int(sw) if sw is not None and not pd.isna(sw) and sw > 0 else n_bars - 1
        end = min(end, n_bars - 1)
        group_end = int(end_col[i]) if end_col is not None and not pd.isna(end_col[i]) else i
        raw_events['bull' if v > 0 else 'bear'].append(
            {'start_bar': i, 'end_bar': end, 'price': float(price),
             'is_mitigated': end < n_bars - 1, 'group_end': group_end})

    if not any(raw_events.values()):
        return None

    for ev_list in raw_events.values():
        for ev in ev_list:
            ev['visible_from'] = ev['group_end'] + swing_length

    if max_unswept is not None:
        perm = sorted([ev for ev in (raw_events['bull'] + raw_events['bear'])
                       if not ev['is_mitigated']], key=lambda e: e['start_bar'])
        for i, ev in enumerate(perm):
            if i + max_unswept < len(perm):
                ev['displaced_at'] = perm[i + max_unswept]['start_bar']

    if max_swept is not None and max_swept > 0:
        swept = sorted([ev for ev in (raw_events['bull'] + raw_events['bear'])
                        if ev['is_mitigated']], key=lambda e: e['start_bar'])
        for i, ev in enumerate(swept):
            if i + max_swept < len(swept):
                ev['displaced_at'] = swept[i + max_swept]['start_bar']

    all_events = []
    for direction in ('bull', 'bear'):
        for ev in raw_events[direction]:
            e = {'dir': direction, 's': ev['start_bar'], 'e': ev['end_bar'],
                 'p': ev['price'], 'm': ev['is_mitigated'], 'vf': ev['visible_from']}
            if 'displaced_at' in ev:
                e['da'] = ev['displaced_at']
            all_events.append(e)

    return {
        'events':  all_events,
        'max_mit': max_swept if max_swept is not None else -1,
        'clr':     colors['orange_liquidity'],
        'ext':     extend_lines,
    }


# ---------------------------------------------------------------------------
# OB aVWAP extraction  (Track 2 — historical recomputation per bar)
# ---------------------------------------------------------------------------

def _extract_ob_avwap_events(raw_df, ind_conf, timeframe, colors):
    """Extract OB aVWAP anchor events + precomputed VWAP paths for Track 2 HTML replay.

    At each bar n the JS re-evaluates unmitigated vs mitigated status and applies
    max_unmit/max_mit caps in-time, fixing the lookahead bug where max_unmitigated=1
    would only reveal the final surviving anchor instead of the current one.
    Returns a list of config dicts (one per OB_params entry).
    """
    try:
        from src.indicators.indicators import load_indicator_config
        result = load_indicator_config(ind_conf, timeframe)
        if not result:
            return None
        ind_list, params = result
        if 'aVWAP' not in ind_list:
            return None
        avwap_params = params.get('aVWAP', {})
        if not avwap_params.get('OB', False):
            return None
        ob_configs = avwap_params.get('OB_params', [])
        if isinstance(ob_configs, dict):
            ob_configs = [ob_configs]
        if not ob_configs:
            return None
    except Exception as e:
        print(f"  Warning: could not load OB aVWAP params: {e}")
        return None

    from smartmoneyconcepts import smc as _smc
    from src.visualization.src.replay.vwap import build_cumulative_arrays

    col_lower = {c.lower(): c for c in raw_df.columns}
    needed = ['open', 'high', 'low', 'close', 'volume']
    if not all(k in col_lower for k in needed):
        return None

    ohlcv = raw_df[[col_lower[k] for k in needed]].copy()
    ohlcv.columns = needed
    n_bars = len(raw_df)
    cum_tpv, cum_vol = build_cumulative_arrays(raw_df)

    configs_out = []

    for config in ob_configs:
        periods         = config.get('periods', 25)
        max_unmitigated = config.get('max_unmitigated_aVWAPs', None)
        max_mitigated   = config.get('max_mitigated_aVWAPs', None)
        faded           = config.get('faded', False)
        extend_to_end   = config.get('extend_to_end', False)
        show_ghost      = faded and extend_to_end
        mode            = config.get('mode', 'combined').lower()

        if mode in ('bullish', 'valleys', 'bull', 'valley'):
            include_bull, include_bear = True, False
        elif mode in ('bearish', 'peaks', 'bear', 'peak'):
            include_bull, include_bear = False, True
        elif mode in ('none', 'off', 'false'):
            continue
        else:
            include_bull, include_bear = True, True

        try:
            swing_hl  = _smc.swing_highs_lows(ohlcv, swing_length=periods)
            ob_result = _smc.ob(ohlcv, swing_hl, close_mitigation=False)
        except Exception:
            continue

        n_res   = len(ob_result)
        ob_col  = ob_result['OB'].values             if 'OB'             in ob_result.columns else None
        mit_col = ob_result['MitigatedIndex'].values if 'MitigatedIndex' in ob_result.columns else None

        if ob_col is None:
            continue

        hl_vals    = swing_hl['HighLow'].values if 'HighLow' in swing_hl.columns else None
        sh_indices = np.where(hl_vals == 1)[0]  if hl_vals is not None else np.array([], dtype=int)
        sl_indices = np.where(hl_vals == -1)[0] if hl_vals is not None else np.array([], dtype=int)
        high_arr   = ohlcv['high'].values
        low_arr    = ohlcv['low'].values
        close_arr  = ohlcv['close'].values

        events = []
        for i in range(min(n_bars, n_res)):
            v = ob_col[i]
            if v == 0 or pd.isna(v):
                continue
            direction = 'bull' if v > 0 else 'bear'
            if (direction == 'bull' and not include_bull) or \
               (direction == 'bear' and not include_bear):
                continue

            mi  = mit_col[i] if mit_col is not None else None
            end = int(mi) if mi is not None and not pd.isna(mi) and mi > 0 else n_bars - 1
            end = min(end, n_bars - 1)
            is_mitigated = end < n_bars - 1

            # visible_from: same formula as _extract_ob_events
            is_bull      = (direction == 'bull')
            ref_indices  = sh_indices if is_bull else sl_indices
            level_arr    = high_arr   if is_bull else low_arr
            visible_from = i

            if hl_vals is not None:
                pos = int(np.searchsorted(ref_indices, i, side='left')) - 1
                if pos >= 0:
                    sh_bar   = int(ref_indices[pos])
                    sh_level = float(level_arr[sh_bar])
                    close_idx = n_bars - 1
                    for j in range(sh_bar + 1, n_bars):
                        if (is_bull  and close_arr[j] > sh_level) or \
                           (not is_bull and close_arr[j] < sh_level):
                            close_idx = j
                            break
                    visible_from = max(close_idx, sh_bar + periods)

            # Precompute VWAP path from anchor bar to end of data
            ab       = i
            base_tpv = cum_tpv[ab - 1] if ab > 0 else 0.0
            base_vol = cum_vol[ab - 1] if ab > 0 else 0.0
            seg_tpv  = cum_tpv[ab:] - base_tpv
            seg_vol  = cum_vol[ab:] - base_vol
            with np.errstate(divide='ignore', invalid='ignore'):
                path = np.where(seg_vol > 0, seg_tpv / seg_vol, np.nan)
            vals = [None if (isinstance(val, float) and val != val) else float(val) for val in path]

            clr  = colors['teal_OB'] if direction == 'bull' else colors['red_OB']
            gclr = colors.get('teal_OB_ghost' if direction == 'bull' else 'red_OB_ghost', clr)

            events.append({
                's':    ab,
                'e':    end,
                'm':    is_mitigated,
                'vf':   visible_from,
                'dir':  direction,
                'vals': vals,
                'clr':  clr,
                'gclr': gclr,
            })

        if events:
            configs_out.append({
                'events':     events,
                'max_unmit':  max_unmitigated,
                'max_mit':    max_mitigated,
                'show_ghost': show_ghost,
            })

    return configs_out if configs_out else None


# ---------------------------------------------------------------------------
# BoS/CHoCH aVWAP extraction  (Track 2 — historical recomputation per bar)
# ---------------------------------------------------------------------------

def _extract_bos_choch_avwap_events(raw_df, ind_conf, timeframe, colors):
    """Extract BoS/CHoCH aVWAP anchor events + precomputed VWAP paths for Track 2 HTML replay.

    visible_from = break_bar: the anchor can't be confirmed until the break bar,
    so the aVWAP only appears in replay once the break is confirmed.
    max_aVWAPs cap is re-evaluated in-time at each bar (per side if per_side=True).
    Returns a list of config dicts (one per BoS_CHoCH_params entry).
    """
    try:
        from src.indicators.indicators import load_indicator_config
        result = load_indicator_config(ind_conf, timeframe)
        if not result:
            return None
        ind_list, params = result
        if 'aVWAP' not in ind_list:
            return None
        avwap_params = params.get('aVWAP', {})
        if not avwap_params.get('BoS_CHoCH', False):
            return None
        bos_configs = avwap_params.get('BoS_CHoCH_params', [])
        if isinstance(bos_configs, dict):
            bos_configs = [bos_configs]
        if not bos_configs:
            return None
    except Exception as e:
        print(f"  Warning: could not load BoS/CHoCH aVWAP params: {e}")
        return None

    from src.visualization.src.replay.vwap import build_cumulative_arrays

    col_lower = {c.lower(): c for c in raw_df.columns}
    low_col  = col_lower.get('low',  None)
    high_col = col_lower.get('high', None)
    if low_col is None or high_col is None:
        return None

    low_vals  = raw_df[low_col].values
    high_vals = raw_df[high_col].values
    n_bars    = len(raw_df)
    cum_tpv, cum_vol = build_cumulative_arrays(raw_df)

    # Colors: BoS = stronger signal (0.75 opacity), CHoCH = weaker (0.5 opacity)
    _clr = {
        ('BoS',   'bull'): colors['teal_trans_3'],
        ('BoS',   'bear'): colors['red_trans_3'],
        ('CHoCH', 'bull'): colors['teal_trans_2'],
        ('CHoCH', 'bear'): colors['red_trans_2'],
    }

    configs_out = []

    for config in bos_configs:
        _sl           = config.get('swing_length', 15)
        bos_sl        = config.get('BoS_swing_length',   _sl)
        choch_sl      = config.get('CHoCH_swing_length', _sl)
        mode          = config.get('mode', 'combined').lower()
        include_BoS   = config.get('include_BoS',   True)
        include_CHoCH = config.get('include_CHoCH', True)
        # Per-side caps for each signal type (fall back to combined max_aVWAPs)
        _fallback     = config.get('max_aVWAPs', None)
        max_bos_cap   = config.get('max_BoS_aVWAPs',   _fallback)
        max_choch_cap = config.get('max_CHoCH_aVWAPs', _fallback)

        if mode in ('bullish', 'bull', 'valleys', 'valley'):
            include_bull, include_bear = True, False
        elif mode in ('bearish', 'bear', 'peaks', 'peak'):
            include_bull, include_bear = False, True
        elif mode in ('none', 'off', 'false'):
            continue
        else:
            include_bull, include_bear = True, True

        bos_col         = f'BoS_{bos_sl}'
        choch_col       = f'CHoCH_{choch_sl}'
        break_bos_col   = f'BoS_CHoCH_Break_Index_{bos_sl}'
        break_choch_col = f'BoS_CHoCH_Break_Index_{choch_sl}'

        has_bos   = bos_col   in raw_df.columns and break_bos_col   in raw_df.columns
        has_choch = choch_col in raw_df.columns and break_choch_col in raw_df.columns
        if not has_bos and not has_choch:
            continue

        bos_vals        = raw_df[bos_col].values        if has_bos   else None
        break_bos_vals  = raw_df[break_bos_col].values  if has_bos   else None
        choch_vals      = raw_df[choch_col].values       if has_choch else None
        break_choch_vals = raw_df[break_choch_col].values if has_choch else None

        events = []

        # Process each signal type independently
        signal_specs = []
        if include_BoS and has_bos:
            if include_bull: signal_specs.append(('BoS', 'bull',  1))
            if include_bear: signal_specs.append(('BoS', 'bear', -1))
        if include_CHoCH and has_choch:
            if include_bull: signal_specs.append(('CHoCH', 'bull',  1))
            if include_bear: signal_specs.append(('CHoCH', 'bear', -1))

        for sig_type, direction, sig_val in signal_specs:
            if sig_type == 'BoS':
                src_vals   = bos_vals
                break_vals = break_bos_vals
            else:
                src_vals   = choch_vals
                break_vals = break_choch_vals
            for i in range(n_bars):
                v = src_vals[i]
                if v != sig_val:
                    continue
                bi = break_vals[i]
                if isinstance(bi, float) and bi != bi:
                    continue
                break_bar = int(bi)
                if break_bar <= i or break_bar >= n_bars:
                    continue

                if direction == 'bull':
                    anchor_bar = int(np.argmin(low_vals[i:break_bar + 1])) + i
                else:
                    anchor_bar = int(np.argmax(high_vals[i:break_bar + 1])) + i

                ab       = anchor_bar
                base_tpv = cum_tpv[ab - 1] if ab > 0 else 0.0
                base_vol = cum_vol[ab - 1] if ab > 0 else 0.0
                seg_tpv  = cum_tpv[ab:] - base_tpv
                seg_vol  = cum_vol[ab:] - base_vol
                with np.errstate(divide='ignore', invalid='ignore'):
                    path = np.where(seg_vol > 0, seg_tpv / seg_vol, np.nan)
                vals = [None if (isinstance(v2, float) and v2 != v2) else float(v2) for v2 in path]

                events.append({
                    's':   i,
                    'ab':  ab,
                    'vf':  break_bar,
                    'dir': direction,
                    'st':  sig_type,    # 'BoS' or 'CHoCH'
                    'vals': vals,
                    'clr': _clr[(sig_type, direction)],
                })

        if events:
            configs_out.append({
                'events':    events,
                'max_bos':   max_bos_cap,
                'max_choch': max_choch_cap,
            })

    return configs_out if configs_out else None


# ---------------------------------------------------------------------------
# Peaks/valleys aVWAP extraction  (Track 2 — historical recomputation per bar)
# ---------------------------------------------------------------------------

def _extract_peaks_valleys_avwap_events(raw_df, ind_conf, timeframe, colors):
    """Extract peaks/valleys aVWAP anchor events + precomputed VWAP paths for Track 2 HTML replay.

    Peak/valley detection mirrors the peaks_valleys indicator: rolling(periods, center=True).
    visible_from = anchor_bar + periods // 2  (forward lookahead of the centered window).
    max_aVWAPs cap is re-evaluated in-time per direction (peaks vs valleys) at each bar.
    Returns a list of config dicts.
    """
    try:
        from src.indicators.indicators import load_indicator_config
        result = load_indicator_config(ind_conf, timeframe)
        if not result:
            return None
        ind_list, params = result
        if 'aVWAP' not in ind_list:
            return None
        avwap_params = params.get('aVWAP', {})
    except Exception as e:
        print(f"  Warning: could not load peaks/valleys aVWAP params: {e}")
        return None

    show_peaks   = avwap_params.get('peaks',         False)
    show_valleys = avwap_params.get('valleys',        False)
    show_pv      = avwap_params.get('peaks_valleys',  False)

    peaks_cfgs   = avwap_params.get('peaks_params',         [])
    valleys_cfgs = avwap_params.get('valleys_params',       [])
    pv_cfgs      = avwap_params.get('peaks_valleys_params', [])

    if isinstance(peaks_cfgs,   dict): peaks_cfgs   = [peaks_cfgs]
    if isinstance(valleys_cfgs, dict): valleys_cfgs = [valleys_cfgs]
    if isinstance(pv_cfgs,      dict): pv_cfgs      = [pv_cfgs]

    # Build list of (direction, periods, max_aVWAPs) to process
    groups = []
    if show_peaks:
        for cfg in peaks_cfgs:
            groups.append(('peak',   cfg.get('periods', 25), cfg.get('max_aVWAPs', None)))
    if show_valleys:
        for cfg in valleys_cfgs:
            groups.append(('valley', cfg.get('periods', 25), cfg.get('max_aVWAPs', None)))
    if show_pv:
        for cfg in pv_cfgs:
            groups.append(('both',   cfg.get('periods', 25), cfg.get('max_aVWAPs', None)))

    if not groups:
        return None

    from src.visualization.src.replay.vwap import build_cumulative_arrays

    col_lower = {c.lower(): c for c in raw_df.columns}
    high_col  = col_lower.get('high', None)
    low_col   = col_lower.get('low',  None)
    if high_col is None or low_col is None:
        return None

    high_arr = raw_df[high_col].values.astype(float)
    low_arr  = raw_df[low_col].values.astype(float)
    n_bars   = len(raw_df)
    cum_tpv, cum_vol = build_cumulative_arrays(raw_df)

    peak_clr   = colors['red_trans_3']
    valley_clr = colors['teal_trans_3']

    # Cache peak/valley detection per periods to avoid recomputation across configs
    _cache = {}

    def _detect(periods):
        if periods in _cache:
            return _cache[periods]
        high_s   = pd.Series(high_arr)
        low_s    = pd.Series(low_arr)
        roll_max = high_s.rolling(periods, center=True, min_periods=1).max()
        roll_min = low_s.rolling(periods, center=True, min_periods=1).min()
        peaks    = list(high_s[high_s == roll_max].index)
        valleys  = list(low_s[low_s == roll_min].index)
        _cache[periods] = (peaks, valleys)
        return peaks, valleys

    def _vwap_vals(ab):
        base_tpv = cum_tpv[ab - 1] if ab > 0 else 0.0
        base_vol = cum_vol[ab - 1] if ab > 0 else 0.0
        seg_tpv  = cum_tpv[ab:] - base_tpv
        seg_vol  = cum_vol[ab:] - base_vol
        with np.errstate(divide='ignore', invalid='ignore'):
            path = np.where(seg_vol > 0, seg_tpv / seg_vol, np.nan)
        return [None if (isinstance(v, float) and v != v) else float(v) for v in path]

    configs_out = []

    for direction, periods, max_cap in groups:
        peak_bars, valley_bars = _detect(periods)
        half = periods // 2
        events = []

        if direction in ('peak', 'both'):
            for ab in peak_bars:
                vf = min(ab + half, n_bars - 1)
                events.append({
                    's':   ab,
                    'vf':  vf,
                    'dir': 'peak',
                    'vals': _vwap_vals(ab),
                    'clr': peak_clr,
                })

        if direction in ('valley', 'both'):
            for ab in valley_bars:
                vf = min(ab + half, n_bars - 1)
                events.append({
                    's':   ab,
                    'vf':  vf,
                    'dir': 'valley',
                    'vals': _vwap_vals(ab),
                    'clr': valley_clr,
                })

        if events:
            configs_out.append({
                'events':  events,
                'max_cap': max_cap,
            })

    return configs_out if configs_out else None


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

def _lw_js() -> str:
    import lightweight_charts
    path = Path(lightweight_charts.__file__).parent / 'js' / 'lightweight-charts.js'
    return path.read_text(encoding='utf-8')


_LW_LINE_STYLES = {
    'solid': 0, 'dotted': 1, 'dashed': 2, 'large_dashed': 3, 'sparse_dotted': 4,
}


def build_html(prepared_df, col_styles, ticker, timeframe, ind_conf,
               ob_data=None, qqemod_data=None, fvg_data=None,
               bos_data=None, liq_data=None, pmm_data=None,
               ob_avwap_data=None, bos_choch_avwap_data=None,
               pv_avwap_data=None, colors=None):
    bars = _build_data(prepared_df, col_styles)
    n_bars = len(bars)

    lines_meta = {
        col: {
            'color': s['color'],
            'width': s['width'],
            'lineStyle': _LW_LINE_STYLES.get(s['style'], 0),
        }
        for col, s in col_styles.items()
    }

    payload = {'bars': bars, 'lines': lines_meta}
    if ob_data       is not None: payload['ob']      = ob_data
    if qqemod_data   is not None: payload['qq']      = qqemod_data
    if fvg_data      is not None: payload['fvg']     = fvg_data
    if bos_data      is not None: payload['bos']     = bos_data
    if liq_data      is not None: payload['liq']     = liq_data
    if pmm_data      is not None: payload['pmm']     = pmm_data
    if ob_avwap_data       is not None: payload['ob_avwap']        = ob_avwap_data
    if bos_choch_avwap_data is not None: payload['bos_choch_avwap'] = bos_choch_avwap_data
    if pv_avwap_data        is not None: payload['pv_avwap']        = pv_avwap_data

    data_json = json.dumps(payload, separators=(',', ':'))
    lw_js = _lw_js()
    title = f"{ticker} {timeframe} replay"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #000000; color: #cccccc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; user-select: none; }}
  #chart {{ width: 100vw; height: calc(100vh - 52px); }}
  #controls {{
    height: 52px; display: flex; align-items: center; gap: 10px;
    padding: 0 14px; background: #000000; border-top: 1px solid #222222;
  }}
  button {{
    background: #111111; color: #cccccc; border: 1px solid #333333;
    padding: 5px 11px; cursor: pointer; border-radius: 3px; font-size: 13px;
  }}
  button:hover {{ background: #222222; }}
  button.active {{ background: #2962ff; border-color: #2962ff; color: #fff; }}
  #slider {{ flex: 1; min-width: 0; accent-color: #2962ff; cursor: pointer; }}
  .sep {{ width: 1px; height: 24px; background: #222222; }}
  label {{ font-size: 12px; color: #666666; display: flex; align-items: center; gap: 5px; white-space: nowrap; }}
  input[type=number] {{
    width: 46px; background: #111111; color: #cccccc; border: 1px solid #333333;
    padding: 4px 6px; border-radius: 3px; font-size: 12px; text-align: center;
  }}
  input[type=number]::-webkit-inner-spin-button {{ opacity: 1; }}
  #date-input {{
    width: 95px; background: #111111; color: #cccccc; border: 1px solid #333333;
    padding: 4px 6px; border-radius: 3px; font-size: 12px;
  }}
  #date-input:focus {{ outline: none; border-color: #555555; }}
</style>
</head>
<body>
<div id="chart"></div>
<div id="controls">
  <button id="btn-start" title="First bar">&#x23EE;</button>
  <button id="btn-prev"  title="Step back (Arrow Left)">&#x25C0;</button>
  <button id="btn-play"  title="Play / pause (Space)">&#x25B6;</button>
  <button id="btn-next"  title="Step forward (Arrow Right)">&#x25B6;&#x25B6;</button>
  <button id="btn-end"   title="Last bar">&#x23ED;</button>
  <div class="sep"></div>
  <input type="range" id="slider" min="0" max="{n_bars - 1}" value="0">
  <label>bar <input type="text" id="bar-jump-input" placeholder="#" autocomplete="off" style="width:46px;text-align:center"> / {n_bars - 1}</label>
  <div class="sep"></div>
  <label>date <input type="text" id="date-input" placeholder="YYYY-MM-DD" autocomplete="off" spellcheck="false"></label>
  <div class="sep"></div>
  <label>fps <input type="number" id="fps-input" value="8" min="1" max="60"></label>
</div>

<script>
/* lightweight-charts v4 */
{lw_js}
</script>

<script>
(function() {{
  'use strict';

  const DATA = {data_json};
  const N = DATA.bars.length;
  // Zone array: prefer QQEMOD-derived (always accurate), fall back to CSV column, else null.
  const QQ_ZONE    = (DATA.qq && DATA.qq.zone) ? DATA.qq.zone : null;
  const HAS_VOLUME = DATA.bars.length > 0 && 'v' in DATA.bars[0];

  // App colour palette (matches src/visualization/src/color_palette.py)
  const C_TEAL = 'rgba(38,166,154,1.0)';
  const C_RED  = 'rgba(239,83,80,1.0)';
  const C_VOL  = 'rgba(255,165,0,0.5)';

  // --- chart setup ---
  const container = document.getElementById('chart');
  const chart = LightweightCharts.createChart(container, {{
    width:  container.clientWidth,
    height: container.clientHeight,
    layout: {{ background: {{ color: '#000000' }}, textColor: '#cccccc' }},
    grid:   {{ vertLines: {{ color: '#0d0d0d' }}, horzLines: {{ color: '#0d0d0d' }} }},
    crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
    rightPriceScale: {{ borderColor: '#1a1a1a' }},
    timeScale: {{ borderColor: '#1a1a1a', timeVisible: true, secondsVisible: false }},
  }});

  const candleSeries = chart.addCandlestickSeries({{
    upColor: C_TEAL, downColor: C_RED,
    borderUpColor: C_TEAL, borderDownColor: C_RED,
    wickUpColor: C_TEAL, wickDownColor: C_RED,
  }});

  // Volume histogram (drawn behind everything else)
  let volumeSeries = null;
  if (HAS_VOLUME) {{
    volumeSeries = chart.addHistogramSeries({{
      color: C_VOL,
      priceFormat: {{ type: 'volume' }},
      priceScaleId: 'vol',
    }});
    chart.priceScale('vol').applyOptions({{
      scaleMargins: {{ top: 0.85, bottom: 0.0 }},
    }});
  }}

  // Track 1: progressive-reveal indicator lines
  const lineSeries = {{}};
  for (const [col, meta] of Object.entries(DATA.lines)) {{
    lineSeries[col] = chart.addLineSeries({{
      color: meta.color, lineWidth: meta.width, lineStyle: meta.lineStyle,
      priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
    }});
  }}

  // Track 4: OB segment lines  (one thick line per event)
  const obSeries = [];
  const obKey    = [];
  if (DATA.ob) {{
    for (const ev of DATA.ob.events) {{
      const color = ev.dir === 'bull' ? DATA.ob.bull_clr : DATA.ob.bear_clr;
      obSeries.push(chart.addLineSeries({{
        color, lineWidth: 8, lineStyle: 0,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      }}));
      obKey.push(null);
    }}
  }}

  // Track 4: FVG segment lines (dashed, outer edge)
  const fvgSeries = [];
  const fvgKey    = [];
  if (DATA.fvg) {{
    const ls = DATA.fvg.ls !== undefined ? DATA.fvg.ls : 2;
    for (const ev of DATA.fvg.events) {{
      const color = ev.dir === 'bull' ? DATA.fvg.bull_clr : DATA.fvg.bear_clr;
      fvgSeries.push(chart.addLineSeries({{
        color, lineWidth: 1, lineStyle: ls,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      }}));
      fvgKey.push(null);
    }}
  }}

  // Track 4: BoS/CHoCH segment lines (solid, per-event color)
  const bosSeries = [];
  const bosKey    = [];
  if (DATA.bos) {{
    for (const ev of DATA.bos.events) {{
      bosSeries.push(chart.addLineSeries({{
        color: ev.clr, lineWidth: 1, lineStyle: 0,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      }}));
      bosKey.push(null);
    }}
  }}

  // Track 4: Liquidity segment lines
  const liqSeries = [];
  const liqKey    = [];
  if (DATA.liq) {{
    for (const ev of DATA.liq.events) {{
      liqSeries.push(chart.addLineSeries({{
        color: DATA.liq.clr, lineWidth: 1, lineStyle: 0,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      }}));
      liqKey.push(null);
    }}
  }}

  // Track 2: PMM aVWAP — slot-based (one series per direction×slot)
  const pmmSeries = {{}};
  const pmmKey    = {{}};
  if (DATA.pmm) {{
    for (const dir of ['valley', 'peak']) {{
      const side = DATA.pmm[dir];
      if (!side) continue;
      const color = (dir === 'valley') ? C_TEAL : C_RED;
      pmmSeries[dir] = [];
      pmmKey[dir]    = [];
      for (let i = 0; i < side.slots.length; i++) {{
        pmmSeries[dir].push(chart.addLineSeries({{
          color, lineWidth: 2, lineStyle: 0,
          priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
        }}));
        pmmKey[dir].push(-1);
      }}
    }}
  }}

  // Track 2: QQEMOD aVWAP anchor lines
  const qqSeries = [];
  const qqKey    = [];
  let liveBearSeries = null;
  let liveBullSeries = null;
  const qqPathMap = new Map();   // anchor_bar → values[]
  if (DATA.qq) {{
    for (const ev of DATA.qq.anchors) {{
      qqSeries.push(chart.addLineSeries({{
        color: ev.clr, lineWidth: ev.w, lineStyle: ev.ls,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      }}));
      qqKey.push(null);
      qqPathMap.set(ev.ab, ev.vals);
    }}
    if (DATA.qq.live_bear_clr) {{
      liveBearSeries = chart.addLineSeries({{
        color: DATA.qq.live_bear_clr, lineWidth: 2, lineStyle: 0,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      }});
    }}
    if (DATA.qq.live_bull_clr) {{
      liveBullSeries = chart.addLineSeries({{
        color: DATA.qq.live_bull_clr, lineWidth: 2, lineStyle: 0,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
      }});
    }}
    if (DATA.qq.live_paths) {{
      for (const [k, v] of Object.entries(DATA.qq.live_paths)) {{
        qqPathMap.set(parseInt(k), v);
      }}
    }}
  }}

  // Track 2: OB aVWAP — per-config, one solid + one optional ghost series per event
  const obAvwapSeries = [];
  const obAvwapGhost  = [];
  if (DATA.ob_avwap) {{
    for (const cfg of DATA.ob_avwap) {{
      for (const ev of cfg.events) {{
        obAvwapSeries.push(chart.addLineSeries({{
          color: ev.clr, lineWidth: 2, lineStyle: 0,
          priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
        }}));
        if (cfg.show_ghost) {{
          obAvwapGhost.push(chart.addLineSeries({{
            color: ev.gclr, lineWidth: 1, lineStyle: 1,
            priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
          }}));
        }} else {{
          obAvwapGhost.push(null);
        }}
      }}
    }}
  }}

  // Track 2: BoS/CHoCH aVWAP — per-config, one series per event
  const bosChochAvwapSeries = [];
  if (DATA.bos_choch_avwap) {{
    for (const cfg of DATA.bos_choch_avwap) {{
      for (const ev of cfg.events) {{
        bosChochAvwapSeries.push(chart.addLineSeries({{
          color: ev.clr, lineWidth: 2, lineStyle: 0,
          priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
        }}));
      }}
    }}
  }}

  // Track 2: Peaks/valleys aVWAP — per-config, one series per event
  const pvAvwapSeries = [];
  if (DATA.pv_avwap) {{
    for (const cfg of DATA.pv_avwap) {{
      for (const ev of cfg.events) {{
        pvAvwapSeries.push(chart.addLineSeries({{
          color: ev.clr, lineWidth: 2, lineStyle: 0,
          priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
        }}));
      }}
    }}
  }}

  // --- shared segment renderer (OB / FVG / Liquidity) ---
  // key -2 = not yet visible,  -1 = hidden (displaced/mitigated),  >=0 = active endBar
  function _renderSegs(segData, series, keys, n) {{
    if (!segData) return;
    const ext = segData.ext === true;
    for (let i = 0; i < segData.events.length; i++) {{
      const ev      = segData.events[i];
      const visFrom = ev.vf !== undefined ? ev.vf : ev.s;
      let key;
      if (n < visFrom) {{
        key = -2;
      }} else if (ev.da !== undefined && n >= ev.da) {{
        key = -1;
      }} else if (segData.max_mit === 0 && ev.m && ev.e < n) {{
        key = -1;
      }} else {{
        const endBar = ext ? n : Math.min(ev.e, n);
        key = (endBar > ev.s) ? endBar : -2;  // guard: need 2 distinct timestamps
      }}
      if (key === keys[i]) continue;
      keys[i] = key;
      if (key < 0) {{
        series[i].setData([]);
      }} else {{
        series[i].setData([
          {{ time: DATA.bars[ev.s].time, value: ev.p }},
          {{ time: DATA.bars[key].time,  value: ev.p }},
        ]);
      }}
    }}
  }}

  // BoS/CHoCH: no visibility delay, no mitigation hide, simple start/end
  function _renderBosCh(segData, series, keys, n) {{
    if (!segData) return;
    for (let i = 0; i < segData.events.length; i++) {{
      const ev  = segData.events[i];
      const key = ev.s < n ? Math.min(ev.e, n) : -1;  // guard: need 2 distinct timestamps
      if (key === keys[i]) continue;
      keys[i] = key;
      if (key < 0) {{
        series[i].setData([]);
      }} else {{
        series[i].setData([
          {{ time: DATA.bars[ev.s].time, value: ev.p }},
          {{ time: DATA.bars[key].time,  value: ev.p }},
        ]);
      }}
    }}
  }}

  // PMM: slot-based aVWAP with evolving greedy anchor selection
  function _renderPmm(n) {{
    if (!DATA.pmm) return;
    for (const dir of ['valley', 'peak']) {{
      const side = DATA.pmm[dir];
      if (!side || !pmmSeries[dir]) continue;
      for (let i = 0; i < pmmSeries[dir].length; i++) {{
        const ab  = side.slots[i][n];
        const ser = pmmSeries[dir][i];
        if (ab < 0) {{
          if (pmmKey[dir][i] !== -1) {{ ser.setData([]); pmmKey[dir][i] = -1; }}
          continue;
        }}
        // Always update when active: path grows 1 bar per step
        pmmKey[dir][i] = n;
        const vals = DATA.pmm.paths[ab];
        if (!vals) {{ ser.setData([]); continue; }}
        const pts  = [];
        const endK = Math.min(n - ab, vals.length - 1);
        for (let k = 0; k <= endK; k++) {{
          const v = vals[k];
          if (v !== null) pts.push({{ time: DATA.bars[ab + k].time, value: v }});
        }}
        ser.setData(pts);
      }}
    }}
  }}

  // Build VWAP path pts up to bar n for a given anchor bar
  function _vwapPts(ab, n) {{
    const vals = qqPathMap.get(ab);
    if (!vals) return [];
    const endIdx = Math.min(n - ab + 1, vals.length);
    const pts = [];
    for (let k = 0; k < endIdx; k++) {{
      const v = vals[k];
      if (v !== null) pts.push({{ time: DATA.bars[ab + k].time, value: v }});
    }}
    return pts;
  }}

  // Build OB aVWAP path pts up to bar n for a given event
  function _obVwapPts(ev, upTo) {{
    const vals = ev.vals;
    if (!vals) return [];
    const endIdx = Math.min(upTo - ev.s + 1, vals.length);
    const pts = [];
    for (let k = 0; k < endIdx; k++) {{
      const v = vals[k];
      if (v !== null) pts.push({{ time: DATA.bars[ev.s + k].time, value: v }});
    }}
    return pts;
  }}

  // OB aVWAP Track 2: re-evaluate caps in-time at each bar
  function _renderObAvwap(n) {{
    if (!DATA.ob_avwap) return;
    let serIdx = 0;
    for (const cfg of DATA.ob_avwap) {{
      const events   = cfg.events;
      const maxUnmit = cfg.max_unmit;
      const maxMit   = cfg.max_mit;

      // Classify events visible at bar n into unmitigated vs mitigated per side
      const unmitBull = [], unmitBear = [], mitBull = [], mitBear = [];
      for (let i = 0; i < events.length; i++) {{
        const ev = events[i];
        if (ev.vf > n) continue;
        if (ev.m && ev.e <= n) {{
          (ev.dir === 'bull' ? mitBull : mitBear).push(i);
        }} else {{
          (ev.dir === 'bull' ? unmitBull : unmitBear).push(i);
        }}
      }}

      // Sort descending by start bar (most recent first) then apply per-side caps
      const byS = (a, b) => events[b].s - events[a].s;
      unmitBull.sort(byS); unmitBear.sort(byS);
      mitBull.sort(byS);   mitBear.sort(byS);

      const capU = (maxUnmit !== null && maxUnmit !== undefined) ? maxUnmit : Infinity;
      const capM = (maxMit   !== null && maxMit   !== undefined) ? maxMit   : Infinity;

      const activeUnmit = new Set([...unmitBull.slice(0, capU), ...unmitBear.slice(0, capU)]);
      const activeMit   = new Set([...mitBull.slice(0, capM),   ...mitBear.slice(0, capM)]);

      for (let i = 0; i < events.length; i++) {{
        const ser  = obAvwapSeries[serIdx + i];
        const gser = obAvwapGhost[serIdx + i];
        const ev   = events[i];

        if (activeUnmit.has(i)) {{
          ser.setData(_obVwapPts(ev, n));
          if (gser) gser.setData([]);
        }} else if (activeMit.has(i)) {{
          ser.setData(_obVwapPts(ev, ev.e));   // solid stops at mitigation bar
          if (gser) {{                          // ghost extends from mitigation to n
            const vals = ev.vals;
            const gPts = [];
            const gStart = ev.e - ev.s;
            const gEnd   = Math.min(n - ev.s + 1, vals.length);
            for (let k = gStart; k < gEnd; k++) {{
              const v = vals[k];
              if (v !== null) gPts.push({{ time: DATA.bars[ev.s + k].time, value: v }});
            }}
            gser.setData(gPts);
          }}
        }} else {{
          ser.setData([]);
          if (gser) gser.setData([]);
        }}
      }}
      serIdx += events.length;
    }}
  }}

  // Build peaks/valleys aVWAP path pts up to bar n (vals array starts at anchor bar ev.s)
  function _pvVwapPts(ev, n) {{
    const vals = ev.vals;
    if (!vals) return [];
    const endIdx = Math.min(n - ev.s + 1, vals.length);
    const pts = [];
    for (let k = 0; k < endIdx; k++) {{
      const v = vals[k];
      if (v !== null) pts.push({{ time: DATA.bars[ev.s + k].time, value: v }});
    }}
    return pts;
  }}

  // Peaks/valleys aVWAP Track 2: re-evaluate caps in-time at each bar
  function _renderPvAvwap(n) {{
    if (!DATA.pv_avwap) return;
    let serIdx = 0;
    for (const cfg of DATA.pv_avwap) {{
      const events = cfg.events;
      const maxCap = cfg.max_cap;

      // Collect visible events (anchor confirmed by bar n), split by direction
      const visPeaks = [], visValleys = [];
      for (let i = 0; i < events.length; i++) {{
        const ev = events[i];
        if (ev.vf > n) continue;
        (ev.dir === 'peak' ? visPeaks : visValleys).push(i);
      }}

      // Sort descending by anchor bar (most recent first), apply per-direction cap
      const byS = (a, b) => events[b].s - events[a].s;
      visPeaks.sort(byS); visValleys.sort(byS);

      const cap = (maxCap !== null && maxCap !== undefined) ? maxCap : Infinity;
      const activeSet = new Set([...visPeaks.slice(0, cap), ...visValleys.slice(0, cap)]);

      for (let i = 0; i < events.length; i++) {{
        const ser = pvAvwapSeries[serIdx + i];
        if (activeSet.has(i)) {{
          ser.setData(_pvVwapPts(events[i], n));
        }} else {{
          ser.setData([]);
        }}
      }}
      serIdx += events.length;
    }}
  }}

  // Build BoS/CHoCH aVWAP path pts up to bar n (vals array starts at anchor bar ev.ab)
  function _bcVwapPts(ev, n) {{
    const vals = ev.vals;
    if (!vals) return [];
    const endIdx = Math.min(n - ev.ab + 1, vals.length);
    const pts = [];
    for (let k = 0; k < endIdx; k++) {{
      const v = vals[k];
      if (v !== null) pts.push({{ time: DATA.bars[ev.ab + k].time, value: v }});
    }}
    return pts;
  }}

  // BoS/CHoCH aVWAP Track 2: re-evaluate caps in-time at each bar
  function _renderBosChochAvwap(n) {{
    if (!DATA.bos_choch_avwap) return;
    let serIdx = 0;
    for (const cfg of DATA.bos_choch_avwap) {{
      const events   = cfg.events;
      const maxBos   = cfg.max_bos;
      const maxChoch = cfg.max_choch;

      // Collect events whose break bar has been reached, split by signal type × side
      const bosBull = [], bosBear = [], chochBull = [], chochBear = [];
      for (let i = 0; i < events.length; i++) {{
        const ev = events[i];
        if (ev.vf > n) continue;
        if (ev.st === 'BoS') {{
          (ev.dir === 'bull' ? bosBull : bosBear).push(i);
        }} else {{
          (ev.dir === 'bull' ? chochBull : chochBear).push(i);
        }}
      }}

      // Sort descending by signal bar (most recent first) then apply per-side caps
      const byS = (a, b) => events[b].s - events[a].s;
      bosBull.sort(byS); bosBear.sort(byS); chochBull.sort(byS); chochBear.sort(byS);

      const capB = (maxBos   !== null && maxBos   !== undefined) ? maxBos   : Infinity;
      const capC = (maxChoch !== null && maxChoch !== undefined) ? maxChoch : Infinity;

      const activeSet = new Set([
        ...bosBull.slice(0, capB),   ...bosBear.slice(0, capB),
        ...chochBull.slice(0, capC), ...chochBear.slice(0, capC),
      ]);

      for (let i = 0; i < events.length; i++) {{
        const ser = bosChochAvwapSeries[serIdx + i];
        if (activeSet.has(i)) {{
          ser.setData(_bcVwapPts(events[i], n));
        }} else {{
          ser.setData([]);
        }}
      }}
      serIdx += events.length;
    }}
  }}

  // --- render ---
  function render(n) {{
    const slice = DATA.bars.slice(0, n + 1);

    candleSeries.setData(slice.map((b, i) => {{
      // Priority: candle_colors column → QQEMOD zone → CSV zone flag → up/down
      let clr;
      if (b.c) {{
        clr = b.c;
      }} else if (QQ_ZONE) {{
        clr = (QQ_ZONE[i] === 1) ? C_TEAL : C_RED;
      }} else if ('z' in b) {{
        clr = b.z ? C_TEAL : C_RED;
      }} else {{
        clr = (b.close >= b.open) ? C_TEAL : C_RED;
      }}
      // Border/wick: always solid so transparent-fill candles remain readable.
      // Black (neutral) candles get a transparent body + teal/red outline like a hollow candle.
      // For any rgba fill we strip alpha to 1.0 to get the solid border version.
      let border, body;
      if (!clr || clr === '#000000') {{
        body   = 'rgba(0,0,0,0)';
        border = (b.close >= b.open) ? C_TEAL : C_RED;
      }} else {{
        body   = clr;
        border = clr.replace(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*[^)]+\)/, 'rgba($1,$2,$3,1.0)');
      }}
      return {{ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close,
               color: body, borderColor: border, wickColor: border }};
    }}));

    if (volumeSeries) {{
      volumeSeries.setData(slice
        .filter(b => b.v !== null && b.v !== undefined)
        .map(b => ({{ time: b.time, value: b.v, color: C_VOL }})));
    }}

    for (const [col, series] of Object.entries(lineSeries)) {{
      const pts = [];
      for (const b of slice) {{
        const v = b[col];
        if (v !== null && v !== undefined) pts.push({{ time: b.time, value: v }});
      }}
      series.setData(pts);
    }}

    // Segment indicators (OB, FVG, Liquidity share the same lazy-visibility logic)
    _renderSegs(DATA.ob,  obSeries,  obKey,  n);
    _renderSegs(DATA.fvg, fvgSeries, fvgKey, n);
    _renderSegs(DATA.liq, liqSeries, liqKey, n);
    _renderBosCh(DATA.bos, bosSeries, bosKey, n);

    // PMM aVWAPs (greedy extrema, evolving per bar)
    _renderPmm(n);

    // OB aVWAP (Track 2: in-time cap evaluation)
    _renderObAvwap(n);

    // BoS/CHoCH aVWAP (Track 2: in-time cap evaluation)
    _renderBosChochAvwap(n);

    // Peaks/valleys aVWAP (Track 2: in-time cap evaluation)
    _renderPvAvwap(n);

    // QQEMOD aVWAP committed anchors
    if (DATA.qq) {{
      for (let i = 0; i < DATA.qq.anchors.length; i++) {{
        const ev  = DATA.qq.anchors[i];
        const active = ev.add <= n && (ev.rem === null || n < ev.rem);
        const key = active ? n : -1;
        if (key === qqKey[i]) continue;
        qqKey[i] = key;
        if (!active) {{
          qqSeries[i].setData([]);
        }} else {{
          qqSeries[i].setData(_vwapPts(ev.ab, n));
        }}
      }}

      // Live floating bear anchor
      if (liveBearSeries && DATA.qq.live_bear) {{
        const ab = DATA.qq.live_bear[n];
        if (ab >= 0) {{
          liveBearSeries.setData(_vwapPts(ab, n));
        }} else {{
          liveBearSeries.setData([]);
        }}
      }}

      // Live floating bull anchor
      if (liveBullSeries && DATA.qq.live_bull) {{
        const ab = DATA.qq.live_bull[n];
        if (ab >= 0) {{
          liveBullSeries.setData(_vwapPts(ab, n));
        }} else {{
          liveBullSeries.setData([]);
        }}
      }}
    }}

    const _bt = DATA.bars[n].time;
    let _bd = '';
    if (typeof _bt === 'string') _bd = _bt.slice(0, 10);
    else if (typeof _bt === 'object' && _bt.year) _bd = _bt.year + '-' + String(_bt.month).padStart(2,'0') + '-' + String(_bt.day).padStart(2,'0');
    else if (typeof _bt === 'number') _bd = new Date(_bt * 1000).toISOString().slice(0, 10);
    document.getElementById('slider').value = n;
    const _barInp  = document.getElementById('bar-jump-input');
    const _dateInp = document.getElementById('date-input');
    if (document.activeElement !== _barInp)  _barInp.value  = n;
    if (document.activeElement !== _dateInp) _dateInp.value = _bd;
  }}

  // --- state ---
  let current = 0;
  let playing  = false;
  let rafId    = null;
  let lastTime = 0;

  function jump(n) {{
    current = Math.max(0, Math.min(N - 1, n));
    render(current);
  }}

  function tick(ts) {{
    if (!playing) return;
    const fps = Math.max(1, parseInt(document.getElementById('fps-input').value) || 8);
    const interval = 1000 / fps;
    if (ts - lastTime >= interval) {{
      lastTime = ts;
      if (current >= N - 1) {{ setPlaying(false); return; }}
      jump(current + 1);
    }}
    rafId = requestAnimationFrame(tick);
  }}

  function setPlaying(val) {{
    playing = val;
    document.getElementById('btn-play').classList.toggle('active', playing);
    document.getElementById('btn-play').innerHTML = playing ? '&#x23F8;' : '&#x25B6;';
    if (playing) {{ lastTime = 0; rafId = requestAnimationFrame(tick); }}
    else if (rafId) {{ cancelAnimationFrame(rafId); rafId = null; }}
  }}

  // Apply ?fps=N from URL (set by the browser index)
  (function() {{
    const _p = parseInt(new URLSearchParams(location.search).get('fps'));
    if (_p >= 1) document.getElementById('fps-input').value = _p;
  }})();

  // Double-click on chart → jump to that bar
  document.getElementById('chart').addEventListener('dblclick', function(e) {{
    const rect = this.getBoundingClientRect();
    const t = chart.timeScale().coordinateToTime(e.clientX - rect.left);
    if (t === null || t === undefined) return;
    let best = 0;
    for (let i = 0; i < N; i++) {{
      if (DATA.bars[i].time <= t) best = i;
      else break;
    }}
    setPlaying(false);
    jump(best);
  }});

  // --- controls ---
  document.getElementById('btn-start').onclick = () => jump(0);
  document.getElementById('btn-prev') .onclick = () => {{ setPlaying(false); jump(current - 1); }};
  document.getElementById('btn-play') .onclick = () => setPlaying(!playing);
  document.getElementById('btn-next') .onclick = () => {{ setPlaying(false); jump(current + 1); }};
  document.getElementById('btn-end')  .onclick = () => jump(N - 1);
  document.getElementById('slider')   .oninput = e  => {{ setPlaying(false); jump(parseInt(e.target.value)); }};

  document.addEventListener('keydown', e => {{
    if (e.target.tagName === 'INPUT') return;
    if (e.key === 'ArrowLeft')  {{ setPlaying(false); jump(current - (e.shiftKey ? 20 : 1)); }}
    if (e.key === 'ArrowRight') {{ setPlaying(false); jump(current + (e.shiftKey ? 20 : 1)); }}
    if (e.key === 'ArrowUp')   {{ e.preventDefault(); const fi = document.getElementById('fps-input'); fi.value = Math.min(60, (parseInt(fi.value) || 8) + 1); }}
    if (e.key === 'ArrowDown') {{ e.preventDefault(); const fi = document.getElementById('fps-input'); fi.value = Math.max(1,  (parseInt(fi.value) || 8) - 1); }}
    if (e.key === ' ')          {{ e.preventDefault(); setPlaying(!playing); }}
    if (e.key === 'Home')       jump(0);
    if (e.key === 'End')        jump(N - 1);
    // Forward cycling keys to parent browser (postMessage works across iframe boundaries)
    if (e.key === '[' || e.key === ']' || e.key === '-' || e.key === '=' || e.key === '\\\\') {{
      e.preventDefault();
      try {{ window.parent.postMessage({{ key: e.key }}, '*'); }} catch(_) {{}}
    }}
    // Digit key → seed bar jump input
    if (/^[0-9]$/.test(e.key) && !e.ctrlKey && !e.metaKey) {{
      e.preventDefault();
      const inp = document.getElementById('bar-jump-input');
      inp.focus(); inp.value = e.key;
    }}
    // Letter key → seed ticker input in parent browser
    if (e.key.length === 1 && /[a-zA-Z]/.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey) {{
      e.preventDefault();
      try {{ window.parent.postMessage({{ key: e.key }}, '*'); }} catch(_) {{}}
    }}
  }});

  function _fmtDate(n) {{
    const _t = DATA.bars[n].time;
    if (typeof _t === 'string') return _t.slice(0, 10);
    if (typeof _t === 'object' && _t.year) return _t.year + '-' + String(_t.month).padStart(2,'0') + '-' + String(_t.day).padStart(2,'0');
    return new Date(_t * 1000).toISOString().slice(0, 10);
  }}

  // Date jump input
  document.getElementById('date-input').addEventListener('focus',   function()  {{ this.select(); }});
  document.getElementById('date-input').addEventListener('blur',    function()  {{ this.value = _fmtDate(current); }});
  document.getElementById('date-input').addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') {{
      const q = this.value.trim();
      let best = N - 1;
      for (let i = 0; i < N; i++) {{
        const s = _fmtDate(i);
        if (s >= q) {{ best = i; break; }}
      }}
      setPlaying(false); jump(best); this.blur();
    }}
    if (e.key === 'Escape') {{ this.blur(); }}
  }});

  // Bar jump input
  document.getElementById('bar-jump-input').addEventListener('focus',   function()  {{ this.select(); }});
  document.getElementById('bar-jump-input').addEventListener('blur',    function()  {{ this.value = current; }});
  document.getElementById('bar-jump-input').addEventListener('input',   function()  {{ this.value = this.value.replace(/[^0-9]/g, ''); }});
  document.getElementById('bar-jump-input').addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') {{
      const n = parseInt(this.value);
      if (!isNaN(n)) {{ setPlaying(false); jump(n); }}
      this.blur();
    }}
    if (e.key === 'Escape') {{ this.blur(); }}
  }});

  // Receive keys forwarded from parent browser index (when iframe not yet focused)
  window.addEventListener('message', function(e) {{
    if (!e.data || !e.data.key) return;
    if (e.data.key === ' ') {{ setPlaying(!playing); return; }}
    if (e.data.key === 'ArrowUp')   {{ const fi = document.getElementById('fps-input'); fi.value = Math.min(60, (parseInt(fi.value) || 8) + 1); return; }}
    if (e.data.key === 'ArrowDown') {{ const fi = document.getElementById('fps-input'); fi.value = Math.max(1,  (parseInt(fi.value) || 8) - 1); return; }}
    if (/^[0-9]$/.test(e.data.key)) {{
      const inp = document.getElementById('bar-jump-input');
      inp.focus(); inp.value = e.data.key;
    }}
  }});

  // --- resize ---
  window.addEventListener('resize', () => {{
    chart.applyOptions({{ width: container.clientWidth, height: container.clientHeight }});
  }});

  // --- init ---
  render(0);

  // Apply ?lock= param: jump to a specific bar/date on load
  (function() {{
    const lock = new URLSearchParams(location.search).get('lock');
    if (!lock) return;
    if (lock === 'end') {{ jump(N - 1); return; }}
    if (lock.startsWith('bar:')) {{
      const n = parseInt(lock.slice(4));
      if (!isNaN(n)) jump(Math.max(0, Math.min(N - 1, n)));
      return;
    }}
    if (lock.startsWith('date:')) {{
      const q = lock.slice(5);
      for (let i = 0; i < N; i++) {{
        if (_fmtDate(i) >= q) {{ jump(i); return; }}
      }}
      jump(N - 1);
    }}
  }})();
}})();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def generate_browser_index(output_dir: Path, timeframe: str, ind_conf: str, fps: int = 8) -> Path:
    """Generate index.html in output_dir — a cycling iframe browser for all exported replays."""
    files = sorted(f.name for f in Path(output_dir).glob("*.html") if f.name != "index.html")
    if not files:
        return None

    sep = f"_{timeframe}_"
    labels = [f[:f.index(sep)] if sep in f else f.split("_")[0] for f in files]

    files_js  = json.dumps(files)
    labels_js = json.dumps(labels)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Replay Browser — {timeframe} / ind_conf_{ind_conf}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #000; color: #ccc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; overflow: hidden; }}
  #nav {{
    height: 44px; display: flex; align-items: center; gap: 10px;
    padding: 0 14px; background: #000; border-bottom: 1px solid #222; flex-shrink: 0;
  }}
  button {{
    background: #111; color: #ccc; border: 1px solid #333;
    padding: 5px 12px; cursor: pointer; border-radius: 3px; font-size: 13px;
  }}
  button:hover {{ background: #222; }}
  #count {{ color: #555; font-size: 12px; white-space: nowrap; }}
  #hint {{ font-size: 11px; color: #2a2a2a; margin-left: auto; white-space: nowrap; }}
  .nav-sep {{ width: 1px; height: 24px; background: #222; flex-shrink: 0; }}
  #lock-wrap {{ display: flex; align-items: center; }}
  #lock-mode-btn {{
    background: #111; color: #555; border: 1px solid #2a2a2a; border-right: none;
    padding: 4px 9px; border-radius: 3px 0 0 3px; font-size: 12px;
    cursor: pointer; user-select: none; white-space: nowrap;
  }}
  #lock-mode-btn:hover {{ color: #ccc; }}
  #lock-val-inp {{
    background: #111; color: #ccc; border: 1px solid #2a2a2a; border-left: none;
    padding: 4px 8px; border-radius: 0 3px 3px 0; font-size: 12px; width: 110px;
  }}
  #lock-val-inp:disabled {{ color: #2a2a2a; pointer-events: none; }}
  #lock-val-inp:not(:disabled):focus {{ outline: none; }}
  #ticker-wrap {{ position: relative; }}
  #ticker-input {{
    background: #111; color: #fff; border: 1px solid #333;
    padding: 4px 10px; border-radius: 3px; font-size: 14px; font-weight: bold;
    width: 130px; text-align: center; cursor: pointer;
  }}
  #ticker-input:focus {{ outline: none; border-color: #555; cursor: text; }}
  #dropdown {{
    display: none; position: absolute; top: calc(100% + 4px); left: 0;
    background: #0d0d0d; border: 1px solid #2a2a2a; border-radius: 3px;
    max-height: 260px; overflow-y: auto; z-index: 100; min-width: 100%;
    box-shadow: 0 4px 12px rgba(0,0,0,0.6);
  }}
  .dd-item {{
    padding: 6px 12px; font-size: 12px; cursor: pointer; color: #888;
    white-space: nowrap;
  }}
  .dd-item:hover, .dd-item.hi {{ background: #1a1a1a; color: #fff; }}
  #frame {{ width: 100%; height: calc(100vh - 44px); border: none; display: block; }}
</style>
</head>
<body>

<div id="nav">
  <button id="btn-prev" title="">&#9664;</button>
  <div id="ticker-wrap">
    <input id="ticker-input" type="text" autocomplete="off" spellcheck="false">
    <div id="dropdown"></div>
  </div>
  <span id="count"></span>
  <button id="btn-next" title="">&#9654;</button>
  <div class="nav-sep"></div>
  <div id="lock-wrap">
    <div id="lock-mode-btn" title="Lock mode (\\ to cycle)">start</div>
    <input id="lock-val-inp" type="text" disabled autocomplete="off" spellcheck="false" placeholder="">
  </div>
  <span id="hint">{timeframe} &nbsp;·&nbsp; conf {ind_conf} &nbsp;·&nbsp; {len(files)} tickers</span>
</div>

<iframe id="frame" src="" frameborder="0" allowfullscreen></iframe>

<script>
(function() {{
  const FILES  = {files_js};
  const LABELS = {labels_js};
  const TOTAL  = FILES.length;
  const FPS    = {fps};
  let idx = 0;
  let dropIdx = -1;
  let lockMode    = 'start';
  let lockBarVal  = '';
  let lockDateVal = '';
  const LOCK_MODES = ['start', 'bar', 'date', 'end'];

  const tickerInput = document.getElementById('ticker-input');
  const dropdown    = document.getElementById('dropdown');

  function buildLockParam() {{
    if (lockMode === 'end')                  return '&lock=end';
    if (lockMode === 'bar'  && lockBarVal)   return '&lock=bar:'  + lockBarVal;
    if (lockMode === 'date' && lockDateVal)  return '&lock=date:' + encodeURIComponent(lockDateVal);
    return '';
  }}

  function updateLockDisplay() {{
    const btn = document.getElementById('lock-mode-btn');
    btn.textContent = lockMode;
    btn.classList.toggle('has-lock', lockMode !== 'start');
    const inp = document.getElementById('lock-val-inp');
    const needsVal = lockMode === 'bar' || lockMode === 'date';
    inp.disabled    = !needsVal;
    inp.placeholder = lockMode === 'bar' ? 'bar #' : lockMode === 'date' ? 'YYYY-MM-DD' : '';
    inp.value       = lockMode === 'bar' ? lockBarVal : lockMode === 'date' ? lockDateVal : '';
  }}

  function go(n) {{
    idx = ((n % TOTAL) + TOTAL) % TOTAL;
    document.getElementById('frame').src = FILES[idx] + '?fps=' + FPS + buildLockParam();
    document.getElementById('count').textContent = (idx + 1) + ' / ' + TOTAL;
    window.location.hash = LABELS[idx];
    document.getElementById('btn-prev').title = LABELS[((idx - 1) + TOTAL) % TOTAL];
    document.getElementById('btn-next').title = LABELS[(idx + 1) % TOTAL];
    tickerInput.value = LABELS[idx];
  }}

  function buildDropdown(q) {{
    dropdown.innerHTML = '';
    dropIdx = -1;
    const up = q.trim().toUpperCase();
    const matches = LABELS.reduce(function(acc, l, i) {{
      if (!up || l.startsWith(up)) acc.push({{ l: l, i: i }});
      return acc;
    }}, []);
    if (!matches.length) {{ dropdown.style.display = 'none'; return; }}
    matches.forEach(function(m) {{
      const el = document.createElement('div');
      el.className = 'dd-item';
      el.textContent = m.l;
      el.addEventListener('mousedown', function(e) {{ e.preventDefault(); }});
      el.addEventListener('click', function() {{ go(m.i); tickerInput.blur(); }});
      dropdown.appendChild(el);
    }});
    dropdown.style.display = 'block';
  }}

  function moveDrop(delta) {{
    const items = dropdown.querySelectorAll('.dd-item');
    if (!items.length) return;
    items[dropIdx] && items[dropIdx].classList.remove('hi');
    dropIdx = Math.max(0, Math.min(items.length - 1, dropIdx + delta));
    items[dropIdx].classList.add('hi');
    items[dropIdx].scrollIntoView({{ block: 'nearest' }});
  }}

  tickerInput.addEventListener('focus', function() {{
    this.select();
    buildDropdown('');
  }});
  tickerInput.addEventListener('input', function() {{
    const clean = this.value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
    if (clean !== this.value) this.value = clean;
    buildDropdown(clean);
  }});
  tickerInput.addEventListener('blur', function() {{
    dropdown.style.display = 'none';
    dropIdx = -1;
    this.value = LABELS[idx];
  }});
  tickerInput.addEventListener('keydown', function(e) {{
    if (e.key === 'ArrowDown') {{ e.preventDefault(); moveDrop(dropIdx < 0 ? 0 : 1); return; }}
    if (e.key === 'ArrowUp')   {{ e.preventDefault(); moveDrop(-1); return; }}
    if (e.key === 'Enter') {{
      const items = dropdown.querySelectorAll('.dd-item');
      if (dropIdx >= 0 && items[dropIdx]) {{
        const label = items[dropIdx].textContent;
        const i = LABELS.indexOf(label);
        if (i >= 0) go(i);
      }} else if (items.length === 1) {{
        const i = LABELS.indexOf(items[0].textContent);
        if (i >= 0) go(i);
      }} else {{
        const q = this.value.trim().toUpperCase();
        const i = LABELS.findIndex(function(l) {{ return l === q; }});
        if (i >= 0) go(i);
      }}
      this.blur();
    }}
    if (e.key === 'Escape') {{ this.blur(); }}
  }});

  document.getElementById('btn-prev').addEventListener('click', function() {{ go(idx - 1); }});
  document.getElementById('btn-next').addEventListener('click', function() {{ go(idx + 1); }});

  const lkValInp = document.getElementById('lock-val-inp');

  function cycleLock() {{
    lockMode = LOCK_MODES[(LOCK_MODES.indexOf(lockMode) + 1) % LOCK_MODES.length];
    updateLockDisplay();
    if (lockMode === 'bar' || lockMode === 'date') {{
      lkValInp.focus(); lkValInp.select();
    }} else {{
      go(idx);
    }}
  }}

  document.getElementById('lock-mode-btn').addEventListener('click', cycleLock);

  lkValInp.addEventListener('input', function() {{
    if (lockMode === 'bar') this.value = this.value.replace(/[^0-9]/g, '');
    else this.value = this.value.replace(/[^0-9\-]/g, '');
  }});
  lkValInp.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') {{
      if (lockMode === 'bar')  lockBarVal  = this.value.trim();
      if (lockMode === 'date') lockDateVal = this.value.trim();
      updateLockDisplay(); go(idx); this.blur();
    }}
    if (e.key === 'Escape') {{
      this.value = lockMode === 'bar' ? lockBarVal : lockDateVal;
      this.blur();
    }}
    if (e.key === '\\\\') {{
      e.preventDefault();
      if (lockMode === 'bar')  lockBarVal  = this.value.trim();
      if (lockMode === 'date') lockDateVal = this.value.trim();
      cycleLock();
    }}
  }});

  document.addEventListener('keydown', function(e) {{
    if (document.activeElement.tagName === 'INPUT') return;
    if (e.key === '[' || e.key === '=') {{ e.preventDefault(); go(idx - 1); }}
    if (e.key === ']' || e.key === '-') {{ e.preventDefault(); go(idx + 1); }}
    if (e.key === '/') {{ e.preventDefault(); tickerInput.focus(); }}
    if (e.key === ' ' || e.key === 'ArrowUp' || e.key === 'ArrowDown') {{ e.preventDefault(); try {{ document.getElementById('frame').contentWindow.postMessage({{ key: e.key }}, '*'); }} catch(_) {{}} }}
    if (e.key.length === 1 && /[a-zA-Z]/.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey) {{
      e.preventDefault();
      tickerInput.focus();
      tickerInput.value = e.key.toUpperCase();
      buildDropdown(e.key.toUpperCase());
    }}
    if (/^[0-9]$/.test(e.key) && !e.ctrlKey && !e.metaKey) {{
      e.preventDefault();
      try {{ document.getElementById('frame').contentWindow.postMessage({{ key: e.key }}, '*'); }} catch(_) {{}}
    }}
    if (e.key === '\\\\') {{ cycleLock(); }}
  }});

  window.addEventListener('message', function(e) {{
    if (!e.data || !e.data.key) return;
    if (e.data.key === '[' || e.data.key === '=') go(idx - 1);
    if (e.data.key === ']' || e.data.key === '-') go(idx + 1);
    if (e.data.key === '\\\\') {{ cycleLock(); }}
    if (e.data.key.length === 1 && /[a-zA-Z]/.test(e.data.key)) {{
      tickerInput.focus();
      tickerInput.value = e.data.key.toUpperCase();
      buildDropdown(e.data.key.toUpperCase());
    }}
  }});

  const startLabel = decodeURIComponent(window.location.hash.slice(1)).toUpperCase();
  const startIdx = LABELS.findIndex(function(l) {{ return l === startLabel; }});
  go(startIdx >= 0 ? startIdx : 0);
}})();
</script>
</body>
</html>
"""
    out = Path(output_dir) / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def export_replay_html(prepared_df, colors, ticker, timeframe, ind_conf, output_dir, raw_df=None, out_path=None):
    # smc-based extractors (FVG, OB, Liquidity) need a volume column that
    # prepare_dataframe drops when show_volume=False.  Use raw_df when available.
    ohlcv_df     = raw_df if raw_df is not None else prepared_df
    col_styles   = _col_styles(prepared_df, colors)
    ob_data      = _extract_ob_events(ohlcv_df, ind_conf, timeframe, colors)
    qqemod_data  = _extract_qqemod_events(ohlcv_df, ind_conf, timeframe, colors)
    fvg_data     = _extract_fvg_events(ohlcv_df, ind_conf, timeframe, colors)
    bos_data     = _extract_bos_choch_events(ohlcv_df, colors)
    liq_data     = _extract_liquidity_events(ohlcv_df, ind_conf, timeframe, colors)
    pmm_data     = _extract_pmm_events(ohlcv_df, ind_conf, timeframe)
    ob_avwap_data        = _extract_ob_avwap_events(ohlcv_df, ind_conf, timeframe, colors)
    bos_choch_avwap_data = _extract_bos_choch_avwap_events(ohlcv_df, ind_conf, timeframe, colors)
    pv_avwap_data        = _extract_peaks_valleys_avwap_events(ohlcv_df, ind_conf, timeframe, colors)

    n_ob          = len(ob_data['events'])      if ob_data      else 0
    n_qq          = len(qqemod_data['anchors']) if qqemod_data  else 0
    n_fvg         = len(fvg_data['events'])     if fvg_data     else 0
    n_bos         = len(bos_data['events'])     if bos_data     else 0
    n_liq         = len(liq_data['events'])     if liq_data     else 0
    n_pmm         = sum(len(pmm_data.get(d, {}).get('slots', [])) for d in ('valley', 'peak')) if pmm_data else 0
    n_ob_avwap    = sum(len(c['events']) for c in ob_avwap_data)        if ob_avwap_data        else 0
    n_bos_avwap   = sum(len(c['events']) for c in bos_choch_avwap_data) if bos_choch_avwap_data else 0
    n_pv_avwap    = sum(len(c['events']) for c in pv_avwap_data)        if pv_avwap_data        else 0
    print(f"  [Export] OB:{n_ob}  QQEMOD:{n_qq}  FVG:{n_fvg}  "
          f"BoS/CHoCH:{n_bos}  Liq:{n_liq}  PMM slots:{n_pmm}  "
          f"OBaVWAP:{n_ob_avwap}  BoSaVWAP:{n_bos_avwap}  PVaVWAP:{n_pv_avwap}")

    html = build_html(prepared_df, col_styles, ticker, timeframe, ind_conf,
                      ob_data=ob_data, qqemod_data=qqemod_data, fvg_data=fvg_data,
                      bos_data=bos_data, liq_data=liq_data, pmm_data=pmm_data,
                      ob_avwap_data=ob_avwap_data, bos_choch_avwap_data=bos_choch_avwap_data,
                      pv_avwap_data=pv_avwap_data, colors=colors)

    if out_path is not None:
        out = Path(out_path)
    else:
        ts  = datetime.now().strftime('%d%m%y_%H%M%S')
        out = Path(output_dir) / f"{ticker}_{timeframe}_{ts}_replay.html"
    out.write_text(html, encoding='utf-8')
    print(f"[Export] Saved {out}  ({len(html) // 1024} KB,  {len(prepared_df)} bars,  "
          f"{len(col_styles)} T1 lines,  OB:{n_ob}  QQEMOD:{n_qq}  FVG:{n_fvg}  "
          f"BoS/CHoCH:{n_bos}  Liq:{n_liq}  PMM:{n_pmm}  "
          f"OBaVWAP:{n_ob_avwap}  BoSaVWAP:{n_bos_avwap})")
    return out
