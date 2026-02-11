# import pandas as pd
# from typing import Literal, Optional
#
# def aVWAP_channel(
#     df: pd.DataFrame,
#     mode: Literal['support', 'resistance'] = 'support',
#     distance_pct: float = 5.0,
#     direction: Literal['below', 'above', 'within'] = 'within',
#     include_extremes: bool = False
# ) -> pd.DataFrame:
#     """
#     Unified aVWAP channel scanner for support/resistance levels.
#
#     Parameters:
#         df: DataFrame containing:
#             - Columns starting with 'aVWAP_'
#             - 'Close' (current price)
#
#         mode: 'support' or 'resistance' - which level to scan for
#             - support = bottom-most peaks aVWAP of the channel
#             - resistance = top-most valleys aVWAP of the channel
#         distance_pct: Percentage threshold from aVWAP level
#         direction: Price position relative to aVWAP:
#             - 'below': Price must be ≥X% below level
#             - 'above': Price must be ≥X% above level
#             - 'within': Price must be within X% of level
#         include_extremes: If True, includes both highest/lowest aVWAP in results
#
#     Returns:
#         pd.DataFrame: Signal details if conditions met, else empty
#     """
#     if len(df) == 0:
#         return pd.DataFrame()
#
#     latest = df.iloc[-1]
#     aVWAP_cols = [col for col in df.columns if col.startswith('aVWAP_') and pd.notna(latest[col])]
#
#     if not aVWAP_cols or pd.isna(latest['Close']):
#         return pd.DataFrame()
#
#     # Get relevant aVWAP level
#     if mode == 'support':
#         target_aVWAP = min(latest[col] for col in aVWAP_cols)
#         signal_prefix = 'aVWAP_Support'
#     else:  # resistance
#         target_aVWAP = max(latest[col] for col in aVWAP_cols)
#         signal_prefix = 'aVWAP_Resistance'
#
#     distance = (latest['Close'] - target_aVWAP) / target_aVWAP * 100
#
#     # Check conditions
#     if direction == 'below':
#         condition = (distance <= -distance_pct)
#     elif direction == 'above':
#         condition = (distance >= distance_pct)
#     else:  # 'within'
#         condition = (abs(distance) <= distance_pct)
#
#     if condition:
#         result = {
#             'Close': latest['Close'],
#             'Signal': f'{signal_prefix}_{direction}',
#             'aVWAP_Level': target_aVWAP,
#             'Distance_Pct': distance,
#             'Threshold_Pct': distance_pct,
#             'Position': 'below' if distance < 0 else 'above'
#         }
#
#         if include_extremes:
#             result.update({
#                 'Highest_aVWAP': max(latest[col] for col in aVWAP_cols),
#                 'Lowest_aVWAP': min(latest[col] for col in aVWAP_cols)
#             })
#
#         return pd.DataFrame(result, index=[latest.name])
#
#     return pd.DataFrame()
#
# def calculate_indicator(df, **params):
#     """Standard interface wrapper"""
#     return aVWAP_channel(df, **params)




import pandas as pd
from typing import Literal, Optional

def aVWAP_channel(
    df: pd.DataFrame,
    mode: Literal['support', 'resistance'] = 'support',
    distance_pct: float = 5.0,
    direction: Literal['below', 'above', 'within'] = 'within',
    outside_range: bool = False  # Consistent with SMA scanner
) -> pd.DataFrame:
    """
    Enhanced aVWAP channel scanner with consistent outside_range parameter.
    
    Parameters:
        df: DataFrame with aVWAP columns and 'Close'
        mode: 'support' or 'resistance' - which level to scan for
        distance_pct: Percentage threshold from aVWAP level
        direction: Desired price position relative to aVWAP
        outside_range (bool):
            - For 'within' mode:
                False = price is within distance_pct of aVWAP level (close)
                True = price is NOT within distance_pct of aVWAP level (far)
            - For 'below'/'above' modes:
                False = within distance_pct (normal position)
                True = beyond distance_pct (extended position)
    
    Returns:
        pd.DataFrame: Signal details if conditions met, else empty
    """
    if len(df) == 0:
        return pd.DataFrame()

    latest = df.iloc[-1]
    
    # Filter columns based on mode for better accuracy
    if mode == 'support':
        # Look for valley columns for support
        aVWAP_cols = [col for col in df.columns 
                     if col.startswith('aVWAP_valley_') and pd.notna(latest[col])]
        if not aVWAP_cols:
            # Fallback to all aVWAP columns if no valleys found
            aVWAP_cols = [col for col in df.columns 
                         if col.startswith('aVWAP_') and pd.notna(latest[col])]
        target_aVWAP = min(latest[col] for col in aVWAP_cols)
        signal_prefix = 'aVWAP_Support'
    else:  # resistance
        # Look for peak columns for resistance
        aVWAP_cols = [col for col in df.columns 
                     if col.startswith('aVWAP_peak_') and pd.notna(latest[col])]
        if not aVWAP_cols:
            # Fallback to all aVWAP columns if no peaks found
            aVWAP_cols = [col for col in df.columns 
                         if col.startswith('aVWAP_') and pd.notna(latest[col])]
        target_aVWAP = max(latest[col] for col in aVWAP_cols)
        signal_prefix = 'aVWAP_Resistance'

    if not aVWAP_cols or pd.isna(latest['Close']) or pd.isna(target_aVWAP):
        return pd.DataFrame()

    distance = (latest['Close'] - target_aVWAP) / target_aVWAP * 100

    # Check conditions based on direction and outside_range
    condition_met = False
    
    if direction == 'within':
        if outside_range:
            # Price is NOT within ±distance_pct% of level
            condition_met = (abs(distance) > distance_pct)
            position = 'Outside Range'
        else:
            # Price is within ±distance_pct% of level
            condition_met = (abs(distance) <= distance_pct)
            position = 'Within Range'
    
    elif direction == 'below':
        if outside_range:
            # Price is below level by MORE than distance_pct% (extended below)
            condition_met = (distance < -distance_pct)
            position = 'Extended Below'
        else:
            # Price is below level but within distance_pct% (0 to -distance_pct)
            condition_met = (-distance_pct <= distance <= 0)
            position = 'Below (Near)'
    
    else:  # direction == 'above'
        if outside_range:
            # Price is above level by MORE than distance_pct% (extended above)
            condition_met = (distance > distance_pct)
            position = 'Extended Above'
        else:
            # Price is above level but within distance_pct% (0 to +distance_pct)
            condition_met = (0 <= distance <= distance_pct)
            position = 'Above (Near)'

    if condition_met:
        result = {
            'Close': latest['Close'],
            'Signal': f'{signal_prefix}_{direction}',
            'aVWAP_Level': target_aVWAP,
            'Distance_Pct': distance,
            'Threshold_Pct': distance_pct,
            'Position': position,
            'Outside_Range': outside_range
        }

        return pd.DataFrame(result, index=[latest.name])

    return pd.DataFrame()

def calculate_indicator(df, **params):
    """Standard interface wrapper"""
    return aVWAP_channel(df, **params)
