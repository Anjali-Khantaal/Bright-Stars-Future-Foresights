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
import pandas as pd
import requests

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
        # Optionally, you can retry or simply return None here.
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
    # Add more as needed...
}
KNOWN_COUNTRIES = {
    "united states", "united kingdom", "saudi arabia", "china",
    "india", "germany", "france", "uae", "brazil", "canada",
    # etc...
}

# =====================
# Helper Functions
# =====================
def safe_score(value):
    """
    Convert any value to an integer [0, 100] for st.progress().
    This prevents ValueError if the score is a string like '70.0' or out of range.
    """
    try:
        val = float(value)
        if val < 0:
            val = 0
        if val > 100:
            val = 100
        return int(val)
    except:
        # If conversion fails, default to 0
        return 0

def safe_float_str(value):
    """
    Convert any value to a float for display (e.g., {:.2f}).
    Returns 0.0 if parsing fails.
    """
    try:
        return float(value)
    except:
        return 0.0

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

def find_matching_categories(title, snippet):
    """
    Return a list of PREDEFINED_CATEGORIES that match the article's title or snippet,
    based on presence of relevant keywords.
    """
    matched = []
    # Combine title + snippet, then check for any of the category keywords
    text_lower = (title or "") + " " + (snippet or "")
    text_lower = text_lower.lower()

    for cat, keywords in PREDEFINED_CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                matched.append(cat)
                break  # Avoid duplicates from the same category
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
    """Return up to 5 article title suggestions matching the search query."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    query = "SELECT DISTINCT title FROM articles WHERE title LIKE ? LIMIT 5"
    c.execute(query, (f"%{search_query}%",))
    suggestions = [row[0] for row in c.fetchall()]
    conn.close()
    return suggestions

def get_articles(search_query=None, source_filter="All", categories=None, date_range=None, sort_by="date"):
    """
    Fetch articles applying:
     - search query on title/snippet,
     - source filter,
     - multiple categories (if provided),
     - date_range filter,
     - sorting.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    query_conditions = []
    query_params = []
    
    # Search query filter
    if search_query:
        query_conditions.append("(title LIKE ? OR snippet LIKE ?)")
        like_query = f"%{search_query}%"
        query_params.extend([like_query, like_query])
    
    # Source filter
    if source_filter != "All":
        if source_filter == "RSS":
            query_conditions.append("source != 'arXiv'")
        elif source_filter == "arXiv":
            query_conditions.append("source = 'arXiv'")
    
    # Multiple categories (faceted filtering)
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
    
    # Date range filtering (only if date_range is provided)
    if date_range:
        start_date, end_date = date_range
        query_conditions.append("published_date BETWEEN ? AND ?")
        query_params.extend([start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")])
    
    # --- Modified SQL: Include full_text column ---
    base_query = """
        SELECT id, title, link, snippet, full_text, published_date, source, 
               relevance_score, novelty_score, heat_score, locations
        FROM articles
    """
    
    if query_conditions:
        base_query += " WHERE " + " AND ".join(query_conditions)
    
    # Sorting order
    if sort_by == "relevance":
        order_by = "relevance_score DESC"
    elif sort_by == "novelty":
        order_by = "novelty_score DESC"
    elif sort_by == "heat":
        order_by = "heat_score DESC"
    elif sort_by == "date":
        order_by = "published_date DESC"
    else:
        order_by = "relevance_score DESC"  # Default fallback
    
    base_query += f" ORDER BY {order_by}"
    
    c.execute(base_query, query_params)
    rows = c.fetchall()
    conn.close()
    return rows

def display_choropleth_map(filtered_articles, theme="Dark"):
    """
    Displays a choropleth map where each country's shade corresponds to how many times 
    it appears in the filtered articles. Darker shades represent a higher count.
    """
    # Aggregate country counts from the stored 'locations' column (assumed at index 10)
    country_counts = {}
    for article in filtered_articles:
        # 'locations' is the last field in each article row (index 10 as per SELECT)
        locations_str = article[10]  
        if locations_str:
            # Split by comma and strip any extra spaces
            countries = [country.strip() for country in locations_str.split(",") if country.strip()]
            for country in countries:
                country_counts[country] = country_counts.get(country, 0) + 1

    # Convert the dictionary to a DataFrame for choropleth mapping
    df = pd.DataFrame(list(country_counts.items()), columns=["Country", "Count"])

    # Load world GeoJSON boundaries (this is a public resource)
    geojson_url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
    world_geo = requests.get(geojson_url).json()

    # Choose tile style based on the selected theme
    tile = "CartoDB dark_matter" if theme == "Dark" else "CartoDB positron"
    m = folium.Map(location=[20, 0], zoom_start=2, tiles=tile)

    # Create the choropleth layer that colors countries based on their count
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

    # Optionally, add tooltips to display country names on hover
    folium.features.GeoJsonTooltip(
        fields=["name"],
        aliases=["Country:"],
        localize=True
    ).add_to(choropleth.geojson)

    folium_static(m)

def display_geospatial_map(filtered_articles):
    """Display a map with locations where technology is trending based on filtered articles."""
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
        full_text = article[4]  # 'full_text' column
        if not full_text:
            continue

        text_lower = full_text.lower()

        # Check if any known country name appears in the text
        for country in KNOWN_COUNTRIES:
            if country in text_lower:
                # Also handle short forms like "US" -> "United States"
                # if you want to expand short forms, do it here:
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
    st.image(ADNOC_LOGO_URL, width=150)
    st.title("Future Foresights Dashboard")
    
    # Inject custom CSS for a cohesive look (custom theme)
    st.markdown("""
    <style>
    body {
        font-family: 'Arial', sans-serif;
    }
    .summary-container {
       background-color: #262730;  /* Dark grey background */
       border-left: 4px solid #009688;  /* Teal border */
       padding: 15px;
       margin: 15px 0;
       border-radius: 8px;
       line-height: 1.5;
       color: #ffffff;  /* White text for readability */
       box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .summary-container p {
       margin-bottom: 8px;
    }
    details summary {
       cursor: pointer;
       color: #00bcd4;  /* Lighter teal color */
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
    /* Improve spacing when details are open */
    details[open] > *:not(summary) {
       margin-top: 10px;
    }
    /* Simple inline badge styling */
    .badge {
       display: inline-block;
       background-color: #009688;
       color: #fff;
       padding: 2px 6px;
       border-radius: 10px;
       font-size: 0.75rem;
       margin-left: 6px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Light/Dark Mode Toggle in Sidebar
    theme_choice = st.sidebar.radio("Choose Theme", options=["Light", "Dark"], index=1)

    if theme_choice == "Light":
        st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] {
            background-color: #ffffff;
            color: #000000;
        }
        /* Force label text color to black in the sidebar and main container */
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
        /* Force label text color to white in the sidebar and main container */
        label, .stTextInput label, .stSelectbox label, .stDateInput label, 
        .stCheckbox label, .stRadio label {
            color: #ffffff !important;
        }
        </style>
        """, unsafe_allow_html=True)

    
    create_table_if_not_exists()
    
    # Responsive Design: Arrange filter controls using columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        source_filter = st.selectbox("Select Source", ["All", "RSS", "arXiv"],
                                     help="Filter articles by their source")
    with col2:
        # Multiple category selection for faceted filtering
        selected_categories = st.multiselect("Choose Categories", options=list(PREDEFINED_CATEGORIES.keys()))
    with col3:
        # Live Search/Autocomplete
        search_query = st.text_input("Search by any keyword or partial title:")
        if search_query:
            suggestions = get_title_suggestions(search_query)
            if suggestions:
                chosen = st.selectbox("Suggestions", suggestions, key="autocomplete")
                if chosen:
                    search_query = chosen
    with col4:
        # Date range filter is optional via a checkbox
        apply_date_filter = st.checkbox("Apply Published Date Filter", value=False)
        if apply_date_filter:
            date_range = st.date_input("Published Date Range", value=(date(2020, 1, 1), date.today()))
            if isinstance(date_range, tuple):
                start_date, end_date = date_range
            else:
                start_date = end_date = None
        else:
            start_date = end_date = None

    # Sorting option
    sort_by = st.selectbox("Sort by", ["Relevance Score", "Novelty Score", "Heat Score", "Published Date"], index=0)
    sort_mapping = {
        "Relevance Score": "relevance",
        "Novelty Score": "novelty",
        "Heat Score": "heat",
        "Published Date": "date"
    }
    selected_sort = sort_mapping[sort_by]

    # Fetch articles
    articles = get_articles(
        search_query=search_query,
        source_filter=source_filter,
        categories=selected_categories if selected_categories else None,
        date_range=(start_date, end_date) if start_date and end_date else None,
        sort_by=selected_sort
    )
    
    st.write(f"**Found {len(articles)} articles** matching your criteria:")

    if st.checkbox("Show Choropleth Map"):
        st.header("Choropleth Map of Countries Mentioned")
        display_choropleth_map(articles, theme=theme_choice)

    for article in articles:
        (article_id, title, link, snippet, full_text, published_date, source,
         relevance_score, novelty_score, heat_score, locations) = article
        
        # Convert numeric values for display
        rel_val = safe_float_str(relevance_score)
        nov_val = safe_float_str(novelty_score)
        heat_val = safe_float_str(heat_score)

        # 1) Show Title & Badges
        st.subheader(title)
        # Determine matched categories for inline badges
        from re import IGNORECASE
        matched_cats = []
        matched_cats = find_matching_categories(title, snippet)
        
        if matched_cats:
            # Build simple HTML badges
            badge_str = "".join(
                f"<span class='badge'>{cat}</span>"
                for cat in matched_cats
            )
            # Show them right under the title
            st.markdown(badge_str, unsafe_allow_html=True)
        
        # 2) Show Source & Scores
        st.write(
            f"**Source:** {source} | **Published:** {published_date} "
            f"| **Relevance Score:** {rel_val:.2f} "
            f"| **Novelty Score:** {nov_val:.2f} "
            f"| **Heat Score:** {heat_val:.2f}"
        )
        
        # Interactive Score Bars
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
        
        # 3) Summaries
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

        # 4) Read More Link
        st.markdown(f"[Read More]({link})", unsafe_allow_html=True)
        st.write("---")
    
    # Uncomment to display the geospatial map:
    # st.header("Geospatial Insights")
    # display_geospatial_map(articles)

if __name__ == "__main__":
    main()
