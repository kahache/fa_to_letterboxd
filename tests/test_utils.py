import unittest
from datetime import date, timedelta
from src.utils import DataCleaner

class TestDataCleaner(unittest.TestCase):
    """
    Test suite for the utility functions.
    """
    
    def test_date_parsing_relative(self):
        """Test 'today' and 'X days ago' logic."""
        today_iso = date.today().isoformat()
        two_days_ago = (date.today() - timedelta(days=2)).isoformat()
        
        self.assertEqual(DataCleaner.parse_fa_date("Today"), today_iso)
        self.assertEqual(DataCleaner.parse_fa_date("2 days ago"), two_days_ago)

    def test_date_parsing_absolute(self):
        """Test specific date string formats."""
        # Test English format from FilmAffinity
        self.assertEqual(DataCleaner.parse_fa_date("February 13, 2026"), "2026-02-13")
        self.assertEqual(DataCleaner.parse_fa_date("Feb 13, 2026"), "2026-02-13")

    def test_title_cleaning(self):
        """Test title whitespace cleaning."""
        dirty_title = "\n   Inception    \n"
        self.assertEqual(DataCleaner.clean_title(dirty_title), "Inception")

if __name__ == "__main__":
    unittest.main()
