# Tiingo-Screener-Python

Stock screener application that fetches CSV ticker data from the Tiingo API, calculates technical indicators, runs scans, and provides advanced visualization capabilities.

## ✨ Features
- **Automated Data Pipeline**: Tickers → Indicators → Scans → Visualization
- **Multi-Timeframe Analysis**: Support for daily, weekly, hourly, and minute timeframes
- **Advanced Visualization**: TradingView-style charts using lightweight-charts library
- **Flexible Data Management**: Version-controlled buffer system with save/load capabilities
- **Comprehensive Scanning**: Multiple indicator-based scan criteria

## 📁 Data System Framework

### Buffer Architecture

./data/
├── tickers/ # Raw API data buffer
├── indicators/ # Calculated indicators buffer
├── scans/ # Scan results buffer
├── versions/ # Saved versions subfolders
└── screenshots/ # Visualization screenshots

### Workflow
1. **API Fetch**: Tiingo API → `./data/tickers/`
2. **Indicator Calculation**: Tickers buffer → `./data/indicators/`
3. **Scan Execution**: Indicators buffer → `./data/scans/`
4. **Versioning**: Collections can be saved/loaded from version subfolders

### Data Format
- All data stored as CSV files
- Standardized naming conventions

## 📊 Visualization Application
- **Multi-Timeframe Panels**: View multiple timeframes simultaneously
- **Custom Indicators**: Plot multiple technical indicators (customizable)
- **Interactive Navigation**: Manually toggle through tickers and timeframes
- **TradingView Style**: Clean, professional charts using lightweight-charts

## 🖥️ CLI Usage Guide

Values in `[brackets]` represent application CLI inputs.

### MAIN FUNCTIONS
| Command | Description | Example |
|---------|-------------|---------|
| `--full-run` | Complete process: fetch > indicators > scan | `--full-run` |
| `--fetch` | Download tickers from API to buffer | `--fetch` |
| `--ind` | Calculate indicators from tickers buffer | `--ind --ind-conf ind_conf_1` |
| `--scan` | Run scanner on indicators buffer | `--scan --scan-list scan_list_1` |
| `--vis` | Launch visualization | `--vis --ticker MSFT --timeframe d --ver 1` |

**Visualization Options:**
- `--ticker [SYMBOL]` - Specify ticker symbol
- `--timeframe [TF]` - Timeframe (`d`, `w`, `4h`, `h`, `5min`)
- `--ver [VERSION]` - Indicator version (`1`, `2`, `3`, `4`)
- `--scan-file [FILE]` - Scan results file (`scan_results_*.csv`)

### LIST DATA COMMANDS
| Command | Description |
|---------|-------------|
| `--list-tickers` | List ticker files in buffer |
| `--list-ind` | List indicator files in buffer |
| `--list-scans` | List scan files in buffer |
| `--list-tickers-ver` | List saved ticker versions |
| `--list-ind-ver` | List saved indicator versions |
| `--list-scans-ver` | List saved scan versions |

### DATA MANAGEMENT COMMANDS
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
| `--clear-indicators` | Clear indicators buffer |
| `--clear-scans` | Clear scans buffer |
| `--clear-screenshots` | Clear screenshots buffer |

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/tiingo-screener-python.git
   cd tiingo-screener-python

2. pip install -r requirements.txt
