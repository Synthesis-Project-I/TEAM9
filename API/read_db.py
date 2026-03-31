import sqlite3

con = sqlite3.connect(".data/database.db")

cursor = con.cursor()
cursor.execute("""
SELECT * FROM Data ORDER BY QUALITY_EVALUATION DESC LIMIT 50
""")

for entry in cursor.fetchall():
    print(entry, "\n")

print(cursor.description)
