"""
aVWAP_anchor_score.py

New aVWAP anchor-selection method: instead of placing an aVWAP at every
detected swing point (your existing periods-based peaks_valleys approach),
this scores every candidate swing structurally and only keeps the best N.

Scoring is anchor-quality-based, not behavior-based — it doesn't look at how
the aVWAP performs afterward (no reversion/touch testing), so the score
doesn't decay as the line ages. Five components, each ATR-normalized so
results are comparable across tickers/timeframes:

  1. prominence        - how deep/isolated the swing is vs surrounding bars
                          (topographic-prominence concept, via scipy find_peaks)
  2. isolation_bars     - how many bars on each side it remains the extreme
  3. departure_sharpness - fast move in + fast move out (V-shape) vs slow grind
  4. vol_climax_z        - volume outlier at the swing bar vs its own recent history
  5. range_climax_z       - true-range outlier at the swing bar vs its own recent history

Drop-in indicator module: exposes calculate_indicator(df, **params) so it can
be called via get_indicators(df, ['aVWAP_quality'], {'aVWAP_quality': {...}}).

Output columns: aVWAP_valley_q1, aVWAP_valley_q2, ... (q1 = highest score)
and/or aVWAP_peak_q1, aVWAP_peak_q2, ... depending on which modes are enabled.
"""

import pandas as pd
import numpy as np
from scipy.signal import find_peaks


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _isolation_window(values: np.ndarray, idx: int, max_window: int, mode: str) -> int:
    """Largest N such that `values[idx]` is the min (valley) or max (peak)
    over the window [idx-N, idx+N]. Bigger N = more dominant local extreme."""
    n = len(values)
    val = values[idx]
    best_n = 0
    for w in range(1, max_window + 1):
        lo, hi = max(0, idx - w), min(n - 1, idx + w)
        window = values[lo:hi + 1]
        if mode == 'valley':
            if window.min() < val:
                break
        else:
            if window.max() > val:
                break
        best_n = w
        if lo == 0 and hi == n - 1:
            break
    return best_n


def _departure_sharpness(close: np.ndarray, idx: int, atr_val: float,
                          lookback: int, lookforward: int, sign: int) -> float:
    """ATR-normalized slope-out minus slope-in (sign-adjusted for valley vs peak).
    Positive = sharp reversal (V/inverted-V). Near zero/negative = slow grind
    or continuation through the point rather than a real turn."""
    n = len(close)
    start, end = max(0, idx - lookback), min(n - 1, idx + lookforward)
    pre = close[start:idx + 1]
    post = close[idx:end + 1]

    pre_slope = (pre[-1] - pre[0]) / max(len(pre) - 1, 1)
    post_slope = (post[-1] - post[0]) / max(len(post) - 1, 1)

    pre_v = pre_slope / atr_val
    post_v = post_slope / atr_val

    return sign * (post_v - pre_v)


def _climax_zscore(series: np.ndarray, idx: int, window: int) -> float:
    """How much of an outlier this bar is vs its own recent history
    (used for both volume and true range)."""
    start = max(0, idx - window)
    local = series[start:idx]  # history BEFORE the bar, excludes idx itself
    if len(local) < 5 or np.nanstd(local) == 0:
        return 0.0
    return (series[idx] - np.nanmean(local)) / np.nanstd(local)


def calculate_avwap(df: pd.DataFrame, anchor_index: int) -> pd.Series:
    """Same cumulative typical-price VWAP as in aVWAP_channel.py — kept local
    here so this module has no import dependency on that file."""
    df_anchored = df.iloc[anchor_index:].copy()
    df_anchored['cumulative_volume'] = df_anchored['Volume'].cumsum()
    df_anchored['cumulative_volume_price'] = (
        df_anchored['Volume'] *
        (df_anchored['High'] + df_anchored['Low'] + df_anchored['Close']) / 3
    ).cumsum()
    return df_anchored['cumulative_volume_price'] / df_anchored['cumulative_volume']


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def calculate_avwap_quality(
    df,
    valleys=True,
    peaks=False,
    top_n=3,
    min_score=None,
    distance=5,
    max_window=200,
    atr_period=14,
    departure_lookback=10,
    departure_lookforward=10,
    vol_climax_window=20,
    range_climax_window=20,
    keep_scores=False,
):
    """
    Score candidate swing points and return aVWAPs anchored only to the
    best `top_n` per mode (valley/peak).

    Params
    ------
    valleys / peaks   : which side(s) to generate candidates for
    top_n             : max aVWAPs to keep per mode
    min_score         : optional floor — candidates below this are dropped
                         before the top_n cut
    distance          : min bars between raw candidates (scipy find_peaks)
    max_window        : cap for the isolation-window search
    atr_period        : ATR lookback used to normalize prominence/sharpness
    departure_lookback/lookforward : bars used either side of the candidate
                         to measure approach/departure slope
    vol_climax_window / range_climax_window : lookback for the volume and
                         true-range outlier z-scores
    keep_scores       : if True, also attach a constant `_score` column per
                         aVWAP for debugging/inspection

    Returns a DataFrame (date-indexed) with only the new aVWAP_* (and
    optional _score) columns — no OHLCV columns — so get_indicators can
    concat it directly without column collisions.
    """
    if not valleys and not peaks:
        return pd.DataFrame(index=df.index)

    work = df.reset_index()  # expects a 'date' index, matching the rest of the codebase
    high = work['High'].values
    low = work['Low'].values
    close = work['Close'].values
    volume = work['Volume'].values

    prev_close = pd.Series(close).shift(1).values
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)),
    )
    atr = pd.Series(tr).rolling(atr_period).mean().values

    def score_candidates(extreme_values, mode):
        search_arr = -extreme_values if mode == 'valley' else extreme_values
        cand_idx, props = find_peaks(search_arr, distance=distance, prominence=(None, None))
        sign = 1 if mode == 'valley' else -1

        rows = []
        for idx, prom in zip(cand_idx, props['prominences']):
            atr_val = atr[idx]
            if np.isnan(atr_val) or atr_val == 0:
                continue
            isolation = _isolation_window(extreme_values, idx, max_window, mode)
            sharpness = _departure_sharpness(
                close, idx, atr_val, departure_lookback, departure_lookforward, sign
            )
            vol_z = _climax_zscore(volume, idx, vol_climax_window)
            range_z = _climax_zscore(tr, idx, range_climax_window)
            prominence_norm = prom / atr_val

            score = (
                prominence_norm
                * np.log1p(isolation)
                * max(sharpness, 0.01)
                * (1 + max(vol_z, 0))
                * (1 + max(range_z, 0))
            )
            rows.append({
                'idx': idx, 'mode': mode, 'prominence_norm': prominence_norm,
                'isolation_bars': isolation, 'departure_sharpness': sharpness,
                'vol_climax_z': vol_z, 'range_climax_z': range_z, 'score': score,
            })
        return rows

    rows = []
    if valleys:
        rows.extend(score_candidates(low, 'valley'))
    if peaks:
        rows.extend(score_candidates(high, 'peak'))

    aVWAP_series = {}
    for mode in ('valley', 'peak'):
        mode_rows = sorted(
            (r for r in rows if r['mode'] == mode),
            key=lambda r: r['score'], reverse=True,
        )
        if min_score is not None:
            mode_rows = [r for r in mode_rows if r['score'] >= min_score]
        mode_rows = mode_rows[:top_n]

        for rank, r in enumerate(mode_rows, start=1):
            col = f'aVWAP_{mode}_q{rank}'
            aVWAP_series[col] = calculate_avwap(work, r['idx'])
            if keep_scores:
                aVWAP_series[f'{col}_score'] = pd.Series(r['score'], index=work.index)

    out_df = pd.DataFrame(aVWAP_series, index=work.index)
    out_df['date'] = work['date']
    out_df.set_index('date', inplace=True)
    return out_df


def calculate_indicator(df, **params):
    return calculate_avwap_quality(df, **params)
