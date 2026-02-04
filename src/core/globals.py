from pathlib import Path
from datetime import datetime

# GLOBAL Variables
DATE_STAMP = datetime.now().strftime('%d%m%y')

# Project ROOT Directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Buffer & Storage Directories
SCANNER_DIR     = PROJECT_ROOT / "data" / "scans"
INDICATORS_DIR  = PROJECT_ROOT / "data" / "indicators"
TICKERS_DIR     = PROJECT_ROOT / "data" / "tickers"

# Indicator Configs & Scan Lists Directories
IND_CONF_DIR     = PROJECT_ROOT / "src" / "indicators" / "ind_configs"
SCAN_CONF_DIR    = PROJECT_ROOT / "src" / "scanner" / "scan_configs"
SCAN_LIST_DIR    = PROJECT_ROOT / "src" / "scanner" / "scan_lists"

# Screenshots taken from visualization application chart
SCREENSHOTS_DIR = PROJECT_ROOT / "docs" / "screenshots"

# Tickers Lists for Fetch (eg TSX, QQQ, NASDAQ)
TICKERS_LIST    = PROJECT_ROOT / 'src/tickers/ticker_lists/TSX.csv'

# Tiingo API Key
API_KEY = '9807b06bf5b97a8b26f5ff14bff18ee992dfaa13'
