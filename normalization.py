import sqlite3

def main():
    db_file = 'articles.db'
    table_name = 'articles'

    # Connect to the database
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # STEP 1: Drop the current relevance_score column.
    # Note: This requires SQLite version 3.35.0 or higher.
    try:
        cur.execute(f"ALTER TABLE {table_name} DROP COLUMN relevance_score;")
        print("Dropped column 'relevance_score'.")
    except sqlite3.OperationalError as e:
        print("Error dropping column 'relevance_score' (it may not exist or your SQLite version may not support dropping columns):", e)

    # STEP 2: Recreate the relevance_score column.
    try:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN relevance_score REAL;")
        print("Added column 'relevance_score'.")
    except sqlite3.OperationalError as e:
        print("Error adding column 'relevance_score':", e)
        conn.close()
        return

    # STEP 3: Normalize the scores from relevance_score_unnormalised.
    # The normalization rescales each raw score to a 0–100 range by using:
    #     normalized = (raw_score / max_raw_score) * 100
    cur.execute(f"SELECT MAX(relevance_score_unnormalised) FROM {table_name};")
    result = cur.fetchone()
    max_raw = result[0] if result and result[0] is not None else 0

    if max_raw == 0:
        print("Maximum raw relevance score is 0. All normalized scores will be set to 0.")
        cur.execute(f"UPDATE {table_name} SET relevance_score = 0;")
    else:
        # Retrieve each article's id and raw score.
        cur.execute(f"SELECT id, relevance_score_unnormalised FROM {table_name};")
        rows = cur.fetchall()

        # Update each row with its normalized relevance score.
        for row in rows:
            article_id, raw_score = row
            normalized_score = (raw_score / max_raw) * 100
            cur.execute(
                f"UPDATE {table_name} SET relevance_score = ? WHERE id = ?;",
                (normalized_score, article_id)
            )
        print("Normalized relevance scores updated for all articles.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()