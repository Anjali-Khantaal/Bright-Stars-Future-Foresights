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
from typing import Tuple, List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from collections import Counter

# Database configuration
DATABASE = "articles.db"
MAX_WORKERS = 5  # For parallel processing
REQUEST_TIMEOUT = 10
RATE_LIMIT_DELAY = 1

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

@dataclass
class Article:
    title: str
    link: str
    snippet: str
    relevance_score: float
    published_date: str
    source: str
    full_text: str = ""
    locations: str = ""
    novelty_score: float = 0.0
    heat_score: float = 0.0

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.create_articles_table()

    def create_articles_table(self) -> None:
        """Creates the articles table with new scoring columns."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    link TEXT UNIQUE,
                    snippet TEXT,
                    relevance_score REAL,
                    published_date TEXT,
                    source TEXT,
                    full_text TEXT,
                    locations TEXT,
                    novelty_score REAL DEFAULT 0,
                    heat_score REAL DEFAULT 0
                )
            """)

    def article_exists(self, link: str) -> bool:
        """Check if an article exists in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles WHERE link = ?", (link,))
            return cursor.fetchone()[0] > 0

    def insert_article(self, article: Article) -> None:
        """Insert an article into the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO articles 
                (title, link, snippet, relevance_score, published_date, source, 
                full_text, locations, novelty_score, heat_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (article.title, article.link, article.snippet, article.relevance_score,
                article.published_date, article.source, article.full_text,
                article.locations, article.novelty_score, article.heat_score)
            )

class ArticleProcessor:
    def __init__(self):
        self.db_manager = DatabaseManager(DATABASE)
        
    def calculate_novelty_score(self, text: str) -> float:
        """Calculate novelty score based on innovation indicators."""
        innovation_indicators = {
            'breakthrough': 10,
            'revolutionary': 8,
            'first-ever': 10,
            'innovative': 7,
            'novel': 6,
            'new technology': 8,
            'patent': 7,
            'prototype': 5,
            'research': 4,
            'development': 3,
            'latest': 4,
            'emerging': 5
        }
        
        text = text.lower()
        score = 0
        total_weight = 0
        
        for indicator, weight in innovation_indicators.items():
            if indicator in text:
                score += weight
                total_weight += weight
        
        # Return a plain float value
        return min(100.0, (score / max(total_weight, 1)) * 100)

    def calculate_heat_score(self, text: str, published_date: str) -> float:
        """Calculate heat score based on trending indicators and recency."""
        trending_indicators = {
            'trending': 10,
            'viral': 9,
            'popular': 7,
            'breaking': 8,
            'exclusive': 6,
            'report': 4,
            'announces': 5,
            'launches': 6
        }
        
        text = text.lower()
        base_score = 0
        total_weight = 0
        
        for indicator, weight in trending_indicators.items():
            if indicator in text:
                base_score += weight
                total_weight += weight
        
        try:
            pub_date = datetime.strptime(published_date, "%Y-%m-%d %H:%M:%S")
            days_old = (datetime.now() - pub_date).days
            recency_factor = max(0, 1 - (days_old / 30))  # Decay over 30 days
        except:
            recency_factor = 0.5
        
        # Return a plain float value
        return min(100.0, (base_score / max(total_weight, 1)) * 70 + (recency_factor * 30))

    def get_llm_summary(self, text: str) -> Tuple[str, float]:
        """Get summary using LLM model."""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as temp_file:
                temp_file.write(text)
                temp_file_path = temp_file.name

            output = subprocess.check_output(
                ["python", "summary.py", temp_file_path],
                universal_newlines=True,
                timeout=120
            )
            
            # Clean and parse the output
            parts = output.strip().split("RELEVANCE SCORE: ")
            summary = parts[0].strip()
            
            # Extract just the number from the relevance score
            relevance_str = parts[1].split()[0] if len(parts) > 1 else "0"
            relevance = float(re.findall(r"[\d.]+", relevance_str)[0])
            
            return summary, relevance
        except Exception as e:
            print(f"Error in LLM summary: {e}")
            return f"Error: {str(e)}", 0.0
        
    def extract_full_text(self, url: str) -> str:
        """Extract full text from article URL with improved error handling."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()
                
            paragraphs = soup.find_all('p')
            article_text = " ".join(p.get_text().strip() for p in paragraphs)
            return re.sub(r'\s+', ' ', article_text).strip()
        except Exception as e:
            print(f"Error extracting text from {url}: {e}")
            return ""

    def process_entry(self, entry: dict, source: str) -> Optional[Article]:
        """Process a single feed entry."""
        try:
            title = entry.get("title", "No title")
            link = entry.get("link", "")
            
            if not link or self.db_manager.article_exists(link):
                return None
                
            scraped_text = self.extract_full_text(link)
            
            try:
                published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                published_date_str = published_date.strftime("%Y-%m-%d %H:%M:%S")
            except:
                published_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            
            # Get summary and clean relevance score
            summary, relevance = self.get_llm_summary(scraped_text)
            
            # Calculate clean float scores
            novelty_score = self.calculate_novelty_score(scraped_text)
            heat_score = self.calculate_heat_score(scraped_text, published_date_str)
            
            return Article(
                title=title,
                link=link,
                snippet=summary,
                relevance_score=float(relevance),
                published_date=published_date_str,
                source=source,
                full_text=scraped_text,
                novelty_score=float(novelty_score),
                heat_score=float(heat_score)
            )
        except Exception as e:
            print(f"Error processing entry: {e}")
            return None

class FeedCollector:
    def __init__(self):
        self.processor = ArticleProcessor()
        
    def fetch_feed(self, name: str, url: str) -> None:
        """Fetch and process a single feed."""
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                print(f"Warning: Error parsing feed {name}: {feed.bozo_exception}")
                return

            for entry in feed.entries:
                article = self.processor.process_entry(entry, name)
                if article:
                    self.processor.db_manager.insert_article(article)
            
            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            print(f"Error processing feed {name}: {e}")

    def collect_feeds(self) -> None:
        """Collect feeds using thread pool."""
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for name, url in FEEDS.items():
                executor.submit(self.fetch_feed, name, url)

def main():
    collector = FeedCollector()
    print("Starting data collection...")
    while True:
        collector.collect_feeds()
        time.sleep(300)  # Wait 5 minutes between collection cycles

if __name__ == "__main__":
    main()



# import feedparser
# import json
# import requests
# from bs4 import BeautifulSoup
# import re
# import time
# from datetime import datetime, timedelta, timezone
# import sqlite3
# import subprocess
# import tempfile
# import geopy.geocoders

# # Database configuration
# DATABASE = "articles.db"

# # ArXiv configuration
# ARXIV_API_URL = (
#     "http://export.arxiv.org/api/query?"
#     "search_query=all:oil+AND+gas&"
#     "start=0&max_results=3&"
#     "sortBy=lastUpdatedDate&sortOrder=descending"
# )

# # Configuration from colleague's script
# DAYS_LIMIT = 365
# TECHNOLOGY_KEYWORDS = [
#     # General Oil & Gas Industry Terms
#     "oil", "gas", "petroleum",
 
#     # Digital Transformation & Automation
#     "technology", "innovation", "AI", "machine learning", "automation",
#     "robotics", "digital transformation", "IoT", "sustainability",
#     "digital twin", "predictive analytics", "edge computing", "cloud computing",
#     "industrial IoT", "big data analytics", "cybersecurity in oil & gas",
#     "SCADA", "remote monitoring", "5G in oil & gas", "AI-driven optimization",
#     "process automation", "digital oilfield", "smart sensors", "machine vision",

#     # AI & Machine Learning Applications
#     "AI-assisted drilling", "AI in reservoir simulation", "reinforcement learning in drilling",
#     "predictive maintenance AI", "autonomous drilling", "AI-powered seismic interpretation",
#     "cognitive computing in exploration", "deep learning for oilfield analytics",
#     "AI-based pipeline monitoring", "LLM", "LLMs in oil and gas",

#     # Robotics & Advanced Machinery
#     "autonomous underwater vehicles", "remotely operated vehicles", "AI-driven inspection robots",
#     "self-healing pipelines", "automated drilling rigs", "drone inspections in oil & gas",
#     "smart drilling", "digital roughnecks", "robotic well intervention", "robotic refinery maintenance",

#     # Energy Transition & Carbon Management
#     "carbon capture", "carbon utilization", "carbon storage", "carbon sequestration",
#     "direct air capture", "low-carbon hydrogen", "blue hydrogen", "green hydrogen",
#     "hydrogen blending in pipelines", "carbon footprint reduction", "carbon intensity reduction",
#     "methane detection", "methane emissions monitoring", "flare gas recovery",
#     "renewable natural gas", "decarbonization strategies", "biofuels in oil & gas",
#     "CO₂ injection", "net-zero emissions", "sustainable drilling",

#     # Enhanced Oil Recovery (EOR) Technologies
#     "chemical EOR", "thermal EOR", "microbial EOR", "CO₂ EOR", "nanotechnology in EOR",
#     "gas injection EOR", "smart water flooding", "surfactant-polymer flooding",
#     "smart tracers in EOR", "low-salinity water injection",

#     # Subsurface & Seismic Innovations
#     "subsurface imaging", "AI-assisted seismic processing", "fiber optic sensing",
#     "seismic inversion", "distributed acoustic sensing", "4D seismic analysis",
#     "electromagnetic exploration", "seismic reflection tomography", "microseismic monitoring",
#     "seismic while drilling", "AI-based reservoir modeling",

#     # Drilling & Well Technologies
#     "drilling automation", "automated drilling control", "managed pressure drilling",
#     "intelligent completions", "smart well technology", "rotary steerable systems",
#     "logging while drilling", "measurement while drilling", "wellbore stability analysis",
#     "digital drilling fluids", "expandable tubulars", "real-time downhole monitoring",
#     "casing drilling technology", "high-temperature drilling tools",

#     # Pipeline & Refinery Innovations
#     "AI-driven pipeline monitoring", "smart pipeline coatings", "leak detection systems",
#     "pipeline integrity management", "hydrogen pipeline transport", "pipeline pigging technology",
#     "AI-based predictive pipeline maintenance", "refinery digitalization",
#     "advanced catalyst development", "renewable refining technologies",

#     # Offshore & Deepwater Technologies
#     "subsea production systems", "floating LNG", "offshore wind integration with oil & gas",
#     "deepwater drilling automation", "AI-driven FPSO monitoring", "subsea robotics",
#     "autonomous underwater monitoring", "digital twin for offshore platforms",
#     "subsea factory concept", "autonomous tanker loading",

#     # Emerging Materials & Nanotechnology
#     "nanomaterials in oil recovery", "smart drilling fluids", "self-healing materials",
#     "graphene-based sensors", "smart coatings for pipelines", "high-temperature superconductors",
#     "nano-enhanced lubricants", "superhydrophobic coatings for pipelines",

#     # Alternative & Hybrid Energy Sources
#     "gas-to-liquids", "power-to-gas", "synthetic fuels", "hybrid energy systems in oilfields",
#     "enhanced geothermal systems", "hydrogen-powered drilling", "floating solar in oilfields",
#     "renewable diesel", "bio-refineries in oil & gas", "AI-driven energy storage optimization",

#     # Advanced Computing Technologies
#     "quantum computing",

#     # Top 25 Global Oil Companies
#     "Saudi Aramco", "ExxonMobil", "Chevron", "Shell", "PetroChina", "TotalEnergies",
#     "BP", "Sinopec", "Gazprom", "ConocoPhillips", "Rosneft", "Eni", "Equinor",
#     "Phillips 66", "Valero Energy", "Marathon Petroleum", "Petrobras", "Lukoil",
#     "Occidental Petroleum", "Repsol", "Devon Energy", "Hess Corporation", "OMV",
#     "CNOOC", "Canadian Natural Resources"
# ]

# # RSS feed sources from colleague's script
# FEEDS = {
#         "Reuters Commodities": "http://feeds.reuters.com/reuters/commoditiesNews",
#         "OilPrice": "https://oilprice.com/rss",
#         "Rigzone": "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
#         "EIA (U.S. Energy Information Administration)": "https://www.eia.gov/rss/news.xml",
#         "U.S. Department of Energy": "https://www.energy.gov/rss.xml",
#         "EPA News": "https://www.epa.gov/rss/epa-news.xml",
#         "Offshore Energy.biz": "https://www.offshore-energy.biz/feed/",
#         "Energy Voice": "https://www.energyvoice.com/feed/",
#         "DOAJ (Directory of Open Access Journals)": "https://doaj.org/feed",
#         "UK Oil & Gas Authority": "https://www.ogauthority.co.uk/feed",
#         "World Energy Council": "https://www.worldenergy.org/rss",
#         "ABC News" : "http://feeds.abcnews.com/abcnews/usheadlines",
#         "ABC News Tech" : "http://feeds.abcnews.com/abcnews/technologyheadlines",
#         "CNN" : "http://rss.cnn.com/rss/cnn_topstories.rss",
#         "Huffington Post" : "https://chaski.huffpost.com/us/auto/vertical/front-page",
#         "NBC News" : "http://feeds.nbcnews.com/feeds/nbcpolitics",
#         "Scientific American Global" : "http://rss.sciam.com/ScientificAmerican-Global",
#         "NASA" : "https://www.nasa.gov/news-release/feed/",
#         "The Guardian" : "https://www.theguardian.com/science/rss",
#         "Phys.org" : "https://phys.org/rss-feed/",
#         "WIRED" : "https://www.wired.com/feed",
#         "WIRED AI" : "https://www.wired.com/feed/tag/ai/latest/rss",
#         "WIRED Backchannel" : "https://www.wired.com/feed/category/backchannel/latest/rss",
#         "Forbes" : "http://www.forbes.com/technology/feed/",
#         "TIME" : "http://time.com/tech/feed/",
#         "Tech Insider" : "http://www.techinsider.io/rss",
#         "NYT: The Daily" : "https://feeds.simplecast.com/54nAGcIl",
#         "Smartless" : "https://feeds.simplecast.com/hNaFxXpO",
#         "NPR's Up first" : "https://feeds.npr.org/510318/podcast.xml",
#         "Fox News: Science" : "https://moxie.foxnews.com/google-publisher/science.xml",
#         "Fox News" : "https://moxie.foxnews.com/google-publisher/latest.xml",
#         "Fox News: Tech" : "https://moxie.foxnews.com/google-publisher/tech.xml",
#         "Oil and Gas IQ" : "https://www.oilandgasiq.com/rss/articles",
#         "World Oil: Latest News" : "https://worldoil.com/rss?feed=news",
#         "World Oil: Current Issues" : "https://worldoil.com/rss?feed=issue",
#         "OGJ: General Interest" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22general-interest%22%7D",
#         "OGJ Exploration and Development" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22exploration-development%22%7D",
#         "OGJ: Drilling and Production" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22drilling-production%22%7D", 
#         "OGJ: Refining" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22refining-processing%22%7D",
#         "OGJ: Pipelines" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22pipelines-transportation%22%7D",
#         "OGJ: Energy Transition" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22energy-transition%22%7D",
#         "US Energy and Information Administration" : "https://www.eia.gov/rss/todayinenergy.xml",
#         "Oil and Gas 360" : "https://www.oilandgas360.com/feed/",
#         "Shale" : "https://shalemag.com/feed/",
#         "MEES" : "https://www.mees.com/latest-issue/rss",
#         "Egypt Oil and Gas" : "https://egyptoil-gas.com/news/feed/",
#         "DIC Oil" : "https://dicoiltools.wordpress.com/feed/",
#         "Permian Basin" : "http://pboilandgasmagazine.com/feed/",
#         "Schneider" : "https://blog.se.com/oil-and-gas/feed/",
#         "Oil and Gas Magazine" : "https://www.oilandgasmagazine.com.mx/feed/",
#         "BOE Report" : "https://boereport.com/feed/",
#         "AOG Digital" : "https://aogdigital.com/news/latest?format=feed",
#         "Adrian" : "http://adrianoil.blogspot.com/feeds/posts/default?alt=rss",
#         "Oil and Gas Investments" : "https://oilandgas-investments.com/feed/",
#         "Yokogawa": "https://www.yokogawa.com/eu/blog/oil-gas/en/feed/",
#         "Medium" : "https://medium.com/feed/deepstream-tech"
#     }

# def create_articles_table():
#     """Creates the articles table if it doesn't exist."""
#     conn = sqlite3.connect(DATABASE)
#     c = conn.cursor()
#     c.execute("""
#         CREATE TABLE IF NOT EXISTS articles (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             title TEXT,
#             link TEXT UNIQUE,
#             snippet TEXT,
#             relevance_score REAL,
#             published_date TEXT,
#             source TEXT,
#             full_text TEXT,
#             locations TEXT,
#             novelty_score REAL DEFAULT 0,
#             heat_score REAL DEFAULT 0
#         )
#     """)
#     conn.commit()
#     conn.close()

# def insert_article(title, link, snippet, relevance_score, published_date, source, full_text="", locations="", novelty_score=0.0, heat_score=0.0):
#     """Insert an article into the database."""
#     conn = sqlite3.connect(DATABASE)
#     c = conn.cursor()
#     c.execute(
#         """
#         INSERT OR IGNORE INTO articles 
#         (title, link, snippet, relevance_score, published_date, source, full_text, locations, novelty_score, heat_score)
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """,
#         (title, link, snippet, relevance_score, published_date, source, full_text, locations, novelty_score, heat_score)
#     )
#     conn.commit()
#     conn.close()

# def extract_geospatial_info(text):
#     """Extract country names from text using geopy."""
#     locations = set()
#     return list(locations)

# def extract_full_text(url):
#     """Scrapes and extracts the full text of an article."""
#     try:
#         headers = {'User-Agent': 'Mozilla/5.0'}
#         response = requests.get(url, headers=headers, timeout=5)
        
#         if response.status_code != 200:
#             return "Error: Unable to fetch article"

#         soup = BeautifulSoup(response.text, 'html.parser')
#         paragraphs = soup.find_all('p')
#         article_text = "\n".join(p.get_text() for p in paragraphs)
#         return re.sub(r'\s+', ' ', article_text).strip()

#     except Exception as e:
#         return f"Error extracting text: {e}"

# def get_llm_summary(text):
#     """
#     Writes the scraped text to a temporary file and calls summary.py 
#     with that file as input. Returns the summary output and scores.
#     """
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as temp_file:
#         temp_file.write(text)
#         temp_file_path = temp_file.name

#     try:
#         # Run summary.py with the temporary file as argument.
#         output = subprocess.check_output(
#             ["python", "summary.py", temp_file_path],
#             universal_newlines=True,
#             timeout=120  # adjust timeout as needed
#         )
#         # Parse the output to extract summary and scores
#         summary = ""
#         relevance_score = 0.0
#         novelty_score = 0.0
#         heat_score = 0.0
        
#         for line in output.splitlines():
#             if line.startswith("SUMMARY:"):
#                 summary = line.replace("SUMMARY:", "").strip()
#             elif line.startswith("RELEVANCE SCORE:"):
#                 relevance_score = float(line.replace("RELEVANCE SCORE:", "").strip())
#             elif line.startswith("NOVELTY SCORE:"):
#                 novelty_score = float(line.replace("NOVELTY SCORE:", "").strip())
#             elif line.startswith("HEAT SCORE:"):
#                 heat_score = float(line.replace("HEAT SCORE:", "").strip())
        
#         return summary, relevance_score, novelty_score, heat_score
#     except Exception as e:
#         return f"Error in LLM summary: {e}", 0.0, 0.0, 0.0

# def article_exists(link):
#     """Check if an article already exists in the database."""
#     conn = sqlite3.connect(DATABASE)
#     c = conn.cursor()
#     c.execute("SELECT COUNT(*) FROM articles WHERE link = ?", (link,))
#     result = c.fetchone()[0]
#     conn.close()
#     return result > 0

# def fetch_rss_feeds():
#     """Enhanced RSS feed fetching using colleague's implementation."""
#     print("Fetching RSS feeds...")
#     cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS_LIMIT)
    
#     for name, url in FEEDS.items():
#         print(f"Fetching feed: {name} ({url})")
#         try:
#             feed = feedparser.parse(url)
            
#             if feed.bozo:
#                 print(f"Warning: Error parsing feed: {feed.bozo_exception}")
#                 continue

#             for entry in feed.entries:
#                 title = entry.get("title", "No title")
#                 link = entry.get("link", "No link")

#                 if article_exists(link):  # Skip if the article is already in the database
#                     print(f"Skipping existing article: {title}")
#                     continue

#                 scraped_text = extract_full_text(link) if link != "No link" else ""
#                 if datetime(*entry.published_parsed[:6], tzinfo=timezone.utc) and datetime(*entry.published_parsed[:6], tzinfo=timezone.utc) < cutoff_date:
#                     published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
#                 else:
#                     published_date = ''
#                 location = extract_geospatial_info(scraped_text)
#                 clean_text = f"{title} {scraped_text}".lower()
#                 if any(keyword.lower() in clean_text for keyword in TECHNOLOGY_KEYWORDS):
#                     summary, relevance, novelty, heat = get_llm_summary(scraped_text)
#                     insert_article(
#                         title=title,
#                         link=link,
#                         snippet=summary,
#                         relevance_score=relevance,
#                         published_date=published_date.strftime("%Y-%m-%d %H:%M:%S") if published_date != '' else '',
#                         source=name,
#                         full_text=scraped_text,
#                         locations=str(location),
#                         novelty_score=novelty,
#                         heat_score=heat
#                     )

#             time.sleep(1)  # Rate limiting
            
#         except Exception as e:
#             print(f"Error processing feed {name}: {e}")

# def fetch_arxiv():
#     """Fetch articles from arXiv."""
#     print("Fetching from arXiv (oil AND gas)...")
#     try:
#         response = requests.get(ARXIV_API_URL, timeout=10)
#         if response.status_code == 200:
#             feed = feedparser.parse(response.text)
            
#             for entry in feed.entries:
#                 title = entry.title if hasattr(entry, 'title') else "No Title"
#                 link = entry.link if hasattr(entry, 'link') else ""
#                 snippet = getattr(entry, 'summary', '')
#                 published_date = entry.updated if hasattr(entry, 'updated') else datetime.utcnow().isoformat()
#                 source = "arXiv"
                
#                 insert_article(
#                     title=title,
#                     link=link,
#                     snippet=snippet,
#                     published_date=published_date,
#                     source=source
#                 )
#         else:
#             print(f"ArXiv returned non-200 status code: {response.status_code}")
#     except Exception as e:
#         print(f"Error fetching data from arXiv: {e}")

# def main():
#     print("Creating database table if not exists...")
#     create_articles_table()

#     print("Starting data collection...")
#     while True:
#         fetch_rss_feeds()
#         fetch_arxiv()

# if __name__ == "__main__":
#     main()

# import feedparser
# import json
# import requests
# from bs4 import BeautifulSoup
# import re
# import time
# from datetime import datetime, timedelta, timezone
# import sqlite3
# import subprocess
# import tempfile
# from typing import Tuple, List, Dict, Optional
# from concurrent.futures import ThreadPoolExecutor
# from dataclasses import dataclass
# from collections import Counter

# # Database configuration
# DATABASE = "articles.db"
# MAX_WORKERS = 5  # For parallel processing
# REQUEST_TIMEOUT = 10
# RATE_LIMIT_DELAY = 1

# TECHNOLOGY_KEYWORDS = [
#     # General Oil & Gas Industry Terms
#     "oil", "gas", "petroleum",
 
#     # Digital Transformation & Automation
#     "technology", "innovation", "AI", "machine learning", "automation",
#     "robotics", "digital transformation", "IoT", "sustainability",
#     "digital twin", "predictive analytics", "edge computing", "cloud computing",
#     "industrial IoT", "big data analytics", "cybersecurity in oil & gas",
#     "SCADA", "remote monitoring", "5G in oil & gas", "AI-driven optimization",
#     "process automation", "digital oilfield", "smart sensors", "machine vision",

#     # AI & Machine Learning Applications
#     "AI-assisted drilling", "AI in reservoir simulation", "reinforcement learning in drilling",
#     "predictive maintenance AI", "autonomous drilling", "AI-powered seismic interpretation",
#     "cognitive computing in exploration", "deep learning for oilfield analytics",
#     "AI-based pipeline monitoring", "LLM", "LLMs in oil and gas",

#     # Robotics & Advanced Machinery
#     "autonomous underwater vehicles", "remotely operated vehicles", "AI-driven inspection robots",
#     "self-healing pipelines", "automated drilling rigs", "drone inspections in oil & gas",
#     "smart drilling", "digital roughnecks", "robotic well intervention", "robotic refinery maintenance",

#     # Energy Transition & Carbon Management
#     "carbon capture", "carbon utilization", "carbon storage", "carbon sequestration",
#     "direct air capture", "low-carbon hydrogen", "blue hydrogen", "green hydrogen",
#     "hydrogen blending in pipelines", "carbon footprint reduction", "carbon intensity reduction",
#     "methane detection", "methane emissions monitoring", "flare gas recovery",
#     "renewable natural gas", "decarbonization strategies", "biofuels in oil & gas",
#     "CO₂ injection", "net-zero emissions", "sustainable drilling",

#     # Enhanced Oil Recovery (EOR) Technologies
#     "chemical EOR", "thermal EOR", "microbial EOR", "CO₂ EOR", "nanotechnology in EOR",
#     "gas injection EOR", "smart water flooding", "surfactant-polymer flooding",
#     "smart tracers in EOR", "low-salinity water injection",

#     # Subsurface & Seismic Innovations
#     "subsurface imaging", "AI-assisted seismic processing", "fiber optic sensing",
#     "seismic inversion", "distributed acoustic sensing", "4D seismic analysis",
#     "electromagnetic exploration", "seismic reflection tomography", "microseismic monitoring",
#     "seismic while drilling", "AI-based reservoir modeling",

#     # Drilling & Well Technologies
#     "drilling automation", "automated drilling control", "managed pressure drilling",
#     "intelligent completions", "smart well technology", "rotary steerable systems",
#     "logging while drilling", "measurement while drilling", "wellbore stability analysis",
#     "digital drilling fluids", "expandable tubulars", "real-time downhole monitoring",
#     "casing drilling technology", "high-temperature drilling tools",

#     # Pipeline & Refinery Innovations
#     "AI-driven pipeline monitoring", "smart pipeline coatings", "leak detection systems",
#     "pipeline integrity management", "hydrogen pipeline transport", "pipeline pigging technology",
#     "AI-based predictive pipeline maintenance", "refinery digitalization",
#     "advanced catalyst development", "renewable refining technologies",

#     # Offshore & Deepwater Technologies
#     "subsea production systems", "floating LNG", "offshore wind integration with oil & gas",
#     "deepwater drilling automation", "AI-driven FPSO monitoring", "subsea robotics",
#     "autonomous underwater monitoring", "digital twin for offshore platforms",
#     "subsea factory concept", "autonomous tanker loading",

#     # Emerging Materials & Nanotechnology
#     "nanomaterials in oil recovery", "smart drilling fluids", "self-healing materials",
#     "graphene-based sensors", "smart coatings for pipelines", "high-temperature superconductors",
#     "nano-enhanced lubricants", "superhydrophobic coatings for pipelines",

#     # Alternative & Hybrid Energy Sources
#     "gas-to-liquids", "power-to-gas", "synthetic fuels", "hybrid energy systems in oilfields",
#     "enhanced geothermal systems", "hydrogen-powered drilling", "floating solar in oilfields",
#     "renewable diesel", "bio-refineries in oil & gas", "AI-driven energy storage optimization",

#     # Advanced Computing Technologies
#     "quantum computing",

#     # Top 25 Global Oil Companies
#     "Saudi Aramco", "ExxonMobil", "Chevron", "Shell", "PetroChina", "TotalEnergies",
#     "BP", "Sinopec", "Gazprom", "ConocoPhillips", "Rosneft", "Eni", "Equinor",
#     "Phillips 66", "Valero Energy", "Marathon Petroleum", "Petrobras", "Lukoil",
#     "Occidental Petroleum", "Repsol", "Devon Energy", "Hess Corporation", "OMV",
#     "CNOOC", "Canadian Natural Resources"
# ]

# # RSS feed sources from colleague's script
# FEEDS = {
#         "Reuters Commodities": "http://feeds.reuters.com/reuters/commoditiesNews",
#         "OilPrice": "https://oilprice.com/rss",
#         "Rigzone": "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
#         "EIA (U.S. Energy Information Administration)": "https://www.eia.gov/rss/news.xml",
#         "U.S. Department of Energy": "https://www.energy.gov/rss.xml",
#         "EPA News": "https://www.epa.gov/rss/epa-news.xml",
#         "Offshore Energy.biz": "https://www.offshore-energy.biz/feed/",
#         "Energy Voice": "https://www.energyvoice.com/feed/",
#         "DOAJ (Directory of Open Access Journals)": "https://doaj.org/feed",
#         "UK Oil & Gas Authority": "https://www.ogauthority.co.uk/feed",
#         "World Energy Council": "https://www.worldenergy.org/rss",
#         "ABC News" : "http://feeds.abcnews.com/abcnews/usheadlines",
#         "ABC News Tech" : "http://feeds.abcnews.com/abcnews/technologyheadlines",
#         "CNN" : "http://rss.cnn.com/rss/cnn_topstories.rss",
#         "Huffington Post" : "https://chaski.huffpost.com/us/auto/vertical/front-page",
#         "NBC News" : "http://feeds.nbcnews.com/feeds/nbcpolitics",
#         "Scientific American Global" : "http://rss.sciam.com/ScientificAmerican-Global",
#         "NASA" : "https://www.nasa.gov/news-release/feed/",
#         "The Guardian" : "https://www.theguardian.com/science/rss",
#         "Phys.org" : "https://phys.org/rss-feed/",
#         "WIRED" : "https://www.wired.com/feed",
#         "WIRED AI" : "https://www.wired.com/feed/tag/ai/latest/rss",
#         "WIRED Backchannel" : "https://www.wired.com/feed/category/backchannel/latest/rss",
#         "Forbes" : "http://www.forbes.com/technology/feed/",
#         "TIME" : "http://time.com/tech/feed/",
#         "Tech Insider" : "http://www.techinsider.io/rss",
#         "NYT: The Daily" : "https://feeds.simplecast.com/54nAGcIl",
#         "Smartless" : "https://feeds.simplecast.com/hNaFxXpO",
#         "NPR's Up first" : "https://feeds.npr.org/510318/podcast.xml",
#         "Fox News: Science" : "https://moxie.foxnews.com/google-publisher/science.xml",
#         "Fox News" : "https://moxie.foxnews.com/google-publisher/latest.xml",
#         "Fox News: Tech" : "https://moxie.foxnews.com/google-publisher/tech.xml",
#         "Oil and Gas IQ" : "https://www.oilandgasiq.com/rss/articles",
#         "World Oil: Latest News" : "https://worldoil.com/rss?feed=news",
#         "World Oil: Current Issues" : "https://worldoil.com/rss?feed=issue",
#         "OGJ: General Interest" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22general-interest%22%7D",
#         "OGJ Exploration and Development" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22exploration-development%22%7D",
#         "OGJ: Drilling and Production" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22drilling-production%22%7D", 
#         "OGJ: Refining" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22refining-processing%22%7D",
#         "OGJ: Pipelines" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22pipelines-transportation%22%7D",
#         "OGJ: Energy Transition" : "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22energy-transition%22%7D",
#         "US Energy and Information Administration" : "https://www.eia.gov/rss/todayinenergy.xml",
#         "Oil and Gas 360" : "https://www.oilandgas360.com/feed/",
#         "Shale" : "https://shalemag.com/feed/",
#         "MEES" : "https://www.mees.com/latest-issue/rss",
#         "Egypt Oil and Gas" : "https://egyptoil-gas.com/news/feed/",
#         "DIC Oil" : "https://dicoiltools.wordpress.com/feed/",
#         "Permian Basin" : "http://pboilandgasmagazine.com/feed/",
#         "Schneider" : "https://blog.se.com/oil-and-gas/feed/",
#         "Oil and Gas Magazine" : "https://www.oilandgasmagazine.com.mx/feed/",
#         "BOE Report" : "https://boereport.com/feed/",
#         "AOG Digital" : "https://aogdigital.com/news/latest?format=feed",
#         "Adrian" : "http://adrianoil.blogspot.com/feeds/posts/default?alt=rss",
#         "Oil and Gas Investments" : "https://oilandgas-investments.com/feed/",
#         "Yokogawa": "https://www.yokogawa.com/eu/blog/oil-gas/en/feed/",
#         "Medium" : "https://medium.com/feed/deepstream-tech"
#     }

# @dataclass
# class Article:
#     title: str
#     link: str
#     snippet: str
#     relevance_score: float
#     published_date: str
#     source: str
#     full_text: str = ""
#     locations: str = ""
#     novelty_score: float = 0.0
#     heat_score: float = 0.0

# class DatabaseManager:
#     def __init__(self, db_path: str):
#         self.db_path = db_path
#         self.create_articles_table()

#     def create_articles_table(self) -> None:
#         """Creates the articles table with new scoring columns."""
#         with sqlite3.connect(self.db_path) as conn:
#             conn.execute("""
#                 CREATE TABLE IF NOT EXISTS articles (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     title TEXT,
#                     link TEXT UNIQUE,
#                     snippet TEXT,
#                     relevance_score REAL,
#                     published_date TEXT,
#                     source TEXT,
#                     full_text TEXT,
#                     locations TEXT,
#                     novelty_score REAL DEFAULT 0,
#                     heat_score REAL DEFAULT 0
#                 )
#             """)

#     def article_exists(self, link: str) -> bool:
#         """Check if an article exists in the database."""
#         with sqlite3.connect(self.db_path) as conn:
#             cursor = conn.cursor()
#             cursor.execute("SELECT COUNT(*) FROM articles WHERE link = ?", (link,))
#             return cursor.fetchone()[0] > 0

#     def insert_article(self, article: Article) -> None:
#         """Insert an article into the database."""
#         with sqlite3.connect(self.db_path) as conn:
#             conn.execute(
#                 """
#                 INSERT OR IGNORE INTO articles 
#                 (title, link, snippet, relevance_score, published_date, source, 
#                 full_text, locations, novelty_score, heat_score)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 """,
#                 (article.title, article.link, article.snippet, article.relevance_score,
#                 article.published_date, article.source, article.full_text,
#                 article.locations, article.novelty_score, article.heat_score)
#             )

# class ArticleProcessor:
#     def __init__(self):
#         self.db_manager = DatabaseManager(DATABASE)
        
#     def calculate_novelty_score(self, text: str) -> float:
#         """Calculate novelty score based on innovation indicators."""
#         innovation_indicators = {
#             'breakthrough': 10,
#             'revolutionary': 8,
#             'first-ever': 10,
#             'innovative': 7,
#             'novel': 6,
#             'new technology': 8,
#             'patent': 7,
#             'prototype': 5,
#             'research': 4,
#             'development': 3,
#             'latest': 4,
#             'emerging': 5
#         }
        
#         text = text.lower()
#         score = 0
#         total_weight = 0
        
#         for indicator, weight in innovation_indicators.items():
#             if indicator in text:
#                 score += weight
#                 total_weight += weight
        
#         # Return a plain float value
#         return min(100.0, (score / max(total_weight, 1)) * 100)

#     def calculate_heat_score(self, text: str, published_date: str) -> float:
#         """Calculate heat score based on trending indicators and recency."""
#         trending_indicators = {
#             'trending': 10,
#             'viral': 9,
#             'popular': 7,
#             'breaking': 8,
#             'exclusive': 6,
#             'report': 4,
#             'announces': 5,
#             'launches': 6
#         }
        
#         text = text.lower()
#         base_score = 0
#         total_weight = 0
        
#         for indicator, weight in trending_indicators.items():
#             if indicator in text:
#                 base_score += weight
#                 total_weight += weight
        
#         try:
#             pub_date = datetime.strptime(published_date, "%Y-%m-%d %H:%M:%S")
#             days_old = (datetime.now() - pub_date).days
#             recency_factor = max(0, 1 - (days_old / 30))  # Decay over 30 days
#         except:
#             recency_factor = 0.5
        
#         # Return a plain float value
#         return min(100.0, (base_score / max(total_weight, 1)) * 70 + (recency_factor * 30))

#     def get_llm_summary(self, text: str) -> Tuple[str, float]:
#         """Get summary using LLM model."""
#         try:
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as temp_file:
#                 temp_file.write(text)
#                 temp_file_path = temp_file.name

#             output = subprocess.check_output(
#                 ["python", "summary.py", temp_file_path],
#                 universal_newlines=True,
#                 timeout=120
#             )
            
#             # Clean and parse the output
#             parts = output.strip().split("RELEVANCE SCORE: ")
#             summary = parts[0].strip()
            
#             # Extract just the number from the relevance score
#             relevance_str = parts[1].split()[0] if len(parts) > 1 else "0"
#             relevance = float(re.findall(r"[\d.]+", relevance_str)[0])
            
#             return summary, relevance
#         except Exception as e:
#             print(f"Error in LLM summary: {e}")
#             return f"Error: {str(e)}", 0.0
        
#     def extract_full_text(self, url: str) -> str:
#         """Extract full text from article URL with improved error handling."""
#         try:
#             headers = {'User-Agent': 'Mozilla/5.0'}
#             response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
#             response.raise_for_status()
            
#             soup = BeautifulSoup(response.text, 'html.parser')
#             # Remove script and style elements
#             for element in soup(['script', 'style']):
#                 element.decompose()
                
#             paragraphs = soup.find_all('p')
#             article_text = " ".join(p.get_text().strip() for p in paragraphs)
#             return re.sub(r'\s+', ' ', article_text).strip()
#         except Exception as e:
#             print(f"Error extracting text from {url}: {e}")
#             return ""

#     def process_entry(self, entry: dict, source: str) -> Optional[Article]:
#         """Process a single feed entry."""
#         try:
#             title = entry.get("title", "No title")
#             link = entry.get("link", "")
            
#             if not link or self.db_manager.article_exists(link):
#                 return None
                
#             scraped_text = self.extract_full_text(link)
            
#             try:
#                 published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
#                 published_date_str = published_date.strftime("%Y-%m-%d %H:%M:%S")
#             except:
#                 published_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            
#             # Get summary and clean relevance score
#             summary, relevance = self.get_llm_summary(scraped_text)
            
#             # Calculate clean float scores
#             novelty_score = self.calculate_novelty_score(scraped_text)
#             heat_score = self.calculate_heat_score(scraped_text, published_date_str)
            
#             return Article(
#                 title=title,
#                 link=link,
#                 snippet=summary,
#                 relevance_score=float(relevance),
#                 published_date=published_date_str,
#                 source=source,
#                 full_text=scraped_text,
#                 novelty_score=float(novelty_score),
#                 heat_score=float(heat_score)
#             )
#         except Exception as e:
#             print(f"Error processing entry: {e}")
#             return None

# class FeedCollector:
#     def __init__(self):
#         self.processor = ArticleProcessor()
        
#     def fetch_feed(self, name: str, url: str) -> None:
#         """Fetch and process a single feed."""
#         try:
#             feed = feedparser.parse(url)
#             if feed.bozo:
#                 print(f"Warning: Error parsing feed {name}: {feed.bozo_exception}")
#                 return

#             for entry in feed.entries:
#                 article = self.processor.process_entry(entry, name)
#                 if article:
#                     self.processor.db_manager.insert_article(article)
            
#             time.sleep(RATE_LIMIT_DELAY)
#         except Exception as e:
#             print(f"Error processing feed {name}: {e}")

#     def collect_feeds(self) -> None:
#         """Collect feeds using thread pool."""
#         with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#             for name, url in FEEDS.items():
#                 executor.submit(self.fetch_feed, name, url)

# def main():
#     collector = FeedCollector()
#     print("Starting data collection...")
#     while True:
#         collector.collect_feeds()
#         time.sleep(300)  # Wait 5 minutes between collection cycles

# if __name__ == "__main__":
#     main()

# import feedparser
# import json
# import requests
# from bs4 import BeautifulSoup
# import re
# import time
# from datetime import datetime, timedelta, timezone
# import sqlite3
# import subprocess
# import tempfile
# import geopy.geocoders

# # Database configuration
# DATABASE = "articles.db"
# # geolocator = geopy.geocoders.Nominatim(user_agent="geo_extractor")

# # ArXiv configuration
# ARXIV_API_URL = (
#     "http://export.arxiv.org/api/query?"
#     "search_query=all:oil+AND+gas&"
#     "start=0&max_results=3&"
#     "sortBy=lastUpdatedDate&sortOrder=descending"
# )

# # Configuration from colleague's script
# DAYS_LIMIT = 365
# TECHNOLOGY_KEYWORDS = [
#     # General Oil & Gas Industry Terms
#     "oil", "gas", "petroleum",
#     # Digital Transformation & Automation
#     "technology", "innovation", "AI", "machine learning", "automation",
#     "robotics", "digital transformation", "IoT", "sustainability",
#     "digital twin", "predictive analytics", "edge computing", "cloud computing",
#     "industrial IoT", "big data analytics", "cybersecurity in oil & gas",
#     "SCADA", "remote monitoring", "5G in oil & gas", "AI-driven optimization",
#     "process automation", "digital oilfield", "smart sensors", "machine vision",
#     # AI & Machine Learning Applications
#     "AI-assisted drilling", "AI in reservoir simulation", "reinforcement learning in drilling",
#     "predictive maintenance AI", "autonomous drilling", "AI-powered seismic interpretation",
#     "cognitive computing in exploration", "deep learning for oilfield analytics",
#     "AI-based pipeline monitoring", "LLM", "LLMs in oil and gas",
#     # ... (additional keywords as needed)
# ]

# # RSS feed sources from colleague's script
# FEEDS = {
#     "Reuters Commodities": "http://feeds.reuters.com/reuters/commoditiesNews",
#     "OilPrice": "https://oilprice.com/rss",
#     "Rigzone": "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
#     "EIA (U.S. Energy Information Administration)": "https://www.eia.gov/rss/news.xml",
#     "U.S. Department of Energy": "https://www.energy.gov/rss.xml",
#     "EPA News": "https://www.epa.gov/rss/epa-news.xml",
#     "Offshore Energy.biz": "https://www.offshore-energy.biz/feed/",
#     "Energy Voice": "https://www.energyvoice.com/feed/",
#     "DOAJ (Directory of Open Access Journals)": "https://doaj.org/feed",
#     "UK Oil & Gas Authority": "https://www.ogauthority.co.uk/feed",
#     "World Energy Council": "https://www.worldenergy.org/rss",
#     "ABC News": "http://feeds.abcnews.com/abcnews/usheadlines",
#     "ABC News Tech": "http://feeds.abcnews.com/abcnews/technologyheadlines",
#     "CNN": "http://rss.cnn.com/rss/cnn_topstories.rss",
#     "Huffington Post": "https://chaski.huffpost.com/us/auto/vertical/front-page",
#     "NBC News": "http://feeds.nbcnews.com/feeds/nbcpolitics",
#     "Scientific American Global": "http://rss.sciam.com/ScientificAmerican-Global",
#     "NASA": "https://www.nasa.gov/news-release/feed/",
#     "The Guardian": "https://www.theguardian.com/science/rss",
#     "Phys.org": "https://phys.org/rss-feed/",
#     "WIRED": "https://www.wired.com/feed",
#     "WIRED AI": "https://www.wired.com/feed/tag/ai/latest/rss",
#     "WIRED Backchannel": "https://www.wired.com/feed/category/backchannel/latest/rss",
#     "Forbes": "http://www.forbes.com/technology/feed/",
#     "TIME": "http://time.com/tech/feed/",
#     "Tech Insider": "http://www.techinsider.io/rss",
#     "NYT: The Daily": "https://feeds.simplecast.com/54nAGcIl",
#     "Smartless": "https://feeds.simplecast.com/hNaFxXpO",
#     "NPR's Up first": "https://feeds.npr.org/510318/podcast.xml",
#     "Fox News: Science": "https://moxie.foxnews.com/google-publisher/science.xml",
#     "Fox News": "https://moxie.foxnews.com/google-publisher/latest.xml",
#     "Fox News: Tech": "https://moxie.foxnews.com/google-publisher/tech.xml",
#     "Oil and Gas IQ": "https://www.oilandgasiq.com/rss/articles",
#     "World Oil: Latest News": "https://worldoil.com/rss?feed=news",
#     "World Oil: Current Issues": "https://worldoil.com/rss?feed=issue",
#     "OGJ: General Interest": "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22general-interest%22%7D",
#     "OGJ Exploration and Development": "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22exploration-development%22%7D",
#     "OGJ: Drilling and Production": "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22drilling-production%22%7D", 
#     "OGJ: Refining": "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22refining-processing%22%7D",
#     "OGJ: Pipelines": "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22pipelines-transportation%22%7D",
#     "OGJ: Energy Transition": "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22energy-transition%22%7D",
#     "US Energy and Information Administration": "https://www.eia.gov/rss/todayinenergy.xml",
#     "Oil and Gas 360": "https://www.oilandgas360.com/feed/",
#     "Shale": "https://shalemag.com/feed/",
#     "MEES": "https://www.mees.com/latest-issue/rss",
#     "Egypt Oil and Gas": "https://egyptoil-gas.com/news/feed/",
#     "DIC Oil": "https://dicoiltools.wordpress.com/feed/",
#     "Permian Basin": "http://pboilandgasmagazine.com/feed/",
#     "Schneider": "https://blog.se.com/oil-and-gas/feed/",
#     "Oil and Gas Magazine": "https://www.oilandgasmagazine.com.mx/feed/",
#     "BOE Report": "https://boereport.com/feed/",
#     "AOG Digital": "https://aogdigital.com/news/latest?format=feed",
#     "Adrian": "http://adrianoil.blogspot.com/feeds/posts/default?alt=rss",
#     "Oil and Gas Investments": "https://oilandgas-investments.com/feed/",
#     "Yokogawa": "https://www.yokogawa.com/eu/blog/oil-gas/en/feed/",
#     "Medium": "https://medium.com/feed/deepstream-tech"
# }

# def create_articles_table():
#     """Creates the articles table if it doesn't exist."""
#     conn = sqlite3.connect(DATABASE)
#     c = conn.cursor()
#     c.execute("""
#         CREATE TABLE IF NOT EXISTS articles (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             title TEXT,
#             link TEXT UNIQUE,
#             snippet TEXT,
#             relevance_score REAL,
#             novelty_score REAL,
#             heat_score REAL,
#             published_date TEXT,
#             source TEXT,
#             full_text TEXT,
#             locations TEXT
#         )
#     """)
#     conn.commit()
#     conn.close()

# def insert_article(title, link, snippet, relevance_score, novelty_score, heat_score, published_date, source, full_text="", locations=""):
#     """Insert an article into the database."""
#     conn = sqlite3.connect(DATABASE)
#     c = conn.cursor()
#     c.execute(
#         """
#         INSERT OR IGNORE INTO articles 
#         (title, link, snippet, relevance_score, novelty_score, heat_score, published_date, source, full_text, locations)
#         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """,
#         (title, link, snippet, relevance_score, novelty_score, heat_score, published_date, source, full_text, locations)
#     )
#     conn.commit()
#     conn.close()

# def extract_geospatial_info(text):
#     """Extract country names from text using geopy."""
#     locations = set()
#     '''
#     for word in text.split():
#         try:
#             location = geolocator.geocode(word, timeout=2)
#             if location:
#                 locations.add(location.address.split(",")[-1].strip())
#         except Exception:
#             continue
#     '''
#     return list(locations)

# def extract_full_text(url):
#     """Scrapes and extracts the full text of an article."""
#     try:
#         headers = {'User-Agent': 'Mozilla/5.0'}
#         response = requests.get(url, headers=headers, timeout=5)
#         if response.status_code != 200:
#             return "Error: Unable to fetch article"
#         soup = BeautifulSoup(response.text, 'html.parser')
#         paragraphs = soup.find_all('p')
#         article_text = "\n".join(p.get_text() for p in paragraphs)
#         return re.sub(r'\s+', ' ', article_text).strip()
#     except Exception as e:
#         return f"Error extracting text: {e}"

# def get_llm_summary(text):
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as temp_file:
#         temp_file.write(text)
#         temp_file_path = temp_file.name

#     try:
#         output = subprocess.check_output(
#             ["python", "summary.py", temp_file_path],
#             universal_newlines=True,
#             timeout=120  # adjust timeout as needed
#         )
#         # Debug: print the raw output
#         print("Raw summary script output:")
#         print(output)
        
#         # Parse the output line by line
#         summary_text = ""
#         relevance_score = 0.0
#         novelty_score = 0.0
#         heat_score = 0.0
#         for line in output.splitlines():
#             if line.startswith("SUMMARY:"):
#                 summary_text = line[len("SUMMARY:"):].strip()
#             elif line.startswith("RELEVANCE SCORE:"):
#                 try:
#                     relevance_score = float(line[len("RELEVANCE SCORE:"):].strip())
#                 except ValueError:
#                     relevance_score = 0.0
#             elif line.startswith("NOVELTY SCORE:"):
#                 try:
#                     novelty_score = float(line[len("NOVELTY SCORE:"):].strip())
#                 except ValueError:
#                     novelty_score = 0.0
#             elif line.startswith("HEAT SCORE:"):
#                 try:
#                     heat_score = float(line[len("HEAT SCORE:"):].strip())
#                 except ValueError:
#                     heat_score = 0.0
#         return summary_text, relevance_score, novelty_score, heat_score
#     except Exception as e:
#         print(f"Error in LLM summary: {e}")
#         return f"Error in LLM summary: {e}", 0.0, 0.0, 0.0


# def article_exists(link):
#     """Check if an article already exists in the database."""
#     conn = sqlite3.connect(DATABASE)
#     c = conn.cursor()
#     c.execute("SELECT COUNT(*) FROM articles WHERE link = ?", (link,))
#     result = c.fetchone()[0]
#     conn.close()
#     return result > 0

# def fetch_rss_feeds():
#     """Enhanced RSS feed fetching using colleague's implementation."""
#     print("Fetching RSS feeds...")
#     cutoff_date = datetime.now(timezone.utc) - timedelta(days=DAYS_LIMIT)
    
#     for name, url in FEEDS.items():
#         print(f"Fetching feed: {name} ({url})")
#         try:
#             feed = feedparser.parse(url)
#             if feed.bozo:
#                 print(f"Warning: Error parsing feed: {feed.bozo_exception}")
#                 continue

#             for entry in feed.entries:
#                 title = entry.get("title", "No title")
#                 link = entry.get("link", "No link")
#                 if article_exists(link):
#                     print(f"Skipping existing article: {title}")
#                     continue

#                 # Scrape the article text if available
#                 scraped_text = extract_full_text(link) if link != "No link" else ""
#                 # Determine published date based on cutoff
#                 if entry.get("published_parsed") is not None:
#                     published_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
#                     if published_dt < cutoff_date:
#                         published_date = published_dt
#                     else:
#                         published_date = ''
#                 else:
#                     published_date = ''

#                 location = extract_geospatial_info(scraped_text)
#                 clean_text = f"{title} {scraped_text}".lower()
#                 if any(keyword.lower() in clean_text for keyword in TECHNOLOGY_KEYWORDS):
#                     # Call the updated LLM summary script with the scraped text.
#                     summary, relevance, novelty, heat = get_llm_summary(scraped_text)
#                     print(f"LLM Summary for '{title}': {summary[:100]}...")  # Print a snippet for verification

#                     # Insert article with the new scores.
#                     insert_article(
#                         title=title,
#                         link=link,
#                         snippet=summary,
#                         relevance_score=relevance,
#                         novelty_score=novelty,
#                         heat_score=heat,
#                         published_date=published_date.strftime("%Y-%m-%d %H:%M:%S") if published_date != '' else '',
#                         source=name,
#                         full_text=scraped_text,
#                         locations=str(location)
#                     )

#             time.sleep(1)  # Rate limiting
            
#         except Exception as e:
#             print(f"Error processing feed {name}: {e}")

# def fetch_arxiv():
#     """Fetch articles from arXiv."""
#     print("Fetching from arXiv (oil AND gas)...")
#     try:
#         response = requests.get(ARXIV_API_URL, timeout=10)
#         if response.status_code == 200:
#             feed = feedparser.parse(response.text)
#             for entry in feed.entries:
#                 title = entry.title if hasattr(entry, 'title') else "No Title"
#                 link = entry.link if hasattr(entry, 'link') else ""
#                 snippet = getattr(entry, 'summary', '')
#                 published_date = entry.updated if hasattr(entry, 'updated') else datetime.utcnow().isoformat()
#                 source = "arXiv"
#                 # Insert arXiv article without LLM scoring
#                 insert_article(
#                     title=title,
#                     link=link,
#                     snippet=snippet,
#                     relevance_score=0.0,
#                     novelty_score=0.0,
#                     heat_score=0.0,
#                     published_date=published_date,
#                     source=source,
#                     full_text="",
#                     locations=""
#                 )
#         else:
#             print(f"ArXiv returned non-200 status code: {response.status_code}")
#     except Exception as e:
#         print(f"Error fetching data from arXiv: {e}")

# def main():
#     print("Creating database table if not exists...")
#     create_articles_table()
#     print("Starting data collection...")
#     while True:
#         fetch_rss_feeds()
#         fetch_arxiv()

# if __name__ == "__main__":
#     main()
