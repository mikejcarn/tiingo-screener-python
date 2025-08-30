import pandas as pd

def calculate_rsi(df, periods=14):

    delta = df['Close'].diff()
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.ewm(alpha=1/periods, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/periods, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return {'RSI': rsi}

def calculate_indicator(df, **params):
    return calculate_rsi(df, **params)
