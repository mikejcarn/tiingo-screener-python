# import pandas as pd
# from typing import Literal, Optional
#
# def OB_aVWAP(
#     df: pd.DataFrame,
#     mode: Literal['bullish', 'bearish'] = 'bullish',
#     distance_pct: float = 1.0,
#     direction: Literal['below', 'above', 'within'] = 'within',
#     require_in_range: bool = False,
#     max_lookback: Optional[int] = None
# ) -> pd.DataFrame:
#     """
#     Unified scanner for price relative to Order Block's anchored VWAP.
#
#     Parameters:
#         df: DataFrame containing:
#             - 'OB' (1=bullish, -1=bearish, 0=neutral)
#             - 'OB_High', 'OB_Low' (price range)
#             - 'Close' (current price)
#             - Columns matching pattern: 'aVWAP_OB_bull_*' or 'aVWAP_OB_bear_*'
#
#         mode: 'bullish' or 'bearish' - which OB type to scan for
#         distance_pct: Percentage distance threshold from aVWAP
#         direction: Price position relative to aVWAP:
#             - 'below': Price below OB's aVWAP
#             - 'above': Price above OB's aVWAP
#             - 'within': Price near aVWAP (either side)
#         require_in_range: If True, price must also be within OB's High/Low range
#         max_lookback: Max bars to look back for OBs (None for all history)
#
#     Returns:
#         pd.DataFrame: Signal details if conditions met, else empty
#     """
#     if len(df) == 0:
#         return pd.DataFrame()
#
#     latest = df.iloc[-1]
#     target_ob = 1 if mode == 'bullish' else -1
#     avwap_prefix = f'aVWAP_OB_bull_' if mode == 'bullish' else f'aVWAP_OB_bear_'
#
#     # Apply lookback window if specified
#     scan_range = df
#     if max_lookback is not None:
#         scan_range = df.iloc[-max_lookback:]
#
#     # Find most recent OB of specified type
#     for i in range(len(scan_range)-1, -1, -1):
#         if scan_range['OB'].iloc[i] == target_ob:
#             ob_high = scan_range['OB_High'].iloc[i]
#             ob_low = scan_range['OB_Low'].iloc[i]
#             avwap_col = f'{avwap_prefix}{i}'
#           
#             if avwap_col in df.columns and pd.notna(df[avwap_col].iloc[-1]):
#                 current_avwap = df[avwap_col].iloc[-1]
#                 distance = (latest['Close'] - current_avwap) / current_avwap * 100
#               
#                 # Check if price is within OB range (if required)
#                 in_range = True
#                 if require_in_range:
#                     in_range = (latest['Close'] >= ob_low) and (latest['Close'] <= ob_high)
#               
#                 # Direction conditions
#                 if direction == 'below':
#                     condition = (-distance_pct <= distance <= 0)
#                 elif direction == 'above':
#                     condition = (0 <= distance <= distance_pct)
#                 else:  # 'within'
#                     condition = abs(distance) <= distance_pct
#               
#                 if condition and in_range:
#                     return pd.DataFrame({
#                         'Close': latest['Close'],
#                         'Signal': f'{mode.capitalize()}OB_aVWAP_{direction}',
#                         'OB_aVWAP': current_avwap,
#                         'OB_High': ob_high,
#                         'OB_Low': ob_low,
#                         'Distance_Pct': distance,
#                         'Position': 'below' if distance < 0 else 'above',
#                         'OB_Index': i,
#                         'OB_Mode': mode
#                     }, index=[latest.name])
#           
#             break  # Only check most recent OB
#   
#     return pd.DataFrame()
#
# def calculate_indicator(df, **params):
#     """Standard interface wrapper"""
#     return OB_aVWAP(df, **params)




import pandas as pd
from typing import Literal, Optional

def OB_aVWAP(
    df: pd.DataFrame,
    mode: Literal['bullish', 'bearish'] = 'bullish',
    distance_pct: float = 1.0,
    direction: Literal['below', 'above', 'within'] = 'within',
    require_in_range: bool = False,
    max_lookback: Optional[int] = None,
) -> pd.DataFrame:
    """
    Scan latest Close vs the most-recent valid OB aVWAP (bull/bear),
    based on your column naming: aVWAP_OB_{bull|bear}_c{cfg}_{anchorIdx}.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()

    latest = df.iloc[-1]

    # Your columns are bull/bear, not bullish/bearish
    side = 'bull' if mode == 'bullish' else 'bear'

    # Find all matching aVWAP columns
    prefix = f'aVWAP_OB_{side}_c'
    avwap_cols = [c for c in df.columns if c.startswith(prefix)]
    if not avwap_cols:
        return pd.DataFrame()

    # Keep only columns that have a value on the latest bar
    usable = []
    for c in avwap_cols:
        v = latest.get(c, pd.NA)
        if pd.notna(v):
            # parse anchor index from "..._{anchorIdx}"
            try:
                anchor_idx = int(c.split('_')[-1])
            except Exception:
                continue
            usable.append((anchor_idx, c, float(v)))

    if not usable:
        return pd.DataFrame()

    # If max_lookback is provided, only consider anchors within last N bars.
    # NOTE: anchor_idx is the ORIGINAL positional index used when you computed columns.
    # This assumes your CSV row count matches that same timeline length.
    if max_lookback is not None:
        min_anchor = len(df) - max_lookback
        usable = [(a, c, v) for (a, c, v) in usable if a >= min_anchor]
        if not usable:
            return pd.DataFrame()

    # Choose most recent anchor (largest anchor_idx)
    anchor_idx, avwap_col, current_avwap = max(usable, key=lambda x: x[0])

    close = float(latest['Close'])
    distance = (close - current_avwap) / current_avwap * 100.0

    # Direction condition
    if direction == 'below':
        condition = (-distance_pct <= distance <= 0)
    elif direction == 'above':
        condition = (0 <= distance <= distance_pct)
    else:  # within
        condition = abs(distance) <= distance_pct

    # Optional: require price inside OB range (only works if OB_High/OB_Low exist)
    in_range = True
    ob_high = ob_low = pd.NA
    if require_in_range:
        if 'OB_High' not in df.columns or 'OB_Low' not in df.columns:
            # Can't evaluate in-range without these
            return pd.DataFrame()
        # OB range at the anchor bar (positional)
        try:
            ob_high = float(df.iloc[anchor_idx]['OB_High'])
            ob_low = float(df.iloc[anchor_idx]['OB_Low'])
        except Exception:
            return pd.DataFrame()
        in_range = (close >= ob_low) and (close <= ob_high)

    if not (condition and in_range):
        return pd.DataFrame()

    # Extract config index for reporting: aVWAP_OB_bull_c{cfg}_{idx}
    try:
        cfg_idx = int(avwap_col.split('_c')[1].split('_')[0])
    except Exception:
        cfg_idx = 0

    return pd.DataFrame(
        {
            'Close': [close],
            'Signal': [f'{mode}_OB_aVWAP_{direction}'],
            'OB_aVWAP': [current_avwap],
            'Distance_Pct': [distance],
            'Position': ['below' if distance < 0 else 'above'],
            'Anchor_Index': [anchor_idx],
            'Config_Idx': [cfg_idx],
            'aVWAP_Column': [avwap_col],
            'OB_High': [ob_high],
            'OB_Low': [ob_low],
        },
        index=[df.index[-1]],
    )

