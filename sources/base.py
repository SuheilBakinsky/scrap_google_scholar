"""
Base classes for data sources in Scholar Scraper.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from utils.error_handling import log_exceptions


class Paper:
    """Class representing an academic paper."""
    
    def __init__(
        self,
        title: str,
        abstract: str,
        year: str,
        url: str,
        authors: str,
        source: str,
        fulltext: Optional[str] = None,
        doi: Optional[str] = None,
        paper_id: Optional[str] = None
    ) -> None:
        """
        Initialize a paper object.
        
        Args:
            title: Title of the paper
            abstract: Abstract text of the paper
            year: Publication year
            url: URL to the paper
            authors: Comma-separated list of authors
            source: Source of the paper (e.g., "arxiv" or "pubmed")
            fulltext: Optional full text of the paper
            doi: Optional DOI identifier
            paper_id: Optional source-specific identifier
        """
        self.title = title
        self.abstract = abstract
        self.year = year
        self.url = url
        self.authors = authors
        self.source = source
        self.fulltext = fulltext
        self.doi = doi
        self.paper_id = paper_id
    
    def to_dict(self) -> Dict[str, Optional[str]]:
        """
        Convert the paper object to a dictionary.
        
        Returns:
            Dict representation of the paper
        """
        return {
            'title': self.title,
            'abstract': self.abstract,
            'year': self.year,
            'url': self.url,
            'authors': self.authors,
            'source': self.source,
            'fulltext': self.fulltext,
            'doi': self.doi,
            'paper_id': self.paper_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Optional[str]]) -> 'Paper':
        """
        Create a Paper object from a dictionary.
        
        Args:
            data: Dictionary containing paper attributes
            
        Returns:
            Paper object created from the dictionary
        """
        return cls(
            title=data.get('title', ''),
            abstract=data.get('abstract', ''),
            year=data.get('year', ''),
            url=data.get('url', ''),
            authors=data.get('authors', ''),
            source=data.get('source', ''),
            fulltext=data.get('fulltext'),
            doi=data.get('doi'),
            paper_id=data.get('paper_id')
        )


class DataSource(ABC):
    """Abstract base class for academic paper data sources."""
    
    def __init__(self, rate_limit_delay: float = 1.0) -> None:
        """
        Initialize a data source.
        
        Args:
            rate_limit_delay: Time to wait between API requests (in seconds)
        """
        self.rate_limit_delay = rate_limit_delay
    
    @abstractmethod
    def search(self, keywords: List[str], num_results: int) -> List[Paper]:
        """
        Search for papers matching the given keywords.
        
        Args:
            keywords: List of keywords to search for
            num_results: Maximum number of results to return
            
        Returns:
            List of Paper objects matching the search
        """
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Get the name of this data source.
        
        Returns:
            String name of the data source (e.g., "arxiv")
        """
        pass
