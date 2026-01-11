"""
Mind Rune - WebSocket Game Server

Handles client connections, authentication, and message routing.
Integrates with ECS game loop for real-time multiplayer.

Uses custom WebSocket implementation (no external dependencies).
"""

import asyncio
import json
import logging
import time
import hashlib
import secrets
from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from backend.server.websocket import WebSocketServer, WebSocketConnection
from backend.server.protocol import Message, MessageType, MessageBuilder, EntityData
from backend.engine.ecs import World, Entity
from backend.engine.game_loop import GameLoop
from backend.engine.spatial import SpatialHashGrid
from backend.components.core import (
    Position, Velocity, Stats, CombatState, Cooldowns, Player, Sprite,
    Identity, EntityType, Vision, Inventory, AI, AIState, Faction, Respawn
)

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Client connection states"""
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating" 
    AUTHENTICATED = "authenticated"
    IN_GAME = "in_game"
    DISCONNECTING = "disconnecting"


@dataclass
class ClientConnection:
    """Represents a connected client"""
    websocket: WebSocketConnection
    connection_id: str
    state: ConnectionState = ConnectionState.CONNECTED
    
    # Auth
    account_id: Optional[int] = None
    username: Optional[str] = None
    
    # Game
    player_entity: Optional[Entity] = None
    
    # Stats
    connected_at: float = field(default_factory=time.time)
    last_message_at: float = field(default_factory=time.time)
    messages_received: int = 0
    messages_sent: int = 0
    
    # Rate limiting
    action_timestamps: List[float] = field(default_factory=list)
    
    def is_rate_limited(self, max_per_second: int = 20) -> bool:
        """Check if client is sending too many messages"""
        now = time.time()
        self.action_timestamps = [t for t in self.action_timestamps if now - t < 1.0]
        return len(self.action_timestamps) >= max_per_second


@dataclass
class PlayerAction:
    """Queued player action to process on next tick"""
    entity: Entity
    action_type: str
    data: Dict[str, Any]
    timestamp: float


class GameServer:
    """
    Main game server.
    
    Manages:
    - WebSocket connections
    - Authentication
    - Player spawning/despawning
    - Action queue processing
    - State broadcasting
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        
        # WebSocket server
        self.ws_server: Optional[WebSocketServer] = None
        
        # Connections
        self.connections: Dict[str, ClientConnection] = {}
        self.entity_to_connection: Dict[Entity, str] = {}
        
        # Game state
        self.game_loop: Optional[GameLoop] = None
        self.world: Optional[World] = None
        self.spatial_index: Optional[SpatialHashGrid] = None
        self.world_3d = None
        
        # Action queue
        self.action_queue: List[PlayerAction] = []
        self.action_queue_lock = asyncio.Lock()
        
        # Simple user database
        self.users: Dict[str, Dict] = {
            "test": {"password_hash": self._hash_password("test"), "account_id": 1},
            "player1": {"password_hash": self._hash_password("password1"), "account_id": 2},
            "player2": {"password_hash": self._hash_password("password2"), "account_id": 3},
        }
        self.next_account_id = 4
        
        # Server state
        self.running = False
        
        logger.info(f"GameServer initialized on {host}:{port}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    # ========================================================================
    # SERVER LIFECYCLE
    # ========================================================================
    
    async def start(self, game_loop: GameLoop, world_3d) -> None:
        """Start the server"""
        self.game_loop = game_loop
        self.world = game_loop.get_world()
        self.world_3d = world_3d
        
        # Create spatial index
        self.spatial_index = SpatialHashGrid(cell_size=16.0)
        
        # Register tick callback
        self.game_loop.add_on_tick_end(self._on_tick_end)
        
        # Create WebSocket server
        self.ws_server = WebSocketServer(self.host, self.port)
        self.ws_server.on_connect = self._handle_connect
        self.ws_server.on_disconnect = self._handle_disconnect
        self.ws_server.on_message = self._handle_message
        
        await self.ws_server.start()
        self.running = True
        
        logger.info(f"Game server started on ws://{self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the server"""
        self.running = False
        
        # Close all connections
        for conn in list(self.connections.values()):
            await self._disconnect_client(conn, "Server shutting down")
        
        # Stop WebSocket server
        if self.ws_server:
            await self.ws_server.stop()
        
        logger.info("Server stopped")
    
    # ========================================================================
    # CONNECTION HANDLING
    # ========================================================================
    
    async def _handle_connect(self, ws_conn: WebSocketConnection) -> None:
        """Handle new WebSocket connection"""
        client = ClientConnection(
            websocket=ws_conn,
            connection_id=ws_conn.connection_id,
            state=ConnectionState.CONNECTED
        )
        
        self.connections[ws_conn.connection_id] = client
        logger.info(f"Client connected: {ws_conn.connection_id}")
        
        # Send welcome message
        await self._send(client, MessageBuilder.system_message(
            "Welcome to Mind Rune! Please login or register."
        ))
    
    async def _handle_disconnect(self, ws_conn: WebSocketConnection) -> None:
        """Handle WebSocket disconnect"""
        conn_id = ws_conn.connection_id
        if conn_id in self.connections:
            client = self.connections[conn_id]
            await self._disconnect_client(client, "Connection closed")
    
    async def _disconnect_client(self, client: ClientConnection, reason: str) -> None:
        """Clean up disconnected client"""
        conn_id = client.connection_id
        
        # Remove player entity
        if client.player_entity is not None and self.world.is_alive(client.player_entity):
            # Notify other players
            await self._broadcast_except(client, MessageBuilder.entity_despawn(client.player_entity))
            
            # Remove from spatial index
            self.spatial_index.remove(client.player_entity)
            
            # Destroy entity
            self.world.destroy_entity(client.player_entity)
            
            # Remove mapping
            if client.player_entity in self.entity_to_connection:
                del self.entity_to_connection[client.player_entity]
        
        # Remove connection
        if conn_id in self.connections:
            del self.connections[conn_id]
        
        logger.info(f"Client {conn_id} cleaned up: {reason}")
    
    # ========================================================================
    # MESSAGE HANDLING
    # ========================================================================
    
    async def _handle_message(self, ws_conn: WebSocketConnection, raw: str) -> None:
        """Process incoming message"""
        conn_id = ws_conn.connection_id
        if conn_id not in self.connections:
            return
        
        client = self.connections[conn_id]
        client.last_message_at = time.time()
        client.messages_received += 1
        
        try:
            msg = Message.from_json(raw)
        except Exception as e:
            logger.warning(f"Invalid message from {conn_id}: {e}")
            await self._send(client, MessageBuilder.error("INVALID_MESSAGE", str(e)))
            return
        
        # Rate limiting
        if client.is_rate_limited():
            await self._send(client, MessageBuilder.error("RATE_LIMITED", "Too many messages"))
            return
        
        client.action_timestamps.append(time.time())
        
        # Route message
        handlers = {
            MessageType.AUTH_LOGIN: self._handle_login,
            MessageType.AUTH_REGISTER: self._handle_register,
            MessageType.AUTH_LOGOUT: self._handle_logout,
            MessageType.PLAYER_MOVE: self._handle_move,
            MessageType.PLAYER_ATTACK: self._handle_attack,
            MessageType.PLAYER_INTERACT: self._handle_interact,
            MessageType.INVENTORY_PICKUP: self._handle_pickup,
            MessageType.CHAT_SEND: self._handle_chat,
            MessageType.PING: self._handle_ping,
            MessageType.REQUEST_STATE: self._handle_request_state,
        }
        
        handler = handlers.get(msg.type)
        if handler:
            await handler(client, msg)
        else:
            logger.warning(f"Unhandled message type: {msg.type}")
    
    # ========================================================================
    # AUTH HANDLERS
    # ========================================================================
    
    async def _handle_login(self, client: ClientConnection, msg: Message) -> None:
        """Handle login request"""
        username = msg.data.get("username", "")
        password = msg.data.get("password", "")
        
        if not username or not password:
            await self._send(client, MessageBuilder.auth_failure("Missing username or password"))
            return
        
        user = self.users.get(username)
        if not user or user["password_hash"] != self._hash_password(password):
            await self._send(client, MessageBuilder.auth_failure("Invalid credentials"))
            return
        
        # Check if already logged in
        for conn in self.connections.values():
            if conn.account_id == user["account_id"] and conn.connection_id != client.connection_id:
                await self._send(client, MessageBuilder.auth_failure("Already logged in"))
                return
        
        # Set auth state
        client.state = ConnectionState.AUTHENTICATED
        client.account_id = user["account_id"]
        client.username = username
        
        # Spawn player
        spawn_x, spawn_y, spawn_z = 8.0, 8.0, 0.0
        player_entity = self._spawn_player(client, spawn_x, spawn_y, spawn_z)
        
        client.player_entity = player_entity
        client.state = ConnectionState.IN_GAME
        
        self.entity_to_connection[player_entity] = client.connection_id
        
        # Send success
        await self._send(client, MessageBuilder.auth_success(
            player_entity, username, spawn_x, spawn_y, spawn_z
        ))
        
        # Send initial state
        await self._send_full_state(client)
        
        # Notify others
        entity_data = self._entity_to_data(player_entity)
        if entity_data:
            await self._broadcast_except(client, MessageBuilder.entity_spawn(entity_data))
        
        logger.info(f"Player {username} logged in as entity {player_entity}")
    
    async def _handle_register(self, client: ClientConnection, msg: Message) -> None:
        """Handle registration"""
        username = msg.data.get("username", "")
        password = msg.data.get("password", "")
        
        if not username or not password:
            await self._send(client, MessageBuilder.auth_failure("Missing required fields"))
            return
        
        if len(username) < 3 or len(username) > 20:
            await self._send(client, MessageBuilder.auth_failure("Username must be 3-20 characters"))
            return
        
        if username in self.users:
            await self._send(client, MessageBuilder.auth_failure("Username already taken"))
            return
        
        # Create user
        self.users[username] = {
            "password_hash": self._hash_password(password),
            "account_id": self.next_account_id
        }
        self.next_account_id += 1
        
        await self._send(client, MessageBuilder.system_message(
            f"Account created! You can now login as {username}."
        ))
        
        logger.info(f"New account registered: {username}")
    
    async def _handle_logout(self, client: ClientConnection, msg: Message) -> None:
        """Handle logout"""
        await self._disconnect_client(client, "Logged out")
    
    # ========================================================================
    # GAME ACTION HANDLERS
    # ========================================================================
    
    async def _handle_move(self, client: ClientConnection, msg: Message) -> None:
        """Handle movement"""
        if client.state != ConnectionState.IN_GAME or client.player_entity is None:
            return
        
        dx = max(-1, min(1, msg.data.get("dx", 0)))
        dy = max(-1, min(1, msg.data.get("dy", 0)))
        dz = max(-1, min(1, msg.data.get("dz", 0)))
        
        async with self.action_queue_lock:
            self.action_queue.append(PlayerAction(
                entity=client.player_entity,
                action_type="move",
                data={"dx": dx, "dy": dy, "dz": dz},
                timestamp=time.time()
            ))
    
    async def _handle_attack(self, client: ClientConnection, msg: Message) -> None:
        """Handle attack"""
        if client.state != ConnectionState.IN_GAME or client.player_entity is None:
            return
        
        target_id = msg.data.get("target_id")
        if target_id is None:
            return
        
        async with self.action_queue_lock:
            self.action_queue.append(PlayerAction(
                entity=client.player_entity,
                action_type="attack",
                data={"target_id": target_id},
                timestamp=time.time()
            ))
    
    async def _handle_interact(self, client: ClientConnection, msg: Message) -> None:
        """Handle interaction"""
        if client.state != ConnectionState.IN_GAME or client.player_entity is None:
            return
        
        async with self.action_queue_lock:
            self.action_queue.append(PlayerAction(
                entity=client.player_entity,
                action_type="interact",
                data=msg.data,
                timestamp=time.time()
            ))
    
    async def _handle_pickup(self, client: ClientConnection, msg: Message) -> None:
        """Handle item pickup"""
        if client.state != ConnectionState.IN_GAME or client.player_entity is None:
            return
        
        async with self.action_queue_lock:
            self.action_queue.append(PlayerAction(
                entity=client.player_entity,
                action_type="pickup",
                data=msg.data,
                timestamp=time.time()
            ))
    
    async def _handle_chat(self, client: ClientConnection, msg: Message) -> None:
        """Handle chat"""
        if client.state != ConnectionState.IN_GAME:
            return
        
        message = msg.data.get("message", "").strip()[:500]
        channel = msg.data.get("channel", "local")
        
        if not message:
            return
        
        chat_msg = MessageBuilder.chat_receive(
            client.player_entity,
            client.username or "Unknown",
            message,
            channel
        )
        
        if channel == "local":
            pos = self.world.get_component(client.player_entity, Position)
            if pos:
                nearby = self.spatial_index.query_radius(pos.x, pos.y, pos.z, 30.0)
                for entity in nearby:
                    if entity in self.entity_to_connection:
                        conn = self.connections.get(self.entity_to_connection[entity])
                        if conn:
                            await self._send(conn, chat_msg)
        else:
            await self._broadcast(chat_msg)
    
    async def _handle_ping(self, client: ClientConnection, msg: Message) -> None:
        """Handle ping"""
        await self._send(client, MessageBuilder.pong(msg.data.get("ts", 0)))
    
    async def _handle_request_state(self, client: ClientConnection, msg: Message) -> None:
        """Handle state request"""
        if client.state == ConnectionState.IN_GAME:
            await self._send_full_state(client)
    
    # ========================================================================
    # PLAYER MANAGEMENT
    # ========================================================================
    
    def _spawn_player(self, client: ClientConnection, x: float, y: float, z: float) -> Entity:
        """Spawn player entity"""
        entity = self.world.create_entity()
        
        self.world.add_component(entity, Position, Position(x=x, y=y, z=z))
        self.world.add_component(entity, Stats, Stats(
            strength=15, dexterity=12, constitution=14,
            max_hp=140, max_mp=50, level=1
        ))
        self.world.add_component(entity, CombatState, CombatState(hp=140, mp=50))
        self.world.add_component(entity, Cooldowns, Cooldowns())
        self.world.add_component(entity, Player, Player(
            account_id=client.account_id or 0,
            character_name=client.username or "Unknown",
            connection_id=client.connection_id
        ))
        self.world.add_component(entity, Sprite, Sprite(char="@", color="#ffff00"))
        self.world.add_component(entity, Identity, Identity(
            entity_type=EntityType.PLAYER,
            name=client.username or "Unknown",
            description="A brave adventurer"
        ))
        self.world.add_component(entity, Vision, Vision(radius=20.0))
        self.world.add_component(entity, Inventory, Inventory())
        self.world.add_component(entity, Respawn, Respawn(
            respawn_x=x, respawn_y=y, respawn_z=z
        ))
        
        self.spatial_index.insert(entity, x, y, z)
        return entity
    
    # ========================================================================
    # STATE BROADCASTING
    # ========================================================================
    
    def _on_tick_end(self, tick: int, stats) -> None:
        """Called at end of each tick"""
        asyncio.create_task(self._process_tick(tick))
    
    async def _process_tick(self, tick: int) -> None:
        """Process actions and broadcast state"""
        # Process action queue
        async with self.action_queue_lock:
            actions = self.action_queue.copy()
            self.action_queue.clear()
        
        events = []
        for action in actions:
            event = self._process_action(action)
            if event:
                events.extend(event)
        
        # Broadcast state
        await self._broadcast_delta_state(tick, events)
    
    def _process_action(self, action: PlayerAction) -> Optional[List[Dict]]:
        """Process a single action"""
        entity = action.entity
        
        if not self.world.is_alive(entity):
            return None
        
        if action.action_type == "move":
            pos = self.world.get_component(entity, Position)
            if pos:
                dx = action.data.get("dx", 0)
                dy = action.data.get("dy", 0)
                
                new_x = pos.x + dx
                new_y = pos.y + dy
                
                if self.world_3d and self.world_3d.is_walkable(int(new_x), int(new_y), int(pos.z)):
                    pos.x = new_x
                    pos.y = new_y
                    self.spatial_index.update(entity, pos.x, pos.y, pos.z)
        
        elif action.action_type == "attack":
            target_id = action.data.get("target_id")
            if target_id and self.world.is_alive(target_id):
                combat = self.world.get_component(entity, CombatState)
                if combat:
                    combat.target = target_id
        
        return None
    
    async def _send_full_state(self, client: ClientConnection) -> None:
        """Send full game state"""
        if client.player_entity is None:
            return
        
        pos = self.world.get_component(client.player_entity, Position)
        if not pos:
            return
        
        player_data = self._entity_to_data(client.player_entity)
        if not player_data:
            return
        
        # Get visible entities
        visible_entities = []
        nearby = self.spatial_index.query_radius(pos.x, pos.y, pos.z, 30.0)
        for entity in nearby:
            if entity != client.player_entity:
                entity_data = self._entity_to_data(entity)
                if entity_data:
                    visible_entities.append(entity_data)
        
        # Get visible tiles
        tiles = {}
        if self.world_3d:
            visible_tiles = self.world_3d.get_visible_tiles(
                int(pos.x), int(pos.y), int(pos.z), 25
            )
            for (x, y, z), tile in visible_tiles.items():
                tiles[f"{x},{y},{z}"] = {
                    "char": tile.tile_type.value,
                    "color": tile.color,
                    "walkable": tile.tile_type.is_walkable,
                    "solid": tile.tile_type.is_solid
                }
        
        msg = MessageBuilder.game_state(
            tick=self.game_loop.current_tick if self.game_loop else 0,
            player=player_data,
            entities=visible_entities,
            tiles=tiles,
            messages=[]
        )
        
        await self._send(client, msg)
    
    async def _broadcast_delta_state(self, tick: int, events: List[Dict]) -> None:
        """Broadcast delta state"""
        for conn in self.connections.values():
            if conn.state != ConnectionState.IN_GAME or conn.player_entity is None:
                continue
            
            pos = self.world.get_component(conn.player_entity, Position)
            if not pos:
                continue
            
            changed = []
            nearby = self.spatial_index.query_radius(pos.x, pos.y, pos.z, 30.0)
            for entity in nearby:
                entity_data = self._entity_to_data(entity)
                if entity_data:
                    changed.append(entity_data)
            
            msg = MessageBuilder.game_state_delta(
                tick=tick,
                changed=changed,
                removed=[],
                tiles={},
                events=events
            )
            
            await self._send(conn, msg)
    
    def _entity_to_data(self, entity: Entity) -> Optional[EntityData]:
        """Convert entity to network data"""
        pos = self.world.get_component(entity, Position)
        identity = self.world.get_component(entity, Identity)
        sprite = self.world.get_component(entity, Sprite)
        stats = self.world.get_component(entity, Stats)
        combat = self.world.get_component(entity, CombatState)
        ai = self.world.get_component(entity, AI)
        
        if not pos or not identity or not sprite:
            return None
        
        return EntityData(
            entity_id=entity,
            entity_type=identity.entity_type.value,
            name=identity.name,
            x=pos.x,
            y=pos.y,
            z=pos.z,
            char=sprite.char,
            color=sprite.color,
            hp=combat.hp if combat else None,
            max_hp=stats.max_hp if stats else None,
            level=stats.level if stats else None,
            faction=ai.faction.value if ai else None
        )
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    async def _send(self, client: ClientConnection, msg: Message) -> None:
        """Send message to client"""
        try:
            await client.websocket.send(msg.to_json())
            client.messages_sent += 1
        except Exception as e:
            logger.error(f"Error sending to {client.connection_id}: {e}")
    
    async def _broadcast(self, msg: Message) -> None:
        """Broadcast to all in-game clients"""
        for conn in self.connections.values():
            if conn.state == ConnectionState.IN_GAME:
                await self._send(conn, msg)
    
    async def _broadcast_except(self, exclude: ClientConnection, msg: Message) -> None:
        """Broadcast to all except one"""
        for conn in self.connections.values():
            if conn.state == ConnectionState.IN_GAME and conn.connection_id != exclude.connection_id:
                await self._send(conn, msg)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server stats"""
        return {
            "connections": len(self.connections),
            "players_in_game": sum(1 for c in self.connections.values() if c.state == ConnectionState.IN_GAME),
            "registered_users": len(self.users),
            "queued_actions": len(self.action_queue),
        }
