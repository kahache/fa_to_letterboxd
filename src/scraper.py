import time
import random
import logging
import tls_client
from typing import Optional

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class FilmAffinityScraper:
    """
    Handles network requests to FilmAffinity using tls-client 
    to mimic modern browser fingerprints.
    """
    
    BASE_URL = "https://www.filmaffinity.com"

    def __init__(self, language: str = "en"):
        self.language = language
        # Initialize a Chrome-like session
        self.session = tls_client.Session(
            client_identifier="chrome_120",
            random_tls_extension_order=True
        )
        self._set_headers()

    def _set_headers(self):
        """Sets the initial headers for the session."""
        self.session.headers.update({
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"{self.BASE_URL}/{self.language}/main.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def warm_up(self):
        """Visits the homepage to establish cookies."""
        logging.info("Warming up session...")
        try:
            self.session.get(f"{self.BASE_URL}/{self.language}/main.html", timeout_seconds=15)
            time.sleep(random.uniform(1.5, 3.0))
        except Exception as e:
            logging.error(f"Warm-up failed: {e}")

    def get_ratings_page(self, user_id: str, page: int) -> Optional[str]:
        """
        Fetches a specific ratings page for a user.
        """
        url = (
            f"{self.BASE_URL}/{self.language}/userratings.php?"
            f"user_id={user_id}&p={page}&orderby=rating-date&chv=list"
        )
        
        logging.info(f"Fetching page {page}...")
        
        try:
            # Random delay to mimic human behavior
            if page > 1:
                time.sleep(random.uniform(2.0, 4.0))
                
            response = self.session.get(url, timeout_seconds=20)
            
            if response.status_code == 200:
                return response.text
            else:
                logging.error(f"Failed to fetch page {page}. Status: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Network error on page {page}: {e}")
            return None
