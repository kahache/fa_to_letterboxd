#!/usr/bin/env python3
"""
fa_to_letterboxd.py (FINAL VERSION - FIX DUPLICATES & FULL ENGLISH)
──────────────────────────────────────────────────────────────────
Scrapes FilmAffinity user ratings and exports them to a Letterboxd-compatible CSV.
Fixes: Duplicated titles and 50/50 items per page.
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

import tls_client
from bs4 import BeautifulSoup

@dataclass
class MovieEntry:
    Title: str
    Year: Optional[str]
    Directors: Optional[str]
    Rating10: Optional[str]
    WatchedDate: Optional[str]

SESSION = tls_client.Session(
    client_identifier="chrome_120",
    random_tls_extension_order=True
)

def _refresh_headers(lang: str = "en") -> None:
    SESSION.headers.update({
        "Accept-Language": f"en-US,en;q=0.9,{lang};q=0.8",
        "Referer": f"https://www.filmaffinity.com/{lang}/main.html"
    })

def warm_up_session(lang: str = "en") -> None:
    _refresh_headers(lang)
    try:
        SESSION.get(f"https://www.filmaffinity.com/{lang}/main.html", timeout_seconds=15)
        time.sleep(random.uniform(1.0, 2.0))
    except: pass

def fetch_page(url: str) -> Optional[BeautifulSoup]:
    try:
        resp = SESSION.get(url, timeout_seconds=20)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "lxml")
    except: pass
    return None

def _parse_fa_date(raw: str) -> Optional[str]:
    today = date.today()
    text = re.sub(r"^Rated\s*", "", raw, flags=re.I).strip()
    if not text: return None
    if text.lower() == "today": return today.isoformat()
    if text.lower() == "yesterday": return (today - timedelta(days=1)).isoformat()
    m = re.match(r"(\d+)\s+days?\s+ago", text, re.I)
    if m: return (today - timedelta(days=int(m.group(1)))).isoformat()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y"):
        try: return datetime.strptime(text, fmt).date().isoformat()
        except ValueError: pass
    return None

def _parse_movies(soup, skip_tv: bool) -> list[MovieEntry]:
    entries = []
    # Find all movie-cards to ensure 50/50 items
    movie_cards = soup.find_all("div", class_=re.compile(r"movie-card"))
    
    for card in movie_cards:
        # Title Fix: Specifically target the 'a' tag to avoid duplicated text from responsive hidden spans
        title_container = card.find("div", class_="mc-title")
        if not title_container: continue
        
        title_link = title_container.find("a")
        title = title_link.get_text(strip=True) if title_link else title_container.get_text(strip=True)
        
        # Optional TV Filter
        if skip_tv and any(kw in title for kw in ["(TV Series)", "Serie de TV", "Miniserie"]):
            continue
            
        # Year and Directors
        year_el = card.find("span", class_="mc-year")
        year = year_el.get_text(strip=True) if year_el else ""
            
        dir_container = card.find("div", class_="mc-director")
        director = ", ".join([d.get_text(strip=True) for d in dir_container.find_all("a")]) if dir_container else ""
            
        # Rating Fix: Look in the parent 'row' container
        rating = ""
        row_container = card.find_parent("div", class_=re.compile(r"row mb-4|row"))
        if row_container:
            rat_box = row_container.find("div", class_=re.compile(r"fa-user-rat-box"))
            if rat_box:
                m_rat = re.search(r"(\d+)", rat_box.get_text())
                if m_rat: rating = m_rat.group(1)

        # Date Fix: Look in the parent 'fa-content-card'
        watched_date = None
        parent_block = card.find_parent("div", class_="fa-content-card")
        if parent_block:
            header = parent_block.find("div", class_="card-header")
            if header:
                watched_date = _parse_fa_date(header.get_text(strip=True))

        entries.append(MovieEntry(
            Title=title, Year=year, Directors=director,
            Rating10=rating, WatchedDate=watched_date
        ))
            
    return entries

def get_total_pages(soup) -> int:
    pages = soup.find_all("a", href=re.compile(r"[?&]p=\d+"))
    if pages:
        nums = [int(re.search(r"p=(\d+)", a["href"]).group(1)) for a in pages if re.search(r"p=(\d+)", a["href"])]
        return max(nums) if nums else 1
    return 1

def main():
    parser = argparse.ArgumentParser(description="Export FilmAffinity ratings to Letterboxd.")
    parser.add_argument("user_id", help="The numeric FilmAffinity user ID.")
    parser.add_argument("--output", "-o", default="filmaffinity_export.csv", help="Output CSV filename.")
    parser.add_argument("--lang", default="en", help="Site language (en/es).")
    parser.add_argument("--skip-tv", action="store_true", help="Omit TV shows from export.")
    args = parser.parse_args()

    print(f"🎬 Exporting FilmAffinity user {args.user_id}...")
    warm_up_session(args.lang)
    
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[f.name for f in fields(MovieEntry)])
        writer.writeheader()

        base_url = f"https://www.filmaffinity.com/{args.lang}/userratings.php?user_id={args.user_id}&orderby=rating-date&chv=list"
        
        soup = fetch_page(f"{base_url}&p=1")
        if not soup:
            print("❌ Error: Could not connect to the page. Check user ID or privacy settings.")
            return

        total_pages = get_total_pages(soup)
        print(f"  Pages to process: {total_pages}")

        for p in range(1, total_pages + 1):
            if p > 1:
                soup = fetch_page(f"{base_url}&p={p}")
            
            if soup:
                movies = _parse_movies(soup, args.skip_tv)
                for m in movies:
                    writer.writerow(m.__dict__)
                print(f"  → Page {p}/{total_pages}: {len(movies)} movies saved.")
                time.sleep(random.uniform(1.0, 2.0))

    print(f"\n✅ SUCCESS! File '{args.output}' is ready.")
    print("Next step: Upload it to https://letterboxd.com/import/")

if __name__ == "__main__":
    main()