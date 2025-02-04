#!/usr/bin/env python3
import feedparser
import json

def fetch_feed(feed_name, feed_url, max_entries=5):
    """
    Fetches feed data from the given RSS feed URL.
    Returns a dictionary containing the feed title, URL, and a list of entries.
    Even if feed.bozo is True (i.e. minor XML errors), the function continues.
    """
    print(f"Fetching feed: {feed_name} ({feed_url})")
    feed = feedparser.parse(feed_url)

    # Log a warning if there are parsing issues (bozo bit is True)
    if feed.bozo:
        print(f"Warning: Error parsing feed: {feed.bozo_exception}")

    # Build the feed data dictionary.
    feed_data = {
        "feed_title": feed.feed.get("title", "No title available"),
        "feed_url": feed_url,
        "entries": []
    }

    # Loop through a limited number of entries (if available)
    for entry in feed.entries[:max_entries]:
        # Note: Some summaries may contain HTML; you can later post-process
        # them (e.g., using BeautifulSoup to extract plain text) if desired.
        entry_data = {
            "title": entry.get("title", "No title"),
            "link": entry.get("link", "No link"),
            "summary": entry.get("summary", "No summary available")
        }
        feed_data["entries"].append(entry_data)
    
    return feed_data

def main():
    # A more comprehensive dictionary of RSS feeds.
    # These feeds are chosen because they typically publish metadata
    # (titles, summaries, links) that are publicly available and permissible.
    feeds = {
        "Reuters Commodities": "http://feeds.reuters.com/reuters/commoditiesNews",
        "OilPrice": "https://oilprice.com/rss",
        "Rigzone": "https://www.rigzone.com/rss/news",
        "EIA (U.S. Energy Information Administration)": "https://www.eia.gov/rss/news.xml",
        "U.S. Department of Energy": "https://www.energy.gov/rss.xml",
        "EPA News": "https://www.epa.gov/rss/epa-news.xml",  # U.S. Environmental Protection Agency
        "Offshore Energy.biz": "https://www.offshore-energy.biz/feed/",
        "Energy Voice": "https://www.energyvoice.com/feed/",
        "DOAJ (Directory of Open Access Journals)": "https://doaj.org/feed",
        "UK Oil & Gas Authority": "https://www.ogauthority.co.uk/feed",
        "World Energy Council": "https://www.worldenergy.org/rss"  # If available on the site
    }
    
    all_feed_data = {}

    # Process each feed and collect its data
    for name, url in feeds.items():
        feed_data = fetch_feed(name, url)
        all_feed_data[name] = feed_data
        print("-" * 80)

    # Save the collected feed data into a JSON file
    json_filename = "feed_data.json"
    try:
        with open(json_filename, "w", encoding="utf-8") as json_file:
            json.dump(all_feed_data, json_file, ensure_ascii=False, indent=4)
        print(f"\nAll feed data has been saved to {json_filename}")
    except Exception as e:
        print(f"Error writing JSON file: {e}")

if __name__ == "__main__":
    main()
