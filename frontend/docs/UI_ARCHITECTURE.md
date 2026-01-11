# Terminal UI Architecture

## Philosophy

**Mind Rune's UI is a love letter to vintage CRT terminals.** Every pixel, every glow, every scanline is deliberate. We embrace negative space, use ASCII art for everything, and make the limitations of terminal rendering our greatest strength.

## Core Principles

1. **Terminal First** - Everything renders as if it's a 1980s terminal
2. **Negative Space** - Empty space is beautiful, don't clutter
3. **Monospace Everything** - Fixed-width fonts, character grid
4. **Real-Time Updates** - 60 FPS rendering with smooth interpolation
5. **Performance Budget** - <16ms frame time, <50MB memory
6. **Accessibility** - High contrast, keyboard-first, screen reader support

---

## Layout System

### Main Screen Layout (80×24 minimum, scales to 120×40)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ MIND RUNE v0.1.0                                    [HP ████████░░ 80/100]  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                      [MP ██████░░░░ 60/100]  ║
║                        GAME VIEWPORT                 [XP ███░░░░░░░  3/10]  ║
║                                                                              ║
║          . . . . # # # # . . . .                     STR: 10  DEX: 12        ║
║          . . t . # . . # . . . .                     INT:  8  VIT: 14        ║
║          . . . . # . @ # . ^ ^ .                                             ║
║          ~ ~ . . . . . . . ^ ^ .                     LVL: 2  XP: 30%         ║
║          ~ ~ ~ . . E . . . . . .                                             ║
║          ~ ~ . . . . . . . t . .                     ┌─────────────────┐    ║
║          . . . . . . P . . . . .                     │ Rusty Sword   1 │    ║
║          . . . # # # . . . . . .                     │ Health Potion 3 │    ║
║          . . . # . # . . . . . .                     └─────────────────┘    ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ > You hit the goblin for 12 damage!                                         ║
║ > Goblin attacks you for 5 damage.                                          ║
║ > You gained 15 experience.                                                 ║
║ > Player "Aragorn" entered the zone.                                        ║
║ [T to chat] [I for inventory] [C for character]        Latency: 45ms  FPS:60║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### Layout Zones

#### 1. Header Bar (2 lines)
- Title + version (left)
- HP/MP/XP bars (right)
- Connection status indicator

#### 2. Main Content Area (Split view)
- **Left: Game Viewport** (60% width)
  - 3D world rendered in 2D
  - ASCII tiles
  - Entities (players, NPCs, items)
  - Camera centered on player
  
- **Right: Status Panel** (40% width)
  - Character stats
  - Active buffs/debuffs
  - Quickslot inventory
  - Minimap (optional)

#### 3. Message Log (4 lines)
- Combat messages
- System notifications
- Chat messages
- Scrollable history (1000 lines)

#### 4. Status Line (1 line)
- Available commands
- Debug info (FPS, latency, entity count)

---

## Component Architecture

### Base Component Class

All UI components inherit from `UIComponent`:

```javascript
class UIComponent {
  constructor(x, y, width, height) {
    this.bounds = { x, y, width, height };
    this.visible = true;
    this.dirty = true;
    this.buffer = null;
  }
  
  render(ctx) { /* Override */ }
  update(deltaTime) { /* Override */ }
  handleInput(event) { /* Override */ }
  markDirty() { this.dirty = true; }
}
```

### Core Components

#### Viewport Component
- Renders the game world
- Handles camera movement
- Tile rendering with color
- Entity sprite rendering
- Z-level visualization
- Fog of war overlay

#### StatusPanel Component
- HP/MP/XP bars with animations
- Character stats display
- Active effects with timers
- Equipment preview
- Cooldown indicators

#### MessageLog Component
- Circular buffer (1000 messages)
- Auto-scroll on new messages
- Color coding by message type
- Timestamp display (optional)
- Search/filter functionality

#### InventoryPanel Component
- Grid or list view
- Item tooltips
- Drag and drop support
- Stack counts
- Rarity color coding

#### ChatInput Component
- Text input with history
- Command autocomplete
- Emote support
- Chat channels

#### Minimap Component
- 16×16 overview
- Player position indicator
- Major landmarks
- Fog of war

---

## Rendering Pipeline

### Frame Cycle (60 FPS)

```
1. Input Processing (keyboard/mouse)
   ↓
2. Network Update (process incoming messages)
   ↓
3. State Update (game logic, animations)
   ↓
4. Dirty Check (which components changed?)
   ↓
5. Component Render (only dirty components)
   ↓
6. Composite (draw to main canvas)
   ↓
7. Post-Processing (CRT effects)
   ↓
8. Display
```

### Double Buffering

- Each component renders to its own offscreen canvas
- Only redraw components marked dirty
- Composite all buffers to main canvas
- Apply CRT effects as final pass

### Dirty Tracking

Components mark themselves dirty when:
- Data changes (HP update, new message, etc.)
- Animation frame update
- Window resize
- User interaction

---

## CRT Aesthetic Specifications

### Color Palette

**Primary Phosphor Colors:**
```css
--phosphor-green:   #33ff33
--phosphor-amber:   #ffb000
--phosphor-white:   #f0f0f0
--phosphor-cyan:    #00ffff

--background:       #0a0a0a
--shadow:           #001100
--highlight:        #66ff66
--glow:             #33ff3377
```

**Semantic Colors:**
```css
--hp-color:         #ff3333  /* Red */
--mp-color:         #3333ff  /* Blue */
--xp-color:         #33ff33  /* Green */
--damage-color:     #ff6666
--heal-color:       #66ff66
--system-color:     #ffff66
--chat-color:       #66ffff
```

### Visual Effects

1. **Scanlines** - Horizontal lines across entire screen, 2px spacing
2. **Phosphor Glow** - Text-shadow with blur for CRT glow
3. **Screen Curvature** - Subtle barrel distortion (optional)
4. **Chromatic Aberration** - RGB channel offset (subtle)
5. **Vignette** - Darkened edges
6. **Flicker** - Subtle brightness variation (1-2%)
7. **Bloom** - Bright text bleeds slightly
8. **Noise** - Subtle static overlay (5% opacity)

### Typography

**Primary Font Stack:**
```css
font-family: 'IBM Plex Mono', 'Courier New', 'Courier', monospace;
font-size: 14px;
line-height: 1.2;
letter-spacing: 0.05em;
```

**Character Set:**
- Standard ASCII (32-126)
- Box-drawing characters (─│┌┐└┘├┤┬┴┼)
- Block elements (░▒▓█)
- Arrows (↑→↓←)
- Symbols (@#$%&*+=)

---

## Responsive Design

### Breakpoints

- **Small** (80×24): Minimal UI, single column
- **Medium** (100×30): Standard split view
- **Large** (120×40): Extra panels, more viewport

### Scaling Strategy

- Use CSS viewport units for sizing
- Scale font-size based on window dimensions
- Maintain aspect ratio of character grid
- Hide optional components on small screens

---

## Performance Optimization

### Rendering Optimizations

1. **Viewport Culling** - Only render visible tiles
2. **Dirty Rectangles** - Only redraw changed areas
3. **Object Pooling** - Reuse canvas contexts
4. **Batched Drawing** - Group similar operations
5. **RequestAnimationFrame** - Use browser timing

### Memory Management

- Limit message log to 1000 entries
- Cache rendered tiles as sprites
- LRU cache for entity sprites
- Throttle non-critical updates

### Network Optimization

- Delta compression for state updates
- Predictive movement (client-side)
- Priority-based message queue
- Binary protocol for efficiency

---

## Accessibility

### Keyboard Navigation

- **Tab/Shift-Tab** - Cycle through UI components
- **Enter** - Activate focused element
- **ESC** - Cancel/close dialogs
- **Arrow keys** - Navigate lists/grids
- All game actions have keybinds

### Screen Reader Support

- ARIA labels on all interactive elements
- Role attributes for semantic structure
- Live regions for dynamic content
- Skip navigation links

### Colorblind Modes

- High contrast option
- Alternative color palettes
- Icon-based status indicators
- Customizable color schemes

---

## State Management

### Client State Structure

```javascript
{
  // Connection
  connection: {
    status: 'connected' | 'connecting' | 'disconnected',
    latency: 45,
    lastUpdate: timestamp
  },
  
  // Player
  player: {
    entityId: 12345,
    position: { x, y, z },
    stats: { hp, maxHp, mp, maxMp, ... },
    inventory: [...],
    equipment: {...},
    buffs: [...]
  },
  
  // World
  world: {
    chunks: Map<chunkKey, ChunkData>,
    entities: Map<entityId, EntityData>,
    visibleEntities: Set<entityId>
  },
  
  // UI State
  ui: {
    scene: 'game' | 'login' | 'character',
    activePanel: 'inventory' | 'character' | null,
    chatMode: false,
    tooltipTarget: entityId | null
  },
  
  // Messages
  messages: CircularBuffer<Message>
}
```

### State Updates

- **Immutable updates** - Never mutate state directly
- **Event-driven** - Components subscribe to state changes
- **Validation** - Enforce invariants client-side
- **Rollback** - Handle server corrections

---

## Input System

### Input Modes

1. **Normal Mode** - WASD movement, hotkeys
2. **Chat Mode** - Text input active
3. **Menu Mode** - Dialog/inventory navigation
4. **Targeting Mode** - Select targets for skills

### Keybindings

#### Core Actions
- **W/A/S/D** or **Arrow Keys** - Move
- **Space** - Interact/pickup
- **Tab** - Cycle targets
- **Shift+Click** - Examine entity

#### UI Actions
- **I** - Toggle inventory
- **C** - Toggle character sheet
- **M** - Toggle map
- **T** - Chat mode
- **ESC** - Cancel/close

#### Combat Actions
- **1-9** - Use hotbar skill/item
- **F** - Auto-attack toggle
- **R** - Target nearest enemy

#### System Actions
- **F11** - Toggle fullscreen
- **F12** - Toggle debug overlay
- **+/-** - Zoom in/out

### Mouse Support

- **Click tile** - Move to location
- **Click entity** - Target/interact
- **Hover** - Show tooltip
- **Right-click** - Context menu
- **Drag** - Move items (inventory)

---

## Animation System

### Supported Animations

1. **Character Movement** - Linear interpolation between tiles
2. **HP/MP Changes** - Smooth bar transitions with easing
3. **Damage Numbers** - Float up and fade out
4. **Buff Icons** - Pulse on application
5. **Level Up** - Flash and particle effect
6. **Attack Swing** - Quick sprite shake
7. **Loot Sparkle** - Rotating glow on items

### Animation Queue

- Priority-based execution
- Cancel on state change
- Pooled animation objects
- Delta-time based timing

---

## Error Handling

### User-Facing Errors

- **Connection Lost** - Show reconnecting overlay
- **Invalid Command** - Display error in message log
- **Server Error** - Friendly message with retry
- **Version Mismatch** - Prompt to reload

### Debug Mode

- **F12** toggles debug overlay
- Shows: FPS, entity count, memory usage
- Network message log
- State inspector
- Performance graphs

---

## Development Workflow

### Hot Reload

- CSS changes reload instantly
- JS modules reload on change
- State preserved across reloads (localStorage)

### Testing

- Unit tests for components (Jest)
- E2E tests for user flows (Playwright)
- Visual regression tests (Percy)
- Performance benchmarks

### Browser Support

- **Chrome/Edge** 90+ (primary target)
- **Firefox** 88+
- **Safari** 14+
- Graceful degradation for older browsers

---

## File Structure

```
frontend/
├── index.html                 # Main HTML shell
├── css/
│   ├── terminal.css          # Base terminal styles
│   ├── crt-effects.css       # CRT visual effects
│   ├── components.css        # Component styles
│   └── themes.css            # Color themes
├── js/
│   ├── main.js               # Entry point
│   ├── game.js               # Game class
│   ├── renderer.js           # Rendering engine
│   ├── viewport.js           # Viewport management
│   ├── input.js              # Input handling
│   ├── network.js            # WebSocket client
│   ├── state-manager.js      # State management
│   ├── entity-cache.js       # Entity caching
│   ├── components/
│   │   ├── ui-component.js   # Base class
│   │   ├── viewport.js       # Game viewport
│   │   ├── status-panel.js   # Status display
│   │   ├── message-log.js    # Message log
│   │   ├── inventory.js      # Inventory UI
│   │   └── minimap.js        # Minimap
│   └── utils/
│       ├── color.js          # Color utilities
│       ├── text.js           # Text rendering
│       └── math.js           # Vector/grid math
└── assets/
    ├── fonts/                # Monospace fonts
    └── sounds/               # UI sounds (optional)
```

---

## Next Steps

1. ✅ Architecture designed
2. ⏭️ Implement CSS styling system
3. ⏭️ Build core rendering engine
4. ⏭️ Create UI components
5. ⏭️ Implement input handling
6. ⏭️ Build networking layer
7. ⏭️ Integrate with backend
8. ⏭️ Polish and optimize

**This architecture ensures scalability, maintainability, and that sweet, sweet CRT aesthetic!** 🖥️✨
