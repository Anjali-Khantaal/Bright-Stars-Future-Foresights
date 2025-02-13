#!/usr/bin/env python3
import feedparser
import json
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime, timedelta, timezone

# Set how many days old articles should be
DAYS_LIMIT = 180  # Change this to adjust time range

# Keywords related to oil & gas technologies
TECHNOLOGY_KEYWORDS = [
    # General Oil & Gas Industry Terms
    "oil", "gas", "petroleum",

    # Digital Transformation & Automation
    "technology", "innovation", "AI", "machine learning", "automation",
    "robotics", "digital transformation", "IoT", "sustainability",
    "digital twin", "predictive analytics", "edge computing", "cloud computing",
    "industrial IoT", "big data analytics", "cybersecurity in oil & gas",
    "SCADA", "remote monitoring", "5G in oil & gas", "AI-driven optimization",
    "process automation", "digital oilfield", "smart sensors", "machine vision",

    # AI & Machine Learning Applications
    "AI-assisted drilling", "AI in reservoir simulation", "reinforcement learning in drilling",
    "predictive maintenance AI", "autonomous drilling", "AI-powered seismic interpretation",
    "cognitive computing in exploration", "deep learning for oilfield analytics",
    "AI-based pipeline monitoring", "LLM", "LLMs in oil and gas",

    # Robotics & Advanced Machinery
    "autonomous underwater vehicles", "remotely operated vehicles", "AI-driven inspection robots",
    "self-healing pipelines", "automated drilling rigs", "drone inspections in oil & gas",
    "smart drilling", "digital roughnecks", "robotic well intervention", "robotic refinery maintenance",

    # Energy Transition & Carbon Management
    "carbon capture", "carbon utilization", "carbon storage", "carbon sequestration",
    "direct air capture", "low-carbon hydrogen", "blue hydrogen", "green hydrogen",
    "hydrogen blending in pipelines", "carbon footprint reduction", "carbon intensity reduction",
    "methane detection", "methane emissions monitoring", "flare gas recovery",
    "renewable natural gas", "decarbonization strategies", "biofuels in oil & gas",
    "CO₂ injection", "net-zero emissions", "sustainable drilling",

    # Enhanced Oil Recovery (EOR) Technologies
    "chemical EOR", "thermal EOR", "microbial EOR", "CO₂ EOR", "nanotechnology in EOR",
    "gas injection EOR", "smart water flooding", "surfactant-polymer flooding",
    "smart tracers in EOR", "low-salinity water injection",

    # Subsurface & Seismic Innovations
    "subsurface imaging", "AI-assisted seismic processing", "fiber optic sensing",
    "seismic inversion", "distributed acoustic sensing", "4D seismic analysis",
    "electromagnetic exploration", "seismic reflection tomography", "microseismic monitoring",
    "seismic while drilling", "AI-based reservoir modeling",

    # Drilling & Well Technologies
    "drilling automation", "automated drilling control", "managed pressure drilling",
    "intelligent completions", "smart well technology", "rotary steerable systems",
    "logging while drilling", "measurement while drilling", "wellbore stability analysis",
    "digital drilling fluids", "expandable tubulars", "real-time downhole monitoring",
    "casing drilling technology", "high-temperature drilling tools",

    # Pipeline & Refinery Innovations
    "AI-driven pipeline monitoring", "smart pipeline coatings", "leak detection systems",
    "pipeline integrity management", "hydrogen pipeline transport", "pipeline pigging technology",
    "AI-based predictive pipeline maintenance", "refinery digitalization",
    "advanced catalyst development", "renewable refining technologies",

    # Offshore & Deepwater Technologies
    "subsea production systems", "floating LNG", "offshore wind integration with oil & gas",
    "deepwater drilling automation", "AI-driven FPSO monitoring", "subsea robotics",
    "autonomous underwater monitoring", "digital twin for offshore platforms",
    "subsea factory concept", "autonomous tanker loading",

    # Emerging Materials & Nanotechnology
    "nanomaterials in oil recovery", "smart drilling fluids", "self-healing materials",
    "graphene-based sensors", "smart coatings for pipelines", "high-temperature superconductors",
    "nano-enhanced lubricants", "superhydrophobic coatings for pipelines",

    # Alternative & Hybrid Energy Sources
    "gas-to-liquids", "power-to-gas", "synthetic fuels", "hybrid energy systems in oilfields",
    "enhanced geothermal systems", "hydrogen-powered drilling", "floating solar in oilfields",
    "renewable diesel", "bio-refineries in oil & gas", "AI-driven energy storage optimization",

    # Advanced Computing Technologies
    "quantum computing",

    # Top 25 Global Oil Companies
    "Saudi Aramco", "ExxonMobil", "Chevron", "Shell", "PetroChina", "TotalEnergies",
    "BP", "Sinopec", "Gazprom", "ConocoPhillips", "Rosneft", "Eni", "Equinor",
    "Phillips 66", "Valero Energy", "Marathon Petroleum", "Petrobras", "Lukoil",
    "Occidental Petroleum", "Repsol", "Devon Energy", "Hess Corporation", "OMV",
    "CNOOC", "Canadian Natural Resources"
]

def fetch_feed(feed_name, feed_url, max_entries=10):
    """Fetches feed data, filters by keywords & publication date."""
    print(f"Fetching feed: {feed_name} ({feed_url})")
    
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        print(f"Error fetching feed: {e}")
        return None

    if feed.bozo:
        print(f"Warning: Error parsing feed: {feed.bozo_exception}")

    feed_data = {
        "feed_title": feed.feed.get("title", "No title available"),
        "feed_url": feed_url,
        "entries": []
    }
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS_LIMIT)
    
    for entry in feed.entries[:max_entries]:
        title = entry.get("title", "No title")
        link = entry.get("link", "No link")
        summary = entry.get("summary", "No summary available")

        try:
            published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except (AttributeError, TypeError):
            print(f"Skipping '{title}' (Missing date)")
            continue  

        if published_date < cutoff_date:
            print(f"Skipping '{title}' (Published: {published_date}) - Too old")
            continue
        
        full_text = extract_full_text(link) if link != "No link" else "Full text unavailable"
        clean_text = f"{title} {summary} {full_text}".lower()
        clean_text = re.sub(r'\s+', ' ', clean_text)

        if any(keyword.lower() in clean_text for keyword in TECHNOLOGY_KEYWORDS):
            feed_data["entries"].append({
                "title": title,
                "link": link,
                "published_date": published_date.strftime("%Y-%m-%d %H:%M:%S"),
                "summary": summary,
                "full_text": full_text
            })
    
    return feed_data if feed_data["entries"] else None

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

def main():
    feeds = {
        "Reuters Commodities": "http://feeds.reuters.com/reuters/commoditiesNews",
        "OilPrice": "https://oilprice.com/rss",
        "Rigzone": "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
        "EIA (U.S. Energy Information Administration)": "https://www.eia.gov/rss/news.xml",
        "U.S. Department of Energy": "https://www.energy.gov/rss.xml",
        "EPA News": "https://www.epa.gov/rss/epa-news.xml",
        "Offshore Energy.biz": "https://www.offshore-energy.biz/feed/",
        "Energy Voice": "https://www.energyvoice.com/feed/",
        "DOAJ (Directory of Open Access Journals)": "https://doaj.org/feed",
        "UK Oil & Gas Authority": "https://www.ogauthority.co.uk/feed",
        "World Energy Council": "https://www.worldenergy.org/rss",
        "ABC News" : "http://feeds.abcnews.com/abcnews/usheadlines",
        "ABC News Tech" : "http://feeds.abcnews.com/abcnews/technologyheadlines",
        "CNN" : "http://rss.cnn.com/rss/cnn_topstories.rss",
        "Huffington Post" : "https://chaski.huffpost.com/us/auto/vertical/front-page",
        "NBC News" : "http://feeds.nbcnews.com/feeds/nbcpolitics",
        "Scientific American Global" : "http://rss.sciam.com/ScientificAmerican-Global",
        "NASA" : "https://www.nasa.gov/news-release/feed/",
        "The Guardian" : "https://www.theguardian.com/science/rss",
        "Phys.org" : "https://phys.org/rss-feed/",
        "WIRED" : "https://www.wired.com/feed",
        "WIRED AI" : "https://www.wired.com/feed/tag/ai/latest/rss",
        "WIRED Backchannel" : "https://www.wired.com/feed/category/backchannel/latest/rss",
        "Forbes" : "http://www.forbes.com/technology/feed/",
        "TIME" : "http://time.com/tech/feed/",
        "Tech Insider" : "http://www.techinsider.io/rss",
        "NYT: The Daily" : "https://feeds.simplecast.com/54nAGcIl",
        "Smartless" : "https://feeds.simplecast.com/hNaFxXpO",
        "NPR's Up first" : "https://feeds.npr.org/510318/podcast.xml",
        "Fox News: Science" : "https://moxie.foxnews.com/google-publisher/science.xml",
        "Fox News" : "https://moxie.foxnews.com/google-publisher/latest.xml",
        "Fox News: Tech" : "https://moxie.foxnews.com/google-publisher/tech.xml",
        "Oil and Gas IQ" : "https://www.oilandgasiq.com/rss/articles",
        "World Oil: Latest News" : "https://worldoil.com/rss?feed=news",
        "World Oil: Current Issues" : "https://worldoil.com/rss?feed=issue",
        "OGJ: General Interest" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22general-interest%22%7D",
        "OGJ Exploration and Development" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22exploration-development%22%7D",
        "OGJ: Drilling and Production" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22drilling-production%22%7D", 
        "OGJ: Refining" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22refining-processing%22%7D",
        "OGJ: Pipelines" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22pipelines-transportation%22%7D",
        "OGJ: Energy Transition" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22energy-transition%22%7D",
        "US Energy and Information Administration" : "https://www.eia.gov/rss/todayinenergy.xml",
        "Oil and Gas 360" : "https://www.oilandgas360.com/feed/",
        "Shale" : "https://shalemag.com/feed/",
        "MEES" : "https://www.mees.com/latest-issue/rss",
        "Egypt Oil and Gas" : "https://egyptoil-gas.com/news/feed/",
        "DIC Oil" : "https://dicoiltools.wordpress.com/feed/",
        "Permian Basin" : "http://pboilandgasmagazine.com/feed/",
        "Schneider" : "https://blog.se.com/oil-and-gas/feed/",
        "Oil and Gas Magazine" : "https://www.oilandgasmagazine.com.mx/feed/",
        "BOE Report" : "https://boereport.com/feed/",
        "AOG Digital" : "https://aogdigital.com/news/latest?format=feed",
        "Adrian" : "http://adrianoil.blogspot.com/feeds/posts/default?alt=rss",
        "Oil and Gas Investments" : "https://oilandgas-investments.com/feed/",
        "Yokogawa": "https://www.yokogawa.com/eu/blog/oil-gas/en/feed/",
        "Medium" : "https://medium.com/feed/deepstream-tech"
    }
    
    all_feed_data = {}
    removed_feeds = []

    for name, url in feeds.items():
        feed_data = fetch_feed(name, url)
        if feed_data:
            all_feed_data[name] = feed_data
        else:
            removed_feeds.append(name)

        print("-" * 80)
        time.sleep(2)

    print("\nFeeds removed due to no recent or relevant articles:", removed_feeds)

    # Save results to a JSON file
    with open("filtered_news.json", "w", encoding="utf-8") as f:
        json.dump(all_feed_data, f, indent=4, ensure_ascii=False)

    print("\nFiltered news saved to 'filtered_news.json'")

if __name__ == "__main__":
    main()
    