import feedparser
import requests
import sqlite3
from datetime import datetime


# CONFIGURATION
DATABASE = "articles.db"

# Some public RSS feeds for testing (oil & gas news)
RSS_FEEDS = [
    "https://www.rigzone.com/rss/news/",          # Rigzone
    "https://feeds.marketwatch.com/marketwatch/energy",  # MarketWatch Energy
]

# ArXiv query for "oil AND gas"
ARXIV_API_URL = (
    "http://export.arxiv.org/api/query?"
    "search_query=all:oil+AND+gas&"
    "start=0&max_results=3&"  # limiting to 3 results for demo
    "sortBy=lastUpdatedDate&sortOrder=descending"
)


# DATABASE SETUP
def create_articles_table():
    """
    Creates the 'articles' table in 'articles.db' if it does not exist.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT UNIQUE,
            snippet TEXT,
            published_date TEXT,
            source TEXT
        )
        """
    )
    conn.commit()
    conn.close()

def insert_article(title, link, snippet, published_date, source):
    """
    Insert a single article into the database.
    Uses 'INSERT OR IGNORE' to avoid duplicates by link.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        """
        INSERT OR IGNORE INTO articles (title, link, snippet, published_date, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title, link, snippet, published_date, source)
    )
    conn.commit()
    conn.close()


# FETCH FUNCTIONS
def fetch_rss_feeds():
    """
    Fetch articles from a list of RSS feeds and store them in the DB.
    """
    print("Fetching RSS feeds...")
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = entry.title if hasattr(entry, 'title') else "No Title"
                link = entry.link if hasattr(entry, 'link') else ""
                snippet = getattr(entry, 'summary', '')[:300]  # first 300 chars
                published_date = getattr(entry, 'published', datetime.utcnow().isoformat())
                source = feed_url
                insert_article(title, link, snippet, published_date, source)
        except Exception as e:
            print(f"Error fetching or parsing feed {feed_url}: {e}")

def fetch_arxiv():
    """
    Fetch articles from arXiv (ATOM feed) using a query for 'oil AND gas'.
    """
    print("Fetching from arXiv (oil AND gas)...")
    try:
        response = requests.get(ARXIV_API_URL, timeout=10)
        if response.status_code == 200:
            data = response.text
            # Use feedparser for consistency
            feed = feedparser.parse(data)
            for entry in feed.entries:
                title = entry.title if hasattr(entry, 'title') else "No Title"
                link = entry.link if hasattr(entry, 'link') else ""
                snippet = getattr(entry, 'summary', '')[:300]
                published_date = entry.updated if hasattr(entry, 'updated') else datetime.utcnow().isoformat()
                source = "arXiv"
                insert_article(title, link, snippet, published_date, source)
        else:
            print(f"ArXiv returned non-200 status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching data from arXiv: {e}")


# MAIN EXECUTION
if __name__ == "__main__":
    print("Creating table if not exists...")
    create_articles_table()

    print("Fetching data...")
    fetch_rss_feeds()
    fetch_arxiv()

    print("Data fetching complete. Run 'streamlit run dashboard_app.py' to see the dashboard.")
