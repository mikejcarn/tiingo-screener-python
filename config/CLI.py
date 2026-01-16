# from pathlib import Path
# import argparse
# from config.data_manager import dm
#
# def init_cli(vis, fetch, ind, scan, full_run):
#     """Enhanced CLI using DataManager"""
#     parser = argparse.ArgumentParser(description="Stock Analysis Toolkit")
#
#     # Visualization
#     parser.add_argument('--vis', action='store_true', help='Launch visualization')
#     parser.add_argument('--ticker', type=str, default=None, help='Specify ticker for visualization')
#     parser.add_argument('--scan-file', type=str, default=None, help='Specify scan file')
#     parser.add_argument('--timeframe', type=str, default=None, help="Specify timeframe (eg '1hour')")
#     parser.add_argument('--ind-conf', type=str, default=None, 
#                        help='Indicator config (used for both visualization and generation)')
#
#     # Data processing
#     parser.add_argument('--fetch', action='store_true', help='Fetch ticker data')
#     parser.add_argument('--ind', action='store_true', help='Generate indicators')
#     parser.add_argument('--scan', action='store_true', help='Run scanner')
#     parser.add_argument('--scan-list', type=str, default=None, help='Specify scan list version')
#     parser.add_argument('--full-run', action='store_true', help='Reset + Tickers + Indicators + Scanner')
#
#     # Folder management
#     parser.add_argument('--clear-all', action='store_true', help='Clear all data folders (preserves versions)')
#     parser.add_argument('--clear-tickers', action='store_true', help='Clear tickers data')
#     parser.add_argument('--clear-indicators', action='store_true', help='Clear only indicator buffer files')
#     parser.add_argument('--clear-scans', action='store_true', help='Clear only scan buffer files')
#     parser.add_argument('--clear-screenshots', action='store_true', help='Clear screenshots')
#
#     # Version control - Indicators
#     parser.add_argument('--save-ind', type=str, metavar='NAME', help='Save current indicators as version')
#     parser.add_argument('--load-ind', type=str, metavar='NAME', help='Load specific indicator version')
#     parser.add_argument('--list-ind', action='store_true', help='List available indicator files in buffer')
#     parser.add_argument('--list-ind-ver', action='store_true', help='List available indicator versions')
#     parser.add_argument('--delete-ind', type=str, metavar='NAME', help='Delete specific indicator version')
#     parser.add_argument('--delete-ind-all', action='store_true', help='Delete ALL indicator versions')
#
#     # Version control - Scans
#     parser.add_argument('--save-scan', type=str, metavar='NAME', help='Save current scans as version')
#     parser.add_argument('--load-scan', type=str, metavar='NAME', help='Load specific scan version')
#     parser.add_argument('--list-scans', action='store_true', help='Show available scan files in buffer')
#     parser.add_argument('--list-scans-ver', action='store_true', help='List available scan versions')
#     parser.add_argument('--delete-scan', type=str, metavar='NAME', help='Delete specific scan version')
#     parser.add_argument('--delete-scan-all', action='store_true', help='Delete ALL scan versions')
#
#     # Version control - Tickers (new)
#     parser.add_argument('--save-tickers', type=str, metavar='NAME', help='Save current tickers as version')
#     parser.add_argument('--load-tickers', type=str, metavar='NAME', help='Load specific ticker version')
#     parser.add_argument('--list-tickers', action='store_true', help='List available ticker files in buffer')
#     parser.add_argument('--list-tickers-ver', action='store_true', help='List available ticker versions')
#     parser.add_argument('--delete-tickers', type=str, metavar='NAME', help='Delete specific ticker version')
#     parser.add_argument('--delete-tickers-all', action='store_true', help='Delete ALL ticker versions')
#     parser.add_argument('--ticker-timeframe', type=str, default=None, 
#                        help='Filter tickers by timeframe (e.g., daily, weekly)')
#
#     args = parser.parse_args()
#
#     # Execute commands using functions from app.py
#     if args.vis: 
#         vis(ticker=args.ticker, scan_file=args.scan_file, 
#             timeframe=args.timeframe, version=args.ind_conf)
#     elif args.fetch: 
#         fetch()
#     elif args.ind: 
#         ind(args.ind_conf)
#     elif args.scan: 
#         scan(args.scan_list)
#     elif args.full_run: 
#         full_run(fetch, ind, scan)
#    
#     # Clear commands
#     elif args.clear_tickers: 
#         dm.clear_buffer(dm.tickers_dir)
#     elif args.clear_indicators: 
#         dm.clear_buffer(dm.indicators_dir)
#     elif args.clear_scans: 
#         dm.clear_buffer(dm.scanner_dir, "scan_results_*.csv")
#     elif args.clear_screenshots: 
#         dm.clear_buffer(dm.screenshots_dir)
#     elif args.clear_all: 
#         dm.clear_all_buffers()
#    
#     # Indicator commands
#     elif args.list_ind: 
#         dm.list_ind()
#     elif args.list_ind_ver: 
#         dm.list_versions(dm.indicators_dir, "Indicators")
#     elif args.save_ind: 
#         dm.save_indicators(args.save_ind)
#     elif args.load_ind: 
#         dm.load_version(dm.indicators_dir, args.load_ind)
#     elif args.delete_ind: 
#         dm.delete_version(dm.indicators_dir, args.delete_ind)
#     elif args.delete_ind_all: 
#         dm.delete_all_versions(dm.indicators_dir)
#    
#     # Scan commands
#     elif args.list_scans: 
#         dm.list_scans()
#     elif args.list_scans_ver: 
#         dm.list_versions(dm.scanner_dir, "Scan")
#     elif args.save_scan: 
#         dm.save_scans(args.save_scan)
#     elif args.load_scan: 
#         dm.load_version(dm.scanner_dir, args.load_scan, "scan_results_*.csv")
#     elif args.delete_scan: 
#         dm.delete_version(dm.scanner_dir, args.delete_scan)
#     elif args.delete_scan_all: 
#         dm.delete_all_versions(dm.scanner_dir)
#    
#     # Ticker commands (new)
#     elif args.list_tickers: 
#         dm.list_tickers(timeframe=args.ticker_timeframe)
#     elif args.list_tickers_ver: 
#         dm.list_versions(dm.tickers_dir, "Tickers")
#     elif args.save_tickers: 
#         dm.save_tickers(args.save_tickers)
#     elif args.load_tickers: 
#         dm.load_version(dm.tickers_dir, args.load_tickers)
#     elif args.delete_tickers: 
#         dm.delete_version(dm.tickers_dir, args.delete_tickers)
#     elif args.delete_tickers_all: 
#         dm.delete_all_versions(dm.tickers_dir)
#    
#     else: 
#         show_help()
#
# def show_help() -> None:
#     """Display comprehensive help"""
#     print("""
#   STOCK ANALYSIS TOOLKIT - COMMAND REFERENCE:
#
#   MAIN FUNCTIONS:
#   --full-run                  Run full process: fetch > indicators > scan
#   --fetch                     Download tickers from API to tickers buffer
#   --ind                       Calculate indicators from tickers buffer
#       --ind-conf              Specify indicator config for generation ("1", "2", "3", "4")
#   --scan                      Run scanner on indicators buffer
#       --scan-list             Specify scan list ("scan_list_1")
#   --vis                       Launch visualization
#       --ticker                Specify ticker ("MSFT")
#       --timeframe             Specify timeframe ("d", "w", "4h", "h", "5min")
#       --ind-conf              Specify indicator version for visualization ("1", "2", "3", "4")
#       --scan-file             Specify scan file ("scan_results_*.csv") 
#
#   LIST DATA:
#   --list-tickers              List ticker files in buffer
#   --list-ind                  List indicator files in buffer
#   --list-scans                List scan files in buffer
#   --list-tickers-ver          List saved ticker versions
#   --list-ind-ver              List saved indicator versions
#   --list-scans-ver            List saved scan versions
#
#   SAVE/LOAD/DELETE DATA:
#   --save-tickers              Save tickers in buffer to version ("tickers_1")
#   --load-tickers              Load tickers version to buffer ("tickers_1")
#   --delete-tickers            Delete tickers version ("tickers_1")
#   --delete-tickers-all        Delete ALL ticker versions
#   --save-ind                  Save indicators in buffer to version ("ind_conf_1")
#   --load-ind                  Load indicators version to buffer ("ind_conf_1")
#   --delete-ind                Delete indicators version ("ind_conf_1")
#   --delete-ind-all            Delete ALL indicator versions
#   --save-scan                 Save current scans to version ("scan_list_1")
#   --load-scan                 Load scans version 
#   --delete-scan               Delete scans version  
#   --delete-scan-all           Delete ALL scans versions
#
#   BUFFER MANAGEMENT:           
#   --clear-all                 Reset all buffers (keep versions)
#   --clear-tickers             Clear tickers buffer
#   --clear-indicators          Clear indicator buffer
#   --clear-scans               Clear scan buffer
#   --clear-screenshots         Clear screenshots buffer
# """)






# from pathlib import Path
# import argparse
# from config.data_manager import dm
#
# def init_cli(vis, fetch, ind, scan, full_run):
#     """Enhanced CLI using DataManager"""
#     parser = argparse.ArgumentParser(description="Stock Analysis Toolkit")
#
#     # Visualization - updated for multiple tickers
#     parser.add_argument('--vis', action='store_true', help='Launch visualization')
#     parser.add_argument('--ticker', type=str, default=None, 
#                        help='Specify ticker(s) for visualization (comma-separated)')
#     parser.add_argument('--timeframe', type=str, default=None, 
#                        help="Specify timeframe(s) (comma-separated, e.g., 'd,w,4h')")
#     parser.add_argument('--ind-conf', type=str, default=None, 
#                        help='Indicator config (used for both visualization and generation)')
#     parser.add_argument('--scan-file', type=str, default=None, help='Specify scan file')
#
#     # Data processing
#     parser.add_argument('--fetch', action='store_true', help='Fetch ticker data')
#     parser.add_argument('--ind', action='store_true', help='Generate indicators')
#     parser.add_argument('--scan', action='store_true', help='Run scanner')
#     parser.add_argument('--scan-list', type=str, default=None, help='Specify scan list version')
#     parser.add_argument('--full-run', action='store_true', help='Reset + Tickers + Indicators + Scanner')
#
#     # Folder management
#     parser.add_argument('--clear-all', action='store_true', help='Clear all data folders (preserves versions)')
#     parser.add_argument('--clear-tickers', action='store_true', help='Clear tickers data')
#     parser.add_argument('--clear-indicators', action='store_true', help='Clear only indicator buffer files')
#     parser.add_argument('--clear-scans', action='store_true', help='Clear only scan buffer files')
#     parser.add_argument('--clear-screenshots', action='store_true', help='Clear screenshots')
#
#     # Version control - Indicators
#     parser.add_argument('--save-ind', type=str, metavar='NAME', help='Save current indicators as version')
#     parser.add_argument('--load-ind', type=str, metavar='NAME', help='Load specific indicator version')
#     parser.add_argument('--list-ind', action='store_true', help='List available indicator files in buffer')
#     parser.add_argument('--list-ind-ver', action='store_true', help='List available indicator versions')
#     parser.add_argument('--delete-ind', type=str, metavar='NAME', help='Delete specific indicator version')
#     parser.add_argument('--delete-ind-all', action='store_true', help='Delete ALL indicator versions')
#
#     # Version control - Scans
#     parser.add_argument('--save-scan', type=str, metavar='NAME', help='Save current scans as version')
#     parser.add_argument('--load-scan', type=str, metavar='NAME', help='Load specific scan version')
#     parser.add_argument('--list-scans', action='store_true', help='Show available scan files in buffer')
#     parser.add_argument('--list-scans-ver', action='store_true', help='List available scan versions')
#     parser.add_argument('--delete-scan', type=str, metavar='NAME', help='Delete specific scan version')
#     parser.add_argument('--delete-scan-all', action='store_true', help='Delete ALL scan versions')
#
#     # Version control - Tickers (new)
#     parser.add_argument('--save-tickers', type=str, metavar='NAME', help='Save current tickers as version')
#     parser.add_argument('--load-tickers', type=str, metavar='NAME', help='Load specific ticker version')
#     parser.add_argument('--list-tickers', action='store_true', help='List available ticker files in buffer')
#     parser.add_argument('--list-tickers-ver', action='store_true', help='List available ticker versions')
#     parser.add_argument('--delete-tickers', type=str, metavar='NAME', help='Delete specific ticker version')
#     parser.add_argument('--delete-tickers-all', action='store_true', help='Delete ALL ticker versions')
#     parser.add_argument('--ticker-timeframe', type=str, default=None, 
#                        help='Filter tickers by timeframe (e.g., daily, weekly)')
#
#     args = parser.parse_args()
#
#     # Parse multiple tickers and timeframes
#     tickers = args.ticker.split(',') if args.ticker else None
#     timeframes = args.timeframe.split(',') if args.timeframe else None
#    
#     # Execute commands using functions from app.py
#     if args.vis: 
#         vis(tickers=tickers, timeframes=timeframes, scan_file=args.scan_file, 
#             version=args.ind_conf)
#     elif args.fetch: 
#         fetch()
#     elif args.ind: 
#         ind(args.ind_conf)
#     elif args.scan: 
#         scan(args.scan_list)
#     elif args.full_run: 
#         full_run(fetch, ind, scan)
#    
#     # Clear commands
#     elif args.clear_tickers: 
#         dm.clear_buffer(dm.tickers_dir)
#     elif args.clear_indicators: 
#         dm.clear_buffer(dm.indicators_dir)
#     elif args.clear_scans: 
#         dm.clear_buffer(dm.scanner_dir, "scan_results_*.csv")
#     elif args.clear_screenshots: 
#         dm.clear_buffer(dm.screenshots_dir)
#     elif args.clear_all: 
#         dm.clear_all_buffers()
#    
#     # Indicator commands
#     elif args.list_ind: 
#         dm.list_ind()
#     elif args.list_ind_ver: 
#         dm.list_versions(dm.indicators_dir, "Indicators")
#     elif args.save_ind: 
#         dm.save_indicators(args.save_ind)
#     elif args.load_ind: 
#         dm.load_version(dm.indicators_dir, args.load_ind)
#     elif args.delete_ind: 
#         dm.delete_version(dm.indicators_dir, args.delete_ind)
#     elif args.delete_ind_all: 
#         dm.delete_all_versions(dm.indicators_dir)
#    
#     # Scan commands
#     elif args.list_scans: 
#         dm.list_scans()
#     elif args.list_scans_ver: 
#         dm.list_versions(dm.scanner_dir, "Scan")
#     elif args.save_scan: 
#         dm.save_scans(args.save_scan)
#     elif args.load_scan: 
#         dm.load_version(dm.scanner_dir, args.load_scan, "scan_results_*.csv")
#     elif args.delete_scan: 
#         dm.delete_version(dm.scanner_dir, args.delete_scan)
#     elif args.delete_scan_all: 
#         dm.delete_all_versions(dm.scanner_dir)
#    
#     # Ticker commands (new)
#     elif args.list_tickers: 
#         dm.list_tickers(timeframe=args.ticker_timeframe)
#     elif args.list_tickers_ver: 
#         dm.list_versions(dm.tickers_dir, "Tickers")
#     elif args.save_tickers: 
#         dm.save_tickers(args.save_tickers)
#     elif args.load_tickers: 
#         dm.load_version(dm.tickers_dir, args.load_tickers)
#     elif args.delete_tickers: 
#         dm.delete_version(dm.tickers_dir, args.delete_tickers)
#     elif args.delete_tickers_all: 
#         dm.delete_all_versions(dm.tickers_dir)
#    
#     else: 
#         show_help()
#
# def show_help() -> None:
#     """Display comprehensive help"""
#     print("""
#   STOCK ANALYSIS TOOLKIT - COMMAND REFERENCE:
#
#   MAIN FUNCTIONS:
#   --full-run                  Run full process: fetch > indicators > scan
#   --fetch                     Download tickers from API to tickers buffer
#   --ind                       Calculate indicators from tickers buffer
#       --ind-conf              Specify indicator config for generation ("1", "2", "3", "4")
#   --scan                      Run scanner on indicators buffer
#       --scan-list             Specify scan list ("scan_list_1")
#  
#   VISUALIZATION:
#   --vis                       Launch visualization
#       --ticker                Specify ticker(s) ("MSFT" or "MSFT,AAPL,GOOGL")
#       --timeframe             Specify timeframe(s) ("d" or "d,w,4h" or "d,d,d" for multiple)
#       --ind-conf              Specify indicator config ("1", "2", "3", "4")
#       --scan-file             Specify scan file ("scan_results_*.csv") 
#
#       Examples:               python app.py --vis --ticker MSFT --ind-conf 1
#                                             --vis --ticker MSFT,AAPL,GOOGL --timeframe d
#                                             --vis --ticker MSFT --timeframe d,w,4h
#                                             --vis --ticker MSFT,AAPL --timeframe w,d
#
#   LIST DATA:
#   --list-tickers              List ticker files in buffer
#   --list-ind                  List indicator files in buffer
#   --list-scans                List scan files in buffer
#   --list-tickers-ver          List saved ticker versions
#   --list-ind-ver              List saved indicator versions
#   --list-scans-ver            List saved scan versions
#
#   SAVE/LOAD/DELETE DATA:
#   --save-tickers              Save tickers in buffer to version ("tickers_1")
#   --load-tickers              Load tickers version to buffer ("tickers_1")
#   --delete-tickers            Delete tickers version ("tickers_1")
#   --delete-tickers-all        Delete ALL ticker versions
#   --save-ind                  Save indicators in buffer to version ("ind_conf_1")
#   --load-ind                  Load indicators version to buffer ("ind_conf_1")
#   --delete-ind                Delete indicators version ("ind_conf_1")
#   --delete-ind-all            Delete ALL indicator versions
#   --save-scan                 Save current scans to version ("scan_list_1")
#   --load-scan                 Load scans version 
#   --delete-scan               Delete scans version  
#   --delete-scan-all           Delete ALL scans versions
#
#   BUFFER MANAGEMENT:           
#   --clear-all                 Reset all buffers (keep versions)
#   --clear-tickers             Clear tickers buffer
#   --clear-indicators          Clear indicator buffer
#   --clear-scans               Clear scan buffer
#   --clear-screenshots         Clear screenshots buffer
# """)



from pathlib import Path
import argparse
from config.data_manager import dm

def init_cli(vis, fetch, ind, scan, full_run):
    """Enhanced CLI using DataManager"""
    parser = argparse.ArgumentParser(description="Stock Analysis Toolkit")

    # Visualization - updated for multiple tickers, timeframes, AND indicator configs
    parser.add_argument('--vis', action='store_true', help='Launch visualization')
    parser.add_argument('--ticker', type=str, default=None, 
                       help='Specify ticker(s) for visualization (comma-separated)')
    parser.add_argument('--timeframe', type=str, default=None, 
                       help="Specify timeframe(s) (comma-separated, e.g., 'd,w,4h')")
    parser.add_argument('--ind-conf', type=str, default=None, 
                       help='Indicator config(s) (comma-separated, e.g., "1,2,3" or "2,2,2")')
    parser.add_argument('--scan-file', type=str, default=None, help='Specify scan file')

    # Data processing
    parser.add_argument('--fetch', action='store_true', help='Fetch ticker data')
    parser.add_argument('--ind', action='store_true', help='Generate indicators')
    parser.add_argument('--scan', action='store_true', help='Run scanner')
    parser.add_argument('--scan-list', type=str, default=None, help='Specify scan list version')
    parser.add_argument('--full-run', action='store_true', help='Reset + Tickers + Indicators + Scanner')

    # Folder management
    parser.add_argument('--clear-all', action='store_true', help='Clear all data folders (preserves versions)')
    parser.add_argument('--clear-tickers', action='store_true', help='Clear tickers data')
    parser.add_argument('--clear-indicators', action='store_true', help='Clear only indicator buffer files')
    parser.add_argument('--clear-scans', action='store_true', help='Clear only scan buffer files')
    parser.add_argument('--clear-screenshots', action='store_true', help='Clear screenshots')

    # Version control - Indicators
    parser.add_argument('--save-ind', type=str, metavar='NAME', help='Save current indicators as version')
    parser.add_argument('--load-ind', type=str, metavar='NAME', help='Load specific indicator version')
    parser.add_argument('--list-ind', action='store_true', help='List available indicator files in buffer')
    parser.add_argument('--list-ind-ver', action='store_true', help='List available indicator versions')
    parser.add_argument('--delete-ind', type=str, metavar='NAME', help='Delete specific indicator version')
    parser.add_argument('--delete-ind-all', action='store_true', help='Delete ALL indicator versions')

    # Version control - Scans
    parser.add_argument('--save-scan', type=str, metavar='NAME', help='Save current scans as version')
    parser.add_argument('--load-scan', type=str, metavar='NAME', help='Load specific scan version')
    parser.add_argument('--list-scans', action='store_true', help='Show available scan files in buffer')
    parser.add_argument('--list-scans-ver', action='store_true', help='List available scan versions')
    parser.add_argument('--delete-scan', type=str, metavar='NAME', help='Delete specific scan version')
    parser.add_argument('--delete-scan-all', action='store_true', help='Delete ALL scan versions')

    # Version control - Tickers (new)
    parser.add_argument('--save-tickers', type=str, metavar='NAME', help='Save current tickers as version')
    parser.add_argument('--load-tickers', type=str, metavar='NAME', help='Load specific ticker version')
    parser.add_argument('--list-tickers', action='store_true', help='List available ticker files in buffer')
    parser.add_argument('--list-tickers-ver', action='store_true', help='List available ticker versions')
    parser.add_argument('--delete-tickers', type=str, metavar='NAME', help='Delete specific ticker version')
    parser.add_argument('--delete-tickers-all', action='store_true', help='Delete ALL ticker versions')
    parser.add_argument('--ticker-timeframe', type=str, default=None, 
                       help='Filter tickers by timeframe (e.g., daily, weekly)')

    args = parser.parse_args()

    # Parse multiple inputs
    tickers = args.ticker.split(',') if args.ticker else None
    timeframes = args.timeframe.split(',') if args.timeframe else None
    ind_confs = args.ind_conf.split(',') if args.ind_conf else None
    
    # Execute commands using functions from app.py
    if args.vis: 
        vis(tickers=tickers, timeframes=timeframes, ind_confs=ind_confs, 
            scan_file=args.scan_file)
    elif args.fetch: 
        fetch()
    elif args.ind: 
        ind(args.ind_conf)  # Note: ind() function still takes single ind_conf
    elif args.scan: 
        scan(args.scan_list)
    elif args.full_run: 
        full_run(fetch, ind, scan)
    
    # Clear commands
    elif args.clear_tickers: 
        dm.clear_buffer(dm.tickers_dir)
    elif args.clear_indicators: 
        dm.clear_buffer(dm.indicators_dir)
    elif args.clear_scans: 
        dm.clear_buffer(dm.scanner_dir, "scan_results_*.csv")
    elif args.clear_screenshots: 
        dm.clear_buffer(dm.screenshots_dir)
    elif args.clear_all: 
        dm.clear_all_buffers()
    
    # Indicator commands
    elif args.list_ind: 
        dm.list_ind()
    elif args.list_ind_ver: 
        dm.list_versions(dm.indicators_dir, "Indicators")
    elif args.save_ind: 
        dm.save_indicators(args.save_ind)
    elif args.load_ind: 
        dm.load_version(dm.indicators_dir, args.load_ind)
    elif args.delete_ind: 
        dm.delete_version(dm.indicators_dir, args.delete_ind)
    elif args.delete_ind_all: 
        dm.delete_all_versions(dm.indicators_dir)
    
    # Scan commands
    elif args.list_scans: 
        dm.list_scans()
    elif args.list_scans_ver: 
        dm.list_versions(dm.scanner_dir, "Scan")
    elif args.save_scan: 
        dm.save_scans(args.save_scan)
    elif args.load_scan: 
        dm.load_version(dm.scanner_dir, args.load_scan, "scan_results_*.csv")
    elif args.delete_scan: 
        dm.delete_version(dm.scanner_dir, args.delete_scan)
    elif args.delete_scan_all: 
        dm.delete_all_versions(dm.scanner_dir)
    
    # Ticker commands (new)
    elif args.list_tickers: 
        dm.list_tickers(timeframe=args.ticker_timeframe)
    elif args.list_tickers_ver: 
        dm.list_versions(dm.tickers_dir, "Tickers")
    elif args.save_tickers: 
        dm.save_tickers(args.save_tickers)
    elif args.load_tickers: 
        dm.load_version(dm.tickers_dir, args.load_tickers)
    elif args.delete_tickers: 
        dm.delete_version(dm.tickers_dir, args.delete_tickers)
    elif args.delete_tickers_all: 
        dm.delete_all_versions(dm.tickers_dir)
    
    else: 
        show_help()

def show_help() -> None:
    """Display comprehensive help"""
    print("""
  STOCK ANALYSIS TOOLKIT - COMMAND REFERENCE:

  MAIN FUNCTIONS:
  --fetch                     Download tickers from API to tickers buffer
  --ind                       Calculate indicators from tickers buffer
      --ind-conf              Specify indicator config for generation ("1", "2", "3", "4")
  --scan                      Run scanner on indicators buffer
      --scan-list             Specify scan list ("scan_list_1")
  --full-run                  Run full process: fetch > indicators > scan
  
  VISUALIZATION
  --vis                       Launch visualization
      --ticker                Specify ticker(s) ("MSFT" or "MSFT,AAPL,GOOGL")
      --timeframe             Specify timeframe(s) ("d" or "d,w,4h" or "d,d,d" for multiple)
      --ind-conf              Specify indicator config(s) ("2" or "1,2,3,4")
      --scan-file             Specify scan file ("scan_results_*.csv") 

  EXAMPLES:
    Single ticker:            python app.py --vis --ticker MSFT --timeframe d --ind-conf 2
    Multiple tickers:                       --vis --ticker MSFT,AAPL,GOOGL --timeframe d --ind-conf 2,2,2
    Multiple timeframes:                    --vis --ticker MSFT --timeframe d,w,4h --ind-conf 2,3,4
    Full custom:                            --vis --ticker MSFT,AAPL --timeframe d,w --ind-conf 2,3
    Mixed:                                  --vis --ticker MSFT,AAPL --timeframe d,d,w,w --ind-conf 2,3,1,4

  RULES:
    1. If single ind-conf: Applied to all charts
    2. If ind-conf list matches chart count: Paired 1:1
    3. If mismatch: Single ind-conf repeated OR error shown

  LIST DATA:
  --list-tickers              List ticker files in buffer
  --list-ind                  List indicator files in buffer
  --list-scans                List scan files in buffer
  --list-tickers-ver          List saved ticker versions
  --list-ind-ver              List saved indicator versions
  --list-scans-ver            List saved scan versions

  SAVE/LOAD/DELETE DATA:
  --save-tickers              Save tickers in buffer to version ("tickers_1")
  --load-tickers              Load tickers version to buffer ("tickers_1")
  --delete-tickers            Delete tickers version ("tickers_1")
  --delete-tickers-all        Delete ALL ticker versions
  --save-ind                  Save indicators in buffer to version ("ind_conf_1")
  --load-ind                  Load indicators version to buffer ("ind_conf_1")
  --delete-ind                Delete indicators version ("ind_conf_1")
  --delete-ind-all            Delete ALL indicator versions
  --save-scan                 Save current scans to version ("scan_list_1")
  --load-scan                 Load scans version 
  --delete-scan               Delete scans version  
  --delete-scan-all           Delete ALL scans versions

  BUFFER MANAGEMENT:           
  --clear-all                 Reset all buffers (keep versions)
  --clear-tickers             Clear tickers buffer
  --clear-indicators          Clear indicator buffer
  --clear-scans               Clear scan buffer
  --clear-screenshots         Clear screenshots buffer
""")
