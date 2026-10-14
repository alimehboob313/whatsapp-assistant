# 🤖 WhatsApp AI Agent (FastAPI + Google Gemini + Baileys)

An automated, intelligent WhatsApp AI Agent powered by **Google Gemini** with multi-turn conversation memory, personal number support via QR-code session authentication (**Baileys**), and a **FastAPI** Python brain.

---

## 🌟 Key Features

- **No Meta Business Approval Required**: Uses WebSocket Multi-Device session linking. Scan the QR code once with WhatsApp on your phone and you are connected.
- **Fast & Lightweight**: Powered by `@whiskeysockets/baileys`—no heavy Chromium/Puppeteer browser overhead.
- **Google Gemini Brain**: Seamless multi-turn conversation memory using Google's official `google-genai` SDK (`gemini-flash-lite-latest` or `gemini-3.1-flash-lite`).
- **Interactive Commands**:
  - `/help` - View command list and capabilities
  - `/reset` or `/clear` - Wipe conversation history and start fresh
  - `/info` - View current model, active chats, and health
  - `/ping` - Latency check
- **Two-Way Proactive Messaging**: Includes a REST API endpoint (`POST /api/send`) to send messages or alerts directly to any WhatsApp number.
- **One-Click Startup**: Launch both services simultaneously with `run.bat` or `python run.py`.

---

## 🏗️ Architecture

```
                                  +------------------------------+
                                  |   WhatsApp Servers (Cloud)   |
                                  +---------------+--------------+
                                                  ^
                                                  | WebSocket Multi-Device
                                                  v
+------------------------+        +---------------+--------------+
|  User's WhatsApp Phone | <----> |  Node.js Gateway (Baileys)   |  (Port 3001)
+------------------------+        |  - Displays Terminal QR Code |
                                  |  - Manages Session Auth      |
                                  +---------------+--------------+
                                                  ^
                                                  | HTTP Webhook (JSON)
                                                  v
                                  +---------------+--------------+
                                  |    FastAPI Python Backend    |  (Port 8000)
                                  |  - Conversation Memory       |
                                  |  - Persona / Prompt Config   |
                                  +---------------+--------------+
                                                  ^
                                                  | API Calls
                                                  v
                                  +---------------+--------------+
                                  |      Google Gemini API       |
                                  +------------------------------+
```

---

## 🚀 Quick Start Guide

### 1. Configure Your Gemini API Key
Open `.env` (or copy `.env.example` to `.env`) in the `chatbot/` folder:
```bash
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
```
> 💡 *Don't have a key yet? Get a free API key at [Google AI Studio](https://aistudio.google.com/app/apikey).*

### 2. Run the Agent
Run either of the following in the `chatbot/` directory:

**On Windows:**
Double-click `run.bat` or run:
```powershell
python run.py
```

### 3. Scan the QR Code
1. Look at your terminal window. A QR code will be generated automatically.
2. Open **WhatsApp** on your phone.
3. Tap **Menu** (Android) or **Settings** (iOS) > **Linked Devices** > **Link a Device**.
4. Point your phone camera at the QR code in the terminal.
5. Once scanned, you will see:
   ```
   ✅ WHATSAPP AGENT CONNECTED SUCCESSFULLY!
   ```
6. Send a message to your WhatsApp account from another phone or chat to test it!

---

## 🛠️ Project Structure

```
chatbot/
├── .env                  # Configuration & API keys
├── .env.example          # Environment variables template
├── run.py                # Cross-platform runner for both backend and gateway
├── run.bat               # Windows one-click launcher
├── README.md             # Documentation & setup guide
├── backend/              # Python FastAPI Brain
│   ├── app.py            # FastAPI endpoints (/api/message, /api/send, etc.)
│   ├── agent.py          # Gemini AI agent & per-user memory logic
│   ├── config.py         # Config loader & system prompt
│   └── requirements.txt  # Python package dependencies
└── gateway/              # Node.js WhatsApp Web client
    ├── gateway.js        # Baileys client & QR code generator
    ├── package.json      # Node dependencies
    └── auth_info_baileys/# Local session authentication storage (created after scan)
```

---

## ⚙️ Configuration Options (`.env`)

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(None)* | Your Google Gemini API key from AI Studio |
| `GEMINI_MODEL` | `gemini-flash-lite-latest` | Model ID (`gemini-flash-lite-latest`, `gemini-3.1-flash-lite`, `gemini-3.8-flash`) |
| `MAX_HISTORY_TURNS` | `20` | Maximum conversation turns retained per chat |
| `SYSTEM_INSTRUCTION` | *(Friendly assistant)* | Personality and behavior prompt for your agent |
| `BACKEND_PORT` | `8000` | Port for the FastAPI server |
| `GATEWAY_PORT` | `3001` | Port for the WhatsApp Gateway REST API |

---

## 📬 Proactive Messaging API

To send a message programmatically to a user from code, cron jobs, or an external system:

```bash
curl -X POST http://127.0.0.1:8000/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "1234567890@s.whatsapp.net",
    "message": "Hello! This is a proactive reminder from your WhatsApp agent."
  }'
```

---

## ❓ Troubleshooting

1. **How to disconnect or scan a new phone?**
   - Stop the bot (`Ctrl+C`).
   - Delete the `gateway/auth_info_baileys` folder.
   - Run `python run.py` again to get a fresh QR code.

2. **Backend says "Missing Key"?**
   - Ensure your key is in `.env` as `GEMINI_API_KEY=...` with no quotes or spaces.
   - You can also set it dynamically via API:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/config/key \
       -H "Content-Type: application/json" \
       -d '{"api_key": "YOUR_NEW_KEY"}'
     ```
