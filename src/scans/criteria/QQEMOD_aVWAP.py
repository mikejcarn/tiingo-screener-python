import pandas as pd
import numpy as np


def QQEMOD_aVWAP(
    df: pd.DataFrame,
    mode: str = 'bullish',
    max_lines: int = None,
    min_lines: int = 1,
    extend_to_end: bool = False,
) -> pd.DataFrame:
    """
    Scan for price validly testing a QQEMOD-anchored aVWAP during an opposing zone.

    A "valid test" requires that during the current zone streak, price has actually
    interacted with the aVWAP — at least one wick touched or exceeded it. If every
    candle in the zone is entirely on the wrong side of the aVWAP, it's a downtrend
    through it, not a pullback test.

    Bullish setup:
        - Current candle is in a red (bearish) QQEMOD zone
        - During the current red streak, max(High) >= bear aVWAP value

    Bearish setup:
        - Current candle is in a teal (bullish) QQEMOD zone
        - During the current teal streak, min(Low) <= bull aVWAP value

    Distance_Pct is included in output for reference but is not used as a filter.

    Parameters:
        mode          — 'bullish', 'bearish', or 'both'
        max_lines     — maximum number of aVWAP lines to check per direction
                        (most recent N by anchor index); None = no limit
        min_lines     — minimum number of aVWAPs that must pass the valid-test check
                        before any signals are emitted; default 1 (any single hit fires)
        extend_to_end — mirrors the indicator's extend_to_end flag:
                        False (default): solid lines are clipped at zone end; look for
                          the last non-NaN value within the current zone slice
                        True: solid lines extend to the latest bar; require non-NaN
                          at the latest bar (faster — no zone slice scan)
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()

    latest = df.iloc[-1]

    required_cols = ['QQE1_Above_Upper', 'QQE1_Below_Lower',
                     'QQE2_Above_Threshold', 'QQE2_Below_Threshold', 'QQE2_Above_TL']
    if not all(c in df.columns for c in required_cols):
        return pd.DataFrame()

    is_red = (
        bool(latest['QQE1_Below_Lower']) and
        bool(latest['QQE2_Below_Threshold']) and
        not bool(latest['QQE2_Above_TL'])
    )
    is_teal = (
        bool(latest['QQE1_Above_Upper']) and
        bool(latest['QQE2_Above_Threshold']) and
        bool(latest['QQE2_Above_TL'])
    )

    close = float(latest['Close'])
    signals = []

    def _resolve_avwap_val(col, zone_start):
        if extend_to_end:
            val = latest.get(col)
            return float(val) if pd.notna(val) else None
        zone_slice = df[col].iloc[zone_start:]
        valid = zone_slice.dropna()
        return float(valid.iloc[-1]) if len(valid) > 0 else None

    def _select_cols(prefix, zone_start):
        cols = [
            c for c in df.columns
            if c.startswith(prefix) and int(c.split('_')[-1]) < zone_start
        ]
        cols.sort(key=lambda c: int(c.split('_')[-1]), reverse=True)
        if max_lines is not None:
            cols = cols[:max_lines]
        return cols

    if mode in ('bullish', 'both') and is_red:
        zone_start = _find_zone_start(df, 'red')
        zone_highs = df['High'].iloc[zone_start:].values
        candidates = []

        for col in _select_cols('aVWAP_QQEMOD_bear_', zone_start):
            avwap_val = _resolve_avwap_val(col, zone_start)
            if avwap_val is None:
                continue
            if np.max(zone_highs) < avwap_val:
                continue  # price never touched the aVWAP — not a valid test
            dist = (close - avwap_val) / avwap_val * 100.0
            candidates.append({
                'Signal': 'bullish_pullback_to_aVWAP',
                'Close': close,
                'aVWAP': avwap_val,
                'Distance_Pct': round(dist, 3),
                'aVWAP_Column': col,
                'Zone': 'red',
            })

        if len(candidates) >= min_lines:
            signals.extend(candidates)

    if mode in ('bearish', 'both') and is_teal:
        zone_start = _find_zone_start(df, 'teal')
        zone_lows = df['Low'].iloc[zone_start:].values
        candidates = []

        for col in _select_cols('aVWAP_QQEMOD_bull_', zone_start):
            avwap_val = _resolve_avwap_val(col, zone_start)
            if avwap_val is None:
                continue
            if np.min(zone_lows) > avwap_val:
                continue  # price never touched the aVWAP — not a valid test
            dist = (close - avwap_val) / avwap_val * 100.0
            candidates.append({
                'Signal': 'bearish_pullback_to_aVWAP',
                'Close': close,
                'aVWAP': avwap_val,
                'Distance_Pct': round(dist, 3),
                'aVWAP_Column': col,
                'Zone': 'teal',
            })

        if len(candidates) >= min_lines:
            signals.extend(candidates)

    if not signals:
        return pd.DataFrame()

    return pd.DataFrame(signals, index=[df.index[-1]] * len(signals))


def _find_zone_start(df, zone):
    """Scan backwards to find the first row of the current continuous zone streak."""
    n = len(df)
    i = n - 1
    while i >= 0:
        row = df.iloc[i]
        if zone == 'red':
            in_zone = (
                bool(row['QQE1_Below_Lower']) and
                bool(row['QQE2_Below_Threshold']) and
                not bool(row['QQE2_Above_TL'])
            )
        else:  # teal
            in_zone = (
                bool(row['QQE1_Above_Upper']) and
                bool(row['QQE2_Above_Threshold']) and
                bool(row['QQE2_Above_TL'])
            )
        if not in_zone:
            break
        i -= 1
    return i + 1
