import pandas as pd

def engulfing_candle(df, mode='both', min_patterns=1, lookback_candles=None):
    """
    Scanner for engulfing candle patterns.
    
    Parameters:
        df (pd.DataFrame): Must contain:
            - 'bullish_engulfing_signal'
            - 'bearish_engulfing_signal'
            - 'engulfing_pattern_cluster'
        mode (str): One of ['bullish', 'bearish', 'both'] - which patterns to scan for
        min_patterns (int): Minimum number of engulfing candles required to pass
        lookback_candles (int, optional): Number of recent candles to check (going backwards). 
                                         If None, checks all candles in dataframe.
            
    Returns:
        pd.DataFrame: 
            - If conditions met: DataFrame of candles that triggered the scan
            - If conditions not met: Empty DataFrame
    """
    
    if len(df) == 0:
        return pd.DataFrame()
    
    # Validate required columns exist
    required_cols = ['bullish_engulfing_signal', 'bearish_engulfing_signal', 'engulfing_pattern_cluster']
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()
    
    # Get the last N candles based on lookback_candles
    if lookback_candles is not None and lookback_candles > 0:
        lookback_df = df.iloc[-lookback_candles:].copy()
    else:
        lookback_df = df.copy()
    
    if len(lookback_df) == 0:
        return pd.DataFrame()
    
    # Initialize results
    matching_candles = []
    
    # Check each candle in lookback period
    for idx, row in lookback_df.iterrows():
        pattern_match = False
        
        if mode.lower() == 'bullish':
            pattern_match = (row['bullish_engulfing_signal'] == 1)
        elif mode.lower() == 'bearish':
            pattern_match = (row['bearish_engulfing_signal'] == 1)
        elif mode.lower() == 'both':
            pattern_match = (row['bullish_engulfing_signal'] == 1 or row['bearish_engulfing_signal'] == 1)
        else:
            raise ValueError("mode must be 'bullish', 'bearish', or 'both'")
        
        if pattern_match:
            matching_candles.append(idx)
    
    # Count how many patterns found
    patterns_found = len(matching_candles)
    
    # Check if we have at least min_patterns
    if patterns_found >= min_patterns:
        # Return the pattern candles
        return df.loc[matching_candles]
    
    return pd.DataFrame()


# Optional: More specific scanner for detecting recent breakouts
def engulfing_breakout(df, mode='both', lookback_candles=10, require_recent=True):
    """
    Specialized scanner for engulfing breakouts.
    Checks for engulfing patterns and confirms the breakout direction held.
    
    Parameters:
        df (pd.DataFrame): Must contain engulfing pattern columns
        mode (str): 'bullish', 'bearish', or 'both'
        lookback_candles (int): How many candles to look back for patterns
        require_recent (bool): If True, requires the pattern to be within last 3 candles
        
    Returns:
        pd.DataFrame: DataFrame with pattern information if conditions met
    """
    
    if len(df) == 0:
        return pd.DataFrame()
    
    # Get recent data
    recent_df = df.iloc[-lookback_candles:].copy()
    
    # Find pattern candles
    pattern_indices = []
    pattern_types = []
    
    for idx, row in recent_df.iterrows():
        if mode in ['bullish', 'both'] and row['bullish_engulfing_signal'] == 1:
            pattern_indices.append(idx)
            pattern_types.append('bullish')
        elif mode in ['bearish', 'both'] and row['bearish_engulfing_signal'] == 1:
            pattern_indices.append(idx)
            pattern_types.append('bearish')
    
    if not pattern_indices:
        return pd.DataFrame()
    
    # If require_recent, check if pattern is within last 3 candles
    if require_recent:
        latest_idx = df.index[-1]
        recent_patterns = [idx for idx in pattern_indices if idx >= df.index[-3]]
        if not recent_patterns:
            return pd.DataFrame()
        pattern_indices = recent_patterns
        pattern_types = [pattern_types[pattern_indices.index(idx)] for idx in pattern_indices]
    
    # Return the pattern candles with additional context
    result_df = df.loc[pattern_indices].copy()
    result_df['pattern_type'] = pattern_types
    result_df['candles_since'] = [len(df) - 1 - df.index.get_loc(idx) for idx in pattern_indices]
    
    return result_df
