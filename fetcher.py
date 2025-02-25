import feedparser
import json
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime, timedelta, timezone
import sqlite3
import subprocess
import tempfile
import geopy.geocoders
# Database configuration
DATABASE = "articles.db"
#geolocator = geopy.geocoders.Nominatim(user_agent="geo_extractor")
# ArXiv configuration
ARXIV_API_URL = (
    "http://export.arxiv.org/api/query?"
    "search_query=all:oil+AND+gas&"
    "start=0&max_results=3&"
    "sortBy=lastUpdatedDate&sortOrder=descending"
)

# Configuration from colleague's script
DAYS_LIMIT = 365
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

# RSS feed sources from colleague's script
FEEDS = {
        "Reuters Commodities": "http://feeds.reuters.com/reuters/commoditiesNews",
        "OilPrice": "https://oilprice.com/rss",
        "Rigzone": "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
        "EIA (U.S. Energy Information Administration)": "https://www.eia.gov/rss/news.xml",
        "U.S. Department of Energy": "https://www.energy.gov/rss.xml",
        "EPA News": "https://www.epa.gov/rss/epa-news.xml",
        "Offshore Energy.biz": "https://www.offshore-energy.biz/feed/",
        "Energy Voice": "https://www.energyvoice.com/feed/",
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
            relevance_score REAL,
            novelty_score TEXT,
            heat_score TEXT,
            published_date TEXT,
            source TEXT,
            full_text TEXT,
            locations TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_article(title, link, snippet, relevance_score,novelty_score, heat_score, published_date, source, full_text="", locations=""):
    """Insert an article into the database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute(
        """
        INSERT OR IGNORE INTO articles 
        (title, link, snippet, relevance_score, novelty_score, heat_score, published_date, source, full_text, locations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (title, link, snippet, relevance_score,novelty_score, heat_score, published_date, source, full_text, locations)
    )
    conn.commit()
    conn.close()


def extract_geospatial_info(text):
    """Extract country names from text using geopy."""
    locations = set()
    '''for word in text.split():
        try:
            location = geolocator.geocode(word, timeout=2)
            if location:
                locations.add(location.address.split(",")[-1].strip())
        except Exception:
            continue'''
    return list(locations)

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

def get_llm_summary(text):
    """
    Writes the scraped text to a temporary file and calls LLM_Summary.py 
    with that file as input. Returns the summary output.
    """
    # Create a temporary file (if LLM_Summary.py expects a PDF, consider saving as .pdf
    # or modify LLM_Summary.py to also support text files)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as temp_file:
        temp_file.write(text)
        temp_file_path = temp_file.name

    try:
        # Run LLM_Summary.py with the temporary file as argument.
        output = subprocess.check_output(
            ["python", "summary.py", temp_file_path],
            universal_newlines=True,
            timeout=120  # adjust timeout as needed
        )
        # Parsing the output
        output_lines = output.strip().split("\n")
        
        summary_lines = []
        novelty_text = ""
        heat_text = ""
        relevance_score = None
        collecting_summary, collecting_novelty, collecting_heat = False, False, False

        for line in output_lines:
            if line.startswith("SUMMARY:"):
                collecting_summary = True
                collecting_novelty = False
                collecting_heat = False
                summary_lines.append(line.replace("SUMMARY:", "").strip())
            elif line.startswith("RELEVANCE SCORE:"):
                collecting_summary = False
                collecting_novelty = False
                collecting_heat = False
                relevance_score = float(line.replace("RELEVANCE SCORE:", "").strip())
            elif line.startswith("NOVELTY SCORE:"):
                collecting_summary = False
                collecting_novelty = True
                collecting_heat = False
                novelty_text = line.replace("NOVELTY SCORE:", "").strip()
            elif line.startswith("HEAT SCORE:"):
                collecting_summary = False
                collecting_novelty = False
                collecting_heat = True
                heat_text = line.replace("HEAT SCORE:", "").strip()
            elif collecting_summary:
                summary_lines.append(line.strip())
            elif collecting_novelty:
                novelty_text += " " + line.strip()
            elif collecting_heat:
                heat_text += " " + line.strip()

        # Extract only the numeric scores
        novelty_score = float(re.search(r'\d+', novelty_text).group()) if re.search(r'\d+', novelty_text) else None
        heat_score = float(re.search(r'\d+', heat_text).group()) if re.search(r'\d+', heat_text) else None

        # Join extracted multi-line outputs into full text
        summary = "\n".join(summary_lines).strip()
        
        return summary, relevance_score, novelty_score, heat_score

    except Exception as e:
        return f"Error in LLM summary: {e}"
    
def article_exists(link):
    """Check if an article already exists in the database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM articles WHERE link = ?", (link,))
    result = c.fetchone()[0]
    conn.close()
    return result > 0  # Returns True if the article exists, False otherwise

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

                if article_exists(link):  # Skip if the article is already in the database
                    print(f"Skipping existing article: {title}")
                    continue
                # Instead of using the provided summary, we scrape the article.
                scraped_text = extract_full_text(link) if link != "No link" else ""
                
                published_date = ''
                location = extract_geospatial_info(scraped_text)
                # Only run LLM_Summary.py if the article contains any of the keywords.
                clean_text = f"{title} {scraped_text}".lower()
                if any(keyword.lower() in clean_text for keyword in TECHNOLOGY_KEYWORDS):
                    # Call the LLM summarizer with the scraped text.
                    llm_summary, relevance, novelity, heat_score = get_llm_summary(scraped_text)

                    insert_article(
                        title=title,
                        link=link,
                        snippet=llm_summary,  # using the LLM summary as snippet
                        relevance_score=relevance,
                        novelty_score=novelity,
                        heat_score=heat_score,
                        published_date=published_date.strftime("%Y-%m-%d %H:%M:%S") if published_date!='' else '',
                        source=name,
                        full_text=scraped_text,
                        locations=str(location)
                    )

            time.sleep(1)  # Rate limiting
            
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
                # For arXiv, we use the provided summary.
                snippet = getattr(entry, 'summary', '')
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
    while True:
        fetch_rss_feeds()
        fetch_arxiv()

if __name__ == "__main__":
    main()
