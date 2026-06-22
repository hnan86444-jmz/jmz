import sqlite3

conn = sqlite3.connect("travel_agency.db")
cur = conn.cursor()

for table in ["flights", "hotels", "rental_cars"]:
    print(f"\n--- {table} ---")
    cur.execute(f"PRAGMA table_info({table});")
    for row in cur.fetchall():
        print(row)