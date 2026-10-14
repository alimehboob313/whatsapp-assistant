import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = ROOT_DIR / "backend"
GATEWAY_DIR = ROOT_DIR / "gateway"

processes = []

def cleanup(sig=None, frame=None):
    print("\n🛑 Shutting down WhatsApp Agent processes...")
    for p in processes:
        if p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass
    time.sleep(1)
    for p in processes:
        if p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass
    print("👋 Goodbye!")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("=" * 60)
    print("🚀 STARTING WHATSAPP AI AGENT (FastAPI + Gemini + WhatsApp Web)")
    print("=" * 60)

    # 1. Start Python FastAPI Backend
    print(f"📦 Launching FastAPI Backend on http://127.0.0.1:8000...")
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--reload"
    ]
    p_backend = subprocess.Popen(
        backend_cmd,
        cwd=str(BACKEND_DIR)
    )
    processes.append(p_backend)

    # Give backend a moment to bind port
    time.sleep(2)

    # 2. Start Node.js WhatsApp Gateway
    print(f"📦 Launching WhatsApp Gateway (Baileys)...")
    npm_executable = "npm.cmd" if sys.platform == "win32" else "npm"
    gateway_cmd = [npm_executable, "start"]

    p_gateway = subprocess.Popen(
        gateway_cmd,
        cwd=str(GATEWAY_DIR)
    )
    processes.append(p_gateway)

    print("=" * 60)
    print("✨ Both services are running.")
    print("📱 Scan the QR code below when it appears to link WhatsApp.")
    print("⌨️ Press Ctrl+C at any time to stop both services.")
    print("=" * 60)

    # Monitor processes
    while True:
        for p in processes:
            ret = p.poll()
            if ret is not None:
                print(f"⚠️ A process exited unexpectedly with code {ret}.")
                cleanup()
        time.sleep(1)

if __name__ == "__main__":
    main()
