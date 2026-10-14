const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason
} = require('@whiskeysockets/baileys');
const pino = require('pino');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const express = require('express');
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const GATEWAY_PORT = process.env.GATEWAY_PORT || 3001;
const AUTH_DIR = path.resolve(__dirname, 'auth_info_baileys');

let sock = null;
let isConnected = false;
let lastQR = null;

// ==========================================
// 1. WhatsApp Connection Management
// ==========================================
async function startGateway() {
    console.log('🔄 Initializing WhatsApp Web Client...');
    
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    sock = makeWASocket({
        auth: state,
        logger: pino({ level: 'silent' }), // Keep terminal clean
        printQRInTerminal: false,
        browser: ['WhatsApp AI Agent', 'Desktop', '1.0.0']
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            lastQR = qr;
            console.log('\n============================================================');
            console.log('📲 SCAN THIS QR CODE WITH WHATSAPP TO CONNECT YOUR AGENT:');
            console.log('1. Open WhatsApp on your phone');
            console.log('2. Tap Settings / Menu -> Linked Devices -> Link a Device');
            console.log('============================================================\n');
            qrcode.generate(qr, { small: true });
            console.log('\nWaiting for scan...');
        }

        if (connection === 'open') {
            isConnected = true;
            lastQR = null;
            console.log('\n============================================================');
            console.log('✅ WHATSAPP AGENT CONNECTED SUCCESSFULLY!');
            console.log(`🤖 Forwarding incoming messages to FastAPI at: ${BACKEND_URL}`);
            console.log('============================================================\n');
        }

        if (connection === 'close') {
            isConnected = false;
            const statusCode = (lastDisconnect?.error)?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

            console.log(`⚠️ Connection closed. Code: ${statusCode || 'unknown'}. Reconnecting: ${shouldReconnect}`);

            if (shouldReconnect) {
                setTimeout(() => startGateway(), 3000);
            } else {
                console.log('🔄 Session logged out or expired. Resetting session to provide a new QR code...');
                try {
                    const fs = require('fs');
                    if (fs.existsSync(AUTH_DIR)) {
                        fs.rmSync(AUTH_DIR, { recursive: true, force: true });
                    }
                } catch (e) {
                    console.error('Failed to clear auth dir:', e.message);
                }
                setTimeout(() => startGateway(), 2000);
            }
        }
    });

    // ==========================================
    // 2. Incoming Messages Listener
    // ==========================================
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;

        for (const msg of messages) {
            // Ignore messages sent by the bot itself or status broadcasts
            if (msg.key.fromMe) continue;
            if (msg.key.remoteJid === 'status@broadcast') continue;

            // Extract plain text or image caption
            const text =
                msg.message?.conversation ||
                msg.message?.extendedTextMessage?.text ||
                msg.message?.imageMessage?.caption ||
                '';

            if (!text || text.trim() === '') continue;

            const chatId = msg.key.remoteJid;
            const senderName = msg.pushName || 'Friend';
            const isGroup = chatId.endsWith('@g.us');

            console.log(`📩 [${senderName}] (${chatId}): "${text.length > 50 ? text.substring(0, 50) + '...' : text}"`);

            try {
                // Show typing indicator in WhatsApp
                await sock.sendPresenceUpdate('composing', chatId);

                // Forward message to FastAPI Backend
                const response = await axios.post(`${BACKEND_URL}/api/message`, {
                    chat_id: chatId,
                    sender: msg.key.participant || chatId,
                    sender_name: senderName,
                    message: text,
                    is_group: isGroup
                }, { timeout: 30000 });

                // Turn off typing indicator
                await sock.sendPresenceUpdate('paused', chatId);

                if (response.data && response.data.reply) {
                    const replyText = response.data.reply;
                    
                    // Reply quoting the original message
                    await sock.sendMessage(chatId, { text: replyText }, { quoted: msg });
                    console.log(`📤 Replied to [${senderName}]: "${replyText.substring(0, 50)}..."`);
                }
            } catch (err) {
                await sock.sendPresenceUpdate('paused', chatId);
                console.error(`❌ Error communicating with FastAPI backend: ${err.message}`);

                // Inform user only if backend connection failed
                if (err.code === 'ECONNREFUSED' || err.code === 'ENOTFOUND') {
                    await sock.sendMessage(chatId, {
                        text: '⚠️ *Backend Unavailable:* The AI brain (FastAPI server) is currently offline. Please ensure the Python server is running.'
                    }, { quoted: msg });
                }
            }
        }
    });
}

// ==========================================
// 3. Proactive Messaging HTTP API
// ==========================================
const app = express();
app.use(express.json());

app.get('/status', (req, res) => {
    res.json({
        connected: isConnected,
        qrReady: !isConnected && !!lastQR,
        backendUrl: BACKEND_URL
    });
});

app.post('/send', async (req, res) => {
    const { to, message } = req.body;
    if (!to || !message) {
        return res.status(400).json({ error: 'Fields "to" and "message" are required.' });
    }

    if (!isConnected || !sock) {
        return res.status(503).json({ error: 'WhatsApp client is not currently connected.' });
    }

    try {
        let jid = to.trim();
        // Format raw numbers like 1234567890 to WhatsApp JID format
        if (!jid.includes('@')) {
            jid = jid.replace(/[^0-9]/g, '') + '@s.whatsapp.net';
        }

        await sock.sendMessage(jid, { text: message });
        res.json({ success: true, sent_to: jid });
    } catch (err) {
        console.error('Failed to send outbound message:', err);
        res.status(500).json({ error: err.message });
    }
});

app.listen(GATEWAY_PORT, () => {
    console.log(`🌐 WhatsApp Gateway REST API running on http://127.0.0.1:${GATEWAY_PORT}`);
});

// Start the WhatsApp Socket client
startGateway();
