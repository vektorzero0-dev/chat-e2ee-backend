import os
import sqlite3
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="CyberCrypt Private Chat API")

# Izinkan CORS penuh
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Buat folder untuk penyimpanan media (Foto, Video, VN)
MEDIA_DIR = "uploaded_media"
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

# Inisialisasi Database SQLite Bawaan Python
DB_FILE = "chat_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id TEXT NOT NULL,
            receiver_id TEXT NOT NULL,
            msg_type TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class MessageCreate(BaseModel):
    sender_id: str
    receiver_id: str
    msg_type: str
    content: str

# 1. Endpoint Kirim Pesan
@app.post("/messages")
def send_message(msg: MessageCreate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (sender_id, receiver_id, msg_type, content) VALUES (?, ?, ?, ?)",
        (msg.sender_id, msg.receiver_id, msg.msg_type, msg.content)
    )
    conn.commit()
    conn.close()
    return {"status": "success"}

# 2. Endpoint Upload Media (Foto, Video, VN)
@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(MEDIA_DIR, f"{datetime.now().timestamp()}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"url": f"/media/{os.path.basename(file_path)}"}

# 3. Endpoint Ambil Riwayat Chat
@app.get("/messages/{user1_id}/{user2_id}")
def get_chat_history(user1_id: str, user2_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT sender_id, receiver_id, msg_type, content, timestamp 
        FROM messages 
        WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
        ORDER BY timestamp ASC
    ''', (user1_id, user2_id, user2_id, user1_id))
    
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        history.append({
            "sender_id": r[0],
            "receiver_id": r[1],
            "msg_type": r[2],
            "content": r[3],
            "timestamp": r[4]
        })
    return history

@app.get("/")
def root():
    return {"status": "online", "message": "Backend Active"}