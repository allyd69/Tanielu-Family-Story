# app.py
import streamlit as st
import sqlite3
import base64
from PIL import Image
import io
import datetime
import hashlib
import os

# Database setup
DB_FILE = "tanielu_family_story.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Photos table
    c.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            date DATE,
            location TEXT,
            people TEXT,  -- comma-separated user ids
            tags TEXT,    -- comma-separated tags
            uploader_id INTEGER,
            image_data TEXT,  -- base64 encoded image
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploader_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    # Add demo accounts if not exist
    demo_users = [
        ('john@family.com', 'demo123', 'Dad'),
        ('mary@family.com', 'demo123', 'Mum'),
        ('sarah@family.com', 'demo123', 'Daughter')
    ]
    for email, pw, role in demo_users:
        hashed_pw = hashlib.sha256(pw.encode()).hexdigest()
        try:
            c.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (email, hashed_pw, role))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Already exists
    conn.close()

init_db()

# Helper functions
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def authenticate(email, pw):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    hashed_pw = hash_password(pw)
    c.execute("SELECT id, role FROM users WHERE email = ? AND password = ?", (email, hashed_pw))
    user = c.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, email, role FROM users")
    users = c.fetchall()
    conn.close()
    return users

def save_photo(title, desc, date, loc, people, tags, uploader_id, image_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    people_str = ','.join(map(str, people)) if people else ''
    tags_str = ','.join(tags) if tags else ''
    c.execute('''
        INSERT INTO photos (title, description, date, location, people, tags, uploader_id, image_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, desc, date, loc, people_str, tags_str, uploader_id, image_data))
    conn.commit()
    conn.close()

def get_all_photos():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM photos ORDER BY date DESC, created_at DESC")
    photos = c.fetchall()
    conn.close()
    return photos

def search_photos(query):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    like_query = f"%{query}%"
    c.execute('''
        SELECT * FROM photos 
        WHERE title LIKE ? OR description LIKE ? OR location LIKE ? OR tags LIKE ? OR people LIKE ?
        ORDER BY date DESC, created_at DESC
    ''', (like_query, like_query, like_query, like_query, like_query))
    photos = c.fetchall()
    conn.close()
    return photos

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT email, role FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def resize_image(image, max_size=(800, 800)):
    img = Image.open(io.BytesIO(image))
    img.thumbnail(max_size)
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return buffered.getvalue()

def base64_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

# Unique feature: Family Role Map - a simple text-based family tree view
def get_family_role_map():
    users = get_all_users()
    role_map = {}
    for uid, email, role in users:
        if role not in role_map:
            role_map[role] = []
        role_map[role].append(email)
    return role_map

# App
st.set_page_config(page_title="Tanielu Family Story", layout="wide")

if 'user' not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.header("Login")
        email = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            user = authenticate(email, pw)
            if user:
                st.session_state.user = {'id': user[0], 'email': email, 'role': user[1]}
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    with tab2:
        st.header("Sign Up")
        new_email = st.text_input("New Email")
        new_pw = st.text_input("New Password", type="password")
        new_role = st.selectbox("Your Role in the Family", ["Mum", "Dad", "Son", "Daughter", "Grandparent", "Other"])
        if st.button("Sign Up"):
            if new_email and new_pw and new_role:
                hashed_pw = hash_password(new_pw)
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (new_email, hashed_pw, new_role))
                    conn.commit()
                    st.success("Account created! Please login.")
                except sqlite3.IntegrityError:
                    st.error("Email already exists")
                conn.close()
            else:
                st.error("Fill all fields")
else:
    st.sidebar.header(f"Welcome, {st.session_state.user['email']} ({st.session_state.user['role']})")
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.rerun()
    
    # Main app
    st.title("Tanielu Family Story")
    
    # Upload section
    with st.expander("Upload Photo"):
        title = st.text_input("Title")
        desc = st.text_area("Description/Story")
        date = st.date_input("Date", value=datetime.date.today())
        loc = st.text_input("Location")
        users = get_all_users()
        people_options = {u[1]: u[0] for u in users}  # email: id
        selected_people = st.multiselect("People in Photo", list(people_options.keys()))
        people_ids = [people_options[p] for p in selected_people]
        tags = st.text_input("Tags (comma-separated)")
        tags_list = [t.strip() for t in tags.split(',')] if tags else []
        uploaded_file = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])
        is_collage = st.checkbox("This is a collage (In production, AI will separate photos)")
        
        if uploaded_file:
            image_bytes = uploaded_file.read()
            if is_collage:
                st.warning("In production, AI will detect and separate individual photos from this collage.")
            # Standardize size
            resized_bytes = resize_image(image_bytes)
            image_data = base64_image(resized_bytes)
            if st.button("Save Photo"):
                save_photo(title, desc, str(date), loc, people_ids, tags_list, st.session_state.user['id'], image_data)
                st.success("Photo saved!")

    # Search
    search_query = st.text_input("Search Memories")
    if search_query:
        photos = search_photos(search_query)
    else:
        photos = get_all_photos()
    
    # View modes
    view_mode = st.radio("View Mode", ["Timeline", "Grid"])
    
    if view_mode == "Timeline":
        for photo in photos:
            pid, title, desc, date, loc, people_str, tags_str, uploader_id, image_data, created_at = photo
            uploader = get_user_by_id(uploader_id)
            people_emails = []
            if people_str:
                people_ids = people_str.split(',')
                for pid in people_ids:
                    p = get_user_by_id(int(pid))
                    if p:
                        people_emails.append(p[0])
            tags = tags_str.split(',') if tags_str else []
            with st.expander(f"{title} - {date}"):
                img_bytes = base64.b64decode(image_data)
                st.image(img_bytes, use_column_width=True)
                st.write(f"**Description:** {desc}")
                st.write(f"**Location:** {loc}")
                st.write(f"**People:** {', '.join(people_emails)}")
                st.write(f"**Tags:** {', '.join(tags)}")
                st.write(f"**Uploaded by:** {uploader[0]} ({uploader[1]})")
    
    elif view_mode == "Grid":
        cols = st.columns(3)
        for i, photo in enumerate(photos):
            pid, title, desc, date, loc, people_str, tags_str, uploader_id, image_data, created_at = photo
            img_bytes = base64.b64decode(image_data)
            with cols[i % 3]:
                st.image(img_bytes, caption=title, use_column_width=True)
                if st.button("Details", key=f"det_{pid}"):
                    st.write(f"**Title:** {title}")
                    st.write(f"**Date:** {date}")
                    st.write(f"**Description:** {desc}")
                    st.write(f"**Location:** {loc}")
                    # More details can be added in a modal-like expander, but Streamlit limits

    # Unique Feature: Family Role Map
    st.sidebar.header("Family Role Map")
    role_map = get_family_role_map()
    for role, emails in role_map.items():
        st.sidebar.write(f"**{role}:** {', '.join(emails)}")

    # Premium Features (placeholder, all enabled in demo)
    st.sidebar.header("Premium Features")
    st.sidebar.write("Unlimited uploads (demo)")
    st.sidebar.write("Export album (coming soon)")
    st.sidebar.write("Comments on photos (coming soon)")

# Run with: streamlit run app.py
