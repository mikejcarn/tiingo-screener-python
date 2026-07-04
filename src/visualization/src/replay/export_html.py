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

_OHLCV_COLS = frozenset({'date', 'time', 'index', 'open', 'high', 'low', 'close', 'volume'})

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
        elif col.startswith('aVWAP_BoS_CHoCH_bear_'):
            _add(col, colors['red'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_BoS_CHoCH_bull_'):
            _add(col, colors['teal'], _w(cfg), _s(cfg))
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

    bars = []
    for row in prepared_df.itertuples(index=False):
        bar = {
            'time':  _to_unix(row.date),
            'open':  _safe_float(row.open),
            'high':  _safe_float(row.high),
            'low':   _safe_float(row.low),
            'close': _safe_float(row.close),
        }
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
               ob_data=None, qqemod_data=None):
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
    if ob_data is not None:
        payload['ob'] = ob_data
    if qqemod_data is not None:
        payload['qq'] = qqemod_data

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
  body {{ background: #131722; color: #d1d4dc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; user-select: none; }}
  #chart {{ width: 100vw; height: calc(100vh - 52px); }}
  #controls {{
    height: 52px; display: flex; align-items: center; gap: 10px;
    padding: 0 14px; background: #1e222d; border-top: 1px solid #2a2e39;
  }}
  button {{
    background: #2a2e39; color: #d1d4dc; border: 1px solid #363c4e;
    padding: 5px 11px; cursor: pointer; border-radius: 3px; font-size: 13px;
  }}
  button:hover {{ background: #363c4e; }}
  button.active {{ background: #2962ff; border-color: #2962ff; color: #fff; }}
  #slider {{ flex: 1; min-width: 0; accent-color: #2962ff; cursor: pointer; }}
  #bar-info {{ font-size: 12px; color: #787b86; min-width: 90px; white-space: nowrap; }}
  .sep {{ width: 1px; height: 24px; background: #363c4e; }}
  label {{ font-size: 12px; color: #787b86; display: flex; align-items: center; gap: 5px; white-space: nowrap; }}
  input[type=number] {{
    width: 46px; background: #2a2e39; color: #d1d4dc; border: 1px solid #363c4e;
    padding: 4px 6px; border-radius: 3px; font-size: 12px; text-align: center;
  }}
  input[type=number]::-webkit-inner-spin-button {{ opacity: 1; }}
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
  <span id="bar-info">0 / {n_bars - 1}</span>
  <div class="sep"></div>
  <label>fps <input type="number" id="fps-input" value="12" min="1" max="60"></label>
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

  // --- chart setup ---
  const container = document.getElementById('chart');
  const chart = LightweightCharts.createChart(container, {{
    width:  container.clientWidth,
    height: container.clientHeight,
    layout: {{ background: {{ color: '#131722' }}, textColor: '#d1d4dc' }},
    grid:   {{ vertLines: {{ color: '#1e222d' }}, horzLines: {{ color: '#1e222d' }} }},
    crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
    rightPriceScale: {{ borderColor: '#2a2e39' }},
    timeScale: {{ borderColor: '#2a2e39', timeVisible: true, secondsVisible: false }},
  }});

  const candleSeries = chart.addCandlestickSeries({{
    upColor: '#26a69a', downColor: '#ef5350',
    borderUpColor: '#26a69a', borderDownColor: '#ef5350',
    wickUpColor: '#26a69a', wickDownColor: '#ef5350',
  }});

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

  // --- render ---
  function render(n) {{
    const slice = DATA.bars.slice(0, n + 1);

    candleSeries.setData(slice.map(b => ({{
      time: b.time, open: b.open, high: b.high, low: b.low, close: b.close
    }})));

    for (const [col, series] of Object.entries(lineSeries)) {{
      const pts = [];
      for (const b of slice) {{
        const v = b[col];
        if (v !== null && v !== undefined) pts.push({{ time: b.time, value: v }});
      }}
      series.setData(pts);
    }}

    // OB segments
    if (DATA.ob) {{
      for (let i = 0; i < DATA.ob.events.length; i++) {{
        const ev = DATA.ob.events[i];
        const visFrom = ev.vf !== undefined ? ev.vf : ev.s;
        let key;
        if (n < visFrom) {{
          key = -2;                                   // not yet visible
        }} else if (ev.da !== undefined && n >= ev.da) {{
          key = -1;                                   // displaced
        }} else if (DATA.ob.max_mit === 0 && ev.m && ev.e < n) {{
          key = -1;                                   // mitigated + max_mit=0
        }} else {{
          key = ev.e >= n ? n : ev.e;                 // growing or finalized
        }}
        if (key === obKey[i]) continue;
        obKey[i] = key;
        if (key < 0) {{
          obSeries[i].setData([]);
        }} else {{
          const endBar = Math.min(ev.e, n);
          obSeries[i].setData([
            {{ time: DATA.bars[ev.s].time, value: ev.p }},
            {{ time: DATA.bars[endBar].time, value: ev.p }},
          ]);
        }}
      }}
    }}

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

    document.getElementById('bar-info').textContent = n + ' / ' + (N - 1);
    document.getElementById('slider').value = n;
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
    const fps = Math.max(1, parseInt(document.getElementById('fps-input').value) || 12);
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
    if (e.key === ' ')          {{ e.preventDefault(); setPlaying(!playing); }}
    if (e.key === 'Home')       jump(0);
    if (e.key === 'End')        jump(N - 1);
  }});

  // --- resize ---
  window.addEventListener('resize', () => {{
    chart.applyOptions({{ width: container.clientWidth, height: container.clientHeight }});
  }});

  // --- init ---
  render(0);
}})();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def export_replay_html(prepared_df, colors, ticker, timeframe, ind_conf, output_dir):
    col_styles  = _col_styles(prepared_df, colors)
    ob_data     = _extract_ob_events(prepared_df, ind_conf, timeframe, colors)
    qqemod_data = _extract_qqemod_events(prepared_df, ind_conf, timeframe, colors)

    n_ob    = len(ob_data['events']) if ob_data else 0
    n_qq    = len(qqemod_data['anchors']) if qqemod_data else 0
    print(f"  [Export] OB events: {n_ob}  QQEMOD anchors: {n_qq}")

    html = build_html(prepared_df, col_styles, ticker, timeframe, ind_conf,
                      ob_data=ob_data, qqemod_data=qqemod_data)

    ts  = datetime.now().strftime('%d%m%y_%H%M%S')
    out = Path(output_dir) / f"{ticker}_{timeframe}_{ts}_replay.html"
    out.write_text(html, encoding='utf-8')
    print(f"[Export] Saved {out}  ({len(html) // 1024} KB,  {len(prepared_df)} bars,  "
          f"{len(col_styles)} indicator lines,  {n_ob} OB,  {n_qq} QQEMOD)")
    return out
