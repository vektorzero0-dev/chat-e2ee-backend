import os
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select

app = FastAPI(title="CyberCrypt Private Chat API")

# Izinkan CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Buat folder untuk menyimpan media (Foto, Video, VN)
MEDIA_DIR = "uploaded_media"
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


# Model Database Pesan
class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sender_id: str
    receiver_id: str
    msg_type: str  # text, image, video, audio, location
    content: str  # Teks pesan, URL media, atau koordinat lat,long
    timestamp: datetime = Field(default_factory=datetime.utcnow)


sqlite_file_name = "chat_database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


class MessageCreate(BaseModel):
    sender_id: str
    receiver_id: str
    msg_type: str
    content: str


# 1. Endpoint Kirim Pesan (Teks / Lokasi)
@app.post("/messages")
def send_message(msg: MessageCreate):
    with Session(engine) as session:
        db_msg = Message(**msg.dict())
        session.add(db_msg)
        session.commit()
        session.refresh(db_msg)
        return db_msg


# 2. Endpoint Upload Media (Foto, Video, VN)
@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(MEDIA_DIR, f"{datetime.now().timestamp()}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"url": f"/media/{os.path.basename(file_path)}"}


# 3. Endpoint Ambil Riwayat Chat (Bisa dibaca kapan saja walau lawan bicara offline)
@app.get("/messages/{user1_id}/{user2_id}", response_model=List[Message])
def get_chat_history(user1_id: str, user2_id: str):
    with Session(engine) as session:
        statement = select(Message).where(
            ((Message.sender_id == user1_id) & (Message.receiver_id == user2_id))
            | ((Message.sender_id == user2_id) & (Message.receiver_id == user1_id))
        ).order_by(Message.timestamp)
        results = session.exec(statement).all()
        return results


@app.get("/")
def root():
    return {"status": "online", "message": "Backend Private Chat Active"}