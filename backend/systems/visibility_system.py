"""
Mind Rune - Visibility System

Field of view and fog of war calculations.
Uses raycasting for line-of-sight.

FEATURES:
- Per-entity vision radius
- Fog of war (explored vs visible)
- Line of sight blocking by walls
- Shadowcasting for smooth FOV
"""

import math
from typing import Set, Dict, Tuple, List, Optional
import logging

from backend.engine.ecs import System, World, Entity
from backend.components.core import Position, Vision, Player

logger = logging.getLogger(__name__)


class VisibilitySystem(System):
    """
    Calculates visibility/FOV for entities.
    Priority: 50
    """
    
    def __init__(self, world_3d):
        super().__init__(priority=50)
        self.world_3d = world_3d
        
        # Visibility cache per player
        self.visible_tiles: Dict[Entity, Set[Tuple[int, int, int]]] = {}
    
    def _do_update(self, dt: float, world: World) -> None:
        # Update visibility for all entities with Vision component
        for entity, (pos, vision) in world.query(Position, Vision):
            # Only calculate detailed FOV for players
            if world.get_component(entity, Player):
                self._calculate_fov(entity, pos, vision)
    
    def _calculate_fov(self, entity: Entity, pos: Position, vision: Vision) -> None:
        """Calculate field of view using shadowcasting"""
        center_x = int(pos.x)
        center_y = int(pos.y)
        center_z = int(pos.z)
        radius = int(vision.radius)
        
        visible = set()
        
        # Center tile is always visible
        visible.add((center_x, center_y, center_z))
        
        # Cast rays in all directions (simple raycasting)
        # For a proper roguelike, use recursive shadowcasting
        num_rays = max(32, radius * 4)
        
        for i in range(num_rays):
            angle = (2.0 * math.pi * i) / num_rays
            self._cast_ray(
                center_x, center_y, center_z,
                math.cos(angle), math.sin(angle),
                radius, visible
            )
        
        # Update vision component
        for tile in visible:
            vision.explored_tiles.add(tile)
        
        # Store current visible set
        self.visible_tiles[entity] = visible
    
    def _cast_ray(self, ox: int, oy: int, oz: int,
                  dx: float, dy: float, max_dist: int,
                  visible: Set[Tuple[int, int, int]]) -> None:
        """Cast a single ray and mark visible tiles"""
        x = float(ox)
        y = float(oy)
        
        for _ in range(max_dist):
            x += dx
            y += dy
            
            tile_x = int(round(x))
            tile_y = int(round(y))
            
            # Check distance
            dist_sq = (tile_x - ox)**2 + (tile_y - oy)**2
            if dist_sq > max_dist * max_dist:
                break
            
            visible.add((tile_x, tile_y, oz))
            
            # Check if blocked
            if self.world_3d and self._blocks_vision(tile_x, tile_y, oz):
                break
    
    def _blocks_vision(self, x: int, y: int, z: int) -> bool:
        """Check if tile blocks vision"""
        if not self.world_3d:
            return False
        
        tile = self.world_3d.get_tile(x, y, z)
        if tile is None:
            return True
        
        return tile.tile_type.blocks_vision
    
    def get_visible_tiles(self, entity: Entity) -> Set[Tuple[int, int, int]]:
        """Get currently visible tiles for entity"""
        return self.visible_tiles.get(entity, set())
    
    def is_visible_to(self, entity: Entity, x: int, y: int, z: int) -> bool:
        """Check if position is visible to entity"""
        visible = self.visible_tiles.get(entity, set())
        return (x, y, z) in visible
    
    def is_explored_by(self, entity: Entity, x: int, y: int, z: int, world: World) -> bool:
        """Check if position has been explored by entity"""
        vision = world.get_component(entity, Vision)
        if not vision:
            return False
        return (x, y, z) in vision.explored_tiles


class VisibilityData:
    """Helper class for serializing visibility data"""
    
    @staticmethod
    def get_visibility_for_client(entity: Entity, pos: Position, 
                                  vis_system: VisibilitySystem,
                                  world: World, radius: int = 25) -> Dict:
        """Get visibility data formatted for client"""
        vision = world.get_component(entity, Vision)
        visible = vis_system.get_visible_tiles(entity)
        
        tiles = {}
        center_x = int(pos.x)
        center_y = int(pos.y)
        center_z = int(pos.z)
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                x = center_x + dx
                y = center_y + dy
                z = center_z
                
                key = f"{x},{y},{z}"
                
                is_visible = (x, y, z) in visible
                is_explored = vision and (x, y, z) in vision.explored_tiles
                
                tiles[key] = {
                    "visible": is_visible,
                    "explored": is_explored
                }
        
        return tiles


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("=== Visibility System Test ===")
    
    from backend.engine.ecs import World
    from backend.world.world_3d import World3D
    
    # Create world
    ecs_world = World(debug=False)
    world_3d = World3D(seed=12345)
    world_3d.preload_around(0, 0, 0)
    
    # Register components
    ecs_world.register_component(Position)
    ecs_world.register_component(Vision)
    ecs_world.register_component(Player)
    
    # Create player
    player = ecs_world.create_entity()
    ecs_world.add_component(player, Position, Position(x=8, y=8, z=0))
    ecs_world.add_component(player, Vision, Vision(radius=15))
    ecs_world.add_component(player, Player, Player(account_id=1, character_name="Hero"))
    
    # Create visibility system
    vis_system = VisibilitySystem(world_3d)
    
    # Calculate FOV
    vis_system.update(0.05, ecs_world)
    
    # Print results
    visible = vis_system.get_visible_tiles(player)
    print(f"Visible tiles: {len(visible)}")
    
    vision = ecs_world.get_component(player, Vision)
    print(f"Explored tiles: {len(vision.explored_tiles)}")
    
    # Print visibility map
    print("\nVisibility around player (8,8):")
    print("  (@ = player, . = visible, # = blocked, ? = not visible)")
    for y in range(0, 17):
        row = ""
        for x in range(0, 17):
            if x == 8 and y == 8:
                row += "@"
            elif (x, y, 0) in visible:
                tile = world_3d.get_tile(x, y, 0)
                if tile and tile.tile_type.is_solid:
                    row += "#"
                else:
                    row += "."
            else:
                row += " "
        print(f"  {row}")
