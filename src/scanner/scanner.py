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
        criteria_params: Dict of parameter dicts for criteria functions
        logic: 'AND'/'OR' for dict mode only
        api_key: Optional Tiingo API key
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
    # Create indexed criteria list
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
    """Enhanced timeframe scanner with parameter support - OCCURRENCE-BASED FIX"""

    print(f"\n=== ADVANCED SCAN: {scan_name or 'unnamed'} ===")
    print(f"Timeframe criteria: {timeframe_criteria}")
    print(f"Criteria params: {criteria_params}")
    print(f"Logic: {logic}")

    timeframe_configs = {}
    
    # Parse criteria to determine how many times each should be called
    for timeframe, criteria_spec in timeframe_criteria.items():
        if isinstance(criteria_spec, (list, tuple)):
            criteria_list = criteria_spec
        else:
            criteria_list = [criteria_spec]
        
        # Count how many parameter sets each criteria has
        criteria_calls = []
        for criteria_name in criteria_list:
            func = _load_criteria(criteria_name)
            if not func:
                print(f"  ERROR: Failed to load criteria '{criteria_name}'")
                return pd.DataFrame()
            
            # Determine how many times to call this criteria
            call_count = 1  # Default: call once
            
            if criteria_name in criteria_params:
                param_config = criteria_params[criteria_name]
                
                # Check for timeframe-specific parameters
                if timeframe in param_config:
                    timeframe_specific = param_config[timeframe]
                    # If it's a list, call once for each parameter set
                    if isinstance(timeframe_specific, list):
                        call_count = len(timeframe_specific)
                        print(f"  {timeframe}: {criteria_name} has {call_count} parameter sets")
                # Check for global parameters (without timeframe)
                elif isinstance(param_config, dict) and 'mode' in param_config:
                    # Single parameter dict
                    call_count = 1
            
            # Add the criteria for each call
            for call_idx in range(call_count):
                criteria_calls.append((criteria_name, func, call_idx))
        
        timeframe_configs[timeframe] = criteria_calls
        print(f"  {timeframe}: Will execute {len(criteria_calls)} criteria calls")

    # Group files by ticker
    ticker_files = {}
    for file in _get_data_files():
        ticker, timeframe = _parse_filename(file)
        ticker_files.setdefault(ticker, {})[timeframe] = file

    all_results = []
    
    for ticker, files in ticker_files.items():
        print(f"\nProcessing {ticker}")
        
        timeframe_signals = {}
        timeframe_results = {}
        missing_timeframes = []
        
        # Check for missing timeframes
        for timeframe in timeframe_configs.keys():
            if timeframe not in files:
                missing_timeframes.append(timeframe)
        
        if missing_timeframes:
            print(f"  Skipping: Missing {missing_timeframes}")
            continue
        
        # Process each timeframe
        for timeframe, criteria_calls in timeframe_configs.items():
            print(f"  {timeframe}:")
            df = _load_indicator_file(INDICATORS_DIR / files[timeframe])
            
            passed_all = True
            timeframe_criteria_data = {}
            
            for criteria_name, criteria_func, call_idx in criteria_calls:
                func_name = criteria_func.__name__
                print(f"    Checking {criteria_name}[{call_idx}]...")
                
                # Get parameters for THIS call
                timeframe_params = {}
                
                if criteria_name in criteria_params:
                    param_config = criteria_params[criteria_name]
                    
                    # Check for timeframe-specific parameters
                    if timeframe in param_config:
                        timeframe_specific = param_config[timeframe]
                        
                        # If it's a list, use call_idx
                        if isinstance(timeframe_specific, list):
                            if call_idx < len(timeframe_specific):
                                timeframe_params = timeframe_specific[call_idx]
                                print(f"      Using params[{criteria_name}][{timeframe}][{call_idx}]: {timeframe_params}")
                            else:
                                print(f"      ERROR: No params at index {call_idx}")
                                passed_all = False
                                break
                        else:
                            # Single parameter dict for all calls
                            timeframe_params = timeframe_specific
                            print(f"      Using params[{criteria_name}][{timeframe}]: {timeframe_params}")
                    else:
                        # No timeframe-specific params, check for general params
                        if isinstance(param_config, dict):
                            timeframe_params = param_config
                            print(f"      Using general params[{criteria_name}]: {timeframe_params}")
                
                # Execute criteria function
                try:
                    results = criteria_func(df, **timeframe_params)
                    print(f"      Results: {len(results)} row(s)")
                except TypeError as e:
                    # Try without params if function doesn't accept them
                    try:
                        results = criteria_func(df)
                        print(f"      Results (no params): {len(results)} row(s)")
                    except Exception as e2:
                        print(f"      ERROR: {e2}")
                        results = pd.DataFrame()
                        passed_all = False
                        break
                except Exception as e:
                    print(f"      ERROR: {e}")
                    results = pd.DataFrame()
                    passed_all = False
                    break
                
                # Check if criteria passed
                if results.empty:
                    print(f"      ✗ FAILED: No results")
                    passed_all = False
                    break
                else:
                    print(f"      ✓ PASSED")
                
                # Store results with call index
                if not results.empty:
                    last_row = results.iloc[-1]
                    for col in last_row.index:
                        if col not in ['date', 'Ticker', 'Timeframe', 'Close']:
                            # Add call index to differentiate multiple calls
                            if call_idx > 0:
                                col_name = f'{func_name}_{call_idx}_{col}'
                            else:
                                col_name = f'{func_name}_{col}'
                            timeframe_criteria_data[col_name] = last_row[col]
            
            timeframe_signals[timeframe] = passed_all
            
            if passed_all:
                print(f"  {timeframe}: ALL criteria passed")
                last_row = df.iloc[[-1]].copy()
                last_row['Ticker'] = ticker
                last_row['Timeframe'] = timeframe
                
                # Add criteria data
                for col, value in timeframe_criteria_data.items():
                    last_row[col] = value
                
                timeframe_results[timeframe] = last_row
            else:
                print(f"  {timeframe}: FAILED")
        
        # Apply AND/OR logic
        print(f"\n  {ticker} signals: {timeframe_signals}")
        
        if logic == 'AND' and all(timeframe_signals.values()):
            print(f"  ✓ {ticker}: AND logic satisfied")
            combined = pd.concat(timeframe_results.values())
            all_results.append(combined)
            
        elif logic == 'OR' and any(timeframe_signals.values()):
            print(f"  ✓ {ticker}: OR logic satisfied")
            combined = pd.concat([timeframe_results[tf] for tf in timeframe_signals if timeframe_signals[tf]])
            
            result_row = {
                'date': combined.iloc[0]['date'],
                'Ticker': ticker,
                'Timeframe': '|'.join([tf for tf, passed in timeframe_signals.items() if passed]),
                'Close': combined.iloc[0]['Close']
            }
            
            # Add criteria data
            for tf, passed in timeframe_signals.items():
                if passed:
                    for col in timeframe_results[tf].columns:
                        if col not in ['date', 'Ticker', 'Timeframe', 'Close']:
                            result_row[f'{tf}_{col}'] = timeframe_results[tf][col].iloc[0]
            
            all_results.append(pd.DataFrame(result_row, index=[0]))
        else:
            print(f"  ✗ {ticker}: Logic NOT satisfied")
    
    print(f"\n=== SCAN COMPLETE ===\n")
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
    filename = f"scan_{scan_date}"
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
