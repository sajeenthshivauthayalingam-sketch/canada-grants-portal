import sqlite3

conn = sqlite3.connect("grants.db")
cur = conn.cursor()
cur.execute("SELECT name, source_url FROM scholarships LIMIT 5;")
rows = cur.fetchall()
print(rows)
