# Setup Guide for Mind Rune

This guide will help you get Mind Rune running on your local machine.

## Prerequisites

Before you begin, make sure you have:
- **Python 3.12 or higher** - [Download Python](https://www.python.org/downloads/)
- **A modern web browser** - Chrome, Firefox, Safari, or Edge
- **Git** (optional) - For cloning the repository

## Step 1: Get the Code

### Option A: Clone from GitHub (Recommended)
```bash
git clone https://github.com/mindworm666/mind-rune.git
cd mind-rune
```

### Option B: Download ZIP
1. Go to https://github.com/mindworm666/mind-rune
2. Click "Code" → "Download ZIP"
3. Extract the ZIP file
4. Open terminal/command prompt in the extracted folder

## Step 2: Backend Setup

### 2.1 Navigate to Backend Directory
```bash
cd backend
```

### 2.2 Create a Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` appear in your terminal prompt.

### 2.3 Install Dependencies
```bash
pip install -r requirements.txt
```

This will install:
- FastAPI (web framework)
- Uvicorn (ASGI server)
- SQLAlchemy (database)
- python-jose (JWT tokens)
- passlib (password hashing)
- websockets (real-time communication)

### 2.4 Run the Backend Server
```bash
python main.py
```

You should see output like:
```
✅ Database initialized
🎮 Mind Rune server starting...
📡 WebSocket endpoint: ws://localhost:8000/ws
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Leave this terminal window open!** The server needs to keep running.

## Step 3: Frontend Setup

Open a **new terminal window/tab** (keep the backend running).

### 3.1 Navigate to Frontend Directory
```bash
cd mind-rune/frontend
```

### 3.2 Start a Web Server

**Option A: Python HTTP Server (Easiest)**
```bash
python3 -m http.server 8080
```

**Option B: Just Open the File**
You can also simply double-click `index.html` to open it in your browser, but this might have CORS issues.

### 3.3 Open in Browser
Navigate to: `http://localhost:8080`

## Step 4: Create Your Character

1. You'll see the Mind Rune login screen
2. Enter a username and password
3. Click **Register** to create a new account
4. You'll automatically be logged in and enter the game world!

## Step 5: Play!

### Controls
- **Arrow Keys** or **WASD** - Move your character
- **T** - Open chat
- **Enter** - Send chat message
- **ESC** - Close chat

### What You See
- `@` - Your character (or other players)
- `.` - Ground (walkable)
- `#` - Walls (blocked)
- `~` - Water (blocked)
- `^` - Mountains
- `t` - Trees

## Troubleshooting

### "Module not found" errors
Make sure your virtual environment is activated:
```bash
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

Then reinstall dependencies:
```bash
pip install -r requirements.txt
```

### "Connection refused" in browser
Make sure the backend server is running on port 8000:
```bash
cd backend
python main.py
```

### "CORS errors" in browser console
Use the Python HTTP server instead of opening the file directly:
```bash
cd frontend
python3 -m http.server 8080
```

### WebSocket won't connect
1. Check that backend is running
2. Check browser console (F12) for error messages
3. Try refreshing the page
4. Clear browser cache and localStorage

### Port already in use
If port 8000 or 8080 is already taken:

**Backend (change port):**
Edit `main.py`, change the last line to:
```python
uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
```

**Frontend (change port):**
```bash
python3 -m http.server 8081
```

Then update `js/game.js` with the new backend port:
```javascript
const API_URL = 'http://localhost:8001';
const WS_URL = 'ws://localhost:8001/ws';
```

## Testing with Multiple Players

To test multiplayer functionality:

1. Open the game in one browser window
2. Open a **new incognito/private window** 
3. Go to `http://localhost:8080`
4. Register with a different username
5. Move around - you should see each other!

## Stopping the Server

Press `Ctrl+C` in the terminal where the backend is running.

## Next Steps

- Check out the [README.md](../README.md) for more information
- Explore the code in `backend/` and `frontend/`
- Try modifying the world generation in `backend/game.py`
- Customize the look in `frontend/css/style.css`

---

**Need help?** Open an issue on GitHub: https://github.com/mindworm666/mind-rune/issues

**Have fun exploring Mind Rune!** 🎮✨
