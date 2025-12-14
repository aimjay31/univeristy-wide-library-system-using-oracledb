import oracledb

def test_oracle_connection(host, user, password, service="FREE", port=1521):
    dsn = f"{host}:{port}/{service}"
    try:
        conn = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn
        )
        print(f"✅ Connected to Oracle → {host}")
        conn.close()
    except oracledb.Error as e:
        print(f"❌ Connection failed → {host}")
        print(e)


# LOCAL (only works if DB is started)
test_oracle_connection("localhost", "c##uni1", "user")

# REMOTE
test_oracle_connection("192.168.1.2", "c##uni1", "u")
