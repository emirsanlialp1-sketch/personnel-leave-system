import sqlite3

def add_user():
    conn = sqlite3.connect("leave_management.db")
    c = conn.cursor()
    
    new_user = ("zeynep", "5678", "Zeynep Kaya", "Lojistik", 12)
    
    try:
        c.execute("INSERT INTO users (username, password, full_name, department, remaining_leave) VALUES (?, ?, ?, ?, ?)", new_user)
        conn.commit()
        print(f"Başarılı: '{new_user[2]}' kullanıcısı sisteme eklendi.")
        print(f"Kullanıcı Adı: {new_user[0]}")
        print(f"Şifre: {new_user[1]}")
    except sqlite3.IntegrityError:
        print("Hata: Bu kullanıcı adı zaten mevcut.")
    
    conn.close()

if __name__ == "__main__":
    add_user()
