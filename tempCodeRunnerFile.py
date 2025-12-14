# LOCAL (only works if DB is started)
test_oracle_connection("localhost", "c##uni1", "user")

# REMOTE
test_oracle_connection("192.168.1.2", "c##uni1", "u")