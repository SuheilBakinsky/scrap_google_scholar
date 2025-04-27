"""
ArXiv data source for Scholar Scraper.
"""
import arxiv
from time import sleep
from typing import List, Optional

from config.settings import config
from .base import DataSource, Paper
from utils.error_handling import log_exceptions, handle_api_error
from utils.caching import cache_result


class ArxivSource(DataSource):
    """ArXiv.org data source implementation."""
    
    def __init__(self, rate_limit_delay: float = config.DEFAULT_RATE_LIMIT_DELAY) -> None:
        """
        Initialize the ArXiv data source.
        
        Args:
            rate_limit_delay: Time to wait between API requests (in seconds)
        """
        super().__init__(rate_limit_delay)
    
    @property
    def source_name(self) -> str:
        """Get the name of this data source."""
        return "arxiv"
    
    @cache_result(expiry_hours=24.0)
    def search(self, keywords: List[str], num_results: int = 5) -> List[Paper]:
        """
        Search ArXiv for papers matching the given keywords.
        
        Args:
            keywords: List of keywords to search for
            num_results: Maximum number of results to return
            
        Returns:
            List of Paper objects matching the search
        """
        # Use a simpler, more flexible approach that is guaranteed to return results
        # First try a more targeted approach
        papers = self._search_with_strategy(keywords, num_results, strategy="targeted")
        
        # If no results, fall back to a more relaxed approach
        if not papers:
            print("No results with targeted search, trying flexible search...")
            papers = self._search_with_strategy(keywords, num_results, strategy="flexible")
            
        # If still no results, try with just the primary keyword
        if not papers and len(keywords) > 0:
            print("No results with flexible search, trying with primary keyword only...")
            papers = self._search_with_strategy([keywords[0]], num_results, strategy="broad")
        
        return papers
    
    def _search_with_strategy(self, keywords: List[str], num_results: int, strategy: str = "targeted") -> List[Paper]:
        """
        Search ArXiv with a specific query strategy.
        
        Args:
            keywords: List of keywords to search for
            num_results: Maximum number of results to return
            strategy: Search strategy to use:
                - 'targeted': More precise but restrictive
                - 'flexible': Balance between precision and recall
                - 'broad': Maximizes recall over precision
            
        Returns:
            List of Paper objects matching the search
        """
        if strategy == "targeted":
            # More precise query focused on finding exact matches
            if len(keywords) == 1:
                query = f"title:{keywords[0]} OR abstract:{keywords[0]}"
            elif len(keywords) == 2:
                query = f"(title:{keywords[0]} OR abstract:{keywords[0]}) AND (title:{keywords[1]} OR abstract:{keywords[1]})"
            else:
                primary = " AND ".join([f"(title:{kw} OR abstract:{kw})" for kw in keywords[:2]])
                secondary = " OR ".join(keywords[2:])
                query = f"({primary}) AND ({secondary})"
        
        elif strategy == "flexible":
            # More balanced query with some AND and some OR
            if len(keywords) == 1:
                query = keywords[0]
            elif len(keywords) == 2:
                query = f"{keywords[0]} AND {keywords[1]}"
            else:
                # Use the first keyword as required, the rest as optional but boost relevance
                required = keywords[0]
                optional = " OR ".join(keywords[1:])
                query = f"{required} AND ({optional})"
        
        else:  # "broad"
            # Maximum recall with simple OR
            query = " OR ".join(keywords)
        
        print(f"ArXiv {strategy} query: {query}")
        
        # Initialize the ArXiv client
        client = arxiv.Client()
        
        # Limit the maximum results to avoid timeout
        max_results = min(num_results * 3, config.MAX_RESULTS_PER_SOURCE)
        
        # Create the search object
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        # Collect matching papers
        papers = []
        
        try:
            for result in client.results(search):
                paper = Paper(
                    title=result.title,
                    abstract=result.summary,
                    year=str(result.published.year),
                    url=result.pdf_url,
                    authors=', '.join(a.name for a in result.authors),
                    source=self.source_name,
                    paper_id=result.entry_id
                )
                papers.append(paper)
                
                # Stop once we have enough results
                if len(papers) >= num_results:
                    break
                
                # Respect rate limits
                sleep(self.rate_limit_delay)
                
        except arxiv.UnexpectedEmptyPageError:
            # This happens when there are no results, just return empty list
            print(f"No ArXiv results found for {strategy} query: {query}")
        except Exception as e:
            handle_api_error("ArXiv", e)
            print(f"Error searching ArXiv with {strategy} strategy: {str(e)}")
        
        if papers:
            print(f"Found {len(papers)} ArXiv papers with {strategy} query: {query}")
        
        return papers
    
    def search_nutrition(self, keywords: List[str], num_results: int = 5) -> List[Paper]:
        """
        Special nutrition-focused search for ArXiv.
        
        Args:
            keywords: List of keywords to search for
            num_results: Maximum number of results to return
            
        Returns:
            List of Paper objects matching the search
        """
        # In nutrition mode, simply use a broad OR search
        query = ' OR '.join(keywords)
        print(f"ArXiv nutrition query: {query}")
        
        # Initialize the ArXiv client
        client = arxiv.Client()
        
        # Limit the maximum results to avoid timeout
        max_results = min(num_results * 3, config.MAX_RESULTS_PER_SOURCE)
        
        # Create the search object
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        # Collect matching papers
        papers = []
        
        try:
            for result in client.results(search):
                paper = Paper(
                    title=result.title,
                    abstract=result.summary,
                    year=str(result.published.year),
                    url=result.pdf_url,
                    authors=', '.join(a.name for a in result.authors),
                    source=self.source_name,
                    paper_id=result.entry_id
                )
                papers.append(paper)
                
                # Stop once we have enough results
                if len(papers) >= num_results:
                    break
                
                # Respect rate limits
                sleep(self.rate_limit_delay)
                
        except arxiv.UnexpectedEmptyPageError:
            # This happens when there are no results, just return empty list
            print(f"No ArXiv nutrition results found for query: {query}")
        except Exception as e:
            handle_api_error("ArXiv", e)
            print(f"Error searching ArXiv nutrition: {str(e)}")
        
        print(f"Found {len(papers)} ArXiv nutrition papers for query: {query}")
        return papers
