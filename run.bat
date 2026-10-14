@echo off
title WhatsApp AI Agent Launcher
echo ============================================================
echo   WhatsApp AI Agent (FastAPI + Google Gemini + Baileys)
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/2] Checking Python and Node dependencies...
python -c "import fastapi, uvicorn, google.genai" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing backend dependencies...
    pip install -r backend\requirements.txt
)

if not exist "gateway\node_modules" (
    echo Installing gateway dependencies...
    cd gateway && npm install && cd ..
)

echo [2/2] Launching agent system...
echo.
python run.py

pause
