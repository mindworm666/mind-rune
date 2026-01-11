#!/bin/bash
# Mind Rune - Development Server Startup Script

echo "=========================================="
echo "   MIND RUNE - Development Server"
echo "=========================================="
echo ""

# Check Python version
python3 --version || { echo "Python 3 is required"; exit 1; }

# Install dependencies if needed
if ! python3 -c "import websockets" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip3 install websockets
fi

# Change to backend directory
cd "$(dirname "$0")/backend"

echo "Starting game server on ws://localhost:8765..."
echo "Press Ctrl+C to stop"
echo ""

# Start the server
python3 main.py
