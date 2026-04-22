import unittest
from unittest.mock import MagicMock, patch
from src.scraper import FilmAffinityScraper

class TestScraper(unittest.TestCase):
    """
    Test suite for the Network Scraper using Mocking.
    """

    @patch('tls_client.Session.get')
    def test_scraper_success(self, mock_get):
        """Test successful page retrieval."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Success</html>"
        mock_get.return_value = mock_response

        scraper = FilmAffinityScraper()
        content = scraper.get_ratings_page("760411", 1)
        
        self.assertEqual(content, "<html>Success</html>")
        self.assertEqual(mock_get.call_count, 1)

    @patch('tls_client.Session.get')
    def test_scraper_failure(self, mock_get):
        """Test error handling on 404/500."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        scraper = FilmAffinityScraper()
        content = scraper.get_ratings_page("760411", 1)
        
        self.assertIsNone(content)

if __name__ == "__main__":
    unittest.main()
