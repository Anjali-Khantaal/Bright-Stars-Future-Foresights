import sqlite3
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Configuration
DATABASE = "articles.db"
ADNOC_LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRjLmGUCFcKxiEkiIl_YMaJ1GL9iPUwIZWojQ&s"

@dataclass
class Article:
    id: int
    title: str
    link: str
    snippet: str
    published_date: str
    source: str
    relevance_score: float
    locations: str
    novelty_score: float
    heat_score: float

class DashboardManager:
    PREDEFINED_CATEGORIES = {
        "Oil & Gas Industry": ["oil", "gas", "petroleum"],
        "Digital Transformation & Automation": ["technology", "innovation", "digital transformation"],
        "AI & Machine Learning Applications": ["AI", "machine learning", "big data analytics"],
        "Sustainability & Energy Transition": ["carbon capture", "hydrogen", "renewable energy"],
        "Advanced Materials & Sensing": ["nanomaterials", "smart sensors", "fiber optic sensing"],
        "Subsurface & Seismic Technologies": ["seismic inversion", "electromagnetic exploration", "microseismic monitoring"]
    }

    def __init__(self):
        self.setup_database()
        self.geolocator = Nominatim(user_agent="geo_extractor")

    def setup_database(self) -> None:
        """Initialize database with new scoring columns."""
        with sqlite3.connect(DATABASE) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    link TEXT UNIQUE,
                    snippet TEXT,
                    full_text TEXT,
                    published_date TEXT,
                    source TEXT,
                    relevance_score REAL,
                    locations TEXT,
                    novelty_score REAL DEFAULT 0,
                    heat_score REAL DEFAULT 0
                )
            """)

    def get_articles(self, search_query: Optional[str] = None, 
                    source_filter: str = "All", 
                    category: str = "All", 
                    sort_by: str = "date") -> List[Article]:
        """Enhanced article retrieval with scoring features."""
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
            keywords = self.PREDEFINED_CATEGORIES.get(category, [])
            if keywords:
                keyword_conditions = " OR ".join(["title LIKE ? OR snippet LIKE ?" for _ in keywords])
                query_conditions.append(f"({keyword_conditions})")
                for kw in keywords:
                    query_params.extend([f"%{kw}%", f"%{kw}%"])
        
        base_query = """
            SELECT id, title, link, snippet, published_date, source, 
                   relevance_score, locations, novelty_score, heat_score
            FROM articles
        """
        
        if query_conditions:
            base_query += " WHERE " + " AND ".join(query_conditions)
        
        order_mapping = {
            "date": "published_date DESC",
            "relevance": "relevance_score DESC",
            "novelty": "novelty_score DESC",
            "heat": "heat_score DESC"
        }
        base_query += f" ORDER BY {order_mapping.get(sort_by, 'published_date DESC')}"
        
        with sqlite3.connect(DATABASE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(base_query, query_params)
            return [Article(**dict(row)) for row in cursor.fetchall()]

    def geocode(self, location_name: str) -> Optional[List[float]]:
        """Geocode location with error handling."""
        try:
            location = self.geolocator.geocode(location_name, timeout=10)
            if location:
                return [location.latitude, location.longitude]
        except GeocoderTimedOut:
            st.warning(f"Geocoding timed out for location: {location_name}")
        except Exception as e:
            st.error(f"Error geocoding location {location_name}: {e}")
        return None

    def create_score_distribution_chart(self, articles: List[Article]) -> go.Figure:
        """Create a scatter plot of novelty vs heat scores."""
        df = pd.DataFrame([
            {
                'title': article.title,
                'novelty_score': article.novelty_score,
                'heat_score': article.heat_score,
                'relevance_score': article.relevance_score
            }
            for article in articles
        ])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['novelty_score'],
            y=df['heat_score'],
            mode='markers',
            marker=dict(
                size=df['relevance_score'] * 10,
                color=df['relevance_score'],
                colorscale='Viridis',
                showscale=True
            ),
            text=df['title'],
            hoverinfo='text'
        ))
        
        fig.update_layout(
            title='Article Score Distribution',
            xaxis_title='Novelty Score',
            yaxis_title='Heat Score',
            height=600
        )
        
        return fig

def main():
    st.set_page_config(layout="wide")
    dashboard = DashboardManager()
    
    # Header
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(ADNOC_LOGO_URL, width=150)
    with col2:
        st.title("Future Foresights Dashboard")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        source_filter = st.selectbox("Select Source", ["All", "RSS", "arXiv"])
    with col2:
        category_options = ["All"] + list(dashboard.PREDEFINED_CATEGORIES.keys())
        selected_category = st.selectbox("Choose a Category", category_options)
    with col3:
        search_query = st.text_input("Search Keywords:", "")
    with col4:
        sort_options = {
            "date": "Publication Date",
            "relevance": "Relevance Score",
            "novelty": "Novelty Score",
            "heat": "Heat Score"
        }
        sort_by = st.selectbox("Sort By:", list(sort_options.keys()), format_func=lambda x: sort_options[x])
    
    # Get and display articles
    articles = dashboard.get_articles(search_query, source_filter, selected_category, sort_by)
    
    # Analytics Section
    st.header("Analytics Dashboard")
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(dashboard.create_score_distribution_chart(articles), use_container_width=True)
    
    with col2:
        # Summary statistics
        df = pd.DataFrame([{
            'novelty_score': article.novelty_score,
            'heat_score': article.heat_score,
            'relevance_score': article.relevance_score
        } for article in articles])
        
        st.write("### Key Metrics")
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric("Average Novelty", f"{df['novelty_score'].mean():.1f}")
        with metrics_col2:
            st.metric("Average Heat", f"{df['heat_score'].mean():.1f}")
        with metrics_col3:
            st.metric("Average Relevance", f"{df['relevance_score'].mean():.1f}")
    
    # Articles Section
    st.header(f"Articles ({len(articles)})")
    for article in articles:
        with st.expander(f"{article.title} (Novelty: {article.novelty_score:.1f}, Heat: {article.heat_score:.1f})"):
            st.write(f"**Source:** {article.source} | **Published:** {article.published_date}")
            st.write(f"**Relevance Score:** {article.relevance_score:.2f}")
            
            summary_text = article.snippet.split("SUMMARY: ", 1)[-1]
            st.write("**Summary:**")
            
            for line in summary_text.split('\n'):
                if not line.strip():
                    st.write("")
                    continue
                
                if re.match(r'^\d+\.\s', line.strip()):
                    st.markdown(line.strip())
                else:
                    st.markdown(line)
                    
            st.markdown(f"[Read More]({article.link})")

if __name__ == "__main__":
    main()


# import sqlite3
# import streamlit as st
# import pandas as pd
# import folium
# from streamlit_folium import folium_static
# from geopy.geocoders import Nominatim
# from geopy.exc import GeocoderTimedOut
# import re
# from typing import List, Dict, Optional, Tuple
# from dataclasses import dataclass
# from datetime import datetime
# import plotly.express as px
# import plotly.graph_objects as go

# # Configuration
# DATABASE = "articles.db"
# ADNOC_LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRjLmGUCFcKxiEkiIl_YMaJ1GL9iPUwIZWojQ&s"

# @dataclass
# class Article:
#     id: int
#     title: str
#     link: str
#     snippet: str
#     published_date: str
#     source: str
#     relevance_score: float
#     locations: str
#     novelty_score: float
#     heat_score: float

#     @staticmethod
#     def parse_score(score_str: str) -> float:
#         """Parse score value from string, handling various formats."""
#         try:
#             # If it's already a float, return it
#             if isinstance(score_str, float):
#                 return score_str
            
#             # If it's a string, clean and convert
#             if isinstance(score_str, str):
#                 # Remove any text and get first number
#                 numbers = re.findall(r'[\d.]+', score_str)
#                 if numbers:
#                     return float(numbers[0])
            
#             return 0.0  # Default value if parsing fails
#         except Exception:
#             return 0.0

#     def __post_init__(self):
#         """Clean up score values after initialization."""
#         self.relevance_score = self.parse_score(self.relevance_score)
#         self.novelty_score = self.parse_score(self.novelty_score)
#         self.heat_score = self.parse_score(self.heat_score)

# class DashboardManager:
    
#     PREDEFINED_CATEGORIES = {
#         "Oil & Gas Industry": ["oil", "gas", "petroleum"],
#         "Digital Transformation & Automation": ["technology", "innovation", "digital transformation"],
#         "AI & Machine Learning Applications": ["AI", "machine learning", "big data analytics"],
#         "Sustainability & Energy Transition": ["carbon capture", "hydrogen", "renewable energy"],
#         "Advanced Materials & Sensing": ["nanomaterials", "smart sensors", "fiber optic sensing"],
#         "Subsurface & Seismic Technologies": ["seismic inversion", "electromagnetic exploration", "microseismic monitoring"]
#     }

#     def __init__(self):
#         self.setup_database()
#         self.geolocator = Nominatim(user_agent="geo_extractor")

#     def setup_database(self) -> None:
#         """Initialize database with new scoring columns."""
#         with sqlite3.connect(DATABASE) as conn:
#             conn.execute("""
#                 CREATE TABLE IF NOT EXISTS articles (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     title TEXT,
#                     link TEXT UNIQUE,
#                     snippet TEXT,
#                     full_text TEXT,
#                     published_date TEXT,
#                     source TEXT,
#                     relevance_score REAL,
#                     locations TEXT,
#                     novelty_score REAL DEFAULT 0,
#                     heat_score REAL DEFAULT 0
#                 )
#             """)

#     def get_articles(self, search_query: Optional[str] = None, 
#                     source_filter: str = "All", 
#                     category: str = "All", 
#                     sort_by: str = "date") -> List[Article]:
#         """Enhanced article retrieval with scoring features."""
#         query_conditions = []
#         query_params = []
        
#         if search_query:
#             query_conditions.append("(title LIKE ? OR snippet LIKE ?)")
#             like_query = f"%{search_query}%"
#             query_params.extend([like_query, like_query])
        
#         if source_filter != "All":
#             if source_filter == "RSS":
#                 query_conditions.append("source != 'arXiv'")
#             elif source_filter == "arXiv":
#                 query_conditions.append("source = 'arXiv'")
        
#         if category != "All":
#             keywords = self.PREDEFINED_CATEGORIES.get(category, [])
#             if keywords:
#                 keyword_conditions = " OR ".join(["title LIKE ? OR snippet LIKE ?" for _ in keywords])
#                 query_conditions.append(f"({keyword_conditions})")
#                 for kw in keywords:
#                     query_params.extend([f"%{kw}%", f"%{kw}%"])
        
#         base_query = """
#             SELECT id, title, link, snippet, published_date, source, 
#             relevance_score, locations, novelty_score, heat_score
#             FROM articles
#         """
        
#         if query_conditions:
#             base_query += " WHERE " + " AND ".join(query_conditions)
        
#         order_mapping = {
#             "date": "published_date DESC",
#             "relevance": "relevance_score DESC",
#             "novelty": "novelty_score DESC",
#             "heat": "heat_score DESC"
#         }
#         base_query += f" ORDER BY {order_mapping.get(sort_by, 'published_date DESC')}"
        
#         with sqlite3.connect(DATABASE) as conn:
#             conn.row_factory = sqlite3.Row
#             cursor = conn.execute(base_query, query_params)
#             return [Article(**dict(row)) for row in cursor.fetchall()]

#     def geocode(self, location_name: str) -> Optional[List[float]]:
#         """Geocode location with error handling."""
#         try:
#             location = self.geolocator.geocode(location_name, timeout=10)
#             if location:
#                 return [location.latitude, location.longitude]
#         except GeocoderTimedOut:
#             st.warning(f"Geocoding timed out for location: {location_name}")
#         except Exception as e:
#             st.error(f"Error geocoding location {location_name}: {e}")
#         return None

#     # def create_score_distribution_chart(self, articles: List[Article]) -> go.Figure:
#     #     """Create a scatter plot of novelty vs heat scores."""
#     #     df = pd.DataFrame([
#     #         {
#     #             'title': article.title,
#     #             'novelty_score': article.novelty_score,
#     #             'heat_score': article.heat_score,
#     #             'relevance_score': article.relevance_score
#     #         }
#     #         for article in articles
#     #     ])
        
#     #     fig = go.Figure()
#     #     fig.add_trace(go.Scatter(
#     #         x=df['novelty_score'],
#     #         y=df['heat_score'],
#     #         mode='markers',
#     #         marker=dict(
#     #             size=df['relevance_score'] * 10,
#     #             color=df['relevance_score'],
#     #             colorscale='Viridis',
#     #             showscale=True
#     #         ),
#     #         text=df['title'],
#     #         hoverinfo='text'
#     #     ))
        
#     #     fig.update_layout(
#     #         title='Article Score Distribution',
#     #         xaxis_title='Novelty Score',
#     #         yaxis_title='Heat Score',
#     #         height=600
#     #     )

#     #     return fig


# def main():
#     st.set_page_config(layout="wide")
#     dashboard = DashboardManager()
    
#     # Header
#     col1, col2 = st.columns([1, 4])
#     with col1:
#         st.image(ADNOC_LOGO_URL, width=150)
#     with col2:
#         st.title("Future Foresights Dashboard")
    
#     # Filters
#     col1, col2, col3, col4 = st.columns(4)
#     with col1:
#         source_filter = st.selectbox("Select Source", ["All", "RSS", "arXiv"])
#     with col2:
#         category_options = ["All"] + list(dashboard.PREDEFINED_CATEGORIES.keys())
#         selected_category = st.selectbox("Choose a Category", category_options)
#     with col3:
#         search_query = st.text_input("Search Keywords:", "")
#     with col4:
#         sort_options = {
#             "date": "Publication Date",
#             "relevance": "Relevance Score",
#             "novelty": "Novelty Score",
#             "heat": "Heat Score"
#         }
#         sort_by = st.selectbox("Sort By:", list(sort_options.keys()), format_func=lambda x: sort_options[x])
    
#     # Get and display articles
#     articles = dashboard.get_articles(search_query, source_filter, selected_category, sort_by)
    
#     # Analytics Section
#     st.header("Analytics Dashboard")
#     col1, col2 = st.columns(2)
    
#     # with col1:
#     #     st.plotly_chart(dashboard.create_score_distribution_chart(articles), use_container_width=True)
    
#     with col2:
#         # Summary statistics
#         df = pd.DataFrame([{
#             'novelty_score': article.novelty_score,
#             'heat_score': article.heat_score,
#             'relevance_score': article.relevance_score
#         } for article in articles])
        
#         st.write("### Key Metrics")
#         metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
#         with metrics_col1:
#             st.metric("Average Novelty", f"{df['novelty_score'].mean():.1f}")
#         with metrics_col2:
#             st.metric("Average Heat", f"{df['heat_score'].mean():.1f}")
#         with metrics_col3:
#             st.metric("Average Relevance", f"{df['relevance_score'].mean():.1f}")
    
#     # Articles Section
#     st.header(f"Articles ({len(articles)})")
#     for article in articles:
#         with st.expander(f"{article.title}"):
#             st.write(f"**Source:** {article.source} | **Published:** {article.published_date}")
#             st.write(f"**Relevance Score:** {article.relevance_score:.2f}")
#             st.write(f"**Novelty Score:** {article.novelty_score:.1f}")
#             st.write(f"**Heat Score:** {article.heat_score:.1f}")
            
#             summary_text = article.snippet.split("SUMMARY: ", 1)[-1]
#             st.write("**Summary:**")
            
#             for line in summary_text.split('\n'):
#                 if not line.strip():
#                     st.write("")
#                     continue
                
#                 if re.match(r'^\d+\.\s', line.strip()):
#                     st.markdown(line.strip())
#                 else:
#                     st.markdown(line)
                    
#             st.markdown(f"[Read More]({article.link})")

# if __name__ == "__main__":
#     main()



# import sqlite3
# import streamlit as st
# import subprocess
# import os
# import pandas as pd
# import folium
# from streamlit_folium import folium_static
# from geopy.geocoders import Nominatim
# from geopy.exc import GeocoderTimedOut
# import re

# # Database configuration
# DATABASE = "articles.db"
# ADNOC_LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRjLmGUCFcKxiEkiIl_YMaJ1GL9iPUwIZWojQ&s"

# PREDEFINED_CATEGORIES = {
#     "Oil & Gas Industry": ["oil", "gas", "petroleum"],
#     "Digital Transformation & Automation": ["technology", "innovation", "digital transformation"],
#     "AI & Machine Learning Applications": ["AI", "machine learning", "big data analytics"],
#     "Sustainability & Energy Transition": ["carbon capture", "hydrogen", "renewable energy"],
#     "Advanced Materials & Sensing": ["nanomaterials", "smart sensors", "fiber optic sensing"],
#     "Subsurface & Seismic Technologies": ["seismic inversion", "electromagnetic exploration", "microseismic monitoring"]
# }

# def geocode(location_name):
#     """Convert location name to latitude and longitude using geopy."""
#     geolocator = Nominatim(user_agent="geo_extractor")
#     try:
#         location = geolocator.geocode(location_name, timeout=10)
#         if location:
#             return [location.latitude, location.longitude]
#     except GeocoderTimedOut:
#         return None
#     return None

# # ----------------------
# # Utility DB Functions
# # ----------------------
# def create_table_if_not_exists():
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

# def get_articles(search_query=None, source_filter="All", category="All", sort_by="date"):
#     conn = sqlite3.connect(DATABASE)
#     c = conn.cursor()
#     query_conditions = []
#     query_params = []
    
#     if search_query:
#         query_conditions.append("(title LIKE ? OR snippet LIKE ?)")
#         like_query = f"%{search_query}%"
#         query_params.extend([like_query, like_query])
    
#     if source_filter != "All":
#         if source_filter == "RSS":
#             query_conditions.append("source != 'arXiv'")
#         elif source_filter == "arXiv":
#             query_conditions.append("source = 'arXiv'")
    
#     if category != "All":
#         keywords = PREDEFINED_CATEGORIES.get(category, [])
#         if keywords:
#             keyword_conditions = " OR ".join(["title LIKE ? OR snippet LIKE ?" for _ in keywords])
#             query_conditions.append(f"({keyword_conditions})")
#             for kw in keywords:
#                 query_params.extend([f"%{kw}%", f"%{kw}%"])
    
#     base_query = """
#         SELECT id, title, link, snippet, published_date, source, relevance_score, novelty_score, heat_score, locations
#         FROM articles
#     """
    
#     if query_conditions:
#         base_query += " WHERE " + " AND ".join(query_conditions)
    
#     order_by = "published_date DESC" if sort_by == "date" else "relevance_score DESC"
#     base_query += f" ORDER BY {order_by}"
    
#     c.execute(base_query, query_params)
#     rows = c.fetchall()
#     conn.close()
#     return rows

# def display_geospatial_map(filtered_articles):
#     """Display a map with locations where technology is trending based on filtered articles."""
#     m = folium.Map(location=[20, 0], zoom_start=2)
    
#     for article in filtered_articles:
#         # Unpack relevant data; expected order: id, title, link, snippet, published_date, source, relevance_score, novelty_score, heat_score, locations
#         _, title, _, _, _, _, _, _, _, locations = article  
#         if locations:
#             for loc in locations.split(", "):
#                 coordinates = geocode(loc)
#                 if coordinates:
#                     folium.Marker(location=coordinates, popup=title).add_to(m)
#     folium_static(m)

# def main():
#     st.image(ADNOC_LOGO_URL, width=150)
#     st.title("Future Foresights Dashboard")
#     create_table_if_not_exists()
    
#     source_filter = st.selectbox("Select Source", ["All", "RSS", "arXiv"], help="Filter articles by their source")
#     category_options = ["All"] + list(PREDEFINED_CATEGORIES.keys())
#     selected_category = st.selectbox("Choose a Category", category_options)
#     search_query = st.text_input("Search by any keyword or partial title:", "")
    
#     # Default sorting is by relevance score; adjust as needed.
#     articles = get_articles(search_query, source_filter, selected_category, sort_by="relevance")
    
#     st.write(f"**Found {len(articles)} articles** matching your criteria:")
#     for article in articles:
#         # Unpack the returned tuple according to the updated schema.
#         id, title, link, snippet, published_date, source, relevance_score, novelty_score, heat_score, locations = article
#         st.subheader(title)
#         st.write(f"**Source:** {source} | **Published:** {published_date}")
#         st.write(f"**Relevance Score:** {relevance_score:.2f} | **Novelty Score:** {novelty_score:.2f} | **Heat Score:** {heat_score:.2f}")
        
#         # If the snippet contains the 'SUMMARY:' marker, split it out.
#         if "SUMMARY:" in snippet:
#             summary_text = snippet.split("SUMMARY:", 1)[1].strip()
#         else:
#             summary_text = snippet
#         st.write("**Summary:**")
#         for line in summary_text.splitlines():
#             if not line.strip():
#                 st.write("")
#             elif re.match(r'^\d+\.\s', line.strip()):
#                 st.markdown(line.strip())
#             else:
#                 st.markdown(line)
#         st.markdown(f"[Read More]({link})", unsafe_allow_html=True)
#         st.write("---")
    
#     # Uncomment the following lines to enable geospatial mapping:
#     # st.header("Geospatial Insights")
#     # display_geospatial_map(articles)

# if __name__ == "__main__":
    main()
