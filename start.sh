#!/bin/bash

# Mind Rune - Quick Start Script
# This script sets up and runs both backend and frontend

set -e

echo "🎮 Mind Rune - Quick Start"
echo "=========================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.12 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Found Python $PYTHON_VERSION"

# Navigate to backend
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/installed" ]; then
    echo "📥 Installing dependencies..."
    pip install -q -r requirements.txt
    touch venv/installed
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

echo ""
echo "🚀 Starting Mind Rune servers..."
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:8080"
echo "WebSocket: ws://localhost:8000/ws"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Start backend in background
python main.py &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 2

# Start frontend server
cd ../frontend
python3 -m http.server 8080 &
FRONTEND_PID=$!

# Wait for backend to be ready
sleep 1

echo ""
echo "✨ Mind Rune is running!"
echo ""
echo "👉 Open your browser to: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop..."

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT

# Keep script running
wait
