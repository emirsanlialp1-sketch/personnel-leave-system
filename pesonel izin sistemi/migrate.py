import sqlite3

def migrate():
    conn = sqlite3.connect("leave_management.db")
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE announcements ADD COLUMN image_path TEXT")
        print("image_path sütunu başarıyla eklendi.")
    except sqlite3.OperationalError:
        print("Sütun zaten mevcut veya tablo yok.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
