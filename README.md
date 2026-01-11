# Mind Rune 🎮

A real-time multiplayer roguelike adventure game with a retro CRT terminal aesthetic.

![Mind Rune](https://img.shields.io/badge/Status-Playable-green)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features ✨

- **Real-time Combat** - No turns! All actions have cooldowns
- **Multiplayer** - See other players in real-time
- **Procedural World** - Infinite 3D world with dungeons
- **Heavy CRT Effects** - Scanlines, phosphor glow, chromatic aberration
- **ASCII Graphics** - Classic roguelike aesthetics
- **Entity Component System** - Scalable, extensible architecture

## Quick Start 🚀

### 1. Start the Backend Server

```bash
# From project root
python3 backend/main.py

# Or use the startup script
./start_server.sh
```

The server will start on `ws://localhost:8765`

### 2. Start the Frontend

```bash
# From project root
cd frontend
python3 -m http.server 8080

# Or use the startup script
./start_frontend.sh
```

Open your browser to `http://localhost:8080`

### 3. Login and Play!

Test accounts:
- `test` / `test`
- `player1` / `password1`
- `player2` / `password2`

Or register a new account!

## Controls 🎮

| Key | Action |
|-----|--------|
| `W/↑` | Move North |
| `A/←` | Move West |
| `S/↓` | Move South |
| `D/→` | Move East |
| `Space` | Interact |
| `G` | Pick up item |
| `I` | Toggle inventory |
| `C` | Character sheet |
| `M` | Toggle minimap |
| `T` | Chat |
| `H` | Help |
| `<` / `>` | Use stairs |
| `F3` | Toggle debug info |

## Architecture 📐

```
mind-rune/
├── backend/
│   ├── main.py              # Server entry point
│   ├── engine/
│   │   ├── ecs.py           # Entity Component System
│   │   ├── game_loop.py     # Fixed-timestep game loop (20 TPS)
│   │   └── spatial.py       # Spatial hash grid
│   ├── components/
│   │   └── core.py          # All game components
│   ├── systems/
│   │   ├── core_systems.py  # Combat, movement, cooldowns
│   │   ├── ai_system.py     # NPC decision making
│   │   ├── inventory_system.py
│   │   └── visibility_system.py
│   ├── world/
│   │   ├── world_3d.py      # Chunk-based 3D world
│   │   └── starter_world.py # Initial play area
│   └── server/
│       ├── websocket.py     # WebSocket implementation
│       ├── protocol.py      # Message types
│       └── game_server.py   # Main server
│
├── frontend/
│   ├── index.html           # Main HTML
│   ├── css/
│   │   ├── terminal.css     # Base terminal styles
│   │   └── crt-effects.css  # CRT shader effects
│   └── js/
│       ├── main.js          # Entry point
│       ├── game.js          # Main game client
│       ├── renderer.js      # ASCII rendering
│       ├── network.js       # WebSocket client
│       ├── input.js         # Input handling
│       └── viewport.js      # Camera system
│
└── docs/
    ├── ARCHITECTURE.md      # System design
    └── INVARIANTS.md        # Core invariants
```

## Technical Details 🔧

### Backend
- **Language**: Python 3.8+
- **Architecture**: Entity Component System (ECS)
- **Tick Rate**: 20 TPS (50ms per tick)
- **Protocol**: WebSocket with JSON messages
- **World**: Chunk-based (16×16×16), procedurally generated

### Frontend
- **Rendering**: Canvas 2D ASCII rendering
- **Target FPS**: 60
- **Effects**: CSS-based CRT simulation
- **Input**: Keyboard + mouse support

### Key Systems
- **CooldownSystem** - All actions have cooldowns
- **CombatSystem** - Real-time damage with threat tables
- **AISystem** - State machine AI (idle, wander, chase, attack, flee)
- **MovementSystem** - Grid-based movement with collision
- **InventorySystem** - Items, equipment, loot drops
- **VisibilitySystem** - Fog of war with shadowcasting

## Gameplay Loop 🔄

1. **Login** → Create/select character
2. **Spawn** → Start in town (safe zone)
3. **Explore** → Venture into wilderness
4. **Fight** → Real-time combat with monsters
5. **Loot** → Collect items and gold
6. **Level** → Gain XP, improve stats
7. **Die** → Respawn in town
8. **Repeat** → Each run gets harder/deeper

## The Starter World 🗺️

```
100×100 tile area with:
- Town center (safe zone with NPCs)
- Wilderness zones (enemies)
- Dungeon entrance (stairs down)
- Items scattered around
```

Enemy Types:
- 🟢 **Goblins** - Weak, drop ears
- 🔵 **Wolves** - Fast, drop bones  
- 🟤 **Orcs** - Strong, drop weapons
- ⚪ **Skeletons** - Medium, drop bones & gear

## Development 🛠️

### Run Tests
```bash
python3 test_connection.py
```

### Debug Mode
Press `F3` in-game to show:
- FPS counter
- Network latency
- Entity count
- Player position
- Server tick

### Adding New Features

**New Component:**
```python
# backend/components/core.py
@dataclass
class MyComponent:
    value: int = 0
```

**New System:**
```python
# backend/systems/my_system.py
class MySystem(System):
    def _do_update(self, dt: float, world: World):
        for entity, (my_comp,) in world.query(MyComponent):
            # Process entities
            pass
```

## Roadmap 🗺️

- [x] Core ECS engine
- [x] Real-time combat
- [x] Multiplayer networking
- [x] Terminal UI with CRT effects
- [x] Procedural world generation
- [x] Basic AI
- [ ] Database persistence
- [ ] More dungeon levels
- [ ] Skills & abilities
- [ ] Quests
- [ ] PvP zones

## License 📄

MIT License - See LICENSE file

## Credits 🙏

Inspired by:
- Dwarf Fortress
- NetHack
- Caves of Qud
- Cataclysm: DDA

---

*"In the depths of the Mind Rune, adventure awaits..."*
