import oracledb
import platform
import subprocess

def ping_host(host):
    """
    Returns True if the target host replies to ping.
    """
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(
            ["ping", param, "1", host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def test_oracle_connection(host, user="c##uni1", password="user", service="FREE"):
    """
    Tests connection to Oracle on the specified host.
    """
    dsn = f"{host}/{service}"
    try:
        conn = oracledb.connect(user=user, password=password, dsn=dsn)
        print(f"✅ Connected to Oracle on {host} successfully!")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Oracle connection failed for {host}: {e}")
        return False


# -----------------------------
# TEST LOCAL
# -----------------------------
print("\n🔵 Testing LOCAL Oracle connection...")
test_oracle_connection("localhost")

# -----------------------------
# TEST OTHER LAPTOP
# -----------------------------
other_laptop_ip = "192.168.1.15"  # 🔹 CHANGE THIS TO TARGET IP

print(f"\n🔵 Pinging {other_laptop_ip}...")
if ping_host(other_laptop_ip):
    print(f"✅ Host {other_laptop_ip} is reachable!")
    print("🔵 Testing Oracle connection on that laptop...")
    test_oracle_connection(other_laptop_ip)
else:
    print(f"❌ Host {other_laptop_ip} is NOT reachable (ping failed).")

