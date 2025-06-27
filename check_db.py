import sqlite3

# Connect to database
conn = sqlite3.connect('chat_history.db')
cursor = conn.cursor()

# Get table schema
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Current database schema:")
for table in tables:
    print(table[0])

# Get columns of chats table
cursor.execute("PRAGMA table_info(chats)")
columns = cursor.fetchall()
print("\nColumns in chats table:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()
