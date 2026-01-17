# import os
# import pandas as pd
# from pathlib import Path
# from datetime import datetime
# from src.indicators.get_indicators import get_indicators
# from config.settings import TICKERS_DIR, INDICATORS_DIR
#
# def run_indicators(indicator_list, params=None, timeframe_filter=None):
#     """
#     Process and save each ticker immediately after calculation.
#    
#     Args:
#         indicator_list: List of indicators to calculate
#         params: Dictionary of parameters for the indicators
#         timeframe_filter: Optional timeframe to process (e.g., '1hour', 'daily')
#                          If None, processes all timeframes
#     """
#
#     tickers_data = load_tickers(TICKERS_DIR)
#    
#     # Filter by timeframe if specified
#     if timeframe_filter is not None:
#         timeframe_filter = timeframe_filter.lower()
#         tickers_data = {k: v for k, v in tickers_data.items() 
#                        if v["timeframe"].lower() == timeframe_filter}
#         if not tickers_data:
#             print(f"\nNo files found for timeframe: {timeframe_filter}")
#             return
#
#     total_files = len(tickers_data)
#     print('\n=== INDICATORS ===\n')
#     print(f"Input directory: {TICKERS_DIR}")
#     print(f"Output directory: {INDICATORS_DIR}")
#     print(f"\nLoaded {total_files} datasets. Processing...")
#
#     processed_count = 0
#     for key, data in tickers_data.items():
#         processed_count += 1
#         ticker = data["ticker"]
#         timeframe = data["timeframe"]
#        
#         print(f"\rProcessing {processed_count}/{total_files}: {str(ticker).strip().ljust(6)}", end="")       
#
#         try:
#             df_with_indicators = get_indicators(data["df"], indicator_list, params)
#            
#             save_ticker(
#                 df=df_with_indicators,
#                 ticker=ticker,
#                 timeframe=timeframe,
#                 date_stamp=data["date_stamp"],
#                 output_dir=INDICATORS_DIR
#             )
#
#         except KeyError as e:
#             print(f"\nError processing {ticker}_{timeframe}: {str(e)}")
#             continue
#    
#     print(f"\n\nAll files processed\n")
#
# # Helper Functions ------------------------------------------------------------
#
# def load_tickers(input_dir):
#     """Load CSVs with datetime index and metadata."""
#     tickers_data = {}
#     for file in os.listdir(input_dir):
#         if file.endswith(".csv"):
#             parts = file.split("_")
#             ticker, timeframe = parts[0], parts[1]
#             date_stamp = parts[2].replace(".csv", "")
#            
#             df = pd.read_csv(
#                 os.path.join(input_dir, file),
#                 parse_dates=["date"],
#                 index_col="date"
#             )
#             df.attrs = {"timeframe": timeframe}
#            
#             tickers_data[f"{ticker}_{timeframe}"] = {
#                 "df": df,
#                 "ticker": ticker,
#                 "timeframe": timeframe,
#                 "date_stamp": date_stamp
#             }
#     return tickers_data
#
#
# def save_ticker(df, ticker, timeframe, date_stamp, output_dir):
#     """Save one processed ticker immediately."""
#     os.makedirs(output_dir, exist_ok=True)
#     filename = f"{ticker}_{timeframe}_{date_stamp}.csv"
#     filepath = os.path.join(output_dir, filename)
#    
#     df.to_csv(filepath, index=True, index_label="date")






# import os
# import pandas as pd
# from pathlib import Path
# from datetime import datetime
# import importlib.util
# import sys
# from src.indicators.get_indicators import get_indicators
# from config.settings import TICKERS_DIR, INDICATORS_DIR, IND_CONF_DIR
#
# def run_indicators(ind_conf=None, timeframe=None):
#     """
#     Process indicators using config files from IND_CONF_DIR.
#    
#     Args:
#         ind_conf: Indicator config version (e.g., '1', '2', '3', '4')
#         timeframe: Optional timeframe to process (e.g., 'daily', 'weekly')
#                    If None, processes all timeframes in the config
#     """
#     # Load the indicator config
#     config_data = load_indicator_config(ind_conf)
#     if config_data is None:
#         return
#    
#     indicators_dict = config_data['indicators']
#     params_dict = config_data['params']
#    
#     # Determine which timeframes to process
#     if timeframe:
#         # Single timeframe
#         timeframes_to_process = [timeframe.lower()]
#     else:
#         # All timeframes from the config
#         timeframes_to_process = list(indicators_dict.keys())
#    
#     print(f'\n=== INDICATORS (Config: {ind_conf}) ===\n')
#     print(f"Timeframes to process: {', '.join(timeframes_to_process)}")
#     print(f"Input directory: {TICKERS_DIR}")
#     print(f"Output directory: {INDICATORS_DIR}")
#    
#     # Load all ticker data ONCE
#     tickers_data = load_tickers(TICKERS_DIR)
#    
#     if not tickers_data:
#         print("No ticker data found!")
#         return
#    
#     # Process each timeframe
#     for timeframe_name in timeframes_to_process:
#         # Check if this timeframe exists in the config
#         if timeframe_name not in indicators_dict:
#             print(f"\nWarning: No config found for timeframe '{timeframe_name}'")
#             continue
#        
#         # Get configs for this timeframe
#         indicator_list = indicators_dict[timeframe_name]
#         timeframe_params = params_dict[timeframe_name]
#        
#         # Filter tickers for this timeframe
#         timeframe_tickers = {k: v for k, v in tickers_data.items() 
#                            if v["timeframe"].lower() == timeframe_name.lower()}
#        
#         if not timeframe_tickers:
#             print(f"\nNo files found for timeframe: {timeframe_name}")
#             continue
#        
#         total_files = len(timeframe_tickers)
#         print(f"\nProcessing {timeframe_name} ({total_files} files)...")
#        
#         processed_count = 0
#         for key, data in timeframe_tickers.items():
#             processed_count += 1
#             ticker = data["ticker"]
#            
#             print(f"\r  {processed_count}/{total_files}: {str(ticker).strip().ljust(6)}", end="")
#            
#             try:
#                 df_with_indicators = get_indicators(data["df"], indicator_list, timeframe_params)
#                
#                 save_ticker(
#                     df=df_with_indicators,
#                     ticker=ticker,
#                     timeframe=timeframe_name,
#                     date_stamp=data["date_stamp"],
#                     output_dir=INDICATORS_DIR
#                 )
#                
#             except Exception as e:
#                 print(f"\nError processing {ticker}_{timeframe_name}: {str(e)}")
#                 continue
#        
#         print(f"\n  {timeframe_name} complete!")
#    
#     print(f"\n\nAll indicators processed\n")
#
# # Helper Functions ------------------------------------------------------------
#
# def load_indicator_config(ind_conf):
#     """Load indicator configuration from IND_CONF_DIR"""
#     if ind_conf is None:
#         print("Error: Please specify an indicator config (e.g., '1', '2', '3', '4')")
#         return None
#    
#     config_file = Path(IND_CONF_DIR) / f"ind_conf_{ind_conf}.py"
#    
#     if not config_file.exists():
#         print(f"Error: Config file not found: {config_file}")
#        
#         # List available configs
#         available_configs = []
#         for f in Path(IND_CONF_DIR).glob('ind_conf_*.py'):
#             config_num = f.stem.split('_')[-1]
#             if config_num.isdigit():
#                 available_configs.append(config_num)
#        
#         if available_configs:
#             print(f"Available configs: {', '.join(sorted(available_configs))}")
#         else:
#             print(f"No config files found in {IND_CONF_DIR}")
#        
#         return None
#    
#     try:
#         # Dynamically import the config module
#         spec = importlib.util.spec_from_file_location(f"ind_conf_{ind_conf}", config_file)
#         module = importlib.util.module_from_spec(spec)
#         spec.loader.exec_module(module)
#        
#         # Check if module has required attributes
#         if not hasattr(module, 'indicators') or not hasattr(module, 'params'):
#             print(f"Error: Config file {config_file} missing 'indicators' or 'params'")
#             return None
#        
#         return {
#             'indicators': module.indicators,
#             'params': module.params
#         }
#        
#     except Exception as e:
#         print(f"Error loading config {ind_conf}: {str(e)}")
#         return None
#
# def load_tickers(input_dir):
#     """Load CSVs with datetime index and metadata."""
#     tickers_data = {}
#     for file in os.listdir(input_dir):
#         if file.endswith(".csv"):
#             parts = file.split("_")
#             if len(parts) >= 3:
#                 ticker, timeframe = parts[0], parts[1]
#                 date_stamp = parts[2].replace(".csv", "")
#                
#                 df = pd.read_csv(
#                     os.path.join(input_dir, file),
#                     parse_dates=["date"],
#                     index_col="date"
#                 )
#                 df.attrs = {"timeframe": timeframe}
#                
#                 tickers_data[f"{ticker}_{timeframe}"] = {
#                     "df": df,
#                     "ticker": ticker,
#                     "timeframe": timeframe,
#                     "date_stamp": date_stamp
#                 }
#     return tickers_data
#
# def save_ticker(df, ticker, timeframe, date_stamp, output_dir):
#     """Save one processed ticker immediately."""
#     os.makedirs(output_dir, exist_ok=True)
#     filename = f"{ticker}_{timeframe}_{date_stamp}.csv"
#     filepath = os.path.join(output_dir, filename)
#    
#     df.to_csv(filepath, index=True, index_label="date")





import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import importlib.util
import sys
from src.indicators.get_indicators import get_indicators
from config.settings import TICKERS_DIR, INDICATORS_DIR, IND_CONF_DIR

def run_indicators(ind_conf=None, timeframe=None):
    """
    Process indicators using config files from IND_CONF_DIR.
    
    Args:
        ind_conf: Indicator config version (e.g., '1', '2', '3', '4')
        timeframe: Optional timeframe(s) to process
                   String: 'daily' -> single timeframe
                   List: ['daily', 'weekly'] -> multiple timeframes
                   None: processes all timeframes in the config
    """
    # Load the indicator config
    config_data = load_indicator_config(ind_conf)
    if config_data is None:
        return
    
    indicators_dict = config_data['indicators']
    params_dict = config_data['params']
    
    # Determine which timeframes to process
    if timeframe is None:
        # All timeframes from the config
        timeframes_to_process = list(indicators_dict.keys())
    elif isinstance(timeframe, str):
        # Single timeframe string
        timeframes_to_process = [timeframe.lower()]
    elif isinstance(timeframe, list):
        # List of timeframes
        timeframes_to_process = [tf.lower() for tf in timeframe]
    else:
        print(f"Error: Invalid timeframe parameter type: {type(timeframe)}")
        return
    
    print(f'\n=== INDICATORS (Config: {ind_conf}) ===\n')
    print(f"Timeframes to process: {', '.join(timeframes_to_process)}")
    print(f"Input directory: {TICKERS_DIR}")
    print(f"Output directory: {INDICATORS_DIR}")
    
    # Load all ticker data ONCE
    tickers_data = load_tickers(TICKERS_DIR)
    
    if not tickers_data:
        print("No ticker data found!")
        return
    
    # Process each timeframe
    for timeframe_name in timeframes_to_process:
        # Check if this timeframe exists in the config
        if timeframe_name not in indicators_dict:
            print(f"\nWarning: No config found for timeframe '{timeframe_name}'")
            continue
        
        # Get configs for this timeframe
        indicator_list = indicators_dict[timeframe_name]
        timeframe_params = params_dict[timeframe_name]
        
        # Filter tickers for this timeframe
        timeframe_tickers = {k: v for k, v in tickers_data.items() 
                           if v["timeframe"].lower() == timeframe_name.lower()}
        
        if not timeframe_tickers:
            print(f"\nNo files found for timeframe: {timeframe_name}")
            continue
        
        total_files = len(timeframe_tickers)
        print(f"\nProcessing {timeframe_name} ({total_files} files)...")
        
        processed_count = 0
        for key, data in timeframe_tickers.items():
            processed_count += 1
            ticker = data["ticker"]
            
            print(f"\r  {processed_count}/{total_files}: {str(ticker).strip().ljust(6)}", end="")
            
            try:
                df_with_indicators = get_indicators(data["df"], indicator_list, timeframe_params)
                
                save_ticker(
                    df=df_with_indicators,
                    ticker=ticker,
                    timeframe=timeframe_name,
                    date_stamp=data["date_stamp"],
                    output_dir=INDICATORS_DIR
                )
                
            except Exception as e:
                print(f"\nError processing {ticker}_{timeframe_name}: {str(e)}")
                continue
        
        print(f"\n  {timeframe_name} complete!")
    
    print(f"\n\nAll indicators processed\n")

# Helper Functions ------------------------------------------------------------

def load_indicator_config(ind_conf):
    """Load indicator configuration from IND_CONF_DIR"""
    if ind_conf is None:
        print("Error: Please specify an indicator config (e.g., '1', '2', '3', '4')")
        return None
    
    config_file = Path(IND_CONF_DIR) / f"ind_conf_{ind_conf}.py"
    
    if not config_file.exists():
        print(f"Error: Config file not found: {config_file}")
        
        # List available configs
        available_configs = []
        for f in Path(IND_CONF_DIR).glob('ind_conf_*.py'):
            config_num = f.stem.split('_')[-1]
            if config_num.isdigit():
                available_configs.append(config_num)
        
        if available_configs:
            print(f"Available configs: {', '.join(sorted(available_configs))}")
        else:
            print(f"No config files found in {IND_CONF_DIR}")
        
        return None
    
    try:
        # Dynamically import the config module
        spec = importlib.util.spec_from_file_location(f"ind_conf_{ind_conf}", config_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check if module has required attributes
        if not hasattr(module, 'indicators') or not hasattr(module, 'params'):
            print(f"Error: Config file {config_file} missing 'indicators' or 'params'")
            return None
        
        return {
            'indicators': module.indicators,
            'params': module.params
        }
        
    except Exception as e:
        print(f"Error loading config {ind_conf}: {str(e)}")
        return None

def load_tickers(input_dir):
    """Load CSVs with datetime index and metadata."""
    tickers_data = {}
    for file in os.listdir(input_dir):
        if file.endswith(".csv"):
            parts = file.split("_")
            if len(parts) >= 3:
                ticker, timeframe = parts[0], parts[1]
                date_stamp = parts[2].replace(".csv", "")
                
                df = pd.read_csv(
                    os.path.join(input_dir, file),
                    parse_dates=["date"],
                    index_col="date"
                )
                df.attrs = {"timeframe": timeframe}
                
                tickers_data[f"{ticker}_{timeframe}"] = {
                    "df": df,
                    "ticker": ticker,
                    "timeframe": timeframe,
                    "date_stamp": date_stamp
                }
    return tickers_data

def save_ticker(df, ticker, timeframe, date_stamp, output_dir):
    """Save one processed ticker immediately."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{ticker}_{timeframe}_{date_stamp}.csv"
    filepath = os.path.join(output_dir, filename)
    
    df.to_csv(filepath, index=True, index_label="date")
