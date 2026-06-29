# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Activate venv first
source venv/bin/activate

# Show all available commands
python app.py

# Core pipeline commands
python app.py --tickers                                          # Fetch all default timeframes
python app.py --tickers --timeframe daily,weekly                 # Fetch specific timeframes
python app.py --tickers --end-date 2024-06-01                   # Fetch up to a specific date
python app.py --ind --ind-conf 2                                # Run indicators (all timeframes)
python app.py --ind --ind-conf 2 --timeframe daily              # Run indicators (specific timeframe)
python app.py --scan --scan-list 2                              # Run scanner (uses all ind_conf subdirs)
python app.py --scan --scan-list 2 --ind-conf 0                 # Run scanner against a specific ind_conf
python app.py --vis --ticker BTCUSD --ind-conf 2                # Visualize single ticker
python app.py --vis --ticker AAPL,MSFT --timeframe d,w --ind-conf 1,2  # Multi-chart, per-chart conf
python app.py --vis --scan-file scan_20240101.csv               # Visualize scan results
python app.py --vis --ticker AAPL --end-date 2024-01-01         # Visualize up to a specific date
```

Timeframe aliases: `d`/`daily`, `w`/`weekly`, `4h`/`4hour`, `h`/`1hour`, `5min`

## Architecture Overview

### Data Pipeline
```
Tiingo API → data/tickers/ → data/indicators/ind_conf_N/ → data/scans/
```
Each stage reads CSVs from the previous stage's buffer directory. All data is stored as CSVs named `{TICKER}_{TIMEFRAME}_{DDMMYY}.csv`. The `DataManager` (`src/core/data_manager.py`) handles all file I/O, versioning (save/load/delete named snapshots), and buffer clearing.

### Indicator Conf Subdirectories

Indicator CSVs are written to `data/indicators/ind_conf_{N}/` subdirectories, one per conf. Running `--ind --ind-conf 0` writes to `ind_conf_0/`, running `--ind --ind-conf 9` writes to `ind_conf_9/`. Multiple confs persist side-by-side without overwriting each other.

- `--clear-ind` clears all `ind_conf_*/` subdirs
- `--clear-ind --ind-conf 0` clears only `ind_conf_0/`
- `--save-ind NAME` / `--load-ind NAME` snapshot/restore per-conf

The flat `data/indicators/` root no longer holds CSVs directly — all CSVs live in conf subdirs.

When `--vis` is used without `--ind-conf` (scan file mode), cycling handlers automatically search all available `ind_conf_*/` subdirs. When `--vis --ind-conf 0,9` is used, each chart panel reads from its own conf's subdir independently.

### Key Design Patterns

**Indicator configs** (`src/indicators/ind_configs/ind_conf_*.py`) define which indicators run per timeframe and their parameters. Each file exports two dicts: `indicators` (timeframe → list of indicator names) and `params` (timeframe → indicator → param dict). The indicator runner (`src/indicators/indicators.py`) imports the config and calls each named indicator function from `src/indicators/indicators_list/`.

**Scan configs** (`src/scans/scan_configs/scan_conf_{timeframe}.py`) define named scans with a `criteria` dict (timeframe → criteria function name or list) and a `params` dict. There is one config file per timeframe (e.g. `scan_conf_daily.py`, `scan_conf_1hour.py`). Scan lists (`src/scans/scan_lists.py`) group scan names to run together. The scanner (`src/scans/scans.py`) loads criteria functions from `src/scans/criteria/` by name and applies them to indicator CSVs.

**Visualization** (`src/visualization/visualization.py`) supports up to 4 simultaneous charts via `lightweight-charts` (PyQt5/WebEngine). Charts are configured as a matrix of ticker × timeframe × ind_conf. The `--vis` command fetches data on-the-fly for a single ticker, or reads from the indicators buffer for scan-based browsing. Each chart panel stores its `ind_conf` in a topbar textbox widget so cycling hotkeys (6–9, -/=/[/]) read from the correct conf subdir.

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
- `6`–`9`: Cycle timeframes for charts 1–4 (reads from that chart's ind_conf subdir)
- `-`, `=`, `[`, `]`: Cycle tickers for charts 1–4 (cycles scan results if scan file loaded)
- `Spacebar`: Toggle minimize all panels
- `Ctrl+C`: Exit
- Type a ticker symbol directly to jump to it
- `_`, `+`, `{`, `}`: Screenshot charts 1–4 (saved to `docs/screenshots/`)

## Key Indicators

### QQEMOD_aVWAP (`src/indicators/indicators_list/aVWAP.py`)

Anchors VWAPs at QQEMOD zone transitions (red/bear and teal/bull). Key params in ind_conf:

- `max_anchors` — keep the last N bear anchors + last N bull anchors independently (e.g. `5` keeps 5 bear + 5 bull)
- `extend_to_end` — when `True`, every aVWAP segment runs all the way to the last bar instead of stopping at the next zone boundary
- `max_aVWAPs` — legacy alias for `max_anchors` (still accepted)

Output columns: `aVWAP_QQEMOD_bear_{idx}`, `aVWAP_QQEMOD_bear_dot_{idx}` (dotted bridge lines), `aVWAP_QQEMOD_bull_{idx}`, `aVWAP_QQEMOD_bull_dot_{idx}`.

### aVWAP Anchor Score (`src/indicators/indicators_list/aVWAP_anchor_score.py`)

Scores every candidate swing point (valley/peak) on prominence, isolation, and reversal sharpness, then anchors VWAPs only to the top `max_anchors` candidates. Output columns: `aVWAP_valley_q1`, `aVWAP_valley_q2`, ... and/or `aVWAP_peak_q1`, `aVWAP_peak_q2`, ... (q1 = highest score).

Key params: `valleys`, `peaks`, `max_anchors`, `min_score_pct` (0–1 score floor), `max_atr_distance` (proximity filter), `w_prominence`/`w_isolation`/`w_sharpness` (component weights).

## Key Scan Criteria

### QQEMOD_aVWAP (`src/scans/criteria/QQEMOD_aVWAP.py`)

Scans for price validly testing a QQEMOD-anchored aVWAP during an opposing zone.

- **Bullish** (`mode='bullish'`): current candle is in a red zone AND at least one candle's High during the current red streak reached or exceeded a prior bear aVWAP. Anchors created inside the current zone are excluded (circular reference guard).
- **Bearish** (`mode='bearish'`): current candle is in a teal zone AND at least one candle's Low during the current teal streak touched or went below a prior bull aVWAP.

`Distance_Pct` is included as an informational output column but is not used as a filter.

Scan entries `d_QQEMOD_aVWAP_bullish` and `d_QQEMOD_aVWAP_bearish` are defined in `src/scans/scan_configs/scan_conf_daily.py` and grouped in `scan_list_0` in `src/scans/scan_lists.py`.

## Bar-by-Bar Replay Mode

Watch indicators develop dynamically as price action plays out bar by bar. Requires a pre-built indicator buffer (`--ind` first). Implemented in `src/visualization/src/replay/`.

```bash
python app.py --replay --ticker AAPL --timeframe daily --ind-conf 0
```

### Replay Controls

- `←` / `→` — step backward / forward one bar
- `Shift+←` / `Shift+→` — jump 20 bars at a time
- `Home` / `End` — jump to first / last bar
- `Space` — toggle play / pause
- `f` / `Backspace` — toggle auto-fit (default on; press to free-zoom, press again to snap back)
- `↑` / `↓` or `,` / `.` — faster / slower (step interval ±0.1 s; topbar shows multiplier e.g. `1.0x`)
- `/` — reset to normal speed (1.0x)
- Type a number + `Enter` — jump to that bar index
- `Ctrl+C` — exit

### Rendering Approaches

Two strategies are used depending on the indicator:

**Progressive reveal** — for indicators with no lookahead in the CSV (SMA, Supertrend, peaks/valleys aVWAP, BoS/CHoCH aVWAP): slice `prepared_df.iloc[:n+1]` and call `line.set()`. The pre-computed value at each bar is already historically accurate.

**Historical recomputation** — for indicators where the CSV has lookahead baked in:

- **QQEMOD_aVWAP** — uses an Anchor Event Log (`src/visualization/src/replay/event_log.py`). Each anchor is committed when its zone closes (the opposite zone starts), because argmin/argmax within a zone can't be finalised until the zone ends. `max_anchors` trimming is applied rolling bar-by-bar.
- **price_maxima_minima** — runs `greedy_extrema(data[:n+1])` at every bar. O(N × max_anchors) per step, fast enough for interactive use.

Segment-based indicators (FVG, OB, BoS/CHoCH, Liquidity, divergences) are not supported — they require two-point segments that change shape per step.
