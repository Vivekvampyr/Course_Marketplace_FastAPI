from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from app.database import get_db, SessionLocal
from app.schemas.chat import ChatRequest, ChatHistoryResponse
from app.services.gemini_service import ask_gemini, ask_gemini_ws
from app.dependencies.auth import get_current_user
from app.models.chat import ChatMessage
from app.models.user import User
from app.utils.jwt import decode_token
import json

router = APIRouter(prefix="/chat", tags=["AI Chat"])

# ── WebSocket Connection Manager ───────────────────────
class ConnectionManager:
    def __init__(self):
        # user_id → WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        # user_id → conversation history for Gemini
        self.conversation_history: Dict[int, list] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.conversation_history[user_id] = []

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)
        self.conversation_history.pop(user_id, None)

    async def send_message(self, user_id: int, message: str):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_text(message)

    def add_to_history(self, user_id: int, role: str, text: str):
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        # Gemini history format
        self.conversation_history[user_id].append({
            "role": role,
            "parts": [{"text": text}]
        })
        # Keep only last 10 exchanges to avoid token overflow
        if len(self.conversation_history[user_id]) > 20:
            self.conversation_history[user_id] = self.conversation_history[user_id][-20:]

    def get_history(self, user_id: int) -> list:
        return self.conversation_history.get(user_id, [])


manager = ConnectionManager()


# ── REST: Ask AI (single question) ────────────────────
@router.post("/ask")
async def ask_ai(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    response = await ask_gemini(
        message=data.message,
        course_id=data.course_id,
        user_id=current_user.id,
        db=db
    )
    return {"message": data.message, "response": response}


# ── REST: Chat history ─────────────────────────────────
@router.get("/history", response_model=List[ChatHistoryResponse])
def get_chat_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# ── REST: Clear chat history ───────────────────────────
@router.delete("/history")
def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Chat history cleared"}


# ── WebSocket: Live AI Chat ────────────────────────────
@router.websocket("/ws/{token}")
async def websocket_chat(websocket: WebSocket, token: str):
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001)
        return

    user_id = int(payload.get("sub"))
    db = SessionLocal()

    try:
        await manager.connect(user_id, websocket)

        await manager.send_message(user_id, json.dumps({
            "type": "system",
            "message": "Connected! Ask me anything about your courses."
        }))

        while True:
            try:
                raw = await websocket.receive_text()
            except Exception:
                break

            # ── Skip empty frames ──────────────────────
            if not raw or not raw.strip():
                continue

            # ── Accept plain text OR JSON ──────────────
            try:
                data = json.loads(raw)
                user_message = data.get("message", "").strip()
            except json.JSONDecodeError:
                user_message = raw.strip()

            # ── Skip if still empty ────────────────────
            if not user_message:
                continue

            # ── Typing indicator ───────────────────────
            await manager.send_message(user_id, json.dumps({
                "type": "typing",
                "message": "AI is thinking..."
            }))

            # ── Add to history ─────────────────────────
            manager.add_to_history(user_id, "user", user_message)
            past_history = manager.get_history(user_id)[:-1]

            # ── Get Gemini response ────────────────────
            ai_response = await ask_gemini_ws(user_message, past_history)

            # ── Add response to history ────────────────
            manager.add_to_history(user_id, "model", ai_response)

            # ── Save to DB ─────────────────────────────
            try:
                chat = ChatMessage(
                    user_id=user_id,
                    message=user_message,
                    response=ai_response
                )
                db.add(chat)
                db.commit()
            except Exception:
                db.rollback()

            # ── Send response ──────────────────────────
            await manager.send_message(user_id, json.dumps({
                "type": "response",
                "message": ai_response
            }))

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    finally:
        db.close()