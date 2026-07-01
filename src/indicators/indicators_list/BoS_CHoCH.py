import pandas as pd
from smartmoneyconcepts import smc

def calculate_BoS_CHoCH(df, swing_lengths=None, swing_length=25,
                         show_bos=True, show_choch=True):
    # Support both swing_length (single) and swing_lengths (list)
    if swing_lengths is None:
        swing_lengths = [swing_length]

    df = df.rename(columns={
        'Open': 'open', 'Close': 'close',
        'Low': 'low', 'High': 'high', 'Volume': 'volume',
    }).copy()

    out = {}
    for sl in swing_lengths:
        swing_highs_lows = smc.swing_highs_lows(df, swing_length=sl)
        result = smc.bos_choch(df, swing_highs_lows, close_break=True)
        result.index = df.index

        tmp = pd.concat([df, result], axis=1)
        tmp = tmp.rename(columns={
            'BOS': f'BoS_{sl}',
            'CHOCH': f'CHoCH_{sl}',
            'Level': f'BoS_CHoCH_Price_{sl}',
            'BrokenIndex': f'BoS_CHoCH_Break_Index_{sl}',
        }, errors='ignore').fillna(0)

        if not show_bos:
            tmp[f'BoS_{sl}'] = 0
        if not show_choch:
            tmp[f'CHoCH_{sl}'] = 0

        out[f'BoS_{sl}']                  = tmp[f'BoS_{sl}']
        out[f'CHoCH_{sl}']                = tmp[f'CHoCH_{sl}']
        out[f'BoS_CHoCH_Price_{sl}']      = tmp[f'BoS_CHoCH_Price_{sl}']
        out[f'BoS_CHoCH_Break_Index_{sl}'] = tmp[f'BoS_CHoCH_Break_Index_{sl}']

    return out

def calculate_indicator(df, **params):
    """
    Wrapper function to calculate:
        - Break of Structure (BoS)
        - Change of Character (CHoCH)
    """
    return calculate_BoS_CHoCH(df, **params)
