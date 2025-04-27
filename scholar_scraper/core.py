"""
Core functionality for Scholar Scraper.
This module contains the main ScholarScraper class that coordinates the search process.
"""
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from sentence_transformers import SentenceTransformer, util

from api.gemini import GeminiAPI
from config.settings import config
from sources.arxiv_source import ArxivSource
from sources.pubmed_source import PubmedSource
from sources.base import DataSource, Paper
from utils.error_handling import log_exceptions, DataSourceError
from utils.caching import cache_result


class ScholarScraper:
    """
    Main class for searching academic papers and generating summaries.
    
    This class coordinates the search process across multiple data sources,
    deduplicates results, and generates summaries using the Gemini API.
    """
    
    def __init__(self) -> None:
        """Initialize the ScholarScraper with data sources and APIs."""
        # Initialize data sources
        self.sources: Dict[str, DataSource] = {
            "arxiv": ArxivSource(),
            "pubmed": PubmedSource()
        }
        
        # Initialize APIs
        self.gemini_api = GeminiAPI()
        
        # Check configuration
        config_errors = config.validate()
        if config_errors:
            error_msg = "; ".join(f"{k}: {v}" for k, v in config_errors.items())
            raise ValueError(f"Configuration errors: {error_msg}")
    
    def translate_keywords(self, keywords: List[str], source_lang: str = 'German') -> List[str]:
        """
        Translate keywords to English if necessary.
        
        Args:
            keywords: List of keywords to translate
            source_lang: Source language of the keywords
            
        Returns:
            List of translated keywords in English
        """
        translated_keywords = []
        for kw in keywords:
            # Translate the keyword
            translated = self.gemini_api.translate_to_english(kw, source_lang)
            # Clean up and add to result list
            translated_keywords.append(translated.strip(', '))
        return translated_keywords
    
    def extract_keywords_from_question(self, question: str) -> List[Tuple[str, int]]:
        """
        Extract relevant search keywords from a research question.
        
        Args:
            question: Research question text
            
        Returns:
            List of (keyword, weight) tuples
        """
        # First translate the question if needed
        question = self.gemini_api.translate_to_english(question)
        # Then extract keywords
        return self.gemini_api.extract_keywords_from_question(question)
    
    def search_source(self, source_name: str, keywords: List[str], 
                     num_results: int, nutrition_only: bool = False) -> List[Paper]:
        """
        Search a specific source for papers.
        
        Args:
            source_name: Name of the source to search
            keywords: List of keywords to search for
            num_results: Maximum number of results to return
            nutrition_only: Whether to use nutrition-specific search
            
        Returns:
            List of Paper objects from the search
            
        Raises:
            DataSourceError: If the source is not available
        """
        source = self.sources.get(source_name)
        if not source:
            raise DataSourceError(source_name, f"Source '{source_name}' not available")
        
        if nutrition_only:
            # Use nutrition-specific search if available
            if hasattr(source, 'search_nutrition'):
                return source.search_nutrition(keywords, num_results)
        
        # Default to standard search
        return source.search(keywords, num_results)
    
    def search_papers(self, keywords: List[str], num_results: int = 5, 
                     sources: Optional[List[str]] = None, 
                     nutrition_only: bool = False,
                     parallel: bool = True) -> List[Paper]:
        """
        Search multiple sources for papers matching the keywords.
        
        Args:
            keywords: List of keywords to search for
            num_results: Maximum number of results per source
            sources: List of sources to search (defaults to all available)
            nutrition_only: Whether to use nutrition-specific search
            parallel: Whether to search sources in parallel
            
        Returns:
            List of Paper objects from all sources, deduplicated
        """
        if not sources:
            sources = list(self.sources.keys())
        
        # Filter to only available sources
        available_sources = [s for s in sources if s in self.sources]
        if not available_sources:
            raise ValueError(f"None of the requested sources {sources} are available")
        
        papers: List[Paper] = []
        source_papers: Dict[str, List[Paper]] = {}
        
        if parallel:
            # Search sources in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=len(available_sources)) as executor:
                # Create future for each source
                future_to_source = {
                    executor.submit(self.search_source, source, keywords, num_results, nutrition_only): source
                    for source in available_sources
                }
                
                # Process results as they complete
                for future in as_completed(future_to_source):
                    source = future_to_source[future]
                    try:
                        source_papers[source] = future.result()
                        papers.extend(source_papers[source])
                    except Exception as e:
                        print(f"Error searching {source}: {str(e)}")
                        source_papers[source] = []
        else:
            # Search sources sequentially
            for source in available_sources:
                try:
                    source_results = self.search_source(source, keywords, num_results, nutrition_only)
                    source_papers[source] = source_results
                    papers.extend(source_results)
                except Exception as e:
                    print(f"Error searching {source}: {str(e)}")
                    source_papers[source] = []
        
        # Print pre-deduplication counts
        source_counts = {s: len(source_papers.get(s, [])) for s in available_sources}
        print(f"Before deduplication: {', '.join(f'{s}={c}' for s, c in source_counts.items())}")
        
        # Deduplicate papers by title
        by_source: Dict[str, List[Paper]] = {s: [] for s in available_sources}
        for paper in papers:
            src = paper.source
            if src in by_source and len(by_source[src]) < num_results:
                # Only add if not already present (by title)
                if not any(p.title == paper.title for p in by_source[src]):
                    by_source[src].append(paper)
        
        # Flatten the results and report post-deduplication counts
        result = []
        for source in available_sources:
            result.extend(by_source.get(source, []))
        
        post_counts = {s: len(by_source.get(s, [])) for s in available_sources}
        print(f"After deduplication: {', '.join(f'{s}={c}' for s, c in post_counts.items())}")
        
        return result
    
    @cache_result(expiry_hours=168.0)  # Cache for a week
    def semantic_search(self, query: str, papers: List[Paper], 
                       model_name: str = config.DEFAULT_SENTENCE_TRANSFORMER_MODEL, 
                       top_k: int = 10, abstracts_only: bool = True) -> List[Paper]:
        """
        Rank papers by semantic similarity to the query.
        
        Args:
            query: The search query to rank against
            papers: List of papers to rank
            model_name: Name of the sentence transformer model to use
            top_k: Number of top results to return
            abstracts_only: Whether to only use abstracts (vs fulltext)
            
        Returns:
            List of papers sorted by relevance to the query
        """
        if not papers:
            return []
        
        # Group papers by source
        papers_by_source: Dict[str, List[Paper]] = {}
        for paper in papers:
            if paper.source not in papers_by_source:
                papers_by_source[paper.source] = []
            papers_by_source[paper.source].append(paper)
        
        # Get available sources from the papers
        available_sources = list(papers_by_source.keys())
        if not available_sources:
            return []
        
        # Calculate how many papers to get from each source
        papers_per_source = max(1, top_k // len(available_sources))
        
        # Load the model
        model = SentenceTransformer(model_name)
        
        # Encode the query
        query_emb = model.encode(query, convert_to_tensor=True)
        
        # Process each source separately and collect top papers
        result_papers = []
        
        for source in available_sources:
            source_papers = papers_by_source[source]
            if not source_papers:
                continue
                
            # Prepare text representations of papers from this source
            texts = []
            for paper in source_papers:
                if abstracts_only:
                    texts.append(paper.abstract)
                else:
                    texts.append(paper.fulltext or paper.abstract)
            
            # Encode the texts
            doc_embs = model.encode(texts, convert_to_tensor=True)
            
            # Calculate cosine similarity for this source's papers
            cos_scores = util.cos_sim(query_emb, doc_embs)[0]
            
            # Get indices of top-k scores for this source
            source_top_k = min(papers_per_source, len(source_papers))
            top_indices = cos_scores.argsort(descending=True)[:source_top_k]
            
            # Add top papers from this source to the result
            result_papers.extend([source_papers[i] for i in top_indices])
        
        # Log the results for debugging
        source_counts = Counter([p.source for p in result_papers])
        print(f"After semantic search: {', '.join(f'{s}={c}' for s, c in source_counts.items())}")
        
        # If we need to reduce the total number of papers, apply global ranking
        if len(result_papers) > top_k:
            # Re-rank all selected papers globally
            texts = []
            for paper in result_papers:
                if abstracts_only:
                    texts.append(paper.abstract)
                else:
                    texts.append(paper.fulltext or paper.abstract)
            
            # Encode the texts
            doc_embs = model.encode(texts, convert_to_tensor=True)
            
            # Calculate cosine similarity
            cos_scores = util.cos_sim(query_emb, doc_embs)[0]
            
            # Get indices of top-k scores
            final_top_k = min(top_k, len(result_papers))
            top_indices = cos_scores.argsort(descending=True)[:final_top_k]
            
            # Create the final ranked list
            result_papers = [result_papers[i] for i in top_indices]
        
        return result_papers
    
    def summarize_papers(self, papers: List[Paper], keywords: List[str], 
                        nutrition_only: bool = False) -> str:
        """
        Generate a summary of the papers.
        
        Args:
            papers: List of papers to summarize
            keywords: Keywords used for the search
            nutrition_only: Whether to focus on nutritional aspects
            
        Returns:
            Generated summary text
        """
        abstracts = [paper.abstract for paper in papers]
        return self.gemini_api.summarize_papers(abstracts, keywords, nutrition_only)
    
    def save_results(self, papers: List[Paper], summary: str, keywords: List[str]) -> str:
        """
        Save search results to a file.
        
        Args:
            papers: List of papers to save
            summary: Generated summary text
            keywords: Keywords used for the search
            
        Returns:
            Path to the saved results file
        """
        # Create results directory if it doesn't exist
        os.makedirs(config.RESULTS_DIR, exist_ok=True)
        
        # Create a safe filename from keywords
        safe_keywords = '_'.join([k.replace(' ', '_') for k in keywords[:5]])
        filename = config.RESULTS_DIR / f"results_{safe_keywords}.txt"
        
        # Write the results to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== Summary ===\n")
            f.write(summary + "\n\n")
            f.write("=== Found Papers ===\n")
            
            for i, paper in enumerate(papers, 1):
                f.write(f"\n{i}. {paper.title}\n")
                f.write(f"   Year: {paper.year}\n")
                if paper.url:
                    f.write(f"   URL: {paper.url}\n")
                f.write(f"   Authors: {paper.authors}\n")
                f.write(f"   Source: {paper.source}\n")
                f.write("-" * 80 + "\n")
        
        return str(filename)
    
    def get_source_breakdown(self, papers: List[Paper]) -> Dict[str, int]:
        """
        Get a breakdown of papers by source.
        
        Args:
            papers: List of papers to analyze
            
        Returns:
            Dictionary of paper counts by source
        """
        return dict(Counter(paper.source for paper in papers))
    
    def clear_cache(self, older_than_hours: Optional[float] = None) -> int:
        """
        Clear the cache of API responses.
        
        Args:
            older_than_hours: If provided, only clear cache files older than this many hours
            
        Returns:
            Number of cache files cleared
        """
        from utils.caching import clear_cache
        return clear_cache(older_than_hours)
