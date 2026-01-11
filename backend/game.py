"""
Game world logic for Mind Rune
Handles world generation, player management, and game mechanics
"""
import random
from typing import Dict, Set, Optional, List
from fastapi import WebSocket
from models import Position, Tile


class GameWorld:
    """Manages the game world state"""
    
    def __init__(self, width: int = 100, height: int = 100):
        self.width = width
        self.height = height
        self.players: Dict[int, Dict] = {}  # character_id -> player data
        self.terrain_cache: Dict[tuple, str] = {}
    
    async def add_player(self, character_id: int, name: str, position: dict):
        """Add a player to the world"""
        self.players[character_id] = {
            "name": name,
            "position": Position(**position) if isinstance(position, dict) else position,
            "health": 100,
            "level": 1
        }
        print(f"✨ Player {name} joined at ({position})")
    
    async def remove_player(self, character_id: int):
        """Remove a player from the world"""
        if character_id in self.players:
            name = self.players[character_id]["name"]
            del self.players[character_id]
            print(f"👋 Player {name} left")
    
    async def move_player(self, character_id: int, direction: str) -> Optional[Position]:
        """Move a player in a direction (n/s/e/w/ne/nw/se/sw)"""
        if character_id not in self.players:
            return None
        
        current_pos = self.players[character_id]["position"]
        new_x, new_y = current_pos.x, current_pos.y
        
        # Calculate new position
        if 'n' in direction:
            new_y -= 1
        if 's' in direction:
            new_y += 1
        if 'e' in direction:
            new_x += 1
        if 'w' in direction:
            new_x -= 1
        
        # Check bounds
        if 0 <= new_x < self.width and 0 <= new_y < self.height:
            # Check if terrain is walkable
            if self.is_walkable(new_x, new_y):
                new_pos = Position(x=new_x, y=new_y)
                self.players[character_id]["position"] = new_pos
                return new_pos
        
        return None
    
    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a tile is walkable"""
        terrain = self.get_terrain(x, y)
        return terrain not in ['#', '~']  # Walls and water not walkable
    
    def get_terrain(self, x: int, y: int) -> str:
        """Get terrain type at position (procedurally generated)"""
        # Use simple procedural generation with seeded randomness
        key = (x, y)
        if key not in self.terrain_cache:
            # Deterministic pseudo-random terrain
            seed_value = (x * 73856093) ^ (y * 19349663)
            random.seed(seed_value)
            
            rand = random.random()
            if rand < 0.05:
                terrain = '#'  # Wall
            elif rand < 0.10:
                terrain = '~'  # Water
            elif rand < 0.15:
                terrain = '^'  # Mountain
            elif rand < 0.20:
                terrain = 't'  # Tree
            else:
                terrain = '.'  # Ground
            
            self.terrain_cache[key] = terrain
        
        return self.terrain_cache[key]
    
    def get_visible_area(self, position: dict, radius: int = 10) -> List[List[str]]:
        """Get visible tiles around a position"""
        if isinstance(position, dict):
            pos = Position(**position)
        else:
            pos = position
        
        view = []
        for y in range(pos.y - radius, pos.y + radius + 1):
            row = []
            for x in range(pos.x - radius, pos.x + radius + 1):
                if 0 <= x < self.width and 0 <= y < self.height:
                    # Check if another player is at this position
                    player_here = None
                    for pid, pdata in self.players.items():
                        ppos = pdata["position"]
                        if ppos.x == x and ppos.y == y:
                            player_here = '@'
                            break
                    
                    if player_here:
                        row.append(player_here)
                    else:
                        row.append(self.get_terrain(x, y))
                else:
                    row.append(' ')  # Out of bounds
            view.append(row)
        
        return view
    
    def get_nearby_players(self, position: dict, radius: int = 20) -> List[Dict]:
        """Get list of nearby players"""
        if isinstance(position, dict):
            pos = Position(**position)
        else:
            pos = position
        
        nearby = []
        for char_id, player in self.players.items():
            ppos = player["position"]
            distance = abs(ppos.x - pos.x) + abs(ppos.y - pos.y)  # Manhattan distance
            if distance <= radius:
                nearby.append({
                    "character_id": char_id,
                    "name": player["name"],
                    "position": ppos.__dict__,
                    "distance": distance
                })
        
        return nearby


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, username: str, character_id: int, websocket: WebSocket):
        """Register a new connection"""
        self.active_connections[username] = websocket
        print(f"🔌 {username} connected (total: {len(self.active_connections)})")
    
    async def disconnect(self, username: str):
        """Remove a connection"""
        if username in self.active_connections:
            del self.active_connections[username]
            print(f"🔌 {username} disconnected (total: {len(self.active_connections)})")
    
    async def send_personal_message(self, message: dict, username: str):
        """Send message to specific user"""
        if username in self.active_connections:
            await self.active_connections[username].send_json(message)
    
    async def broadcast(self, message: dict, exclude: WebSocket = None):
        """Send message to all connected users"""
        for username, connection in self.active_connections.items():
            if connection != exclude:
                try:
                    await connection.send_json(message)
                except:
                    pass  # Connection might be closed
