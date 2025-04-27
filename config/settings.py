"""
Settings and configuration for the Scholar Scraper application.
This module centralizes all configuration parameters and provides validation.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Union
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory of the application
BASE_DIR = Path(__file__).parent.parent


class AppConfig:
    """Configuration class for Scholar Scraper application."""

    # API Keys and credentials
    GOOGLE_GEMINI_API_KEY: Optional[str] = os.getenv("GOOGLE_GEMINI_API_KEY")
    GOOGLE_TRANSLATE_API_KEY: Optional[str] = os.getenv("GOOGLE_TRANSLATE_API_KEY")

    # API Endpoints
    GEMINI_API_ENDPOINT: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    PUBMED_SEARCH_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    PUBMED_SUMMARY_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    PUBMED_FETCH_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    # Rate limiting
    PUBMED_RATE_LIMIT_DELAY: float = 0.34  # 3 requests/second
    DEFAULT_RATE_LIMIT_DELAY: float = 1.0

    # Search settings
    DEFAULT_NUM_RESULTS: int = 10
    MAX_RESULTS_PER_SOURCE: int = 30
    DEFAULT_SOURCES: List[str] = ["arxiv", "pubmed"]
    
    # Output settings
    RESULTS_DIR: Path = BASE_DIR / "results"
    
    # Model settings
    DEFAULT_SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    
    # Language settings
    DEFAULT_SOURCE_LANGUAGE: str = "German"

    @classmethod
    def validate(cls) -> Dict[str, str]:
        """
        Validate the configuration and return any errors.
        
        Returns:
            Dict[str, str]: Dictionary of error messages keyed by config parameter
        """
        errors = {}
        
        # Check for required API keys
        if not cls.GOOGLE_GEMINI_API_KEY:
            errors["GOOGLE_GEMINI_API_KEY"] = "Google Gemini API key is required. Set GOOGLE_GEMINI_API_KEY in .env file."
        
        # Create results directory if it doesn't exist
        os.makedirs(cls.RESULTS_DIR, exist_ok=True)
        
        return errors
    
    
# Create a config singleton
config = AppConfig()
