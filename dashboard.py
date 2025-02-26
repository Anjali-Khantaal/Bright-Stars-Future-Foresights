import sqlite3
import streamlit as st
import subprocess
import os
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import re
import pycountry

# ----------------------
# GLOBALS
# ----------------------
DATABASE = "articles.db"
ADNOC_LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRjLmGUCFcKxiEkiIl_YMaJ1GL9iPUwIZWojQ&s"

PREDEFINED_CATEGORIES = {
    "Oil & Gas Industry": ["oil", "gas", "petroleum"],
    "Digital Transformation & Automation": ["technology", "innovation", "digital transformation"],
    "AI & Machine Learning Applications": ["AI", "machine learning", "big data analytics"],
    "Sustainability & Energy Transition": ["carbon capture", "hydrogen", "renewable energy"],
    "Advanced Materials & Sensing": ["nanomaterials", "smart sensors", "fiber optic sensing"],
    "Subsurface & Seismic Technologies": ["seismic inversion", "electromagnetic exploration", "microseismic monitoring"]
}

# Common abbreviations or alternate names that pycountry won’t match by default
COUNTRY_SYNONYMS = {
    r"\bu\.?s\.?\b": "United States",
    r"\bu\.?k\.?\b": "United Kingdom",
    r"\busa\b": "United States",
    r"\buk\b": "United Kingdom",
    r"\bu\.?a\.?e\.?\b": "United Arab Emirates",
    r"\brussia\b": "Russian Federation"
}

# ----------------------
# GEOCODING
# ----------------------
@st.cache_data(show_spinner=False)
def geocode_with_cache(location_name):
    """Cached geocoding function so we don’t keep hitting the geocoder repeatedly."""
    geolocator = Nominatim(user_agent="geo_extractor")
    try:
        location = geolocator.geocode(location_name, timeout=10)
        if location:
            return [location.latitude, location.longitude]
    except GeocoderTimedOut:
        return None
    return None

def geocode(location_name):
    return geocode_with_cache(location_name)

# ----------------------
# COUNTRY EXTRACTION
# ----------------------
def extract_countries(text):
    """
    Scan the provided text for any mention of a country using pycountry’s list.
    Also replace known abbreviations (U.S., UK, etc.) before scanning.
    """
    if not text:
        return []

    text_lower = text.lower()

    # 1. Replace synonyms/abbreviations with official names
    for pattern, replacement in COUNTRY_SYNONYMS.items():
        text_lower = re.sub(pattern, replacement.lower(), text_lower)

    found_countries = set()
    for country in pycountry.countries:
        # Check common name
        if country.name.lower() in text_lower:
            found_countries.add(country.name)
        # Check official_name if available
        if hasattr(country, "official_name") and country.official_name.lower() in text_lower:
            found_countries.add(country.name)
    return list(found_countries)

# ----------------------
# DB FUNCTIONS
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
            full_text TEXT,
            published_date TEXT,
            source TEXT,
            relevance_score REAL,
            locations TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_articles(search_query=None, source_filter="All", category="All", sort_by="date"):
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
    
    if category != "All":
        keywords = PREDEFINED_CATEGORIES.get(category, [])
        if keywords:
            keyword_conditions = " OR ".join(["title LIKE ? OR snippet LIKE ?" for _ in keywords])
            query_conditions.append(f"({keyword_conditions})")
            for kw in keywords:
                query_params.extend([f"%{kw}%", f"%{kw}%"])
    
    base_query = """
        SELECT id, title, link, snippet, full_text, published_date, source, relevance_score, locations
        FROM articles
    """
    
    if query_conditions:
        base_query += " WHERE " + " AND ".join(query_conditions)
    
    order_by = "published_date DESC" if sort_by == "date" else "relevance_score DESC"
    base_query += f" ORDER BY {order_by}"
    
    c.execute(base_query, query_params)
    rows = c.fetchall()
    conn.close()
    return rows

# ----------------------
# MAP DISPLAY
# ----------------------
def display_geospatial_map(filtered_articles):
    """
    Display a folium map with markers for each country found in the articles’ full_text.
    If multiple articles mention the same country, they are aggregated.
    """
    m = folium.Map(location=[20, 0], zoom_start=2)
    country_to_articles = {}
    
    # For each filtered article, extract countries from its full_text
    for article in filtered_articles:
        title = article[1]
        full_text = article[4] if article[4] else ""
        countries = extract_countries(full_text)
        for country in countries:
            country_to_articles.setdefault(country, []).append(title)
    
    # Add a marker for each unique country
    for country, titles in country_to_articles.items():
        coordinates = geocode(country)
        if coordinates:
            popup_text = f"{country}: " + ", ".join(titles)
            folium.Marker(location=coordinates, popup=popup_text).add_to(m)
    
    folium_static(m)

# ----------------------
# MAIN APP
# ----------------------
def main():
    st.image(ADNOC_LOGO_URL, width=150)
    st.title("Future Foresights Dashboard")
    create_table_if_not_exists()
    
    # 1. Filter controls
    source_filter = st.selectbox(
        "Select Source",
        ["All", "RSS", "arXiv"],
        help="Filter articles by their source"
    )
    category_options = ["All"] + list(PREDEFINED_CATEGORIES.keys())
    selected_category = st.selectbox("Choose a Category", category_options)
    search_query = st.text_input("Search by any keyword or partial title:", "")
    
    # 2. Get filtered articles
    articles = get_articles(search_query, source_filter, selected_category, sort_by="relevance")
    
    # 3. Show the map first
    st.header("Geospatial Insights")
    st.write("The map below shows the countries mentioned in the full text of the articles that match your filter:")
    display_geospatial_map(articles)
    
    # 4. Then show the articles list
    st.write(f"**Found {len(articles)} articles** matching your criteria:")
    for article in articles:
        # Unpack: (id, title, link, snippet, full_text, published_date, source, relevance_score, locations)
        id_, title, link, snippet, full_text, published_date, source, relevance_score, locations = article
        st.subheader(title)
        st.write(f"**Source:** {source} | **Published:** {published_date} | **Relevance Score:** {relevance_score:.2f}")
        st.write("**Summary:**")
        lines = snippet.split('\n')
        for line in lines:
            if not line.strip():
                st.write("")
                continue
            if re.match(r'^\d+\.\s', line.strip()):
                st.markdown(line.strip())
            else:
                st.markdown(line)
        st.markdown(f"[Read More]({link})", unsafe_allow_html=True)
        st.write("---")

if __name__ == "__main__":
    main()
