import sqlite3
import os

DB_NAME = "leave_management.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  full_name TEXT,
                  department TEXT,
                  remaining_leave INTEGER)''')
    
    # Leaves table
    c.execute('''CREATE TABLE IF NOT EXISTS leaves
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  start_date TEXT,
                  end_date TEXT,
                  description TEXT,
                  status TEXT,
                  leave_type TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # Sick reports table
    c.execute('''CREATE TABLE IF NOT EXISTS sick_reports
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  image_path TEXT,
                  description TEXT,
                  date TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # Announcements table
    c.execute('''CREATE TABLE IF NOT EXISTS announcements
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender_id INTEGER,
                  target_user_id INTEGER, -- NULL for all, specific ID for private
                  title TEXT,
                  message TEXT,
                  image_path TEXT,
                  date TEXT,
                  FOREIGN KEY(sender_id) REFERENCES users(id))''')
    
    # Add a demo user if empty
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, full_name, department, remaining_leave) VALUES (?, ?, ?, ?, ?)",
                  ("personel", "1234", "Ahmet Yılmaz", "Üretim", 15))
        c.execute("INSERT INTO users (username, password, full_name, department, remaining_leave) VALUES (?, ?, ?, ?, ?)",
                  ("yonetici", "admin", "Mehmet Demir", "Yönetim", 20))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
