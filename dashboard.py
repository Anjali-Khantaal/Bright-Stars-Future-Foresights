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
    "General Oil & Gas Industry Terms": [
        "oil", "gas", "petroleum", "refining", "drilling"
    ],
    "Digital Transformation & Automation": [
        "digital transformation", "automation", "robotics", "iot", "industry 4.0"
    ],
    "AI & Machine Learning Applications": [
        "machine learning", "ai", "artificial intelligence", "neural network", "deep learning"
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
def get_articles(search_query=None):
    """
    Retrieves articles from the database.
    If a search_query is provided, it does a basic LIKE match
    on the title/snippet fields.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    if search_query:
        query = """
        SELECT id, title, link, snippet, published_date, source
        FROM articles
        WHERE title LIKE ? OR snippet LIKE ?
        ORDER BY published_date DESC
        """
        like_query = f"%{search_query}%"
        c.execute(query, (like_query, like_query))
    else:
        query = """
        SELECT id, title, link, snippet, published_date, source
        FROM articles
        ORDER BY published_date DESC
        """
        c.execute(query)

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

    # Button to fetch new data (optional: runs fetch_data.py if environment allows)
    if st.sidebar.button("Fetch Latest Articles"):
        st.sidebar.write("Attempting to fetch data from external sources...")
        # Clear the cache so new data is reflected immediately
        st.cache_data.clear()

        try:
            # Adjust the Python path if needed for your environment
            result = subprocess.run(
                ["python", "fetch_data.py"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                st.sidebar.success("Data fetched successfully! Reload the page or navigate to see the latest articles.")
            else:
                st.sidebar.error(f"An error occurred while fetching data:\n{result.stderr}")
        except FileNotFoundError:
            st.sidebar.error("Could not find or run fetch_data.py. Please run it manually.")
        st.sidebar.info("In production, this step can be automated or run on a schedule.")

    # Predefined categories (add "All" on top)
    category_options = ["All"] + list(PREDEFINED_CATEGORIES.keys())
    selected_category = st.sidebar.selectbox("Choose a Category", category_options)

    # Search bar
    search_query = st.sidebar.text_input("Search by any keyword or partial title:", "")

    # ---------------
    # MAIN PAGE LOGIC
    # ---------------
    # If user selects a category or enters a query, switch off home mode
    if selected_category != "All" or search_query:
        st.session_state["home_mode"] = False

    if st.session_state["home_mode"]:
        # Show welcome message instead of article results
        st.markdown("""
        ### Welcome to the Future Foresights Dashboard
        - **Click "Fetch Latest Articles"** (in the sidebar) to update the database with new items.
        - **Use the "Choose a Category" dropdown** or type a **search query** to explore relevant articles.
        """)
        # Stop execution to avoid showing articles
        st.stop()

    # If we're not in home mode, show instructions and articles
    st.markdown("""
    **How to use this dashboard**:
    1. **Select a Category** (in the sidebar) for a quick filter, e.g., "AI & Machine Learning Applications".
    2. **Enter a search query** for partial matches in the title or snippet.
    3. **Fetch Latest Articles** to refresh the database with new feeds from RSS/arXiv.
    """)

    # Retrieve & filter data
    articles = get_articles(search_query)
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
