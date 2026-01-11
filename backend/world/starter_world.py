"""
Mind Rune - Starter World Generator

Creates the initial play area with:
- 100x100 starter zone
- Town area with safe NPCs
- Wilderness with enemies
- Basic dungeon entrance
- Items and loot
"""

import random
import math
from typing import List, Tuple, Dict, Optional
import logging

from backend.engine.ecs import World, Entity
from backend.engine.spatial import SpatialHashGrid
from backend.world.world_3d import World3D, Tile, TileType, Chunk
from backend.components.core import (
    Position, Velocity, Stats, CombatState, Cooldowns, AI, AIState, Faction,
    Sprite, Identity, EntityType, Loot, Inventory
)

logger = logging.getLogger(__name__)


class StarterWorldGenerator:
    """Generates the starter area for new players"""
    
    def __init__(self, ecs_world: World, world_3d: World3D, spatial_index: SpatialHashGrid):
        self.ecs_world = ecs_world
        self.world_3d = world_3d
        self.spatial_index = spatial_index
        self.rng = random.Random(world_3d.seed)
        
        # Track spawned entities
        self.spawned_entities: List[Entity] = []
    
    def generate(self) -> None:
        """Generate the complete starter area"""
        logger.info("Generating starter world...")
        
        # Preload chunks for starter area (100x100 centered at origin)
        self._preload_chunks()
        
        # Override terrain for starter area
        self._generate_terrain()
        
        # Place structures
        self._place_town()
        
        # Spawn NPCs
        self._spawn_friendly_npcs()
        self._spawn_enemies()
        
        # Place items
        self._place_starter_items()
        
        logger.info(f"Starter world generated. Spawned {len(self.spawned_entities)} entities.")
    
    def _preload_chunks(self) -> None:
        """Preload chunks for starter area"""
        # 100x100 area needs about 7x7 chunks
        for cx in range(-1, 8):
            for cy in range(-1, 8):
                self.world_3d.get_chunk((cx, cy, 0))
    
    def _generate_terrain(self) -> None:
        """Generate custom terrain for starter area"""
        # Create a cleared area around spawn (town)
        town_center = (8, 8)
        town_radius = 6
        
        # Generate terrain
        for x in range(0, 100):
            for y in range(0, 100):
                dist_from_town = math.sqrt((x - town_center[0])**2 + (y - town_center[1])**2)
                
                if dist_from_town < town_radius:
                    # Town area - floor tiles
                    self._set_tile(x, y, 0, TileType.FLOOR, "#a0a0a0")
                elif dist_from_town < town_radius + 2:
                    # Town border - path
                    self._set_tile(x, y, 0, TileType.SAND, "#d4b896")
                else:
                    # Wilderness - keep procedural but modify
                    tile = self.world_3d.get_tile(x, y, 0)
                    if tile:
                        # Add more trees in forest areas
                        if tile.tile_type == TileType.GRASS and self.rng.random() < 0.15:
                            self._set_tile(x, y, 0, TileType.TREE, "#228b22")
                        # Add rocks occasionally
                        elif tile.tile_type == TileType.GRASS and self.rng.random() < 0.02:
                            self._set_tile(x, y, 0, TileType.ROCK, "#808080")
        
        # Create walls around edges
        for x in range(0, 100):
            self._set_tile(x, 0, 0, TileType.WALL, "#404040")
            self._set_tile(x, 99, 0, TileType.WALL, "#404040")
        for y in range(0, 100):
            self._set_tile(0, y, 0, TileType.WALL, "#404040")
            self._set_tile(99, y, 0, TileType.WALL, "#404040")
        
        # Create a path from town to different areas
        self._create_path(town_center, (50, 50))  # Path to center
        self._create_path(town_center, (90, 50))  # Path to east
        self._create_path(town_center, (50, 90))  # Path to south (dungeon)
        
        # Place dungeon entrance
        self._create_dungeon_entrance(50, 90)
    
    def _set_tile(self, x: int, y: int, z: int, tile_type: TileType, color: str) -> None:
        """Set a tile in the world"""
        self.world_3d.set_tile(x, y, z, Tile(
            tile_type=tile_type,
            z_level=z,
            color=color
        ))
    
    def _create_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> None:
        """Create a path between two points"""
        x, y = start
        ex, ey = end
        
        while abs(x - ex) > 1 or abs(y - ey) > 1:
            # Move toward target with some randomness
            if abs(x - ex) > abs(y - ey):
                x += 1 if ex > x else -1
            elif abs(y - ey) > 0:
                y += 1 if ey > y else -1
            
            # Random deviation
            if self.rng.random() < 0.2:
                x += self.rng.choice([-1, 0, 1])
                y += self.rng.choice([-1, 0, 1])
            
            x = max(1, min(98, x))
            y = max(1, min(98, y))
            
            # Clear path
            self._set_tile(x, y, 0, TileType.SAND, "#d4b896")
            # Widen path slightly
            if self.rng.random() < 0.3:
                nx = x + self.rng.choice([-1, 1])
                ny = y + self.rng.choice([-1, 1])
                self._set_tile(nx, ny, 0, TileType.SAND, "#d4b896")
    
    def _create_dungeon_entrance(self, x: int, y: int) -> None:
        """Create dungeon entrance area"""
        # Clear area
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                self._set_tile(x + dx, y + dy, 0, TileType.FLOOR, "#505050")
        
        # Walls around
        for dx in range(-3, 4):
            self._set_tile(x + dx, y - 3, 0, TileType.WALL, "#303030")
            self._set_tile(x + dx, y + 3, 0, TileType.WALL, "#303030")
        for dy in range(-3, 4):
            self._set_tile(x - 3, y + dy, 0, TileType.WALL, "#303030")
            self._set_tile(x + 3, y + dy, 0, TileType.WALL, "#303030")
        
        # Entrance (stairs down)
        self._set_tile(x, y, 0, TileType.STAIRS_DOWN, "#ffff00")
    
    def _place_town(self) -> None:
        """Place town structures"""
        town_center = (8, 8)
        
        # Simple buildings (just walls with doors)
        buildings = [
            (3, 3, 3, 4, "Shop"),   # x, y, w, h, name
            (10, 3, 4, 3, "Inn"),
            (3, 11, 3, 3, "Armory"),
        ]
        
        for bx, by, bw, bh, name in buildings:
            # Walls
            for x in range(bx, bx + bw):
                self._set_tile(x, by, 0, TileType.WALL, "#8b4513")
                self._set_tile(x, by + bh - 1, 0, TileType.WALL, "#8b4513")
            for y in range(by, by + bh):
                self._set_tile(bx, y, 0, TileType.WALL, "#8b4513")
                self._set_tile(bx + bw - 1, y, 0, TileType.WALL, "#8b4513")
            
            # Floor inside
            for x in range(bx + 1, bx + bw - 1):
                for y in range(by + 1, by + bh - 1):
                    self._set_tile(x, y, 0, TileType.FLOOR, "#deb887")
            
            # Door
            door_x = bx + bw // 2
            self._set_tile(door_x, by + bh - 1, 0, TileType.DOOR, "#8b4513")
    
    def _spawn_friendly_npcs(self) -> None:
        """Spawn friendly NPCs in town"""
        friendly_npcs = [
            (5, 5, "Merchant", "M", "#00ff00", "A traveling merchant."),
            (12, 5, "Innkeeper", "I", "#00ff00", "The friendly innkeeper."),
            (5, 13, "Blacksmith", "B", "#00ff00", "A skilled blacksmith."),
            (8, 10, "Elder", "E", "#00ffff", "The village elder."),
        ]
        
        for x, y, name, char, color, desc in friendly_npcs:
            entity = self._spawn_npc(
                x=x, y=y, z=0,
                name=name,
                char=char,
                color=color,
                description=desc,
                faction=Faction.FRIENDLY,
                level=1,
                hp=100,
                aggro_radius=0  # Never aggro
            )
            self.spawned_entities.append(entity)
    
    def _spawn_enemies(self) -> None:
        """Spawn enemies in wilderness"""
        # Define enemy types
        enemy_types = [
            {
                "name": "Goblin",
                "char": "g",
                "color": "#228b22",
                "hp": 30,
                "attack": 5,
                "level": 1,
                "xp_value": 10,
                "loot": {
                    "guaranteed": [],
                    "possible": {"goblin_ear": 0.5, "health_potion": 0.1},
                    "gold_min": 1,
                    "gold_max": 5
                }
            },
            {
                "name": "Wolf",
                "char": "w",
                "color": "#808080",
                "hp": 25,
                "attack": 7,
                "level": 1,
                "xp_value": 8,
                "loot": {
                    "guaranteed": [],
                    "possible": {"bone": 0.7},
                    "gold_min": 0,
                    "gold_max": 0
                }
            },
            {
                "name": "Orc",
                "char": "O",
                "color": "#556b2f",
                "hp": 60,
                "attack": 12,
                "level": 3,
                "xp_value": 25,
                "loot": {
                    "guaranteed": [],
                    "possible": {"rusty_sword": 0.2, "health_potion": 0.3},
                    "gold_min": 5,
                    "gold_max": 15
                }
            },
            {
                "name": "Skeleton",
                "char": "s",
                "color": "#f5f5dc",
                "hp": 35,
                "attack": 8,
                "level": 2,
                "xp_value": 15,
                "loot": {
                    "guaranteed": ["bone"],
                    "possible": {"iron_helm": 0.1},
                    "gold_min": 2,
                    "gold_max": 8
                }
            },
        ]
        
        # Spawn zones (avoid town area)
        spawn_zones = [
            (25, 25, 30, "goblin"),   # x, y, radius, enemy_type
            (75, 25, 25, "wolf"),
            (50, 50, 20, "orc"),
            (50, 80, 15, "skeleton"),
            (80, 80, 20, "goblin"),
        ]
        
        for zx, zy, radius, enemy_key in spawn_zones:
            enemy_type = next((e for e in enemy_types if e["name"].lower() == enemy_key), enemy_types[0])
            
            # Spawn 3-6 enemies per zone
            num_enemies = self.rng.randint(3, 6)
            
            for _ in range(num_enemies):
                # Random position within zone
                angle = self.rng.random() * 2 * math.pi
                dist = self.rng.random() * radius
                x = int(zx + math.cos(angle) * dist)
                y = int(zy + math.sin(angle) * dist)
                
                # Ensure valid position
                x = max(5, min(94, x))
                y = max(5, min(94, y))
                
                # Check if walkable
                if not self.world_3d.is_walkable(x, y, 0):
                    continue
                
                entity = self._spawn_enemy(x, y, enemy_type)
                if entity:
                    self.spawned_entities.append(entity)
    
    def _spawn_npc(self, x: float, y: float, z: float, name: str, char: str,
                   color: str, description: str, faction: Faction,
                   level: int = 1, hp: int = 100, aggro_radius: float = 0) -> Entity:
        """Spawn an NPC entity"""
        entity = self.ecs_world.create_entity()
        
        self.ecs_world.add_component(entity, Position, Position(x=x, y=y, z=z))
        self.ecs_world.add_component(entity, Velocity, Velocity())
        self.ecs_world.add_component(entity, Stats, Stats(
            level=level,
            max_hp=hp,
            attack_power=5,
            move_speed=3.0
        ))
        self.ecs_world.add_component(entity, CombatState, CombatState(hp=hp, mp=0))
        self.ecs_world.add_component(entity, Cooldowns, Cooldowns())
        self.ecs_world.add_component(entity, Sprite, Sprite(char=char, color=color))
        self.ecs_world.add_component(entity, Identity, Identity(
            entity_type=EntityType.NPC,
            name=name,
            description=description
        ))
        self.ecs_world.add_component(entity, AI, AI(
            state=AIState.IDLE,
            faction=faction,
            aggro_radius=aggro_radius,
            chase_radius=aggro_radius * 2,
            spawn_x=x,
            spawn_y=y,
            spawn_z=z
        ))
        
        self.spatial_index.insert(entity, x, y, z)
        return entity
    
    def _spawn_enemy(self, x: int, y: int, enemy_type: Dict) -> Entity:
        """Spawn an enemy entity"""
        entity = self.ecs_world.create_entity()
        
        hp = enemy_type["hp"]
        
        self.ecs_world.add_component(entity, Position, Position(x=float(x), y=float(y), z=0.0))
        self.ecs_world.add_component(entity, Velocity, Velocity())
        self.ecs_world.add_component(entity, Stats, Stats(
            level=enemy_type["level"],
            max_hp=hp,
            attack_power=enemy_type["attack"],
            move_speed=3.5
        ))
        self.ecs_world.add_component(entity, CombatState, CombatState(hp=hp, mp=0))
        self.ecs_world.add_component(entity, Cooldowns, Cooldowns())
        self.ecs_world.add_component(entity, Sprite, Sprite(
            char=enemy_type["char"],
            color=enemy_type["color"]
        ))
        self.ecs_world.add_component(entity, Identity, Identity(
            entity_type=EntityType.NPC,
            name=enemy_type["name"],
            description=f"A hostile {enemy_type['name'].lower()}."
        ))
        self.ecs_world.add_component(entity, AI, AI(
            state=AIState.WANDERING,
            faction=Faction.HOSTILE,
            aggro_radius=10.0,
            chase_radius=20.0,
            attack_range=1.5,
            spawn_x=float(x),
            spawn_y=float(y),
            spawn_z=0.0
        ))
        
        # Add loot table
        loot_data = enemy_type.get("loot", {})
        self.ecs_world.add_component(entity, Loot, Loot(
            guaranteed_items=loot_data.get("guaranteed", []),
            possible_items=loot_data.get("possible", {}),
            gold_min=loot_data.get("gold_min", 0),
            gold_max=loot_data.get("gold_max", 0),
            experience_value=enemy_type.get("xp_value", 10)
        ))
        
        self.spatial_index.insert(entity, x, y, 0)
        return entity
    
    def _place_starter_items(self) -> None:
        """Place some starter items in the world"""
        # Items near town for new players
        starter_items = [
            (10, 12, "health_potion"),
            (6, 10, "rusty_sword"),
        ]
        
        # This would use the inventory system to place ground items
        # For now, we'll spawn them as entities
        for x, y, template_id in starter_items:
            entity = self._spawn_item(x, y, template_id)
            if entity:
                self.spawned_entities.append(entity)
    
    def _spawn_item(self, x: int, y: int, template_id: str) -> Optional[Entity]:
        """Spawn an item entity on the ground"""
        from backend.systems.inventory_system import ITEM_TEMPLATES
        
        template = ITEM_TEMPLATES.get(template_id)
        if not template:
            return None
        
        entity = self.ecs_world.create_entity()
        
        self.ecs_world.add_component(entity, Position, Position(x=float(x), y=float(y), z=0.0))
        self.ecs_world.add_component(entity, Sprite, Sprite(
            char=template.get("char", "?"),
            color=template.get("color", "#ffffff")
        ))
        self.ecs_world.add_component(entity, Identity, Identity(
            entity_type=EntityType.ITEM,
            name=template["name"],
            description=template.get("description", "")
        ))
        
        self.spatial_index.insert(entity, x, y, 0)
        return entity


def create_starter_world(ecs_world: World, seed: int = 12345) -> Tuple[World3D, SpatialHashGrid]:
    """Create and populate the starter world"""
    # Create 3D world
    world_3d = World3D(seed=seed)
    
    # Create spatial index
    spatial_index = SpatialHashGrid(cell_size=16.0)
    
    # Register all components
    ecs_world.register_component(Position)
    ecs_world.register_component(Velocity)
    ecs_world.register_component(Stats)
    ecs_world.register_component(CombatState, dependencies=[Stats])
    ecs_world.register_component(Cooldowns)
    ecs_world.register_component(AI)
    ecs_world.register_component(Sprite)
    ecs_world.register_component(Identity)
    ecs_world.register_component(Loot)
    ecs_world.register_component(Inventory, dependencies=[Stats])
    
    # Generate starter area
    generator = StarterWorldGenerator(ecs_world, world_3d, spatial_index)
    generator.generate()
    
    return world_3d, spatial_index


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from backend.engine.ecs import World
    
    print("=== Starter World Generation Test ===\n")
    
    ecs_world = World(debug=False)
    world_3d, spatial_index = create_starter_world(ecs_world)
    
    print(f"ECS World: {ecs_world.get_entity_count()} entities")
    print(f"3D World: {world_3d.get_stats()}")
    
    # Print map
    print("\nStarter area map (100x100):\n")
    
    # Print in chunks
    for chunk_y in range(6):
        rows = []
        for local_y in range(16):
            y = chunk_y * 16 + local_y
            if y >= 100:
                break
            row = ""
            for x in range(100):
                tile = world_3d.get_tile(x, y, 0)
                if tile:
                    row += tile.tile_type.value
                else:
                    row += " "
            rows.append(row)
        
        for row in rows:
            print(row[:100])
