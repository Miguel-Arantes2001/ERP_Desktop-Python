import sqlite3



conn = sqlite3.connect("erp.db")  
cursor = conn.cursor()

cursor.execute("SELECT id, email FROM users")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
