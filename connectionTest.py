import oracledb

try:
    conn = oracledb.connect(user="c##uni1", password="user", dsn="localhost/FREE")
    print("✅ Connected to Oracle successfully!")
    conn.close()
except Exception as e:
    print("❌ Error:", e)
