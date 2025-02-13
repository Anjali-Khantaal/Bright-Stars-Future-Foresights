import feedparser
import json
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime, timedelta, timezone
import sqlite3

# Database configuration
DATABASE = "articles.db"

# ArXiv configuration
ARXIV_API_URL = (
    "http://export.arxiv.org/api/query?"
    "search_query=all:oil+AND+gas&"
    "start=0&max_results=3&"
    "sortBy=lastUpdatedDate&sortOrder=descending"
)

# Configuration from colleague's script
DAYS_LIMIT = 180
TECHNOLOGY_KEYWORDS = [
    "oil", "gas", "petroleum",
    "technology", "innovation", "AI", "machine learning", "automation",
    # ... (rest of the keywords)
]

# RSS feed sources from colleague's script
FEEDS = {
    "Reuters Commodities": "http://feeds.reuters.com/reuters/commoditiesNews",
    "OilPrice": "https://oilprice.com/rss",
    "U.S. Department of Energy": "https://www.energy.gov/rss.xml",
    "EPA News": "https://www.epa.gov/rss/epa-news.xml",
    "Offshore Energy.biz": "https://www.offshore-energy.biz/feed/",
    "Energy Voice": "https://www.energyvoice.com/feed/",
    "DOAJ (Directory of Open Access Journals)": "https://doaj.org/feed",
    "UK Oil & Gas Authority": "https://www.ogauthority.co.uk/feed"
    # ... (rest of the feeds)
}

def create_articles_table():
    """Creates the articles table if it doesn't exist."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT UNIQUE,
            snippet TEXT,
            published_date TEXT,
            source TEXT,
            full_text TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_article(title, link, snippet, published_date, source, full_text=""):
    """Insert an article into the database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        """
        INSERT OR IGNORE INTO articles 
        (title, link, snippet, published_date, source, full_text)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, link, snippet, published_date, source, full_text)
    )
    conn.commit()
    conn.close()

def extract_full_text(url):
    """Scrapes and extracts the full text of an article."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return "Error: Unable to fetch article"

        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        article_text = "\n".join(p.get_text() for p in paragraphs)
        return re.sub(r'\s+', ' ', article_text).strip()

    except Exception as e:
        return f"Error extracting text: {e}"

def fetch_rss_feeds():
    """Enhanced RSS feed fetching using colleague's implementation."""
    print("Fetching RSS feeds...")
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS_LIMIT)
    
    for name, url in FEEDS.items():
        print(f"Fetching feed: {name} ({url})")
        try:
            feed = feedparser.parse(url)
            
            if feed.bozo:
                print(f"Warning: Error parsing feed: {feed.bozo_exception}")
                continue

            for entry in feed.entries:
                title = entry.get("title", "No title")
                link = entry.get("link", "No link")
                summary = entry.get("summary", "No summary available")

                try:
                    published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except (AttributeError, TypeError):
                    print(f"Skipping '{title}' (Missing date)")
                    continue

                if published_date < cutoff_date:
                    continue

                full_text = extract_full_text(link) if link != "No link" else ""
                clean_text = f"{title} {summary} {full_text}".lower()
                
                if any(keyword.lower() in clean_text for keyword in TECHNOLOGY_KEYWORDS):
                    insert_article(
                        title=title,
                        link=link,
                        snippet=summary[:300],
                        published_date=published_date.strftime("%Y-%m-%d %H:%M:%S"),
                        source=name,
                        full_text=full_text
                    )

            time.sleep(2)  # Rate limiting
            
        except Exception as e:
            print(f"Error processing feed {name}: {e}")

def fetch_arxiv():
    """Fetch articles from arXiv."""
    print("Fetching from arXiv (oil AND gas)...")
    try:
        response = requests.get(ARXIV_API_URL, timeout=10)
        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            
            for entry in feed.entries:
                title = entry.title if hasattr(entry, 'title') else "No Title"
                link = entry.link if hasattr(entry, 'link') else ""
                snippet = getattr(entry, 'summary', '')[:300]
                published_date = entry.updated if hasattr(entry, 'updated') else datetime.utcnow().isoformat()
                source = "arXiv"
                
                insert_article(
                    title=title,
                    link=link,
                    snippet=snippet,
                    published_date=published_date,
                    source=source
                )
        else:
            print(f"ArXiv returned non-200 status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching data from arXiv: {e}")

def main():
    print("Creating database table if not exists...")
    create_articles_table()

    print("Starting data collection...")
    fetch_rss_feeds()
    fetch_arxiv()
    
    print("Data collection complete. Run 'streamlit run dashboard_app.py' to view the dashboard.")

if __name__ == "__main__":
    main()
