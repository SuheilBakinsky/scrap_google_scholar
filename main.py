#!/usr/bin/env python
"""
Scholar Scraper - Search academic databases and summarize papers with Gemini.
Main entry point for the application.
"""
import sys
from typing import List, Optional
from scholar_scraper.cli import run_cli
from scholar_scraper.core import ScholarScraper


def main(
    keywords: Optional[List[str]] = None, 
    question: Optional[str] = None,
    num_papers: int = 10,
    sources: Optional[List[str]] = None,
    nutrition_only: bool = False,
    semantic_search: bool = False,
    abstracts_only: bool = False,
    no_summary: bool = False,
    no_parallel: bool = False
) -> int:
    """
    Main entry point for the Scholar Scraper application.
    
    Args:
        keywords: List of keywords to search for
        question: Research question to extract keywords from
        num_papers: Number of papers to retrieve per source
        sources: List of sources to search (defaults to ['arxiv', 'pubmed'])
        nutrition_only: Whether to use nutrition-specific prompts
        semantic_search: Whether to use semantic search for ranking
        abstracts_only: Whether to only include abstracts in semantic search
        no_summary: Whether to hide the summary in terminal output
        no_parallel: Whether to disable parallel searching
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # If parameters are provided, use them directly
    if keywords or question:
        # Initialize the scraper
        scraper = ScholarScraper()
        
        # Process question if provided
        if question:
            print(f"Question: {question}")
            # Translate the question if needed
            translated_question = scraper.gemini_api.translate_to_english(question)
            # Extract keywords from the question
            kw_pairs = scraper.extract_keywords_from_question(translated_question)
            keywords = [kw for kw, wt in kw_pairs]
            query_for_semantic = translated_question
        elif keywords:
            # Translate keywords
            translated_keywords = scraper.translate_keywords(keywords)
            keywords = translated_keywords
            query_for_semantic = ' '.join(keywords)
        
        # Use default sources if none provided
        if not sources:
            sources = ['arxiv', 'pubmed']
            
        print(f"Using the following keywords for search: {', '.join(keywords)}")
        print(f"Searching sources: {', '.join(sources)}")
        
        # Search for papers
        papers = scraper.search_papers(
            keywords, 
            num_papers * 3 if semantic_search else num_papers, 
            sources, 
            nutrition_only,
            not no_parallel
        )
        
        # Rank results with semantic search if requested
        if semantic_search and papers:
            papers = scraper.semantic_search(
                query_for_semantic, 
                papers, 
                top_k=num_papers, 
                abstracts_only=abstracts_only
            )
        
        if papers:
            # Generate summary
            summary = scraper.summarize_papers(papers, keywords, nutrition_only)
            
            # Save results to file
            filename = scraper.save_results(papers, summary, keywords)
            
            # Display results if requested
            if not no_summary:
                print("\n=== Summary ===")
                print(summary)
            
            print(f"\nResults saved to {filename}")
            return 0
        else:
            print("No papers found matching the keywords.")
            return 1
    
    # Otherwise, use the CLI interface
    return run_cli()


if __name__ == "__main__":
    sys.exit(main())
