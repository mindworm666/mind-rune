"""
Mind Rune - Network Protocol

Defines all message types for client<->server communication.
Binary-efficient JSON with delta compression for state updates.

MESSAGE FORMAT:
{
    "type": str,         # Message type
    "id": int,           # Message ID for request/response tracking  
    "ts": float,         # Server timestamp
    "data": {...}        # Payload
}
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import json
import time


class MessageType(Enum):
    """All message types"""
    
    # Client -> Server
    AUTH_LOGIN = "auth_login"
    AUTH_REGISTER = "auth_register"
    AUTH_LOGOUT = "auth_logout"
    
    PLAYER_MOVE = "player_move"
    PLAYER_ATTACK = "player_attack"
    PLAYER_USE_SKILL = "player_use_skill"
    PLAYER_INTERACT = "player_interact"
    
    INVENTORY_USE = "inventory_use"
    INVENTORY_DROP = "inventory_drop"
    INVENTORY_PICKUP = "inventory_pickup"
    INVENTORY_EQUIP = "inventory_equip"
    INVENTORY_UNEQUIP = "inventory_unequip"
    
    CHAT_SEND = "chat_send"
    
    REQUEST_STATE = "request_state"
    PING = "ping"
    
    # Server -> Client
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    
    GAME_STATE = "game_state"
    GAME_STATE_DELTA = "game_state_delta"
    
    ENTITY_SPAWN = "entity_spawn"
    ENTITY_DESPAWN = "entity_despawn"
    ENTITY_UPDATE = "entity_update"
    
    COMBAT_EVENT = "combat_event"
    DAMAGE_EVENT = "damage_event"
    DEATH_EVENT = "death_event"
    LEVEL_UP_EVENT = "level_up_event"
    
    ITEM_DROPPED = "item_dropped"
    ITEM_PICKED_UP = "item_picked_up"
    
    CHAT_RECEIVE = "chat_receive"
    SYSTEM_MESSAGE = "system_message"
    
    WORLD_UPDATE = "world_update"
    
    PONG = "pong"
    ERROR = "error"


@dataclass
class Message:
    """Base message structure"""
    type: MessageType
    data: Dict[str, Any] = field(default_factory=dict)
    id: int = 0
    ts: float = field(default_factory=time.time)
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "id": self.id,
            "ts": self.ts,
            "data": self.data
        })
    
    @staticmethod
    def from_json(raw: str) -> 'Message':
        obj = json.loads(raw)
        return Message(
            type=MessageType(obj["type"]),
            id=obj.get("id", 0),
            ts=obj.get("ts", time.time()),
            data=obj.get("data", {})
        )


# ============================================================================
# CLIENT -> SERVER MESSAGES
# ============================================================================

@dataclass
class AuthLoginData:
    username: str
    password: str  # Hashed client-side
    
@dataclass
class AuthRegisterData:
    username: str
    password: str
    email: str

@dataclass
class PlayerMoveData:
    dx: int  # -1, 0, 1
    dy: int  # -1, 0, 1
    dz: int  # -1, 0, 1 (stairs)

@dataclass  
class PlayerAttackData:
    target_id: int

@dataclass
class PlayerInteractData:
    target_id: Optional[int] = None
    target_x: Optional[int] = None
    target_y: Optional[int] = None
    target_z: Optional[int] = None

@dataclass
class InventoryActionData:
    item_id: int
    slot: Optional[str] = None  # For equip

@dataclass
class ChatSendData:
    message: str
    channel: str = "local"  # local, global, party


# ============================================================================
# SERVER -> CLIENT MESSAGES
# ============================================================================

@dataclass
class AuthSuccessData:
    player_id: int
    character_name: str
    spawn_x: float
    spawn_y: float
    spawn_z: float

@dataclass
class AuthFailureData:
    reason: str

@dataclass
class EntityData:
    """Serialized entity for network"""
    entity_id: int
    entity_type: str
    name: str
    x: float
    y: float
    z: float
    char: str
    color: str
    hp: Optional[int] = None
    max_hp: Optional[int] = None
    level: Optional[int] = None
    faction: Optional[str] = None

@dataclass  
class GameStateData:
    """Full game state snapshot"""
    tick: int
    player: EntityData
    entities: List[EntityData]
    world_tiles: Dict[str, Dict]  # "x,y,z" -> tile data
    messages: List[Dict]
    
@dataclass
class GameStateDeltaData:
    """Delta state update"""
    tick: int
    changed_entities: List[EntityData]
    removed_entities: List[int]
    changed_tiles: Dict[str, Dict]
    events: List[Dict]

@dataclass
class CombatEventData:
    attacker_id: int
    defender_id: int
    damage: int
    damage_type: str
    hit: bool
    critical: bool = False

@dataclass
class DamageEventData:
    target_id: int
    source_id: Optional[int]
    amount: int
    damage_type: str
    current_hp: int
    max_hp: int

@dataclass
class DeathEventData:
    entity_id: int
    killer_id: Optional[int]
    entity_name: str
    killer_name: Optional[str]

@dataclass
class LevelUpEventData:
    entity_id: int
    new_level: int
    stat_gains: Dict[str, int]

@dataclass
class ItemEventData:
    item_id: int
    item_name: str
    item_char: str
    item_color: str
    x: float
    y: float
    z: float

@dataclass
class ChatReceiveData:
    sender_id: Optional[int]
    sender_name: str
    message: str
    channel: str
    timestamp: float

@dataclass
class SystemMessageData:
    message: str
    level: str = "info"  # info, warning, error

@dataclass
class ErrorData:
    code: str
    message: str


# ============================================================================
# MESSAGE BUILDERS
# ============================================================================

class MessageBuilder:
    """Factory for creating properly typed messages"""
    
    _msg_id = 0
    
    @classmethod
    def _next_id(cls) -> int:
        cls._msg_id += 1
        return cls._msg_id
    
    # Auth
    @classmethod
    def auth_success(cls, player_id: int, name: str, x: float, y: float, z: float) -> Message:
        return Message(
            type=MessageType.AUTH_SUCCESS,
            id=cls._next_id(),
            data={
                "player_id": player_id,
                "character_name": name,
                "spawn_x": x,
                "spawn_y": y,
                "spawn_z": z
            }
        )
    
    @classmethod
    def auth_failure(cls, reason: str) -> Message:
        return Message(
            type=MessageType.AUTH_FAILURE,
            id=cls._next_id(),
            data={"reason": reason}
        )
    
    # Game State
    @classmethod
    def game_state(cls, tick: int, player: EntityData, entities: List[EntityData],
                   tiles: Dict, messages: List) -> Message:
        return Message(
            type=MessageType.GAME_STATE,
            id=cls._next_id(),
            data={
                "tick": tick,
                "player": asdict(player),
                "entities": [asdict(e) for e in entities],
                "world_tiles": tiles,
                "messages": messages
            }
        )
    
    @classmethod
    def game_state_delta(cls, tick: int, changed: List[EntityData], 
                         removed: List[int], tiles: Dict, events: List) -> Message:
        return Message(
            type=MessageType.GAME_STATE_DELTA,
            id=cls._next_id(),
            data={
                "tick": tick,
                "changed_entities": [asdict(e) for e in changed],
                "removed_entities": removed,
                "changed_tiles": tiles,
                "events": events
            }
        )
    
    # Entity Events
    @classmethod
    def entity_spawn(cls, entity: EntityData) -> Message:
        return Message(
            type=MessageType.ENTITY_SPAWN,
            id=cls._next_id(),
            data=asdict(entity)
        )
    
    @classmethod
    def entity_despawn(cls, entity_id: int) -> Message:
        return Message(
            type=MessageType.ENTITY_DESPAWN,
            id=cls._next_id(),
            data={"entity_id": entity_id}
        )
    
    @classmethod
    def entity_update(cls, entity: EntityData) -> Message:
        return Message(
            type=MessageType.ENTITY_UPDATE,
            id=cls._next_id(),
            data=asdict(entity)
        )
    
    # Combat Events
    @classmethod
    def damage_event(cls, target_id: int, source_id: Optional[int], amount: int,
                     damage_type: str, current_hp: int, max_hp: int) -> Message:
        return Message(
            type=MessageType.DAMAGE_EVENT,
            id=cls._next_id(),
            data={
                "target_id": target_id,
                "source_id": source_id,
                "amount": amount,
                "damage_type": damage_type,
                "current_hp": current_hp,
                "max_hp": max_hp
            }
        )
    
    @classmethod
    def death_event(cls, entity_id: int, killer_id: Optional[int],
                    entity_name: str, killer_name: Optional[str]) -> Message:
        return Message(
            type=MessageType.DEATH_EVENT,
            id=cls._next_id(),
            data={
                "entity_id": entity_id,
                "killer_id": killer_id,
                "entity_name": entity_name,
                "killer_name": killer_name
            }
        )
    
    @classmethod
    def level_up_event(cls, entity_id: int, new_level: int, gains: Dict) -> Message:
        return Message(
            type=MessageType.LEVEL_UP_EVENT,
            id=cls._next_id(),
            data={
                "entity_id": entity_id,
                "new_level": new_level,
                "stat_gains": gains
            }
        )
    
    # Chat
    @classmethod
    def chat_receive(cls, sender_id: Optional[int], sender_name: str,
                     message: str, channel: str) -> Message:
        return Message(
            type=MessageType.CHAT_RECEIVE,
            id=cls._next_id(),
            data={
                "sender_id": sender_id,
                "sender_name": sender_name,
                "message": message,
                "channel": channel,
                "timestamp": time.time()
            }
        )
    
    @classmethod
    def system_message(cls, message: str, level: str = "info") -> Message:
        return Message(
            type=MessageType.SYSTEM_MESSAGE,
            id=cls._next_id(),
            data={"message": message, "level": level}
        )
    
    # Utility
    @classmethod
    def pong(cls, client_ts: float) -> Message:
        return Message(
            type=MessageType.PONG,
            id=cls._next_id(),
            data={"client_ts": client_ts, "server_ts": time.time()}
        )
    
    @classmethod
    def error(cls, code: str, message: str) -> Message:
        return Message(
            type=MessageType.ERROR,
            id=cls._next_id(),
            data={"code": code, "message": message}
        )


# Testing
if __name__ == "__main__":
    # Test message serialization
    msg = MessageBuilder.auth_success(1, "Hero", 0.0, 0.0, 0.0)
    print(f"Message: {msg.to_json()}")
    
    # Test deserialization
    raw = '{"type": "player_move", "id": 1, "ts": 1234567890.0, "data": {"dx": 1, "dy": 0, "dz": 0}}'
    parsed = Message.from_json(raw)
    print(f"Parsed: {parsed}")
