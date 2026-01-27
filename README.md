# Tiingo-Screener-Python

Stock screener application that fetches ticker data from the Tiingo API, calculates technical indicators, runs scans, and provides advanced visualization capabilities.

## ✨ Application Features
- **Automated Data Pipeline**: Tickers → Indicators → Scans → Visualization
- **Multi-Timeframe Analysis**: Support for daily, weekly, hourly, and minute timeframes
- **Advanced Visualization**: TradingView-style charts using lightweight-charts library
- **Flexible Data Management**: Version-controlled buffer system with save/load/delete capabilities
- **Comprehensive Scanning**: Multiple indicator-based scan criteria
- **Dynamic CLI**: Flexible timeframe specification across all commands

## 📁 Data System Framework

### Buffer & Storage Architecture

```bash
./data/
├── tickers/              # Raw API data buffer
│   └── tickers_*_*/
├── indicators/           # Calculated indicators buffer
│   └── ind_conf_*/
├── scans/                # Scan results buffer
│   └── scan_list_*/
└── screenshots/          # Visualization screenshots
```

### Workflow
1. **API Fetch**: Tiingo API → `./data/tickers/`
2. **Indicator Calculation**: Tickers buffer → `./data/indicators/`
3. **Scan Execution**: Indicators buffer → `./data/scans/`
4. **Storage**: Version subfolders can be saved/loaded/deleted in buffers 

### Data Format
- Stock data fetched as JSON from Tiingo API (www.tiingo.com)
- JSON data converted to pandas Dataframes for manipulation
- Data is stored locally as CSV files in buffer and storage folders
- Data Formats: Tickers/Indicators: `[TICKER]_[TF]_[DATE]`, Scans: `scan_results_[DATE]_[TYPE]`

## 📊 Visualization Application

### Visualization Features
- **Multi-Charts**: Load up to 4 charts simultaneously in an app window
- **Custom Indicators**: Plot customized technical indicators
- **Interactive Navigation**: Toggle through tickers, timeframes, and scan results
- **TradingView Style**: Clean, professional charts using lightweight-charts

![multichart](docs/images/multichart.png)
![maximized](docs/images/maximized.png)

### Visualization Controls

**Global Controls:**
- `Mouse Drag` – Pan charts
- `Scroll Wheel` – Zoom in/out
- `Spacebar` – Toggle minimize all panels
- `Ctrl+C` – Exit application
- `Text Input` – Manual ticker entry

**Per-Chart Controls:**

| Action | Chart 1 | Chart 2 | Chart 3 | Chart 4 |
|--------|---------|---------|---------|---------|
| Maximize | `1` | `2` | `3` | `4` |
| Cycle Timeframes | `6` | `7` | `8` | `9` |
| Cycle Tickers | `-` | `=` | `[` | `]` |
| Screenshot | `_` | `+` | `{` | `}` |
- If a scan_results file is loaded, `-` will cycle results in scan file
- Otherwise, cycle buttons will cycle indicator buffer files

## 🖥️ CLI Usage Guide

- Values in `[brackets]` represent application CLI inputs.
- Shared `--timeframe` parameter [TF]: Use the same parameter for fetch, indicators, and visualization
- Dynamic timeframes: Specify exactly which timeframes to process for each command

### MAIN FUNCTIONS
| Command | Description | Example |
|---------|-------------|---------|
| `--full-run` | Complete process: fetch > indicators > scan | `--full-run` |
| `--fetch` | Download tickers from API to buffer | `--fetch daily` |
| `--ind` | Calculate indicators from tickers buffer | `--ind --ind-conf 1` |
| `--scan` | Run scanner on indicators buffer | `--scan --scan-list 1` |
| `--vis` | Launch visualization | `--vis --ticker MSFT --timeframe d --ind-conf 1` `--vis --ticker MSFT --timeframe w,d,4h,h --ind-conf 1,2,3,4` `--vis --ticker MSFT,BTCUSD,AAPL,SOFI --timeframe w,d,4h,h --ind-conf 1` |

**`--fetch` Options:**
- `--timeframe [TF]` - Timeframes(s) to fetch (comma-separated e.g., "daily,weekly")
- Default: `weekly,daily,4hour,1hour`

**`--ind` Options:**
- `--ind-conf [VERSION]` - Indicator config (`1`, `2`, `3`, `4`)
- `--timeframe [TF]` - Timeframe(s) to process (comma-separated, e.g., "daily,weekly,4hour")
- Default: All timeframes in tickers buffer

**`--scan` Options:**
- `--scan-list [VERSION]` - Specify scan list (`1`, `2`, `3`, `4`)

**`--vis` Options:**
- `--ticker [SYMBOL]` - Ticker symbol(s) (`BTCUSD`, `BTCUSD,SOFI,AAPL,MSFT`)
- `--timeframe [TF]` - Timeframe(s) (`5min`, `w,d,4h,h`)
- `--ind-conf [VERSION]` - Indicator config(s) (`1`, `1,2,3,4`)
- `--scan-file [FILE]` - Scan results file (`scan_results_*.csv`)

## EXAMPLES

### Fetch Data:
```
# Fetch default timeframes (weekly, daily, 4hour, 1hour)
python app.py --fetch

# Fetch specific timeframes
python app.py --fetch --timeframe daily,weekly

# Fetch single timeframe
python app.py --fetch --timeframe daily
```

### Calculate Indicators:
```
# Process all timeframes with config 2
python app.py --ind --ind-conf 2

# Process specific timeframes with config 3
python app.py --ind --ind-conf 3 --timeframe daily,weekly

# Process single timeframe with config 1
python app.py --ind --ind-conf 1 --timeframe daily
```

### Visualization:
```
# Single chart with default timeframe
python app.py --vis --ticker MSFT --ind-conf 2

# Multiple tickers with same timeframe
python app.py --vis --ticker MSFT,AAPL,GOOGL --timeframe d --ind-conf 2,2,2

# Multiple timeframes with multiple configs
python app.py --vis --ticker MSFT --timeframe d,w,4h --ind-conf 2,3,4

# Scan file visualization
python app.py --vis --scan-file scan_results_20240101.csv
```

![--vis --ticker BTCUSD --ind-conf 0](docs/images/single_1.png)
*--vis --ticker BTCUSD --ind-conf 0*
![--vis --ticker BTCUSD --ind-conf 2](docs/images/single_2.png)
*--vis --ticker BTCUSD --ind-conf 2*
![--vis --ticker AAPL,BTCUSD,SOFI --timeframe w,d,4h --ind-conf 2,1,3](docs/images/3charts.png)
*--vis --ticker AAPL,BTCUSD,SOFI --timeframe w,d,4h --ind-conf 2,1,3*
![--vis --ticker AAPL --timeframe w,d,4h,h --ind-conf 1](docs/images/4charts.png)
*--vis --ticker AAPL --timeframe w,d,4h,h --ind-conf 1*

### LIST BUFFER & STORAGE DATA
| Command | Description |
|---------|-------------|
| `--list-tickers` | List ticker files in buffer |
| `--list-ind` | List indicator files in buffer |
| `--list-scans` | List scan files in buffer |
| `--list-tickers-ver` | List saved ticker versions |
| `--list-ind-ver` | List saved indicator versions |
| `--list-scans-ver` | List saved scan versions |

### STORAGE DATA MANAGEMENT
| Category | Save | Load | Delete Single | Delete All |
|----------|------|------|---------------|------------|
| **Tickers** | `--save-tickers [NAME]` | `--load-tickers [NAME]` | `--delete-tickers [NAME]` | `--delete-tickers-all` |
| **Indicators** | `--save-ind [NAME]` | `--load-ind [NAME]` | `--delete-ind [NAME]` | `--delete-ind-all` |
| **Scans** | `--save-scan [NAME]` | `--load-scan [NAME]` | `--delete-scan [NAME]` | `--delete-scan-all` |

### BUFFER MANAGEMENT
| Command | Description |
|---------|-------------|
| `--clear-all` | Reset all buffers (preserves versions) |
| `--clear-tickers` | Clear tickers buffer |
| `--clear-ind` | Clear indicators buffer |
| `--clear-scans` | Clear scans buffer |
| `--clear-screenshots` | Clear screenshots buffer |

## Advanced Indicator Configurations

### 🔧 Indicator Configuration Files

Located in `./src/indicators/ind_configs/`:
- ind_conf_0.py - Testing
- ind_conf_1.py - aVWAPavg
- ind_conf_2.py - aVWAP
- ind_conf_3.py
- ind_conf_4.py - Support/Resistance

Each config file contains:
- `indicators` - Dictionary of timeframes with indicator lists
- `params` - Dictionary of parameters for each indicator/timeframe

Customizing Configurations
- Edit the appropriate `ind_conf_X.py` file
- Add/remove indicators from the lists
- Adjust parameters for your analysis
- Run with: `python app.py --ind --ind-conf X`

## 🚀 Installation

**Clone the repository and install requirements:**
```bash
git clone https://github.com/yourusername/tiingo-screener-python.git
cd tiingo-screener-python
pip install -r requirements.txt
```

**Set up your Tiingo API Key in `.src/core/globals.py`:**
```bash
API_KEY = 'your_tiingo_api_key_here'
```

**Run the application:**
```bash
python app.py --help  # View all available commands
```
