"""
Mind Rune - A Minimalist Multiplayer Roguelike MMO
Backend API Server with WebSocket support
"""
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Dict, Set
import uvicorn

from auth import create_access_token, verify_token, hash_password, verify_password
from database import init_db, get_db
from models import User, Character, Position
from game import GameWorld, ConnectionManager

# Initialize game world and connection manager
game_world = GameWorld()
connection_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and game world on startup"""
    await init_db()
    print("🎮 Mind Rune server starting...")
    print("📡 WebSocket endpoint: ws://localhost:8000/ws")
    yield
    print("🛑 Mind Rune server shutting down...")


app = FastAPI(
    title="Mind Rune API",
    description="Backend for Mind Rune - A Minimalist Multiplayer Roguelike MMO",
    version="0.1.0",
    lifespan=lifespan
)

# CORS configuration for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API health check"""
    return {
        "name": "Mind Rune API",
        "version": "0.1.0",
        "status": "running",
        "players_online": len(connection_manager.active_connections),
    }


@app.post("/auth/register")
async def register(username: str, password: str, db=Depends(get_db)):
    """Register a new user account"""
    # Check if username already exists
    existing_user = await db.get_user_by_username(username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = hash_password(password)
    user = await db.create_user(username, hashed_password)
    
    # Create starting character for user
    character = await db.create_character(
        user_id=user["id"],
        name=username,
        position=Position(x=0, y=0)
    )
    
    # Generate access token
    access_token = create_access_token(data={"sub": username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": username,
        "character_id": character["id"]
    }


@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    """Login with username and password"""
    user = await db.get_user_by_username(form_data.username)
    
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user["username"]})
    
    # Get user's character
    character = await db.get_character_by_user_id(user["id"])
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user["username"],
        "character_id": character["id"] if character else None
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """
    WebSocket endpoint for real-time game communication
    Client should send token as query parameter: /ws?token=xxx
    """
    await websocket.accept()
    
    username = None
    character_id = None
    
    try:
        # Authenticate via token
        if not token:
            await websocket.send_json({"error": "Authentication token required"})
            await websocket.close()
            return
        
        username = verify_token(token)
        if not username:
            await websocket.send_json({"error": "Invalid token"})
            await websocket.close()
            return
        
        # Get character
        async with get_db() as db:
            user = await db.get_user_by_username(username)
            character = await db.get_character_by_user_id(user["id"])
            character_id = character["id"]
        
        # Add to game world
        await connection_manager.connect(username, character_id, websocket)
        await game_world.add_player(character_id, character["name"], character["position"])
        
        # Send initial game state
        await websocket.send_json({
            "type": "init",
            "character_id": character_id,
            "position": character["position"],
            "world": game_world.get_visible_area(character["position"]),
            "players": game_world.get_nearby_players(character["position"])
        })
        
        # Broadcast player joined
        await connection_manager.broadcast({
            "type": "player_joined",
            "username": username,
            "character_id": character_id
        }, exclude=websocket)
        
        # Main game loop - listen for commands
        while True:
            data = await websocket.receive_json()
            await handle_game_command(data, character_id, username, websocket, db)
            
    except WebSocketDisconnect:
        if username and character_id:
            await connection_manager.disconnect(username)
            await game_world.remove_player(character_id)
            await connection_manager.broadcast({
                "type": "player_left",
                "username": username
            })
    except Exception as e:
        print(f"WebSocket error for {username}: {e}")
        if username:
            await connection_manager.disconnect(username)


async def handle_game_command(data: dict, character_id: int, username: str, websocket: WebSocket, db):
    """Handle incoming game commands from player"""
    command_type = data.get("type")
    
    if command_type == "move":
        direction = data.get("direction")
        new_position = await game_world.move_player(character_id, direction)
        
        if new_position:
            # Update database
            async with get_db() as db:
                await db.update_character_position(character_id, new_position)
            
            # Send update to player
            await websocket.send_json({
                "type": "move_success",
                "position": new_position.__dict__,
                "world": game_world.get_visible_area(new_position)
            })
            
            # Broadcast to nearby players
            await connection_manager.broadcast({
                "type": "player_moved",
                "character_id": character_id,
                "username": username,
                "position": new_position.__dict__
            }, exclude=websocket)
    
    elif command_type == "chat":
        message = data.get("message", "")
        await connection_manager.broadcast({
            "type": "chat",
            "username": username,
            "message": message
        })
    
    elif command_type == "ping":
        await websocket.send_json({"type": "pong"})


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
