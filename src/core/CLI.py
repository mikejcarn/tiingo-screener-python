from pathlib import Path
import argparse
from src.core.data_manager import dm

def init_cli(vis, fetch, ind, scan, full_run):
    """Enhanced CLI using DataManager"""
    parser = argparse.ArgumentParser(description="Stock Analysis Toolkit")

    # Visualization - updated for multiple tickers, timeframes, AND indicator configs
    parser.add_argument('--vis', action='store_true', help='Launch visualization')
    parser.add_argument('--ticker', type=str, default=None, 
                       help='Specify ticker(s) for visualization (comma-separated)')
    parser.add_argument('--timeframe', type=str, default=None, 
                       help="Specify timeframe(s) for vis, fetch, or ind (comma-separated, e.g., 'd,w,4h' or 'daily,weekly')")
   
    # SINGLE --ind-conf definition that works for both vis() and ind()
    parser.add_argument('--ind-conf', type=str, default=None, 
                       help='Indicator config: single number for --ind (e.g., "2"), comma-separated for --vis (e.g., "1,2,3")')
   
    parser.add_argument('--scan-file', type=str, default=None, help='Specify scan file')

    # Data processing
    parser.add_argument('--fetch', action='store_true', help='Fetch ticker data')
    parser.add_argument('--ind', action='store_true', help='Generate indicators')
    # Note: --ind-conf and --timeframe are already defined above (shared)
    parser.add_argument('--scan', action='store_true', help='Run scanner')
    parser.add_argument('--scan-list', type=str, default=None, help='Specify scan list version')
    parser.add_argument('--full-run', action='store_true', help='Reset + Tickers + Indicators + Scanner')

    # Folder management
    parser.add_argument('--clear-all', action='store_true', help='Clear all data folders (preserves versions)')
    parser.add_argument('--clear-tickers', action='store_true', help='Clear tickers data')
    parser.add_argument('--clear-ind', action='store_true', help='Clear only indicator buffer files')
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

    # Parse timeframe(s) - shared between vis, fetch, and ind
    timeframes = args.timeframe.split(',') if args.timeframe else None
   
    # Parse tickers if provided
    tickers = args.ticker.split(',') if args.ticker else None
   
    # Execute commands using functions from app.py
    if args.vis: 
        # For visualization, ind-conf can be multiple values (comma-separated)
        vis_ind_confs = args.ind_conf.split(',') if args.ind_conf else None
        vis(tickers=tickers, timeframes=timeframes, ind_confs=vis_ind_confs, 
            scan_file=args.scan_file)
   
    elif args.fetch: 
        # Pass timeframes to fetch function (None = use defaults)
        fetch(timeframes=timeframes)
   
    elif args.ind: 
        # For indicators, ind-conf is a single version number (not comma-separated)
        # timeframe is already parsed above
        ind(args.ind_conf, timeframes=timeframes)
   
    elif args.scan: 
        scan(args.scan_list)
   
    elif args.full_run: 
        full_run(fetch, ind, scan)
   
    # Clear commands
    elif args.clear_tickers: 
        dm.clear_buffer(dm.tickers_dir)
    elif args.clear_ind: 
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
      --timeframe             Specify timeframe(s) to fetch (comma-separated, e.g., "daily,weekly")
  --ind                       Calculate indicators from tickers buffer
      --ind-conf              Specify indicator config for generation ("1", "2", "3", "4")
      --timeframe             Specify timeframe(s) to process (comma-separated, e.g., "daily,weekly,4hour")
  --scan                      Run scanner on indicators buffer
      --scan-list             Specify scan list ("scan_list_1")
  --full-run                  Run full process: fetch > indicators > scan

  VISUALIZATION
  --vis                       Launch visualization
      --ticker                Specify ticker(s) ("MSFT" or "MSFT,AAPL,GOOGL")
      --timeframe             Specify timeframe(s) ("d" or "d,w,4h" or "daily,weekly,4hour")
      --ind-conf              Specify indicator config(s) ("2" or "1,2,3,4")
      --scan-file             Specify scan file ("scan_results_*.csv") 

  EXAMPLES:
    Fetch:
      Default timeframes:     python app.py --fetch
      Specific timeframes:    python app.py --fetch --timeframe daily,weekly
      Single timeframe:       python app.py --fetch --timeframe daily

    Visualization:
      Single ticker:          python app.py --vis --ticker MSFT --timeframe d --ind-conf 2
      Multiple tickers:       python app.py --vis --ticker MSFT,AAPL,GOOGL --timeframe d --ind-conf 2,2,2
      Multiple timeframes:    python app.py --vis --ticker MSFT --timeframe d,w,4h --ind-conf 2,3,4
 
    Indicators:
      All timeframes:         python app.py --ind --ind-conf 2
      Single timeframe:       python app.py --ind --ind-conf 2 --timeframe daily
      Multiple timeframes:    python app.py --ind --ind-conf 3 --timeframe daily,weekly

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
  --clear-ind                 Clear indicator buffer
  --clear-scans               Clear scan buffer
  --clear-screenshots         Clear screenshots buffer
""")
