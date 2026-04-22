import argparse
import csv
import logging
import sys
from src.scraper import FilmAffinityScraper
from src.parser import FilmAffinityParser

# Setup English logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

def main():
    parser = argparse.ArgumentParser(description="Professional FilmAffinity to Letterboxd Exporter")
    parser.add_argument("user_id", help="The numeric FilmAffinity User ID")
    parser.add_argument("--output", "-o", default="filmaffinity_export.csv", help="Output CSV filename")
    parser.add_argument("--lang", default="en", choices=["en", "es"], help="Site language")
    parser.add_argument("--skip-tv", action="store_true", help="Exclude TV Series from export")
    
    args = parser.parse_args()

    scraper = FilmAffinityScraper(language=args.lang)
    all_movies = []

    print(f"\n🚀 Starting export for User ID: {args.user_id}")
    scraper.warm_up()

    # 1. Fetch First Page to get total pages
    first_page_html = scraper.get_ratings_page(args.user_id, page=1)
    if not first_page_html:
        logging.error("Could not access the first page. Check User ID or privacy settings.")
        sys.exit(1)

    first_page_parser = FilmAffinityParser(first_page_html)
    total_pages = first_page_parser.get_total_pages()
    print(f"📈 Detected {total_pages} pages of ratings.")

    # 2. Loop through all pages
    try:
        for p in range(1, total_pages + 1):
            if p == 1:
                html = first_page_html
            else:
                html = scraper.get_ratings_page(args.user_id, page=p)
            
            if html:
                page_parser = FilmAffinityParser(html)
                movies = page_parser.parse_movies(skip_tv=args.skip_tv)
                all_movies.extend(movies)
                print(f"  ✅ Page {p}/{total_pages}: Processed {len(movies)} items.")
            else:
                logging.warning(f"  ⚠️ Skipping page {p} due to connection error.")

        # 3. Export to CSV
        if all_movies:
            with open(args.output, "w", newline="", encoding="utf-8") as f:
                # We get the field names from the to_dict method of our first movie
                fieldnames = all_movies[0].to_dict().keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for movie in all_movies:
                    writer.writerow(movie.to_dict())
            
            print(f"\n✨ SUCCESS! {len(all_movies)} movies exported to '{args.output}'.")
            print("👉 You can now upload it to: https://letterboxd.com/import/\n")
        else:
            print("\n❌ No movies were found to export.")

    except KeyboardInterrupt:
        print("\n\n🛑 Process interrupted by user. Saving partial progress is not supported yet.")

if __name__ == "__main__":
    main()
