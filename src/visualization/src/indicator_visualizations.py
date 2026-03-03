import re
from collections import defaultdict

import pandas as pd
import numpy as np
from src.visualization.src.color_palette import get_color_palette

colors = get_color_palette()


def add_visualizations(subchart, df, show_banker_RSI):
    """
    Add visualization layers to subchart if input df column data is present
    """

    _FVG_visualization(subchart, df)
    _OB_visualization(subchart, df)
    _BoS_CHoCH_visualization(subchart, df)
    _liquidity_visualization(subchart, df)
    _aVWAP_visualization(subchart, df)
    _supertrend_visualization(subchart, df)
    _SMA_visualization(subchart, df)
    if show_banker_RSI:
        _banker_RSI_visualization(subchart, df)

    # Includes Regular/Hidden divergences for RSI, MACD, OBV, Volume, etc
    _combined_divergence_visualization(subchart, df)


# -----------------------------
# Helpers (NEW)
# -----------------------------
def _ensure_time_col(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize a time column for charting.
    - If df has 'date' but not 'time', create 'time' from 'date'
    - If df has 'time' but not 'date', create 'date' from 'time'
    """
    if 'date' in df.columns and 'time' not in df.columns:
        df = df.copy()
        df['time'] = df['date']
    elif 'time' in df.columns and 'date' not in df.columns:
        df = df.copy()
        df['date'] = df['time']
    return df


def _line_set_df(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Return a 2-col DF: time + value, formatted for lightweight-charts-style setters.
    We standardize on 'time' for all series to avoid date/time mismatch bugs.
    """
    df = _ensure_time_col(df)
    out = df[['time', col]].rename(columns={col: 'value'}).copy()
    return out


def _cfg_idx(col: str) -> int:
    m = re.search(r'_c(\d+)_', col)
    return int(m.group(1)) if m else 0


def _anchor_idx(col: str) -> int:
    """
    Extract trailing integer anchor from '..._251' etc.
    """
    try:
        return int(col.split('_')[-1])
    except Exception:
        return -1


def _select_recent_by_cfg(cols, per_cfg=3):
    """
    Given columns like aVWAP_OB_bull_c2_251, group by cfg idx,
    sort by anchor idx desc, and return only the most recent `per_cfg`.
    """
    grouped = defaultdict(list)
    for c in cols:
        cfg = _cfg_idx(c)
        anc = _anchor_idx(c)
        grouped[cfg].append((anc, c))

    selected = []
    for cfg, items in grouped.items():
        items.sort(reverse=True)  # newest anchors first
        selected.extend([c for _, c in items[:per_cfg]])
    return selected


# -----------------------------
# Visualizations
# -----------------------------
def _FVG_visualization(subchart, df):
    df = _ensure_time_col(df)

    # Note: your original uses lower-case ohlc here; leaving as-is
    # but guarding for common variants.
    ohlc_cols_variants = [
        ['close', 'high', 'low', 'open'],
        ['Close', 'High', 'Low', 'Open'],
    ]
    ohlc_cols = next((v for v in ohlc_cols_variants if all(c in df.columns for c in v)), None)

    if all(col in df.columns for col in ['FVG', 'FVG_High', 'FVG_Low', 'FVG_Mitigated_Index']) and ohlc_cols:
        # Find the last row with actual data (before NaN padding)
        last_data_idx = df[ohlc_cols].last_valid_index()

        # Get all FVG occurrences (bullish=1, bearish=-1)
        fvg_indices = df[df['FVG'] != 0].index

        for idx in fvg_indices:
            mit_idx = df.loc[idx, 'FVG_Mitigated_Index']

            # Determine end idx
            if pd.isna(mit_idx) or mit_idx == 0:
                end_idx = last_data_idx
            else:
                end_idx = int(mit_idx)
                end_idx = min(end_idx, last_data_idx)

            fvg_type = df.loc[idx, 'FVG']
            level = 'FVG_High' if fvg_type == 1 else 'FVG_Low'
            color = colors['teal_trans_3'] if fvg_type == 1 else colors['red_trans_3']

            if idx <= end_idx:
                subchart.create_line(
                    price_line=False,
                    price_label=False,
                    color=color,
                    width=1,
                    style='dashed'
                ).set(pd.DataFrame({
                    'time': [df.loc[idx, 'time'], df.loc[end_idx, 'time']],
                    'value': [df.loc[idx, level]] * 2
                }))


def _OB_visualization(subchart, df):
    df = _ensure_time_col(df)

    if all(col in df.columns for col in ['OB', 'OB_High', 'OB_Low']):
        for idx in df[df['OB'] != 0].index:
            start_time = df.loc[idx, 'time']
            midpoint = (df.loc[idx, 'OB_High'] + df.loc[idx, 'OB_Low']) / 2

            # Determine end time based on mitigation index if present/valid
            end_time = df.iloc[-1]['time']
            if 'OB_Mitigated_Index' in df.columns:
                try:
                    mitigation_idx = int(df.loc[idx, 'OB_Mitigated_Index'])
                    if 0 < mitigation_idx < len(df):
                        end_time = df.loc[mitigation_idx, 'time']
                except Exception:
                    pass

            subchart.create_line(
                price_line=False,
                price_label=False,
                color=colors['teal_OB'] if df.loc[idx, 'OB'] == 1 else colors['red_OB'],
                width=10,
                style='solid'
            ).set(pd.DataFrame({
                'time': [start_time, end_time],
                'value': [midpoint, midpoint]
            }))


def _BoS_CHoCH_visualization(subchart, df):
    df = _ensure_time_col(df)

    required_cols = ['BoS', 'CHoCH', 'BoS_CHoCH_Price', 'BoS_CHoCH_Break_Index']
    if any(col not in df.columns for col in required_cols):
        return

    df2 = df.dropna(subset=required_cols)
    events = df2[(df2['BoS'] != 0) | (df2['CHoCH'] != 0)].index[-25:]

    for idx in events:
        start_time = df2.loc[idx, 'time']
        price = df2.loc[idx, 'BoS_CHoCH_Price']

        # Safely handle break index
        end_time = df2.iloc[-1]['time']
        try:
            break_idx = int(df2.loc[idx, 'BoS_CHoCH_Break_Index'])
            if 0 < break_idx < len(df2):
                end_time = df2.loc[break_idx, 'time']
        except Exception:
            pass

        # Determine color and style
        if df2.loc[idx, 'BoS'] != 0:
            color = colors['teal_trans_3'] if df2.loc[idx, 'BoS'] > 0 else colors['red_trans_3']
            style = 'solid'
            width = 1
        else:
            color = colors['aqua'] if df2.loc[idx, 'CHoCH'] > 0 else colors['red_dark']
            style = 'solid'
            width = 1

        subchart.create_line(
            price_line=False,
            price_label=False,
            color=color,
            width=width,
            style=style
        ).set(pd.DataFrame({
            'time': [start_time, end_time],
            'value': [price, price]
        }))


def _liquidity_visualization(subchart, df):
    df = _ensure_time_col(df)

    if all(col in df.columns for col in ['Liquidity', 'Liquidity_Level']):
        liquidity_events = df[df['Liquidity'] != 0]
        for idx in liquidity_events.index:
            level = df.loc[idx, 'Liquidity_Level']

            subchart.create_line(
                price_line=False,
                price_label=False,
                color=colors['orange_liquidity'],
                width=1,
                style='solid'
            ).set(pd.DataFrame({
                'time': [df.iloc[0]['time'], df.iloc[-1]['time']],
                'value': [level, level]
            }))


def _banker_RSI_visualization(subchart, df):
    df = _ensure_time_col(df)

    if 'banker_RSI' in df.columns:
        color_rules = [
            (0, 5, colors['teal_trans_3']),
            (5, 10, colors['teal']),
            (10, 15, colors['aqua']),
            (15, 20, colors['neon'])
        ]

        if 'volume' in df.columns or 'Volume' in df.columns:
            scale_margin_top = 0.85
            scale_margin_bottom = 0.1
        else:
            scale_margin_top = 0.95
            scale_margin_bottom = 0.0

        rsi_hist = subchart.create_histogram(
            color='rgba(100, 100, 100, 0.4)',
            price_line=False,
            price_label=False,
            scale_margin_top=scale_margin_top,
            scale_margin_bottom=scale_margin_bottom
        )

        hist_data = pd.DataFrame({
            'time': df['time'],
            'value': df['banker_RSI'],
            'color': 'rgba(100, 100, 100, 0.4)'
        })

        for low, high, color in color_rules:
            mask = (hist_data['value'] >= low) & (hist_data['value'] <= high)
            hist_data.loc[mask, 'color'] = color

        rsi_hist.set(hist_data)


def _aVWAP_visualization(subchart, df):
    """
    Improvements:
    - Standardize on 'time' column across all series
    - For OB aVWAPs: color/width by config index (c0/c1/c2...)
    - Optionally limit plotted OB anchors per config to keep the chart readable
    """
    df = _ensure_time_col(df)

    # -------------------------
    # Peaks / Valleys / Gaps / BoS/CHoCH (unchanged selection; standardized time)
    # -------------------------
    peak_cols = [col for col in df.columns if col.startswith('aVWAP_peak_')]
    for col in peak_cols:
        subchart.create_line(
            price_line=False,
            price_label=False,
            color=colors['red_trans_3'],
            width=1
        ).set(_line_set_df(df, col))

    valley_cols = [col for col in df.columns if col.startswith('aVWAP_valley_')]
    for col in valley_cols:
        subchart.create_line(
            price_line=False,
            price_label=False,
            color=colors['teal_trans_3'],
            width=1
        ).set(_line_set_df(df, col))

    gap_up_cols = [col for col in df.columns if col.startswith('Gap_Up_aVWAP_')]
    for col in gap_up_cols:
        subchart.create_line(
            price_line=False,
            price_label=False,
            color=colors['teal_trans_2'],
            width=1,
            style='dotted'
        ).set(_line_set_df(df, col))

    gap_down_cols = [col for col in df.columns if col.startswith('Gap_Down_aVWAP_')]
    for col in gap_down_cols:
        subchart.create_line(
            price_line=False,
            price_label=False,
            color=colors['red_trans_2'],
            width=1,
            style='dotted'
        ).set(_line_set_df(df, col))

    BoS_CHoCH_bear_cols = [col for col in df.columns if col.startswith('aVWAP_BoS_CHoCH_bear_')]
    for col in BoS_CHoCH_bear_cols:
        subchart.create_line(
            price_line=False,
            price_label=False,
            color=colors['red'],
            width=1
        ).set(_line_set_df(df, col))

    BoS_CHoCH_bull_cols = [col for col in df.columns if col.startswith('aVWAP_BoS_CHoCH_bull_')]
    for col in BoS_CHoCH_bull_cols:
        subchart.create_line(
            price_line=False,
            price_label=False,
            color=colors['teal'],
            width=1
        ).set(_line_set_df(df, col))

    # -------------------------
    # OB aVWAPs
    # -------------------------
    # Toggle: limit plotted OB anchors per config to keep charts readable
    LIMIT_OB_ANCHORS_PER_CFG = True
    OB_ANCHORS_PER_CFG = 3  # plot only the most recent N anchors for each config

    # Bullish OB aVWAPs
    OB_bull_cols = [col for col in df.columns if col.startswith('aVWAP_OB_bull_')]
    if LIMIT_OB_ANCHORS_PER_CFG:
        OB_bull_cols = _select_recent_by_cfg(OB_bull_cols, per_cfg=OB_ANCHORS_PER_CFG)

    for col in OB_bull_cols:
        cfg = _cfg_idx(col)
        # Primary config c0 emphasized
        width = 2 if cfg == 0 else 1

        # Config-aware color (falls back to aqua if palette keys missing)
        color = (
            colors.get('aqua') if cfg == 0 else
            colors.get('teal_trans_2', colors.get('aqua')) if cfg == 1 else
            colors.get('teal_trans_3', colors.get('aqua'))
        )

        subchart.create_line(
            price_line=False,
            price_label=False,
            color=color,
            width=width
        ).set(_line_set_df(df, col))

    # Bearish OB aVWAPs
    OB_bear_cols = [col for col in df.columns if col.startswith('aVWAP_OB_bear_')]
    if LIMIT_OB_ANCHORS_PER_CFG:
        OB_bear_cols = _select_recent_by_cfg(OB_bear_cols, per_cfg=OB_ANCHORS_PER_CFG)

    for col in OB_bear_cols:
        cfg = _cfg_idx(col)
        width = 2 if cfg == 0 else 1

        color = (
            colors.get('red_dark') if cfg == 0 else
            colors.get('red_trans_2', colors.get('red_dark')) if cfg == 1 else
            colors.get('red_trans_3', colors.get('red_dark'))
        )

        subchart.create_line(
            price_line=False,
            price_label=False,
            color=color,
            width=width
        ).set(_line_set_df(df, col))

    # -------------------------
    # Average aVWAPs (kept, standardized time)
    # -------------------------
    avg_configs = [
        {
            'name': 'Peaks_Valleys_avg',
            'primary_width': 4,
            'secondary_width': 2,
            'color': colors['orange_aVWAP'],
            'style': 'solid'
        },
        {
            'name': 'Peaks_avg',
            'primary_width': 4,
            'secondary_width': 2,
            'color': colors['red'],
            'style': 'solid'
        },
        {
            'name': 'Valleys_avg',
            'primary_width': 4,
            'secondary_width': 2,
            'color': colors['teal'],
            'style': 'solid'
        },
        {
            'name': 'OB_avg',
            'primary_width': 3,
            'secondary_width': 1.5,
            'color': colors['orange_aVWAP'],
            'style': 'dashed'
        },
        {
            'name': 'Gaps_avg',
            'primary_width': 4,
            'secondary_width': 2,
            'color': colors['orange_aVWAP'],
            'style': 'dotted'
        },
        {
            'name': 'BoS_CHoCH_avg',
            'primary_width': 3,
            'secondary_width': 1.5,
            'color': colors['orange_aVWAP'],
            'style': 'large_dashed'
        },
        {
            'name': 'All_avg',
            'primary_width': 5,
            'secondary_width': 3,
            'color': colors['gray_trans'],
            'style': 'solid'
        }
    ]

    for avg_cfg in avg_configs:
        avg_name = avg_cfg['name']
        matching_cols = [col for col in df.columns if col.startswith(avg_name)]

        for col in matching_cols:
            width = avg_cfg['primary_width'] if col == avg_name else avg_cfg['secondary_width']

            subchart.create_line(
                price_line=False,
                price_label=False,
                color=avg_cfg['color'],
                width=width,
                style=avg_cfg['style']
            ).set(_line_set_df(df, col))


def _supertrend_visualization(subchart, df):
    df = _ensure_time_col(df)

    if all(col in df.columns for col in ['Supertrend_Upper', 'Supertrend_Lower', 'Supertrend_Direction']):
        upper_line = subchart.create_line(
            price_line=False,
            price_label=False,
            color=colors['orange'],
            width=1.0,
        )
        upper_line.set(_line_set_df(df, 'Supertrend_Upper'))

        lower_line = subchart.create_line(
            price_line=False,
            price_label=False,
            color=colors['orange'],
            width=1.0,
        )
        lower_line.set(_line_set_df(df, 'Supertrend_Lower'))

        active_supertrend = np.where(
            df['Supertrend_Direction'] == -1,
            df['Supertrend_Lower'],
            df['Supertrend_Upper']
        )
        active_line = subchart.create_line(
            price_line=False,
            price_label=False,
            color=colors['black'],
            width=2.0
        )
        active_line.set(pd.DataFrame({'time': df['time'], 'value': active_supertrend}))


def _SMA_visualization(subchart, df):
    df = _ensure_time_col(df)

    sma_cols = [col for col in df.columns if col.startswith('SMA_')]
    for sma_col in sma_cols:
        try:
            period = int(sma_col.split('_')[1])
        except Exception:
            period = 0

        width = (
            1 if period <= 10 else
            3 if period <= 50 else
            5 if period <= 100 else
            7 if period <= 200 else
            9
        )

        subchart.create_line(
            price_line=False,
            price_label=False,
            color=colors['blue_SMA'],
            width=width
        ).set(_line_set_df(df, sma_col))


def _combined_divergence_visualization(subchart, df):
    df = _ensure_time_col(df)

    divergence_types = [
        {
            'name': 'RSI',
            'regular_bull_col': 'RSI_Regular_Bullish',
            'hidden_bull_col': 'RSI_Hidden_Bullish',
            'regular_bear_col': 'RSI_Regular_Bearish',
            'hidden_bear_col': 'RSI_Hidden_Bearish',
            'regular_shape': 'square',
            'hidden_shape': 'circle',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        },
        {
            'name': 'Stochastic',
            'regular_bull_col': 'Stochastic_Regular_Bullish',
            'hidden_bull_col': 'Stochastic_Hidden_Bullish',
            'regular_bear_col': 'Stochastic_Regular_Bearish',
            'hidden_bear_col': 'Stochastic_Hidden_Bearish',
            'regular_shape': 'square',
            'hidden_shape': 'circle',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        },
        {
            'name': 'MFI',
            'regular_bull_col': 'MFI_Regular_Bullish',
            'hidden_bull_col': 'MFI_Hidden_Bullish',
            'regular_bear_col': 'MFI_Regular_Bearish',
            'hidden_bear_col': 'MFI_Hidden_Bearish',
            'regular_shape': 'square',
            'hidden_shape': 'circle',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        },
        {
            'name': 'Fractal',
            'regular_bull_col': 'Fractal_Bullish',
            'regular_bear_col': 'Fractal_Bearish',
            'regular_shape': 'square',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        },
        {
            'name': 'MACD',
            'regular_bull_col': 'MACD_Regular_Bullish',
            'hidden_bull_col': 'MACD_Hidden_Bullish',
            'regular_bear_col': 'MACD_Regular_Bearish',
            'hidden_bear_col': 'MACD_Hidden_Bearish',
            'regular_shape': 'square',
            'hidden_shape': 'circle',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        },
        {
            'name': 'OBV',
            'regular_bull_col': 'OBV_Regular_Bullish',
            'hidden_bull_col': 'OBV_Hidden_Bullish',
            'regular_bear_col': 'OBV_Regular_Bearish',
            'hidden_bear_col': 'OBV_Hidden_Bearish',
            'regular_shape': 'square',
            'hidden_shape': 'circle',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        },
        {
            'name': 'Fisher',
            'regular_bull_col': 'Fisher_Regular_Bullish',
            'hidden_bull_col': 'Fisher_Hidden_Bullish',
            'regular_bear_col': 'Fisher_Regular_Bearish',
            'hidden_bear_col': 'Fisher_Hidden_Bearish',
            'regular_shape': 'square',
            'hidden_shape': 'circle',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        },
        {
            'name': 'Vortex',
            'regular_bull_col': 'VI_Regular_Bullish',
            'hidden_bull_col': 'VI_Hidden_Bullish',
            'regular_bear_col': 'VI_Regular_Bearish',
            'hidden_bear_col': 'VI_Hidden_Bearish',
            'regular_shape': 'square',
            'hidden_shape': 'circle',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        },
        {
            'name': 'Momentum',
            'regular_bull_col': 'Momo_Regular_Bullish',
            'hidden_bull_col': 'Momo_Hidden_Bullish',
            'regular_bear_col': 'Momo_Regular_Bearish',
            'hidden_bear_col': 'Momo_Hidden_Bearish',
            'regular_shape': 'square',
            'hidden_shape': 'circle',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        },
        {
            'name': 'Volume',
            'regular_bull_col': 'Vol_Regular_Bullish',
            'hidden_bull_col': 'Vol_Hidden_Bullish',
            'regular_bear_col': 'Vol_Regular_Bearish',
            'hidden_bear_col': 'Vol_Hidden_Bearish',
            'regular_shape': 'square',
            'hidden_shape': 'circle',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        },
        {
            'name': 'ATR',
            'regular_bull_col': 'ATR_Regular_Bullish',
            'hidden_bull_col': 'ATR_Hidden_Bullish',
            'regular_bear_col': 'ATR_Regular_Bearish',
            'hidden_bear_col': 'ATR_Hidden_Bearish',
            'regular_shape': 'square',
            'hidden_shape': 'circle',
            'bull_color': colors['teal'],
            'bear_color': colors['red']
        }
    ]

    markers = []

    for div in divergence_types:
        # Regular bullish
        if div.get('regular_bull_col') in df.columns:
            reg_bull_mask = df[div['regular_bull_col']].fillna(False).astype(bool)
            for _, row in df[reg_bull_mask].iterrows():
                markers.append({
                    'time': row['time'],
                    'position': 'below',
                    'shape': div['regular_shape'],
                    'color': div['bull_color'],
                    'text': ''
                })

        # Hidden bullish
        if div.get('hidden_bull_col') in df.columns:
            hid_bull_mask = df[div['hidden_bull_col']].fillna(False).astype(bool)
            for _, row in df[hid_bull_mask].iterrows():
                markers.append({
                    'time': row['time'],
                    'position': 'below',
                    'shape': div['hidden_shape'],
                    'color': div['bull_color'],
                    'text': ''
                })

        # Regular bearish
        if div.get('regular_bear_col') in df.columns:
            reg_bear_mask = df[div['regular_bear_col']].fillna(False).astype(bool)
            for _, row in df[reg_bear_mask].iterrows():
                markers.append({
                    'time': row['time'],
                    'position': 'above',
                    'shape': div['regular_shape'],
                    'color': div['bear_color'],
                    'text': ''
                })

        # Hidden bearish
        if div.get('hidden_bear_col') in df.columns:
            hid_bear_mask = df[div['hidden_bear_col']].fillna(False).astype(bool)
            for _, row in df[hid_bear_mask].iterrows():
                markers.append({
                    'time': row['time'],
                    'position': 'above',
                    'shape': div['hidden_shape'],
                    'color': div['bear_color'],
                    'text': ''
                })

    if markers:
        subchart.marker_list(sorted(markers, key=lambda x: x['time']))
