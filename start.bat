@echo off
REM Mind Rune - Quick Start Script for Windows
REM This script sets up and runs both backend and frontend

echo.
echo 🎮 Mind Rune - Quick Start
echo ==========================
echo.

REM Check Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python is not installed. Please install Python 3.12 or higher.
    pause
    exit /b 1
)

python --version
echo ✅ Python found
echo.

REM Navigate to backend
cd backend

REM Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔌 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies if needed
if not exist "venv\installed" (
    echo 📥 Installing dependencies...
    pip install -q -r requirements.txt
    type nul > venv\installed
    echo ✅ Dependencies installed
) else (
    echo ✅ Dependencies already installed
)

echo.
echo 🚀 Starting Mind Rune servers...
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:8080
echo WebSocket: ws://localhost:8000/ws
echo.
echo Press Ctrl+C to stop servers
echo.

REM Start backend in background
start /B python main.py

REM Wait a bit for backend to start
timeout /t 2 /nobreak >nul

REM Start frontend server
cd ..\frontend
start /B python -m http.server 8080

timeout /t 1 /nobreak >nul

echo.
echo ✨ Mind Rune is running!
echo.
echo 👉 Open your browser to: http://localhost:8080
echo.
echo Press any key to stop servers...
pause >nul

REM Kill Python processes
taskkill /F /IM python.exe >nul 2>nul

echo.
echo 🛑 Servers stopped
pause
