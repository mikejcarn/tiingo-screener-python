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
