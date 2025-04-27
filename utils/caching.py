"""
Caching utilities for Scholar Scraper.
This module provides a simple caching mechanism to avoid redundant API calls.
"""
import json
import os
import pickle
import hashlib
from typing import Any, Callable, Dict, Optional, TypeVar
from functools import wraps
from pathlib import Path
from datetime import datetime, timedelta

from config.settings import config

# Define cache directory
CACHE_DIR = Path(__file__).parent.parent / ".cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Type variable for generic function
T = TypeVar('T')


def generate_cache_key(function_name: str, args: tuple, kwargs: Dict[str, Any]) -> str:
    """
    Generate a unique cache key based on function name and arguments.
    
    Args:
        function_name: Name of the function being cached
        args: Positional arguments to the function
        kwargs: Keyword arguments to the function
        
    Returns:
        str: A unique hash representing the function call
    """
    # Convert args and kwargs to a string representation
    args_str = str(args) + str(sorted(kwargs.items()))
    # Generate a hash
    key = hashlib.md5(f"{function_name}:{args_str}".encode()).hexdigest()
    return key


def cache_result(expiry_hours: float = 24.0) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to cache function results to avoid redundant API calls.
    
    Args:
        expiry_hours: Number of hours before cache expires
        
    Returns:
        Decorator function that caches results
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Check if cache is disabled via kwargs
            skip_cache = kwargs.pop('skip_cache', False)
            if skip_cache:
                return func(*args, **kwargs)
            
            # Generate cache key
            cache_key = generate_cache_key(func.__name__, args, kwargs)
            cache_file = CACHE_DIR / f"{cache_key}.pkl"
            
            # If cache exists and is not expired, return cached result
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                    
                    # Check if cache has expired
                    if datetime.now() - cached_data['timestamp'] < timedelta(hours=expiry_hours):
                        return cached_data['result']
                except (pickle.PickleError, KeyError, EOFError):
                    # If cache is corrupted, ignore and recompute
                    pass
            
            # Call the function and cache the result
            result = func(*args, **kwargs)
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump({
                        'result': result,
                        'timestamp': datetime.now()
                    }, f)
            except (pickle.PickleError, TypeError):
                # If result cannot be pickled, just return without caching
                pass
            
            return result
        return wrapper
    return decorator


def clear_cache(older_than_hours: Optional[float] = None) -> int:
    """
    Clear the cache files.
    
    Args:
        older_than_hours: If provided, only clear cache files older than this many hours
        
    Returns:
        int: Number of cache files deleted
    """
    count = 0
    for cache_file in CACHE_DIR.glob("*.pkl"):
        if older_than_hours is not None:
            # Check file modification time
            mod_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mod_time < timedelta(hours=older_than_hours):
                continue
        
        cache_file.unlink()
        count += 1
    
    return count
