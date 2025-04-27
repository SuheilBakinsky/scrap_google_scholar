"""
PubMed data source for Scholar Scraper.
"""
import requests
import logging
from time import sleep
from typing import Dict, List, Optional, Any

from config.settings import config
from .base import DataSource, Paper
from utils.error_handling import log_exceptions, handle_api_error
from utils.caching import cache_result

# Set up logger
logger = logging.getLogger("scholar_scraper.pubmed")


class PubmedSource(DataSource):
    """PubMed data source implementation."""
    
    def __init__(self, rate_limit_delay: float = config.PUBMED_RATE_LIMIT_DELAY) -> None:
        """
        Initialize the PubMed data source.
        
        Args:
            rate_limit_delay: Time to wait between API requests (in seconds)
        """
        super().__init__(rate_limit_delay)
    
    @property
    def source_name(self) -> str:
        """Get the name of this data source."""
        return "pubmed"
    
    @cache_result(expiry_hours=24.0)
    def search(self, keywords: List[str], num_results: int = 5, raw_query: bool = False) -> List[Paper]:
        """
        Search PubMed for papers matching the given keywords.
        
        Args:
            keywords: List of keywords to search for
            num_results: Maximum number of results to return
            raw_query: If True, treat keywords as already formatted query strings
            
        Returns:
            List of Paper objects matching the search
        """
        # Build the query based on the mode
        if raw_query:
            # In nutrition mode, join keywords with OR - explicit parentheses for clarity
            query = '(' + ' OR '.join(keywords) + ')'
            logger.info(f"PubMed nutrition query: {query}")
            print(f"PubMed nutrition query: {query}")  # Keep print for user visibility
        else:
            # In regular mode, build a weighted query using PubMed's syntax
            # More important terms appear first in the query
            weighted_terms = []
            for i, kw in enumerate(keywords[:5]):  # Limit to top 5 keywords for better results
                # Add term with appropriate weight
                weighted_terms.append(f"{kw}[Title/Abstract]")
            
            # Join terms with AND, ensuring we get more relevant results
            query = ' AND '.join(weighted_terms)
            logger.info(f"PubMed regular query: {query}")
            print(f"PubMed regular query: {query}")  # Keep print for user visibility
        
        # Step 1: Search PubMed for paper IDs
        try:
            logger.info(f"Requesting PubMed IDs for query: {query} (max: {num_results*2})")
            id_list = self._search_pubmed_ids(query, num_results * 2)  # Fetch more to ensure we have enough after filtering
            if not id_list:
                logger.warning(f"No PubMed IDs found for query: {query}")
                print(f"No PubMed IDs found for query: {query}")
                return []
            
            logger.info(f"Found {len(id_list)} PubMed IDs for query: {query}")
            print(f"Found {len(id_list)} PubMed IDs for query: {query}")
            
            # Step 2: Fetch paper summaries and create Paper objects
            logger.info(f"Fetching details for {len(id_list)} PubMed papers")
            papers = self._fetch_pubmed_summaries(id_list)
            
            logger.info(f"Retrieved {len(papers)} valid PubMed papers")
            
            # Return up to num_results papers
            return papers[:num_results]
        
        except Exception as e:
            handle_api_error("PubMed", e)
            logger.error(f"Error searching PubMed: {str(e)}")
            print(f"Error searching PubMed: {str(e)}")
            return []
    
    def _search_pubmed_ids(self, query: str, num_results: int) -> List[str]:
        """
        Search PubMed for paper IDs matching the query.
        
        Args:
            query: Search query string
            num_results: Maximum number of results to return
            
        Returns:
            List of PubMed IDs matching the query
        """
        search_params = {
            'db': 'pubmed',
            'term': query,
            'retmax': num_results,
            'retmode': 'json',
            'sort': 'relevance'  # Sort by relevance
        }
        
        # Make the search request
        logger.debug(f"PubMed API request: {config.PUBMED_SEARCH_URL} with params {search_params}")
        search_resp = requests.get(
            config.PUBMED_SEARCH_URL, 
            params=search_params
        )
        search_resp.raise_for_status()
        
        # Extract the list of IDs from the response
        search_data = search_resp.json()
        id_list = search_data['esearchresult'].get('idlist', [])
        
        return id_list
    
    def _fetch_pubmed_summaries(self, id_list: List[str]) -> List[Paper]:
        """
        Fetch summaries for the given PubMed IDs.
        
        Args:
            id_list: List of PubMed IDs to fetch
            
        Returns:
            List of Paper objects with summary information
        """
        papers = []
        
        # First get the basic paper information
        fetch_params = {
            'db': 'pubmed',
            'id': ','.join(id_list),
            'retmode': 'json'
        }
        
        logger.debug(f"Fetching summaries for {len(id_list)} PubMed IDs")
        fetch_resp = requests.get(
            config.PUBMED_SUMMARY_URL, 
            params=fetch_params
        )
        fetch_resp.raise_for_status()
        
        summaries = fetch_resp.json()['result']
        
        # Now fetch each abstract individually
        for i, pmid in enumerate(id_list):
            logger.debug(f"Processing PubMed paper {i+1}/{len(id_list)}: ID {pmid}")
            data = summaries.get(pmid)
            if not data:
                logger.warning(f"Missing summary data for PubMed ID: {pmid}")
                continue
            
            # Extract paper metadata
            title = data.get('title', '')
            authors = ', '.join([a['name'] for a in data.get('authors', [])])
            year = data.get('pubdate', '').split(' ')[0]
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            
            # Fetch the abstract
            abstract = self._fetch_pubmed_abstract(pmid)
            
            # Create and add the Paper object
            paper = Paper(
                title=title,
                abstract=abstract,
                year=year,
                url=url,
                authors=authors,
                source=self.source_name,
                paper_id=pmid
            )
            papers.append(paper)
            
            # Respect rate limits
            sleep(self.rate_limit_delay)
        
        return papers
    
    def _fetch_pubmed_abstract(self, pmid: str) -> str:
        """
        Fetch the abstract for a PubMed ID.
        
        Args:
            pmid: PubMed ID to fetch the abstract for
            
        Returns:
            Abstract text or empty string if not available
        """
        fetch_abs_params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'text',
            'rettype': 'abstract'
        }
        
        try:
            logger.debug(f"Fetching abstract for PubMed ID: {pmid}")
            abs_resp = requests.get(
                config.PUBMED_FETCH_URL, 
                params=fetch_abs_params
            )
            
            if abs_resp.status_code == 200:
                return abs_resp.text.strip()
        except Exception as e:
            handle_api_error("PubMed Abstract", e)
            logger.warning(f"Failed to fetch abstract for PubMed ID {pmid}: {str(e)}")
        
        return ""  # Return empty string if abstract fetch fails
    
    def search_nutrition(self, keywords: List[str], num_results: int = 5) -> List[Paper]:
        """
        Nutrition-focused search for PubMed.
        
        Args:
            keywords: List of keywords to search for
            num_results: Maximum number of results to return
            
        Returns:
            List of Paper objects matching the search
        """
        # For nutrition searches, we use raw_query=True to use OR logic
        logger.info(f"Running PubMed nutrition search with keywords: {keywords}")
        return self.search(keywords, num_results, raw_query=True)
