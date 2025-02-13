import sqlite3
import streamlit as st
import subprocess  # Only if you want to attempt calling fetch_data.py from Python

# We will use st.cache_data (Streamlit 1.18+) or st.cache for older versions to cache data.
# This helps speed up repeated queries or filters.

DATABASE = "articles.db"

# ADNOC Logo (public link). Replace if needed.
ADNOC_LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRjLmGUCFcKxiEkiIl_YMaJ1GL9iPUwIZWojQ&s"

# Define some initial categories and the keywords we want to match.
# You can expand this in the future.

PREDEFINED_CATEGORIES = {
    "Oil & Gas Industry": [
        # Basic terms
        "oil", "gas", "petroleum",
        # Company names
        "Saudi Aramco", "ExxonMobil", "Chevron", "Shell", "PetroChina", "TotalEnergies",
        "BP", "Sinopec", "Gazprom", "ConocoPhillips", "Rosneft", "Eni", "Equinor",
        "Phillips 66", "Valero Energy", "Marathon Petroleum", "Petrobras", "Lukoil",
        "Occidental Petroleum", "Repsol", "Devon Energy", "Hess Corporation", "OMV",
        "CNOOC", "Canadian Natural Resources",
        # Traditional operations
        "floating LNG", "subsea production systems", "chemical EOR", "thermal EOR", 
        "microbial EOR", "gas injection EOR", "managed pressure drilling",
        "rotary steerable systems", "expandable tubulars", "high-temperature drilling tools"
    ],
    
    "Digital Transformation & Automation": [
        # Digital technologies
        "technology", "innovation", "digital transformation", "IoT", "sustainability",
        "digital twin", "edge computing", "cloud computing", "industrial IoT",
        "SCADA", "remote monitoring", "5G in oil & gas", "process automation",
        "digital oilfield", "smart sensors", "quantum computing",
        # Automation systems
        "automation", "robotics", "autonomous underwater vehicles", 
        "remotely operated vehicles", "automated drilling rigs",
        "drone inspections in oil & gas", "digital roughnecks",
        "robotic well intervention", "robotic refinery maintenance",
        "drilling automation", "automated drilling control",
        # Monitoring and control
        "smart pipeline coatings", "leak detection systems",
        "pipeline integrity management", "pipeline pigging technology",
        "refinery digitalization", "digital drilling fluids",
        "real-time downhole monitoring", "autonomous tanker loading"
    ],
    
    "AI & Machine Learning Applications": [
        # Core AI
        "AI", "machine learning", "machine vision", "LLM", "LLMs in oil and gas",
        "deep learning for oilfield analytics", "cognitive computing in exploration",
        # AI applications
        "AI-driven optimization", "predictive analytics", "big data analytics",
        "AI-assisted drilling", "AI in reservoir simulation",
        "reinforcement learning in drilling", "predictive maintenance AI",
        "autonomous drilling", "AI-powered seismic interpretation",
        "AI-based pipeline monitoring", "AI-driven inspection robots",
        "AI-assisted seismic processing", "AI-based reservoir modeling",
        "AI-driven FPSO monitoring", "AI-based predictive pipeline maintenance",
        "AI-driven energy storage optimization"
    ],
    
    "Sustainability & Energy Transition": [
        "carbon capture", "carbon utilization", "carbon storage", "carbon sequestration",
        "direct air capture", "low-carbon hydrogen", "blue hydrogen", "green hydrogen",
        "hydrogen blending in pipelines", "carbon footprint reduction",
        "carbon intensity reduction", "methane detection", "methane emissions monitoring",
        "flare gas recovery", "renewable natural gas", "decarbonization strategies",
        "biofuels in oil & gas", "CO₂ injection", "net-zero emissions",
        "sustainable drilling", "renewable refining technologies",
        "offshore wind integration with oil & gas", "gas-to-liquids",
        "power-to-gas", "synthetic fuels", "hybrid energy systems in oilfields",
        "enhanced geothermal systems", "hydrogen-powered drilling",
        "floating solar in oilfields", "renewable diesel", "bio-refineries in oil & gas"
    ],
    
    "Advanced Materials & Sensing": [
        "nanomaterials in oil recovery", "smart drilling fluids",
        "self-healing materials", "graphene-based sensors",
        "high-temperature superconductors", "nano-enhanced lubricants",
        "superhydrophobic coatings for pipelines", "fiber optic sensing",
        "distributed acoustic sensing", "smart well technology",
        "logging while drilling", "measurement while drilling",
        "self-healing pipelines", "advanced catalyst development"
    ],
    
    "Subsurface & Seismic Technologies": [
        "subsurface imaging", "seismic inversion", "4D seismic analysis",
        "electromagnetic exploration", "seismic reflection tomography",
        "microseismic monitoring", "seismic while drilling",
        "wellbore stability analysis", "intelligent completions",
        "smart water flooding", "surfactant-polymer flooding",
        "smart tracers in EOR", "low-salinity water injection"
    ]
}

def create_table_if_not_exists():
    """
    Create the SQLite table if it doesn't exist yet.
    This prevents errors if the user hasn't run fetch_data.py yet.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT UNIQUE,
            snippet TEXT,
            published_date TEXT,
            source TEXT
        )
    """)
    conn.commit()
    conn.close()

@st.cache_data  # Cache results to speed up repeated queries
def get_articles(search_query=None, source_filter="All"):
    """
    Retrieves articles from the database.
    If a search_query is provided, it does a basic LIKE match on the title/snippet fields.
    If source_filter is provided, it filters by the source.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    query_conditions = []
    query_params = []
    
    if search_query:
        query_conditions.append("(title LIKE ? OR snippet LIKE ?)")
        like_query = f"%{search_query}%"
        query_params.extend([like_query, like_query])
    
    if source_filter != "All":
        if source_filter == "RSS":
            query_conditions.append("source != 'arXiv'")
        elif source_filter == "arXiv":
            query_conditions.append("source = 'arXiv'")
    
    base_query = """
        SELECT id, title, link, snippet, published_date, source
        FROM articles
    """
    
    if query_conditions:
        base_query += " WHERE " + " AND ".join(query_conditions)
    
    base_query += " ORDER BY published_date DESC"
    
    c.execute(base_query, query_params)
    rows = c.fetchall()
    conn.close()
    return rows

@st.cache_data  # Also cache the filtering step
def filter_articles_by_category(articles, category):
    """
    Filters the articles list by checking if any of the defined
    keywords for `category` appear in the title or snippet.
    If category is 'All', returns the entire list.
    """
    if category == "All":
        return articles
    
    keywords = PREDEFINED_CATEGORIES.get(category, [])
    filtered = []

    for article in articles:
        # article format: (id, title, link, snippet, published_date, source)
        title_lower = article[1].lower()
        snippet_lower = article[3].lower()
        
        # If any keyword is found in title or snippet, keep the article
        if any(kw.lower() in (title_lower + " " + snippet_lower) for kw in keywords):
            filtered.append(article)
    return filtered

def main():
    # Ensure the database and table exist before we do anything else
    create_table_if_not_exists()

    # ---------------
    # SESSION SETUP
    # ---------------
    # We'll use a session state variable "home_mode" to track if user is at "Home" (no articles shown).
    if "home_mode" not in st.session_state:
        st.session_state["home_mode"] = True  # Start on home by default

    # ---------------
    # LOGO & TITLE
    # ---------------
    # Display the ADNOC logo at the top to brand the dashboard
    st.image(ADNOC_LOGO_URL, width=150)  # Adjust width if desired
    st.title("Future Foresights Dashboard")

    # ---------------
    # SIDEBAR
    # ---------------
    st.sidebar.header("Navigation & Filters")

    # Home button to reset view
    if st.sidebar.button("Home"):
        # Reset to home mode
        st.session_state["home_mode"] = True

    # Button to fetch new data
    if st.sidebar.button("Fetch Latest Articles"):
        st.sidebar.write("Attempting to fetch data from external sources...")
        # Clear the cache so new data is reflected immediately
        st.cache_data.clear()

        try:
            result = subprocess.run(
                ["python", "integrated-fetcher.py"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                st.sidebar.success("Data fetched successfully! Reload the page or navigate to see the latest articles.")
            else:
                st.sidebar.error(f"An error occurred while fetching data:\n{result.stderr}")
        except FileNotFoundError:
            st.sidebar.error("Could not find or run integrated-fetcher.py. Please run it manually.")
        st.sidebar.info("In production, this step can be automated or run on a schedule.")

    # Source filter
    source_filter = st.sidebar.radio(
        "Select Source",
        ["All", "RSS", "arXiv"],
        help="Filter articles by their source"
    )

    # Predefined categories
    category_options = ["All"] + list(PREDEFINED_CATEGORIES.keys())
    selected_category = st.sidebar.selectbox("Choose a Category", category_options)

    # Search bar
    search_query = st.sidebar.text_input("Search by any keyword or partial title:", "")

    # ---------------
    # MAIN PAGE LOGIC
    # ---------------
    # If user selects a category, source, or enters a query, switch off home mode
    if selected_category != "All" or search_query or source_filter != "All":
        st.session_state["home_mode"] = False

    if st.session_state["home_mode"]:
        # Show welcome message instead of article results
        st.markdown("""
        ### Welcome to the Future Foresights Dashboard
        - **Click "Fetch Latest Articles"** (in the sidebar) to update the database with new items.
        - **Use the filters** in the sidebar to explore relevant articles:
          - Select source (RSS or arXiv)
          - Choose a category
          - Enter search terms
        """)
        # Stop execution to avoid showing articles
        st.stop()

    # If we're not in home mode, show instructions and articles
    st.markdown("""
    **How to use this dashboard**:
    1. **Select a Source** (in the sidebar) to filter between RSS and arXiv articles.
    2. **Select a Category** for a quick filter, e.g., "AI & Machine Learning Applications".
    3. **Enter a search query** for partial matches in the title or snippet.
    4. **Fetch Latest Articles** to refresh the database with new feeds.
    """)

    # Retrieve & filter data
    articles = get_articles(search_query, source_filter)
    articles = filter_articles_by_category(articles, selected_category)

    st.write(f"**Found {len(articles)} articles** matching your criteria:")

    # Display each article
    for article in articles:
        article_id, title, link, snippet, published_date, source = article
        
        st.subheader(title)
        st.write(f"**Source**: {source}")
        st.write(f"**Published**: {published_date}")
        st.write(snippet + "...")
        st.markdown(f"[Read More]({link})", unsafe_allow_html=True)
        st.write("---")

    # ---------------
    # FOOTER
    # ---------------
    st.markdown("### Future Enhancements")
    st.markdown("""
    - **Integration with Classification**:  
      Once you have classification logic (e.g., ML model), store the classification result 
      in the `articles` table (new column, e.g., `classification`). Then, add a new filter 
      or auto-match articles to these categories.
    - **Sentiment Analysis**:  
      Similar approach – store a sentiment score in the DB and allow filtering or sorting by it.
    - **Alerts & Emails**:  
      Automate daily/weekly emails or notifications for newly ingested articles.
    """)

if __name__ == "__main__":
    main()
