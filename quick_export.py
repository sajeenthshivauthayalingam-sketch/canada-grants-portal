import sqlite3
import pandas as pd

conn = sqlite3.connect("grants.db")
df = pd.read_sql_query("SELECT * FROM scholarships", conn)
df.to_csv("scholarships_export.csv", index=False)
conn.close()
