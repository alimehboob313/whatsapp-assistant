import asyncio
import logging
import time
import sys
import os
from typing import Optional, Dict

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from google import genai
from google.genai import types
from google.genai.errors import APIError

from config import GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_INSTRUCTION, MAX_HISTORY_TURNS

logger = logging.getLogger("whatsapp_agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class WhatsAppAgent:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL
        self.system_instruction = SYSTEM_INSTRUCTION
        self.client: Optional[genai.Client] = None
        self.sessions: Dict[str, dict] = {}
        self.lock = asyncio.Lock()
        
        self._init_client()

    def _init_client(self):
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini Client initialized with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")
                self.client = None
        else:
            logger.warning("No GEMINI_API_KEY provided. Agent will operate in setup-prompt mode.")

    def set_api_key(self, new_key: str):
        """Update API key dynamically if changed at runtime."""
        self.api_key = new_key.strip()
        self._init_client()
        self.sessions.clear()

    def _get_or_create_session(self, chat_id: str) -> dict:
        """Retrieve existing chat session or create a new one."""
        if chat_id not in self.sessions:
            chat = None
            if self.client:
                chat = self.client.chats.create(
                    model=self.model,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                    )
                )
            self.sessions[chat_id] = {
                "chat": chat,
                "created_at": time.time(),
                "last_active": time.time(),
                "message_count": 0
            }
        else:
            self.sessions[chat_id]["last_active"] = time.time()
            # If client was initialized after session creation
            if self.sessions[chat_id]["chat"] is None and self.client:
                self.sessions[chat_id]["chat"] = self.client.chats.create(
                    model=self.model,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                    )
                )
        return self.sessions[chat_id]

    def reset_session(self, chat_id: str) -> str:
        """Reset conversation memory for a user."""
        if chat_id in self.sessions:
            del self.sessions[chat_id]
        return "I apologize for any inconvenience. Conversation context has been cleared. What message would you like me to leave for Ali?"

    async def generate_response(self, chat_id: str, sender_name: str, message_text: str) -> str:
        """Process an incoming user message and return the reply."""
        text = message_text.strip()
        if not text:
            return ""

        # Handle built-in slash commands
        cmd = text.lower()
        if cmd in ("/reset", "/clear"):
            return self.reset_session(chat_id)
        if cmd in ("/help", "/info", "/status", "/model", "/about", "/whoareyou"):
            return "I apologize, but I am not at liberty to tell you that."
        if cmd == "/ping":
            return "Online."

        # If API key is missing, guide the user
        if not self.client:
            return (
                "⚠️ *Setup Required: Gemini API Key Missing*\n\n"
                "To chat with me, please add your Google Gemini API key to your `.env` file:\n"
                "```\nGEMINI_API_KEY=your_gemini_api_key_here\n```\n"
                "Get a free API key at: https://aistudio.google.com/app/apikey\n\n"
                "Once added, restart the bot or configure it in the backend."
            )

        async with self.lock:
            session = self._get_or_create_session(chat_id)
            chat = session["chat"]

            if not chat:
                return "⚠️ Could not initialize chat session. Please verify your Gemini API key."

            try:
                # Format prompt with sender name for natural conversation
                prompt = f"User ({sender_name}): {text}"
                
                # Execute in thread to keep async event loop responsive
                response = await asyncio.to_thread(chat.send_message, prompt)
                
                reply = response.text.strip() if response and response.text else "Sorry, I couldn't generate a response."
                
                session["message_count"] += 1
                
                # Limit memory if conversation exceeds max turns to prevent token bloat
                if session["message_count"] > MAX_HISTORY_TURNS * 2:
                    logger.info(f"Chat {chat_id} reached history limit. Resetting session context.")
                    self.reset_session(chat_id)
                
                return reply

            except APIError as e:
                logger.error(f"Gemini API Error: {e}")
                if "ResourceExhausted" in str(e) or "429" in str(e):
                    return "⏳ *Rate Limit:* Too many requests. Please wait a moment before sending another message."
                return f"⚠️ *Gemini Error:* {e.message if hasattr(e, 'message') else 'An API error occurred.'}"
            except Exception as e:
                logger.error(f"Unexpected error processing message: {e}", exc_info=True)
                return "⚠️ *Error:* Something went wrong while generating the response. Please try again in a moment."


# Global agent singleton
agent_instance = WhatsAppAgent()
