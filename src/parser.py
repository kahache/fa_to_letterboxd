import re
from bs4 import BeautifulSoup
from src.models import MovieEntry
from src.utils import DataCleaner

class FilmAffinityParser:
    """
    Service class to parse FilmAffinity HTML pages and extract movie data.
    """
    
    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, "lxml")

    def get_total_pages(self) -> int:
        """
        Extracts the total number of pages from the pagination element.
        """
        pagination = self.soup.find_all("a", href=re.compile(r"[?&]p=\d+"))
        if not pagination:
            return 1
        
        page_numbers = []
        for link in pagination:
            match = re.search(r"p=(\d+)", link["href"])
            if match:
                page_numbers.append(int(match.group(1)))
        
        return max(page_numbers) if page_numbers else 1

    def parse_movies(self, skip_tv: bool = False) -> list[MovieEntry]:
        """
        Extracts all movies from the page.
        """
        entries = []
        # Each date block is a 'fa-content-card'
        date_blocks = self.soup.find_all("div", class_="fa-content-card")
        
        for block in date_blocks:
            watched_date = None
            header = block.find("div", class_="card-header")
            if header:
                watched_date = DataCleaner.parse_fa_date(header.get_text(strip=True))
                
            # Find all movie cards within this date block
            movie_cards = block.find_all("div", class_=re.compile(r"movie-card"))
            
            for card in movie_cards:
                title_container = card.find("div", class_="mc-title")
                if not title_container:
                    continue
                
                # Get clean title from the link tag to avoid duplicates
                title_link = title_container.find("a")
                raw_title = title_link.get_text(strip=True) if title_link else title_container.get_text(strip=True)
                title = DataCleaner.clean_title(raw_title)
                
                # TV Filter logic
                is_tv = any(kw in title for kw in ["(TV Series)", "Serie de TV", "Miniserie"])
                if skip_tv and is_tv:
                    continue
                    
                year_el = card.find("span", class_="mc-year")
                year = year_el.get_text(strip=True) if year_el else ""
                    
                dir_container = card.find("div", class_="mc-director")
                director = ", ".join([d.get_text(strip=True) for d in dir_container.find_all("a")]) if dir_container else ""
                    
                # Find the rating in the parent row container
                rating = ""
                row_container = card.find_parent("div", class_=re.compile(r"row mb-4|row"))
                if row_container:
                    rat_box = row_container.find("div", class_=re.compile(r"fa-user-rat-box"))
                    if rat_box:
                        rat_match = re.search(r"(\d+)", rat_box.get_text())
                        if rat_match:
                            rating = rat_match.group(1)

                entries.append(MovieEntry(
                    title=title,
                    year=year,
                    directors=director,
                    rating10=rating,
                    watched_date=watched_date
                ))
                
        return entries
