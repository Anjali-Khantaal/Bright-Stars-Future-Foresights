import sqlite3
import streamlit as st
import os
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import re
from datetime import datetime, date
from folium.plugins import HeatMap
import ast
import time
import json
import requests

# Set page configuration to wide mode for a more spacious layout
st.set_page_config(page_title="Future Foresights Dashboard", layout="wide")

# At the top of your file, after your imports:
geolocator = Nominatim(user_agent="geo_extractor", timeout=10)
geocode_cache = {}

def geocode_cached(location_name):
    """Convert a location name to latitude and longitude with caching."""
    if location_name in geocode_cache:
        return geocode_cache[location_name]
    time.sleep(1)
    try:
        location = geolocator.geocode(location_name)
        if location:
            coords = [location.latitude, location.longitude]
            geocode_cache[location_name] = coords
            return coords
    except GeocoderTimedOut:
        geocode_cache[location_name] = None
    geocode_cache[location_name] = None
    return None


# =====================
# Database configuration
# =====================
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

# A dictionary to handle common short-form country names.
COUNTRY_ALIASES = {
    "US": "United States",
    "USA": "United States",
    "UAE": "United Arab Emirates",
    "UK": "United Kingdom",
    "KSA": "Saudi Arabia",
    "EU": "European Union",
}
KNOWN_COUNTRIES = {
    "united states", "united kingdom", "saudi arabia", "china",
    "india", "germany", "france", "uae", "brazil", "canada",
}

# =====================
# Helper Functions
# =====================
def safe_score(value):
    try:
        val = float(value)
        if val < 0:
            val = 0
        if val > 100:
            val = 100
        return int(val)
    except:
        return 0

def safe_float_str(value):
    try:
        return float(value)
    except:
        return 0.0

def geocode(location_name):
    geolocator = Nominatim(user_agent="geo_extractor")
    try:
        location = geolocator.geocode(location_name, timeout=10)
        if location:
            return [location.latitude, location.longitude]
    except GeocoderTimedOut:
        return None
    return None

def find_matching_categories(title, snippet):
    matched = []
    text_lower = (title or "") + " " + (snippet or "")
    text_lower = text_lower.lower()
    for cat, keywords in PREDEFINED_CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                matched.append(cat)
                break
    return matched

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
            novelty_score REAL,
            heat_score REAL,
            locations TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_title_suggestions(search_query):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    query = "SELECT DISTINCT title FROM articles WHERE title LIKE ? LIMIT 5"
    c.execute(query, (f"%{search_query}%",))
    suggestions = [row[0] for row in c.fetchall()]
    conn.close()
    return suggestions

def get_articles(search_query=None, source_filter="All", categories=None, date_range=None, sort_by="date"):
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
    
    if categories and len(categories) > 0:
        cat_conditions = []
        for cat in categories:
            keywords = PREDEFINED_CATEGORIES.get(cat, [])
            if keywords:
                subconds = []
                for kw in keywords:
                    subconds.append("(title LIKE ? OR snippet LIKE ?)")
                    query_params.extend([f"%{kw}%", f"%{kw}%"])
                cat_conditions.append("(" + " OR ".join(subconds) + ")")
        if cat_conditions:
            query_conditions.append("(" + " OR ".join(cat_conditions) + ")")
    
    if date_range:
        start_date, end_date = date_range
        query_conditions.append("published_date BETWEEN ? AND ?")
        query_params.extend([start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")])
    
    base_query = """
        SELECT id, title, link, snippet, full_text, published_date, source, 
               relevance_score, novelty_score, heat_score, locations
        FROM articles
    """
    
    if query_conditions:
        base_query += " WHERE " + " AND ".join(query_conditions)
    
    if sort_by == "relevance":
        order_by = "relevance_score DESC"
    elif sort_by == "novelty":
        order_by = "novelty_score DESC"
    elif sort_by == "heat":
        order_by = "heat_score DESC"
    elif sort_by == "date":
        order_by = "published_date DESC"
    else:
        order_by = "relevance_score DESC"
    
    base_query += f" ORDER BY {order_by}"
    
    c.execute(base_query, query_params)
    rows = c.fetchall()
    conn.close()
    return rows

def display_choropleth_map(filtered_articles, theme="Dark"):
    country_counts = {}
    for article in filtered_articles:
        locations_str = article[10]  
        if locations_str:
            countries = [country.strip() for country in locations_str.split(",") if country.strip()]
            for country in countries:
                country_counts[country] = country_counts.get(country, 0) + 1

    df = pd.DataFrame(list(country_counts.items()), columns=["Country", "Count"])
    geojson_url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
    world_geo = requests.get(geojson_url).json()
    tile = "CartoDB dark_matter" if theme == "Dark" else "CartoDB positron"
    m = folium.Map(location=[20, 0], zoom_start=2, tiles=tile)
    choropleth = folium.Choropleth(
        geo_data=world_geo,
        data=df,
        columns=["Country", "Count"],
        key_on="feature.properties.name",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Number of Article Mentions",
        nan_fill_color="white"
    ).add_to(m)
    folium.features.GeoJsonTooltip(
        fields=["name"],
        aliases=["Country:"],
        localize=True
    ).add_to(choropleth.geojson)
    folium_static(m)

def display_geospatial_map(filtered_articles):
    m = folium.Map(location=[20, 0], zoom_start=2)
    for article in filtered_articles:
        _, title, _, _, _, _, _, _, _, locations = article
        if locations:
            for loc in locations.split(", "):
                coordinates = geocode(loc)
                if coordinates:
                    folium.Marker(location=coordinates, popup=title).add_to(m)
    folium_static(m)

def display_heatmap(filtered_articles, theme="Dark"):
    tile = "CartoDB dark_matter" if theme == "Dark" else "CartoDB positron"
    m = folium.Map(location=[20, 0], zoom_start=2, tiles=tile)
    unique_countries = set()
    for article in filtered_articles:
        full_text = article[4]
        if not full_text:
            continue
        text_lower = full_text.lower()
        for country in KNOWN_COUNTRIES:
            if country in text_lower:
                expanded_country = COUNTRY_ALIASES.get(country.upper(), country.title())
                unique_countries.add(expanded_country)
    heat_data = []
    with st.spinner("Geocoding country names..."):
        for country in unique_countries:
            coordinates = geocode_cached(country)
            if coordinates:
                heat_data.append(coordinates)
    if heat_data:
        HeatMap(heat_data, radius=25, blur=15).add_to(m)
    else:
        st.info("No valid location data found. Displaying default world map below.")
    folium_static(m)


def main():
    # st.image(ADNOC_LOGO_URL, width=150)
    # st.title("Future Foresights Dashboard")
    
    # Inject custom CSS for a cohesive look
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    
    .title-centered {
        text-align: center;
        font-size: 2.5rem;       /* Adjust as needed */
        font-weight: 700;        /* Bold */
        margin-top: 20px;
        margin-bottom: 20px;
        color: #ffffff;          /* Or your preferred color */
    }
                
    /* 2) Apply it globally */
    body {
        font-family: 'Roboto', sans-serif;
        margin: 0;
        padding: 0;
    }
    /* 3) Make a subtle gradient background for the main container in Dark mode */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #1e1e1e 0%, #2b2b2b 100%);
        color: #ffffff;
    }          
    .summary-container {
        background-color: #262730;
        border-left: 4px solid #009688;
        padding: 15px;
        margin: 15px 0;
        border-radius: 8px;
        line-height: 1.5;
        color: #ffffff;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .summary-container p {
       margin-bottom: 8px;
    }
    details summary {
       cursor: pointer;
       color: #00bcd4;
       text-decoration: none;
       list-style: none;
       font-weight: bold;
       font-size: 0.95rem;
       margin-top: 10px;
       display: inline-block;
       padding: 6px 12px;
       border: 1px solid #00bcd4;
       border-radius: 4px;
       background-color: transparent;
       transition: background-color 0.2s ease, color 0.2s ease;
    }
    details summary:hover {
       background-color: #00bcd4;
       color: #262730;
    }
    details[open] summary {
       background-color: #00bcd4;
       color: #262730;
    }
    details[open] > *:not(summary) {
       margin-top: 10px;
    }
    .badge {
       display: inline-block;
       background-color: #009688;
       color: #fff;
       padding: 2px 6px;
       border-radius: 10px;
       font-size: 0.75rem;
       margin-left: 6px;
    }
    .element-container:hover .stProgress > div {
        transform: scale(1.03);
        transition: transform 0.2s ease-in-out;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar: Theme Toggle and Filters for improved responsiveness
    # theme_choice = st.sidebar.radio("Choose Theme", options=["Light", "Dark"], index=1)
    theme_choice = "Dark"
    if theme_choice == "Light":
        st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] {
            background-color: #ffffff;
            color: #000000;
        }
        label, .stTextInput label, .stSelectbox label, .stDateInput label, 
        .stCheckbox label, .stRadio label {
            color: #000000 !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        label, .stTextInput label, .stSelectbox label, .stDateInput label, 
        .stCheckbox label, .stRadio label {
            color: #ffffff !important;
        }
        </style>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style='text-align: center;'>
            <img src='{ADNOC_LOGO_URL}' style='width: 150px; margin-bottom: 10px;' />
            <h1 class='title-centered'>Future Foresights Dashboard</h1>
        </div>
        """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    st.sidebar.header("Filters")
    
    source_filter = st.sidebar.selectbox("Select Source", ["All", "RSS", "arXiv"],
                                     help="Filter articles by their source")
    selected_categories = st.sidebar.multiselect("Choose Categories", options=list(PREDEFINED_CATEGORIES.keys()))
    search_query = st.sidebar.text_input("Search by any keyword or partial title:")
    if search_query:
        suggestions = get_title_suggestions(search_query)
        if suggestions:
            chosen = st.sidebar.selectbox("Suggestions", suggestions, key="autocomplete")
            if chosen:
                search_query = chosen
    apply_date_filter = st.sidebar.checkbox("Apply Published Date Filter", value=False)
    if apply_date_filter:
        date_range = st.sidebar.date_input("Published Date Range", value=(date(2020, 1, 1), date.today()))
        if isinstance(date_range, tuple):
            start_date, end_date = date_range
        else:
            start_date = end_date = None
    else:
        start_date = end_date = None

    sort_by = st.sidebar.selectbox("Sort by", ["Relevance Score", "Novelty Score", "Heat Score", "Published Date"], index=0)
    sort_mapping = {
        "Relevance Score": "relevance",
        "Novelty Score": "novelty",
        "Heat Score": "heat",
        "Published Date": "date"
    }
    selected_sort = sort_mapping[sort_by]

    create_table_if_not_exists()
    
    articles = get_articles(
        search_query=search_query,
        source_filter=source_filter,
        categories=selected_categories if selected_categories else None,
        date_range=(start_date, end_date) if start_date and end_date else None,
        sort_by=selected_sort
    )
    
    st.write(f"Based on the current filters (in the sidebar): **Found {len(articles)} articles** matching your criteria:")

    if st.checkbox("Show Choropleth Map"):
        st.header("Choropleth Map of Countries")
        display_choropleth_map(articles, theme=theme_choice)

    for article in articles:
        (article_id, title, link, snippet, full_text, published_date, source,
         relevance_score, novelty_score, heat_score, locations) = article
        st.markdown("<div class='article-container'>", unsafe_allow_html=True)
        
        rel_val = safe_float_str(relevance_score)
        nov_val = safe_float_str(novelty_score)
        heat_val = safe_float_str(heat_score)

        st.subheader(title)
        matched_cats = find_matching_categories(title, snippet)
        if matched_cats:
            badge_str = "".join(
                f"<span class='badge'>{cat}</span>"
                for cat in matched_cats
            )
            st.markdown(badge_str, unsafe_allow_html=True)
        
        st.write(
            f"**Source:** {source} | **Published:** {published_date} "
            f"| **Relevance Score:** {rel_val:.2f} "
            f"| **Novelty Score:** {nov_val:.2f} "
            f"| **Heat Score:** {heat_val:.2f}"
        )
        
        score_col1, score_col2, score_col3 = st.columns(3)
        with score_col1:
            st.write("Relevance")
            st.progress(safe_score(relevance_score))
        with score_col2:
            st.write("Novelty")
            st.progress(safe_score(novelty_score))
        with score_col3:
            st.write("Heat")
            st.progress(safe_score(heat_score))
        
        if "SUMMARY: " in snippet:
            summary_text = snippet.split("SUMMARY: ", 1)[1]
        else:
            summary_text = snippet
        
        st.write("**Summary:**")
        summary_html = '<div class="summary-container">'
        lines = summary_text.split('\n')
        filtered_lines = [line.strip() for line in lines if line.strip()]
        if len(filtered_lines) > 3:
            first_part = "".join(f"<p>{l}</p>" for l in filtered_lines[:3])
            rest_part = "".join(f"<p>{l}</p>" for l in filtered_lines[3:])
            summary_html += first_part
            summary_html += f"""
            <details>
              <summary>Continue Reading</summary>
              {rest_part}
            </details>
            """
        else:
            summary_html += "".join(f"<p>{l}</p>" for l in filtered_lines)
        summary_html += "</div>"
        
        st.markdown(summary_html, unsafe_allow_html=True)
        st.markdown(f"[Read More]({link})", unsafe_allow_html=True)
        st.write("---")
        st.markdown("</div>", unsafe_allow_html=True)
    # Uncomment to display the geospatial map:
    # st.header("Geospatial Insights")
    # display_geospatial_map(articles)

if __name__ == "__main__":
    main()
