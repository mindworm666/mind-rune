"""
Data models for Mind Rune
"""
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Position:
    """Represents a 2D position in the game world"""
    x: int
    y: int
    
    def __dict__(self):
        return {"x": self.x, "y": self.y}


@dataclass
class User:
    """User account model"""
    id: int
    username: str
    password_hash: str
    created_at: str


@dataclass
class Character:
    """Player character model"""
    id: int
    user_id: int
    name: str
    position: Position
    health: int = 100
    level: int = 1
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "position": self.position.__dict__,
            "health": self.health,
            "level": self.level
        }


@dataclass
class Tile:
    """Represents a single tile in the world"""
    x: int
    y: int
    terrain: str  # '.', '#', '~', '^' etc.
    walkable: bool = True
    
    def to_char(self) -> str:
        """Return ASCII character for this tile"""
        return self.terrain
