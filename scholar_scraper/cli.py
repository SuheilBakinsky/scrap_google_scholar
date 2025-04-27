"""
Command-line interface for the Scholar Scraper application.
"""
import argparse
import sys
from typing import List, Optional
from tqdm import tqdm

from config.settings import config
from scholar_scraper.core import ScholarScraper
from utils.error_handling import ScholarScraperError


def create_parser() -> argparse.ArgumentParser:
    """
    Create the command-line argument parser.
    
    Returns:
        Configured ArgumentParser object
    """
    parser = argparse.ArgumentParser(
        description='Search academic databases for papers and generate summaries with Gemini'
    )
    
    # Input options
    input_group = parser.add_argument_group('Input Options')
    input_group.add_argument(
        '--question', 
        type=str, 
        help='Research question to extract keywords and drive the search'
    )
    input_group.add_argument(
        'keywords', 
        nargs='*', 
        help='Keywords to search for (space-separated, overrides --question if given)'
    )
    
    # Search options
    search_group = parser.add_argument_group('Search Options')
    search_group.add_argument(
        '--num-papers', 
        type=int, 
        default=config.DEFAULT_NUM_RESULTS, 
        help=f'Number of papers to retrieve per source (default: {config.DEFAULT_NUM_RESULTS})'
    )
    search_group.add_argument(
        '--source', 
        dest='sources', 
        nargs='+', 
        choices=['arxiv', 'pubmed'], 
        default=config.DEFAULT_SOURCES,
        help='Space-separated list of sources to search (default: arxiv pubmed)'
    )
    search_group.add_argument(
        '--semantic-search', 
        action='store_true', 
        help='Use semantic search to rank the results'
    )
    search_group.add_argument(
        '--no-parallel', 
        action='store_true', 
        help='Disable parallel search (search sources sequentially)'
    )
    
    # Content options
    content_group = parser.add_argument_group('Content Options')
    content_group.add_argument(
        '--abstracts-only', 
        action='store_true', 
        help='Only include abstracts in the semantic search'
    )
    content_group.add_argument(
        '--nutrition-only', 
        action='store_true', 
        help='Use nutrition-specific prompts for Gemini summarization'
    )
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        '--no-summary', 
        action='store_true', 
        help='Do not display the summary in the terminal (still saved to file)'
    )
    output_group.add_argument(
        '--output-dir', 
        type=str, 
        default=str(config.RESULTS_DIR),
        help=f'Directory to save results (default: {config.RESULTS_DIR})'
    )
    
    # Advanced options
    advanced_group = parser.add_argument_group('Advanced Options')
    advanced_group.add_argument(
        '--clear-cache', 
        action='store_true',
        help='Clear the cache before running'
    )
    advanced_group.add_argument(
        '--cache-age', 
        type=float,
        help='Clear cache files older than this many hours'
    )
    
    return parser


def run_cli() -> int:
    """
    Run the command-line interface.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # Initialize the ScholarScraper
        scraper = ScholarScraper()
        
        # Handle cache clearing if requested
        if args.clear_cache:
            cleared = scraper.clear_cache(args.cache_age)
            print(f"Cleared {cleared} cache files")
        
        # Process input
        if args.question:
            print("\nExtracting search keywords for your question using Gemini and proceeding with search:\n")
            print(f"Question: {args.question}\n")
            
            # Translate the question if needed
            question = scraper.gemini_api.translate_to_english(args.question)
            
            # Extract keywords from the question
            kw_pairs = scraper.extract_keywords_from_question(question)
            print("Keywords (with weights):")
            for kw, wt in kw_pairs:
                print(f"- {kw} (weight {wt})")
            
            # Extract just the keywords for searching
            keywords = [kw for kw, wt in kw_pairs]
            query_for_semantic = question
            
        elif args.keywords:
            # If keywords is a single argument, split by comma and strip whitespace
            if len(args.keywords) == 1:
                raw = args.keywords[0]
                keywords = [kw.strip(' ,') for kw in raw.split(',') if kw.strip(' ,')]
            else:
                keywords = [kw.strip(' ,') for kw in args.keywords if kw.strip(' ,')]
            
            # Translate keywords
            translated_keywords = scraper.translate_keywords(keywords)
            print(f"Translated keywords: {translated_keywords}")
            
            keywords = translated_keywords
            query_for_semantic = ' '.join(keywords)
            
        else:
            parser.error('Either keywords or --question must be provided')
        
        print(f"Using the following keywords for search: {', '.join(keywords)}")
        print(f"Searching sources: {', '.join(args.sources)}")
        
        # Search for papers
        print("Searching for papers...")
        papers = scraper.search_papers(
            keywords, 
            args.num_papers * 3 if args.semantic_search else args.num_papers, 
            args.sources, 
            args.nutrition_only,
            not args.no_parallel
        )
        
        # Rank results with semantic search if requested
        if args.semantic_search and papers:
            print("Ranking papers by relevance...")
            top_k = args.num_papers
            papers = scraper.semantic_search(
                query_for_semantic, 
                papers, 
                top_k=top_k, 
                abstracts_only=args.abstracts_only
            )
        
        if papers:
            # Show source breakdown
            print("\n=== Source breakdown ===")
            src_count = scraper.get_source_breakdown(papers)
            for src, count in src_count.items():
                print(f"{src}: {count} papers")
            
            # Generate summary
            print("\nGenerating summary...")
            summary = scraper.summarize_papers(
                papers, 
                keywords, 
                args.nutrition_only
            )
            
            # Save results to file
            filename = scraper.save_results(papers, summary, keywords)
            
            # Display results
            if not args.no_summary:
                print("\n=== Summary ===")
                print(summary)
            
            # Show paper count
            print("\n=== Found Papers ===")
            arxiv_count = sum(1 for p in papers if p.source == 'arxiv')
            pubmed_count = sum(1 for p in papers if p.source == 'pubmed')
            
            print(f"\nFound {arxiv_count} arXiv papers and {pubmed_count} PubMed papers.")
            print("See the results file for complete details.")
            print(f"\nResults saved to {filename}")
            
        else:
            print("No papers found matching the keywords.")
        
        return 0
    
    except ScholarScraperError as e:
        print(f"Error: {str(e)}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(run_cli())
