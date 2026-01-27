import time
from pathlib import Path
from typing import Union, List, Optional, Tuple
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

def vis(tickers=None, timeframes=None, ind_confs=None, scan_file=None):
    """
    Enhanced visualization supporting multiple tickers, timeframes, and indicator configs
    
    MAIN LOGIC FLOW:
    1. Scan file mode - Direct visualization from scan results
    2. Multi-chart mode - Multiple tickers/timeframes with indicators
    3. Tickers-only mode - Multiple tickers, single timeframe
    4. Timeframes-only mode - Single ticker, multiple timeframes
    5. Default mode - Single ticker, default timeframe
    
    Parameters:
    -----------
    tickers : str or list, optional
        Ticker symbols to visualize (e.g., 'MSFT' or ['MSFT', 'AAPL'])
        Default: 'BTCUSD'
    
    timeframes : str or list, optional
        Timeframes to use (e.g., 'd' or ['d', 'w', '4h'])
        Supported: 'd' (daily), 'w' (weekly), '4h' (4-hour), 
                  'h' (1-hour), '5min' (5-minute)
        Default: ['d'] (daily)
    
    ind_confs : str or list, optional
        Indicator configuration versions to apply
        (e.g., '2' or ['1', '2', '3'])
        Default: '2'
    
    scan_file : str or Path, optional
        Path to scan file for scan visualization mode
        Overrides other parameters when provided
    
    Returns:
    --------
    None - Displays charts directly
    """
    
    # SCAN FILE MODE -------------------------------------- 
    if scan_file:
        _handle_scan_mode(scan_file)
        return
    
    # Parse inputs - ensure they're lists
    tickers = _ensure_list(tickers)
    timeframes = _ensure_list(timeframes)
    ind_confs = _ensure_list(ind_confs)
    
    # MULTI-CHART MODE ------------------------------------ 
    if tickers and timeframes:
        _handle_multi_chart_mode(tickers, timeframes, ind_confs)
    
    # TICKERS-ONLY MODE ----------------------------------- 
    elif tickers:
        _handle_tickers_only_mode(tickers, ind_confs)
    
    # TIMEFRAMES-ONLY MODE -------------------------------- 
    elif timeframes:
        _handle_timeframes_only_mode(timeframes, ind_confs)
    
    # DEFAULT MODE ---------------------------------------- 
    else:
        _handle_default_mode(ind_confs)

def _ensure_list(item: Union[str, List, None]) -> List:
    """Convert string or None to list for consistent processing."""
    if item is None:
        return []
    if isinstance(item, str):
        return [item]
    return item

def _expand_inputs(tickers: List[str], timeframes: List[str]) -> Tuple[List[str], List[str]]:
    """Expand single timeframe/ticker for multiple charts."""
    if len(timeframes) == 1 and len(tickers) > 1:
        timeframes = timeframes * len(tickers)
    elif len(tickers) == 1 and len(timeframes) > 1:
        tickers = tickers * len(timeframes)
    return tickers, timeframes

def _validate_lengths(tickers: List[str], timeframes: List[str], ind_confs: List[str], 
                     mode: str = "multi-chart") -> bool:
    """Validate input list lengths with user-friendly error messages."""
    if mode == "multi-chart":
        if len(tickers) != len(timeframes):
            print(f"Error: Mismatch between {len(tickers)} tickers and {len(timeframes)} timeframes")
            print("  Options:")
            print("  1. Use same number of tickers and timeframes")
            print("  2. Use 1 timeframe for all tickers (will be repeated)")
            print("  3. Use 1 ticker for all timeframes (will be repeated)")
            return False
    
    if ind_confs and len(ind_confs) not in (1, len(tickers) if tickers else len(timeframes)):
        target_len = len(tickers) if tickers else len(timeframes)
        print(f"Error: {len(ind_confs)} ind-confs provided for {target_len} charts")
        print("  Options:")
        print(f"  1. Use single ind-conf for all (e.g., '--ind-conf {DEFAULT_INDCONF}')")
        print(f"  2. Use {target_len} ind-confs (e.g., '--ind-conf {','.join([DEFAULT_INDCONF]*target_len)}')")
        return False
    
    return True

def _prepare_ind_confs(ind_confs: List[str], target_len: int) -> List[str]:
    """Prepare indicator configurations for the target number of charts."""
    if not ind_confs:
        return [DEFAULT_INDCONF] * target_len
    if len(ind_confs) == 1:
        return ind_confs * target_len
    return ind_confs

def _fetch_and_process_chart(ticker: str, timeframe: str, ind_conf: str) -> Optional:
    """Fetch and process data for a single chart configuration."""
    # Map timeframe code to full name
    full_timeframe = TIMEFRAME_MAP.get(timeframe, timeframe)
    
    # Fetch data
    df = fetch_ticker(timeframe=full_timeframe, ticker=ticker, api_key=API_KEY)
    if df is None or df.empty:
        print(f"Warning: No data fetched for {ticker}_{full_timeframe}")
        return None
    
    # Load and apply indicators
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

# ============================================================================
# MODE-SPECIFIC FUNCTIONS
# ============================================================================

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

def _handle_multi_chart_mode(tickers: List[str], timeframes: List[str], ind_confs: List[str]) -> None:
    """MULTI-CHART MODE - Multiple tickers/timeframes with indicators."""
    # Expand inputs if needed
    tickers, timeframes = _expand_inputs(tickers, timeframes)
    
    # Prepare indicator configurations
    ind_confs = _prepare_ind_confs(ind_confs, len(timeframes))
    
    # Validate lengths
    if not _validate_lengths(tickers, timeframes, ind_confs, mode="multi-chart"):
        return
    
    # Process each chart
    dfs = []
    for i, (ticker, timeframe) in enumerate(zip(tickers, timeframes)):
        df = _fetch_and_process_chart(ticker, timeframe, ind_confs[i])
        if df is not None:
            dfs.append(df)
    
    if dfs:
        subcharts(df_list=dfs, ticker=tickers, show_volume=False, show_banker_RSI=True)

def _handle_tickers_only_mode(tickers: List[str], ind_confs: List[str]) -> None:
    """TICKERS-ONLY MODE - Multiple tickers, single timeframe."""
    # Prepare indicator configurations
    ind_confs = _prepare_ind_confs(ind_confs, len(tickers))
    
    # Validate lengths
    if not _validate_lengths(tickers, [], ind_confs, mode="tickers"):
        return
    
    # Process each ticker with daily timeframe
    dfs = []
    for i, ticker in enumerate(tickers):
        df = _fetch_and_process_chart(ticker, 'd', ind_confs[i])
        if df is not None:
            dfs.append(df)
    
    if dfs:
        subcharts(df_list=dfs, ticker=tickers, show_volume=False, show_banker_RSI=True)

def _handle_timeframes_only_mode(timeframes: List[str], ind_confs: List[str]) -> None:
    """TIMEFRAMES-ONLY MODE - Single ticker, multiple timeframes."""
    # Prepare indicator configurations
    ind_confs = _prepare_ind_confs(ind_confs, len(timeframes))
    
    # Validate lengths
    if not _validate_lengths([], timeframes, ind_confs, mode="timeframes"):
        return
    
    # Process each timeframe with default ticker
    dfs = []
    ticker_list = []
    for i, timeframe in enumerate(timeframes):
        df = _fetch_and_process_chart(DEFAULT_TICKER, timeframe, ind_confs[i])
        if df is not None:
            dfs.append(df)
            ticker_list.append(DEFAULT_TICKER)
    
    if dfs:
        subcharts(df_list=dfs, ticker=ticker_list, show_volume=False, show_banker_RSI=True)

def _handle_default_mode(ind_confs: List[str]) -> None:
    """DEFAULT MODE - Single ticker, default timeframe."""
    # Determine indicator config
    ind_conf_to_use = ind_confs[0] if ind_confs else DEFAULT_INDCONF
    
    # Process single chart
    df = _fetch_and_process_chart(DEFAULT_TICKER, DEFAULT_TIMEFRAME, ind_conf_to_use)
    if df is not None:
        subcharts(df_list=[df], ticker=[DEFAULT_TICKER], show_volume=False, show_banker_RSI=True)
