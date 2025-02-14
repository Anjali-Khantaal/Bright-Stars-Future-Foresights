import sqlite3
import streamlit as st
import subprocess
import os

# Database configuration remains the same.
DATABASE = "articles.db"
ADNOC_LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRjLmGUCFcKxiEkiIl_YMaJ1GL9iPUwIZWojQ&s"

# Predefined Categories remain unchanged.
PREDEFINED_CATEGORIES = {
    "Oil & Gas Industry": [
        "oil", "gas", "petroleum",
        "Saudi Aramco", "ExxonMobil", "Chevron", "Shell", "PetroChina", "TotalEnergies",
        "BP", "Sinopec", "Gazprom", "ConocoPhillips", "Rosneft", "Eni", "Equinor",
        "Phillips 66", "Valero Energy", "Marathon Petroleum", "Petrobras", "Lukoil",
        "Occidental Petroleum", "Repsol", "Devon Energy", "Hess Corporation", "OMV",
        "CNOOC", "Canadian Natural Resources",
        "floating LNG", "subsea production systems", "chemical EOR", "thermal EOR", 
        "microbial EOR", "gas injection EOR", "managed pressure drilling",
        "rotary steerable systems", "expandable tubulars", "high-temperature drilling tools"
    ],
    
    "Digital Transformation & Automation": [
        "technology", "innovation", "digital transformation", "IoT", "sustainability",
        "digital twin", "edge computing", "cloud computing", "industrial IoT",
        "SCADA", "remote monitoring", "5G in oil & gas", "process automation",
        "digital oilfield", "smart sensors", "quantum computing",
        "automation", "robotics", "autonomous underwater vehicles", 
        "remotely operated vehicles", "automated drilling rigs",
        "drone inspections in oil & gas", "digital roughnecks",
        "robotic well intervention", "robotic refinery maintenance",
        "drilling automation", "automated drilling control",
        "smart pipeline coatings", "leak detection systems",
        "pipeline integrity management", "pipeline pigging technology",
        "refinery digitalization", "digital drilling fluids",
        "real-time downhole monitoring", "autonomous tanker loading"
    ],
    
    "AI & Machine Learning Applications": [
        "AI", "machine learning", "machine vision", "LLM", "LLMs in oil and gas",
        "deep learning for oilfield analytics", "cognitive computing in exploration",
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

# ----------------------
# Utility DB Functions
# ----------------------
def create_table_if_not_exists():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT UNIQUE,
            snippet TEXT,
            full_text TEXT,  -- Added this column
            published_date TEXT,
            source TEXT
        )
    """)
    conn.commit()
    conn.close()

@st.cache_data
def get_articles(search_query=None, source_filter="All"):
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

@st.cache_data
def filter_articles_by_category(articles, category):
    if category == "All":
        return articles
    
    keywords = PREDEFINED_CATEGORIES.get(category, [])
    filtered = []
    for article in articles:
        title_lower = article[1].lower()
        snippet_lower = article[3].lower()
        if any(kw.lower() in (title_lower + " " + snippet_lower) for kw in keywords):
            filtered.append(article)
    return filtered

# ----------------------
# Main App Layout
# ----------------------
def main():
    st.image(ADNOC_LOGO_URL, width=150)
    st.title("Future Foresights Dashboard")
    
    # Ensure the database table exists.
    create_table_if_not_exists()
    
    # Create two tabs: one for Articles and one for Summarization.
    tabs = st.tabs(["Articles", "LLM Summarization"])
    
    with tabs[0]:
        st.header("Articles")
        
        # Sidebar (or in-page filters) for articles.
        source_filter = st.selectbox(
            "Select Source",
            ["All", "RSS", "arXiv"],
            help="Filter articles by their source"
        )
        
        category_options = ["All"] + list(PREDEFINED_CATEGORIES.keys())
        selected_category = st.selectbox("Choose a Category", category_options)
        search_query = st.text_input("Search by any keyword or partial title:", "")
        
        # Refresh button to run integrated-fetcher.py (i.e. integrated.py)
        if st.button("Refresh Articles"):
            st.info("Refreshing articles from external sources...")
            try:
                # Run integrated-fetcher.py using the conda environment 'adnoc'
                result = subprocess.run(
                    ["conda", "run", "-n", "adnoc", "python", "integrated-fetcher.py"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    st.success("Articles refreshed successfully!")
                    st.cache_data.clear()  # Clear cache so new data appears
                else:
                    st.error("Error during refresh:\n" + result.stderr)
            except Exception as e:
                st.error(f"Exception occurred: {e}")
        
        st.markdown("""
        **How to use this section:**
        1. Select a source, category, or enter search terms.
        2. Click "Refresh Articles" to pull in the latest data (runs integrated-fetcher.py).
        """)
        
        articles = get_articles(search_query, source_filter)
        articles = filter_articles_by_category(articles, selected_category)
        st.write(f"**Found {len(articles)} articles** matching your criteria:")
        
        for article in articles:
            article_id, title, link, snippet, published_date, source = article
            st.subheader(title)
            st.write(f"**Source:** {source} | **Published:** {published_date}")
            st.write(snippet + "...")
            st.markdown(f"[Read More]({link})", unsafe_allow_html=True)
            st.write("---")
    
    with tabs[1]:
        st.header("LLM Summarization")
        st.markdown("""
        Upload a PDF file (e.g., one of your filtered PDFs) and generate a summary using the LLM_Summary script.
        (Make sure your conda environment 'adnoc' is active.)
        """)
        
        # File uploader for PDF.
        pdf_file = st.file_uploader("Upload PDF", type="pdf")
        
        # Alternatively, you could use a text input to enter a local file path.
        # pdf_path_input = st.text_input("Or enter PDF file path:")
        
        if pdf_file is not None:
            # Save the uploaded file to a temporary location.
            temp_pdf_path = os.path.join("temp", pdf_file.name)
            os.makedirs("temp", exist_ok=True)
            with open(temp_pdf_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            st.success(f"Uploaded file saved as {temp_pdf_path}")
            
            if st.button("Generate Summary"):
                st.info("Generating summary... This may take a moment.")
                try:
                    # Run LLM_Summary.py with the pdf path using the 'adnoc' conda environment.
                    cmd = ["conda", "run", "-n", "adnoc", "python", "LLM_Summary.py", temp_pdf_path]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        st.success("Summary generated successfully!")
                        st.text_area("Summary", result.stdout, height=300)
                    else:
                        st.error("Error generating summary:\n" + result.stderr)
                except Exception as e:
                    st.error(f"Exception occurred: {e}")
        
        else:
            st.info("Please upload a PDF file to generate a summary.")

if __name__ == "__main__":
    main()
