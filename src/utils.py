import re
from datetime import date, timedelta, datetime
from typing import Optional

class DataCleaner:
    """
    Service class to clean and format data extracted from FilmAffinity.
    """
    
    @staticmethod
    def parse_fa_date(raw_text: str) -> Optional[str]:
        """
        Converts FilmAffinity relative dates (today, 2 days ago) 
        or absolute dates into ISO format (YYYY-MM-DD).
        """
        today = date.today()
        # Remove "Rated" prefix if exists
        text = re.sub(r"^Rated\s*", "", raw_text, flags=re.I).strip()
        
        if not text:
            return None
            
        lower_text = text.lower()
        if lower_text == "today":
            return today.isoformat()
        if lower_text == "yesterday":
            return (today - timedelta(days=1)).isoformat()
            
        # Match "X days ago"
        days_ago_match = re.match(r"(\d+)\s+days?\s+ago", lower_text)
        if days_ago_match:
            days = int(days_ago_match.group(1))
            return (today - timedelta(days=days)).isoformat()
            
        # Try standard date formats
        date_formats = (
            "%B %d, %Y", "%b %d, %Y", "%d/%m/%Y", 
            "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y"
        )
        for fmt in date_formats:
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
                
        return None

    @staticmethod
    def clean_title(title_text: str) -> str:
        """
        Cleans titles to avoid duplicates caused by responsive 
        HTML elements or extra whitespace.
        """
        if not title_text:
            return ""
        # Remove extra whitespace and line breaks
        clean = " ".join(title_text.split())
        return clean
