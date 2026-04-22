#!/usr/bin/env python3
"""
fa_to_letterboxd.py
───────────────────
Scrapes public ratings of a FilmAffinity user and exports them
as a CSV file compatible with Letterboxd's diary importer.
"""

import argparse
import csv
import re
import sys
import time
import random
from dataclasses import dataclass, fields
from datetime import date, timedelta
from typing import Optional
from urllib.parse import urlencode
from datetime import datetime

# Anti-bot library
import tls_client
from bs4 import BeautifulSoup


# ──────────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class MovieEntry:
    Title: str
    Year: Optional[str]
    Directors: Optional[str]
    Rating10: Optional[str]
    WatchedDate: Optional[str]


# ──────────────────────────────────────────────────────────────────────────────
# HTTP (Using tls_client to bypass headers/fingerprinting checks)
# ──────────────────────────────────────────────────────────────────────────────

# Initialize session mimicking Chrome 120
SESSION = tls_client.Session(
    client_identifier="chrome_120",
    random_tls_extension_order=True
)

def _refresh_headers(lang: str = "en") -> None:
    """Updates headers to look like a real browser."""
    SESSION.headers.update({
        "Accept-Language": f"en-US,en;q=0.9,{lang};q=0.8",
        "Referer": f"https://www.filmaffinity.com/{lang}/main.html"
    })

def warm_up_session(lang: str = "en") -> None:
    """Visits the homepage to establish a valid session/cookies."""
    _refresh_headers(lang)
    home = f"https://www.filmaffinity.com/{lang}/main.html"
    print("  Warming up session (visiting homepage)…")
    try:
        resp = SESSION.get(home, timeout_seconds=15)
        if resp.status_code >= 400:
             print(f"  [!] Warm-up got HTTP {resp.status_code} (continuing anyway)")
        
        delay = random.uniform(2.0, 4.0)
        print(f"  Session ready. Waiting {delay:.1f}s before scraping…")
        time.sleep(delay)
    except Exception as exc:
        print(f"  [!] Warm-up failed (continuing anyway): {exc}", file=sys.stderr)


def fetch_page(url: str, retries: int = 5) -> Optional[BeautifulSoup]:
    """Fetches a URL and returns a BeautifulSoup object with retries."""
    for attempt in range(1, retries + 1):
        try:
            time.sleep(random.uniform(0.5, 1.2))
            resp = SESSION.get(url, timeout_seconds=20)

            if resp.status_code == 429:
                wait = 20 * attempt + random.uniform(5, 15)
                print(f"  [!] 429 Rate-limited. Waiting {wait:.0f}s before retry "
                      f"{attempt}/{retries}…", file=sys.stderr)
                time.sleep(wait)
                _refresh_headers()
                continue

            if resp.status_code >= 400:
                raise Exception(f"HTTP {resp.status_code}")
            
            SESSION.headers.update({"Referer": url})
            return BeautifulSoup(resp.text, "lxml")

        except Exception as exc:
            wait = 5 * attempt
            print(f"  [!] Request failed on attempt {attempt}/{retries}. "
                  f"Waiting {wait}s… ({exc})", file=sys.stderr)
            time.sleep(wait)

    return None


# ──────────────────────────────────────────────────────────────────────────────
# Parsing logic
# ──────────────────────────────────────────────────────────────────────────────

_YEAR_RE = re.compile(r"\((\d{4})\)")
_TV_KEYWORDS = (
    "(TV Series)", "(TV Mini-Series)", "(TV Movie)", "(TV Episode)",
    "(Short TV Series)", "Serie de TV", "Miniserie de TV",
    "Película de TV", "Episodio",
)

def _is_tv(text: str) -> bool:
    """Checks if a title represents a TV show based on keywords."""
    return any(kw.lower() in text.lower() for kw in _TV_KEYWORDS)

def _parse_fa_date(raw: str) -> Optional[str]:
    """Converts FilmAffinity relative dates (Today, 2 days ago) to ISO format."""
    today = date.today()
    text = re.sub(r"^Rated\s*", "", raw, flags=re.I).strip()
    if not text: return None
    if text.lower() == "today": return today.isoformat()
    if text.lower() == "yesterday": return (today - timedelta(days=1)).isoformat()
    
    m = re.match(r"(\d+)\s+days?\s+ago", text, re.I)
    if m: return (today - timedelta(days=int(m.group(1)))).isoformat()
    
    # Try different date formats based on site language
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d/%m/%y"):
        try: return datetime.strptime(text, fmt).date().isoformat()
        except ValueError: pass
        
    for fmt in ("%B %d", "%b %d"):
        try:
            parsed = datetime.strptime(text, fmt)
            candidate = date(today.year, parsed.month, parsed.day)
            if candidate > today:
                candidate = date(today.year - 1, parsed.month, parsed.day)
            return candidate.isoformat()
        except ValueError: pass
    return None

def _parse_list_view(soup, skip_tv: bool) -> list[MovieEntry]:
    """Parses the 'List' view (chv=list), extracting Title, Year, and Directors."""
    entries = []
    # FilmAffinity list view rows are typically 'rat-row' or containers of 'mc-title'
    rows = soup.find_all("div", class_=re.compile(r"rat-row|user-ratings-row"))
    
    if not rows:
        # Fallback for different layouts
        titles = soup.find_all("div", class_="mc-title")
        rows = [t.find_parent("div", class_="movie-card") or t.find_parent("div") for t in titles]

    for row in rows:
        if not row: continue
        
        # 1. Extract Title and Year
        title_container = row.find("div", class_="mc-title")
        if not title_container:
            title_container = row.find("a", href=re.compile(r"/film\d+\.html"))
        
        if not title_container: continue
        
        full_text = title_container.get_text(" ", strip=True)
        if skip_tv and _is_tv(full_text): continue
        
        # Link for the title
        link_el = title_container.find("a") if hasattr(title_container, "find") else title_container
        title = link_el.get_text(strip=True) if link_el else full_text
        
        # Year extraction
        year_match = _YEAR_RE.search(full_text)
        year = year_match.group(1) if year_match else None
        
        # 2. Extract Directors
        dir_container = row.find("div", class_="mc-director")
        if dir_container:
            directors = ", ".join([a.get_text(strip=True) for a in dir_container.find_all("a")])
        else:
            # Alternative: links with director stype
            dir_links = row.find_all("a", href=re.compile(r"stype=director|/director\.php"))
            directors = ", ".join([a.get_text(strip=True) for a in dir_links])
        
        # 3. Extract Rating
        # Class ur-iv-rat is standard for user ratings in list view
        rat_el = row.find("div", class_=re.compile(r"ur-iv-rat|avgrat-box"))
        rating = rat_el.get_text(strip=True) if rat_el else None
        if rating and not (rating.isdigit() and 1 <= int(rating) <= 10):
            rating = None
            
        # 4. Extract Watched Date
        date_el = row.find("div", class_="main-title-last") or row.find("small")
        watched_date = None
        if date_el:
            watched_date = _parse_fa_date(date_el.get_text(strip=True))

        entries.append(MovieEntry(
            Title=title, 
            Year=year, 
            Directors=directors if directors else None, 
            Rating10=rating, 
            WatchedDate=watched_date
        ))
    return entries

def get_total_pages(soup) -> int:
    """Determines total number of pages from pagination links or total count."""
    # Method A: Check pagination links
    page_links = soup.find_all("a", href=re.compile(r"[?&]p=\d+"))
    page_nums = []
    for a in page_links:
        m = re.search(r"[?&]p=(\d+)", a["href"])
        if m: page_nums.append(int(m.group(1)))
    
    if page_nums:
        return max(page_nums)
        
    # Method B: Parse the total count text (e.g., "1,500 ratings")
    for cls in ("tit-count-ratings", "count-ratings", "user-ratings-header", "header-count", "count"):
        el = soup.find(class_=cls)
        if el:
            # Clean thousands separators
            clean_text = el.get_text().replace(",", "").replace(".", "")
            nums = re.findall(r"\d+", clean_text)
            if nums: 
                total_items = int(nums[0])
                return (total_items + 49) // 50
                
    return 1

def build_url(user_id: str, page: int, lang: str, view: str = "list") -> str:
    """Constructs the FilmAffinity user ratings URL."""
    params = urlencode({
        "user_id": user_id, 
        "p": page, 
        "orderby": "rating-date", 
        "chv": view
    })
    return f"https://www.filmaffinity.com/{lang}/userratings.php?{params}"


# ──────────────────────────────────────────────────────────────────────────────
# Output & Main Loop
# ──────────────────────────────────────────────────────────────────────────────

def write_csv(entries: list[MovieEntry], output_path: str) -> None:
    """Writes the results to a Letterboxd-compatible CSV file."""
    col_names = [f.name for f in fields(MovieEntry)]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=col_names, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for e in entries:
            writer.writerow({
                "Title": e.Title, 
                "Year": e.Year or "", 
                "Directors": e.Directors or "", 
                "Rating10": e.Rating10 or "", 
                "WatchedDate": e.WatchedDate or ""
            })

def scrape(user_id: str, lang: str, skip_tv: bool, output: str, debug: bool = False) -> None:
    """Main scraping orchestrator."""
    print("FilmAffinity → Letterboxd scraper (Optimized for List View)")
    print(f"  User ID : {user_id}\n  Language: {lang}\n  Skip TV : {skip_tv}\n  Output  : {output}")
    if debug: print("  [DEBUG mode ON]")
    print()

    warm_up_session(lang)

    # Force 'list' view to get Year and Director
    first_url = build_url(user_id, 1, lang, "list")
    print(f"[Page 1/?] {first_url}")
    soup = fetch_page(first_url)

    if soup is None:
        print("ERROR: Could not fetch page 1. Check user ID and privacy settings.", file=sys.stderr)
        sys.exit(1)

    total_pages = get_total_pages(soup)
    print(f"  Detected {total_pages} page(s).\n")

    all_entries: list[MovieEntry] = []
    
    for page in range(1, total_pages + 1):
        if page == 1:
            current_soup = soup
        else:
            url = build_url(user_id, page, lang, "list")
            print(f"[Page {page}/{total_pages}] {url}")
            current_soup = fetch_page(url)
            if current_soup is None:
                print(f"  [!] Failed to fetch page {page}. Skipping.", file=sys.stderr)
                continue

        if debug and page == 1:
            with open("debug_page_1.html", "w", encoding="utf-8") as f:
                f.write(str(current_soup))

        entries = _parse_list_view(current_soup, skip_tv)
        all_entries.extend(entries)
        print(f"  → Found {len(entries)} movies (Total: {len(all_entries)})")

        # Sleep to avoid detection
        if page < total_pages:
            time.sleep(random.uniform(2.5, 4.5))

    # Deduplicate based on title and year
    seen = set()
    unique = []
    for e in all_entries:
        key = (e.Title.lower(), e.Year)
        if key not in seen:
            seen.add(key)
            unique.append(e)
    
    write_csv(unique, output)

    print("\n" + "─" * 50)
    print("✓  Done!")
    print(f"   Movies exported   : {len(unique)}")
    print(f"   With Year/Director: {sum(1 for e in unique if e.Year)}")
    print(f"   Output file       : {output}")
    print("Next step → Upload to https://letterboxd.com/import/")

def main():
    parser = argparse.ArgumentParser(description="Export FilmAffinity ratings to Letterboxd CSV.")
    parser.add_argument("user_id", help="Numeric FilmAffinity user ID")
    parser.add_argument("--output", "-o", default="filmaffinity_export.csv", help="CSV filename")
    parser.add_argument("--lang", default="en", choices=["en", "es"], help="Site language (en is better for matching)")
    parser.add_argument("--include-tv", dest="skip_tv", action="store_false", default=True, help="Include TV shows")
    parser.add_argument("--debug", action="store_true", default=False, help="Save debug HTML")
    args = parser.parse_args()
    
    scrape(user_id=args.user_id, lang=args.lang, skip_tv=args.skip_tv, output=args.output, debug=args.debug)

if __name__ == "__main__":
    main()