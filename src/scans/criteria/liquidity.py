import pandas as pd

def liquidity(df, distance_pct=1.0):
    """
    Scan for when price is near a liquidity level.
    
    Parameters:
        - distance_pct (float): Percentage distance from liquidity level to consider "close"
    
    Returns:
        pd.DataFrame: Single-row DataFrame if conditions met, else empty.
    """
    if len(df) == 0:
        return pd.DataFrame()
    
    latest = df.iloc[-1]
    
    # Only consider rows where Liquidity is not 0
    liquidity_zones = df[df['Liquidity'] != 0]
    
    if len(liquidity_zones) == 0:
        return pd.DataFrame()
    
    # Get the most recent liquidity zone
    latest_zone = liquidity_zones.iloc[-1]
    
    # Calculate distance from current price to liquidity level
    distance = abs(latest['Close'] - latest_zone['Liquidity_Level']) / latest['Close'] * 100
    
    # Check if price is within distance_pct of liquidity level
    if (distance <= distance_pct) and (latest_zone['Liquidity_Level'] != 0):
        return df.iloc[-1:].copy()
    
    return pd.DataFrame()
