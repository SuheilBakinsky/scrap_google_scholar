"""
Error handling utilities for Scholar Scraper.
This module provides centralized error handling functionality.
"""
import logging
import sys
import traceback
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scholar_scraper.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("scholar_scraper")

# Define function return type for decorator
T = TypeVar('T')


def log_exceptions(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    """
    Decorator to log exceptions from functions and optionally continue.
    
    Args:
        func: The function to wrap with exception handling
        
    Returns:
        Wrapped function that logs exceptions
    """
    def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            logger.debug(traceback.format_exc())
            return None
    return cast(Callable[..., Optional[T]], wrapper)


class APIError(Exception):
    """Base exception for API-related errors."""
    def __init__(self, message: str, source: str, status_code: Optional[int] = None) -> None:
        self.message = message
        self.source = source
        self.status_code = status_code
        super().__init__(f"{source} API Error: {message}" + 
                        (f" (Status: {status_code})" if status_code else ""))


class ScholarScraperError(Exception):
    """Base exception for Scholar Scraper application errors."""
    pass


class ConfigError(ScholarScraperError):
    """Exception raised for errors in the configuration."""
    pass


class DataSourceError(ScholarScraperError):
    """Exception raised for errors in data sources."""
    def __init__(self, source: str, message: str) -> None:
        self.source = source
        self.message = message
        super().__init__(f"Error in {source}: {message}")


def handle_api_error(source: str, error: Exception) -> None:
    """
    Handle API errors uniformly across the application.
    
    Args:
        source: The name of the API source (e.g., "Gemini", "ArXiv")
        error: The exception that was raised
    """
    if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
        status_code = error.response.status_code
        logger.error(f"{source} API Error: {str(error)} (Status: {status_code})")
        
        # Handle specific HTTP status codes
        if status_code == 429:
            logger.error(f"{source} API rate limit exceeded")
        elif status_code == 401 or status_code == 403:
            logger.error(f"{source} API authentication error - check your API key")
        elif status_code >= 500:
            logger.error(f"{source} API server error - service may be unavailable")
    else:
        logger.error(f"{source} API Error: {str(error)}")
        
    # Log full traceback at debug level
    logger.debug(traceback.format_exc())
