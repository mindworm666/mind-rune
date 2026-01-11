# Mind Rune - System Invariants

## What Are Invariants?

**Invariants** are conditions that must ALWAYS be true about your game state. They are:
- Enforced by code, not documentation
- Checked at critical points (dev mode) or implicitly maintained (prod)
- The foundation of game correctness

**Why They Matter:**
- Prevent impossible states (negative HP, teleporting through walls)
- Make bugs easier to find (violation = bug nearby)
- Enable optimization (can assume invariants hold)
- Document assumptions in code

## Core Game Invariants

### 1. Entity Existence Invariant

**Rule**: An entity ID is either fully alive (has components) or fully dead (no components).

**Enforced By**:
```python
def add_entity(entity: Entity) -> None:
    """Entity must not already exist"""
    assert entity not in entities, f"Entity {entity} already exists"
    entities.add(entity)
    
def remove_entity(entity: Entity) -> None:
    """Remove ALL traces of entity"""
    # Remove from component storage
    for component_type in component_storage:
        component_storage[component_type].pop(entity, None)
    # Remove from spatial index
    if entity in positions:
        pos = positions[entity]
        spatial_index.remove(entity, pos.x, pos.y, pos.z)
    # Remove from entity set
    entities.remove(entity)
    
    # INVARIANT: Entity is now completely gone
    assert entity not in entities
    assert all(entity not in storage for storage in component_storage.values())
```

**Prevents**:
- Zombie entities (ID exists but no components)
- Ghost components (component exists but entity doesn't)
- Memory leaks from partial cleanup

---

### 2. Position-Spatial Index Invariant

**Rule**: An entity's position component MUST match its position in the spatial index.

**Enforced By**:
```python
def set_position(entity: Entity, new_pos: Position) -> None:
    # Remove from old location
    if entity in positions:
        old_pos = positions[entity]
        spatial_index.remove(entity, old_pos.x, old_pos.y, old_pos.z)
    
    # Update position
    positions[entity] = new_pos
    
    # Add to new location
    spatial_index.insert(entity, new_pos.x, new_pos.y, new_pos.z)
    
    # INVARIANT CHECK (dev mode)
    if DEBUG:
        cells = spatial_index.query_point(new_pos.x, new_pos.y, new_pos.z)
        assert entity in cells, "Entity not in spatial index at position"
```

**Prevents**:
- Collision detection missing entities
- Entities invisible to nearby players
- Incorrect visibility calculations

---

### 3. Health Bounds Invariant

**Rule**: 0 ≤ current_hp ≤ max_hp for all living entities.

**Enforced By**:
```python
def apply_damage(entity: Entity, damage: int) -> None:
    combat = combat_states[entity]
    stats = stat_blocks[entity]
    
    # Clamp to valid range
    combat.hp = max(0, min(combat.hp - damage, stats.max_hp))
    
    # Check for death
    if combat.hp == 0:
        handle_death(entity)
    
    # INVARIANT: HP in valid range
    assert 0 <= combat.hp <= stats.max_hp

def heal(entity: Entity, amount: int) -> None:
    combat = combat_states[entity]
    stats = stat_blocks[entity]
    
    # Clamp to max
    combat.hp = min(combat.hp + amount, stats.max_hp)
    
    # INVARIANT: HP in valid range
    assert 0 <= combat.hp <= stats.max_hp
```

**Prevents**:
- Negative HP bugs
- Healing above max HP
- Overflow errors

---

### 4. Inventory Weight Invariant

**Rule**: Total inventory weight ≤ max_carry_weight OR character is encumbered.

**Enforced By**:
```python
def add_item(entity: Entity, item: Item) -> bool:
    inventory = inventories[entity]
    stats = stat_blocks[entity]
    
    new_weight = inventory.total_weight + item.weight
    
    # Can always pick up (becomes encumbered)
    inventory.items.append(item)
    inventory.total_weight = new_weight
    
    # Update encumbrance status
    inventory.encumbered = new_weight > stats.max_carry_weight
    
    if inventory.encumbered:
        # Apply movement penalty
        apply_status(entity, Status.ENCUMBERED)
    
    # INVARIANT: Weight is sum of items
    assert inventory.total_weight == sum(i.weight for i in inventory.items)
    
    return True
```

**Prevents**:
- Infinite inventory exploits
- Incorrect movement speed
- Desync between client and server

---

### 5. Cooldown Consistency Invariant

**Rule**: If an action is on cooldown, it cannot be executed. Cooldown expiration is monotonic.

**Enforced By**:
```python
def can_act(entity: Entity, action: str, current_time: float) -> bool:
    cooldowns = cooldown_manager.get(entity, {})
    
    if action in cooldowns:
        # Check expiration
        if cooldowns[action].expires_at > current_time:
            return False  # Still on cooldown
        else:
            # Expired, remove it
            del cooldowns[action]
    
    # Check GCD
    if "gcd" in cooldowns:
        if cooldowns["gcd"].expires_at > current_time:
            return False
    
    return True

def execute_action(entity: Entity, action: Action, current_time: float) -> bool:
    # PRECONDITION: Must be able to act
    if not can_act(entity, action.name, current_time):
        return False
    
    # Execute action
    result = action.execute(entity)
    
    if result:
        # Set cooldowns
        set_cooldown(entity, action.name, action.cooldown, current_time)
        set_cooldown(entity, "gcd", GCD_DURATION, current_time)
    
    # INVARIANT: Action now on cooldown
    assert not can_act(entity, action.name, current_time)
    
    return result
```

**Prevents**:
- Action spamming exploits
- Client-server desync
- Frame-rate dependent abilities

---

### 6. Collision Detection Invariant

**Rule**: Solid entities cannot occupy the same tile. Non-solid entities can stack.

**Enforced By**:
```python
def can_move_to(entity: Entity, x: float, y: float, z: float) -> bool:
    # Check world collision
    if world.is_solid(x, y, z):
        return False
    
    # Check entity collision
    entities_at = spatial_index.query_point(x, y, z)
    for other in entities_at:
        if other == entity:
            continue
        # Both solid = collision
        if is_solid(entity) and is_solid(other):
            return False
    
    return True

def move(entity: Entity, dx: float, dy: float, dz: float) -> bool:
    pos = positions[entity]
    new_x, new_y, new_z = pos.x + dx, pos.y + dy, pos.z + dz
    
    # PRECONDITION: Can move there
    if not can_move_to(entity, new_x, new_y, new_z):
        return False
    
    # Execute move
    set_position(entity, Position(new_x, new_y, new_z))
    
    # INVARIANT: Position updated successfully
    assert positions[entity].x == new_x
    assert positions[entity].y == new_y
    assert positions[entity].z == new_z
    
    return True
```

**Prevents**:
- Walking through walls
- Entity overlap bugs
- Pathfinding errors

---

### 7. Component Dependency Invariant

**Rule**: Some components require other components. If A requires B, then has(A) implies has(B).

**Dependencies**:
- `CombatState` requires `Stats` (need max_hp)
- `AI` requires `Position` (need location for decisions)
- `Inventory` requires `Stats` (need carry weight)
- `Equipment` requires `Stats` (need to apply bonuses)

**Enforced By**:
```python
COMPONENT_DEPENDENCIES = {
    CombatState: [Stats],
    AI: [Position],
    Inventory: [Stats],
    Equipment: [Stats],
}

def add_component(entity: Entity, component_type: Type, component: Any) -> None:
    # Check dependencies
    if component_type in COMPONENT_DEPENDENCIES:
        for required in COMPONENT_DEPENDENCIES[component_type]:
            assert has_component(entity, required), \
                f"Cannot add {component_type} without {required}"
    
    # Add component
    component_storage[component_type][entity] = component
    
    # INVARIANT: Dependencies satisfied
    for required in COMPONENT_DEPENDENCIES.get(component_type, []):
        assert has_component(entity, required)

def remove_component(entity: Entity, component_type: Type) -> None:
    # Check if any components depend on this
    for other_type, deps in COMPONENT_DEPENDENCIES.items():
        if component_type in deps:
            assert not has_component(entity, other_type), \
                f"Cannot remove {component_type} while {other_type} exists"
    
    # Remove component
    del component_storage[component_type][entity]
```

**Prevents**:
- Null pointer exceptions
- Undefined behavior
- Incomplete entity states

---

### 8. Action Ordering Invariant

**Rule**: Systems execute in a fixed, deterministic order each tick. No system runs twice per tick.

**Enforced By**:
```python
SYSTEM_ORDER = [
    "cooldown",
    "action",
    "movement",
    "combat",
    "item",
    "ai",
    "progression",
    "visibility",
    "physics",
]

def run_game_tick(dt: float) -> None:
    executed = set()
    
    for system_name in SYSTEM_ORDER:
        # INVARIANT: System not yet executed this tick
        assert system_name not in executed
        
        system = systems[system_name]
        system.update(dt, entities, world, events)
        
        executed.add(system_name)
    
    # INVARIANT: All systems executed exactly once
    assert len(executed) == len(SYSTEM_ORDER)
```

**Prevents**:
- Race conditions
- Non-deterministic behavior
- Hard-to-reproduce bugs

---

### 9. Network State Invariant

**Rule**: Client state is always behind or equal to server state. Never ahead.

**Enforced By**:
```python
class ClientState:
    server_tick: int = 0  # Last acked server tick
    predicted_tick: int = 0  # Client's current prediction
    
    def apply_server_update(self, update: StateUpdate) -> None:
        # PRECONDITION: Update is newer than current state
        assert update.tick >= self.server_tick, \
            f"Received old update: {update.tick} < {self.server_tick}"
        
        # Apply update
        self.apply_deltas(update.deltas)
        self.server_tick = update.tick
        
        # Reconcile predictions
        if self.predicted_tick > self.server_tick:
            # Re-predict from new server state
            self.replay_predictions(self.server_tick, self.predicted_tick)
        
        # INVARIANT: Server tick is reference point
        assert self.predicted_tick >= self.server_tick
```

**Prevents**:
- Rubber-banding
- State desync
- Exploit opportunities

---

### 10. Database Consistency Invariant

**Rule**: Critical game state is immediately persisted. Database constraints match game invariants.

**Enforced By**:
```python
# Database schema
CREATE TABLE characters (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    hp INTEGER NOT NULL CHECK (hp >= 0),  -- Match invariant
    max_hp INTEGER NOT NULL CHECK (max_hp > 0),
    x REAL NOT NULL,
    y REAL NOT NULL,
    z REAL NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    CHECK (hp <= max_hp)  -- Health bounds invariant
);

def save_character(entity: Entity) -> None:
    stats = stat_blocks[entity]
    combat = combat_states[entity]
    pos = positions[entity]
    
    # PRECONDITION: Invariants hold
    assert 0 <= combat.hp <= stats.max_hp
    
    db.execute("""
        UPDATE characters 
        SET hp = ?, max_hp = ?, x = ?, y = ?, z = ?
        WHERE id = ?
    """, (combat.hp, stats.max_hp, pos.x, pos.y, pos.z, entity))
    
    # Database will reject if invariants violated
    # INVARIANT: Save succeeded or raised exception
```

**Prevents**:
- Save corruption
- Invalid states persisting
- Rollback issues

---

## Invariant Checking Strategy

### Development Mode
```python
DEBUG = os.getenv("ENV") == "development"

def assert_invariants(entity: Entity) -> None:
    """Check all invariants for entity (expensive!)"""
    if not DEBUG:
        return
    
    # Check position invariant
    if entity in positions:
        pos = positions[entity]
        cells = spatial_index.query_point(pos.x, pos.y, pos.z)
        assert entity in cells
    
    # Check health invariant
    if entity in combat_states and entity in stat_blocks:
        combat = combat_states[entity]
        stats = stat_blocks[entity]
        assert 0 <= combat.hp <= stats.max_hp
    
    # Check component dependencies
    for comp_type, deps in COMPONENT_DEPENDENCIES.items():
        if has_component(entity, comp_type):
            for required in deps:
                assert has_component(entity, required)
```

### Production Mode
- Invariants maintained by construction (can't violate)
- Critical invariants checked (fast checks only)
- Logging when invariants nearly violated

### Testing Mode
```python
def test_movement_maintains_invariants():
    entity = create_test_entity()
    
    # Move entity
    move(entity, 1, 0, 0)
    
    # Check ALL invariants
    assert_all_invariants(entity)
    
    # Try invalid move
    result = move(entity, 1000, 0, 0)  # Out of bounds
    assert not result  # Should fail
    
    # Invariants still hold
    assert_all_invariants(entity)
```

## Invariant Documentation

When adding new features, document invariants:

```python
class NewComponent:
    """
    Component description.
    
    INVARIANTS:
    - field1 must be positive
    - field2 must be unique across all entities
    - Requires: SomeOtherComponent
    
    MAINTAINED BY:
    - new_component_system.py
    """
    field1: int
    field2: str
```

## Summary

These invariants form the **contract** of our game engine:
- ✅ If you maintain them, the game works correctly
- ✅ If you violate them, you get immediate, actionable errors
- ✅ They enable optimization (can assume invariants hold)
- ✅ They document the system's assumptions

**Remember**: Invariants are not wishes, they are guarantees. Code must enforce them, not just hope for them.
