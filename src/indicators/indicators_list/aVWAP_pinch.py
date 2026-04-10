import pandas as pd
from src.indicators.indicators import get_indicators
from src.indicators.indicators_list.aVWAP import calculate_avwap


def calculate_avwap_pinch(
    df,
    anchor_type='peak',         # 'peak' or 'valley' — the main anchor type
    anchor_periods=100,         # Lookback for anchor detection (larger = fewer, more significant anchors)
    anchor_max_aVWAPs=1,               # Number of most recent anchors to show
    counterpart_periods=20,     # Lookback for counterpart detection (smaller = more sensitive)
    counterpart_max_aVWAPs=3,          # Number of counterpart structure points per anchor
):
    """
    Calculate aVWAP pinch pairs.

    For each anchor (peak or valley), finds the most extreme counterpart
    structure points occurring after it and calculates an aVWAP from each.

      anchor_type='peak'   → anchor at detected peak,    counterparts at N lowest valleys after it
      anchor_type='valley' → anchor at detected valley,  counterparts at N highest peaks after it

    The aVWAPs in each pair converge (pinch) to form support or resistance zones.

    Parameters:
        anchor_type         : 'peak' or 'valley'
        anchor_periods      : Rolling lookback for anchor detection
        anchor_max_aVWAPs          : Number of most recent anchors to include (None = all)
        counterpart_periods : Rolling lookback for counterpart detection (independent of anchor)
        counterpart_max_aVWAPs     : Number of counterpart structure points per anchor

    Output columns:
        aVWAP_peak_{idx}   — aVWAP anchored at a detected peak
        aVWAP_valley_{idx} — aVWAP anchored at a counterpart valley (and vice versa)
    """

    df = df.reset_index()
    df['date'] = pd.to_datetime(df['date'])

    base_cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume', 'date'] if c in df.columns]

    # Detect anchors with anchor_periods
    anchor_df = get_indicators(
        df[base_cols].copy(),
        ['peaks_valleys'],
        {'peaks_valleys': {'periods': anchor_periods}}
    )

    # Detect counterparts with counterpart_periods (typically smaller)
    counter_df = get_indicators(
        df[base_cols].copy(),
        ['peaks_valleys'],
        {'peaks_valleys': {'periods': counterpart_periods}}
    )

    peak_indices          = anchor_df[anchor_df['Peaks']     == 1].index.tolist() if 'Peaks'   in anchor_df.columns else []
    valley_indices        = anchor_df[anchor_df['Valleys']   == 1].index.tolist() if 'Valleys' in anchor_df.columns else []
    counter_peak_indices  = counter_df[counter_df['Peaks']   == 1].index.tolist() if 'Peaks'   in counter_df.columns else []
    counter_valley_indices= counter_df[counter_df['Valleys'] == 1].index.tolist() if 'Valleys' in counter_df.columns else []

    if anchor_type == 'peak':
        main_indices      = sorted(peak_indices, reverse=True)   # Most recent first
        counter_pool      = counter_valley_indices
        find_counterparts = _find_lowest_valleys
        main_label, counter_label = 'peak', 'valley'
    else:
        main_indices      = sorted(valley_indices, reverse=True)
        counter_pool      = counter_peak_indices
        find_counterparts = _find_highest_peaks
        main_label, counter_label = 'valley', 'peak'

    if anchor_max_aVWAPs is not None:
        main_indices = main_indices[:anchor_max_aVWAPs]

    result = {}

    for anchor_idx in main_indices:
        # Main aVWAP (deduplicated — multiple pairs may share an anchor)
        main_key = f'aVWAP_{main_label}_{anchor_idx}'
        if main_key not in result:
            result[main_key] = calculate_avwap(df, anchor_idx)

        # Counterparts: N most extreme opposite structure points after this anchor
        counter_indices = find_counterparts(df, counter_pool, anchor_idx, counterpart_max_aVWAPs)
        for counter_idx in counter_indices:
            counter_key = f'aVWAP_{counter_label}_{counter_idx}'
            if counter_key not in result:
                result[counter_key] = calculate_avwap(df, counter_idx)

    # Assign each Series (RangeIndex) as columns on df, then return a DataFrame
    # with DatetimeIndex so get_indicators can concat it correctly with result_df.
    for key, series in result.items():
        df[key] = series

    avwap_cols = list(result.keys())
    df.set_index('date', inplace=True)
    return df[avwap_cols] if avwap_cols else df[[]]


def _find_lowest_valleys(df, valley_indices, after_idx, max_counterparts):
    """
    Among detected valleys occurring after after_idx, return the indices of the
    N lowest by Low price. Falls back to the N absolute lowest Low bars if no
    detected valleys exist past the anchor.
    """
    candidates = [i for i in valley_indices if i > after_idx]
    if candidates:
        return sorted(candidates, key=lambda i: df.loc[i, 'Low'])[:max_counterparts]
    sub = df.iloc[after_idx + 1:]
    if sub.empty:
        return []
    return [int(i) for i in sub['Low'].nsmallest(max_counterparts).index]


def _find_highest_peaks(df, peak_indices, after_idx, max_counterparts):
    """
    Among detected peaks occurring after after_idx, return the indices of the
    N highest by High price. Falls back to the N absolute highest High bars if no
    detected peaks exist past the anchor.
    """
    candidates = [i for i in peak_indices if i > after_idx]
    if candidates:
        return sorted(candidates, key=lambda i: df.loc[i, 'High'], reverse=True)[:max_counterparts]
    sub = df.iloc[after_idx + 1:]
    if sub.empty:
        return []
    return [int(i) for i in sub['High'].nlargest(max_counterparts).index]


def calculate_indicator(df, **params):
    return calculate_avwap_pinch(df, **params)
