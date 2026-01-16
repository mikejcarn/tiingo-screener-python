import time
from pathlib import Path
from src.indicators.get_indicators import get_indicators
from src.indicators.run_indicators import run_indicators
from src.fetch_data.fetch_tickers import fetch_tickers
from src.fetch_data.fetch_ticker import fetch_ticker
from src.scanner.scanner import run_scanner
from src.visualization.subcharts import subcharts
from src.scanner.scan_configs.scan_configs import scan_configs
from src.indicators.ind_configs.ind_configs import indicators, params
from config.CLI import init_cli
from config.settings import SCANNER_DIR
from config.data_manager import dm
from config.scan_lists import scan_lists

API_KEY = '9807b06bf5b97a8b26f5ff14bff18ee992dfaa13'

# VISUALIZATION ------------------------------------------


# def vis(scan_file=None, ticker=None, timeframe=None, version=None):
#
#     if not scan_file:
#
#         ticker = ticker or 'BTCUSD'
#
#         if timeframe:
#
#             df = fetch_ticker(timeframe=timeframe, ticker=ticker, api_key=API_KEY)
#             ind_conf_ver = f"{timeframe}_{version}" if version else f"{timeframe}"
#             df = get_indicators(df, indicators[ind_conf_ver], params[ind_conf_ver])
#
#             subcharts(
#                       [df],
#                       ticker=ticker,
#                       show_volume=False,
#                       show_banker_RSI=True
#                      )
#             return
#
#         # df1 = fetch_ticker(timeframe='w',  ticker=ticker, api_key=API_KEY)
#         df2 = fetch_ticker(timeframe='d',  ticker=ticker, api_key=API_KEY)
#         # df3 = fetch_ticker(timeframe='4h', ticker=ticker, api_key=API_KEY)
#         # df4 = fetch_ticker(timeframe='h',  ticker=ticker, api_key=API_KEY)
#
#         # df1 = get_indicators(df1, indicators['weekly_2'], params['weekly_2'])
#         df2 = get_indicators(df2, indicators['daily_2'],  params['daily_2'])
#         # df3 = get_indicators(df3, indicators['4hour_2'],  params['4hour_2'])
#         # df4 = get_indicators(df4, indicators['1hour_2'],  params['1hour_2'])
#
#         subcharts(
#                   [df2],
#                   ticker=ticker,
#                   show_volume=False,
#                   show_banker_RSI=True
#                  )
#         return
#
#     scan_path = Path(scan_file)
#     if not scan_path.exists():
#         scan_path = SCANNER_DIR / scan_path.name
#
#     if not scan_path.exists():
#         print(f"Error: Scan file not found at {scan_path}")
#         dm.list_scans()
#         return
#
#     subcharts(
#               scan_file=scan_path,
#               show_volume=False,
#               show_banker_RSI=False
#              )


# VISUALIZATION ------------------------------------------


def vis(tickers=None, timeframes=None, ind_confs=None, scan_file=None):
    """
    Enhanced visualization supporting multiple tickers, timeframes, and indicator configs
    
    Parameters:
    - tickers: List of ticker symbols (e.g., ['MSFT', 'AAPL'])
    - timeframes: List of timeframes (e.g., ['d', 'w', '4h'])
    - ind_confs: List of indicator config versions (e.g., ['1', '2', '3'])
    - scan_file: Path to scan file (single visualization mode)
    """
    
    if scan_file:
        # Single scan file visualization (existing behavior)
        scan_path = Path(scan_file)
        if not scan_path.exists():
            scan_path = SCANNER_DIR / scan_path.name
        
        if not scan_path.exists():
            print(f"Error: Scan file not found at {scan_path}")
            dm.list_scans()
            return
        
        subcharts(scan_file=scan_path, show_volume=False, show_banker_RSI=False)
        return
    
    # Helper function to get indicator config
    def get_indicator_config(timeframe_str, ind_conf_num=None):
        """Get indicator config based on timeframe and version"""
        timeframe_map = {
            'd': 'daily', 'w': 'weekly', '4h': '4hour', 
            'h': '1hour', '5min': '5min'
        }
        full_timeframe = timeframe_map.get(timeframe_str, timeframe_str)
        
        if ind_conf_num:
            # Try to get the specific version
            ind_conf_ver = f"{full_timeframe}_{ind_conf_num}"
            if ind_conf_ver in indicators and ind_conf_ver in params:
                return indicators[ind_conf_ver], params[ind_conf_ver]
        
        # Default to version 2 if version not specified or not found
        ind_conf_ver = f"{full_timeframe}_2"
        if ind_conf_ver in indicators and ind_conf_ver in params:
            return indicators[ind_conf_ver], params[ind_conf_ver]
        
        # If still not found, try version 0
        ind_conf_ver = f"{full_timeframe}_0"
        if ind_conf_ver in indicators and ind_conf_ver in params:
            return indicators[ind_conf_ver], params[ind_conf_ver]
        
        # Last resort - return empty configs
        print(f"Warning: No indicator config found for {full_timeframe}")
        return {}, {}
    
    # Parse inputs - ensure they're lists
    if isinstance(tickers, str):
        tickers = [tickers]
    if isinstance(timeframes, str):
        timeframes = [timeframes]
    if isinstance(ind_confs, str):
        ind_confs = [ind_confs]
    
    # Handle multiple tickers/timeframes/ind_confs
    if tickers and timeframes:
        # Ensure tickers and timeframes are lists
        if isinstance(tickers, str):
            tickers = [tickers]
        if isinstance(timeframes, str):
            timeframes = [timeframes]
        
        # Expand if single timeframe for multiple tickers
        if len(timeframes) == 1 and len(tickers) > 1:
            timeframes = timeframes * len(tickers)
        
        # Expand if single ticker for multiple timeframes
        elif len(tickers) == 1 and len(timeframes) > 1:
            tickers = tickers * len(timeframes)
        
        # Handle indicator configs
        if ind_confs:
            if len(ind_confs) == 1:
                # Single ind-conf: apply to all charts
                ind_confs = ind_confs * len(timeframes)
            elif len(ind_confs) != len(timeframes):
                # Mismatch: show error
                print(f"Error: {len(ind_confs)} ind-confs provided for {len(timeframes)} charts")
                print("  Options:")
                print("  1. Use single ind-conf for all (e.g., '--ind-conf 2')")
                print(f"  2. Use {len(timeframes)} ind-confs (e.g., '--ind-conf {','.join(['2']*len(timeframes))}')")
                return
        else:
            # No ind-conf specified: default to '2' for all
            ind_confs = ['2'] * len(timeframes)
        
        # Check for length mismatch
        if len(tickers) != len(timeframes):
            print(f"Error: Mismatch between {len(tickers)} tickers and {len(timeframes)} timeframes")
            print("  Options:")
            print("  1. Use same number of tickers and timeframes")
            print("  2. Use 1 timeframe for all tickers (will be repeated)")
            print("  3. Use 1 ticker for all timeframes (will be repeated)")
            return
        
        dfs = []
        for i, (ticker, timeframe) in enumerate(zip(tickers, timeframes)):
            # Map timeframe codes to full names if needed
            timeframe_map = {
                'd': 'daily', 'w': 'weekly', '4h': '4hour', 
                'h': '1hour', '5min': '5min'
            }
            full_timeframe = timeframe_map.get(timeframe, timeframe)
            
            # Fetch data
            df = fetch_ticker(timeframe=full_timeframe, ticker=ticker, api_key=API_KEY)
            
            # Apply indicators with specific ind-conf if available
            ind_conf_num = ind_confs[i] if i < len(ind_confs) else '2'
            ind_config, ind_params = get_indicator_config(timeframe, ind_conf_num)
            df = get_indicators(df, ind_config, ind_params)
            
            dfs.append(df)
        
        # Visualize all DataFrames with individual ticker labels
        subcharts(df_list=dfs, ticker=tickers, show_volume=False, show_banker_RSI=True)
    
    elif tickers:
        # Multiple tickers with default daily timeframe
        if isinstance(tickers, str):
            tickers = [tickers]
        
        # Handle indicator configs for tickers-only mode
        if ind_confs:
            if len(ind_confs) == 1:
                ind_confs = ind_confs * len(tickers)
            elif len(ind_confs) != len(tickers):
                print(f"Error: {len(ind_confs)} ind-confs provided for {len(tickers)} tickers")
                print(f"  Use single ind-conf or {len(tickers)} ind-confs")
                return
        else:
            ind_confs = ['2'] * len(tickers)
        
        dfs = []
        for i, ticker in enumerate(tickers):
            df = fetch_ticker(timeframe='daily', ticker=ticker, api_key=API_KEY)
            
            # Apply indicators with specific ind-conf
            ind_conf_num = ind_confs[i]
            ind_config, ind_params = get_indicator_config('d', ind_conf_num)
            df = get_indicators(df, ind_config, ind_params)
            
            dfs.append(df)
        
        # Visualize with individual ticker labels
        subcharts(df_list=dfs, ticker=tickers, show_volume=False, show_banker_RSI=True)
    
    elif timeframes:
        # Single default ticker (BTCUSD) with multiple timeframes
        if isinstance(timeframes, str):
            timeframes = [timeframes]
        
        # Handle indicator configs for timeframes-only mode
        if ind_confs:
            if len(ind_confs) == 1:
                ind_confs = ind_confs * len(timeframes)
            elif len(ind_confs) != len(timeframes):
                print(f"Error: {len(ind_confs)} ind-confs provided for {len(timeframes)} timeframes")
                print(f"  Use single ind-conf or {len(timeframes)} ind-confs")
                return
        else:
            ind_confs = ['2'] * len(timeframes)
        
        dfs = []
        for i, timeframe in enumerate(timeframes):
            timeframe_map = {
                'd': 'daily', 'w': 'weekly', '4h': '4hour', 
                'h': '1hour', '5min': '5min'
            }
            full_timeframe = timeframe_map.get(timeframe, timeframe)
            
            df = fetch_ticker(timeframe=full_timeframe, ticker='BTCUSD', api_key=API_KEY)
            
            # Apply indicators with specific ind-conf
            ind_conf_num = ind_confs[i]
            ind_config, ind_params = get_indicator_config(timeframe, ind_conf_num)
            df = get_indicators(df, ind_config, ind_params)
            
            dfs.append(df)
        
        # Create ticker list with BTCUSD repeated for each timeframe
        ticker_list = ['BTCUSD'] * len(timeframes)
        subcharts(df_list=dfs, ticker=ticker_list, show_volume=False, show_banker_RSI=True)
    
    else:
        # Default behavior - single ticker, default timeframes
        ticker = 'BTCUSD'
        
        # Use ind-conf if specified, otherwise default to 2
        ind_conf_to_use = ind_confs[0] if ind_confs else '2'
        
        # Apply ind-conf to all fetched timeframes
        # df1 = fetch_ticker(timeframe='w', ticker=ticker, api_key=API_KEY)
        df2 = fetch_ticker(timeframe='d', ticker=ticker, api_key=API_KEY)
        # df3 = fetch_ticker(timeframe='4h', ticker=ticker, api_key=API_KEY)
        # df4 = fetch_ticker(timeframe='h', ticker=ticker, api_key=API_KEY)

        # if ind_conf_to_use in ['0', '1', '2', '3', '4']:
        #     df1 = get_indicators(df1, indicators.get(f'weekly_{ind_conf_to_use}', {}), 
        #                          params.get(f'weekly_{ind_conf_to_use}', {}))
        
        if ind_conf_to_use in ['0', '1', '2', '3', '4']:
            df2 = get_indicators(df2, indicators.get(f'daily_{ind_conf_to_use}', {}), 
                                 params.get(f'daily_{ind_conf_to_use}', {}))
        
        # if ind_conf_to_use in ['0', '1', '2', '3', '4']:
        #     df3 = get_indicators(df3, indicators.get(f'4hour_{ind_conf_to_use}', {}), 
        #                          params.get(f'4hour_{ind_conf_to_use}', {}))
        
        # if ind_conf_to_use in ['0', '1', '2', '3', '4']:
        #     df4 = get_indicators(df4, indicators.get(f'1hour_{ind_conf_to_use}', {}), 
        #                          params.get(f'1hour_{ind_conf_to_use}', {}))

        subcharts(df_list=[df2], ticker=['BTCUSD'], show_volume=False, show_banker_RSI=True)

# FETCH TICKERS -------------------------------------------


def fetch():

    fetch_tickers(['weekly'], api_key=API_KEY)
    fetch_tickers(['daily'],  api_key=API_KEY)
    fetch_tickers(['4hour'],  api_key=API_KEY)
    fetch_tickers(['1hour'],  api_key=API_KEY)
    # fetch_tickers(['5min'],   api_key=API_KEY)

# INDICATORS ----------------------------------------------


def ind(ind_conf=None):

    match ind_conf:

        case '0':
            run_indicators(indicators['weekly_0'], params['weekly_0'], "weekly")
            run_indicators(indicators['daily_0'],  params['daily_0'],  "daily")
            run_indicators(indicators['4hour_0'],  params['4hour_0'],  "4hour")
            run_indicators(indicators['1hour_0'],  params['1hour_0'],  "1hour")

        case '1':
            run_indicators(indicators['weekly_1'], params['weekly_1'], "weekly")
            run_indicators(indicators['daily_1'],  params['daily_1'],  "daily")
            run_indicators(indicators['4hour_1'],  params['4hour_1'],  "4hour")
            run_indicators(indicators['1hour_1'],  params['1hour_1'],  "1hour")

        case '2':
            run_indicators(indicators['weekly_2'], params['weekly_2'], "weekly")
            run_indicators(indicators['daily_2'],  params['daily_2'],  "daily")
            run_indicators(indicators['4hour_2'],  params['4hour_2'],  "4hour")
            run_indicators(indicators['1hour_2'],  params['1hour_2'],  "1hour")

        case '3':
            run_indicators(indicators['weekly_3'], params['weekly_3'], "weekly")
            run_indicators(indicators['daily_3'],  params['daily_3'],  "daily")
            run_indicators(indicators['4hour_3'],  params['4hour_3'],  "4hour")
            run_indicators(indicators['1hour_3'],  params['1hour_3'],  "1hour")

        case '4':
            run_indicators(indicators['weekly_4'], params['weekly_4'], "weekly")
            run_indicators(indicators['daily_4'],  params['daily_4'],  "daily")
            run_indicators(indicators['4hour_4'],  params['4hour_4'],  "4hour")
            run_indicators(indicators['1hour_4'],  params['1hour_4'],  "1hour")

# SCANNER -------------------------------------------------


def scan(scan_list='2'):

    scans = scan_lists["scan_list_" + scan_list]

    for scan in scans:
        kwargs = {
            'criteria': scan_configs[scan]['criteria'],
            'criteria_params': scan_configs[scan]['params'],
            'scan_name': scan
        }
        # print(kwargs)
        run_scanner(**kwargs)

# FULL RUN ------------------------------------------------


def full_run(fetch, ind, scan) -> None:
    """Standard full run pipeline"""

    # Start timer
    start_time = time.time()

    # FETCH

    # dm.clear_all_buffers()
    # dm.delete_all_versions(dm.tickers_dir)
    # dm.delete_all_versions(dm.indicators_dir)
    # dm.delete_all_versions(dm.scanner_dir)

    # fetch()

    # INDICATORS

    ind('ind_conf_1')
    dm.save_indicators('ind_conf_1')
    dm.clear_buffer(dm.indicators_dir)

    ind('ind_conf_2')
    dm.save_indicators('ind_conf_2')
    dm.clear_buffer(dm.indicators_dir)

    ind('ind_conf_3')
    dm.save_indicators('ind_conf_3')
    dm.clear_buffer(dm.indicators_dir)

    ind('ind_conf_4')
    dm.save_indicators('ind_conf_4')
    dm.clear_buffer(dm.indicators_dir)

    # SCANNER

    # scan(scan_lists['scan_list_1'])
    # dm.save_scans('ind_conf_1')
    # dm.clear_buffer(dm.scanner_dir)
    #
    # scan(scan_lists['scan_list_1'])
    # dm.save_scans('ind_conf_2')
    # dm.clear_buffer(dm.scanner_dir)
    #
    # scan(scan_lists['scan_list_1'])
    # dm.save_scans('ind_conf_3')
    # dm.clear_buffer(dm.scanner_dir)

    # COMPLETE

    total_time = dm.format_duration(time.time() - start_time)
    print(f"\n✅ Standard full run completed in {total_time}")

# COMMAND LINE INTERFACE (CLI) ----------------------------

# RUN 'python app.py' for HELP command list
if __name__ == "__main__": init_cli(vis, fetch, ind, scan, full_run)






