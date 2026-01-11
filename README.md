# Mind Rune 🎮

**A Minimalist Multiplayer Roguelike MMO**

Mind Rune is a retro-style, ASCII-based multiplayer roguelike where players explore procedurally generated worlds, encounter other adventurers in real-time, and experience meaningful gameplay without overwhelming complexity.

## ✨ Features (Iteration Zero)

- **🔐 Account System**: Register and login to persist your character
- **🌍 Procedurally Generated World**: Explore an infinite ASCII wilderness
- **👥 Real-time Multiplayer**: See other players move in real-time via WebSocket
- **💬 Global Chat**: Communicate with other adventurers
- **⌨️ Simple Controls**: Arrow keys or WASD to move
- **🎨 Retro Aesthetic**: Pure ASCII graphics with terminal-style interface

## 🛠️ Tech Stack

### Backend
- **Python 3.12** with FastAPI
- **WebSockets** for real-time communication
- **SQLite** for data persistence
- **JWT** authentication

### Frontend
- **Pure JavaScript** (no framework bloat!)
- **HTML5 + CSS3** with retro terminal styling
- **WebSocket API** for real-time updates

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- A modern web browser

### Backend Setup

1. Navigate to backend directory:
```bash
cd mind-rune/backend
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
python main.py
```

The API server will start on `http://localhost:8000`

### Frontend Setup

1. Open `mind-rune/frontend/index.html` in your browser, or

2. Serve with a simple HTTP server:
```bash
cd mind-rune/frontend
python -m http.server 8080
```

Then navigate to `http://localhost:8080`

## 🎮 How to Play

1. **Register/Login**: Create an account or login with existing credentials
2. **Movement**: Use arrow keys or WASD to explore the world
3. **Chat**: Press `T` to open chat, type your message, and press Enter
4. **Explore**: Discover the procedurally generated terrain
   - `.` = Ground (walkable)
   - `#` = Wall (blocked)
   - `~` = Water (blocked)
   - `^` = Mountain
   - `t` = Tree
   - `@` = Player character

## 📁 Project Structure

```
mind-rune/
├── backend/
│   ├── main.py              # FastAPI application & WebSocket server
│   ├── auth.py              # JWT authentication
│   ├── database.py          # SQLite database layer
│   ├── models.py            # Data models
│   ├── game.py              # Game world & connection manager
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── index.html           # Main HTML page
│   ├── css/
│   │   └── style.css        # Retro terminal styling
│   └── js/
│       └── game.js          # Game client logic
│
└── README.md
```

## 🔮 Roadmap

### Iteration Zero ✅ (Current)
- [x] Basic account creation and authentication
- [x] Multiplayer connection system
- [x] Simple world generation
- [x] Real-time player movement
- [x] Global chat

### Future Iterations
- [ ] **Combat System**: Turn-based or real-time combat
- [ ] **Inventory & Items**: Collect, use, and trade items
- [ ] **Character Progression**: Experience, levels, and skills
- [ ] **Monsters & NPCs**: AI-controlled entities
- [ ] **Dungeons**: Instanced areas for parties
- [ ] **Quests**: Dynamic quest generation
- [ ] **Guilds/Parties**: Team up with other players
- [ ] **Permadeath Mode**: Hardcore roguelike experience
- [ ] **Sound Effects**: Retro bleeps and bloops
- [ ] **Mobile Support**: Touch controls

## 🎯 Design Philosophy

**Minimalist**: Every feature should add meaningful gameplay, not complexity.

**Accessible**: Anyone should be able to jump in and start playing within seconds.

**Retro**: ASCII graphics and terminal aesthetics for that authentic roguelike feel.

**Multiplayer**: The world feels alive because other players are real people.

**Iteration**: Build in small, complete increments. Each iteration should be playable.

## 🤝 Contributing

This is an early-stage project! Contributions, ideas, and feedback are welcome.

## 📝 License

MIT License - Feel free to use this project as a learning resource or base for your own game!

## 🐛 Known Issues

- Server needs to be restarted to reset the world
- No player authentication timeout (tokens last 30 days)
- Chat messages are not persisted
- No rate limiting on movements

## 💡 Tips for Development

- The backend uses procedural generation with seeded randomness for consistent terrain
- WebSocket connections auto-reconnect after 5 seconds if disconnected
- Press F12 in browser to see console logs for debugging
- Database file (`mindrune.db`) is created automatically on first run

---

**Made with 💚 by mindworm666**

*"In the Mind Rune, every step is an adventure."*
