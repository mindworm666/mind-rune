#!/bin/bash
# Mind Rune - Frontend Development Server

echo "=========================================="
echo "   MIND RUNE - Frontend Server"
echo "=========================================="
echo ""

cd "$(dirname "$0")/frontend"

# Check if Python is available for simple HTTP server
if command -v python3 &> /dev/null; then
    echo "Starting frontend on http://localhost:8080..."
    echo "Press Ctrl+C to stop"
    echo ""
    python3 -m http.server 8080
elif command -v python &> /dev/null; then
    echo "Starting frontend on http://localhost:8080..."
    echo "Press Ctrl+C to stop"
    echo ""
    python -m http.server 8080
else
    echo "Python is required to run the frontend server."
    echo "Alternatively, open frontend/index.html directly in a browser."
    exit 1
fi
