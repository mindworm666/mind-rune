# Mind Rune - Core Architecture

## Overview

Mind Rune uses a **component-based entity system** with a **tick-driven game loop** running at **20 TPS (ticks per second)**. All game actions are real-time with cooldowns, ensuring smooth gameplay without traditional turn-based mechanics.

## Design Principles

### 1. **Real-Time, Not Turn-Based**
- All actions have cooldowns (movement, combat, item use)
- Server runs at fixed 20 TPS (50ms per tick)
- Client interpolates between ticks for smooth visuals
- No waiting for "turns" - everything flows continuously

### 2. **Invariants First**
- Every game state change validates invariants
- Impossible states are prevented, not detected
- All mutations go through validation layers
- Database constraints match game rules

### 3. **3D World, 2D Display**
- World is true 3D (x, y, z coordinates)
- Client renders 2D projection (isometric or top-down)
- Multi-level dungeons and caves
- Vertical gameplay matters (falling damage, flying, climbing)

### 4. **Performance as a Feature**
- Spatial indexing for O(1) proximity queries
- Object pooling to reduce allocations
- Delta compression for network traffic
- Lazy evaluation where possible
- Memory budgets for all systems

### 5. **Terminal Aesthetic with Function**
- Heavy CRT/terminal visual style
- Modular floating panels (inventory, stats, map)
- Command-line interface with autocomplete
- Negative space is intentional, not wasted
- Information density without clutter

## Core Architecture Layers

```
┌─────────────────────────────────────────────┐
│           Frontend (Terminal UI)             │
│  - Rendering Pipeline                        │
│  - Input Handling                            │
│  - Client Prediction                         │
│  - Interpolation                             │
└─────────────────┬───────────────────────────┘
                  │ WebSocket (Binary Protocol)
┌─────────────────▼───────────────────────────┐
│         Network Layer (FastAPI)              │
│  - Connection Management                     │
│  - Message Routing                           │
│  - State Synchronization                     │
│  - Interest Management                       │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│          Game Engine (ECS)                   │
│  ┌─────────────────────────────────────┐    │
│  │  Entities (ID + Components)         │    │
│  │  - Player, NPC, Item, Projectile    │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │  Components (Pure Data)             │    │
│  │  - Position, Stats, Inventory       │    │
│  │  - Combat, AI, Cooldowns            │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │  Systems (Logic)                    │    │
│  │  - Movement, Combat, AI             │    │
│  │  - Inventory, Progression           │    │
│  │  - Visibility, Physics              │    │
│  └─────────────────────────────────────┘    │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│          World Layer                         │
│  - 3D Spatial Index (Hash Grid)             │
│  - Chunk Management                          │
│  - Procedural Generation                     │
│  - Collision Detection                       │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│       Persistence Layer (SQLite)             │
│  - Accounts, Characters                      │
│  - World State (chunks)                      │
│  - Item Templates, NPC Templates            │
└─────────────────────────────────────────────┘
```

## Entity Component System (ECS)

### Entities
Pure IDs - containers for components. No logic, no data beyond their identity.

```python
Entity = int  # Just an ID
```

### Components
Pure data structures - no methods, no logic.

```python
@dataclass
class Position:
    x: float
    y: float
    z: float
    chunk_id: int  # Cached for spatial queries
    
@dataclass
class Stats:
    # Base stats
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int
    
    # Derived (recalculated)
    max_hp: int
    max_mp: int
    armor: int
    damage: int
    
@dataclass
class CombatState:
    hp: int
    mp: int
    target: Optional[Entity]
    in_combat: bool
    last_damage_time: float
    threat_table: Dict[Entity, float]
```

### Systems
Pure functions operating on components. No state beyond game state.

```python
class MovementSystem:
    def update(self, dt: float, entities: Iterable[Entity], 
               world: World, events: EventQueue) -> None:
        # Process all movement actions
        # Validate collision
        # Update spatial index
        # Emit movement events
```

## Game Loop

### Server Loop (20 TPS)
```python
TICK_RATE = 20  # ticks per second
TICK_DURATION = 1.0 / TICK_RATE  # 50ms

while running:
    tick_start = time.monotonic()
    
    # 1. Process input from network queue
    process_client_inputs()
    
    # 2. Run systems in order
    cooldown_system.update(dt, entities, world, events)
    action_system.update(dt, entities, world, events)
    movement_system.update(dt, entities, world, events)
    combat_system.update(dt, entities, world, events)
    ai_system.update(dt, entities, world, events)
    visibility_system.update(dt, entities, world, events)
    
    # 3. Process events and send network updates
    process_events()
    send_state_deltas()
    
    # 4. Sleep until next tick
    elapsed = time.monotonic() - tick_start
    sleep_time = max(0, TICK_DURATION - elapsed)
    time.sleep(sleep_time)
```

### System Execution Order
Order matters! Systems must run in dependency order:

1. **CooldownSystem** - Tick down all cooldowns
2. **ActionSystem** - Validate and queue actions
3. **MovementSystem** - Process movement (first to resolve position)
4. **CombatSystem** - Process attacks and damage
5. **ItemSystem** - Item pickups, uses, drops
6. **AISystem** - NPC decision making
7. **ProgressionSystem** - XP, leveling, stat updates
8. **VisibilitySystem** - Update fog of war, LOS
9. **PhysicsSystem** - Gravity, falling, collision resolution

## Spatial Indexing

For efficient proximity queries (who's nearby? what can I see?), we use a **spatial hash grid**.

```python
class SpatialIndex:
    """O(1) proximity queries using grid hashing"""
    
    CELL_SIZE = 10.0  # Grid cell size in world units
    
    def __init__(self):
        self.cells: Dict[Tuple[int, int, int], Set[Entity]] = defaultdict(set)
        
    def insert(self, entity: Entity, x: float, y: float, z: float):
        cell = (int(x // CELL_SIZE), int(y // CELL_SIZE), int(z // CELL_SIZE))
        self.cells[cell].add(entity)
        
    def query_radius(self, x: float, y: float, z: float, radius: float) -> Set[Entity]:
        # Check cells within radius
        # Only O(entities in radius), not O(all entities)
```

**Why This Matters:**
- Without spatial index: O(N) for every collision check
- With spatial index: O(K) where K = entities in nearby cells
- At 1000 players, this is 100x+ faster

## Cooldown System

All actions use a unified cooldown system:

```python
@dataclass
class Cooldown:
    action: str
    expires_at: float  # Server time
    duration: float    # For client display
    
class CooldownManager:
    # Global cooldown - blocks all actions briefly
    GCD = 0.5  # 500ms
    
    def can_act(self, entity: Entity, action: str) -> bool:
        # Check GCD
        if self.has_cooldown(entity, "gcd"):
            return False
        # Check specific cooldown
        if self.has_cooldown(entity, action):
            return False
        return True
        
    def trigger(self, entity: Entity, action: str, duration: float):
        # Set action-specific cooldown
        self.set_cooldown(entity, action, duration)
        # Set GCD
        self.set_cooldown(entity, "gcd", self.GCD)
```

**Action Cooldowns:**
- Movement: 0.1s (10 moves/second max)
- Basic attack: 1.5s
- Skills: 3-30s depending on power
- Item use: 1-5s depending on item
- Interaction: 0.5s

## Network Protocol

### Message Types
```python
class MessageType(Enum):
    # Client -> Server
    ACTION = 1       # Player wants to do something
    CHAT = 2         # Chat message
    
    # Server -> Client
    STATE_DELTA = 10  # Incremental state update
    EVENT = 11        # Game event (damage, death, etc)
    SNAPSHOT = 12     # Full state (on connect/error)
```

### State Delta Compression
Instead of sending full state every tick, send only changes:

```python
# Bad: 1000 bytes every tick
{
    "entities": [
        {"id": 1, "x": 10, "y": 20, "hp": 100, ...},
        {"id": 2, "x": 15, "y": 25, "hp": 80, ...},
        # ... 50 more entities
    ]
}

# Good: 50 bytes when entity moves
{
    "deltas": [
        {"id": 1, "x": 11}  # Only changed field
    ]
}
```

### Interest Management
Players only receive updates for entities near them:

```python
def get_visible_entities(player: Entity) -> Set[Entity]:
    pos = world.get_component(player, Position)
    # Only entities within render distance (30 tiles)
    return spatial_index.query_radius(pos.x, pos.y, pos.z, radius=30)
```

## Validation and Invariants

### Invariant Examples
1. **Position Invariant**: Entity position must match spatial index
2. **HP Invariant**: 0 ≤ HP ≤ max_hp
3. **Inventory Invariant**: Total weight ≤ max_carry_weight
4. **Action Invariant**: Can only act if cooldowns allow
5. **Physics Invariant**: Entities on ground or falling (no floating)

### Validation Layers
```python
def move_entity(entity: Entity, new_x: float, new_y: float, new_z: float):
    # Layer 1: Precondition validation
    assert can_move(entity), "Entity is stunned/dead"
    assert not has_cooldown(entity, "move"), "Movement on cooldown"
    
    # Layer 2: Collision validation
    if world.is_solid(new_x, new_y, new_z):
        return False  # Can't move into walls
        
    # Layer 3: Execute with invariant maintenance
    old_pos = world.get_component(entity, Position)
    spatial_index.remove(entity, old_pos.x, old_pos.y, old_pos.z)
    
    new_pos = Position(new_x, new_y, new_z)
    world.set_component(entity, new_pos)
    
    spatial_index.insert(entity, new_x, new_y, new_z)
    
    # Layer 4: Post-condition validation (dev mode)
    assert_position_invariant(entity)
```

## Performance Budgets

### Memory Budgets
- **Entity limit**: 10,000 active entities max
- **Component memory**: ~200 bytes per entity average
- **Spatial index**: ~50 bytes per entity
- **Total**: ~2.5 MB for entity system at capacity

### CPU Budgets (per tick @ 20 TPS)
- **Total tick time**: 50ms
- **System execution**: 30ms max
  - Movement: 5ms
  - Combat: 8ms
  - AI: 10ms
  - Others: 7ms
- **Network I/O**: 10ms max
- **Buffer**: 10ms safety margin

### Network Budgets
- **Per client bandwidth**: 10 KB/s down, 1 KB/s up
- **100 clients**: 1 MB/s total (well within modern limits)

## Object Pooling

Reduce GC pressure by reusing objects:

```python
class EntityPool:
    def __init__(self):
        self.available: List[Entity] = []
        self.next_id = 0
        
    def acquire(self) -> Entity:
        if self.available:
            return self.available.pop()
        entity = self.next_id
        self.next_id += 1
        return entity
        
    def release(self, entity: Entity):
        # Clear all components
        world.remove_all_components(entity)
        # Return to pool
        self.available.append(entity)
```

## Testing Strategy

### Unit Tests
- Test each system in isolation
- Mock components and world state
- Verify invariants after every operation

### Integration Tests
- Test system interactions
- Full game loop with simulated inputs
- Stress tests with 1000+ entities

### Property Tests
- Generate random game states
- Verify invariants always hold
- Find edge cases automatically

### Performance Tests
- Benchmark each system
- Regression tests for tick time
- Memory leak detection

## Extensibility Patterns

### Adding New Actions
```python
# 1. Define action data
@dataclass
class CastSpellAction:
    spell_id: int
    target: Optional[Entity]

# 2. Register handler
@action_system.register("cast_spell")
def handle_cast_spell(entity: Entity, action: CastSpellAction) -> bool:
    # Validate cooldown
    if not cooldowns.can_act(entity, "spell"):
        return False
    # Validate resources (mana)
    # Execute spell effect
    # Trigger cooldown
    cooldowns.trigger(entity, "spell", spell.cooldown)
    return True
```

### Adding New Components
```python
# 1. Define component
@dataclass
class Stealth:
    hidden: bool
    detection_radius: float

# 2. Register with world
world.register_component(Stealth)

# 3. Systems automatically handle it
class VisibilitySystem:
    def update(self, ...):
        for entity in entities:
            if world.has_component(entity, Stealth):
                stealth = world.get_component(entity, Stealth)
                # Modify visibility logic
```

## Migration Strategy

We're migrating from the simple iteration-zero codebase to this architecture:

### Phase 1: Core Engine (This Iteration)
- Build ECS framework
- Implement spatial indexing
- Create cooldown system
- Port existing features to new architecture

### Phase 2: Feature Parity (Next Iteration)
- Ensure all iteration-zero features work
- Add migration script for old save data
- Performance testing and optimization

### Phase 3: New Features (Future)
- Build on solid foundation
- Each feature is a new component + system
- Iterative development without refactoring

## Summary

This architecture provides:
✅ **Scalability**: Handle 1000+ entities efficiently
✅ **Maintainability**: Clear separation of concerns
✅ **Extensibility**: Easy to add new features
✅ **Performance**: Optimized for real-time gameplay
✅ **Correctness**: Invariants prevent invalid states
✅ **Testability**: Every piece can be unit tested

Every design decision supports real-time, multiplayer gameplay with a solid foundation for years of iteration.
