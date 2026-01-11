# Mind Rune - How to Play

## Getting Started

### 1. Start the Game

**Start the backend server:**
```bash
python3 backend/main.py
```

**Start the frontend (in another terminal):**
```bash
cd frontend
python3 -m http.server 8080
```

**Open your browser:**
```
http://localhost:8080
```

### 2. Login

Test accounts are available:
- Username: `test` / Password: `test`
- Username: `player1` / Password: `password1`
- Username: `player2` / Password: `password2`

Or click "Register" to create a new account!

### 3. Controls

| Key | Action |
|-----|--------|
| **W** or **↑** | Move North |
| **A** or **←** | Move West |
| **S** or **↓** | Move South |
| **D** or **→** | Move East |
| **Space** | Interact with object/NPC |
| **G** | Pick up item |
| **I** | Open/close inventory |
| **C** | Character sheet |
| **M** | Toggle minimap |
| **T** | Open chat |
| **H** | Show help |
| **<** or **>** | Use stairs up/down |
| **F3** | Toggle debug info |

## The World

You spawn in the **Town Center** - a safe zone where no monsters attack.

### Legend (What you see on screen)

| Symbol | Meaning |
|--------|---------|
| `@` | You (the player) |
| `.` | Floor |
| `,` | Grass |
| `#` | Wall |
| `~` | Water |
| `t` | Tree |
| `^` | Mountain |
| `<` | Stairs up |
| `>` | Stairs down |
| `+` | Door |
| `g` | Goblin |
| `w` | Wolf |
| `O` | Orc |
| `s` | Skeleton |
| `M` | Merchant |
| `I` | Innkeeper |
| `B` | Blacksmith |
| `E` | Elder |

### Areas

1. **Town** (center) - Safe zone with friendly NPCs
2. **Wilderness** (surrounding) - Monsters roam here
3. **Dungeon** (south) - Enter via stairs for deeper challenges

## Combat

Combat is **real-time** - no turns!

- Walk into an enemy to attack
- Enemies attack back automatically
- HP regenerates slowly out of combat
- When you die, you respawn in town

### Enemy Difficulty

- **Goblins** (🟢 green `g`) - Easy, Level 1
- **Wolves** (⚫ gray `w`) - Easy, Level 1
- **Skeletons** (⚪ white `s`) - Medium, Level 2
- **Orcs** (🟤 dark green `O`) - Hard, Level 3

### Leveling Up

- Kill enemies to gain XP
- Level up to increase stats
- Higher level = more HP, damage, and survival

## Tips

1. **Don't rush!** Combat is real-time, take it slow
2. **Watch your HP** - Retreat to town when low
3. **Explore carefully** - Enemies may chase you
4. **Check the minimap** - M key toggles it
5. **Talk to NPCs** - Walk into them to interact

## CRT Effects

Toggle the CRT effects for authentic retro experience:
- Scanlines
- Phosphor glow
- Screen curvature
- Chromatic aberration

The effects are on by default for maximum immersion!

## Multiplayer

Other players appear as yellow `@` symbols. You can:
- See them move in real-time
- Chat with them (press T)
- Explore together

## Troubleshooting

### Can't connect?
- Make sure the server is running (`python3 backend/main.py`)
- Check that port 8765 is not blocked
- Try refreshing the page

### Game is slow?
- Press F3 to check FPS
- Disable CRT effects if needed
- Close other browser tabs

### Lost?
- Press H for help
- Press M for minimap
- The town is always at (8, 8)

---

**Have fun adventuring in Mind Rune!** 🎮
