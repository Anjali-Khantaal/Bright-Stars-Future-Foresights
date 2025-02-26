import sqlite3

def drop_and_recreate_locations_column(db_path="articles.db"):
    """
    Drops the 'locations' column by recreating the table without it,
    then re-adds an empty 'locations' column.
    WARNING: This permanently removes any existing data in 'locations'.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1) Rename the original table
    cursor.execute("ALTER TABLE articles RENAME TO articles_old")

    # 2) Create a new table without the 'locations' column
    #    Adjust the schema below if your 'articles' table has different or extra columns.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT UNIQUE,
            snippet TEXT,
            relevance_score REAL,
            novelty_score TEXT,
            heat_score TEXT,
            published_date TEXT,
            source TEXT,
            full_text TEXT
        )
    """)

    # 3) Copy all columns except 'locations' from the old table
    cursor.execute("""
        INSERT INTO articles_new (id, title, link, snippet, relevance_score, 
                                  novelty_score, heat_score, published_date, 
                                  source, full_text)
        SELECT id, title, link, snippet, relevance_score, 
               novelty_score, heat_score, published_date, 
               source, full_text
        FROM articles_old
    """)
    conn.commit()

    # 4) Drop the old table
    cursor.execute("DROP TABLE articles_old")
    conn.commit()

    # 5) Rename the new table to the original name
    cursor.execute("ALTER TABLE articles_new RENAME TO articles")
    conn.commit()

    # 6) Add the 'locations' column as a fresh TEXT field
    cursor.execute("ALTER TABLE articles ADD COLUMN locations TEXT")
    conn.commit()

    conn.close()
    print("Dropped and recreated the 'locations' column successfully.")


def extract_geospatial_info(text):
    """
    Extract country names from the provided text using simple substring matching.
    You can expand or modify KNOWN_COUNTRIES and COUNTRY_ALIASES as needed.
    """
    KNOWN_COUNTRIES = [
        "United States", "United Kingdom", "Saudi Arabia", "China",
        "India", "Germany", "France", "United Arab Emirates", "Brazil", "Canada"
    ]
    COUNTRY_ALIASES = {
        "US": "United States",
        "USA": "United States",
        "UAE": "United Arab Emirates",
        "UK": "United Kingdom",
        "KSA": "Saudi Arabia"
    }
    
    found_countries = set()
    if text:
        text_lower = text.lower()
        # Check for full country names
        for country in KNOWN_COUNTRIES:
            if country.lower() in text_lower:
                found_countries.add(country)
        # Check for aliases
        for alias, full_name in COUNTRY_ALIASES.items():
            if alias.lower() in text_lower:
                found_countries.add(full_name)
    
    return list(found_countries)


def update_article_locations(db_path="articles.db"):
    """
    Iterates through all articles in the database, 
    combines 'snippet' + 'full_text' for each article,
    extracts country information, and updates the 'locations' column.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Retrieve all articles (id, snippet, full_text)
    cursor.execute("SELECT id, snippet, full_text FROM articles")
    rows = cursor.fetchall()

    updated_count = 0
    for article_id, snippet, full_text in rows:
        # Combine snippet + full_text for broader matching
        combined_text = (snippet or "") + " " + (full_text or "")
        countries = extract_geospatial_info(combined_text)
        print("Article ID:", article_id)
        print("Text:", combined_text[:200])  # Show first 200 chars
        print("Matched Countries:", countries)
        # Convert the list of countries to a comma-separated string
        locations_str = ", ".join(countries) if countries else ""

        # Update the database with the extracted locations
        cursor.execute("UPDATE articles SET locations = ? WHERE id = ?", (locations_str, article_id))
        updated_count += 1

    conn.commit()
    conn.close()
    print(f"Updated 'locations' for {updated_count} articles.")


if __name__ == "__main__":
    db_file = "articles.db"  # Update if your DB is named differently or in a different path

    # 1) Drop the existing 'locations' column by recreating the table
    drop_and_recreate_locations_column(db_path=db_file)

    # 2) Fill the new 'locations' column from combined snippet+full_text
    update_article_locations(db_path=db_file)
