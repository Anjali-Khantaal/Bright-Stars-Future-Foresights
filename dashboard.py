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
# Database configuration
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

def geocode(location_name):
    """Convert location name to latitude and longitude using geopy."""
    geolocator = Nominatim(user_agent="geo_extractor")
    try:
        location = geolocator.geocode(location_name, timeout=10)
        if location:
            return [location.latitude, location.longitude]
    except GeocoderTimedOut:
        return None
    return None

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
        SELECT id, title, link, snippet, published_date, source, relevance_score, locations
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

def display_geospatial_map(filtered_articles):
    """Display a map with locations where technology is trending based on filtered articles."""
    m = folium.Map(location=[20, 0], zoom_start=2)
    
    for article in filtered_articles:
        _,title, _, _, _, _, _, locations = article  # Extract only relevant data
        if locations:
            for loc in locations.split(", "):
                coordinates = geocode(loc)
                if coordinates:
                    folium.Marker(location=coordinates, popup=title).add_to(m)

    folium_static(m)


def main():
    st.image(ADNOC_LOGO_URL, width=150)
    st.title("Future Foresights Dashboard")
    create_table_if_not_exists()
    
    source_filter = st.selectbox("Select Source", ["All", "RSS", "arXiv"], help="Filter articles by their source")
    category_options = ["All"] + list(PREDEFINED_CATEGORIES.keys())
    selected_category = st.selectbox("Choose a Category", category_options)
    search_query = st.text_input("Search by any keyword or partial title:", "")
    

    
    articles = get_articles(search_query, source_filter, selected_category, sort_by="relevance")
    
    st.write(f"**Found {len(articles)} articles** matching your criteria:")
    for article in articles:
        id,title, link, snippet, published_date, source, relevance_score, locations = article
        st.subheader(title)
        st.write(f"**Source:** {source} | **Published:** {published_date} | **Relevance Score:** {relevance_score:.2f}")
        if "SUMMARY: " in snippet:
            summary_text = snippet.split("SUMMARY: ", 1)[1]
        else:
            summary_text = snippet
        st.write("**Summary:**")

        lines = summary_text.split('\n')
        for line in lines:
            # If the line is just a blank line, skip or show it
            if not line.strip():
                st.write("")
                continue
            
            # If the line starts with a digit and a period (e.g., "1. ", "2. "),
            # just display it as-is to preserve numbering
            if re.match(r'^\d+\.\s', line.strip()):
                st.markdown(line.strip())
            else:
                st.markdown(line)
        st.markdown(f"[Read More]({link})", unsafe_allow_html=True)
        st.write("---")
    
    '''st.header("Geospatial Insights")
    display_geospatial_map(articles)  # Now only filtered articles are passed'''


if __name__ == "__main__":
    main()