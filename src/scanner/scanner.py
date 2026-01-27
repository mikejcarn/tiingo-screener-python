import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
import importlib
import requests
from src.core.globals import SCANNER_DIR, INDICATORS_DIR, DATE_STAMP

def run_scanner(criteria='banker_RSI', criteria_params=None, logic='AND', api_key=None, scan_name=None):
    """Ultimate flexible scanner with support for criteria parameters.

    Args:
        criteria: String, List, or Dict of criteria
        logic: 'AND'/'OR' for dict mode only
        api_key: Optional Tiingo API key
        criteria_params: Dict of parameter dicts for criteria functions
        scan_name: Optional custom name suffix for output file
    """
    print('\n=== SCANNER ===\n')
    print(f"Scan: {scan_name}\n")
    print(f"Input directory: {INDICATORS_DIR}")
    print(f"Output directory: {SCANNER_DIR}\n")

    print(criteria)
    print(criteria_params)

    if criteria_params is None:
        criteria_params = {}

    if isinstance(criteria, dict):
        return _advanced_scan(criteria, logic, api_key, criteria_params, scan_name)
    elif isinstance(criteria, list):
        return _multi_criteria_scan(criteria, api_key, criteria_params, scan_name)
    else:
        return _simple_scan(criteria, api_key, criteria_params, scan_name)

def _simple_scan(criteria, api_key=None, criteria_params=None, scan_name=None):
    """Single criteria applied to all files with optional parameters"""
    criteria_func = _load_criteria(criteria)
    if not criteria_func:
        return pd.DataFrame()

    # For simple scan, just get the first parameter set if it's a list
    params = {}
    if criteria in criteria_params:
        param_config = criteria_params[criteria]
        if isinstance(param_config, list):
            params = param_config[0] if param_config else {}
        else:
            params = param_config

    all_results = []
    for file in _get_data_files():
        ticker, timeframe = _parse_filename(file)
        df = _load_indicator_file(INDICATORS_DIR / file)
        
        try:
            results = criteria_func(df, **params)
        except TypeError:
            results = criteria_func(df)
      
        if not results.empty:
            results['Ticker'] = ticker
            results['Timeframe'] = timeframe
            all_results.append(results)
  
    return _process_results(all_results, f"'{criteria}' scan", api_key, scan_name)

def _multi_criteria_scan(criteria_list, api_key=None, criteria_params=None, scan_name=None):
    """Multiple criteria (ALL must pass) for all files with parameters"""
    # Create indexed criteria list to handle duplicates
    indexed_criteria = []
    for idx, criteria_name in enumerate(criteria_list):
        func = _load_criteria(criteria_name)
        if func:
            indexed_criteria.append((idx, criteria_name, func))
        else:
            return pd.DataFrame()

    all_results = []
    for file in _get_data_files():
        ticker, timeframe = _parse_filename(file)
        df = _load_indicator_file(INDICATORS_DIR / file)
        
        passed = True
        criteria_data = {}
        
        for idx, criteria_name, criteria_func in indexed_criteria:
            func_name = criteria_func.__name__
            
            # Get parameters for this specific criteria instance
            params = {}
            if criteria_name in criteria_params:
                param_config = criteria_params[criteria_name]
                
                # Check if params is a list (for indexed parameters)
                if isinstance(param_config, list):
                    if idx < len(param_config):
                        params = param_config[idx]
                else:
                    params = param_config
            
            try:
                result = criteria_func(df, **params)
            except TypeError:
                result = criteria_func(df)
                
            if result.empty:
                passed = False
                break
                
            # Store results with index to differentiate duplicates
            last_result = result.iloc[-1]
            for col in last_result.index:
                if col not in ['date', 'Ticker', 'Timeframe', 'Close']:
                    col_name = f'{func_name}_{idx}_{col}' if idx > 0 else f'{func_name}_{col}'
                    criteria_data[col_name] = last_result[col]
        
        if passed:
            result_row = {
                'date': df.index[-1],
                'Ticker': ticker,
                'Timeframe': timeframe,
                'Close': df.iloc[-1]['Close']
            }
            result_row.update(criteria_data)
            all_results.append(pd.DataFrame(result_row, index=[0]))
    
    return _process_results(all_results, f"multi-criteria {criteria_list} scan", api_key, scan_name)

def _advanced_scan(timeframe_criteria, logic='AND', api_key=None, criteria_params=None, scan_name=None):
    """Enhanced timeframe scanner with parameter support"""

    print(timeframe_criteria)
    print(criteria_params)

    timeframe_configs = {}
    
    # Track criteria by (index, name, function) to handle duplicates
    for timeframe, criteria_spec in timeframe_criteria.items():
        if isinstance(criteria_spec, (list, tuple)):
            criteria_list = criteria_spec
        else:
            criteria_list = [criteria_spec]
        
        # Create indexed criteria: (index, criteria_name, function)
        indexed_criteria = []
        for idx, criteria_name in enumerate(criteria_list):
            func = _load_criteria(criteria_name)
            if func:
                indexed_criteria.append((idx, criteria_name, func))
            else:
                return pd.DataFrame()
        
        timeframe_configs[timeframe] = indexed_criteria

    ticker_files = {}
    for file in _get_data_files():
        ticker, timeframe = _parse_filename(file)
        ticker_files.setdefault(ticker, {})[timeframe] = file

    all_results = []
    for ticker, files in ticker_files.items():
        timeframe_signals = {}
        timeframe_results = {}
        missing_timeframes = []

        for timeframe in timeframe_configs.keys():
            if timeframe not in files:
                missing_timeframes.append(timeframe)

        if missing_timeframes:
            print(f"Skipping {ticker}: Missing timeframes {missing_timeframes}")
            continue

        for timeframe, indexed_criteria in timeframe_configs.items():
            df = _load_indicator_file(INDICATORS_DIR / files[timeframe])
            
            passed_all = True
            timeframe_criteria_data = {}
            
            for idx, criteria_name, criteria_func in indexed_criteria:
                func_name = criteria_func.__name__
                
                # Get parameters for this specific criteria instance
                # Priority: params[criteria_name][timeframe][idx] > params[criteria_name][timeframe] > params[criteria_name]
                timeframe_params = {}
                
                if criteria_name in criteria_params:
                    param_config = criteria_params[criteria_name]
                    
                    if timeframe in param_config:
                        # Check if timeframe params is a list (for indexed parameters)
                        if isinstance(param_config[timeframe], list):
                            if idx < len(param_config[timeframe]):
                                timeframe_params = param_config[timeframe][idx]
                        else:
                            timeframe_params = param_config[timeframe]
                    elif isinstance(param_config, dict):
                        timeframe_params = param_config
                
                try:
                    results = criteria_func(df, **timeframe_params)
                except TypeError as e:
                    # Try without params if function doesn't accept them
                    try:
                        results = criteria_func(df)
                    except Exception:
                        print(f"Error in {func_name}: {e}")
                        results = pd.DataFrame()
                
                if results.empty:
                    passed_all = False
                    break
                
                # Store results with index to differentiate duplicates
                last_row = results.iloc[-1] if not results.empty else pd.Series()
                for col in last_row.index:
                    if col not in ['date', 'Ticker', 'Timeframe', 'Close']:
                        # Use index to differentiate duplicate criteria
                        col_name = f'{func_name}_{idx}_{col}' if idx > 0 else f'{func_name}_{col}'
                        timeframe_criteria_data[col_name] = last_row[col]
            
            timeframe_signals[timeframe] = passed_all
            if passed_all:
                last_row = df.iloc[[-1]].copy()
                last_row['Ticker'] = ticker
                last_row['Timeframe'] = timeframe
                
                # Add criteria-specific data
                for col, value in timeframe_criteria_data.items():
                    last_row[col] = value
                
                timeframe_results[timeframe] = last_row

        if logic == 'AND' and all(timeframe_signals.values()):
            combined = pd.concat(timeframe_results.values())
            all_results.append(combined)
                
        elif logic == 'OR' and any(timeframe_signals.values()):
            combined = pd.concat([timeframe_results[tf] for tf in timeframe_signals if timeframe_signals[tf]])
            
            result_row = {
                'date': combined.iloc[0]['date'],
                'Ticker': ticker,
                'Timeframe': '|'.join([tf for tf, passed in timeframe_signals.items() if passed]),
                'Close': combined.iloc[0]['Close']
            }
            
            # Add all criteria data from passed timeframes
            for tf, passed in timeframe_signals.items():
                if passed:
                    for col in timeframe_results[tf].columns:
                        if col not in ['date', 'Ticker', 'Timeframe', 'Close']:
                            result_row[f'{tf}_{col}'] = timeframe_results[tf][col].iloc[0]
            
            all_results.append(pd.DataFrame(result_row, index=[0]))

    return _process_results(all_results, "advanced scan", api_key, scan_name)

def _load_criteria(criteria_name):
    """Helper to load criteria function from src.scanner.criteria"""
    try:
        criteria_module = importlib.import_module(f"src.scanner.criteria.{criteria_name}")
        return getattr(criteria_module, criteria_name)
    except Exception as e:
        print(f"Error loading criteria '{criteria_name}': {str(e)}")
        return None

def _get_data_files():
    """Get all data files in input directory"""
    return [f for f in os.listdir(INDICATORS_DIR) if f.endswith(".csv")]

def _process_results(results, scan_type, api_key=None, scan_name=None):
    """Process and format results without fragmentation"""
    if not results or len(results) == 0:
        print(f"\nResults: {scan_type} found no setups\n")
        return pd.DataFrame()
    
    try:
        final_results = pd.concat(results)
    except ValueError:
        print(f"\nResults: {scan_type} found no setups\n")
        return pd.DataFrame()
    
    if isinstance(final_results.index, pd.DatetimeIndex):
        final_results = final_results.reset_index()
        if 'index' in final_results.columns:
            final_results = final_results.rename(columns={'index': 'date'})
    
    columns_to_keep = {
        'date': final_results['date'],
        'Ticker': final_results['Ticker'],
        'Timeframe': final_results['Timeframe'],
        'Close': final_results['Close']
    }
    
    extra_cols = {
        col: final_results[col] 
        for col in final_results.columns 
        if col not in ['date', 'Ticker', 'Timeframe', 'Close']
    }
    
    minimal_results = pd.DataFrame({**columns_to_keep, **extra_cols})
    
    if api_key:
        minimal_results = _attach_fundamentals_to_scanner(minimal_results, api_key)
    _save_scan_results(minimal_results, SCANNER_DIR, DATE_STAMP, scan_name)
    print(f"\nResults: {scan_type} found {len(minimal_results)} setups\n")
    return minimal_results

def _save_scan_results(df, output_dir, scan_date, scan_name=None):
    """Save scan results to CSV with custom naming"""
    filename = f"scan_results_{scan_date}"
    if scan_name:
        filename += f"_{scan_name}"
    filename += ".csv"
    filepath = output_dir / filename
    df.to_csv(filepath, index=False)
    print(f"\nResults saved to: {filepath}")

def _parse_filename(filename):
    """Extract ticker and timeframe from filename"""
    parts = filename.split("_")
    return parts[0], parts[1]

def _load_indicator_file(filepath):
    """Load indicator file with proper date handling"""
    df = pd.read_csv(filepath, parse_dates=['date'])
    return df.set_index('date')

def _attach_fundamentals_to_scanner(scanner_df, api_key):
    """Optimized fundamentals attachment"""
    if 'Ticker' not in scanner_df.columns:
        return scanner_df

    format_config = {
        'marketCap': {'format': '${:,.2f}B', 'divisor': 1e9},
        'enterpriseVal': {'format': '${:,.2f}B', 'divisor': 1e9},
        'peRatio': {'format': '{:.2f}', 'divisor': 1},
        'pbRatio': {'format': '{:.2f}', 'divisor': 1},
        'trailingPEG1Y': {'format': '{:.2f}', 'divisor': 1}
    }

    fundamentals = {}
    for ticker in scanner_df['Ticker'].unique():
        try:
            response = requests.get(
                f"https://api.tiingo.com/tiingo/fundamentals/{ticker}/daily",
                headers={'Content-Type': 'application/json'},
                params={'token': api_key},
            )
            response.raise_for_status()
            fund_data = response.json()
            
            if fund_data:
                latest = pd.DataFrame(fund_data).iloc[-1]
                fundamentals[ticker] = {
                    metric: latest.get(metric) 
                    for metric in format_config.keys()
                }
        except Exception as e:
            print(f"Error fetching {ticker}: {str(e)}")
            continue

    formatted_data = {}
    for metric, config in format_config.items():
        values = scanner_df['Ticker'].map(lambda x: fundamentals.get(x, {}).get(metric))
        formatted_data[metric] = values.apply(
            lambda x: config['format'].format(x/config['divisor']) if pd.notnull(x) else None
        )
    
    return scanner_df.assign(**formatted_data)
