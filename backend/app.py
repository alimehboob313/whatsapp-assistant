import logging
import sys
import os

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from config import (
    BACKEND_HOST,
    BACKEND_PORT,
    GATEWAY_URL,
    GEMINI_MODEL,
    GEMINI_API_KEY
)
from agent import agent_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_app")

app = FastAPI(
    title="WhatsApp AI Agent Backend",
    description="FastAPI Brain powered by Google Gemini for WhatsApp",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IncomingWhatsAppMessage(BaseModel):
    chat_id: str = Field(..., description="WhatsApp JID / Chat identifier")
    sender: str = Field(..., description="Sender's phone/JID")
    sender_name: str = Field("User", description="Sender's WhatsApp push name")
    message: str = Field(..., description="Message text")
    is_group: bool = Field(False, description="Whether message was sent in a group chat")


class OutgoingWhatsAppMessage(BaseModel):
    to: str = Field(..., description="Recipient WhatsApp JID or phone number (e.g. 1234567890@s.whatsapp.net)")
    message: str = Field(..., description="Message text to send")


class UpdateKeyRequest(BaseModel):
    api_key: str = Field(..., description="Google Gemini API Key")


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "WhatsApp AI Agent Backend",
        "model": agent_instance.model,
        "api_configured": bool(agent_instance.client),
        "gateway_url": GATEWAY_URL,
        "docs": "/docs"
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "model": agent_instance.model,
        "has_api_key": bool(agent_instance.client),
        "active_sessions": len(agent_instance.sessions)
    }


@app.post("/api/message")
async def handle_incoming_message(payload: IncomingWhatsAppMessage):
    """
    Webhook called by WhatsApp Gateway (Baileys) whenever a message is received.
    """
    logger.info(f"Incoming message from {payload.sender_name} ({payload.chat_id}): {payload.message}")
    
    reply = await agent_instance.generate_response(
        chat_id=payload.chat_id,
        sender_name=payload.sender_name,
        message_text=payload.message
    )
    
    logger.info(f"Generated reply for {payload.chat_id}: {reply[:60]}...")
    return {
        "success": True,
        "reply": reply
    }


@app.post("/api/send")
async def send_proactive_message(payload: OutgoingWhatsAppMessage):
    """
    Proactively send a message to a WhatsApp user via the Gateway.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{GATEWAY_URL}/send",
                json={"to": payload.to, "message": payload.message}
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
    except Exception as e:
        logger.error(f"Failed to communicate with WhatsApp Gateway at {GATEWAY_URL}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to reach WhatsApp Gateway: {str(e)}")


@app.post("/api/config/key")
def update_api_key(req: UpdateKeyRequest):
    """
    Update Gemini API Key at runtime.
    """
    agent_instance.set_api_key(req.api_key)
    return {
        "success": True,
        "message": "Gemini API key updated successfully",
        "configured": bool(agent_instance.client)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=True)
