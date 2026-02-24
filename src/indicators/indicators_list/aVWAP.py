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
#                             peaks_valleys_params=None,
#                             gaps_params=None,
#                             OB_params=None,
#                             BoS_CHoCH_params=None,
#                             avg_lookback=25,
#                             keep_OB_column=False,
#                             aVWAP_channel=False):
#     """
#     Calculate anchored VWAP channels from market structure points.
#   
#     Now supports multiple averages automatically based on the number of param sets.
#     If peaks_valleys_params is a list of N dicts, then peaks_valleys_avg=True
#     will calculate N averages (one for each config). Individual flags like
#     peaks_avg and valleys_avg will also use the corresponding configs if their
#     lookback parameters are present in the param dicts.
#
#     Parameters:
#         peaks_valleys: Calculate aVWAPs from ALL peaks and valleys
#         peaks_valleys_avg: Calculate rolling avg of peaks+valleys aVWAPs
#                           If True, calculates for all configs
#         peaks_avg: Calculate rolling avg of ONLY peaks aVWAPs
#                   If True, calculates for any config with 'peaks_avg_lookback'
#         valleys_avg: Calculate rolling avg of ONLY valleys aVWAPs
#                     If True, calculates for any config with 'valleys_avg_lookback'
#         gaps: Calculate aVWAPs from gap up/down points
#         gaps_avg: Calculate rolling avg of gap aVWAPs
#                  If True, calculates for all gap configs
#         OB: Calculate aVWAPs from Order Blocks (OB)
#         OB_avg: Calculate rolling avg of OB aVWAPs
#                If True, calculates for all OB configs
#         BoS_CHoCH: Calculate aVWAPs from BoS/CHoCH ranges
#         BoS_CHoCH_avg: Calculate rolling avg of BoS/CHoCH aVWAPs
#                       If True, calculates for all BoS/CHoCH configs
#         All_avg: Calculate rolling avg of ALL aVWAP types
#                 If True, calculates for each peaks_valleys config
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
#     # Helper to ensure we're working with lists of configs
#     def ensure_config_list(param, default_dict):
#         """Convert param to list of config dicts"""
#         if param is None:
#             return [default_dict.copy()]
#         if isinstance(param, list):
#             return param
#         return [param]
#   
#     # Helper to safely get value from dict with fallback
#     def get_lookback(param_dict, key, default):
#         if param_dict and key in param_dict:
#             return param_dict[key]
#         return default
#
#     # Set default parameters if not provided
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
#     # Determine which configs to use for each average type based on flags
#     peaks_valleys_avg_configs = list(range(len(peaks_valleys_configs))) if peaks_valleys_avg else []
#     peaks_avg_configs = []
#     valleys_avg_configs = []
#   
#     # For peaks_avg and valleys_avg, only use configs that have the required lookback
#     if peaks_avg:
#         peaks_avg_configs = [i for i, cfg in enumerate(peaks_valleys_configs) 
#                             if 'peaks_avg_lookback' in cfg]
#     if valleys_avg:
#         valleys_avg_configs = [i for i, cfg in enumerate(peaks_valleys_configs) 
#                               if 'valleys_avg_lookback' in cfg]
#   
#     gaps_avg_configs = list(range(len(gaps_configs))) if gaps_avg else []
#     OB_avg_configs = list(range(len(OB_configs))) if OB_avg else []
#     BoS_CHoCH_avg_configs = list(range(len(BoS_CHoCH_configs))) if BoS_CHoCH_avg else []
#   
#     # For All_avg, use the number of peaks_valleys configs
#     all_avg_configs = list(range(len(peaks_valleys_configs))) if All_avg else []
#
#     # Get indicators based on input parameters
#     aVWAP_anchors = []
#     if (peaks_valleys or peaks_valleys_avg_configs or peaks_avg_configs or 
#         valleys_avg_configs or all_avg_configs):
#         aVWAP_anchors.append('peaks_valleys')
#     if gaps or gaps_avg_configs or all_avg_configs:
#         aVWAP_anchors.append('gaps')
#     if OB or OB_avg_configs or all_avg_configs:
#         aVWAP_anchors.append('OB')
#     if BoS_CHoCH or BoS_CHoCH_avg_configs or all_avg_configs:
#         aVWAP_anchors.append('BoS_CHoCH')
#
#     if not aVWAP_anchors:
#         return {}
#
#     # Build params for get_indicators (use max values from all configs)
#     params = {}
#     if 'peaks_valleys' in aVWAP_anchors:
#         max_periods = max([cfg.get('periods', 25) for cfg in peaks_valleys_configs])
#         params['peaks_valleys'] = {'periods': max_periods}
#     if 'gaps' in aVWAP_anchors:
#         params['gaps'] = {}
#     if 'OB' in aVWAP_anchors:
#         max_periods = max([cfg.get('periods', 25) for cfg in OB_configs])
#         params['OB'] = {'periods': max_periods}
#     if 'BoS_CHoCH' in aVWAP_anchors:
#         max_swing = max([cfg.get('swing_length', 25) for cfg in BoS_CHoCH_configs])
#         params['BoS_CHoCH'] = {'swing_length': max_swing}
#
#     df = get_indicators(df, aVWAP_anchors, params)
#     df = df.reset_index()
#     df['date'] = pd.to_datetime(df['date'])
#
#     # Initialize storage dictionaries
#     all_individual_aVWAPs = {}  # Store all individual aVWAPs
#     peaks_only_aVWAPs = {}      # Store peaks only for peaks_avg
#     valleys_only_aVWAPs = {}    # Store valleys only for valleys_avg
#     gaps_aVWAPs = {}            # Store gaps aVWAPs
#     OB_aVWAPs = {}              # Store OB aVWAPs
#     BoS_CHoCH_aVWAPs = {}       # Store BoS/CHoCH aVWAPs
#
#     # Track extreme points for channel calculation
#     highest_peak_idx = None
#     lowest_valley_idx = None
#
#     def process_anchors(indices, prefix, max_count=None):
#         """Process anchors and return dictionary of aVWAP series"""
#         if not indices:
#             return {}
#         sorted_indices = sorted(indices, reverse=True)
#         if max_count is not None:
#             sorted_indices = sorted_indices[:max_count]
#         result = {}
#         for i in sorted_indices:
#             result[f'{prefix}_{i}'] = calculate_avwap(df, i)
#         return result
#
#     # Process peaks and valleys (once, for all configs)
#     if 'peaks_valleys' in aVWAP_anchors:
#         base_peaks_indices = df[df['Peaks'] == 1].index.tolist() if 'Peaks' in df.columns else []
#         base_valleys_indices = df[df['Valleys'] == 1].index.tolist() if 'Valleys' in df.columns else []
#       
#         # We'll process each config separately since max_aVWAPs can differ
#         for config_idx, config in enumerate(peaks_valleys_configs):
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
#             config_peaks = process_anchors(peaks_indices, f'aVWAP_peak_c{config_idx}', max_aVWAPs)
#             config_valleys = process_anchors(valleys_indices, f'aVWAP_valley_c{config_idx}', max_aVWAPs)
#           
#             # Store for averages based on config indices
#             if config_idx in peaks_avg_configs:
#                 peaks_only_aVWAPs.update(config_peaks)
#             if config_idx in valleys_avg_configs:
#                 valleys_only_aVWAPs.update(config_valleys)
#           
#             # Store all for All_avg and individual display
#             all_individual_aVWAPs.update(config_peaks)
#             all_individual_aVWAPs.update(config_valleys)
#
#     # Process gaps (once, for all configs)
#     if 'gaps' in aVWAP_anchors:
#         base_gap_up_indices = df[df['Gap_Up'] == 1].index.tolist() if 'Gap_Up' in df.columns else []
#         base_gap_down_indices = df[df['Gap_Down'] == 1].index.tolist() if 'Gap_Down' in df.columns else []
#       
#         for config_idx, config in enumerate(gaps_configs):
#             max_aVWAPs = config.get('max_aVWAPs', None)
#           
#             config_gap_up = process_anchors(base_gap_up_indices, f'Gap_Up_aVWAP_c{config_idx}', max_aVWAPs)
#             config_gap_down = process_anchors(base_gap_down_indices, f'Gap_Down_aVWAP_c{config_idx}', max_aVWAPs)
#           
#             if config_idx in gaps_avg_configs:
#                 gaps_aVWAPs.update(config_gap_up)
#                 gaps_aVWAPs.update(config_gap_down)
#           
#             all_individual_aVWAPs.update(config_gap_up)
#             all_individual_aVWAPs.update(config_gap_down)
#
#     # Process OBs (once, for all configs)
#     if 'OB' in aVWAP_anchors:
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
#             config_OB_bull = process_anchors(OB_bull_indices, f'aVWAP_OB_bull_c{config_idx}', max_aVWAPs)
#             config_OB_bear = process_anchors(OB_bear_indices, f'aVWAP_OB_bear_c{config_idx}', max_aVWAPs)
#           
#             if config_idx in OB_avg_configs:
#                 OB_aVWAPs.update(config_OB_bull)
#                 OB_aVWAPs.update(config_OB_bear)
#           
#             all_individual_aVWAPs.update(config_OB_bull)
#             all_individual_aVWAPs.update(config_OB_bear)
#
#     # Process BoS/CHoCH (once, for all configs)
#     if 'BoS_CHoCH' in aVWAP_anchors:
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
#             config_BoS = {}
#           
#             # Process bullish signals
#             bullish_signals = df[(df['BoS'] == 1) | (df['CHoCH'] == 1)].index
#             for idx in bullish_signals:
#                 break_idx = int(df.loc[idx, 'BoS_CHoCH_Break_Index']) if not pd.isna(df.loc[idx, 'BoS_CHoCH_Break_Index']) else None
#                 if break_idx:
#                     vwap = process_BoS_CHoCH_range(idx, break_idx, 'bullish')
#                     if vwap is not None:
#                         config_BoS[f'aVWAP_BoS_CHoCH_bull_c{config_idx}_{idx}'] = vwap
#           
#             # Process bearish signals
#             bearish_signals = df[(df['BoS'] == -1) | (df['CHoCH'] == -1)].index
#             for idx in bearish_signals:
#                 break_idx = int(df.loc[idx, 'BoS_CHoCH_Break_Index']) if not pd.isna(df.loc[idx, 'BoS_CHoCH_Break_Index']) else None
#                 if break_idx:
#                     vwap = process_BoS_CHoCH_range(idx, break_idx, 'bearish')
#                     if vwap is not None:
#                         config_BoS[f'aVWAP_BoS_CHoCH_bear_c{config_idx}_{idx}'] = vwap
#           
#             # Apply max_aVWAPs limit
#             if max_aVWAPs is not None and len(config_BoS) > max_aVWAPs:
#                 sorted_keys = sorted(config_BoS.keys(), 
#                                    key=lambda x: int(x.split('_')[-1]), 
#                                    reverse=True)[:max_aVWAPs]
#                 config_BoS = {k: config_BoS[k] for k in sorted_keys}
#           
#             if config_idx in BoS_CHoCH_avg_configs:
#                 BoS_CHoCH_aVWAPs.update(config_BoS)
#           
#             all_individual_aVWAPs.update(config_BoS)
#
#     # Combine all aVWAPs for display if requested
#     if peaks_valleys:
#         # Add all peaks/valleys aVWAPs (filter by prefix)
#         for key, value in all_individual_aVWAPs.items():
#             if 'aVWAP_peak_c' in key or 'aVWAP_valley_c' in key:
#                 df[key] = value
#   
#     if gaps:
#         for key, value in all_individual_aVWAPs.items():
#             if 'Gap_Up_aVWAP_c' in key or 'Gap_Down_aVWAP_c' in key:
#                 df[key] = value
#   
#     if OB:
#         for key, value in all_individual_aVWAPs.items():
#             if 'aVWAP_OB_bull_c' in key or 'aVWAP_OB_bear_c' in key:
#                 df[key] = value
#   
#     if BoS_CHoCH:
#         for key, value in all_individual_aVWAPs.items():
#             if 'aVWAP_BoS_CHoCH' in key:
#                 df[key] = value
#
#     # Calculate averages for each requested config
#     # Peaks_Valleys_avg (using peaks_valleys_avg_configs)
#     for config_idx in peaks_valleys_avg_configs:
#         if config_idx < len(peaks_valleys_configs):
#             config = peaks_valleys_configs[config_idx]
#             lookback = get_lookback(config, 'avg_lookback', avg_lookback)
#           
#             # Collect all aVWAPs from this config
#             config_aVWAPs = {}
#             prefix_patterns = [f'aVWAP_peak_c{config_idx}_', f'aVWAP_valley_c{config_idx}_']
#             for key, value in all_individual_aVWAPs.items():
#                 if any(key.startswith(p) for p in prefix_patterns):
#                     config_aVWAPs[key] = value
#           
#             if config_aVWAPs:
#                 avg_name = 'Peaks_Valleys_avg' if config_idx == 0 else f'Peaks_Valleys_avg_{config_idx}'
#               
#                 if aVWAP_channel and highest_peak_idx is not None and lowest_valley_idx is not None:
#                     first_valid_idx = max(highest_peak_idx, lowest_valley_idx)
#                     temp_avg = calculate_rolling_aVWAP_avg(df, config_aVWAPs, lookback)
#                     df[avg_name] = temp_avg.where(df.index >= first_valid_idx)
#                 else:
#                     df[avg_name] = calculate_rolling_aVWAP_avg(df, config_aVWAPs, lookback)
#
#     # Peaks_avg
#     for config_idx in peaks_avg_configs:
#         if config_idx < len(peaks_valleys_configs):
#             config = peaks_valleys_configs[config_idx]
#             lookback = get_lookback(config, 'peaks_avg_lookback', avg_lookback)
#           
#             config_peaks = {}
#             prefix = f'aVWAP_peak_c{config_idx}_'
#             for key, value in all_individual_aVWAPs.items():
#                 if key.startswith(prefix):
#                     config_peaks[key] = value
#           
#             if config_peaks:
#                 avg_name = 'Peaks_avg' if config_idx == 0 else f'Peaks_avg_{config_idx}'
#                 df[avg_name] = calculate_rolling_aVWAP_avg(df, config_peaks, lookback)
#
#     # Valleys_avg
#     for config_idx in valleys_avg_configs:
#         if config_idx < len(peaks_valleys_configs):
#             config = peaks_valleys_configs[config_idx]
#             lookback = get_lookback(config, 'valleys_avg_lookback', avg_lookback)
#           
#             config_valleys = {}
#             prefix = f'aVWAP_valley_c{config_idx}_'
#             for key, value in all_individual_aVWAPs.items():
#                 if key.startswith(prefix):
#                     config_valleys[key] = value
#           
#             if config_valleys:
#                 avg_name = 'Valleys_avg' if config_idx == 0 else f'Valleys_avg_{config_idx}'
#                 df[avg_name] = calculate_rolling_aVWAP_avg(df, config_valleys, lookback)
#
#     # Gaps_avg
#     for config_idx in gaps_avg_configs:
#         if config_idx < len(gaps_configs):
#             config = gaps_configs[config_idx]
#             lookback = get_lookback(config, 'avg_lookback', avg_lookback)
#           
#             config_gaps = {}
#             patterns = [f'Gap_Up_aVWAP_c{config_idx}_', f'Gap_Down_aVWAP_c{config_idx}_']
#             for key, value in all_individual_aVWAPs.items():
#                 if any(key.startswith(p) for p in patterns):
#                     config_gaps[key] = value
#           
#             if config_gaps:
#                 avg_name = 'Gaps_avg' if config_idx == 0 else f'Gaps_avg_{config_idx}'
#                 df[avg_name] = calculate_rolling_aVWAP_avg(df, config_gaps, lookback)
#
#     # OB_avg
#     for config_idx in OB_avg_configs:
#         if config_idx < len(OB_configs):
#             config = OB_configs[config_idx]
#             lookback = get_lookback(config, 'avg_lookback', avg_lookback)
#           
#             config_OB = {}
#             patterns = [f'aVWAP_OB_bull_c{config_idx}_', f'aVWAP_OB_bear_c{config_idx}_']
#             for key, value in all_individual_aVWAPs.items():
#                 if any(key.startswith(p) for p in patterns):
#                     config_OB[key] = value
#           
#             if config_OB:
#                 avg_name = 'OB_avg' if config_idx == 0 else f'OB_avg_{config_idx}'
#                 df[avg_name] = calculate_rolling_aVWAP_avg(df, config_OB, lookback)
#
#     # BoS_CHoCH_avg
#     for config_idx in BoS_CHoCH_avg_configs:
#         if config_idx < len(BoS_CHoCH_configs):
#             config = BoS_CHoCH_configs[config_idx]
#             lookback = get_lookback(config, 'avg_lookback', avg_lookback)
#           
#             config_BoS = {}
#             patterns = [f'aVWAP_BoS_CHoCH_bull_c{config_idx}_', f'aVWAP_BoS_CHoCH_bear_c{config_idx}_']
#             for key, value in all_individual_aVWAPs.items():
#                 if any(key.startswith(p) for p in patterns):
#                     config_BoS[key] = value
#           
#             if config_BoS:
#                 avg_name = 'BoS_CHoCH_avg' if config_idx == 0 else f'BoS_CHoCH_avg_{config_idx}'
#                 df[avg_name] = calculate_rolling_aVWAP_avg(df, config_BoS, lookback)
#
#     # All_avg (combines all aVWAPs)
#     for config_idx in all_avg_configs:
#         # For All_avg, we use the lookback from the corresponding peaks_valleys config if available
#         lookback = avg_lookback
#         if config_idx < len(peaks_valleys_configs):
#             lookback = get_lookback(peaks_valleys_configs[config_idx], 'avg_lookback', avg_lookback)
#       
#         if all_individual_aVWAPs:
#             avg_name = 'All_avg' if config_idx == 0 else f'All_avg_{config_idx}'
#             df[avg_name] = calculate_rolling_aVWAP_avg(df, all_individual_aVWAPs, lookback)
#
#     # Format output
#     cols_to_drop = ['Open', 'Close', 'High', 'Low', 'Volume']
#     if peaks_valleys or peaks_valleys_avg_configs or peaks_avg_configs or valleys_avg_configs or all_avg_configs:
#         cols_to_drop.extend(['Valleys', 'Peaks'])
#     if gaps or gaps_avg_configs or all_avg_configs:
#         cols_to_drop.extend(['Gap_Up', 'Gap_Down'])
#     if not keep_OB_column:
#         cols_to_drop.extend(['OB', 'OB_High', 'OB_Low', 'OB_Mitigated_Index'])
#     if BoS_CHoCH or BoS_CHoCH_avg_configs:
#         cols_to_drop.extend(['BoS', 'CHoCH', 'BoS_CHoCH_Price', 'BoS_CHoCH_Break_Index'])
#
#     df = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
#     df.set_index('date', inplace=True)
#
#     return df
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
#             parts = col_name.split('_')
#             return int(parts[-1])
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







import pandas as pd
import numpy as np
from src.indicators.indicators import get_indicators


def calculate_avwap_channel(
    df,
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
    keep_OB_column=False,
    aVWAP_channel=False
):
    """
    Calculate anchored VWAP channels from market structure points.

    MINIMAL CHANGE (Option A):
    - Compute OB signal columns per OB config (OB_c0, OB_c1, ...) by calling
      get_indicators() once per OB config with that config's periods.
    - Anchor OB aVWAPs off OB_c{config_idx} instead of the shared df['OB'].
    - This removes redundancy across c0/c1/c2 when OB periods differ.

    Everything else is left as-is.
    """

    # -------------------------
    # Helpers
    # -------------------------
    def ensure_config_list(param, default_dict):
        """Convert param to list of config dicts"""
        if param is None:
            return [default_dict.copy()]
        if isinstance(param, list):
            return param
        return [param]

    def get_lookback(param_dict, key, default):
        if param_dict and key in param_dict:
            return param_dict[key]
        return default

    def add_ob_per_config(df_in: pd.DataFrame, ob_configs: list) -> pd.DataFrame:
        """
        For each OB config, compute OB columns and attach them as OB_c{i}, etc.
        This avoids the 'max_periods' collapse that makes all configs identical.
        """
        out = df_in.copy()

        for i, cfg in enumerate(ob_configs):
            periods = cfg.get('periods', 25)

            # Compute OB for this config
            tmp = get_indicators(out.copy(), ['OB'], {'OB': {'periods': periods}})

            # Attach config-specific columns if present
            if 'OB' in tmp.columns:
                out[f'OB_c{i}'] = tmp['OB']
            if 'OB_High' in tmp.columns:
                out[f'OB_High_c{i}'] = tmp['OB_High']
            if 'OB_Low' in tmp.columns:
                out[f'OB_Low_c{i}'] = tmp['OB_Low']
            if 'OB_Mitigated_Index' in tmp.columns:
                out[f'OB_Mitigated_Index_c{i}'] = tmp['OB_Mitigated_Index']

        return out

    # -------------------------
    # Defaults
    # -------------------------
    default_peaks_valleys = {'periods': 25, 'max_aVWAPs': None}
    default_gaps = {'max_aVWAPs': None}
    default_OB = {
        'periods': 25,
        'max_aVWAPs': None,
        'include_bullish': True,
        'include_bearish': True
    }
    default_BoS_CHoCH = {
        'swing_length': 25,
        'max_aVWAPs': None
    }

    # Convert all params to lists of configs
    peaks_valleys_configs = ensure_config_list(peaks_valleys_params, default_peaks_valleys)
    gaps_configs = ensure_config_list(gaps_params, default_gaps)
    OB_configs = ensure_config_list(OB_params, default_OB)
    BoS_CHoCH_configs = ensure_config_list(BoS_CHoCH_params, default_BoS_CHoCH)

    # Determine which configs to use for each average type based on flags
    peaks_valleys_avg_configs = list(range(len(peaks_valleys_configs))) if peaks_valleys_avg else []
    peaks_avg_configs = []
    valleys_avg_configs = []

    if peaks_avg:
        peaks_avg_configs = [
            i for i, cfg in enumerate(peaks_valleys_configs)
            if 'peaks_avg_lookback' in cfg
        ]
    if valleys_avg:
        valleys_avg_configs = [
            i for i, cfg in enumerate(peaks_valleys_configs)
            if 'valleys_avg_lookback' in cfg
        ]

    gaps_avg_configs = list(range(len(gaps_configs))) if gaps_avg else []
    OB_avg_configs = list(range(len(OB_configs))) if OB_avg else []
    BoS_CHoCH_avg_configs = list(range(len(BoS_CHoCH_configs))) if BoS_CHoCH_avg else []

    all_avg_configs = list(range(len(peaks_valleys_configs))) if All_avg else []

    # -------------------------
    # Determine which anchors we need
    # -------------------------
    aVWAP_anchors = []
    if (peaks_valleys or peaks_valleys_avg_configs or peaks_avg_configs or
            valleys_avg_configs or all_avg_configs):
        aVWAP_anchors.append('peaks_valleys')
    if gaps or gaps_avg_configs or all_avg_configs:
        aVWAP_anchors.append('gaps')
    if OB or OB_avg_configs or all_avg_configs:
        aVWAP_anchors.append('OB')
    if BoS_CHoCH or BoS_CHoCH_avg_configs or all_avg_configs:
        aVWAP_anchors.append('BoS_CHoCH')

    if not aVWAP_anchors:
        return {}

    # -------------------------
    # Build params for get_indicators (EXCEPT OB)
    # (OB is computed per config below)
    # -------------------------
    base_anchors = [a for a in aVWAP_anchors if a != 'OB']

    params = {}
    if 'peaks_valleys' in base_anchors:
        max_periods = max([cfg.get('periods', 25) for cfg in peaks_valleys_configs])
        params['peaks_valleys'] = {'periods': max_periods}
    if 'gaps' in base_anchors:
        params['gaps'] = {}
    if 'BoS_CHoCH' in base_anchors:
        max_swing = max([cfg.get('swing_length', 25) for cfg in BoS_CHoCH_configs])
        params['BoS_CHoCH'] = {'swing_length': max_swing}

    # Compute base indicators (non-OB)
    df = get_indicators(df, base_anchors, params)

    # Compute OB per config if requested/needed
    if 'OB' in aVWAP_anchors:
        df = add_ob_per_config(df, OB_configs)

    # Standardize structure
    df = df.reset_index()
    df['date'] = pd.to_datetime(df['date'])

    # -------------------------
    # Storage
    # -------------------------
    all_individual_aVWAPs = {}
    peaks_only_aVWAPs = {}
    valleys_only_aVWAPs = {}
    gaps_aVWAPs = {}
    OB_aVWAPs = {}
    BoS_CHoCH_aVWAPs = {}

    highest_peak_idx = None
    lowest_valley_idx = None

    def process_anchors(indices, prefix, max_count=None):
        """Process anchors and return dictionary of aVWAP series"""
        if not indices:
            return {}
        sorted_indices = sorted(indices, reverse=True)
        if max_count is not None:
            sorted_indices = sorted_indices[:max_count]
        result = {}
        for i in sorted_indices:
            result[f'{prefix}_{i}'] = calculate_avwap(df, i)
        return result

    # -------------------------
    # Peaks / Valleys
    # -------------------------
    if 'peaks_valleys' in aVWAP_anchors:
        base_peaks_indices = df[df['Peaks'] == 1].index.tolist() if 'Peaks' in df.columns else []
        base_valleys_indices = df[df['Valleys'] == 1].index.tolist() if 'Valleys' in df.columns else []

        for config_idx, config in enumerate(peaks_valleys_configs):
            max_aVWAPs = config.get('max_aVWAPs', None)

            peaks_indices = base_peaks_indices.copy()
            valleys_indices = base_valleys_indices.copy()

            if aVWAP_channel:
                if highest_peak_idx is not None:
                    peaks_indices = [i for i in peaks_indices if i >= highest_peak_idx]
                if lowest_valley_idx is not None:
                    valleys_indices = [i for i in valleys_indices if i >= lowest_valley_idx]

            config_peaks = process_anchors(peaks_indices, f'aVWAP_peak_c{config_idx}', max_aVWAPs)
            config_valleys = process_anchors(valleys_indices, f'aVWAP_valley_c{config_idx}', max_aVWAPs)

            if config_idx in peaks_avg_configs:
                peaks_only_aVWAPs.update(config_peaks)
            if config_idx in valleys_avg_configs:
                valleys_only_aVWAPs.update(config_valleys)

            all_individual_aVWAPs.update(config_peaks)
            all_individual_aVWAPs.update(config_valleys)

    # -------------------------
    # Gaps
    # -------------------------
    if 'gaps' in aVWAP_anchors:
        base_gap_up_indices = df[df['Gap_Up'] == 1].index.tolist() if 'Gap_Up' in df.columns else []
        base_gap_down_indices = df[df['Gap_Down'] == 1].index.tolist() if 'Gap_Down' in df.columns else []

        for config_idx, config in enumerate(gaps_configs):
            max_aVWAPs = config.get('max_aVWAPs', None)

            config_gap_up = process_anchors(base_gap_up_indices, f'Gap_Up_aVWAP_c{config_idx}', max_aVWAPs)
            config_gap_down = process_anchors(base_gap_down_indices, f'Gap_Down_aVWAP_c{config_idx}', max_aVWAPs)

            if config_idx in gaps_avg_configs:
                gaps_aVWAPs.update(config_gap_up)
                gaps_aVWAPs.update(config_gap_down)

            all_individual_aVWAPs.update(config_gap_up)
            all_individual_aVWAPs.update(config_gap_down)

    # -------------------------
    # OBs (CHANGED: use OB_c{config_idx})
    # -------------------------
    if 'OB' in aVWAP_anchors:
        for config_idx, config in enumerate(OB_configs):
            max_aVWAPs = config.get('max_aVWAPs', None)
            include_bullish = config.get('include_bullish', True)
            include_bearish = config.get('include_bearish', True)

            OB_bull_indices = []
            OB_bear_indices = []

            ob_col = f'OB_c{config_idx}'
            if ob_col in df.columns:
                if aVWAP_channel:
                    # NOTE: highest/lowest idx tracking isn't implemented in your snippet;
                    # keeping your structure intact.
                    if lowest_valley_idx is not None and include_bullish:
                        OB_bull_indices = df[(df[ob_col] == 1) & (df.index >= lowest_valley_idx)].index.tolist()
                    if highest_peak_idx is not None and include_bearish:
                        OB_bear_indices = df[(df[ob_col] == -1) & (df.index >= highest_peak_idx)].index.tolist()
                else:
                    if include_bullish:
                        OB_bull_indices = df[df[ob_col] == 1].index.tolist()
                    if include_bearish:
                        OB_bear_indices = df[df[ob_col] == -1].index.tolist()

            config_OB_bull = process_anchors(OB_bull_indices, f'aVWAP_OB_bull_c{config_idx}', max_aVWAPs)
            config_OB_bear = process_anchors(OB_bear_indices, f'aVWAP_OB_bear_c{config_idx}', max_aVWAPs)

            if config_idx in OB_avg_configs:
                OB_aVWAPs.update(config_OB_bull)
                OB_aVWAPs.update(config_OB_bear)

            all_individual_aVWAPs.update(config_OB_bull)
            all_individual_aVWAPs.update(config_OB_bear)

    # -------------------------
    # BoS/CHoCH
    # -------------------------
    if 'BoS_CHoCH' in aVWAP_anchors:
        for config_idx, config in enumerate(BoS_CHoCH_configs):
            max_aVWAPs = config.get('max_aVWAPs', None)

            def process_BoS_CHoCH_range(signal_idx, break_idx, signal_type):
                if pd.isna(break_idx) or break_idx <= signal_idx:
                    return None
                range_df = df.iloc[signal_idx:break_idx + 1]
                if signal_type == 'bullish':
                    extreme_idx = range_df['Low'].idxmin()
                else:
                    extreme_idx = range_df['High'].idxmax()
                return calculate_avwap(df, extreme_idx)

            config_BoS = {}

            bullish_signals = df[(df['BoS'] == 1) | (df['CHoCH'] == 1)].index if 'BoS' in df.columns and 'CHoCH' in df.columns else []
            for idx in bullish_signals:
                break_idx = int(df.loc[idx, 'BoS_CHoCH_Break_Index']) if 'BoS_CHoCH_Break_Index' in df.columns and not pd.isna(df.loc[idx, 'BoS_CHoCH_Break_Index']) else None
                if break_idx:
                    vwap = process_BoS_CHoCH_range(idx, break_idx, 'bullish')
                    if vwap is not None:
                        config_BoS[f'aVWAP_BoS_CHoCH_bull_c{config_idx}_{idx}'] = vwap

            bearish_signals = df[(df['BoS'] == -1) | (df['CHoCH'] == -1)].index if 'BoS' in df.columns and 'CHoCH' in df.columns else []
            for idx in bearish_signals:
                break_idx = int(df.loc[idx, 'BoS_CHoCH_Break_Index']) if 'BoS_CHoCH_Break_Index' in df.columns and not pd.isna(df.loc[idx, 'BoS_CHoCH_Break_Index']) else None
                if break_idx:
                    vwap = process_BoS_CHoCH_range(idx, break_idx, 'bearish')
                    if vwap is not None:
                        config_BoS[f'aVWAP_BoS_CHoCH_bear_c{config_idx}_{idx}'] = vwap

            if max_aVWAPs is not None and len(config_BoS) > max_aVWAPs:
                sorted_keys = sorted(
                    config_BoS.keys(),
                    key=lambda x: int(x.split('_')[-1]),
                    reverse=True
                )[:max_aVWAPs]
                config_BoS = {k: config_BoS[k] for k in sorted_keys}

            if config_idx in BoS_CHoCH_avg_configs:
                BoS_CHoCH_aVWAPs.update(config_BoS)

            all_individual_aVWAPs.update(config_BoS)

    # -------------------------
    # Combine individual aVWAPs for display if requested
    # -------------------------
    if peaks_valleys:
        for key, value in all_individual_aVWAPs.items():
            if 'aVWAP_peak_c' in key or 'aVWAP_valley_c' in key:
                df[key] = value

    if gaps:
        for key, value in all_individual_aVWAPs.items():
            if 'Gap_Up_aVWAP_c' in key or 'Gap_Down_aVWAP_c' in key:
                df[key] = value

    if OB:
        for key, value in all_individual_aVWAPs.items():
            if 'aVWAP_OB_bull_c' in key or 'aVWAP_OB_bear_c' in key:
                df[key] = value

    if BoS_CHoCH:
        for key, value in all_individual_aVWAPs.items():
            if 'aVWAP_BoS_CHoCH' in key:
                df[key] = value

    # -------------------------
    # Averages
    # -------------------------
    for config_idx in peaks_valleys_avg_configs:
        if config_idx < len(peaks_valleys_configs):
            config = peaks_valleys_configs[config_idx]
            lookback = get_lookback(config, 'avg_lookback', avg_lookback)

            config_aVWAPs = {}
            prefix_patterns = [f'aVWAP_peak_c{config_idx}_', f'aVWAP_valley_c{config_idx}_']
            for key, value in all_individual_aVWAPs.items():
                if any(key.startswith(p) for p in prefix_patterns):
                    config_aVWAPs[key] = value

            if config_aVWAPs:
                avg_name = 'Peaks_Valleys_avg' if config_idx == 0 else f'Peaks_Valleys_avg_{config_idx}'
                if aVWAP_channel and highest_peak_idx is not None and lowest_valley_idx is not None:
                    first_valid_idx = max(highest_peak_idx, lowest_valley_idx)
                    temp_avg = calculate_rolling_aVWAP_avg(df, config_aVWAPs, lookback)
                    df[avg_name] = temp_avg.where(df.index >= first_valid_idx)
                else:
                    df[avg_name] = calculate_rolling_aVWAP_avg(df, config_aVWAPs, lookback)

    for config_idx in peaks_avg_configs:
        if config_idx < len(peaks_valleys_configs):
            config = peaks_valleys_configs[config_idx]
            lookback = get_lookback(config, 'peaks_avg_lookback', avg_lookback)

            config_peaks = {}
            prefix = f'aVWAP_peak_c{config_idx}_'
            for key, value in all_individual_aVWAPs.items():
                if key.startswith(prefix):
                    config_peaks[key] = value

            if config_peaks:
                avg_name = 'Peaks_avg' if config_idx == 0 else f'Peaks_avg_{config_idx}'
                df[avg_name] = calculate_rolling_aVWAP_avg(df, config_peaks, lookback)

    for config_idx in valleys_avg_configs:
        if config_idx < len(peaks_valleys_configs):
            config = peaks_valleys_configs[config_idx]
            lookback = get_lookback(config, 'valleys_avg_lookback', avg_lookback)

            config_valleys = {}
            prefix = f'aVWAP_valley_c{config_idx}_'
            for key, value in all_individual_aVWAPs.items():
                if key.startswith(prefix):
                    config_valleys[key] = value

            if config_valleys:
                avg_name = 'Valleys_avg' if config_idx == 0 else f'Valleys_avg_{config_idx}'
                df[avg_name] = calculate_rolling_aVWAP_avg(df, config_valleys, lookback)

    for config_idx in gaps_avg_configs:
        if config_idx < len(gaps_configs):
            config = gaps_configs[config_idx]
            lookback = get_lookback(config, 'avg_lookback', avg_lookback)

            config_gaps = {}
            patterns = [f'Gap_Up_aVWAP_c{config_idx}_', f'Gap_Down_aVWAP_c{config_idx}_']
            for key, value in all_individual_aVWAPs.items():
                if any(key.startswith(p) for p in patterns):
                    config_gaps[key] = value

            if config_gaps:
                avg_name = 'Gaps_avg' if config_idx == 0 else f'Gaps_avg_{config_idx}'
                df[avg_name] = calculate_rolling_aVWAP_avg(df, config_gaps, lookback)

    for config_idx in OB_avg_configs:
        if config_idx < len(OB_configs):
            config = OB_configs[config_idx]
            lookback = get_lookback(config, 'avg_lookback', avg_lookback)

            config_OB = {}
            patterns = [f'aVWAP_OB_bull_c{config_idx}_', f'aVWAP_OB_bear_c{config_idx}_']
            for key, value in all_individual_aVWAPs.items():
                if any(key.startswith(p) for p in patterns):
                    config_OB[key] = value

            if config_OB:
                avg_name = 'OB_avg' if config_idx == 0 else f'OB_avg_{config_idx}'
                df[avg_name] = calculate_rolling_aVWAP_avg(df, config_OB, lookback)

    for config_idx in BoS_CHoCH_avg_configs:
        if config_idx < len(BoS_CHoCH_configs):
            config = BoS_CHoCH_configs[config_idx]
            lookback = get_lookback(config, 'avg_lookback', avg_lookback)

            config_BoS = {}
            patterns = [f'aVWAP_BoS_CHoCH_bull_c{config_idx}_', f'aVWAP_BoS_CHoCH_bear_c{config_idx}_']
            for key, value in all_individual_aVWAPs.items():
                if any(key.startswith(p) for p in patterns):
                    config_BoS[key] = value

            if config_BoS:
                avg_name = 'BoS_CHoCH_avg' if config_idx == 0 else f'BoS_CHoCH_avg_{config_idx}'
                df[avg_name] = calculate_rolling_aVWAP_avg(df, config_BoS, lookback)

    for config_idx in all_avg_configs:
        lookback = avg_lookback
        if config_idx < len(peaks_valleys_configs):
            lookback = get_lookback(peaks_valleys_configs[config_idx], 'avg_lookback', avg_lookback)

        if all_individual_aVWAPs:
            avg_name = 'All_avg' if config_idx == 0 else f'All_avg_{config_idx}'
            df[avg_name] = calculate_rolling_aVWAP_avg(df, all_individual_aVWAPs, lookback)

    # -------------------------
    # Format output
    # -------------------------
    cols_to_drop = ['Open', 'Close', 'High', 'Low', 'Volume']
    if peaks_valleys or peaks_valleys_avg_configs or peaks_avg_configs or valleys_avg_configs or all_avg_configs:
        cols_to_drop.extend(['Valleys', 'Peaks'])
    if gaps or gaps_avg_configs or all_avg_configs:
        cols_to_drop.extend(['Gap_Up', 'Gap_Down'])

    # CHANGED: if we created OB_c{idx} columns, also drop them (and the optional per-config OB_* columns)
    if not keep_OB_column:
        cols_to_drop.extend(['OB', 'OB_High', 'OB_Low', 'OB_Mitigated_Index'])
        for i in range(len(OB_configs)):
            cols_to_drop.extend([
                f'OB_c{i}',
                f'OB_High_c{i}',
                f'OB_Low_c{i}',
                f'OB_Mitigated_Index_c{i}',
            ])

    if BoS_CHoCH or BoS_CHoCH_avg_configs:
        cols_to_drop.extend(['BoS', 'CHoCH', 'BoS_CHoCH_Price', 'BoS_CHoCH_Break_Index'])

    df = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
    df.set_index('date', inplace=True)

    return df


def calculate_indicator(df, **params):
    return calculate_avwap_channel(df, **params)


def calculate_avwap(df, anchor_index):
    """Calculate anchored VWAP from anchor point"""
    df_anchored = df.iloc[anchor_index:].copy()
    df_anchored['cumulative_volume'] = df_anchored['Volume'].cumsum()
    df_anchored['cumulative_volume_price'] = (
        df_anchored['Volume'] *
        (df_anchored['High'] + df_anchored['Low'] + df_anchored['Close']) / 3
    ).cumsum()
    return df_anchored['cumulative_volume_price'] / df_anchored['cumulative_volume']


def calculate_rolling_aVWAP_avg(df, aVWAP_dict, lookback=None):
    """Calculate average of aVWAP values"""
    if not aVWAP_dict:
        return pd.Series(np.nan, index=df.index)

    aVWAP_df = pd.DataFrame(aVWAP_dict)

    def extract_idx(col_name):
        try:
            parts = col_name.split('_')
            return int(parts[-1])
        except Exception:
            return 0

    sorted_cols = sorted(aVWAP_df.columns, key=extract_idx, reverse=True)
    aVWAP_df = aVWAP_df[sorted_cols]

    avg_values = pd.Series(np.nan, index=df.index)
    for idx in aVWAP_df.index.intersection(df.index):
        valid_vals = aVWAP_df.loc[idx].dropna()
        if lookback is not None:
            valid_vals = valid_vals[:lookback]
        if len(valid_vals) > 0:
            avg_values.loc[idx] = valid_vals.mean()
    return avg_values
