"""
Mind Rune - 3D World Generation

True 3D world (x, y, z) with 2D top-down projection.
Supports multiple Z-levels (floors), caves, dungeons.

ARCHITECTURE:
- World is infinite-ish (chunk-based)
- Each chunk is 16x16x16 tiles
- Deterministic procedural generation (seed-based)
- Multi-level: surface (z=0), underground (z<0), sky (z>0)
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, Set
from enum import Enum
import random
import math


# Chunk coordinates
ChunkCoord = Tuple[int, int, int]  # (chunk_x, chunk_y, chunk_z)
# Tile coordinates
TileCoord = Tuple[int, int, int]   # (x, y, z)


class TileType(Enum):
    """Types of tiles in the world"""
    # Traversable
    EMPTY = " "          # Air/empty space
    FLOOR = "."          # Ground floor
    GRASS = ","          # Grassy ground
    WATER = "~"          # Water (maybe traversable)
    SAND = "∙"           # Sand
    
    # Obstacles
    WALL = "#"           # Solid wall
    TREE = "t"           # Tree
    MOUNTAIN = "^"       # Mountain peak
    ROCK = "o"           # Boulder
    
    # Features
    DOOR = "+"           # Door (traversable when open)
    STAIRS_UP = "<"      # Stairs going up
    STAIRS_DOWN = ">"    # Stairs going down
    CHEST = "C"          # Loot chest
    
    @property
    def is_solid(self) -> bool:
        """Can players walk through this?"""
        return self in {
            TileType.WALL, TileType.TREE, TileType.MOUNTAIN,
            TileType.ROCK, TileType.DOOR
        }
    
    @property
    def is_walkable(self) -> bool:
        """Can players walk on this?"""
        return not self.is_solid and self != TileType.EMPTY
    
    @property
    def blocks_vision(self) -> bool:
        """Does this block line of sight?"""
        return self in {TileType.WALL, TileType.MOUNTAIN, TileType.DOOR}


@dataclass
class Tile:
    """A single tile in the world"""
    tile_type: TileType
    z_level: int = 0
    
    # Visual properties
    color: str = "white"
    bg_color: str = "black"
    
    # Metadata
    discovered: bool = False
    visible: bool = False


@dataclass
class Chunk:
    """
    A chunk of world tiles (16x16x16).
    
    INVARIANTS:
    - Size is always CHUNK_SIZE^3
    - Tiles are indexed [x][y][z] where 0 <= x,y,z < CHUNK_SIZE
    """
    coord: ChunkCoord
    tiles: Dict[Tuple[int, int, int], Tile] = field(default_factory=dict)
    
    CHUNK_SIZE = 16
    
    def __post_init__(self):
        # Initialize empty chunk if not loaded
        if not self.tiles:
            for x in range(self.CHUNK_SIZE):
                for y in range(self.CHUNK_SIZE):
                    for z in range(self.CHUNK_SIZE):
                        self.tiles[(x, y, z)] = Tile(TileType.EMPTY)
    
    def get_tile(self, x: int, y: int, z: int) -> Optional[Tile]:
        """Get tile at local chunk coordinates"""
        if not (0 <= x < self.CHUNK_SIZE and 
                0 <= y < self.CHUNK_SIZE and
                0 <= z < self.CHUNK_SIZE):
            return None
        return self.tiles.get((x, y, z))
    
    def set_tile(self, x: int, y: int, z: int, tile: Tile) -> bool:
        """Set tile at local chunk coordinates"""
        if not (0 <= x < self.CHUNK_SIZE and 
                0 <= y < self.CHUNK_SIZE and
                0 <= z < self.CHUNK_SIZE):
            return False
        self.tiles[(x, y, z)] = tile
        return True


class WorldGenerator:
    """
    Generates world chunks procedurally.
    Deterministic based on seed + chunk coordinates.
    """
    
    def __init__(self, seed: int = 42):
        self.seed = seed
    
    def _get_chunk_rng(self, chunk_coord: ChunkCoord) -> random.Random:
        """Get deterministic RNG for a chunk"""
        # Hash chunk coordinates with seed
        chunk_hash = hash((self.seed, chunk_coord))
        return random.Random(chunk_hash)
    
    def generate_chunk(self, chunk_coord: ChunkCoord) -> Chunk:
        """Generate a chunk at given coordinates"""
        chunk = Chunk(coord=chunk_coord)
        cx, cy, cz = chunk_coord
        
        # Surface chunks (cz == 0)
        if cz == 0:
            self._generate_surface_chunk(chunk, cx, cy)
        # Underground chunks (cz < 0)
        elif cz < 0:
            self._generate_underground_chunk(chunk, cx, cy, cz)
        # Sky chunks (cz > 0)
        else:
            self._generate_sky_chunk(chunk, cx, cy, cz)
        
        return chunk
    
    def _generate_surface_chunk(self, chunk: Chunk, cx: int, cy: int) -> None:
        """Generate surface terrain"""
        rng = self._get_chunk_rng(chunk.coord)
        
        for lx in range(Chunk.CHUNK_SIZE):
            for ly in range(Chunk.CHUNK_SIZE):
                # World coordinates
                wx = cx * Chunk.CHUNK_SIZE + lx
                wy = cy * Chunk.CHUNK_SIZE + ly
                
                # Generate terrain using Perlin-like noise
                # (simplified - real implementation would use proper noise)
                terrain_value = self._terrain_noise(wx, wy)
                
                # Determine tile type based on noise value
                if terrain_value < -0.3:
                    tile_type = TileType.WATER
                    color = "blue"
                elif terrain_value < 0.0:
                    tile_type = TileType.SAND
                    color = "yellow"
                elif terrain_value < 0.5:
                    tile_type = TileType.GRASS
                    color = "green"
                elif terrain_value < 0.7:
                    # Trees
                    if rng.random() < 0.3:
                        tile_type = TileType.TREE
                        color = "darkgreen"
                    else:
                        tile_type = TileType.GRASS
                        color = "green"
                else:
                    # Mountains
                    tile_type = TileType.MOUNTAIN
                    color = "gray"
                
                # Set ground tile (z=0 is the surface level)
                chunk.set_tile(lx, ly, 0, Tile(
                    tile_type=tile_type,
                    z_level=0,
                    color=color
                ))
                
                # Fill above with air
                for lz in range(1, Chunk.CHUNK_SIZE):
                    chunk.set_tile(lx, ly, lz, Tile(
                        tile_type=TileType.EMPTY,
                        z_level=lz
                    ))
    
    def _generate_underground_chunk(self, chunk: Chunk, cx: int, cy: int, cz: int) -> None:
        """Generate underground caves and dungeons"""
        rng = self._get_chunk_rng(chunk.coord)
        
        # Start with all solid
        for lx in range(Chunk.CHUNK_SIZE):
            for ly in range(Chunk.CHUNK_SIZE):
                for lz in range(Chunk.CHUNK_SIZE):
                    chunk.set_tile(lx, ly, lz, Tile(
                        tile_type=TileType.WALL,
                        z_level=lz,
                        color="darkgray"
                    ))
        
        # Carve out caves
        num_caves = rng.randint(2, 5)
        for _ in range(num_caves):
            cx_local = rng.randint(2, Chunk.CHUNK_SIZE - 3)
            cy_local = rng.randint(2, Chunk.CHUNK_SIZE - 3)
            cz_local = rng.randint(2, Chunk.CHUNK_SIZE - 3)
            radius = rng.randint(2, 5)
            
            # Carve sphere
            for lx in range(Chunk.CHUNK_SIZE):
                for ly in range(Chunk.CHUNK_SIZE):
                    for lz in range(Chunk.CHUNK_SIZE):
                        dist = math.sqrt(
                            (lx - cx_local)**2 +
                            (ly - cy_local)**2 +
                            (lz - cz_local)**2
                        )
                        if dist <= radius:
                            chunk.set_tile(lx, ly, lz, Tile(
                                tile_type=TileType.FLOOR,
                                z_level=lz,
                                color="gray"
                            ))
    
    def _generate_sky_chunk(self, chunk: Chunk, cx: int, cy: int, cz: int) -> None:
        """Generate sky/floating islands"""
        # For now, just empty air
        for lx in range(Chunk.CHUNK_SIZE):
            for ly in range(Chunk.CHUNK_SIZE):
                for lz in range(Chunk.CHUNK_SIZE):
                    chunk.set_tile(lx, ly, lz, Tile(
                        tile_type=TileType.EMPTY,
                        z_level=lz
                    ))
    
    def _terrain_noise(self, x: int, y: int) -> float:
        """
        Simple pseudo-random terrain noise.
        Real implementation would use Perlin or Simplex noise.
        """
        # Use sine waves for now (creates interesting patterns)
        freq1 = 0.05
        freq2 = 0.1
        freq3 = 0.02
        
        v1 = math.sin(x * freq1) * math.cos(y * freq1)
        v2 = math.sin(x * freq2 + 5) * math.cos(y * freq2 + 5)
        v3 = math.sin(x * freq3 + 10) * math.cos(y * freq3 + 10)
        
        return (v1 + v2 * 0.5 + v3 * 0.3) / 1.8


class World3D:
    """
    3D world manager.
    Handles chunk loading/unloading and tile access.
    
    INVARIANTS:
    - Loaded chunks are always fully generated
    - Tile coordinates map to correct chunks
    - Chunk cache size is bounded
    """
    
    def __init__(self, seed: int = 42, max_cached_chunks: int = 100):
        self.seed = seed
        self.generator = WorldGenerator(seed)
        self.chunks: Dict[ChunkCoord, Chunk] = {}
        self.max_cached_chunks = max_cached_chunks
    
    @staticmethod
    def world_to_chunk(x: int, y: int, z: int) -> Tuple[ChunkCoord, Tuple[int, int, int]]:
        """
        Convert world coordinates to chunk coordinates + local offset.
        
        Returns: (chunk_coord, (local_x, local_y, local_z))
        """
        chunk_x = x // Chunk.CHUNK_SIZE
        chunk_y = y // Chunk.CHUNK_SIZE
        chunk_z = z // Chunk.CHUNK_SIZE
        
        local_x = x % Chunk.CHUNK_SIZE
        local_y = y % Chunk.CHUNK_SIZE
        local_z = z % Chunk.CHUNK_SIZE
        
        return ((chunk_x, chunk_y, chunk_z), (local_x, local_y, local_z))
    
    def get_chunk(self, chunk_coord: ChunkCoord, generate: bool = True) -> Optional[Chunk]:
        """Get or generate chunk"""
        if chunk_coord in self.chunks:
            return self.chunks[chunk_coord]
        
        if not generate:
            return None
        
        # Check cache size
        if len(self.chunks) >= self.max_cached_chunks:
            # Remove oldest chunk (simple LRU would be better)
            oldest = next(iter(self.chunks))
            del self.chunks[oldest]
        
        # Generate new chunk
        chunk = self.generator.generate_chunk(chunk_coord)
        self.chunks[chunk_coord] = chunk
        return chunk
    
    def get_tile(self, x: int, y: int, z: int) -> Optional[Tile]:
        """Get tile at world coordinates"""
        chunk_coord, (lx, ly, lz) = self.world_to_chunk(x, y, z)
        chunk = self.get_chunk(chunk_coord)
        
        if chunk is None:
            return None
        
        return chunk.get_tile(lx, ly, lz)
    
    def set_tile(self, x: int, y: int, z: int, tile: Tile) -> bool:
        """Set tile at world coordinates"""
        chunk_coord, (lx, ly, lz) = self.world_to_chunk(x, y, z)
        chunk = self.get_chunk(chunk_coord)
        
        if chunk is None:
            return False
        
        return chunk.set_tile(lx, ly, lz, tile)
    
    def is_solid(self, x: int, y: int, z: int) -> bool:
        """Check if tile at position is solid"""
        tile = self.get_tile(x, y, z)
        if tile is None:
            return True  # Out of bounds = solid
        return tile.tile_type.is_solid
    
    def is_walkable(self, x: int, y: int, z: int) -> bool:
        """Check if tile at position is walkable"""
        tile = self.get_tile(x, y, z)
        if tile is None:
            return False
        return tile.tile_type.is_walkable
    
    def get_visible_tiles(self, center_x: int, center_y: int, center_z: int, 
                         radius: int) -> Dict[TileCoord, Tile]:
        """Get all tiles visible from center point"""
        visible = {}
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                x = center_x + dx
                y = center_y + dy
                
                # Check distance
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > radius:
                    continue
                
                # For 2D projection, we show tiles at same Z level
                tile = self.get_tile(x, y, center_z)
                if tile is not None:
                    visible[(x, y, center_z)] = tile
        
        return visible
    
    def preload_around(self, x: int, y: int, z: int, radius_chunks: int = 2) -> None:
        """Preload chunks around a position"""
        chunk_coord, _ = self.world_to_chunk(x, y, z)
        cx, cy, cz = chunk_coord
        
        for dx in range(-radius_chunks, radius_chunks + 1):
            for dy in range(-radius_chunks, radius_chunks + 1):
                for dz in range(-1, 2):  # Only load 3 z-levels
                    coord = (cx + dx, cy + dy, cz + dz)
                    self.get_chunk(coord)
    
    def get_stats(self) -> Dict[str, any]:
        """Get world statistics"""
        return {
            "seed": self.seed,
            "loaded_chunks": len(self.chunks),
            "max_cached_chunks": self.max_cached_chunks,
        }


# Testing
if __name__ == "__main__":
    print("=== 3D World Generation Test ===\n")
    
    world = World3D(seed=12345)
    
    # Generate area around origin
    print("Generating chunks around origin...")
    world.preload_around(0, 0, 0, radius_chunks=2)
    
    print(f"World stats: {world.get_stats()}\n")
    
    # Print a small section
    print("Surface terrain (20x20 centered at origin):\n")
    for y in range(-10, 10):
        row = ""
        for x in range(-10, 10):
            tile = world.get_tile(x, y, 0)
            if tile:
                row += tile.tile_type.value
            else:
                row += "?"
        print(row)
    
    # Test 3D
    print("\n=== 3D Test ===")
    print(f"Tile at (0, 0, 0): {world.get_tile(0, 0, 0).tile_type.value}")
    print(f"Tile at (0, 0, -1): {world.get_tile(0, 0, -1).tile_type.value}")
    print(f"Is (0, 0, 0) walkable? {world.is_walkable(0, 0, 0)}")
    print(f"Is (0, 0, 0) solid? {world.is_solid(0, 0, 0)}")
