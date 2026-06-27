"""
O(1) VWAP path computation for arbitrary anchor bars.

Precomputes cumulative TP×Volume and Volume arrays once. Any anchor bar's
VWAP series from that anchor to any later bar is then a single array slice
and two scalar subtractions.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


def build_cumulative_arrays(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns (cum_tpv, cum_vol) — cumulative (TP × Volume) and Volume.

    Handles both capitalized ('High', 'Volume') and lowercase ('high', 'volume')
    column names, since the indicator CSV and prepare_dataframe use different cases.
    """
    def _col(a: str, b: str) -> np.ndarray:
        return df[a].values if a in df.columns else df[b].values

    high = _col('high', 'High')
    low = _col('low', 'Low')
    close = _col('close', 'Close')

    if 'Volume' in df.columns:
        volume = df['Volume'].values
    elif 'volume' in df.columns:
        volume = df['volume'].values
    else:
        volume = np.ones(len(df))

    tp = (high + low + close) / 3.0
    cum_tpv = np.cumsum(tp * volume)
    cum_vol = np.cumsum(volume)
    return cum_tpv, cum_vol


def precompute_vwap_paths(
    anchor_bars: List[int],
    cum_tpv: np.ndarray,
    cum_vol: np.ndarray,
) -> Dict[int, np.ndarray]:
    """
    For each anchor bar, precompute the full VWAP path to end of data.

    Returns {anchor_bar: array} where array[k] = VWAP(anchor, anchor + k).
    Length of array = len(cum_tpv) - anchor_bar.
    """
    n = len(cum_tpv)
    paths: Dict[int, np.ndarray] = {}
    for anchor in anchor_bars:
        if anchor >= n:
            continue
        base_tpv = cum_tpv[anchor - 1] if anchor > 0 else 0.0
        base_vol = cum_vol[anchor - 1] if anchor > 0 else 0.0
        seg_vol = cum_vol[anchor:] - base_vol
        seg_tpv = cum_tpv[anchor:] - base_tpv
        with np.errstate(divide='ignore', invalid='ignore'):
            paths[anchor] = np.where(seg_vol > 0, seg_tpv / seg_vol, np.nan)
    return paths


def get_vwap_df(
    anchor_bar: int,
    replay_bar: int,
    paths: Dict[int, np.ndarray],
    dates: np.ndarray,
) -> pd.DataFrame:
    """
    Return a {time, value} DataFrame for the VWAP from anchor_bar to replay_bar inclusive.
    `dates` must be an array of date strings aligned to the indicator df rows.
    """
    if anchor_bar not in paths:
        return pd.DataFrame(columns=['time', 'value'])
    path = paths[anchor_bar]
    length = min(replay_bar - anchor_bar + 1, len(path))
    if length <= 0:
        return pd.DataFrame(columns=['time', 'value'])
    return pd.DataFrame({
        'time': dates[anchor_bar: anchor_bar + length],
        'value': path[:length],
    })
