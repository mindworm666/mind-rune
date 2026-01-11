"""
Database layer for Mind Rune using SQLite
"""
import aiosqlite
from typing import Optional, Dict
from datetime import datetime
from models import Position

DATABASE_PATH = "mindrune.db"


class Database:
    """Async database wrapper"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.connection = None
    
    async def __aenter__(self):
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            await self.connection.close()
    
    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def create_user(self, username: str, password_hash: str) -> Dict:
        """Create a new user"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, password_hash, datetime.utcnow().isoformat())
            )
            await db.commit()
            user_id = cursor.lastrowid
            
            return {
                "id": user_id,
                "username": username,
                "password_hash": password_hash,
                "created_at": datetime.utcnow().isoformat()
            }
    
    async def get_character_by_user_id(self, user_id: int) -> Optional[Dict]:
        """Get character for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM characters WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    char_dict = dict(row)
                    char_dict["position"] = Position(x=char_dict["pos_x"], y=char_dict["pos_y"])
                    return char_dict
                return None
    
    async def create_character(self, user_id: int, name: str, position: Position) -> Dict:
        """Create a new character"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """INSERT INTO characters 
                (user_id, name, pos_x, pos_y, health, level) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, name, position.x, position.y, 100, 1)
            )
            await db.commit()
            char_id = cursor.lastrowid
            
            return {
                "id": char_id,
                "user_id": user_id,
                "name": name,
                "position": position,
                "health": 100,
                "level": 1
            }
    
    async def update_character_position(self, character_id: int, position: Position):
        """Update character position"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE characters SET pos_x = ?, pos_y = ? WHERE id = ?",
                (position.x, position.y, character_id)
            )
            await db.commit()


async def init_db():
    """Initialize database tables"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Characters table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                pos_x INTEGER NOT NULL DEFAULT 0,
                pos_y INTEGER NOT NULL DEFAULT 0,
                health INTEGER NOT NULL DEFAULT 100,
                level INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        await db.commit()
        print("✅ Database initialized")


def get_db():
    """Dependency for getting database connection"""
    return Database()
