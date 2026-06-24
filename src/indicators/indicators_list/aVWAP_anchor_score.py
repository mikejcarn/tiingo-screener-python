"""
aVWAP_anchor_score.py

aVWAP anchor-selection via structural quality scoring: instead of placing an
aVWAP at every detected swing point, this scores every candidate swing and
only keeps the best N anchors.

Scoring is anchor-quality-based, not behavior-based — it doesn't look at how
the aVWAP performs afterward (no reversion/touch testing), so the score
doesn't decay as the line ages. Three components are measured, each converted
to a percentile rank (0→1) within the current run, then combined as a
weighted sum so the weights are directly comparable:

  1. Prominence        — how deep/significant the swing is vs surrounding bars
                         (topographic-prominence concept, via scipy find_peaks)
  2. Isolation         — how many bars on each side it remains the extreme point
  3. Reversal sharpness — fast move in + fast move out (V-shape) vs slow grind

Score formula:
  score = (w_prominence × prominence_pct)
        + (w_isolation  × isolation_pct)
        + (w_sharpness  × sharpness_pct)

  where each _pct is the candidate's percentile rank (0→1) among all
  candidates for that mode (valley or peak) in the current run.

  Default weights = 1.0 each (equal importance). Double a weight to make
  that component twice as influential.

Output columns: aVWAP_valley_q1, aVWAP_valley_q2, ... (q1 = highest score)
and/or aVWAP_peak_q1, aVWAP_peak_q2, ... depending on which modes are enabled.
"""

import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from scipy.stats import rankdata


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def calculate_avwap_quality(
    df,
    # --- Output control ---
    valleys=True,
    peaks=False,
    max_anchors=3,
    min_score_pct=None,
    keep_scores=False,
    # --- Candidate detection (which bars are considered before scoring) ---
    min_swing_spacing=5,
    atr_period=14,
    # --- Score component 2: Isolation ---
    isolation_max_bars=200,
    # --- Score component 3: Reversal Sharpness ---
    sharpness_bars_before=10,
    sharpness_bars_after=10,
    # --- Component weights (1.0 = equal, 2.0 = twice as influential) ---
    w_prominence=1.0,
    w_isolation=1.0,
    w_sharpness=1.0,
    # --- Proximity filter ---
    max_atr_distance=None,
):
    """
    Score every candidate swing point and return aVWAPs anchored only to the
    best max_anchors per mode (valley/peak).

    Each component is converted to a percentile rank (0→1) among all
    candidates for that mode, then combined as a weighted sum:

        score = (w_prominence × prominence_pct)
              + (w_isolation  × isolation_pct)
              + (w_sharpness  × sharpness_pct)

    This means a deep slow-grinding low can still win on prominence + isolation
    even with low sharpness. Weights control the tradeoff directly — doubling
    a weight makes that dimension twice as influential.

    OUTPUT CONTROL
        valleys           — score valley swings (support anchors)
        peaks             — score peak swings (resistance anchors)
        max_anchors       — how many top-scoring aVWAPs to keep per mode
        min_score_pct     — optional floor as a fraction of the max possible score
                            (0.0–1.0). Scales automatically with weights so the
                            threshold stays meaningful when weights change.
                            0.5 = top half, 0.67 = above average, 0.8 = strong.
                            None = no floor (default).
        keep_scores       — if True, attach constant columns per aVWAP showing
                            the raw score and each component's percentile rank,
                            useful for inspecting why a candidate was chosen

    CANDIDATE DETECTION
        min_swing_spacing — minimum bars between two candidate swings
                            (pre-filter applied before any scoring)
        atr_period        — ATR lookback used to normalize prominence and
                            sharpness so results are comparable across
                            tickers/timeframes

    SCORE COMPONENT 1 — Prominence
        w_prominence       — weight for this component (default 1.0)
        (no detection param — computed automatically via scipy find_peaks,
        normalized by ATR at the swing bar, then percentile-ranked)

    SCORE COMPONENT 2 — Isolation
        w_isolation        — weight for this component (default 1.0)
        isolation_max_bars — how many bars out to search on each side to check
                             whether this bar remains the local extreme;
                             larger = rewards more dominant swing points

    SCORE COMPONENT 3 — Reversal Sharpness
        w_sharpness           — weight for this component (default 1.0)
        sharpness_bars_before — bars before the swing used to measure approach slope
        sharpness_bars_after  — bars after the swing used to measure reversal slope
                                high score = sharp V or inverted-V shape;
                                low score = slow grind (not disqualified, just
                                ranked lower than sharper reversals)

    PROXIMITY FILTER (applied after scoring, before max_anchors cut)
        max_atr_distance  — discard any candidate whose aVWAP value at the
                            current bar is more than this many ATRs from the
                            current close. None = no filter (default).
                            Age of the anchor is irrelevant; only whether the
                            resulting line is near price today matters.

    Returns a DataFrame (date-indexed) with only the aVWAP_* (and optional
    _score/_pct) columns — no OHLCV columns — so get_indicators can concat it
    directly without column collisions.
    """
    if not valleys and not peaks:
        return pd.DataFrame(index=df.index)

    work = df.reset_index()
    high = work['High'].values
    low = work['Low'].values
    close = work['Close'].values

    prev_close = pd.Series(close).shift(1).values
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)),
    )
    atr = pd.Series(tr).rolling(atr_period).mean().values

    def collect_candidates(extreme_values, mode):
        """Collect raw component values for all candidate swings."""
        search_arr = -extreme_values if mode == 'valley' else extreme_values
        cand_idx, props = find_peaks(search_arr, distance=min_swing_spacing, prominence=(None, None))
        sign = 1 if mode == 'valley' else -1

        rows = []
        for idx, prom in zip(cand_idx, props['prominences']):
            atr_val = atr[idx]
            if np.isnan(atr_val) or atr_val == 0:
                continue
            isolation = _isolation_window(extreme_values, idx, isolation_max_bars, mode)
            sharpness = _reversal_sharpness(
                close, idx, atr_val, sharpness_bars_before, sharpness_bars_after, sign
            )
            rows.append({
                'idx': idx,
                'mode': mode,
                'prominence_norm': prom / atr_val,
                'isolation_bars': isolation,
                'reversal_sharpness': sharpness,
            })
        return rows

    def apply_weighted_score(mode_rows):
        """Convert raw components to percentile ranks and compute weighted sum."""
        if not mode_rows:
            return mode_rows

        n = len(mode_rows)
        prom_vals  = np.array([r['prominence_norm']   for r in mode_rows])
        iso_vals   = np.array([r['isolation_bars']     for r in mode_rows])
        sharp_vals = np.array([r['reversal_sharpness'] for r in mode_rows])

        prom_pct  = _percentile_rank(prom_vals)
        iso_pct   = _percentile_rank(iso_vals)
        sharp_pct = _percentile_rank(sharp_vals)

        for i, row in enumerate(mode_rows):
            row['prominence_pct'] = prom_pct[i]
            row['isolation_pct']  = iso_pct[i]
            row['sharpness_pct']  = sharp_pct[i]
            row['score'] = (
                w_prominence * prom_pct[i]
                + w_isolation  * iso_pct[i]
                + w_sharpness  * sharp_pct[i]
            )
        return mode_rows

    all_rows = []
    if valleys:
        all_rows.extend(apply_weighted_score(collect_candidates(low, 'valley')))
    if peaks:
        all_rows.extend(apply_weighted_score(collect_candidates(high, 'peak')))

    current_close = close[-1]
    current_atr = atr[-1]
    proximity_active = (
        max_atr_distance is not None
        and not np.isnan(current_close)
        and not np.isnan(current_atr)
        and current_atr > 0
    )

    aVWAP_series = {}
    for mode in ('valley', 'peak'):
        mode_rows = sorted(
            (r for r in all_rows if r['mode'] == mode),
            key=lambda r: (r['score'], r['idx']), reverse=True,
        )
        if min_score_pct is not None:
            max_score = w_prominence + w_isolation + w_sharpness
            mode_rows = [r for r in mode_rows if r['score'] >= min_score_pct * max_score]
        if proximity_active:
            mode_rows = [
                r for r in mode_rows
                if abs(calculate_avwap(work, r['idx']).iloc[-1] - current_close) / current_atr
                   <= max_atr_distance
            ]
        mode_rows = mode_rows[:max_anchors]

        for rank, r in enumerate(mode_rows, start=1):
            col = f'aVWAP_{mode}_q{rank}'
            aVWAP_series[col] = calculate_avwap(work, r['idx'])
            if keep_scores:
                aVWAP_series[f'{col}_score']         = pd.Series(r['score'],           index=work.index)
                aVWAP_series[f'{col}_prominence_pct'] = pd.Series(r['prominence_pct'], index=work.index)
                aVWAP_series[f'{col}_isolation_pct']  = pd.Series(r['isolation_pct'],  index=work.index)
                aVWAP_series[f'{col}_sharpness_pct']  = pd.Series(r['sharpness_pct'],  index=work.index)

    out_df = pd.DataFrame(aVWAP_series, index=work.index)
    out_df['date'] = work['date']
    out_df.set_index('date', inplace=True)
    return out_df


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _percentile_rank(values: np.ndarray) -> np.ndarray:
    """Convert an array of values to percentile ranks in [0, 1].
    Ties receive the average rank. Single-candidate runs return [1.0]."""
    n = len(values)
    if n == 1:
        return np.array([1.0])
    ranks = rankdata(values, method='average') - 1
    return ranks / (n - 1)


def _isolation_window(values: np.ndarray, idx: int, isolation_max_bars: int, mode: str) -> int:
    """Largest N such that values[idx] is the min (valley) or max (peak)
    over the window [idx-N, idx+N]. Bigger N = more dominant local extreme."""
    n = len(values)
    val = values[idx]
    best_n = 0
    for w in range(1, isolation_max_bars + 1):
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


def _reversal_sharpness(close: np.ndarray, idx: int, atr_val: float,
                        bars_before: int, bars_after: int, sign: int) -> float:
    """ATR-normalized reversal slope: (slope out) minus (slope in), sign-adjusted
    for valley vs peak. Positive = sharp V/inverted-V reversal. Near zero or
    negative = slow grind or continuation through the point."""
    n = len(close)
    start, end = max(0, idx - bars_before), min(n - 1, idx + bars_after)
    pre  = close[start:idx + 1]
    post = close[idx:end + 1]

    pre_slope  = (pre[-1]  - pre[0])  / max(len(pre)  - 1, 1)
    post_slope = (post[-1] - post[0]) / max(len(post) - 1, 1)

    return sign * (post_slope / atr_val - pre_slope / atr_val)


def calculate_avwap(df: pd.DataFrame, anchor_index: int) -> pd.Series:
    """Cumulative typical-price VWAP anchored at anchor_index."""
    df_anchored = df.iloc[anchor_index:].copy()
    df_anchored['cumulative_volume'] = df_anchored['Volume'].cumsum()
    df_anchored['cumulative_volume_price'] = (
        df_anchored['Volume'] *
        (df_anchored['High'] + df_anchored['Low'] + df_anchored['Close']) / 3
    ).cumsum()
    return df_anchored['cumulative_volume_price'] / df_anchored['cumulative_volume']


def calculate_indicator(df, **params):
    return calculate_avwap_quality(df, **params)
