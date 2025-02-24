import sqlite3

conn = sqlite3.connect("articles.db")
c = conn.cursor()
c.execute("SELECT id, title, snippet FROM articles WHERE snippet IS NOT NULL LIMIT 10;")
rows = c.fetchall()
conn.close()

for row in rows:
    print(row)  # Print title and snippet
