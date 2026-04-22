import unittest
from src.models import MovieEntry

class TestMovieEntry(unittest.TestCase):
    """
    Test suite for the MovieEntry dataclass.
    """
    def test_to_dict_conversion(self):
        """
        Check if the dictionary keys match Letterboxd requirements.
        """
        entry = MovieEntry(
            title="Before the Devil Knows You're Dead",
            year="2007",
            directors="Sidney Lumet",
            rating10="7",
            watched_date="2026-02-13"
        )
        data = entry.to_dict()
        
        # Verify keys
        self.assertIn("Title", data)
        self.assertIn("Rating10", data)
        
        # Verify values
        self.assertEqual(data["Title"], "Before the Devil Knows You're Dead")
        self.assertEqual(data["Year"], "2007")
        self.assertEqual(data["Rating10"], "7")

if __name__ == "__main__":
    unittest.main()
