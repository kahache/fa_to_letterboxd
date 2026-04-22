from dataclasses import dataclass, fields
from typing import Optional

@dataclass
class MovieEntry:
    """
    Represents a single movie rating entry from FilmAffinity.
    """
    title: str
    year: Optional[str] = None
    directors: Optional[str] = None
    rating10: Optional[str] = None
    watched_date: Optional[str] = None

    def to_dict(self):
        """
        Converts the dataclass instance to a dictionary 
        matching the Letterboxd CSV header format.
        """
        return {
            "Title": self.title,
            "Year": self.year,
            "Directors": self.directors,
            "Rating10": self.rating10,
            "WatchedDate": self.watched_date
        }
