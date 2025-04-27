"""
Basic tests for the Scholar Scraper application.
"""
import unittest
from unittest.mock import patch, MagicMock

from sources.base import Paper
from scholar_scraper.core import ScholarScraper


class TestScholarScraper(unittest.TestCase):
    """Test cases for the ScholarScraper class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use patch to avoid actual API calls during tests
        self.gemini_patch = patch('scholar_scraper.core.GeminiAPI')
        self.mock_gemini = self.gemini_patch.start()
        
        # Mock translate method
        self.mock_gemini.return_value.translate_to_english.return_value = "corn"
        
        # Create scraper instance with mocked dependencies
        self.scraper = ScholarScraper()
    
    def tearDown(self):
        """Tear down test fixtures."""
        self.gemini_patch.stop()
    
    def test_translate_keywords(self):
        """Test keyword translation."""
        result = self.scraper.translate_keywords(["Mais"])
        self.assertEqual(result, ["corn"])
        self.mock_gemini.return_value.translate_to_english.assert_called_with("Mais", 'German')
    
    def test_get_source_breakdown(self):
        """Test source breakdown calculation."""
        papers = [
            Paper("Title 1", "Abstract 1", "2022", "url1", "Author 1", "arxiv"),
            Paper("Title 2", "Abstract 2", "2023", "url2", "Author 2", "arxiv"),
            Paper("Title 3", "Abstract 3", "2021", "url3", "Author 3", "pubmed")
        ]
        
        breakdown = self.scraper.get_source_breakdown(papers)
        self.assertEqual(breakdown, {"arxiv": 2, "pubmed": 1})


if __name__ == "__main__":
    unittest.main()
