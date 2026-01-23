from typing import List, Optional
from .src.fetch_ticker import fetch_ticker
from .src.fetch_tickers import fetch_tickers

# Export functions for easy importing
__all__ = [
    'fetch_ticker',    # Single ticker fetching
    'fetch_tickers',   # Batch ticker fetching
]
