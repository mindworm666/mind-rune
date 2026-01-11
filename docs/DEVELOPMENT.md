# Development Guide for Mind Rune

This guide is for developers who want to contribute to or modify Mind Rune.

## Project Architecture

### Backend (Python + FastAPI)

```
backend/
├── main.py          # FastAPI app, WebSocket server, endpoints
├── auth.py          # JWT token creation/verification, password hashing
├── database.py      # SQLite async wrapper, database operations
├── models.py        # Data models (User, Character, Position, Tile)
├── game.py          # Game world logic, procedural generation
└── requirements.txt # Python dependencies
```

### Frontend (Vanilla JavaScript)

```
frontend/
├── index.html       # Main page structure
├── css/
│   └── style.css    # Terminal-style retro theme
└── js/
    └── game.js      # Client logic, WebSocket handling, rendering
```

## Key Components

### Authentication Flow

1. **Registration**: 
   - POST `/auth/register` with username/password
   - Backend hashes password with bcrypt
   - Creates user in SQLite
   - Creates starting character at (0, 0)
   - Returns JWT token

2. **Login**:
   - POST `/auth/login` with credentials
   - Backend verifies password hash
   - Returns JWT token with 30-day expiry

3. **WebSocket Connection**:
   - Client connects to `/ws?token=<jwt>`
   - Backend verifies token, extracts username
   - Adds player to game world
   - Broadcasts player joined event

### Game World System

**GameWorld Class** (`backend/game.py`):
- Maintains dictionary of active players
- Procedural terrain generation using seeded randomness
- Position validation and collision detection
- Visibility calculation (21x21 grid around player)

**Terrain Generation**:
```python
def get_terrain(x, y):
    seed = (x * 73856093) ^ (y * 19349663)
    random.seed(seed)
    # Deterministic terrain based on position
```

**Movement**:
- Client sends `{"type": "move", "direction": "n/s/e/w"}`
- Server validates move (bounds, walkable terrain)
- Updates database and game state
- Broadcasts to nearby players

### WebSocket Protocol

**Client → Server:**
```json
{"type": "move", "direction": "n"}
{"type": "chat", "message": "Hello!"}
{"type": "ping"}
```

**Server → Client:**
```json
{"type": "init", "character_id": 1, "position": {"x": 0, "y": 0}, "world": [[]], "players": []}
{"type": "move_success", "position": {"x": 1, "y": 0}, "world": [[]]}
{"type": "player_joined", "username": "Alice", "character_id": 2}
{"type": "player_left", "username": "Bob"}
{"type": "player_moved", "character_id": 3, "position": {"x": 5, "y": 5}}
{"type": "chat", "username": "Alice", "message": "Hi!"}
```

## Development Workflow

### Running in Development Mode

**Terminal 1 - Backend (auto-reload enabled):**
```bash
cd backend
source venv/bin/activate
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
python3 -m http.server 8080
```

### Making Changes

**Backend Changes:**
- FastAPI has auto-reload enabled
- Code changes automatically restart the server
- Check terminal for errors

**Frontend Changes:**
- Simply refresh the browser
- Check browser console (F12) for errors

### Testing

**Manual Testing:**
1. Open game in multiple browser windows/tabs
2. Use incognito windows for different accounts
3. Check WebSocket messages in browser DevTools → Network → WS

**Unit Testing (Future):**
```bash
pytest tests/
```

## Adding New Features

### Example: Add Player Inventory

1. **Update Model** (`models.py`):
```python
@dataclass
class Character:
    # ... existing fields
    inventory: list = field(default_factory=list)
```

2. **Update Database** (`database.py`):
```python
# Add column to characters table
# Add methods: add_item(), remove_item(), get_inventory()
```

3. **Add Game Logic** (`game.py` or new `inventory.py`):
```python
class InventoryManager:
    def pickup_item(self, character_id, item):
        # Implementation
```

4. **Add WebSocket Handler** (`main.py`):
```python
elif command_type == "pickup":
    item_id = data.get("item_id")
    # Handle pickup logic
```

5. **Update Frontend** (`game.js`):
```javascript
// Add UI for inventory
// Handle pickup keybind
// Send pickup command to server
```

## Code Style Guidelines

### Python (Backend)
- Use `async/await` for I/O operations
- Type hints where appropriate
- Docstrings for public functions
- PEP 8 style (4 spaces, snake_case)

### JavaScript (Frontend)
- ES6+ features (classes, arrow functions, async/await)
- camelCase for variables and functions
- Clear naming (e.g., `handleServerMessage` not `hsm`)
- Comments for complex logic

### General Principles
- **KISS**: Keep it simple
- **DRY**: Don't repeat yourself
- **Fail fast**: Validate early, error clearly
- **Minimize state**: Stateless where possible

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

### Characters Table
```sql
CREATE TABLE characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    pos_x INTEGER NOT NULL DEFAULT 0,
    pos_y INTEGER NOT NULL DEFAULT 0,
    health INTEGER NOT NULL DEFAULT 100,
    level INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Performance Considerations

### Current Limits
- SQLite is single-writer (fine for iteration zero)
- No connection pooling
- No rate limiting
- World generation on-demand (cached)

### Future Optimizations
- PostgreSQL for production
- Redis for session/world state
- Rate limiting middleware
- Spatial indexing for player queries
- Chunked world updates (only send changed tiles)

## Security Notes

### Current Implementation
- ✅ Password hashing with bcrypt
- ✅ JWT tokens with expiry
- ✅ SQL injection protection (parameterized queries)
- ⚠️ Secret key hardcoded (use env var in production)
- ⚠️ No rate limiting
- ⚠️ No input sanitization for chat
- ⚠️ CORS allows all origins

### Production TODO
- [ ] Environment variables for secrets
- [ ] Rate limiting on API endpoints
- [ ] Sanitize chat messages (XSS prevention)
- [ ] Proper CORS configuration
- [ ] HTTPS/WSS only
- [ ] Token refresh mechanism
- [ ] Account email verification

## Debugging Tips

### Backend Debugging
```python
# Add print statements
print(f"Player {character_id} moved to {new_position}")

# Use Python debugger
import pdb; pdb.set_trace()

# Check WebSocket connections
print(f"Active connections: {len(connection_manager.active_connections)}")
```

### Frontend Debugging
```javascript
// Browser console
console.log('Position:', this.position);
console.log('WebSocket state:', this.ws.readyState);

// WebSocket logging
this.ws.addEventListener('message', (event) => {
    console.log('Received:', JSON.parse(event.data));
});
```

### Common Issues
- **Database locked**: SQLite doesn't handle concurrent writes well
- **WebSocket closed**: Check token validity, server logs
- **Player not moving**: Check terrain walkability, bounds checking
- **Chat not working**: Check WebSocket connection state

## Useful Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **WebSocket API**: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- **SQLite**: https://www.sqlite.org/docs.html
- **JWT**: https://jwt.io/

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/awesome-feature`
3. Make your changes
4. Test thoroughly
5. Commit: `git commit -m "Add awesome feature"`
6. Push: `git push origin feature/awesome-feature`
7. Open a Pull Request

---

**Questions?** Open an issue on GitHub!
