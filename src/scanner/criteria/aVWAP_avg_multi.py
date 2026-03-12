# import pandas as pd
# from typing import Literal, Optional, List
#
# def aVWAP_avg_multi(
#     df: pd.DataFrame,
#     mode: Literal['combined', 'peaks', 'valleys'] = 'combined',
#     condition: Literal['stacked_bullish', 'stacked_bearish', 'crossover', 
#                        'fan_bullish', 'fan_bearish', 'compression', 'expansion',
#                        'fast_above_slow', 'fast_below_slow', 'ribbon_spread'] = 'stacked_bullish',
#     slow_idx: int = 0,           # Heaviest/slowest (default 0 = main)
#     fast_idx: int = -1,           # Fastest/most reactive (default -1 = last)
#     threshold_pct: float = 0.5,
#     lookback_bars: int = 5
# ) -> pd.DataFrame:
#     """
#     Scanner for multiple aVWAP average lines.
#   
#     Column convention:
#     - avg (index 0) = heaviest/slowest (like 200-day)
#     - avg_1 (index 1) = lighter/faster (like 100-day)
#     - avg_2 (index 2) = even faster (like 50-day)
#     - avg_3 (index 3) = fastest (like 10-day)
#   
#     Parameters:
#         df: DataFrame with columns like:
#             - 'Peaks_Valleys_avg' (slowest/heaviest)
#             - 'Peaks_Valleys_avg_1' (faster)
#             - 'Peaks_Valleys_avg_2' (even faster)
#             - 'Peaks_Valleys_avg_3' (fastest)
#         mode: Which type of averages to analyze
#         condition: Pattern to detect:
#             - 'stacked_bullish': All averages increasing (slow < fast)
#             - 'stacked_bearish': All averages decreasing (slow > fast)
#             - 'crossover': Fastest crosses slowest
#             - 'fan_bullish': All averages moving up
#             - 'fan_bearish': All averages moving down
#             - 'compression': Averages getting closer together
#             - 'expansion': Averages spreading apart
#             - 'fast_above_slow': Fastest above slowest (bullish)
#             - 'fast_below_slow': Fastest below slowest (bearish)
#             - 'ribbon_spread': Distance between fastest and slowest
#         slow_idx: Index of slowest/heaviest average (default 0)
#         fast_idx: Index of fastest/most reactive (default -1 = last)
#         threshold_pct: Threshold for compression/expansion
#         lookback_bars: Bars to look back for trends
#   
#     Returns:
#         pd.DataFrame: Signal details if conditions met
#     """
#     if len(df) == 0:
#         return pd.DataFrame()
#
#     # Determine base column name
#     if mode == 'combined':
#         base_col = 'Peaks_Valleys_avg'
#     elif mode == 'peaks':
#         base_col = 'Peaks_avg'
#     elif mode == 'valleys':
#         base_col = 'Valleys_avg'
#     else:
#         raise ValueError("mode must be 'combined', 'peaks', or 'valleys'")
#
#     # Find all columns for this mode
#     all_avg_cols = [col for col in df.columns if col.startswith(base_col)]
#     if not all_avg_cols:
#         return pd.DataFrame()
#
#     # Sort columns: main first (slowest), then faster in order
#     # This matches: avg (slowest), avg_1 (faster), avg_2 (even faster)
#     sorted_cols = sorted(all_avg_cols, key=lambda x: (x != base_col, x))
#   
#     # Map indices to column names
#     col_by_idx = {}
#     for i, col in enumerate(sorted_cols):
#         if i == 0:
#             col_by_idx[0] = col  # Slowest/heaviest
#         else:
#             col_by_idx[i] = col  # Progressively faster
#   
#     latest = df.iloc[-1]
#   
#     # Get current values for all available averages
#     current_values = {}
#     for col in sorted_cols:
#         if pd.notna(latest[col]):
#             current_values[col] = latest[col]
#   
#     if len(current_values) < 2:
#         return pd.DataFrame()
#   
#     # Convert to list in order (slowest to fastest)
#     values_list = [current_values[col] for col in sorted_cols if col in current_values]
#   
#     # Get slowest and fastest columns
#     slow_col = col_by_idx.get(slow_idx, col_by_idx.get(0))
#     fast_col = col_by_idx.get(fast_idx if fast_idx >= 0 else len(sorted_cols)-1, 
#                               col_by_idx.get(len(sorted_cols)-1))
#   
#     # =====================
#     # CONDITION CHECKING
#     # =====================
#   
#     # STACKED BULLISH: slow < faster < fastest (increasing = bullish)
#     if condition == 'stacked_bullish':
#         is_stacked = all(values_list[i] < values_list[i+1] for i in range(len(values_list)-1))
#         if is_stacked:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_STACKED_BULLISH',
#                 'Condition': condition,
#                 'Slowest_Avg': current_values[slow_col],
#                 'Fastest_Avg': current_values[fast_col],
#                 'All_Avgs': str({k: round(v, 2) for k, v in current_values.items()})
#             }, index=[latest.name])
#   
#     # STACKED BEARISH: slow > faster > fastest (decreasing = bearish)
#     elif condition == 'stacked_bearish':
#         is_stacked = all(values_list[i] > values_list[i+1] for i in range(len(values_list)-1))
#         if is_stacked:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_STACKED_BEARISH',
#                 'Condition': condition,
#                 'Slowest_Avg': current_values[slow_col],
#                 'Fastest_Avg': current_values[fast_col],
#                 'All_Avgs': str({k: round(v, 2) for k, v in current_values.items()})
#             }, index=[latest.name])
#   
#     # FAST ABOVE SLOW: Fastest is above slowest (bullish)
#     elif condition == 'fast_above_slow':
#         if slow_col in current_values and fast_col in current_values:
#             if current_values[fast_col] > current_values[slow_col]:
#                 return pd.DataFrame({
#                     'Close': latest['Close'],
#                     'Signal': f'{mode.upper()}_FAST_ABOVE_SLOW',
#                     'Condition': condition,
#                     'Slowest_Avg': current_values[slow_col],
#                     'Fastest_Avg': current_values[fast_col],
#                     'Spread_Pct': (current_values[fast_col] - current_values[slow_col]) / current_values[slow_col] * 100
#                 }, index=[latest.name])
#   
#     # FAST BELOW SLOW: Fastest is below slowest (bearish)
#     elif condition == 'fast_below_slow':
#         if slow_col in current_values and fast_col in current_values:
#             if current_values[fast_col] < current_values[slow_col]:
#                 return pd.DataFrame({
#                     'Close': latest['Close'],
#                     'Signal': f'{mode.upper()}_FAST_BELOW_SLOW',
#                     'Condition': condition,
#                     'Slowest_Avg': current_values[slow_col],
#                     'Fastest_Avg': current_values[fast_col],
#                     'Spread_Pct': (current_values[slow_col] - current_values[fast_col]) / current_values[slow_col] * 100
#                 }, index=[latest.name])
#   
#     # CROSSOVER: Fastest crosses slowest
#     elif condition == 'crossover':
#         if slow_col not in current_values or fast_col not in current_values:
#             return pd.DataFrame()
#       
#         current_fast = current_values[fast_col]
#         current_slow = current_values[slow_col]
#       
#         # Get previous values
#         prev = df.iloc[-2]
#         prev_fast = prev[fast_col]
#         prev_slow = prev[slow_col]
#       
#         if pd.isna(prev_fast) or pd.isna(prev_slow):
#             return pd.DataFrame()
#       
#         # Bullish: Fast crosses ABOVE slow
#         if prev_fast <= prev_slow and current_fast > current_slow:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_CROSSOVER_BULLISH',
#                 'Condition': condition,
#                 'Slowest_Avg': current_slow,
#                 'Fastest_Avg': current_fast,
#                 'Slow_Col': slow_col,
#                 'Fast_Col': fast_col
#             }, index=[latest.name])
#       
#         # Bearish: Fast crosses BELOW slow
#         elif prev_fast >= prev_slow and current_fast < current_slow:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_CROSSOVER_BEARISH',
#                 'Condition': condition,
#                 'Slowest_Avg': current_slow,
#                 'Fastest_Avg': current_fast,
#                 'Slow_Col': slow_col,
#                 'Fast_Col': fast_col
#             }, index=[latest.name])
#   
#     # RIBBON SPREAD: Distance between fastest and slowest
#     elif condition == 'ribbon_spread':
#         if slow_col in current_values and fast_col in current_values:
#             spread = abs(current_values[fast_col] - current_values[slow_col])
#             spread_pct = (spread / current_values[slow_col]) * 100
#           
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_RIBBON_SPREAD',
#                 'Condition': condition,
#                 'Slowest_Avg': current_values[slow_col],
#                 'Fastest_Avg': current_values[fast_col],
#                 'Spread_Pct': spread_pct,
#                 'Spread_Abs': spread
#             }, index=[latest.name])
#   
#     # FAN BULLISH: All averages moved up over lookback
#     elif condition == 'fan_bullish':
#         if len(df) <= lookback_bars:
#             return pd.DataFrame()
#       
#         past = df.iloc[-lookback_bars-1]
#         all_up = True
#       
#         for col in current_values:
#             if pd.notna(past[col]) and current_values[col] <= past[col]:
#                 all_up = False
#                 break
#       
#         if all_up:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_FAN_BULLISH',
#                 'Condition': condition,
#                 'Lookback_Bars': lookback_bars
#             }, index=[latest.name])
#   
#     # FAN BEARISH: All averages moved down over lookback
#     elif condition == 'fan_bearish':
#         if len(df) <= lookback_bars:
#             return pd.DataFrame()
#       
#         past = df.iloc[-lookback_bars-1]
#         all_down = True
#       
#         for col in current_values:
#             if pd.notna(past[col]) and current_values[col] >= past[col]:
#                 all_down = False
#                 break
#       
#         if all_down:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_FAN_BEARISH',
#                 'Condition': condition,
#                 'Lookback_Bars': lookback_bars
#             }, index=[latest.name])
#   
#     # COMPRESSION: Averages getting closer together
#     elif condition == 'compression':
#         if len(df) <= lookback_bars:
#             return pd.DataFrame()
#       
#         # Current spread
#         current_spread = max(current_values.values()) - min(current_values.values())
#         current_spread_pct = (current_spread / latest['Close']) * 100
#       
#         # Past spread
#         past = df.iloc[-lookback_bars-1]
#         past_values = {col: past[col] for col in current_values if pd.notna(past[col])}
#       
#         if len(past_values) < 2:
#             return pd.DataFrame()
#       
#         past_spread = max(past_values.values()) - min(past_values.values())
#         past_spread_pct = (past_spread / past['Close']) * 100
#       
#         if current_spread_pct < past_spread_pct * (1 - threshold_pct/100):
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_COMPRESSION',
#                 'Condition': condition,
#                 'Past_Spread_Pct': round(past_spread_pct, 2),
#                 'Current_Spread_Pct': round(current_spread_pct, 2),
#                 'Reduction_Pct': round((1 - current_spread_pct/past_spread_pct) * 100, 2)
#             }, index=[latest.name])
#   
#     # EXPANSION: Averages spreading apart
#     elif condition == 'expansion':
#         if len(df) <= lookback_bars:
#             return pd.DataFrame()
#       
#         # Current spread
#         current_spread = max(current_values.values()) - min(current_values.values())
#         current_spread_pct = (current_spread / latest['Close']) * 100
#       
#         # Past spread
#         past = df.iloc[-lookback_bars-1]
#         past_values = {col: past[col] for col in current_values if pd.notna(past[col])}
#       
#         if len(past_values) < 2:
#             return pd.DataFrame()
#       
#         past_spread = max(past_values.values()) - min(past_values.values())
#         past_spread_pct = (past_spread / past['Close']) * 100
#       
#         if current_spread_pct > past_spread_pct * (1 + threshold_pct/100):
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_EXPANSION',
#                 'Condition': condition,
#                 'Past_Spread_Pct': round(past_spread_pct, 2),
#                 'Current_Spread_Pct': round(current_spread_pct, 2),
#                 'Increase_Pct': round((current_spread_pct/past_spread_pct - 1) * 100, 2)
#             }, index=[latest.name])
#   
#     return pd.DataFrame()





# import pandas as pd
# from typing import Literal, Optional, List
#
# def aVWAP_avg_multi(
#     df: pd.DataFrame,
#     mode: Literal['combined', 'peaks', 'valleys'] = 'combined',
#     condition: Literal['stacked_bullish', 'stacked_bearish', 'crossover', 
#                        'fan_bullish', 'fan_bearish', 'compression', 'expansion',
#                        'fast_above_slow', 'fast_below_slow', 'ribbon_spread'] = 'stacked_bullish',
#     slow_idx: int = 0,           # Heaviest/slowest (default 0 = main)
#     fast_idx: int = -1,           # Fastest/most reactive (default -1 = last)
#     threshold_pct: float = 0.5,
#     lookback_bars: int = 5,       # How many bars to look back for trend detection
#     confirmation_bars: int = 1,    # NEW: How many consecutive bars condition must hold
#     require_all_confirmation: bool = True  # NEW: If True, ALL bars must satisfy condition
# ) -> pd.DataFrame:
#     """
#     Scanner for multiple aVWAP average lines with confirmation period.
#    
#     Column convention:
#     - avg (index 0) = heaviest/slowest (like 200-day)
#     - avg_1 (index 1) = lighter/faster (like 100-day)
#     - avg_2 (index 2) = even faster (like 50-day)
#     - avg_3 (index 3) = fastest (like 10-day)
#    
#     Parameters:
#         df: DataFrame with average columns
#         mode: Which type of averages to analyze
#         condition: Pattern to detect
#         slow_idx: Index of slowest/heaviest average
#         fast_idx: Index of fastest/most reactive
#         threshold_pct: Threshold for compression/expansion
#         lookback_bars: Bars to look back for trend detection
#         confirmation_bars: Number of consecutive bars condition must hold
#         require_all_confirmation: 
#             - True: All confirmation_bars must satisfy condition
#             - False: At least one of the confirmation_bars satisfies condition
#    
#     Returns:
#         pd.DataFrame: Signal details if conditions met
#     """
#     if len(df) == 0:
#         return pd.DataFrame()
#
#     # Determine base column name
#     if mode == 'combined':
#         base_col = 'Peaks_Valleys_avg'
#     elif mode == 'peaks':
#         base_col = 'Peaks_avg'
#     elif mode == 'valleys':
#         base_col = 'Valleys_avg'
#     else:
#         raise ValueError("mode must be 'combined', 'peaks', or 'valleys'")
#
#     # Find all columns for this mode
#     all_avg_cols = [col for col in df.columns if col.startswith(base_col)]
#     if not all_avg_cols:
#         return pd.DataFrame()
#
#     # Sort columns: main first (slowest), then faster in order
#     sorted_cols = sorted(all_avg_cols, key=lambda x: (x != base_col, x))
#    
#     # Map indices to column names
#     col_by_idx = {}
#     for i, col in enumerate(sorted_cols):
#         if i == 0:
#             col_by_idx[0] = col  # Slowest/heaviest
#         else:
#             col_by_idx[i] = col  # Progressively faster
#    
#     # Get slowest and fastest columns
#     slow_col = col_by_idx.get(slow_idx, col_by_idx.get(0))
#     fast_col = col_by_idx.get(fast_idx if fast_idx >= 0 else len(sorted_cols)-1, 
#                               col_by_idx.get(len(sorted_cols)-1))
#    
#     # =====================
#     # HELPER FUNCTION TO CHECK CONDITION AT A SPECIFIC INDEX
#     # =====================
#     def check_condition_at_idx(idx):
#         """Check if condition holds at a specific DataFrame index"""
#         if idx < 0 or idx >= len(df):
#             return False
#        
#         row = df.iloc[idx]
#        
#         # Get current values for this row
#         current_values = {}
#         for col in sorted_cols:
#             if pd.notna(row[col]):
#                 current_values[col] = row[col]
#        
#         if len(current_values) < 2:
#             return False
#        
#         # Convert to list in order (slowest to fastest)
#         values_list = [current_values[col] for col in sorted_cols if col in current_values]
#        
#         # Check condition based on type
#         if condition == 'stacked_bullish':
#             return all(values_list[i] < values_list[i+1] for i in range(len(values_list)-1))
#        
#         elif condition == 'stacked_bearish':
#             return all(values_list[i] > values_list[i+1] for i in range(len(values_list)-1))
#        
#         elif condition == 'fast_above_slow':
#             if slow_col in current_values and fast_col in current_values:
#                 return current_values[fast_col] > current_values[slow_col]
#             return False
#        
#         elif condition == 'fast_below_slow':
#             if slow_col in current_values and fast_col in current_values:
#                 return current_values[fast_col] < current_values[slow_col]
#             return False
#        
#         elif condition == 'crossover':
#             # Crossover is special - we need to check the crossover event itself
#             # This will be handled separately in the main logic
#             return False
#        
#         elif condition == 'ribbon_spread':
#             # Ribbon spread always returns True (just measures spread)
#             if slow_col in current_values and fast_col in current_values:
#                 return True
#             return False
#        
#         elif condition == 'fan_bullish':
#             # Fan conditions require lookback and will be handled separately
#             return False
#        
#         elif condition == 'fan_bearish':
#             return False
#        
#         elif condition == 'compression':
#             return False
#        
#         elif condition == 'expansion':
#             return False
#        
#         return False
#    
#     # =====================
#     # HANDLE SPECIAL CONDITIONS THAT NEED LOOKBACK
#     # =====================
#    
#     # CROSSOVER - check if it happened exactly at the last bar
#     if condition == 'crossover':
#         if slow_col not in df.columns or fast_col not in df.columns:
#             return pd.DataFrame()
#        
#         # Need at least 2 bars to check crossover
#         if len(df) < 2:
#             return pd.DataFrame()
#        
#         latest = df.iloc[-1]
#         prev = df.iloc[-2]
#        
#         current_fast = latest[fast_col]
#         current_slow = latest[slow_col]
#         prev_fast = prev[fast_col]
#         prev_slow = prev[slow_col]
#        
#         if pd.isna(current_fast) or pd.isna(current_slow) or pd.isna(prev_fast) or pd.isna(prev_slow):
#             return pd.DataFrame()
#        
#         # Bullish: Fast crosses ABOVE slow
#         if prev_fast <= prev_slow and current_fast > current_slow:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_CROSSOVER_BULLISH',
#                 'Condition': condition,
#                 'Slowest_Avg': current_slow,
#                 'Fastest_Avg': current_fast,
#                 'Slow_Col': slow_col,
#                 'Fast_Col': fast_col
#             }, index=[latest.name])
#        
#         # Bearish: Fast crosses BELOW slow
#         elif prev_fast >= prev_slow and current_fast < current_slow:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_CROSSOVER_BEARISH',
#                 'Condition': condition,
#                 'Slowest_Avg': current_slow,
#                 'Fastest_Avg': current_fast,
#                 'Slow_Col': slow_col,
#                 'Fast_Col': fast_col
#             }, index=[latest.name])
#        
#         return pd.DataFrame()
#    
#     # FAN BULLISH - all averages moving up over lookback
#     elif condition == 'fan_bullish':
#         if len(df) <= lookback_bars:
#             return pd.DataFrame()
#        
#         latest = df.iloc[-1]
#         past = df.iloc[-lookback_bars-1]
#        
#         # Check all averages moved up
#         all_up = True
#         values = {}
#        
#         for col in sorted_cols:
#             if pd.notna(latest[col]) and pd.notna(past[col]):
#                 if latest[col] <= past[col]:
#                     all_up = False
#                     break
#                 values[col] = latest[col]
#             else:
#                 all_up = False
#                 break
#        
#         if all_up:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_FAN_BULLISH',
#                 'Condition': condition,
#                 'Lookback_Bars': lookback_bars,
#                 'Values': str({k: round(v, 2) for k, v in values.items()})
#             }, index=[latest.name])
#        
#         return pd.DataFrame()
#    
#     # FAN BEARISH - all averages moving down over lookback
#     elif condition == 'fan_bearish':
#         if len(df) <= lookback_bars:
#             return pd.DataFrame()
#        
#         latest = df.iloc[-1]
#         past = df.iloc[-lookback_bars-1]
#        
#         # Check all averages moved down
#         all_down = True
#         values = {}
#        
#         for col in sorted_cols:
#             if pd.notna(latest[col]) and pd.notna(past[col]):
#                 if latest[col] >= past[col]:
#                     all_down = False
#                     break
#                 values[col] = latest[col]
#             else:
#                 all_down = False
#                 break
#        
#         if all_down:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_FAN_BEARISH',
#                 'Condition': condition,
#                 'Lookback_Bars': lookback_bars,
#                 'Values': str({k: round(v, 2) for k, v in values.items()})
#             }, index=[latest.name])
#        
#         return pd.DataFrame()
#    
#     # COMPRESSION/EXPANSION - need to compare spread over time
#     elif condition in ['compression', 'expansion']:
#         if len(df) <= lookback_bars:
#             return pd.DataFrame()
#        
#         latest = df.iloc[-1]
#         past = df.iloc[-lookback_bars-1]
#        
#         # Get current values
#         current_values = {}
#         for col in sorted_cols:
#             if pd.notna(latest[col]):
#                 current_values[col] = latest[col]
#        
#         # Get past values
#         past_values = {}
#         for col in sorted_cols:
#             if pd.notna(past[col]):
#                 past_values[col] = past[col]
#        
#         if len(current_values) < 2 or len(past_values) < 2:
#             return pd.DataFrame()
#        
#         # Calculate spreads
#         current_spread = max(current_values.values()) - min(current_values.values())
#         current_spread_pct = (current_spread / latest['Close']) * 100
#        
#         past_spread = max(past_values.values()) - min(past_values.values())
#         past_spread_pct = (past_spread / past['Close']) * 100
#        
#         if condition == 'compression':
#             if current_spread_pct < past_spread_pct * (1 - threshold_pct/100):
#                 return pd.DataFrame({
#                     'Close': latest['Close'],
#                     'Signal': f'{mode.upper()}_COMPRESSION',
#                     'Condition': condition,
#                     'Past_Spread_Pct': round(past_spread_pct, 2),
#                     'Current_Spread_Pct': round(current_spread_pct, 2),
#                     'Reduction_Pct': round((1 - current_spread_pct/past_spread_pct) * 100, 2)
#                 }, index=[latest.name])
#        
#         elif condition == 'expansion':
#             if current_spread_pct > past_spread_pct * (1 + threshold_pct/100):
#                 return pd.DataFrame({
#                     'Close': latest['Close'],
#                     'Signal': f'{mode.upper()}_EXPANSION',
#                     'Condition': condition,
#                     'Past_Spread_Pct': round(past_spread_pct, 2),
#                     'Current_Spread_Pct': round(current_spread_pct, 2),
#                     'Increase_Pct': round((current_spread_pct/past_spread_pct - 1) * 100, 2)
#                 }, index=[latest.name])
#        
#         return pd.DataFrame()
#    
#     # =====================
#     # REGULAR CONDITIONS WITH CONFIRMATION PERIOD
#     # =====================
#     else:
#         # Check if we have enough bars for confirmation
#         if len(df) < confirmation_bars:
#             return pd.DataFrame()
#        
#         # Check each bar in the confirmation period
#         results = []
#         for i in range(confirmation_bars):
#             idx = -1 - i  # -1, -2, -3, etc.
#             results.append(check_condition_at_idx(idx))
#        
#         # Determine if signal triggers based on confirmation mode
#         signal_triggered = False
#         if require_all_confirmation:
#             signal_triggered = all(results)
#         else:
#             signal_triggered = any(results)
#        
#         if signal_triggered:
#             latest = df.iloc[-1]
#            
#             # Get current values for display
#             current_values = {}
#             for col in sorted_cols:
#                 if pd.notna(latest[col]):
#                     current_values[col] = latest[col]
#            
#             # Calculate spread if needed
#             spread_pct = None
#             if slow_col in current_values and fast_col in current_values:
#                 if condition == 'fast_above_slow' or condition == 'fast_below_slow':
#                     spread = abs(current_values[fast_col] - current_values[slow_col])
#                     spread_pct = (spread / current_values[slow_col]) * 100
#            
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_{condition.upper()}',
#                 'Condition': condition,
#                 'Confirmation_Bars': confirmation_bars,
#                 'Require_All': require_all_confirmation,
#                 'Confirmation_Results': str(results),
#                 'Slowest_Avg': current_values.get(slow_col, None),
#                 'Fastest_Avg': current_values.get(fast_col, None),
#                 'Spread_Pct': spread_pct,
#                 'All_Avgs': str({k: round(v, 2) for k, v in current_values.items()})
#             }, index=[latest.name])
#        
#         return pd.DataFrame()


# import pandas as pd
# from typing import Literal, Optional, List
#
# def aVWAP_avg_multi(
#     df: pd.DataFrame,
#     mode: Literal['combined', 'peaks', 'valleys'] = 'combined',
#     condition: Literal['stacked_bullish', 'stacked_bearish', 'crossover', 
#                        'fan_bullish', 'fan_bearish', 'compression', 'expansion',
#                        'fast_above_slow', 'fast_below_slow', 'ribbon_spread'] = 'stacked_bullish',
#     slow_idx: int = 0,           # Heaviest/slowest (default 0 = main)
#     fast_idx: int = -1,           # Fastest/most reactive (default -1 = last)
#     threshold_pct: float = 0.5,
#     lookback_bars: int = 5,
#     confirmation_bars: int = 1,    # How many consecutive bars condition must hold
#     require_all_confirmation: bool = True
# ) -> pd.DataFrame:
#     """
#     Scanner for multiple aVWAP average lines with confirmation period.
#     """
#     if len(df) == 0:
#         return pd.DataFrame()
#
#     # Determine base column name
#     if mode == 'combined':
#         base_col = 'Peaks_Valleys_avg'
#     elif mode == 'peaks':
#         base_col = 'Peaks_avg'
#     elif mode == 'valleys':
#         base_col = 'Valleys_avg'
#     else:
#         raise ValueError("mode must be 'combined', 'peaks', or 'valleys'")
#
#     # Find all columns for this mode
#     all_avg_cols = [col for col in df.columns if col.startswith(base_col)]
#     if not all_avg_cols:
#         return pd.DataFrame()
#
#     # Sort columns: main first (slowest), then faster in order
#     sorted_cols = sorted(all_avg_cols, key=lambda x: (x != base_col, x))
#    
#     # Map indices to column names
#     col_by_idx = {}
#     for i, col in enumerate(sorted_cols):
#         if i == 0:
#             col_by_idx[0] = col  # Slowest/heaviest
#         else:
#             col_by_idx[i] = col  # Progressively faster
#    
#     # Get slowest and fastest columns
#     slow_col = col_by_idx.get(slow_idx, col_by_idx.get(0))
#     fast_col = col_by_idx.get(fast_idx if fast_idx >= 0 else len(sorted_cols)-1, 
#                               col_by_idx.get(len(sorted_cols)-1))
#    
#     # =====================
#     # SIMPLE CONDITION CHECK AT CURRENT BAR
#     # =====================
#     def check_current_bar():
#         """Check if condition holds at the current bar (simplified)"""
#         latest = df.iloc[-1]
#        
#         # Get current values
#         current_values = {}
#         for col in sorted_cols:
#             if pd.notna(latest[col]):
#                 current_values[col] = latest[col]
#        
#         if len(current_values) < 2:
#             return False, {}
#        
#         # Get values in order
#         values_list = [current_values[col] for col in sorted_cols if col in current_values]
#        
#         # Check condition
#         result = False
#        
#         if condition == 'stacked_bullish':
#             result = all(values_list[i] < values_list[i+1] for i in range(len(values_list)-1))
#        
#         elif condition == 'stacked_bearish':
#             result = all(values_list[i] > values_list[i+1] for i in range(len(values_list)-1))
#        
#         elif condition == 'fast_above_slow':
#             if slow_col in current_values and fast_col in current_values:
#                 result = current_values[fast_col] > current_values[slow_col]
#        
#         elif condition == 'fast_below_slow':
#             if slow_col in current_values and fast_col in current_values:
#                 result = current_values[fast_col] < current_values[slow_col]
#        
#         # Add other conditions as needed...
#        
#         return result, current_values
#    
#     # =====================
#     # HANDLE SPECIAL CONDITIONS (crossover, fan, compression, expansion)
#     # =====================
#    
#     # CROSSOVER - check if it happened exactly at the last bar
#     if condition == 'crossover':
#         if len(df) < 2:
#             return pd.DataFrame()
#        
#         latest = df.iloc[-1]
#         prev = df.iloc[-2]
#        
#         if pd.isna(latest[fast_col]) or pd.isna(latest[slow_col]) or pd.isna(prev[fast_col]) or pd.isna(prev[slow_col]):
#             return pd.DataFrame()
#        
#         current_fast = latest[fast_col]
#         current_slow = latest[slow_col]
#         prev_fast = prev[fast_col]
#         prev_slow = prev[slow_col]
#        
#         if prev_fast <= prev_slow and current_fast > current_slow:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_CROSSOVER_BULLISH',
#                 'Condition': condition,
#                 'Slowest_Avg': current_slow,
#                 'Fastest_Avg': current_fast,
#                 'Slow_Col': slow_col,
#                 'Fast_Col': fast_col
#             }, index=[latest.name])
#        
#         elif prev_fast >= prev_slow and current_fast < current_slow:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_CROSSOVER_BEARISH',
#                 'Condition': condition,
#                 'Slowest_Avg': current_slow,
#                 'Fastest_Avg': current_fast,
#                 'Slow_Col': slow_col,
#                 'Fast_Col': fast_col
#             }, index=[latest.name])
#        
#         return pd.DataFrame()
#    
#     # FAN BULLISH
#     elif condition == 'fan_bullish':
#         if len(df) <= lookback_bars:
#             return pd.DataFrame()
#        
#         latest = df.iloc[-1]
#         past = df.iloc[-lookback_bars-1]
#        
#         all_up = True
#         for col in sorted_cols:
#             if pd.notna(latest[col]) and pd.notna(past[col]):
#                 if latest[col] <= past[col]:
#                     all_up = False
#                     break
#        
#         if all_up:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_FAN_BULLISH',
#                 'Condition': condition,
#                 'Lookback_Bars': lookback_bars
#             }, index=[latest.name])
#        
#         return pd.DataFrame()
#    
#     # FAN BEARISH
#     elif condition == 'fan_bearish':
#         if len(df) <= lookback_bars:
#             return pd.DataFrame()
#        
#         latest = df.iloc[-1]
#         past = df.iloc[-lookback_bars-1]
#        
#         all_down = True
#         for col in sorted_cols:
#             if pd.notna(latest[col]) and pd.notna(past[col]):
#                 if latest[col] >= past[col]:
#                     all_down = False
#                     break
#        
#         if all_down:
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_FAN_BEARISH',
#                 'Condition': condition,
#                 'Lookback_Bars': lookback_bars
#             }, index=[latest.name])
#        
#         return pd.DataFrame()
#    
#     # COMPRESSION/EXPANSION
#     elif condition in ['compression', 'expansion']:
#         if len(df) <= lookback_bars:
#             return pd.DataFrame()
#        
#         latest = df.iloc[-1]
#         past = df.iloc[-lookback_bars-1]
#        
#         # Get current values
#         current_values = {}
#         for col in sorted_cols:
#             if pd.notna(latest[col]):
#                 current_values[col] = latest[col]
#        
#         # Get past values
#         past_values = {}
#         for col in sorted_cols:
#             if pd.notna(past[col]):
#                 past_values[col] = past[col]
#        
#         if len(current_values) < 2 or len(past_values) < 2:
#             return pd.DataFrame()
#        
#         current_spread = max(current_values.values()) - min(current_values.values())
#         current_spread_pct = (current_spread / latest['Close']) * 100
#        
#         past_spread = max(past_values.values()) - min(past_values.values())
#         past_spread_pct = (past_spread / past['Close']) * 100
#        
#         if condition == 'compression':
#             if current_spread_pct < past_spread_pct * (1 - threshold_pct/100):
#                 return pd.DataFrame({...}, index=[latest.name])
#        
#         elif condition == 'expansion':
#             if current_spread_pct > past_spread_pct * (1 + threshold_pct/100):
#                 return pd.DataFrame({...}, index=[latest.name])
#        
#         return pd.DataFrame()
#    
#     # =====================
#     # REGULAR CONDITIONS WITH CONFIRMATION
#     # =====================
#     else:
#         if len(df) < confirmation_bars:
#             return pd.DataFrame()
#        
#         # Check each bar in the confirmation period
#         results = []
#         for i in range(confirmation_bars):
#             idx = -1 - i
#             row = df.iloc[idx]
#            
#             # Get values for this bar
#             bar_values = {}
#             for col in sorted_cols:
#                 if pd.notna(row[col]):
#                     bar_values[col] = row[col]
#            
#             if len(bar_values) < 2:
#                 results.append(False)
#                 continue
#            
#             # Get values in order
#             bar_values_list = [bar_values[col] for col in sorted_cols if col in bar_values]
#            
#             # Check condition
#             if condition == 'stacked_bullish':
#                 results.append(all(bar_values_list[j] < bar_values_list[j+1] for j in range(len(bar_values_list)-1)))
#             elif condition == 'stacked_bearish':
#                 results.append(all(bar_values_list[j] > bar_values_list[j+1] for j in range(len(bar_values_list)-1)))
#             elif condition == 'fast_above_slow':
#                 if slow_col in bar_values and fast_col in bar_values:
#                     results.append(bar_values[fast_col] > bar_values[slow_col])
#                 else:
#                     results.append(False)
#             elif condition == 'fast_below_slow':
#                 if slow_col in bar_values and fast_col in bar_values:
#                     results.append(bar_values[fast_col] < bar_values[slow_col])
#                 else:
#                     results.append(False)
#             elif condition == 'ribbon_spread':
#                 if slow_col in bar_values and fast_col in bar_values:
#                     results.append(True)  # Always true, just measures spread
#                 else:
#                     results.append(False)
#        
#         # Determine if signal triggers
#         signal_triggered = all(results) if require_all_confirmation else any(results)
#        
#         if signal_triggered:
#             latest = df.iloc[-1]
#             current_values = {}
#             for col in sorted_cols:
#                 if pd.notna(latest[col]):
#                     current_values[col] = latest[col]
#            
#             spread_pct = None
#             if slow_col in current_values and fast_col in current_values:
#                 if condition in ['fast_above_slow', 'fast_below_slow']:
#                     spread = abs(current_values[fast_col] - current_values[slow_col])
#                     spread_pct = (spread / current_values[slow_col]) * 100
#            
#             return pd.DataFrame({
#                 'Close': latest['Close'],
#                 'Signal': f'{mode.upper()}_{condition.upper()}',
#                 'Condition': condition,
#                 'Confirmation_Bars': confirmation_bars,
#                 'Require_All': require_all_confirmation,
#                 'Confirmation_Results': str(results),
#                 'Slowest_Avg': current_values.get(slow_col, None),
#                 'Fastest_Avg': current_values.get(fast_col, None),
#                 'Spread_Pct': spread_pct,
#                 'All_Avgs': str({k: round(v, 2) for k, v in current_values.items()})
#             }, index=[latest.name])
#        
#         return pd.DataFrame()




import pandas as pd
from typing import Literal, Optional, List

def aVWAP_avg_multi(
    df: pd.DataFrame,
    mode: Literal['combined', 'peaks', 'valleys'] = 'combined',
    condition: Literal['stacked_bullish', 'stacked_bearish', 'crossover', 
                       'fan_bullish', 'fan_bearish', 'compression', 'expansion',
                       'fast_above_slow', 'fast_below_slow', 'ribbon_spread',
                       'ribbon_compact', 'ribbon_wide'] = 'stacked_bullish',
    slow_idx: int = 0,           # Heaviest/slowest (default 0 = main)
    fast_idx: int = -1,           # Fastest/most reactive (default -1 = last)
    threshold_pct: float = 2.0,   # For compact/wide and compression/expansion
    lookback_bars: int = 5,
    confirmation_bars: int = 1,
    require_all_confirmation: bool = True
) -> pd.DataFrame:
    """
    Scanner for multiple aVWAP average lines.
    
    CONDITIONS:
    - stacked_bullish: All averages increasing (slow < fast)
    - stacked_bearish: All averages decreasing (slow > fast)
    - crossover: Fastest crosses slowest
    - fan_bullish: All averages moving up over lookback
    - fan_bearish: All averages moving down over lookback
    - compression: Averages getting closer together
    - expansion: Averages spreading apart
    - fast_above_slow: Fastest above slowest
    - fast_below_slow: Fastest below slowest
    - ribbon_spread: Distance between fastest and slowest
    - ribbon_compact: All averages within threshold_pct% of each other
    - ribbon_wide: Averages spread beyond threshold_pct%
    """
    if len(df) == 0:
        return pd.DataFrame()

    # Determine base column name
    if mode == 'combined':
        base_col = 'Peaks_Valleys_avg'
    elif mode == 'peaks':
        base_col = 'Peaks_avg'
    elif mode == 'valleys':
        base_col = 'Valleys_avg'
    else:
        raise ValueError("mode must be 'combined', 'peaks', or 'valleys'")

    # Find all columns for this mode
    all_avg_cols = [col for col in df.columns if col.startswith(base_col)]
    if not all_avg_cols:
        return pd.DataFrame()

    # Sort columns: main first (slowest), then faster in order
    sorted_cols = sorted(all_avg_cols, key=lambda x: (x != base_col, x))
    
    # Map indices to column names
    col_by_idx = {}
    for i, col in enumerate(sorted_cols):
        if i == 0:
            col_by_idx[0] = col  # Slowest/heaviest
        else:
            col_by_idx[i] = col  # Progressively faster
    
    # Get slowest and fastest columns
    slow_col = col_by_idx.get(slow_idx, col_by_idx.get(0))
    fast_col = col_by_idx.get(fast_idx if fast_idx >= 0 else len(sorted_cols)-1, 
                              col_by_idx.get(len(sorted_cols)-1))
    
    latest = df.iloc[-1]
    
    # Get current values for all available averages
    current_values = {}
    for col in sorted_cols:
        if pd.notna(latest[col]):
            current_values[col] = latest[col]
    
    if len(current_values) < 2:
        return pd.DataFrame()
    
    # Get values in order (slowest to fastest)
    values_list = [current_values[col] for col in sorted_cols if col in current_values]
    
    # =====================
    # RIBBON COMPACT/WIDE - Check ALL lines
    # =====================
    if condition == 'ribbon_compact':
        # Calculate statistics for ALL lines
        all_values = list(current_values.values())
        mean_avg = sum(all_values) / len(all_values)
        min_avg = min(all_values)
        max_avg = max(all_values)
        
        # Calculate spreads
        absolute_spread = max_avg - min_avg
        percent_spread = (absolute_spread / mean_avg) * 100
        
        # All lines are within threshold_pct% of each other
        is_compact = percent_spread <= threshold_pct
        
        if is_compact:
            return pd.DataFrame({
                'Close': latest['Close'],
                'Signal': f'{mode.upper()}_RIBBON_COMPACT',
                'Condition': condition,
                'Num_Averages': len(current_values),
                'Min_Avg': min_avg,
                'Max_Avg': max_avg,
                'Mean_Avg': mean_avg,
                'Spread_Pct': round(percent_spread, 2),
                'Threshold_Pct': threshold_pct,
                'All_Avgs': str({k: round(v, 2) for k, v in current_values.items()})
            }, index=[latest.name])
        
        return pd.DataFrame()
    
    elif condition == 'ribbon_wide':
        # Calculate statistics for ALL lines
        all_values = list(current_values.values())
        mean_avg = sum(all_values) / len(all_values)
        min_avg = min(all_values)
        max_avg = max(all_values)
        
        # Calculate spreads
        absolute_spread = max_avg - min_avg
        percent_spread = (absolute_spread / mean_avg) * 100
        
        # Lines are spread beyond threshold_pct%
        is_wide = percent_spread > threshold_pct
        
        if is_wide:
            return pd.DataFrame({
                'Close': latest['Close'],
                'Signal': f'{mode.upper()}_RIBBON_WIDE',
                'Condition': condition,
                'Num_Averages': len(current_values),
                'Min_Avg': min_avg,
                'Max_Avg': max_avg,
                'Mean_Avg': mean_avg,
                'Spread_Pct': round(percent_spread, 2),
                'Threshold_Pct': threshold_pct,
                'All_Avgs': str({k: round(v, 2) for k, v in current_values.items()})
            }, index=[latest.name])
        
        return pd.DataFrame()
    
    # =====================
    # STACKED CONDITIONS
    # =====================
    elif condition == 'stacked_bullish':
        is_stacked = all(values_list[i] < values_list[i+1] for i in range(len(values_list)-1))
        if is_stacked:
            return pd.DataFrame({
                'Close': latest['Close'],
                'Signal': f'{mode.upper()}_STACKED_BULLISH',
                'Condition': condition,
                'Slowest_Avg': current_values[slow_col],
                'Fastest_Avg': current_values[fast_col],
                'All_Avgs': str({k: round(v, 2) for k, v in current_values.items()})
            }, index=[latest.name])
    
    elif condition == 'stacked_bearish':
        is_stacked = all(values_list[i] > values_list[i+1] for i in range(len(values_list)-1))
        if is_stacked:
            return pd.DataFrame({
                'Close': latest['Close'],
                'Signal': f'{mode.upper()}_STACKED_BEARISH',
                'Condition': condition,
                'Slowest_Avg': current_values[slow_col],
                'Fastest_Avg': current_values[fast_col],
                'All_Avgs': str({k: round(v, 2) for k, v in current_values.items()})
            }, index=[latest.name])
    
    # =====================
    # FAST/SLOW CONDITIONS
    # =====================
    elif condition == 'fast_above_slow':
        if slow_col in current_values and fast_col in current_values:
            if current_values[fast_col] > current_values[slow_col]:
                spread_pct = (current_values[fast_col] - current_values[slow_col]) / current_values[slow_col] * 100
                return pd.DataFrame({
                    'Close': latest['Close'],
                    'Signal': f'{mode.upper()}_FAST_ABOVE_SLOW',
                    'Condition': condition,
                    'Slowest_Avg': current_values[slow_col],
                    'Fastest_Avg': current_values[fast_col],
                    'Spread_Pct': spread_pct
                }, index=[latest.name])
    
    elif condition == 'fast_below_slow':
        if slow_col in current_values and fast_col in current_values:
            if current_values[fast_col] < current_values[slow_col]:
                spread_pct = (current_values[slow_col] - current_values[fast_col]) / current_values[slow_col] * 100
                return pd.DataFrame({
                    'Close': latest['Close'],
                    'Signal': f'{mode.upper()}_FAST_BELOW_SLOW',
                    'Condition': condition,
                    'Slowest_Avg': current_values[slow_col],
                    'Fastest_Avg': current_values[fast_col],
                    'Spread_Pct': spread_pct
                }, index=[latest.name])
    
    # =====================
    # RIBBON SPREAD
    # =====================
    elif condition == 'ribbon_spread':
        if slow_col in current_values and fast_col in current_values:
            spread = abs(current_values[fast_col] - current_values[slow_col])
            spread_pct = (spread / current_values[slow_col]) * 100
           
            return pd.DataFrame({
                'Close': latest['Close'],
                'Signal': f'{mode.upper()}_RIBBON_SPREAD',
                'Condition': condition,
                'Slowest_Avg': current_values[slow_col],
                'Fastest_Avg': current_values[fast_col],
                'Spread_Pct': spread_pct,
                'Spread_Abs': spread
            }, index=[latest.name])
    
    # =====================
    # CROSSOVER
    # =====================
    elif condition == 'crossover':
        if len(df) < 2:
            return pd.DataFrame()
        
        prev = df.iloc[-2]
        
        if pd.isna(latest[fast_col]) or pd.isna(latest[slow_col]) or pd.isna(prev[fast_col]) or pd.isna(prev[slow_col]):
            return pd.DataFrame()
        
        current_fast = latest[fast_col]
        current_slow = latest[slow_col]
        prev_fast = prev[fast_col]
        prev_slow = prev[slow_col]
        
        if prev_fast <= prev_slow and current_fast > current_slow:
            return pd.DataFrame({
                'Close': latest['Close'],
                'Signal': f'{mode.upper()}_CROSSOVER_BULLISH',
                'Condition': condition,
                'Slowest_Avg': current_slow,
                'Fastest_Avg': current_fast
            }, index=[latest.name])
        
        elif prev_fast >= prev_slow and current_fast < current_slow:
            return pd.DataFrame({
                'Close': latest['Close'],
                'Signal': f'{mode.upper()}_CROSSOVER_BEARISH',
                'Condition': condition,
                'Slowest_Avg': current_slow,
                'Fastest_Avg': current_fast
            }, index=[latest.name])
        
        return pd.DataFrame()
    
    # =====================
    # FAN CONDITIONS
    # =====================
    elif condition == 'fan_bullish':
        if len(df) <= lookback_bars:
            return pd.DataFrame()
        
        past = df.iloc[-lookback_bars-1]
        all_up = True
        
        for col in sorted_cols:
            if pd.notna(latest[col]) and pd.notna(past[col]):
                if latest[col] <= past[col]:
                    all_up = False
                    break
        
        if all_up:
            return pd.DataFrame({
                'Close': latest['Close'],
                'Signal': f'{mode.upper()}_FAN_BULLISH',
                'Condition': condition,
                'Lookback_Bars': lookback_bars
            }, index=[latest.name])
        
        return pd.DataFrame()
    
    elif condition == 'fan_bearish':
        if len(df) <= lookback_bars:
            return pd.DataFrame()
        
        past = df.iloc[-lookback_bars-1]
        all_down = True
        
        for col in sorted_cols:
            if pd.notna(latest[col]) and pd.notna(past[col]):
                if latest[col] >= past[col]:
                    all_down = False
                    break
        
        if all_down:
            return pd.DataFrame({
                'Close': latest['Close'],
                'Signal': f'{mode.upper()}_FAN_BEARISH',
                'Condition': condition,
                'Lookback_Bars': lookback_bars
            }, index=[latest.name])
        
        return pd.DataFrame()
    
    # =====================
    # COMPRESSION/EXPANSION
    # =====================
    elif condition in ['compression', 'expansion']:
        if len(df) <= lookback_bars:
            return pd.DataFrame()
        
        past = df.iloc[-lookback_bars-1]
        
        # Get current values
        current_vals = list(current_values.values())
        
        # Get past values
        past_values = {}
        for col in sorted_cols:
            if pd.notna(past[col]):
                past_values[col] = past[col]
        
        if len(current_vals) < 2 or len(past_values) < 2:
            return pd.DataFrame()
        
        past_vals = list(past_values.values())
        
        # Calculate spreads
        current_spread = max(current_vals) - min(current_vals)
        current_spread_pct = (current_spread / latest['Close']) * 100
        
        past_spread = max(past_vals) - min(past_vals)
        past_spread_pct = (past_spread / past['Close']) * 100
        
        if condition == 'compression':
            if current_spread_pct < past_spread_pct * (1 - threshold_pct/100):
                return pd.DataFrame({
                    'Close': latest['Close'],
                    'Signal': f'{mode.upper()}_COMPRESSION',
                    'Condition': condition,
                    'Past_Spread_Pct': round(past_spread_pct, 2),
                    'Current_Spread_Pct': round(current_spread_pct, 2),
                    'Reduction_Pct': round((1 - current_spread_pct/past_spread_pct) * 100, 2)
                }, index=[latest.name])
        
        elif condition == 'expansion':
            if current_spread_pct > past_spread_pct * (1 + threshold_pct/100):
                return pd.DataFrame({
                    'Close': latest['Close'],
                    'Signal': f'{mode.upper()}_EXPANSION',
                    'Condition': condition,
                    'Past_Spread_Pct': round(past_spread_pct, 2),
                    'Current_Spread_Pct': round(current_spread_pct, 2),
                    'Increase_Pct': round((current_spread_pct/past_spread_pct - 1) * 100, 2)
                }, index=[latest.name])
        
        return pd.DataFrame()
    
    return pd.DataFrame()
