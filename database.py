import sqlite3
import datetime

class DatabaseManager:
    def __init__(self, db_name="lift_system.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup_tables()

    def setup_tables(self):
        # Create Tables for Users and Access Logs
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users
                             (id INTEGER PRIMARY KEY, name TEXT, role TEXT, allowed_floors TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS access_logs
                             (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, floor INTEGER, timestamp TEXT)''')
        self.conn.commit()

    def add_user(self, name, role, allowed_floors):
        # allowed_floors is a comma separated string e.g. "0,1,2"
        self.cursor.execute("INSERT INTO users (name, role, allowed_floors) VALUES (?, ?, ?)", 
                            (name, role, allowed_floors))
        self.conn.commit()

    def get_user(self, name):
        self.cursor.execute("SELECT * FROM users WHERE name=?", (name,))
        return self.cursor.fetchone()

    def log_access(self, user_id, name, floor):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO access_logs (user_id, name, floor, timestamp) VALUES (?, ?, ?, ?)",
                            (user_id, name, floor, timestamp))
        self.conn.commit()
