import pandas as pd
import numpy as np
from src.indicators.indicators import get_indicators

def calculate_avwap_channel(df,
                            peaks_valleys=False,
                            peaks_valleys_avg=False,
                            peaks_avg=False,
                            valleys_avg=False,
                            gaps=False, 
                            gaps_avg=False,
                            OB=False,
                            OB_avg=False,
                            BoS_CHoCH=False,
                            BoS_CHoCH_avg=False,
                            All_avg=False,
                            peaks_valleys_params=None,
                            gaps_params=None,
                            OB_params=None,
                            BoS_CHoCH_params=None,
                            avg_lookback=25,
                            # Individual average lookbacks (None = use avg_lookback)
                            peaks_valleys_avg_lookback=None,
                            peaks_avg_lookback=None,
                            valleys_avg_lookback=None,
                            gaps_avg_lookback=None,
                            OB_avg_lookback=None,
                            BoS_CHoCH_avg_lookback=None,
                            All_avg_lookback=None,
                            # Extra
                            keep_OB_column=False,
                            aVWAP_channel=False):
    """
    Calculate anchored VWAP channels from market structure points.

    Parameters:
        peaks_valleys: Calculate aVWAPs from ALL peaks and valleys
        peaks_valleys_avg: Calculate rolling avg of peaks+valleys aVWAPs
        peaks_avg: Calculate rolling avg of ONLY peaks aVWAPs
        valleys_avg: Calculate rolling avg of ONLY valleys aVWAPs
        gaps: Calculate aVWAPs from gap up/down points
        gaps_avg: Calculate rolling avg of gap aVWAPs
        OB: Calculate aVWAPs from Order Blocks (OB)
        OB_avg: Calculate rolling avg of OB aVWAPs
        BoS_CHoCH: Calculate aVWAPs from BoS/CHoCH ranges
        BoS_CHoCH_avg: Calculate rolling avg of BoS/CHoCH aVWAPs
        All_avg: Calculate rolling avg of ALL aVWAP types
        peaks_valleys_params: {'periods': 25, 'max_aVWAPs': None}
        gaps_params: {'max_aVWAPs': None}
        OB_params: {'periods': 25, 'max_aVWAPs': None, 'include_bullish': True, 'include_bearish': True}
        BoS_CHoCH_params: {'swing_length': 25, 'max_aVWAPs': None}
        avg_lookback: Default number of recent aVWAPs to include in averages
        peaks_valleys_avg_lookback: Lookback for peaks_valleys_avg (None = use avg_lookback)
        peaks_avg_lookback: Lookback for peaks_avg (None = use avg_lookback)
        valleys_avg_lookback: Lookback for valleys_avg (None = use avg_lookback)
        gaps_avg_lookback: Lookback for gaps_avg (None = use avg_lookback)
        OB_avg_lookback: Lookback for OB_avg (None = use avg_lookback)
        BoS_CHoCH_avg_lookback: Lookback for BoS_CHoCH_avg (None = use avg_lookback)
        All_avg_lookback: Lookback for All_avg (None = use avg_lookback)
        keep_OB_column: Keep raw OB detection columns in output
        aVWAP_channel: Channel mode - only use anchors after highest/lowest points
    """
    # Set default parameters if not provided
    if peaks_valleys_params is None:
        peaks_valleys_params = {'periods': 25, 'max_aVWAPs': None}
    if gaps_params is None:
        gaps_params = {'max_aVWAPs': None}
    if OB_params is None:
        OB_params = {
            'periods': 25, 
            'max_aVWAPs': None,
            'include_bullish': True,
            'include_bearish': True
        }
    if BoS_CHoCH_params is None:
        BoS_CHoCH_params = {
            'swing_length': 25,
            'max_aVWAPs': None
        }

    # Get indicators based on input parameters
    aVWAP_anchors = []
    if peaks_valleys or peaks_valleys_avg or peaks_avg or valleys_avg or All_avg: 
        aVWAP_anchors.append('peaks_valleys')
    if gaps or gaps_avg or All_avg: 
        aVWAP_anchors.append('gaps')
    if OB or OB_avg or All_avg: 
        aVWAP_anchors.append('OB')
    if BoS_CHoCH or BoS_CHoCH_avg or All_avg:
        aVWAP_anchors.append('BoS_CHoCH')

    if not aVWAP_anchors:
        return {}

    params = {}
    if peaks_valleys or peaks_valleys_avg or peaks_avg or valleys_avg or All_avg: 
        params['peaks_valleys'] = {'periods': peaks_valleys_params['periods']}
    if gaps or gaps_avg or All_avg: 
        params['gaps'] = {}
    if OB or OB_avg or All_avg: 
        params['OB'] = {'periods': OB_params['periods']}
    if BoS_CHoCH or BoS_CHoCH_avg or All_avg:
        params['BoS_CHoCH'] = {'swing_length': BoS_CHoCH_params['swing_length']}

    df = get_indicators(df, aVWAP_anchors, params)
    df = df.reset_index()
    df['date'] = pd.to_datetime(df['date'])

    # Initialize storage dictionaries
    peaks_valleys_aVWAPs = {}
    peaks_only_aVWAPs = {}
    valleys_only_aVWAPs = {}
    gaps_aVWAPs = {}
    OB_aVWAPs = {}
    BoS_CHoCH_aVWAPs = {}

    # Track extreme points for channel calculation
    highest_peak_idx = None
    lowest_valley_idx = None

    def process_anchors(indices, prefix, storage_dict, max_count=None):
        if not indices:
            return
        sorted_indices = sorted(indices, reverse=True)
        if max_count is not None:
            sorted_indices = sorted_indices[:max_count]
        for i in sorted_indices:
            storage_dict[f'{prefix}_{i}'] = calculate_avwap(df, i)

    # Process peaks and valleys
    if peaks_valleys or peaks_valleys_avg or peaks_avg or valleys_avg or All_avg:
        peaks_indices = df[df['Peaks'] == 1].index.tolist() if 'Peaks' in df.columns else []
        valleys_indices = df[df['Valleys'] == 1].index.tolist() if 'Valleys' in df.columns else []
       
        if aVWAP_channel:
            if peaks_indices:
                peak_prices = df.loc[peaks_indices, 'High']
                highest_peak_idx = peaks_indices[peak_prices.argmax()]
                peaks_indices = [i for i in peaks_indices if i >= highest_peak_idx]
           
            if valleys_indices:
                valley_prices = df.loc[valleys_indices, 'Low']
                lowest_valley_idx = valleys_indices[valley_prices.argmin()]
                valleys_indices = [i for i in valleys_indices if i >= lowest_valley_idx]
       
        process_anchors(peaks_indices, 'aVWAP_peak', peaks_only_aVWAPs, 
                       peaks_valleys_params.get('max_aVWAPs'))
        process_anchors(valleys_indices, 'aVWAP_valley', valleys_only_aVWAPs, 
                       peaks_valleys_params.get('max_aVWAPs'))
       
        peaks_valleys_aVWAPs = {**peaks_only_aVWAPs, **valleys_only_aVWAPs}

        if peaks_valleys_avg and peaks_valleys_aVWAPs:
            lookback = peaks_valleys_avg_lookback if peaks_valleys_avg_lookback is not None else avg_lookback
            if aVWAP_channel:
                if highest_peak_idx is not None and lowest_valley_idx is not None:
                    first_valid_idx = max(highest_peak_idx, lowest_valley_idx)
                    temp_avg = calculate_rolling_aVWAP_avg(df, peaks_valleys_aVWAPs, lookback)
                    df['Peaks_Valleys_avg'] = temp_avg.where(df.index >= first_valid_idx)
                else:
                    df['Peaks_Valleys_avg'] = np.nan
            else:
                df['Peaks_Valleys_avg'] = calculate_rolling_aVWAP_avg(df, peaks_valleys_aVWAPs, lookback)

    # Process gaps
    if gaps or gaps_avg or All_avg:
        gap_up_indices = df[df['Gap_Up'] == 1].index.tolist() if 'Gap_Up' in df.columns else []
        gap_down_indices = df[df['Gap_Down'] == 1].index.tolist() if 'Gap_Down' in df.columns else []
       
        process_anchors(gap_up_indices, 'Gap_Up_aVWAP', gaps_aVWAPs, 
                       gaps_params.get('max_aVWAPs'))
        process_anchors(gap_down_indices, 'Gap_Down_aVWAP', gaps_aVWAPs, 
                       gaps_params.get('max_aVWAPs'))

    # Process OBs
    if OB or OB_avg or All_avg:
        OB_bull_indices = []
        OB_bear_indices = []
       
        if 'OB' in df.columns:
            if aVWAP_channel:
                if lowest_valley_idx is not None:
                    OB_bull_indices = df[(df['OB'] == 1) & (df.index >= lowest_valley_idx)].index.tolist()
                if highest_peak_idx is not None:
                    OB_bear_indices = df[(df['OB'] == -1) & (df.index >= highest_peak_idx)].index.tolist()
            else:
                OB_bull_indices = df[df['OB'] == 1].index.tolist() if OB_params.get('include_bullish', True) else []
                OB_bear_indices = df[df['OB'] == -1].index.tolist() if OB_params.get('include_bearish', True) else []
       
        process_anchors(OB_bull_indices, 'aVWAP_OB_bull', OB_aVWAPs, 
                       OB_params.get('max_aVWAPs'))
        process_anchors(OB_bear_indices, 'aVWAP_OB_bear', OB_aVWAPs, 
                       OB_params.get('max_aVWAPs'))

    # Process BoS/CHoCH ranges
    if BoS_CHoCH or BoS_CHoCH_avg or All_avg:
        def process_BoS_CHoCH_range(signal_idx, break_idx, signal_type):
            """Calculate VWAP from extreme point in signal→break range"""
            if pd.isna(break_idx) or break_idx <= signal_idx:
                return None
               
            range_df = df.iloc[signal_idx:break_idx+1]
           
            if signal_type == 'bullish':
                # Find lowest low in range for bullish signals
                extreme_idx = range_df['Low'].idxmin()
            else:  # bearish
                # Find highest high in range for bearish signals
                extreme_idx = range_df['High'].idxmax()
           
            return calculate_avwap(df, extreme_idx)

        # Process bullish signals (BoS=1 or CHoCH=1)
        bullish_signals = df[(df['BoS'] == 1) | (df['CHoCH'] == 1)].index
        for idx in bullish_signals:
            break_idx = int(df.loc[idx, 'BoS_CHoCH_Break_Index']) if not pd.isna(df.loc[idx, 'BoS_CHoCH_Break_Index']) else None
            if break_idx:
                vwap = process_BoS_CHoCH_range(idx, break_idx, 'bullish')
                if vwap is not None:
                    BoS_CHoCH_aVWAPs[f'aVWAP_BoS_CHoCH_bull_{idx}'] = vwap
       
        # Process bearish signals (BoS=-1 or CHoCH=-1)
        bearish_signals = df[(df['BoS'] == -1) | (df['CHoCH'] == -1)].index
        for idx in bearish_signals:
            break_idx = int(df.loc[idx, 'BoS_CHoCH_Break_Index']) if not pd.isna(df.loc[idx, 'BoS_CHoCH_Break_Index']) else None
            if break_idx:
                vwap = process_BoS_CHoCH_range(idx, break_idx, 'bearish')
                if vwap is not None:
                    BoS_CHoCH_aVWAPs[f'aVWAP_BoS_CHoCH_bear_{idx}'] = vwap

    all_aVWAPs = {**peaks_valleys_aVWAPs, **gaps_aVWAPs, **OB_aVWAPs, **BoS_CHoCH_aVWAPs}

    if not all_aVWAPs: 
        return {}

    df = pd.concat([df, pd.DataFrame(all_aVWAPs)], axis=1)

    # Calculate averages with type-specific lookbacks
    if peaks_avg and peaks_only_aVWAPs:
        lookback = peaks_avg_lookback if peaks_avg_lookback is not None else avg_lookback
        df['Peaks_avg'] = calculate_rolling_aVWAP_avg(df, peaks_only_aVWAPs, lookback)
   
    if valleys_avg and valleys_only_aVWAPs:
        lookback = valleys_avg_lookback if valleys_avg_lookback is not None else avg_lookback
        df['Valleys_avg'] = calculate_rolling_aVWAP_avg(df, valleys_only_aVWAPs, lookback)

    if peaks_valleys_avg and peaks_valleys_aVWAPs:
        lookback = peaks_valleys_avg_lookback if peaks_valleys_avg_lookback is not None else avg_lookback
        df['Peaks_Valleys_avg'] = calculate_rolling_aVWAP_avg(df, peaks_valleys_aVWAPs, lookback)

    if gaps_avg and gaps_aVWAPs:                   
        lookback = gaps_avg_lookback if gaps_avg_lookback is not None else avg_lookback
        df['Gaps_avg'] = calculate_rolling_aVWAP_avg(df, gaps_aVWAPs, lookback)

    if OB_avg and OB_aVWAPs:                       
        lookback = OB_avg_lookback if OB_avg_lookback is not None else avg_lookback
        df['OB_avg'] = calculate_rolling_aVWAP_avg(df, OB_aVWAPs, lookback)

    if BoS_CHoCH_avg and BoS_CHoCH_aVWAPs:
        lookback = BoS_CHoCH_avg_lookback if BoS_CHoCH_avg_lookback is not None else avg_lookback
        df['BoS_CHoCH_avg'] = calculate_rolling_aVWAP_avg(df, BoS_CHoCH_aVWAPs, lookback)

    if All_avg and all_aVWAPs:
        lookback = All_avg_lookback if All_avg_lookback is not None else avg_lookback
        df['All_avg'] = calculate_rolling_aVWAP_avg(df, all_aVWAPs, lookback)

    # Format output
    cols_to_drop = ['Open', 'Close', 'High', 'Low', 'Volume']
    if peaks_valleys or peaks_valleys_avg or peaks_avg or valleys_avg or All_avg:
        cols_to_drop.extend(['Valleys', 'Peaks'])
    if gaps or gaps_avg or All_avg:
        cols_to_drop.extend(['Gap_Up', 'Gap_Down'])
    if not keep_OB_column:
        cols_to_drop.extend(['OB', 'OB_High', 'OB_Low', 'OB_Mitigated_Index'])
    if BoS_CHoCH or BoS_CHoCH_avg:
        cols_to_drop.extend(['BoS', 'CHoCH', 'BoS_CHoCH_Price', 'BoS_CHoCH_Break_Index'])

    df = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
    df.set_index('date', inplace=True)

    # Prepare results
    result_dict = {}
    if peaks_valleys and peaks_valleys_aVWAPs:
        result_dict.update({col: df[col] for col in peaks_valleys_aVWAPs})
    if gaps and gaps_aVWAPs:
        result_dict.update({col: df[col] for col in gaps_aVWAPs})
    if OB and OB_aVWAPs:
        if OB_params.get('include_bullish', True):
            bull_cols = [col for col in OB_aVWAPs if col.startswith('aVWAP_OB_bull')]
            result_dict.update({col: df[col] for col in bull_cols})
        if OB_params.get('include_bearish', True):
            bear_cols = [col for col in OB_aVWAPs if col.startswith('aVWAP_OB_bear')]
            result_dict.update({col: df[col] for col in bear_cols})
    if BoS_CHoCH and BoS_CHoCH_aVWAPs:
        bull_cols = [col for col in BoS_CHoCH_aVWAPs if col.startswith('aVWAP_BoS_CHoCH_bull')]
        result_dict.update({col: df[col] for col in bull_cols})
        bear_cols = [col for col in BoS_CHoCH_aVWAPs if col.startswith('aVWAP_BoS_CHoCH_bear')]
        result_dict.update({col: df[col] for col in bear_cols})
       
    if keep_OB_column:
        result_dict.update({
            'OB': df['OB'],
            'OB_High': df['OB_High'],
            'OB_Low': df['OB_Low'],
            'OB_Mitigated_Index': df['OB_Mitigated_Index']
        })

    # Add averages
    avg_columns = [
        ('Peaks_Valleys_avg', peaks_valleys_avg),
        ('Peaks_avg', peaks_avg),
        ('Valleys_avg', valleys_avg),
        ('Gaps_avg', gaps_avg),
        ('OB_avg', OB_avg),
        ('BoS_CHoCH_avg', BoS_CHoCH_avg),
        ('All_avg', All_avg)
    ]
   
    for col, flag in avg_columns:
        if flag and col in df.columns:
            result_dict[col] = df[col]

    return result_dict

def calculate_indicator(df, **params):
    return calculate_avwap_channel(df, **params)

def calculate_avwap(df, anchor_index):
    """Calculate anchored VWAP from anchor point"""
    df_anchored = df.iloc[anchor_index:].copy()
    df_anchored['cumulative_volume'] = df_anchored['Volume'].cumsum()
    df_anchored['cumulative_volume_price'] = (df_anchored['Volume'] * 
        (df_anchored['High'] + df_anchored['Low'] + df_anchored['Close']) / 3).cumsum()
    return df_anchored['cumulative_volume_price'] / df_anchored['cumulative_volume']

def calculate_rolling_aVWAP_avg(df, aVWAP_dict, lookback=None):
    """Calculate average of aVWAP values"""
    aVWAP_df = pd.DataFrame(aVWAP_dict)
    sorted_cols = sorted(aVWAP_df.columns, key=lambda x: int(x.split('_')[-1]), reverse=True)
    aVWAP_df = aVWAP_df[sorted_cols]
   
    avg_values = pd.Series(np.nan, index=df.index)
    for idx in aVWAP_df.index.intersection(df.index):
        valid_vals = aVWAP_df.loc[idx].dropna()
        if lookback is not None:
            valid_vals = valid_vals[:lookback]
        if len(valid_vals) > 0:
            avg_values.loc[idx] = valid_vals.mean()
    return avg_values




# import pandas as pd
# import numpy as np
# from src.indicators.indicators import get_indicators
#
# def calculate_avwap_channel(df,
#                             peaks_valleys=False,
#                             peaks_valleys_avg=False,
#                             peaks_avg=False,
#                             valleys_avg=False,
#                             gaps=False, 
#                             gaps_avg=False,
#                             OB=False,
#                             OB_avg=False,
#                             BoS_CHoCH=False,
#                             BoS_CHoCH_avg=False,
#                             All_avg=False,
#                             peaks_valleys_params=None,  # Can be dict or list of dicts
#                             gaps_params=None,           # Can be dict or list of dicts
#                             OB_params=None,             # Can be dict or list of dicts
#                             BoS_CHoCH_params=None,      # Can be dict or list of dicts
#                             avg_lookback=25,            # Default lookback
#                             keep_OB_column=False,
#                             aVWAP_channel=False):
#     """
#     Calculate anchored VWAP channels from market structure points.
#   
#     Now supports multiple configurations by passing lists of parameter dictionaries.
#     Each configuration will produce its own set of output columns with the same base names
#     (e.g., Peaks_Valleys_avg, Peaks_Valleys_avg_1, Peaks_Valleys_avg_2, etc.)
#   
#     Parameters:
#         peaks_valleys: Calculate aVWAPs from ALL peaks and valleys
#         peaks_valleys_avg: Calculate rolling avg of peaks+valleys aVWAPs
#         peaks_avg: Calculate rolling avg of ONLY peaks aVWAPs
#         valleys_avg: Calculate rolling avg of ONLY valleys aVWAPs
#         gaps: Calculate aVWAPs from gap up/down points
#         gaps_avg: Calculate rolling avg of gap aVWAPs
#         OB: Calculate aVWAPs from Order Blocks (OB)
#         OB_avg: Calculate rolling avg of OB aVWAPs
#         BoS_CHoCH: Calculate aVWAPs from BoS/CHoCH ranges
#         BoS_CHoCH_avg: Calculate rolling avg of BoS/CHoCH aVWAPs
#         All_avg: Calculate rolling avg of ALL aVWAP types
#         peaks_valleys_params: Dict or list of dicts with keys:
#             - 'periods': int (default 25)
#             - 'max_aVWAPs': int or None (default None)
#             - 'avg_lookback': int (optional, for peaks_valleys_avg)
#             - 'peaks_avg_lookback': int (optional, for peaks_avg)
#             - 'valleys_avg_lookback': int (optional, for valleys_avg)
#         gaps_params: Dict or list of dicts with keys:
#             - 'max_aVWAPs': int or None (default None)
#             - 'avg_lookback': int (optional, for gaps_avg)
#         OB_params: Dict or list of dicts with keys:
#             - 'periods': int (default 25)
#             - 'max_aVWAPs': int or None (default None)
#             - 'include_bullish': bool (default True)
#             - 'include_bearish': bool (default True)
#             - 'avg_lookback': int (optional, for OB_avg)
#         BoS_CHoCH_params: Dict or list of dicts with keys:
#             - 'swing_length': int (default 25)
#             - 'max_aVWAPs': int or None (default None)
#             - 'avg_lookback': int (optional, for BoS_CHoCH_avg)
#         avg_lookback: Default lookback for all averages (fallback)
#         keep_OB_column: Keep raw OB detection columns in output
#         aVWAP_channel: Channel mode - only use anchors after highest/lowest points
#     """
#   
#     # Helper to ensure we're working with lists of configs
#     def ensure_config_list(param, default_dict):
#         """Convert param to list of config dicts"""
#         if param is None:
#             return [default_dict.copy()]
#         if isinstance(param, list):
#             return param
#         return [param]
#   
#     # Default dictionaries
#     default_peaks_valleys = {'periods': 25, 'max_aVWAPs': None}
#     default_gaps = {'max_aVWAPs': None}
#     default_OB = {
#         'periods': 25, 
#         'max_aVWAPs': None,
#         'include_bullish': True,
#         'include_bearish': True
#     }
#     default_BoS_CHoCH = {
#         'swing_length': 25,
#         'max_aVWAPs': None
#     }
#   
#     # Convert all params to lists of configs
#     peaks_valleys_configs = ensure_config_list(peaks_valleys_params, default_peaks_valleys)
#     gaps_configs = ensure_config_list(gaps_params, default_gaps)
#     OB_configs = ensure_config_list(OB_params, default_OB)
#     BoS_CHoCH_configs = ensure_config_list(BoS_CHoCH_params, default_BoS_CHoCH)
#   
#     # Determine which anchor types we need (use max periods from all configs)
#     needed_anchors = set()
#   
#     if peaks_valleys or peaks_valleys_avg or peaks_avg or valleys_avg or All_avg:
#         needed_anchors.add('peaks_valleys')
#     if gaps or gaps_avg or All_avg:
#         needed_anchors.add('gaps')
#     if OB or OB_avg or All_avg:
#         needed_anchors.add('OB')
#     if BoS_CHoCH or BoS_CHoCH_avg or All_avg:
#         needed_anchors.add('BoS_CHoCH')
#   
#     if not needed_anchors:
#         return {}
#   
#     # Build params for get_indicators (use max values from all configs)
#     indicator_params = {}
#   
#     if 'peaks_valleys' in needed_anchors:
#         max_periods = max([cfg.get('periods', 25) for cfg in peaks_valleys_configs])
#         indicator_params['peaks_valleys'] = {'periods': max_periods}
#   
#     if 'gaps' in needed_anchors:
#         indicator_params['gaps'] = {}
#   
#     if 'OB' in needed_anchors:
#         max_periods = max([cfg.get('periods', 25) for cfg in OB_configs])
#         indicator_params['OB'] = {'periods': max_periods}
#   
#     if 'BoS_CHoCH' in needed_anchors:
#         max_swing = max([cfg.get('swing_length', 25) for cfg in BoS_CHoCH_configs])
#         indicator_params['BoS_CHoCH'] = {'swing_length': max_swing}
#   
#     # Get base indicators
#     df = get_indicators(df, list(needed_anchors), indicator_params)
#     df = df.reset_index()
#     df['date'] = pd.to_datetime(df['date'])
#   
#     # Track extreme points for channel calculation
#     highest_peak_idx = None
#     lowest_valley_idx = None
#   
#     if aVWAP_channel and ('peaks_valleys' in needed_anchors):
#         peaks_indices = df[df['Peaks'] == 1].index.tolist() if 'Peaks' in df.columns else []
#         valleys_indices = df[df['Valleys'] == 1].index.tolist() if 'Valleys' in df.columns else []
#       
#         if peaks_indices:
#             peak_prices = df.loc[peaks_indices, 'High']
#             highest_peak_idx = peaks_indices[peak_prices.argmax()]
#       
#         if valleys_indices:
#             valley_prices = df.loc[valleys_indices, 'Low']
#             lowest_valley_idx = valleys_indices[valley_prices.argmin()]
#   
#     def process_anchors(indices, prefix, max_count=None):
#         """Process anchors and return dictionary of aVWAP series"""
#         if not indices:
#             return {}
#       
#         sorted_indices = sorted(indices, reverse=True)
#         if max_count is not None:
#             sorted_indices = sorted_indices[:max_count]
#       
#         result = {}
#         for i in sorted_indices:
#             result[f'{prefix}_{i}'] = calculate_avwap(df, i)
#       
#         return result
#   
#     # Process each configuration and collect results
#     all_results = {}
#   
#     # 1. Process peaks_valleys configurations
#     if peaks_valleys or peaks_valleys_avg or peaks_avg or valleys_avg or All_avg:
#         base_peaks_indices = df[df['Peaks'] == 1].index.tolist() if 'Peaks' in df.columns else []
#         base_valleys_indices = df[df['Valleys'] == 1].index.tolist() if 'Valleys' in df.columns else []
#       
#         for config_idx, config in enumerate(peaks_valleys_configs):
#             periods = config.get('periods', 25)
#             max_aVWAPs = config.get('max_aVWAPs', None)
#           
#             # Apply channel filtering if needed
#             peaks_indices = base_peaks_indices.copy()
#             valleys_indices = base_valleys_indices.copy()
#           
#             if aVWAP_channel:
#                 if highest_peak_idx is not None:
#                     peaks_indices = [i for i in peaks_indices if i >= highest_peak_idx]
#                 if lowest_valley_idx is not None:
#                     valleys_indices = [i for i in valleys_indices if i >= lowest_valley_idx]
#           
#             # Calculate aVWAPs for this config
#             peaks_aVWAPs = process_anchors(peaks_indices, 'aVWAP_peak', max_aVWAPs)
#             valleys_aVWAPs = process_anchors(valleys_indices, 'aVWAP_valley', max_aVWAPs)
#           
#             # Store individual aVWAPs if requested
#             if peaks_valleys:
#                 all_results.update(peaks_aVWAPs)
#                 all_results.update(valleys_aVWAPs)
#           
#             # Store peaks_only for peaks_avg calculation
#             if peaks_avg and peaks_aVWAPs:
#                 lookback = config.get('peaks_avg_lookback', avg_lookback)
#                 avg_name = 'Peaks_avg' if config_idx == 0 else f'Peaks_avg_{config_idx}'
#                 all_results[avg_name] = calculate_rolling_aVWAP_avg(df, peaks_aVWAPs, lookback)
#           
#             # Store valleys_only for valleys_avg calculation
#             if valleys_avg and valleys_aVWAPs:
#                 lookback = config.get('valleys_avg_lookback', avg_lookback)
#                 avg_name = 'Valleys_avg' if config_idx == 0 else f'Valleys_avg_{config_idx}'
#                 all_results[avg_name] = calculate_rolling_aVWAP_avg(df, valleys_aVWAPs, lookback)
#           
#             # Combined peaks_valleys for peaks_valleys_avg
#             if peaks_valleys_avg and (peaks_aVWAPs or valleys_aVWAPs):
#                 combined = {**peaks_aVWAPs, **valleys_aVWAPs}
#                 lookback = config.get('avg_lookback', avg_lookback)
#               
#                 if aVWAP_channel and highest_peak_idx is not None and lowest_valley_idx is not None:
#                     first_valid_idx = max(highest_peak_idx, lowest_valley_idx)
#                     temp_avg = calculate_rolling_aVWAP_avg(df, combined, lookback)
#                     avg_series = temp_avg.where(df.index >= first_valid_idx)
#                 else:
#                     avg_series = calculate_rolling_aVWAP_avg(df, combined, lookback)
#               
#                 avg_name = 'Peaks_Valleys_avg' if config_idx == 0 else f'Peaks_Valleys_avg_{config_idx}'
#                 all_results[avg_name] = avg_series
#   
#     # 2. Process gaps configurations
#     if gaps or gaps_avg or All_avg:
#         base_gap_up_indices = df[df['Gap_Up'] == 1].index.tolist() if 'Gap_Up' in df.columns else []
#         base_gap_down_indices = df[df['Gap_Down'] == 1].index.tolist() if 'Gap_Down' in df.columns else []
#       
#         for config_idx, config in enumerate(gaps_configs):
#             max_aVWAPs = config.get('max_aVWAPs', None)
#           
#             gap_up_aVWAPs = process_anchors(base_gap_up_indices, 'Gap_Up_aVWAP', max_aVWAPs)
#             gap_down_aVWAPs = process_anchors(base_gap_down_indices, 'Gap_Down_aVWAP', max_aVWAPs)
#           
#             if gaps:
#                 all_results.update(gap_up_aVWAPs)
#                 all_results.update(gap_down_aVWAPs)
#           
#             if gaps_avg and (gap_up_aVWAPs or gap_down_aVWAPs):
#                 combined = {**gap_up_aVWAPs, **gap_down_aVWAPs}
#                 lookback = config.get('avg_lookback', avg_lookback)
#                 avg_name = 'Gaps_avg' if config_idx == 0 else f'Gaps_avg_{config_idx}'
#                 all_results[avg_name] = calculate_rolling_aVWAP_avg(df, combined, lookback)
#   
#     # 3. Process OB configurations
#     if OB or OB_avg or All_avg:
#         for config_idx, config in enumerate(OB_configs):
#             max_aVWAPs = config.get('max_aVWAPs', None)
#             include_bullish = config.get('include_bullish', True)
#             include_bearish = config.get('include_bearish', True)
#           
#             OB_bull_indices = []
#             OB_bear_indices = []
#           
#             if 'OB' in df.columns:
#                 if aVWAP_channel:
#                     if lowest_valley_idx is not None and include_bullish:
#                         OB_bull_indices = df[(df['OB'] == 1) & (df.index >= lowest_valley_idx)].index.tolist()
#                     if highest_peak_idx is not None and include_bearish:
#                         OB_bear_indices = df[(df['OB'] == -1) & (df.index >= highest_peak_idx)].index.tolist()
#                 else:
#                     if include_bullish:
#                         OB_bull_indices = df[df['OB'] == 1].index.tolist()
#                     if include_bearish:
#                         OB_bear_indices = df[df['OB'] == -1].index.tolist()
#           
#             OB_bull_aVWAPs = process_anchors(OB_bull_indices, 'aVWAP_OB_bull', max_aVWAPs)
#             OB_bear_aVWAPs = process_anchors(OB_bear_indices, 'aVWAP_OB_bear', max_aVWAPs)
#           
#             if OB:
#                 all_results.update(OB_bull_aVWAPs)
#                 all_results.update(OB_bear_aVWAPs)
#           
#             if OB_avg and (OB_bull_aVWAPs or OB_bear_aVWAPs):
#                 combined = {**OB_bull_aVWAPs, **OB_bear_aVWAPs}
#                 lookback = config.get('avg_lookback', avg_lookback)
#                 avg_name = 'OB_avg' if config_idx == 0 else f'OB_avg_{config_idx}'
#                 all_results[avg_name] = calculate_rolling_aVWAP_avg(df, combined, lookback)
#   
#     # 4. Process BoS/CHoCH configurations
#     if BoS_CHoCH or BoS_CHoCH_avg or All_avg:
#         for config_idx, config in enumerate(BoS_CHoCH_configs):
#             max_aVWAPs = config.get('max_aVWAPs', None)
#           
#             def process_BoS_CHoCH_range(signal_idx, break_idx, signal_type):
#                 if pd.isna(break_idx) or break_idx <= signal_idx:
#                     return None
#                 range_df = df.iloc[signal_idx:break_idx+1]
#                 if signal_type == 'bullish':
#                     extreme_idx = range_df['Low'].idxmin()
#                 else:
#                     extreme_idx = range_df['High'].idxmax()
#                 return calculate_avwap(df, extreme_idx)
#           
#             BoS_aVWAPs = {}
#           
#             # Process bullish signals
#             bullish_signals = df[(df['BoS'] == 1) | (df['CHoCH'] == 1)].index
#             for idx in bullish_signals:
#                 break_idx = int(df.loc[idx, 'BoS_CHoCH_Break_Index']) if not pd.isna(df.loc[idx, 'BoS_CHoCH_Break_Index']) else None
#                 if break_idx:
#                     vwap = process_BoS_CHoCH_range(idx, break_idx, 'bullish')
#                     if vwap is not None:
#                         BoS_aVWAPs[f'aVWAP_BoS_CHoCH_bull_{idx}'] = vwap
#           
#             # Process bearish signals
#             bearish_signals = df[(df['BoS'] == -1) | (df['CHoCH'] == -1)].index
#             for idx in bearish_signals:
#                 break_idx = int(df.loc[idx, 'BoS_CHoCH_Break_Index']) if not pd.isna(df.loc[idx, 'BoS_CHoCH_Break_Index']) else None
#                 if break_idx:
#                     vwap = process_BoS_CHoCH_range(idx, break_idx, 'bearish')
#                     if vwap is not None:
#                         BoS_aVWAPs[f'aVWAP_BoS_CHoCH_bear_{idx}'] = vwap
#           
#             # Apply max_aVWAPs limit
#             if max_aVWAPs is not None and len(BoS_aVWAPs) > max_aVWAPs:
#                 sorted_keys = sorted(BoS_aVWAPs.keys(), 
#                                    key=lambda x: int(x.split('_')[-1]), 
#                                    reverse=True)[:max_aVWAPs]
#                 BoS_aVWAPs = {k: BoS_aVWAPs[k] for k in sorted_keys}
#           
#             if BoS_CHoCH:
#                 all_results.update(BoS_aVWAPs)
#           
#             if BoS_CHoCH_avg and BoS_aVWAPs:
#                 lookback = config.get('avg_lookback', avg_lookback)
#                 avg_name = 'BoS_CHoCH_avg' if config_idx == 0 else f'BoS_CHoCH_avg_{config_idx}'
#                 all_results[avg_name] = calculate_rolling_aVWAP_avg(df, BoS_aVWAPs, lookback)
#   
#     # 5. Process All_avg (combines all aVWAP types)
#     if All_avg:
#         # Collect all aVWAPs from all configs (excluding average lines)
#         all_aVWAPs = {}
#         for key, value in all_results.items():
#             if not any(key.startswith(prefix) for prefix in 
#                       ['Peaks_avg', 'Valleys_avg', 'Peaks_Valleys_avg', 
#                        'Gaps_avg', 'OB_avg', 'BoS_CHoCH_avg', 'All_avg']):
#                 all_aVWAPs[key] = value
#       
#         if all_aVWAPs:
#             # Use the maximum number of configs from any type
#             num_configs = max(len(peaks_valleys_configs), len(gaps_configs), 
#                             len(OB_configs), len(BoS_CHoCH_configs))
#           
#             for config_idx in range(num_configs):
#                 # Try to get lookback from corresponding config
#                 lookback = avg_lookback
#                 if config_idx < len(peaks_valleys_configs):
#                     lookback = peaks_valleys_configs[config_idx].get('avg_lookback', avg_lookback)
#                 elif config_idx < len(gaps_configs):
#                     lookback = gaps_configs[config_idx].get('avg_lookback', avg_lookback)
#                 elif config_idx < len(OB_configs):
#                     lookback = OB_configs[config_idx].get('avg_lookback', avg_lookback)
#                 elif config_idx < len(BoS_CHoCH_configs):
#                     lookback = BoS_CHoCH_configs[config_idx].get('avg_lookback', avg_lookback)
#               
#                 avg_name = 'All_avg' if config_idx == 0 else f'All_avg_{config_idx}'
#                 all_results[avg_name] = calculate_rolling_aVWAP_avg(df, all_aVWAPs, lookback)
#   
#     # Keep OB columns if requested
#     if keep_OB_column and 'OB' in df.columns:
#         all_results['OB'] = df['OB']
#         all_results['OB_High'] = df['OB_High']
#         all_results['OB_Low'] = df['OB_Low']
#         if 'OB_Mitigated_Index' in df.columns:
#             all_results['OB_Mitigated_Index'] = df['OB_Mitigated_Index']
#   
#     return all_results
#
# def calculate_indicator(df, **params):
#     return calculate_avwap_channel(df, **params)
#
# def calculate_avwap(df, anchor_index):
#     """Calculate anchored VWAP from anchor point"""
#     df_anchored = df.iloc[anchor_index:].copy()
#     df_anchored['cumulative_volume'] = df_anchored['Volume'].cumsum()
#     df_anchored['cumulative_volume_price'] = (df_anchored['Volume'] * 
#         (df_anchored['High'] + df_anchored['Low'] + df_anchored['Close']) / 3).cumsum()
#     return df_anchored['cumulative_volume_price'] / df_anchored['cumulative_volume']
#
# def calculate_rolling_aVWAP_avg(df, aVWAP_dict, lookback=None):
#     """Calculate average of aVWAP values"""
#     if not aVWAP_dict:
#         return pd.Series(np.nan, index=df.index)
#   
#     aVWAP_df = pd.DataFrame(aVWAP_dict)
#   
#     def extract_idx(col_name):
#         try:
#             return int(col_name.split('_')[-1])
#         except:
#             return 0
#   
#     sorted_cols = sorted(aVWAP_df.columns, key=extract_idx, reverse=True)
#     aVWAP_df = aVWAP_df[sorted_cols]
#   
#     avg_values = pd.Series(np.nan, index=df.index)
#     for idx in aVWAP_df.index.intersection(df.index):
#         valid_vals = aVWAP_df.loc[idx].dropna()
#         if lookback is not None:
#             valid_vals = valid_vals[:lookback]
#         if len(valid_vals) > 0:
#             avg_values.loc[idx] = valid_vals.mean()
#     return avg_values
