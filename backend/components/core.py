"""
Mind Rune - Core Game Components

Pure data structures for entity components.
No logic, just data.

CONVENTIONS:
- All components are @dataclasses
- Fields are public (no getters/setters)
- Default values where sensible
- Type hints on everything
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
from enum import Enum


# ============================================================================
# POSITION AND PHYSICS
# ============================================================================

@dataclass
class Position:
    """
    3D position in world space.
    
    INVARIANT: Must be in spatial index at (x, y, z)
    REQUIRES: Nothing
    """
    x: float
    y: float
    z: float
    chunk_x: int = 0  # Cached chunk coordinates
    chunk_y: int = 0
    chunk_z: int = 0


@dataclass
class Velocity:
    """
    Movement velocity in units per second.
    Applied by physics system.
    """
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0


@dataclass
class Solid:
    """
    Marker component: entity blocks movement.
    Checked by collision system.
    """
    blocks_movement: bool = True
    blocks_projectiles: bool = True


# ============================================================================
# IDENTITY AND DISPLAY
# ============================================================================

class EntityType(Enum):
    """Entity type categories"""
    PLAYER = "player"
    NPC = "npc"
    ITEM = "item"
    PROJECTILE = "projectile"
    EFFECT = "effect"
    STRUCTURE = "structure"


@dataclass
class Identity:
    """Basic entity identification"""
    entity_type: EntityType
    name: str
    description: str = ""


@dataclass
class Sprite:
    """
    Visual representation (ASCII character).
    Used by renderer.
    """
    char: str  # Single ASCII character
    color: str = "white"  # CSS color name or hex
    bg_color: str = "transparent"
    z_order: int = 0  # Higher = drawn on top


# ============================================================================
# STATS AND COMBAT
# ============================================================================

@dataclass
class Stats:
    """
    Base character stats. All derived stats calculated from these.
    
    INVARIANT: All stats >= 0
    REQUIRES: Nothing
    """
    # Base attributes (1-100 typical range)
    strength: int = 10      # Physical damage, carry weight
    dexterity: int = 10     # Attack speed, dodge, accuracy
    constitution: int = 10  # HP, HP regen, poison resist
    intelligence: int = 10  # Magic damage, MP pool, mana regen
    wisdom: int = 10        # Magic defense, perception, resist
    charisma: int = 10      # NPC prices, pet control
    
    # Derived stats (calculated by progression system)
    max_hp: int = 100
    max_mp: int = 50
    armor: int = 0
    magic_resist: int = 0
    attack_power: int = 10
    magic_power: int = 10
    
    # Rates
    hp_regen_per_sec: float = 0.1
    mp_regen_per_sec: float = 0.2
    move_speed: float = 5.0  # Units per second
    attack_speed: float = 1.0  # Attacks per second (base)
    
    # Level
    level: int = 1
    experience: int = 0
    experience_to_next: int = 100


@dataclass
class CombatState:
    """
    Current combat status.
    
    INVARIANT: 0 <= hp <= max_hp, 0 <= mp <= max_mp
    REQUIRES: Stats component
    """
    hp: int
    mp: int
    
    # Combat flags
    in_combat: bool = False
    last_combat_time: float = 0.0
    
    # Targeting
    target: Optional[int] = None  # Entity ID
    targeted_by: Set[int] = field(default_factory=set)
    
    # Threat (for NPCs)
    threat_table: Dict[int, float] = field(default_factory=dict)  # entity -> threat


class DamageType(Enum):
    """Types of damage"""
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    POISON = "poison"
    HOLY = "holy"
    DARK = "dark"


@dataclass
class DamageEvent:
    """Damage to be applied (used in event queue)"""
    target: int  # Entity ID
    source: Optional[int]  # Entity ID or None for environment
    amount: int
    damage_type: DamageType
    timestamp: float


# ============================================================================
# COOLDOWNS AND ACTIONS
# ============================================================================

@dataclass
class Cooldown:
    """A single cooldown timer"""
    action_name: str
    expires_at: float  # Game time when cooldown expires
    duration: float    # Total cooldown duration (for client display)


@dataclass
class Cooldowns:
    """
    All cooldowns for an entity.
    Updated by cooldown system.
    """
    active: Dict[str, Cooldown] = field(default_factory=dict)
    gcd_expires_at: float = 0.0  # Global cooldown


@dataclass
class ActionQueue:
    """Queued actions waiting to execute"""
    actions: List[Dict] = field(default_factory=list)  # List of action dicts


# ============================================================================
# INVENTORY AND ITEMS
# ============================================================================

@dataclass
class Item:
    """
    An item instance.
    Can be in inventory, on ground, or equipped.
    """
    item_id: int  # Unique instance ID
    template_id: str  # Item template (e.g., "iron_sword")
    name: str
    description: str
    
    # Properties
    weight: float
    stackable: bool
    stack_count: int = 1
    max_stack: int = 1
    
    # Value
    value: int = 0  # Gold value
    
    # Durability
    durability: Optional[int] = None
    max_durability: Optional[int] = None
    
    # Stats (if equipment)
    stat_bonuses: Dict[str, int] = field(default_factory=dict)
    
    # Visual
    char: str = "?"
    color: str = "white"


class EquipSlot(Enum):
    """Equipment slots"""
    WEAPON = "weapon"
    OFF_HAND = "off_hand"
    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    FEET = "feet"
    HANDS = "hands"
    NECK = "neck"
    RING_1 = "ring_1"
    RING_2 = "ring_2"


@dataclass
class Inventory:
    """
    Entity inventory.
    
    INVARIANT: total_weight <= max_weight OR encumbered = True
    REQUIRES: Stats component
    """
    items: List[Item] = field(default_factory=list)
    gold: int = 0
    
    # Capacity
    max_items: int = 20
    max_weight: float = 100.0
    total_weight: float = 0.0
    encumbered: bool = False
    
    # Equipment
    equipped: Dict[EquipSlot, Optional[Item]] = field(default_factory=dict)


# ============================================================================
# AI AND BEHAVIOR
# ============================================================================

class AIState(Enum):
    """NPC AI states"""
    IDLE = "idle"
    WANDERING = "wandering"
    CHASING = "chasing"
    ATTACKING = "attacking"
    FLEEING = "fleeing"
    RETURNING = "returning"


class Faction(Enum):
    """Faction allegiances"""
    PLAYER = "player"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    HOSTILE = "hostile"
    WILDLIFE = "wildlife"


@dataclass
class AI:
    """
    NPC AI component.
    Controls decision-making.
    
    REQUIRES: Position, Stats, CombatState
    """
    state: AIState = AIState.IDLE
    faction: Faction = Faction.NEUTRAL
    
    # Behavior parameters
    aggro_radius: float = 10.0
    chase_radius: float = 20.0  # Will give up chase beyond this
    attack_range: float = 1.5
    
    # Spawn point (for returning)
    spawn_x: float = 0.0
    spawn_y: float = 0.0
    spawn_z: float = 0.0
    
    # State timers
    state_time: float = 0.0  # Time in current state
    last_decision_time: float = 0.0
    decision_interval: float = 0.5  # Make decisions every 0.5s
    
    # Targeting
    current_target: Optional[int] = None
    last_seen_target_x: float = 0.0
    last_seen_target_y: float = 0.0
    last_seen_target_z: float = 0.0


@dataclass
class Loot:
    """
    Loot table for entity (usually NPCs).
    Dropped on death.
    """
    guaranteed_items: List[str] = field(default_factory=list)  # Template IDs
    possible_items: Dict[str, float] = field(default_factory=dict)  # Template ID -> drop chance
    gold_min: int = 0
    gold_max: int = 0
    experience_value: int = 0


# ============================================================================
# PLAYER-SPECIFIC
# ============================================================================

@dataclass
class Player:
    """
    Marker component + player data.
    Only players have this.
    """
    account_id: int
    character_name: str
    connection_id: Optional[str] = None  # WebSocket connection
    last_save_time: float = 0.0
    save_interval: float = 60.0  # Save every 60 seconds


@dataclass
class Respawn:
    """Respawn information"""
    respawn_x: float
    respawn_y: float
    respawn_z: float
    respawn_time: float = 5.0  # Seconds until respawn


# ============================================================================
# VISIBILITY AND FOG OF WAR
# ============================================================================

@dataclass
class Vision:
    """
    Vision component. Determines what entity can see.
    Used by visibility system.
    """
    radius: float = 20.0  # View distance
    can_see_invisible: bool = False
    explored_tiles: Set[tuple] = field(default_factory=set)  # (x, y, z) tuples


@dataclass
class Invisible:
    """Marker: entity is invisible"""
    visible_to: Set[int] = field(default_factory=set)  # Entity IDs that can see this


# ============================================================================
# STATUS EFFECTS
# ============================================================================

class StatusType(Enum):
    """Types of status effects"""
    STUNNED = "stunned"
    SLOWED = "slowed"
    HASTED = "hasted"
    POISONED = "poisoned"
    BURNING = "burning"
    FROZEN = "frozen"
    BLESSED = "blessed"
    CURSED = "cursed"
    ENCUMBERED = "encumbered"


@dataclass
class StatusEffect:
    """A single status effect"""
    status_type: StatusType
    duration: float  # Seconds remaining
    stacks: int = 1
    source: Optional[int] = None  # Entity that applied it


@dataclass
class StatusEffects:
    """All status effects on entity"""
    active: List[StatusEffect] = field(default_factory=list)


# ============================================================================
# TEMPORAL / LIFECYCLE
# ============================================================================

@dataclass
class Lifetime:
    """
    Auto-destroy after duration.
    Used for projectiles, effects, corpses.
    """
    created_at: float
    duration: float
    
    def is_expired(self, current_time: float) -> bool:
        return current_time >= self.created_at + self.duration


@dataclass
class Dead:
    """
    Marker: entity is dead but not yet cleaned up.
    Used to handle death state before destruction.
    """
    time_of_death: float
    killer: Optional[int] = None  # Entity ID


# Example: Creating a player entity
if __name__ == "__main__":
    from backend.engine.ecs import World
    
    world = World(debug=True)
    
    # Register components
    world.register_component(Position)
    world.register_component(Stats)
    world.register_component(CombatState, dependencies=[Stats])
    world.register_component(Inventory, dependencies=[Stats])
    world.register_component(Player)
    world.register_component(Sprite)
    world.register_component(Identity)
    world.register_component(Vision)
    world.register_component(Cooldowns)
    
    # Create player entity
    player = world.create_entity()
    
    # Add components
    world.add_component(player, Position, Position(x=0, y=0, z=0))
    world.add_component(player, Stats, Stats(
        strength=15,
        dexterity=12,
        constitution=14,
        max_hp=140,
        max_mp=50,
    ))
    world.add_component(player, CombatState, CombatState(hp=140, mp=50))
    world.add_component(player, Inventory, Inventory(max_items=20, max_weight=150.0))
    world.add_component(player, Player, Player(account_id=1, character_name="Hero"))
    world.add_component(player, Sprite, Sprite(char="@", color="yellow"))
    world.add_component(player, Identity, Identity(
        entity_type=EntityType.PLAYER,
        name="Hero",
        description="A brave adventurer"
    ))
    world.add_component(player, Vision, Vision(radius=25.0))
    world.add_component(player, Cooldowns, Cooldowns())
    
    print("\n=== Player Entity Created ===")
    print(f"Entity ID: {player}")
    print(f"Components: {list(world.get_components(player).keys())}")
    
    # Query example
    for entity, (pos, identity) in world.query(Position, Identity):
        print(f"\nEntity {entity} ({identity.name}):")
        print(f"  Position: ({pos.x}, {pos.y}, {pos.z})")
        print(f"  Type: {identity.entity_type.value}")
