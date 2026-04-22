# FilmAffinity to Letterboxd Scraper

A Python tool designed to scrape user ratings from **FilmAffinity** and export them into a CSV format perfectly formatted for **Letterboxd** import.

## 💡 Background & Acknowledgments

This project recovers the core idea of the original [fa-scraper](https://github.com/mx-psi/fa-scraper), a tool that was widely used but unfortunately stopped working due to changes in FilmAffinity's web architecture and bot protection.

While the inspiration comes from the original tool, this script has been written **from scratch** using **"Vibe Coding"** (AI-assisted iterative development). 

Special thanks to the creators of `fa-scraper` for the original concept that served as a reference for years. This new version aims to provide a modern, functional alternative for the community.

## 🛠 Prerequisites

The script requires **Python 3.11** and a few external libraries to handle scraping and modern web protection:

1.  **tls-client**: To bypass modern anti-bot headers.
2.  **beautifulsoup4**: For parsing the HTML content.
3.  **lxml**: A fast HTML parser for BeautifulSoup.

## 📦 Choose Your Version

This repository offers two ways to run the tool:

### 1. The Unified Script (Easy Mode)
Perfect for casual users. A single `.py` file containing everything. No folders, no complexity.
- **Location**: `fa_to_letterboxd.py`
- **Usage**: Just download the file and run `python fa_to_letterboxd.py [ID]`

### 2. The Source Code (Developer Mode)
The professional, modular version of the tool. Use this if you want to run tests, contribute, or understand the logic.
- **Location**: `src/` and `tests/` folders.
- **Entry Point**: `main.py`
- **Usage**: `python main.py [ID]`

## 🔍 How to find your FilmAffinity User ID

To use this script, you need your unique numeric User ID. Follow these steps:

1.  **Log in** to your FilmAffinity account.
2.  Click on **"My Ratings"** (or "Mis votaciones") in the side menu.
3.  Look at the **URL** in your browser's address bar.
4.  Your User ID is the number at the end of the URL.

**Example:**
If your URL is `https://www.filmaffinity.com/en/userratings.php?user_id=760411`
Your User ID is: **`760411`**

> ⚠️ **Note:** Ensure your profile is set to **Public** in your account settings, otherwise the scraper will not be able to access your ratings

### Installation

Clone this repository or download the script, then install the dependencies:

```bash
pip install -r requirements.txt
```

## 🚀 Usage
To export your ratings, you need your FilmAffinity User ID. You can find it in the URL of your profile or ratings page (it is a numeric code, e.g., 760411).

Run the script from your terminal:

```bash
python3.11 fa_to_letterboxd.py [YOUR_USER_ID]
```
Options:
--output or -o: Specify a custom name for the CSV file (default: filmaffinity_export.csv).

--lang: Set the site language to en (English) or es (Spanish).

--skip-tv: Use this flag if you want to exclude TV Series and only export movies.

## Example:

```bash
python3.11 fa_to_letterboxd.py 760411 --output my_ratings.csv --lang en
```
Once the process is finished, go to Letterboxd Import and upload your CSV file.

## 💻 Tested Environment
This script has been developed and successfully tested on:

Hardware: MacBook Pro (Retina, 13-inch, Early 2015)

OS: macOS Monterey 12.5.7

Python Version: 3.11.x

Community Feedback Needed: If you are using a different operating system (Windows, Linux) or a different Python version and it works (or fails), please open an issue or notify us to update this documentation.

## 📄 License & Contributing
This project is Open Source under the MIT License.

Anyone is welcome to:

Download and use the code for personal purposes.

Fork the repository.

Open Pull Requests to improve the parsing logic, fix bugs, or add new features.

Happy watching! 🍿
