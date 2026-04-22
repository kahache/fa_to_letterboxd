import unittest
from src.parser import FilmAffinityParser

class TestParser(unittest.TestCase):
    """
    Test suite for the HTML Parser.
    """
    
    def test_basic_parsing(self):
        """
        Test parsing with a minimal HTML structure.
        """
        html = """
        <div class="fa-content-card">
            <div class="card-header">February 13, 2026</div>
            <div class="row mb-4">
                <div class="movie-card">
                    <div class="mc-title"><a>Inception</a></div>
                    <span class="mc-year">2010</span>
                    <div class="mc-director"><a>Christopher Nolan</a></div>
                </div>
                <div class="fa-user-rat-box">8</div>
            </div>
        </div>
        """
        parser = FilmAffinityParser(html)
        movies = parser.parse_movies()
        
        self.assertEqual(len(movies), 1)
        self.assertEqual(movies[0].title, "Inception")
        self.assertEqual(movies[0].rating10, "8")
        self.assertEqual(movies[0].watched_date, "2026-02-13")

if __name__ == "__main__":
    unittest.main()
