from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Mengizinkan akses lintas domain (CORS) agar Frontend GitHub Pages bisa terhubung
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Class untuk mengelola koneksi real-time pengguna
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_payload(self, receiver_id: str, payload: dict):
        if receiver_id in self.active_connections:
            await self.active_connections[receiver_id].send_json(payload)

manager = ConnectionManager()

# Endpoint PING untuk Cron-job.org agar server Render tidak pernah tidur
@app.get("/health")
def health_check():
    return {"status": "online", "message": "Server Backend Chat E2EE Aktif 24/7!"}

# Endpoint WebSocket untuk jalur komunikasi real-time
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Meneruskan data JSON (teks terenkripsi / link media terenkripsi) dari pengirim ke penerima
            data = await websocket.receive_json()
            await manager.send_payload(data["to"], data)
    except WebSocketDisconnect:
        manager.disconnect(user_id)
