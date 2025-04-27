# Scholar Scraper

A powerful Python application to search academic databases (ArXiv, PubMed) for research papers and generate summaries using AI.

## Features

- **Multiple Data Sources**: Search ArXiv and PubMed for research papers
- **AI-powered Summaries**: Generate comprehensive summaries using Google Gemini API
- **Smart Ranking**: Semantic search to rank papers by relevance to your query
- **Language Support**: Automatic translation of non-English queries and keywords
- **Parallel Processing**: Fetch results from multiple sources simultaneously 
- **Intelligent Caching**: Avoid redundant API calls with built-in caching system
- **Nutritional Analysis**: Special mode for analyzing food ingredients

## Setup

1. Clone the repository
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```
3. Create a `.env` file with your Google Gemini API key:
```
GOOGLE_GEMINI_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

```bash
python main.py keyword1 keyword2 keyword3
```

### With a Research Question

```bash
python main.py --question "What is the impact of climate change on wheat production?"
```

### Command-line Options

#### Input Options
- `--question TEXT` - Research question to extract keywords and drive the search
- Keywords can be provided as positional arguments

#### Search Options
- `--num-papers N` - Number of papers to retrieve per source (default: 10)
- `--source [arxiv] [pubmed]` - Sources to search (default: both)
- `--semantic-search` - Use semantic search to rank results by relevance
- `--no-parallel` - Disable parallel search (search sources sequentially)

#### Content Options
- `--abstracts-only` - Only use abstracts for semantic search (faster)
- `--nutrition-only` - Use nutrition-specific prompts for summarization

#### Output Options
- `--no-summary` - Don't display the summary in the terminal (still saved to file)
- `--output-dir DIR` - Directory to save results (default: ./results)

#### Advanced Options
- `--clear-cache` - Clear the cache before running
- `--cache-age HOURS` - Clear cache files older than specified hours

## Project Structure

- `main.py` - Main entry point
- `scholar_scraper/` - Core package
  - `core.py` - Main ScholarScraper class
  - `cli.py` - Command-line interface
- `api/` - API integrations
  - `gemini.py` - Google Gemini API client
- `sources/` - Data source implementations
  - `arxiv_source.py` - ArXiv integration
  - `pubmed_source.py` - PubMed integration
- `utils/` - Utility functions
  - `caching.py` - API response caching
  - `error_handling.py` - Error handling utilities
- `config/` - Configuration
  - `settings.py` - Application settings
- `tests/` - Unit tests

## Note

- Requires a Google Gemini API key (see setup)
- For best results, use Python 3.8+ (Python 3.13 is not yet fully supported by all dependencies).
