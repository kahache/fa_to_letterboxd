#!/usr/bin/env python3
"""
fa_to_letterboxd.py
───────────────────
Scrapes the public ratings of a FilmAffinity user and exports them
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

# Cambiamos a tls_client para evitar los errores de CFFI en macOS
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
# HTTP
# ──────────────────────────────────────────────────────────────────────────────

# Iniciamos sesión imitando a Chrome 120
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
    home = f"https://www.filmaffinity.com/{lang}/main.html"
    print(f"  Warming up session (visiting homepage)…")
    try:
        # tls_client usa timeout_seconds en lugar de timeout
        resp = SESSION.get(home, timeout_seconds=15)
        if resp.status_code >= 400:
             print(f"  [!] Warm-up got HTTP {resp.status_code} (continuing anyway)")
        
        delay = random.uniform(2.0, 4.0)
        print(f"  Session ready. Waiting {delay:.1f}s before scraping…")
        time.sleep(delay)
    except Exception as exc:
        print(f"  [!] Warm-up failed (continuing anyway): {exc}", file=sys.stderr)

def fetch_page(url: str, retries: int = 5) -> Optional[BeautifulSoup]:
    for attempt in range(1, retries + 1):
        try:
            time.sleep(random.uniform(0.3, 0.8))
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
# Resto de la lógica (Constants, Parsers, CSV, etc. sin cambios)
# ──────────────────────────────────────────────────────────────────────────────

_YEAR_RE = re.compile(r"\((\d{4})\)")
_TV_KEYWORDS = (
    "(TV Series)", "(TV Mini-Series)", "(TV Movie)", "(TV Episode)",
    "(Short TV Series)", "Serie de TV", "Miniserie de TV",
    "Película de TV", "Episodio",
)

def _is_tv(text: str) -> bool:
    return any(kw.lower() in text.lower() for kw in _TV_KEYWORDS)

def _parse_fa_date(raw: str) -> Optional[str]:
    today = date.today()
    text = re.sub(r"^Rated\s*", "", raw, flags=re.I).strip()
    if not text: return None
    if text.lower() == "today": return today.isoformat()
    if text.lower() == "yesterday": return (today - timedelta(days=1)).isoformat()
    m = re.match(r"(\d+)\s+days?\s+ago", text, re.I)
    if m: return (today - timedelta(days=int(m.group(1)))).isoformat()
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
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

def _parse_grid(soup, skip_tv: bool) -> list[MovieEntry]:
    entries = []
    cards = [c for c in soup.find_all("div", class_="card") if "h-100" in c.get("class", [])]
    for card in cards:
        link = card.find("a", class_="card-body") or card.find("a", href=re.compile(r"/film\d+\.html"))
        if not link: continue
        title = (link.get("title") or link.get_text(strip=True)).strip()
        if not title or (skip_tv and _is_tv(title)): continue
        rat_div = card.find("div", class_="avgrat-box")
        rating = rat_div.get_text(strip=True) if rat_div else None
        if rating and not (rating.isdigit() and 1 <= int(rating) <= 10): rating = None
        small = card.find("small")
        watched_date = _parse_fa_date(small.get_text(strip=True)) if small else None
        entries.append(MovieEntry(Title=title, Year=None, Directors=None, Rating10=rating, WatchedDate=watched_date))
    return entries

def _parse_list(soup, skip_tv: bool) -> list[MovieEntry]:
    entries = []
    rows = soup.find_all("div", class_=re.compile(r"user-ratings-row|rat-row|fa-user-rat-row"))
    if not rows:
        rows = soup.find_all(class_="mc-title")
        if rows: rows = [r.find_parent("div") for r in rows if r.find_parent("div")]
    for row in rows:
        title_link = row.find("a", href=re.compile(r"/film\d+\.html"))
        if not title_link: continue
        title = title_link.get_text(strip=True)
        row_text = row.get_text(" ", strip=True)
        if not title or (skip_tv and _is_tv(row_text)): continue
        m = _YEAR_RE.search(row_text)
        year = m.group(1) if m else None
        dir_links = row.find_all("a", href=re.compile(r"stype=director|/director\.php"))
        directors = ", ".join(a.get_text(strip=True) for a in dir_links) or None
        rat_div = row.find("div", class_="avgrat-box")
        rating = rat_div.get_text(strip=True) if rat_div else None
        if rating and not (rating.isdigit() and 1 <= int(rating) <= 10): rating = None
        small = row.find("small")
        watched_date = _parse_fa_date(small.get_text(strip=True)) if small else None
        entries.append(MovieEntry(Title=title, Year=year, Directors=directors, Rating10=rating, WatchedDate=watched_date))
    return entries

def parse_page(soup, skip_tv: bool) -> list[MovieEntry]:
    entries = _parse_list(soup, skip_tv)
    return entries if entries else _parse_grid(soup, skip_tv)

def get_total_pages(soup) -> int:
    for cls in ("tit-count-ratings", "count-ratings", "user-ratings-header", "header-count", "count"):
        el = soup.find(class_=cls)
        if el:
            nums = re.findall(r"\d+", el.get_text())
            if nums: return max(1, (int(nums[0]) + 49) // 50)
    page_nums = [int(m.group(1)) for a in soup.find_all("a", href=re.compile(r"[?&]p=\d+")) if (m := re.search(r"[?&]p=(\d+)", a["href"]))]
    if page_nums: return max(page_nums)
    cards = [c for c in soup.find_all("div", class_="card") if "h-100" in c.get("class", [])]
    return 999 if len(cards) == 50 else 1

def build_url(user_id: str, page: int, lang: str, view: str = "grid") -> str:
    params = urlencode({"user_id": user_id, "p": page, "orderby": "rating-date", "chv": view})
    return f"https://www.filmaffinity.com/{lang}/userratings.php?{params}"

def write_csv(entries: list[MovieEntry], output_path: str) -> None:
    col_names = [f.name for f in fields(MovieEntry)]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=col_names, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for e in entries:
            writer.writerow({"Title": e.Title, "Year": e.Year or "", "Directors": e.Directors or "", "Rating10": e.Rating10 or "", "WatchedDate": e.WatchedDate or ""})

def dump_debug(soup, page: int) -> None:
    fname = f"fa_debug_page{page}.html"
    with open(fname, "w", encoding="utf-8") as f: f.write(str(soup))
    print(f"  [DEBUG] HTML saved → {fname}")
    cards = [c for c in soup.find_all("div", class_="card") if "h-100" in c.get("class", [])]
    print(f"  [DEBUG] div.card.h-100 found: {len(cards)}")

def scrape(user_id: str, lang: str, skip_tv: bool, output: str, debug: bool = False) -> None:
    print("FilmAffinity → Letterboxd scraper (Powered by tls_client)")
    print(f"  User ID : {user_id}\n  Language: {lang}\n  Skip TV : {skip_tv}\n  Output  : {output}")
    if debug: print("  [DEBUG mode ON]")
    print()

    warm_up_session(lang)

    first_url = build_url(user_id, 1, lang, "grid")
    print(f"[1/?] {first_url}")
    soup = fetch_page(first_url)

    if soup is None:
        print("ERROR: Could not fetch page 1. Check the user ID and make sure the profile is public.", file=sys.stderr)
        sys.exit(1)

    total_pages = get_total_pages(soup)
    known_total = total_pages != 999
    display_total = str(total_pages) if known_total else "?"
    print(f"  Detected {display_total} page(s).\n")

    all_entries: list[MovieEntry] = []
    page = 1
    
    while True:
        if page == 1:
            current_soup = soup
        else:
            url = build_url(user_id, page, lang, "grid")
            print(f"[{page}/{display_total}] {url}")
            current_soup = fetch_page(url)
            if current_soup is None:
                print(f"  [!] Skipping page {page}.", file=sys.stderr)
                page += 1
                continue

        if debug and page <= 2: dump_debug(current_soup, page)

        entries = parse_page(current_soup, skip_tv)

        if not entries:
            if page > 1:
                print(f"  → 0 entries on page {page}, stopping pagination.")
                break
            if not debug:
                print(f"  [!] 0 entries on page 1 — re-run with --debug", file=sys.stderr)

        all_entries.extend(entries)
        print(f"  → {len(entries)} entries (total: {len(all_entries)})")

        if known_total and page >= total_pages: break
        if not known_total and len(entries) < 50: break

        page += 1
        time.sleep(random.uniform(3.0, 6.0))

    seen: set[tuple] = set()
    unique: list[MovieEntry] = []
    for e in all_entries:
        key = (e.Title.lower(), e.Year)
        if key not in seen:
            seen.add(key)
            unique.append(e)
    dupes = len(all_entries) - len(unique)

    write_csv(unique, output)

    print()
    print("─" * 50)
    print("✓  Done!")
    print(f"   Entries exported  : {len(unique)}")
    print(f"   With rating       : {sum(1 for e in unique if e.Rating10)}")
    print(f"   With watch date   : {sum(1 for e in unique if e.WatchedDate)}")
    print(f"   With year         : {sum(1 for e in unique if e.Year)}")
    if dupes: print(f"   Duplicates removed: {dupes}")
    print(f"   Output            : {output}\n\nNext → https://letterboxd.com/import/")

def main():
    parser = argparse.ArgumentParser(description="Export FilmAffinity user ratings to a Letterboxd-compatible CSV.", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("user_id", help="Your numeric FilmAffinity user ID")
    parser.add_argument("--output", "-o", default="filmaffinity_export.csv", help="Output CSV file name")
    parser.add_argument("--lang", default="en", choices=["en", "es"], help="FA language version")
    parser.add_argument("--include-tv", dest="skip_tv", action="store_false", default=True, help="Include TV series")
    parser.add_argument("--debug", action="store_true", default=False, help="Save raw HTML")
    args = parser.parse_args()
    scrape(user_id=args.user_id, lang=args.lang, skip_tv=args.skip_tv, output=args.output, debug=args.debug)

if __name__ == "__main__":
    main()