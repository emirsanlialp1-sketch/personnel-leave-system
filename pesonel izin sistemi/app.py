import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
from PIL import Image

# --- CONFIG ---
st.set_page_config(page_title="Personel İzin Sistemi", layout="wide", initial_sidebar_state="expanded")

# --- DATABASE FUNCTIONS ---
DB_NAME = "leave_management.db"

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def login_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user

def get_user_leaves(user_id):
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT start_date, end_date, description, status, leave_type FROM leaves WHERE user_id = ?", conn, params=(user_id,))
    conn.close()
    return df

def submit_leave(user_id, start_date, end_date, description):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO leaves (user_id, start_date, end_date, description, status, leave_type) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, str(start_date), str(end_date), description, "Beklemede", "Yıllık İzin"))
    conn.commit()
    conn.close()

def submit_sick_report(user_id, image_data, description):
    if not os.path.exists("reports"):
        os.makedirs("reports")
    
    file_path = f"reports/sick_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    with open(file_path, "wb") as f:
        f.write(image_data.getbuffer())
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO sick_reports (user_id, image_path, description, date) VALUES (?, ?, ?, ?)",
              (user_id, file_path, description, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

# --- CSS STYLING ---
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #007bff;
        color: white;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #0056b3;
        border: none;
    }
    .sidebar .sidebar-content {
        background-image: linear-gradient(#2e7bcf,#2e7bcf);
        color: white;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        color: #333; /* Dark text for visibility */
    }
    .metric-card p {
        color: #555;
        font-size: 1.1em;
        font-weight: 500;
    }
    h1, h2, h3 {
        color: #1e3d59;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

def get_pending_leaves():
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT l.id, u.full_name, u.department, l.start_date, l.end_date, l.description, l.leave_type 
        FROM leaves l 
        JOIN users u ON l.user_id = u.id 
        WHERE l.status = 'Beklemede'
    """, conn)
    conn.close()
    return df

def approve_leave(leave_id):
    conn = get_db_connection()
    c = conn.cursor()
    # Get leave details to calculate days
    c.execute("SELECT user_id, start_date, end_date FROM leaves WHERE id = ?", (leave_id,))
    leave = c.fetchone()
    if leave:
        user_id, start, end = leave
        d1 = datetime.strptime(start, "%Y-%m-%d")
        d2 = datetime.strptime(end, "%Y-%m-%d")
        days = (d2 - d1).days + 1
        
        # Update leave status
        c.execute("UPDATE leaves SET status = 'Onaylandı' WHERE id = ?", (leave_id,))
        # Deduct from user's remaining leave
        c.execute("UPDATE users SET remaining_leave = remaining_leave - ? WHERE id = ?", (days, user_id))
        
    conn.commit()
    conn.close()

def reject_leave(leave_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE leaves SET status = 'Reddedildi' WHERE id = ?", (leave_id,))
    conn.commit()
    conn.close()

def send_announcement(sender_id, target_user_id, title, message, image_data=None):
    image_path = None
    if image_data:
        if not os.path.exists("announcements"):
            os.makedirs("announcements")
        image_path = f"announcements/ann_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        with open(image_path, "wb") as f:
            f.write(image_data.getbuffer())

    conn = get_db_connection()
    c = conn.cursor()
    # Ensure target_user_id is None or int
    t_id = int(target_user_id) if target_user_id is not None else None
    c.execute("INSERT INTO announcements (sender_id, target_user_id, title, message, image_path, date) VALUES (?, ?, ?, ?, ?, ?)",
              (sender_id, t_id, title, message, image_path, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def get_announcements(user_id):
    conn = get_db_connection()
    # Get general announcements (target_user_id IS NULL) and personal ones
    df = pd.read_sql_query("""
        SELECT title, message, image_path, date 
        FROM announcements 
        WHERE target_user_id IS NULL OR target_user_id = ?
        ORDER BY id DESC
    """, conn, params=(user_id,))
    conn.close()
    return df

def get_all_users():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT id, full_name, department FROM users WHERE username != 'yonetici'", conn)
    conn.close()
    return df

def get_sent_announcements(is_global=True):
    conn = get_db_connection()
    if is_global:
        df = pd.read_sql_query("""
            SELECT title, message, image_path, date 
            FROM announcements 
            WHERE target_user_id IS NULL
            ORDER BY id DESC
        """, conn)
    else:
        df = pd.read_sql_query("""
            SELECT a.title, a.message, a.image_path, a.date, u.full_name as target_person, u.department as target_dept
            FROM announcements a
            JOIN users u ON a.target_user_id = u.id
            WHERE a.target_user_id IS NOT NULL
            ORDER BY a.id DESC
        """, conn)
    conn.close()
    return df

# --- UI LOGIC ---
if not st.session_state.logged_in:
    # LOGIN PAGE
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.title(" Obel Cıvata")
        st.subheader("Personel İzin Sistemi")
        st.markdown("</div>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            submit = st.form_submit_button("Giriş Yap")
            
            if submit:
                user = login_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_data = {
                        "id": user[0],
                        "username": user[1],
                        "full_name": user[3],
                        "department": user[4],
                        "remaining_leave": user[5]
                    }
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")
    st.info("Demo Girişi: 'personel' / '1234' veya 'yonetici' / 'admin'")

else:
    # DASHBOARD
    user_data = st.session_state.user_data
    is_admin = user_data['username'] == 'yonetici'
    
    st.sidebar.title(f"👋 {user_data['full_name']}")
    st.sidebar.markdown(f"**Departman:** {user_data['department']}")
    
    menu_options = ["Profil", "Duyurular", "İzin Talebi", "Raporlu/Hasta"]
    if is_admin:
        menu_options.append("Onay Bekleyenler")
        menu_options.append("Duyuru Yap")
        menu_options.append("Geçmiş Global Duyurular")
        menu_options.append("Geçmiş Özel Duyurular")
        
    page = st.sidebar.radio("Menü", menu_options)
    
    if st.sidebar.button("🚪 Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()

    if page == "Profil":
        st.header("👤 Personel Profili")
        
        # Refresh user data for latest leave balance
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT remaining_leave FROM users WHERE id = ?", (user_data['id'],))
        current_leave = c.fetchone()[0]
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><h3>İsim Soyisim</h3><p>{user_data['full_name']}</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><h3>Kalan İzin</h3><p style='font-size:24px; color:#28a745; font-weight:bold;'>{current_leave} Gün</p></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><h3>Departman</h3><p>{user_data['department']}</p></div>", unsafe_allow_html=True)
            
        st.divider()
        st.subheader("📋 İzin Geçmişi")
        leaves_df = get_user_leaves(user_data['id'])
        if not leaves_df.empty:
            # Format columns for display
            leaves_df.columns = ['Başlangıç', 'Bitiş', 'Açıklama', 'Durum', 'Tür']
            st.table(leaves_df)
        else:
            st.info("Henüz bir izin kaydınız bulunmamaktadır.")

    elif page == "İzin Talebi":
        st.header("📅 İzin Talebi Oluştur")
        with st.form("leave_form"):
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Başlangıç Tarihi")
            with col2:
                end_date = st.date_input("Bitiş Tarihi")
                
            description = st.text_area("İzin Açıklaması", placeholder="İzin alma sebebinizi kısaca açıklayınız...")
            
            submit_btn = st.form_submit_button("Talebi Gönder")
            
            if submit_btn:
                if end_date < start_date:
                    st.error("Bitiş tarihi başlangıç tarihinden önce olamaz!")
                else:
                    submit_leave(user_data['id'], start_date, end_date, description)
                    st.success("İzin talebiniz başarıyla gönderildi. Yönetici onayı bekleniyor.")

    elif page == "Raporlu/Hasta":
        st.header("🏥 Sağlık Raporu Yükleme")
        st.info("Doktor raporunuzun fotoğrafını buradan yükleyebilirsiniz.")
        
        with st.form("sick_form"):
            uploaded_file = st.file_uploader("Rapor Dosyası (PNG, JPG, JPEG)", type=["png", "jpg", "jpeg"])
            sick_desc = st.text_area("Açıklama", placeholder="Hastalık durumu hakkında kısa bilgi...")
            
            submit_sick = st.form_submit_button("Raporu Kaydet")
            
            if submit_sick:
                if uploaded_file is not None:
                    submit_sick_report(user_data['id'], uploaded_file, sick_desc)
                    st.success("Raporunuz sisteme başarıyla yüklendi.")
                else:
                    st.warning("Lütfen bir dosya seçiniz!")

    elif page == "Duyurular":
        st.header("📢 Duyurular")
        ann_df = get_announcements(user_data['id'])
        if not ann_df.empty:
            for index, row in ann_df.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style='background-color: white; padding: 5px 10px; border-radius: 6px; border-left: 3px solid #007bff; margin-bottom: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>
                        <h5 style='margin-top: 0; margin-bottom: 2px; color: #1e3d59; font-size: 0.95em;'>{row['title']}</h5>
                        <p style='color: #555; font-size: 0.85em; margin-bottom: 0;'>{row['message']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if row['image_path'] and isinstance(row['image_path'], str) and os.path.exists(row['image_path']):
                        st.image(row['image_path'], width=140)
                    st.markdown(f"<small style='color: #888;'>📅 {row['date']}</small><br><br>", unsafe_allow_html=True)
        else:
            st.info("Henüz bir duyuru bulunmuyor.")

    elif page == "Duyuru Yap":
        st.header("✍️ Yeni Duyuru Yayınla")
        users_df = get_all_users()
        
        target_type = st.radio("Duyuru Kime?", ["Herkese", "Şahsi (Özel)"], horizontal=True)
        
        target_user_id = None
        filtered_users = users_df
        
        if target_type == "Şahsi (Özel)":
            st.divider()
            search_query = st.text_input("🔍 Personel Ara (İsim veya Soyisim)", placeholder="Aramak istediğiniz kişinin adını yazın...")
            
            if search_query:
                filtered_users = users_df[users_df['full_name'].str.contains(search_query, case=False)]
            
            # Listelenen personelleri göster
            if not filtered_users.empty:
                st.write("**Eşleşen Personeller:**")
                # İsim Soyisim ve Departman formatında liste gösterimi
                display_list = filtered_users.apply(lambda x: f"{x['full_name']} - {x['department']}", axis=1).tolist()
                for item in display_list[:5]: # İlk 5 kişiyi listele
                    st.caption(f"📌 {item}")
                if len(display_list) > 5:
                    st.caption(f"... ve {len(display_list)-5} kişi daha.")
            else:
                st.warning("Eşleşen personel bulunamadı.")

        st.divider()
        with st.form("announcement_form"):
            selected_user_name = None
            if target_type == "Şahsi (Özel)":
                user_options = {f"{row['full_name']} ({row['department']})": row['id'] for _, row in filtered_users.iterrows()}
                if user_options:
                    selected_user_name = st.selectbox("Gönderilecek Personeli Seçin", options=list(user_options.keys()))
                else:
                    st.error("Lütfen yukarıdaki arama alanından geçerli bir personel bulun.")
            
            title = st.text_input("Duyuru Başlığı")
            message = st.text_area("Duyuru Mesajı")
            ann_image = st.file_uploader("Görsel Ekle (Opsiyonel)", type=["png", "jpg", "jpeg"])
            
            submit_ann = st.form_submit_button("Duyuruyu Yayınla")
            
            if submit_ann:
                if title and message:
                    final_target_id = None
                    if target_type == "Şahsi (Özel)":
                        if selected_user_name:
                            final_target_id = user_options[selected_user_name]
                        else:
                            st.error("Lütfen bir personel seçin!")
                            st.stop()
                    
                    send_announcement(user_data['id'], final_target_id, title, message, ann_image)
                    st.success("Duyuru başarıyla yayınlandı.")
                else:
                    st.warning("Lütfen başlık ve mesaj alanlarını doldurun!")

    elif page == "Geçmiş Global Duyurular":
        st.header("🌎 Gönderilen Global Duyurular")
        df = get_sent_announcements(is_global=True)
        if not df.empty:
            for _, row in df.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style='background-color: #e3f2fd; padding: 5px 10px; border-radius: 6px; border-left: 3px solid #1e88e5; margin-bottom: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>
                        <h5 style='color: #0d47a1; margin-bottom: 2px; font-size: 0.95em;'>{row['title']}</h5>
                        <p style='color: #212121; font-size: 0.85em; margin-bottom: 3px;'>{row['message']}</p>
                        <small style='color: #546e7a; font-size: 0.75em;'>📅 {row['date']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    if row['image_path'] and os.path.exists(row['image_path']):
                        st.image(row['image_path'], width=140)
        else:
            st.info("Henüz global bir duyuru yapmadınız.")

    elif page == "Geçmiş Özel Duyurular":
        st.header("👤 Gönderilen Şahsi Duyurular")
        df = get_sent_announcements(is_global=False)
        if not df.empty:
            for _, row in df.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style='background-color: #f3e5f5; padding: 5px 10px; border-radius: 6px; border-left: 3px solid #8e24aa; margin-bottom: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'>
                        <h5 style='color: #4a148c; margin-bottom: 2px; font-size: 0.95em;'>{row['title']}</h5>
                        <p style='color: #4a148c; font-weight: bold; font-size: 0.8em; margin-bottom: 2px;'>🎯 Alıcı: {row['target_person']}</p>
                        <p style='color: #212121; font-size: 0.85em; margin-bottom: 3px;'>{row['message']}</p>
                        <small style='color: #5e35b1; font-size: 0.75em;'>📅 {row['date']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    if row['image_path'] and os.path.exists(row['image_path']):
                        st.image(row['image_path'], width=140)
        else:
            st.info("Henüz şahsi bir duyuru yapmadınız.")

    elif page == "Onay Bekleyenler":
        st.header("⚖️ Onay Bekleyen İzin Talepleri")
        pending_df = get_pending_leaves()
        
        if not pending_df.empty:
            for index, row in pending_df.iterrows():
                with st.expander(f"{row['full_name']} ({row['department']}) - {row['leave_type']}"):
                    st.write(f"**Departman:** {row['department']}")
                    st.write(f"**Tarih:** {row['start_date']} / {row['end_date']}")
                    st.write(f"**Açıklama:** {row['description']}")
                    
                    col1, col2 = st.columns(2)
                    if col1.button("Onayla", key=f"app_{row['id']}"):
                        approve_leave(row['id'])
                        st.success(f"Talep onaylandı.")
                        st.rerun()
                    if col2.button("Reddet", key=f"rej_{row['id']}"):
                        reject_leave(row['id'])
                        st.warning(f"Talep reddedildi.")
                        st.rerun()
        else:
            st.success("Bekleyen izin talebi bulunmamaktadır.")

