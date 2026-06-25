import time
from pathlib import Path
from typing import Union, List, Optional
from src.indicators.indicators import get_indicators, run_indicators, load_indicator_config
from src.tickers.tickers import fetch_tickers, fetch_ticker
from src.visualization.src.subcharts import subcharts
from src.core.data_manager import dm
from src.core.globals import SCANNER_DIR, API_KEY

# ============================================================================
# CONSTANTS & HELPER FUNCTIONS
# ============================================================================

TIMEFRAME_MAP = {
    'd': 'daily', 'w': 'weekly', '4h': '4hour',
    'h': '1hour', '5min': '5min'
}

DEFAULT_TICKER = 'BTCUSD'
DEFAULT_TIMEFRAME = 'd'
DEFAULT_INDCONF = '2'

# ============================================================================
# MAIN VISUALIZATION FUNCTION
# ============================================================================

def vis(tickers=None, timeframes=None, ind_confs=None, scan_file=None, end_dates=None):
    """
    Enhanced visualization supporting multiple tickers, timeframes, and indicator configs.

    Chart count is driven by whichever input has the most values. All single-value
    inputs are expanded to match. Conflicting multi-value counts (e.g. 2 tickers
    and 3 timeframes) are rejected with an error.

    Parameters:
    -----------
    tickers : str or list, optional
        Ticker symbols to visualize. Default: 'BTCUSD'
    timeframes : str or list, optional
        Timeframes ('d', 'w', '4h', 'h', '5min'). Default: 'd'
    ind_confs : str or list, optional
        Indicator config versions. Default: '2'
    scan_file : str or Path, optional
        Path to scan file — overrides all other params when provided.
    end_dates : list of str, optional
        End date(s) 'YYYY-MM-DD'. Single value applies to all charts;
        multiple values map one-per-chart.
    """

    # SCAN FILE MODE
    if scan_file:
        _handle_scan_mode(scan_file)
        return

    # Parse all inputs to lists
    tickers   = _ensure_list(tickers)
    timeframes = _ensure_list(timeframes)
    ind_confs  = _ensure_list(ind_confs)
    end_dates  = end_dates if end_dates else []

    # Determine chart count from whichever input has the most values
    lengths = [len(x) for x in [tickers, timeframes, ind_confs, end_dates] if x]
    multi = [l for l in lengths if l > 1]

    if len(set(multi)) > 1:
        print(f"Error: Conflicting chart counts — {set(multi)}")
        print("  All multi-value inputs must have the same number of values.")
        return

    target_len = max(multi) if multi else 1

    # Expand single values to fill all charts; apply defaults for missing inputs
    tickers    = _expand(tickers,    target_len, DEFAULT_TICKER)
    timeframes = _expand(timeframes, target_len, DEFAULT_TIMEFRAME)
    ind_confs  = _expand(ind_confs,  target_len, DEFAULT_INDCONF)
    end_dates  = _expand(end_dates,  target_len, None)

    # Fetch and process each chart
    dfs, loaded_tickers, loaded_confs = [], [], []
    for i in range(target_len):
        df = _fetch_and_process_chart(tickers[i], timeframes[i], ind_confs[i], end_dates[i])
        if df is not None:
            dfs.append(df)
            loaded_tickers.append(tickers[i])
            loaded_confs.append(ind_confs[i])

    if dfs:
        subcharts(df_list=dfs, ticker=loaded_tickers, show_volume=False, show_banker_RSI=True, ind_confs=loaded_confs)


def _ensure_list(item: Union[str, List, None]) -> List:
    if item is None:
        return []
    if isinstance(item, str):
        return [item]
    return item


def _expand(items: List, target_len: int, default) -> List:
    """Expand a list to target_len, filling with default if empty or repeating if single."""
    if not items:
        return [default] * target_len
    if len(items) == 1:
        return items * target_len
    return items


# ============================================================================
# CHART FETCH & SCAN MODE
# ============================================================================

def _fetch_and_process_chart(ticker: str, timeframe: str, ind_conf: str, end_date=None) -> Optional[object]:
    """Fetch and process data for a single chart configuration."""
    full_timeframe = TIMEFRAME_MAP.get(timeframe, timeframe)

    df = fetch_ticker(timeframe=full_timeframe, ticker=ticker, end_date=end_date, api_key=API_KEY)
    if df is None or df.empty:
        print(f"Warning: No data fetched for {ticker}_{full_timeframe}")
        return None

    config_result = load_indicator_config(ind_conf, full_timeframe)
    if config_result is None:
        print(f"Warning: Using raw data for {ticker}_{full_timeframe} (no indicators)")
        return df

    ind_config, ind_params = config_result
    if ind_config is not None and ind_params is not None:
        return get_indicators(df, ind_config, ind_params)
    else:
        print(f"Warning: Using raw data for {ticker}_{full_timeframe} (no indicators)")
        return df


def _handle_scan_mode(scan_file: Union[str, Path]) -> None:
    """SCAN FILE MODE - Direct visualization from scan results."""
    scan_path = Path(scan_file)
    if not scan_path.exists():
        scan_path = SCANNER_DIR / scan_path.name

    if not scan_path.exists():
        print(f"Error: Scan file not found at {scan_path}")
        dm.list_scans()
        return

    subcharts(scan_file=scan_path, show_volume=False, show_banker_RSI=False)
