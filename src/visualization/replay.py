"""
Bar-by-bar replay mode.

    python app.py --replay --ticker BTCUSD --timeframe daily --ind-conf 2

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

Approach: indicator CSV is pre-computed once; each step slices
prepared_df.iloc[:n+1] and calls chart.set() + line.set() per
registered column.  No recomputation per step.

aVWAP NaN values before each anchor bar are preserved in the slice,
so lines appear naturally at the correct bar as time advances.

Segment-based indicators (FVG, OB, BoS/CHoCH, Liquidity, divergences)
are not included in replay — they require two-point segments whose
endpoints change per step.  All aVWAP time-series families, SMA, and
Supertrend are fully supported.
"""
import sys
import time
import threading

import numpy as np
import pandas as pd
from lightweight_charts import Chart

from src.visualization.src.color_palette import get_color_palette
from src.visualization.src.charts import prepare_dataframe, configure_base_chart
from src.visualization.src.indicator_visualizations import (
    _cfg_idx, _ensure_time_col, _line_set_df,
)
from src.visualization.src.subcharts import _load_indicator_data

_TIMEFRAME_MAP = {
    'd': 'daily', 'w': 'weekly',
    '4h': '4hour', 'h': '1hour', '5min': '5min',
}

_OHLCV_COLS = frozenset({'date', 'time', 'index', 'open', 'high', 'low', 'close', 'volume'})


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

    state = {
        'n': 0,             # start at the beginning so replay plays forward
        'playing': False,
        'speed': 0.3,       # seconds per bar in play mode
        'auto_fit': True,   # fit chart to all bars on every step
    }

    chart = Chart(inner_width=1.0, inner_height=1.0, maximize=True)
    chart.name = '0'
    configure_base_chart(prepared_df, chart, show_volume=False)

    chart.topbar.textbox('ticker', ticker)
    chart.topbar.textbox('timeframe', str(tf))
    chart.topbar.textbox('ind_conf', str(ind_conf))
    chart.topbar.textbox('bar', f'0/{n_total - 1}')
    chart.topbar.button('auto_fit', 'FIT: ON', align='left', separator=True,
                        func=lambda: _toggle_auto_fit(chart, state))

    colors = get_color_palette()
    registry = _build_line_registry(chart, prepared_df, colors)

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
# Line registry
# ---------------------------------------------------------------------------

def _build_line_registry(chart, df, colors):
    """
    Pre-create one lightweight-charts Line per indicator column.
    Returns {col_name: Line}.

    Styling mirrors _aVWAP_visualization() in indicator_visualizations.py.
    The '_Supertrend_Active' key is synthetic (computed from Upper/Lower/Direction).
    """
    registry = {}

    def _make(col, color, width, style='solid'):
        line = chart.create_line(
            price_line=False,
            price_label=False,
            color=color,
            width=width,
            style=style,
        )
        registry[col] = line

    def _w(cfg):
        return 2 if cfg == 0 else 1

    def _s(cfg):
        return 'solid' if cfg == 0 else 'dotted'

    for col in df.columns:
        if col in _OHLCV_COLS:
            continue

        cfg = _cfg_idx(col)

        # QQEMOD — check dot variants first (they also startswith the solid prefix)
        if col.startswith('aVWAP_QQEMOD_bear_dot_'):
            _make(col, colors['teal'], 1, 'dotted')
        elif col.startswith('aVWAP_QQEMOD_bull_dot_'):
            _make(col, colors['red'], 1, 'dotted')
        elif col.startswith('aVWAP_QQEMOD_bear_'):
            _make(col, colors['teal'], _w(cfg), _s(cfg))
        elif col.startswith('aVWAP_QQEMOD_bull_'):
            _make(col, colors['red'], _w(cfg), _s(cfg))

        # Pinch
        elif col.startswith('aVWAP_pinch_peak_'):
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

        # Price maxima / minima
        elif col.startswith('aVWAP_price_maxima_minima_valley_'):
            _make(col, colors['teal'], 2, 'solid')
        elif col.startswith('aVWAP_price_maxima_minima_peak_'):
            _make(col, colors['red'], 2, 'solid')

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

        # Supertrend (upper / lower drawn individually; active line is synthetic below)
        elif col == 'Supertrend_Upper':
            _make(col, colors['orange'], 1)
        elif col == 'Supertrend_Lower':
            _make(col, colors['orange'], 1)

    # Synthetic Supertrend active line (max(upper,lower) per direction)
    if all(c in df.columns for c in ('Supertrend_Upper', 'Supertrend_Lower', 'Supertrend_Direction')):
        registry['_Supertrend_Active'] = chart.create_line(
            price_line=False, price_label=False,
            color=colors['black'], width=2,
        )

    print(f"  Line registry built: {len(registry)} lines for {ticker_label(df)} columns")
    return registry


def ticker_label(df):
    return sum(1 for c in df.columns if c not in _OHLCV_COLS)


# ---------------------------------------------------------------------------
# Render / step / play
# ---------------------------------------------------------------------------

def _render(chart, df, registry, state, n):
    """Slice df to bar n and update chart + every registered line."""
    s = df.iloc[: n + 1]

    chart.set(s)

    # _ensure_time_col creates 'time' from 'date' for _line_set_df compatibility
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

    if state.get('auto_fit', True):
        chart.fit()

    try:
        chart.topbar['bar'].set(f'{n}/{len(df) - 1}')
    except Exception:
        pass


def _step(chart, df, registry, state, delta, n_total):
    """Step backward (delta=-1) or forward (+1) by |delta| bars."""
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
    """
    Called when the user types in the chart search box and hits Enter.
    If the input is a number, jump to that bar index.
    """
    value = value.strip()
    try:
        target = int(value)
    except ValueError:
        print(f"[Replay] Type a bar number (0–{n_total - 1}) to jump — got '{value}'")
        return
    _jump(chart, df, registry, state, target)
    print(f"[Replay] Jumped to bar {state['n']}/{n_total - 1}")


def _toggle_auto_fit(chart, state):
    """Toggle auto-fit mode. Re-enables by snapping chart to fit-all immediately."""
    state['auto_fit'] = not state['auto_fit']
    try:
        chart.topbar['auto_fit'].set('FIT: ON' if state['auto_fit'] else 'FIT: OFF')
    except Exception:
        pass
    if state['auto_fit']:
        chart.fit()


def _toggle_play(state, n_total):
    """Toggle auto-advance play / pause."""
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
