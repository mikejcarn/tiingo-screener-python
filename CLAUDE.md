# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Activate venv first
source venv/bin/activate

# Show all available commands
python app.py

# Core pipeline commands
python app.py --fetch                                    # Fetch all default timeframes
python app.py --fetch --timeframe daily,weekly           # Fetch specific timeframes
python app.py --ind --ind-conf 2                         # Run indicators (all timeframes)
python app.py --ind --ind-conf 2 --timeframe daily       # Run indicators (specific timeframe)
python app.py --scan --scan-list 2                       # Run scanner
python app.py --vis --ticker BTCUSD --ind-conf 2         # Visualize single ticker
python app.py --vis --ticker AAPL,MSFT --timeframe d,w --ind-conf 1,2  # Multi-chart
python app.py --vis --scan-file scan_20240101.csv        # Visualize scan results
```

Timeframe aliases: `d`/`daily`, `w`/`weekly`, `4h`/`4hour`, `h`/`1hour`, `5min`

## Architecture Overview

### Data Pipeline
```
Tiingo API → data/tickers/ → data/indicators/ → data/scans/
```
Each stage reads CSVs from the previous stage's buffer directory. All data is stored as CSVs named `{TICKER}_{TIMEFRAME}_{DDMMYY}.csv`. The `DataManager` (`src/core/data_manager.py`) handles all file I/O, versioning (save/load/delete named snapshots), and buffer clearing.

### Key Design Patterns

**Indicator configs** (`src/indicators/ind_configs/ind_conf_*.py`) define which indicators run per timeframe and their parameters. Each file exports two dicts: `indicators` (timeframe → list of indicator names) and `params` (timeframe → indicator → param dict). The indicator runner (`src/indicators/indicators.py`) imports the config and calls each named indicator function from `src/indicators/indicators_list/`.

**Scan configs** (`src/scans/scan_configs/scan_conf_{timeframe}.py`) define named scans with a `criteria` dict (timeframe → criteria function name or list) and a `params` dict. There is one config file per timeframe (e.g. `scan_conf_daily.py`, `scan_conf_1hour.py`). Scan lists (`src/scans/scan_lists.py`) group scan names to run together. The scanner (`src/scans/scans.py`) loads criteria functions from `src/scans/criteria/` by name and applies them to indicator CSVs.

**Visualization** (`src/visualization/visualization.py`) supports up to 4 simultaneous charts via `lightweight-charts` (PyQt5/WebEngine). Charts are configured as a matrix of ticker × timeframe × ind_conf. The `--vis` command fetches data on-the-fly for a single ticker, or reads from the indicators buffer for scan-based browsing.

### Adding a New Indicator

1. Create `src/indicators/indicators_list/my_indicator.py` with a `calculate_my_indicator(df, **params)` function that returns the df with new columns appended.
2. Add `'my_indicator'` to the appropriate timeframe list in an `ind_conf_*.py` file.
3. Add parameter dict under `params` in that config file if needed.
4. The indicators runner discovers functions by name — the function name must match `calculate_{indicator_name}`.

### Adding a New Scan Criteria

1. Create `src/scans/criteria/my_criteria.py` with a function that accepts a DataFrame and returns a boolean or filtered DataFrame.
2. Reference it by filename stem in the appropriate `scan_conf_{timeframe}.py` criteria dict.

### API Key

The Tiingo API key is hardcoded in `src/core/globals.py` (`API_KEY`). This file also defines all directory paths relative to `PROJECT_ROOT`. The active ticker list for batch fetching is set via `TICKERS_LIST` (defaults to `src/tickers/ticker_lists/TSX.csv`).

### Visualization Controls

- `1`–`4`: Maximize chart 1–4
- `6`–`9`: Cycle timeframes for charts 1–4
- `-`, `=`, `[`, `]`: Cycle tickers for charts 1–4 (cycles scan results if scan file loaded)
- `Spacebar`: Toggle minimize all panels
- `Ctrl+C`: Exit
- Type a ticker symbol directly to jump to it
- `_`, `+`, `{`, `}`: Screenshot charts 1–4 (saved to `docs/screenshots/`)
