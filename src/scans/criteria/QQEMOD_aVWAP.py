import pandas as pd


def QQEMOD_aVWAP(
    df: pd.DataFrame,
    mode: str = 'bullish',
    distance_pct: float = 1.0,
) -> pd.DataFrame:
    """
    Scan for price touching a QQEMOD-anchored aVWAP during an opposing candle zone.

    Bullish setup:
        Current candle is red (bearish QQEMOD zone) AND a bear aVWAP
        (anchored at the lowest low of a prior red segment) is within
        distance_pct% of current close. The aVWAP acts as support being
        tested during the pullback.

    Bearish setup:
        Current candle is teal (bullish QQEMOD zone) AND a bull aVWAP
        (anchored at the highest high of a prior teal segment) is within
        distance_pct% of current close. The aVWAP acts as resistance being
        tested during the recovery.

    Requires QQEMOD to be in the indicator list so that QQE1_Above_Upper,
    QQE1_Below_Lower, QQE2_Above_Threshold, QQE2_Below_Threshold, and
    QQE2_Above_TL columns are present in the data.

    Parameters:
        mode          — 'bullish', 'bearish', or 'both'
        distance_pct  — max % distance between close and aVWAP to qualify
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

    # Bullish: red zone + bear aVWAP nearby (support being tested)
    if mode in ('bullish', 'both') and is_red:
        bear_cols = [c for c in df.columns
                     if c.startswith('aVWAP_QQEMOD_bear_') and pd.notna(latest.get(c))]
        for col in bear_cols:
            avwap_val = float(latest[col])
            dist = (close - avwap_val) / avwap_val * 100.0
            if abs(dist) <= distance_pct:
                signals.append({
                    'Signal': 'bullish_pullback_to_aVWAP',
                    'Close': close,
                    'aVWAP': avwap_val,
                    'Distance_Pct': round(dist, 3),
                    'aVWAP_Column': col,
                    'Zone': 'red',
                })

    # Bearish: teal zone + bull aVWAP nearby (resistance being tested)
    if mode in ('bearish', 'both') and is_teal:
        bull_cols = [c for c in df.columns
                     if c.startswith('aVWAP_QQEMOD_bull_') and pd.notna(latest.get(c))]
        for col in bull_cols:
            avwap_val = float(latest[col])
            dist = (close - avwap_val) / avwap_val * 100.0
            if abs(dist) <= distance_pct:
                signals.append({
                    'Signal': 'bearish_pullback_to_aVWAP',
                    'Close': close,
                    'aVWAP': avwap_val,
                    'Distance_Pct': round(dist, 3),
                    'aVWAP_Column': col,
                    'Zone': 'teal',
                })

    if not signals:
        return pd.DataFrame()

    return pd.DataFrame(signals, index=[df.index[-1]] * len(signals))
