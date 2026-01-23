import time
import importlib
from pathlib import Path
from src.indicators.indicators import get_indicators, run_indicators, load_indicator_config
from src.tickers.tickers import fetch_tickers, fetch_ticker
from src.scanner.scanner import run_scanner
from src.visualization.visualization import vis
# from src.scanner.scan_configs.scan_configs import scan_configs
from core.CLI import init_cli
from core.data_manager import dm
from core.scan_lists import scan_lists

from core.globals import API_KEY, SCAN_CONF_DIR

# VISUALIZATION ------------------------------------------

# import vis() for init_cli()

# FETCH TICKERS -------------------------------------------


def fetch(timeframes=None):
    """
    Fetch ticker data for specified timeframes.
    
    Parameters:
    - timeframes: List of timeframes to fetch (e.g., ['daily', 'weekly'])
                 If None, uses default timeframes
    """
    # Default timeframes
    if timeframes is None:
        timeframes = ['weekly', 'daily', '4hour', '1hour']
    
    # Handle string input (from CLI)
    if isinstance(timeframes, str):
        if ',' in timeframes:
            timeframes = [tf.strip() for tf in timeframes.split(',')]
        else:
            timeframes = [timeframes]
    
    print(f"\n=== FETCHING TICKERS ===\n")
    print(f"Fetching timeframes: {', '.join(timeframes)}")
    
    for timeframe in timeframes:
        print(f"\nFetching {timeframe} data...")
        fetch_tickers([timeframe], api_key=API_KEY)
    
    print(f"\n✅ Fetch complete for {len(timeframes)} timeframe(s)")

# INDICATORS ----------------------------------------------


def ind(ind_conf=None, timeframes=None):
    """
    Simple wrapper that passes timeframes directly to run_indicators
    """
    if ind_conf is None:
        print("Error: Please specify --ind-conf (1, 2, 3, or 4)")
        return
    
    # Parse comma-separated string into list
    if isinstance(timeframes, str) and ',' in timeframes:
        timeframes = [tf.strip() for tf in timeframes.split(',')]
    
    run_indicators(ind_conf=ind_conf, timeframe=timeframes)

# SCANNER -------------------------------------------------


def scan(scan_list='2'):
    """Simplest scanner using SCAN_CONF_DIR."""
    # Load configs
    scan_configs = {}
    for config_file in Path(SCAN_CONF_DIR).glob('scan_conf_*.py'):
        try:
            module_name = config_file.stem
            module = importlib.import_module(f"src.scanner.scan_configs.{module_name}")
            scan_configs.update(module.scan_conf)
        except Exception as e:
            print(f"Error loading {config_file.stem}: {e}")
            continue
    
    # Run scans
    scans = scan_lists[f"scan_list_{scan_list}"]
    for scan_name in scans:
        if scan_name in scan_configs:
            run_scanner(
                criteria=scan_configs[scan_name]['criteria'],
                criteria_params=scan_configs[scan_name].get('params', {}),
                scan_name=scan_name
            )
        else:
            print(f"Warning: Scan '{scan_name}' not found")

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
