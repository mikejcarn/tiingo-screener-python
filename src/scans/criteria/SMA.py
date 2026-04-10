import pandas as pd

def SMA(
        df,
        sma_periods=[50, 20, 10],
        distance_pct=1.0,
        mode='within',
        outside_range=False
       ):
    """
    Combined SMA scanner that can detect:
    - Price within SMAs
    - Price above/below SMAs
    - Extended moves beyond SMAs
    - SMA order relationships

    Parameters:
        df (pd.DataFrame): DataFrame with price data and SMA columns
        sma_periods (list): List of SMA periods to check (e.g., [50, 200])
            For 'order' mode: Checks if SMAs follow this order (e.g., [50, 20, 10] means SMA_50 < SMA_20 < SMA_10)
            For other modes: ALL periods must pass the criteria for a successful scan
        mode (str): One of ['within', 'above', 'below', 'order'] - determines scan type
        distance_pct (float): Percentage distance threshold
        outside_range (bool):
            - For 'within' mode:
                False = price is within distance_pct of SMA (close to SMA)
                True = price is NOT within distance_pct of SMA (far from SMA)
            - For 'above'/'below' modes:
                False = within distance_pct (normal move)
                True = beyond distance_pct (extended move)
            - For 'order' mode: N/A

    Returns:
        pd.DataFrame: Results with Distance_Pct and Position columns
        For 'order' mode: Returns 1 row if order condition met
        For other modes: Returns 1 row per SMA period ONLY if ALL periods meet criteria
    """

    if len(df) == 0:
        return pd.DataFrame()

    latest = df.iloc[-1]
    results = []

    # Handle 'order' mode separately (already checks ALL periods together)
    if mode == 'order':
        # Check if all required SMA columns exist
        sma_values = {}
        all_exist = True

        for period in sma_periods:
            sma_col = f'SMA_{period}'
            if sma_col not in df.columns or pd.isna(latest[sma_col]):
                all_exist = False
                break
            sma_values[period] = latest[sma_col]

        if all_exist and len(sma_periods) >= 2:
            # Check if SMAs follow the specified order
            order_correct = True

            for i in range(len(sma_periods) - 1):
                current_period = sma_periods[i]
                next_period = sma_periods[i + 1]

                # Check if current SMA is less than next SMA
                if sma_values[current_period] >= sma_values[next_period]:
                    order_correct = False
                    break

            if order_correct:
                # Format the order string
                order_str = ' < '.join([f'SMA_{p}' for p in sma_periods])

                result = latest.copy()
                result['Period'] = 'Order'
                result['Distance_Pct'] = 0.0
                result['Position'] = f'Order: {order_str}'
                results.append(result.to_frame().T)

        return pd.concat(results) if results else pd.DataFrame()

    # For other modes: Check ALL periods must meet criteria
    all_periods_pass = True
    period_results = []

    for period in sma_periods:
        sma_col = f'SMA_{period}'

        # Skip if SMA column doesn't exist or is NaN
        if sma_col not in df.columns or pd.isna(latest[sma_col]):
            all_periods_pass = False
            break

        current_price = latest['Close']
        sma_value = latest[sma_col]

        # Calculate distance percentage (always positive)
        distance = abs(current_price - sma_value) / current_price * 100

        # Determine position relative to SMA
        position = 'Above' if current_price > sma_value else 'Below'

        # Check conditions based on scan mode
        condition_met = False

        if mode == 'within':
            if outside_range:
                # Price is NOT within distance_pct of SMA (far from SMA)
                condition_met = (distance > distance_pct)
                position = 'Outside'
            else:
                # Price is within distance_pct of SMA (close to SMA)
                condition_met = (distance <= distance_pct)
                position = 'Within'

        elif mode == 'above':
            if current_price > sma_value:
                if outside_range:
                    condition_met = (distance > distance_pct)
                    position += ' (Extended)'
                else:
                    condition_met = (distance <= distance_pct)

        elif mode == 'below':
            if current_price < sma_value:
                if outside_range:
                    condition_met = (distance > distance_pct)
                    position += ' (Extended)'
                else:
                    condition_met = (distance <= distance_pct)

        # If this period doesn't meet condition, fail the entire scan
        if not condition_met:
            all_periods_pass = False
            break

        # Store result for this period
        result = latest.copy()
        result['Period'] = period
        result['Distance_Pct'] = distance
        result['Position'] = position
        period_results.append(result.to_frame().T)

    # Only return results if ALL periods passed
    if all_periods_pass and period_results:
        return pd.concat(period_results)

    return pd.DataFrame()
