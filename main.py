from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inisialisasi Database SQLite Lokal di Render
def init_db():
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    # Tabel simpan kunci publik user
    c.execute('''CREATE TABLE IF NOT EXISTS keys (user_id TEXT PRIMARY KEY, public_key TEXT)''')
    # Tabel simpan pesan terenkripsi saat offline
    c.execute('''CREATE TABLE IF NOT EXISTS pending_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, to_user TEXT, message TEXT)''')
    conn.commit()
    conn.close()

init_db()

active_connections = {}

@app.post("/register-key")
async def register_key(data: dict):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO keys (user_id, public_key) VALUES (?, ?)", (data["user_id"], data["public_key"]))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/get-key/{user_id}")
async def get_key(user_id: str):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT public_key FROM keys WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"public_key": row[0]}
    return {"error": "User tidak ditemukan"}, 404

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    active_connections[user_id] = websocket

    # 1. Ambil & kirim pesan tunda dari DB saat user baru online
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT id, message FROM pending_messages WHERE to_user = ?", (user_id,))
    pending = c.fetchall()
    
    for msg_id, msg_data in pending:
        await websocket.send_text(msg_data)
        c.execute("DELETE FROM pending_messages WHERE id = ?", (msg_id,))
    
    conn.commit()
    conn.close()

    try:
        while True:
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            target = data.get("to")

            # 2. Jika target online, langsung kirim. Jika offline, simpan ke Database
            if target in active_connections:
                await active_connections[target].send_text(data_str)
            else:
                conn = sqlite3.connect("chat.db")
                c = conn.cursor()
                c.execute("INSERT INTO pending_messages (to_user, message) VALUES (?, ?)", (target, data_str))
                conn.commit()
                conn.close()
    except WebSocketDisconnect:
        del active_connections[user_id]