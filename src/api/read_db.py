import sqlite3
from pathlib import Path

con = sqlite3.connect(Path(__file__).resolve().parent / "data" / "database.db")

cursor = con.cursor()
cursor.execute("""
SELECT * FROM Data ORDER BY QUALITY_EVALUATION DESC LIMIT 50
""")

for entry in cursor.fetchall():
    print(entry, "\n")

print(cursor.description)
