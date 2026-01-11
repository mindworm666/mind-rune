"""
Mind Rune - Entity Component System (ECS)

Pure ECS implementation:
- Entities are just IDs
- Components are pure data
- Systems are pure logic

Optimized for:
- Fast component lookups (dict-based)
- Efficient iteration (contiguous component arrays)
- Memory efficiency (object pooling)
"""

from typing import Dict, Set, Type, Any, Optional, List, Tuple
from dataclasses import dataclass
import time


# Entity is just an integer ID
Entity = int


class EntityPool:
    """Manages entity ID allocation and recycling"""
    
    def __init__(self):
        self.next_id: int = 1  # 0 is reserved as null
        self.available: List[Entity] = []
        self.active: Set[Entity] = set()
    
    def acquire(self) -> Entity:
        """Get a new or recycled entity ID"""
        if self.available:
            entity = self.available.pop()
        else:
            entity = self.next_id
            self.next_id += 1
        
        self.active.add(entity)
        return entity
    
    def release(self, entity: Entity) -> None:
        """Return entity ID to pool"""
        if entity in self.active:
            self.active.remove(entity)
            self.available.append(entity)
    
    def is_active(self, entity: Entity) -> bool:
        """Check if entity is currently active"""
        return entity in self.active
    
    def get_count(self) -> int:
        """Get number of active entities"""
        return len(self.active)


class ComponentStorage:
    """
    Stores components of a single type.
    Optimized for fast lookups and iteration.
    """
    
    def __init__(self, component_type: Type):
        self.component_type = component_type
        self.components: Dict[Entity, Any] = {}
    
    def add(self, entity: Entity, component: Any) -> None:
        """Add component to entity"""
        self.components[entity] = component
    
    def remove(self, entity: Entity) -> bool:
        """Remove component from entity. Returns True if existed."""
        if entity in self.components:
            del self.components[entity]
            return True
        return False
    
    def get(self, entity: Entity) -> Optional[Any]:
        """Get component for entity. Returns None if not present."""
        return self.components.get(entity)
    
    def has(self, entity: Entity) -> bool:
        """Check if entity has this component"""
        return entity in self.components
    
    def get_all(self) -> Dict[Entity, Any]:
        """Get all components (for iteration)"""
        return self.components
    
    def clear(self) -> None:
        """Remove all components"""
        self.components.clear()


class World:
    """
    Central ECS registry. Manages entities and components.
    
    INVARIANTS:
    - Entity exists iff it's in entity_pool.active
    - If entity has components, it must be active
    - Component dependencies are satisfied
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.entity_pool = EntityPool()
        self.component_storages: Dict[Type, ComponentStorage] = {}
        self.component_dependencies: Dict[Type, List[Type]] = {}
    
    # Entity Management
    
    def create_entity(self) -> Entity:
        """Create a new entity"""
        entity = self.entity_pool.acquire()
        if self.debug:
            print(f"[ECS] Created entity {entity}")
        return entity
    
    def destroy_entity(self, entity: Entity) -> None:
        """
        Destroy entity and all its components.
        Maintains invariant: no orphan components.
        """
        if not self.entity_pool.is_active(entity):
            return
        
        # Remove all components
        for storage in self.component_storages.values():
            storage.remove(entity)
        
        # Release entity ID
        self.entity_pool.release(entity)
        
        if self.debug:
            print(f"[ECS] Destroyed entity {entity}")
    
    def is_alive(self, entity: Entity) -> bool:
        """Check if entity exists"""
        return self.entity_pool.is_active(entity)
    
    def get_entity_count(self) -> int:
        """Get number of active entities"""
        return self.entity_pool.get_count()
    
    # Component Management
    
    def register_component(self, component_type: Type, 
                          dependencies: Optional[List[Type]] = None) -> None:
        """Register a component type with optional dependencies"""
        if component_type not in self.component_storages:
            self.component_storages[component_type] = ComponentStorage(component_type)
        
        if dependencies:
            self.component_dependencies[component_type] = dependencies
    
    def add_component(self, entity: Entity, component_type: Type, 
                     component: Any) -> None:
        """
        Add component to entity.
        
        PRECONDITION: Entity must exist
        PRECONDITION: Dependencies must be satisfied
        """
        if not self.is_alive(entity):
            raise ValueError(f"Entity {entity} does not exist")
        
        # Check dependencies
        if component_type in self.component_dependencies:
            for dep in self.component_dependencies[component_type]:
                if not self.has_component(entity, dep):
                    raise ValueError(
                        f"Cannot add {component_type.__name__} to entity {entity}: "
                        f"missing dependency {dep.__name__}"
                    )
        
        # Get or create storage
        if component_type not in self.component_storages:
            self.register_component(component_type)
        
        storage = self.component_storages[component_type]
        storage.add(entity, component)
        
        if self.debug:
            print(f"[ECS] Added {component_type.__name__} to entity {entity}")
    
    def remove_component(self, entity: Entity, component_type: Type) -> bool:
        """
        Remove component from entity.
        
        PRECONDITION: No other components depend on this one
        """
        if component_type not in self.component_storages:
            return False
        
        # Check if any components depend on this
        for other_type, deps in self.component_dependencies.items():
            if component_type in deps:
                if self.has_component(entity, other_type):
                    raise ValueError(
                        f"Cannot remove {component_type.__name__} from entity {entity}: "
                        f"{other_type.__name__} depends on it"
                    )
        
        storage = self.component_storages[component_type]
        result = storage.remove(entity)
        
        if self.debug and result:
            print(f"[ECS] Removed {component_type.__name__} from entity {entity}")
        
        return result
    
    def get_component(self, entity: Entity, component_type: Type) -> Optional[Any]:
        """Get component from entity"""
        if component_type not in self.component_storages:
            return None
        return self.component_storages[component_type].get(entity)
    
    def has_component(self, entity: Entity, component_type: Type) -> bool:
        """Check if entity has component"""
        if component_type not in self.component_storages:
            return False
        return self.component_storages[component_type].has(entity)
    
    def get_components(self, entity: Entity) -> Dict[Type, Any]:
        """Get all components for an entity"""
        components = {}
        for comp_type, storage in self.component_storages.items():
            comp = storage.get(entity)
            if comp is not None:
                components[comp_type] = comp
        return components
    
    def get_all_with_component(self, component_type: Type) -> Dict[Entity, Any]:
        """Get all entities with a specific component"""
        if component_type not in self.component_storages:
            return {}
        return self.component_storages[component_type].get_all()
    
    def query(self, *component_types: Type) -> List[Tuple[Entity, Tuple[Any, ...]]]:
        """
        Query entities with all specified components.
        
        Returns: List of (entity, (comp1, comp2, ...)) tuples
        
        Example:
            for entity, (pos, vel) in world.query(Position, Velocity):
                pos.x += vel.dx
        """
        if not component_types:
            return []
        
        # Start with entities that have first component
        first_type = component_types[0]
        if first_type not in self.component_storages:
            return []
        
        results = []
        first_storage = self.component_storages[first_type]
        
        # Check each entity with first component
        for entity in first_storage.get_all().keys():
            # Get all requested components
            components = []
            has_all = True
            
            for comp_type in component_types:
                comp = self.get_component(entity, comp_type)
                if comp is None:
                    has_all = False
                    break
                components.append(comp)
            
            if has_all:
                results.append((entity, tuple(components)))
        
        return results
    
    # Utility
    
    def clear(self) -> None:
        """Clear all entities and components"""
        for storage in self.component_storages.values():
            storage.clear()
        self.entity_pool = EntityPool()
        
        if self.debug:
            print("[ECS] Cleared world")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get world statistics"""
        component_counts = {
            comp_type.__name__: len(storage.get_all())
            for comp_type, storage in self.component_storages.items()
        }
        
        return {
            "entities": self.get_entity_count(),
            "entity_capacity": self.entity_pool.next_id - 1,
            "recycled_ids": len(self.entity_pool.available),
            "component_types": len(self.component_storages),
            "components_by_type": component_counts,
        }


class System:
    """
    Base class for systems.
    Systems operate on entities with specific components.
    """
    
    def __init__(self, priority: int = 0):
        self.priority = priority
        self.enabled = True
        self.last_update_time = 0.0
        self.update_count = 0
    
    def update(self, dt: float, world: World) -> None:
        """
        Update system. Called every tick.
        
        Args:
            dt: Delta time in seconds (typically 0.05 for 20 TPS)
            world: World instance with entities and components
        """
        if not self.enabled:
            return
        
        start = time.monotonic()
        self._do_update(dt, world)
        elapsed = time.monotonic() - start
        
        self.last_update_time = elapsed
        self.update_count += 1
    
    def _do_update(self, dt: float, world: World) -> None:
        """Override this in subclasses"""
        raise NotImplementedError
    
    def reset_stats(self) -> None:
        """Reset performance statistics"""
        self.last_update_time = 0.0
        self.update_count = 0


class SystemScheduler:
    """
    Manages system execution order and timing.
    
    INVARIANT: Systems execute in priority order each tick.
    """
    
    def __init__(self):
        self.systems: List[System] = []
        self.system_names: Dict[System, str] = {}
    
    def add_system(self, name: str, system: System) -> None:
        """Add system to scheduler"""
        self.systems.append(system)
        self.system_names[system] = name
        # Sort by priority (higher priority = earlier execution)
        self.systems.sort(key=lambda s: -s.priority)
    
    def remove_system(self, system: System) -> None:
        """Remove system from scheduler"""
        if system in self.systems:
            self.systems.remove(system)
            del self.system_names[system]
    
    def update(self, dt: float, world: World) -> Dict[str, float]:
        """
        Update all systems in order.
        
        Returns: Dict of system_name -> update_time
        """
        timings = {}
        
        for system in self.systems:
            if system.enabled:
                system.update(dt, world)
                name = self.system_names[system]
                timings[name] = system.last_update_time
        
        return timings
    
    def get_system_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all systems"""
        stats = {}
        for system in self.systems:
            name = self.system_names[system]
            stats[name] = {
                "enabled": system.enabled,
                "priority": system.priority,
                "last_update_time": system.last_update_time,
                "update_count": system.update_count,
            }
        return stats


# Example component types (defined here for documentation)

@dataclass
class Transform:
    """Position and orientation in 3D space"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0  # Radians


@dataclass
class Velocity:
    """Movement velocity"""
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0


# Example usage and testing
if __name__ == "__main__":
    # Create world
    world = World(debug=True)
    
    # Register components
    world.register_component(Transform)
    world.register_component(Velocity)
    
    # Create entities
    entity1 = world.create_entity()
    entity2 = world.create_entity()
    
    # Add components
    world.add_component(entity1, Transform, Transform(x=10, y=20, z=0))
    world.add_component(entity1, Velocity, Velocity(dx=1, dy=0, dz=0))
    
    world.add_component(entity2, Transform, Transform(x=0, y=0, z=0))
    
    # Query entities with both Transform and Velocity
    print("\nEntities with Transform and Velocity:")
    for entity, (transform, velocity) in world.query(Transform, Velocity):
        print(f"  Entity {entity}: pos=({transform.x}, {transform.y}), vel=({velocity.dx}, {velocity.dy})")
    
    # Get stats
    print("\nWorld stats:")
    for key, value in world.get_stats().items():
        print(f"  {key}: {value}")
    
    # Cleanup
    world.destroy_entity(entity1)
    world.destroy_entity(entity2)
    
    print("\nAfter cleanup:")
    print(f"  Active entities: {world.get_entity_count()}")
