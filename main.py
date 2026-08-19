from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

# Izinkan CORS dari GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# KONEKSI SISTEM (Memori)
active_connections: dict[str, WebSocket] = {}

# 1. Route Root (Mencegah Error 404 saat dicek di browser)
@app.get("/")
def read_root():
    return {"status": "online", "message": "E2EE Server Terminal Active"}

# 2. Endpoint WebSocket untuk Chat
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    active_connections[user_id] = websocket
    print(f"[NODE_CONNECTED]: {user_id}")

    try:
        while True:
            data_str = await websocket.receive_text()
            data = json.loads(data_str)
            target = data.get("to")

            # Meneruskan data terenkripsi ke target jika sedang online
            if target in active_connections:
                await active_connections[target].send_text(data_str)
            else:
                # Beri respon jika lawan offline
                await websocket.send_text(json.dumps({
                    "type": "system_error",
                    "message": f"Node [{target}] offline / belum terhubung."
                }))
    except WebSocketDisconnect:
        if user_id in active_connections:
            del active_connections[user_id]
        print(f"[NODE_DISCONNECTED]: {user_id}")
        @app.get("/health")
def health_check():
    return "OK"
