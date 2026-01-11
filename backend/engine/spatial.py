"""
Mind Rune - Spatial Indexing

Efficient spatial queries using hash-grid structure.
Provides O(1) insertion/removal and O(k) queries where k = entities in radius.

Critical for:
- Collision detection
- Visibility checks
- AI perception
- Area effects
"""

from typing import Dict, Set, Tuple, List, Optional
from dataclasses import dataclass
import math


@dataclass
class AABB:
    """Axis-aligned bounding box"""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float
    
    def contains_point(self, x: float, y: float, z: float) -> bool:
        """Check if point is inside AABB"""
        return (self.min_x <= x <= self.max_x and
                self.min_y <= y <= self.max_y and
                self.min_z <= z <= self.max_z)
    
    def intersects(self, other: 'AABB') -> bool:
        """Check if two AABBs intersect"""
        return (self.min_x <= other.max_x and self.max_x >= other.min_x and
                self.min_y <= other.max_y and self.max_y >= other.min_y and
                self.min_z <= other.max_z and self.max_z >= other.min_z)


# Type alias for entities
Entity = int

# Grid cell coordinates
Cell = Tuple[int, int, int]


class SpatialHashGrid:
    """
    3D spatial hash grid for fast proximity queries.
    
    INVARIANTS:
    - Entity in grid iff it has been inserted and not removed
    - Entity's cell matches its position
    - No duplicate entities in same cell
    
    PERFORMANCE:
    - Insert: O(1)
    - Remove: O(1)  
    - Query radius: O(k) where k = entities in radius
    - Memory: O(n) where n = number of entities
    """
    
    def __init__(self, cell_size: float = 10.0):
        self.cell_size = cell_size
        # Maps cell -> set of entities in that cell
        self.cells: Dict[Cell, Set[Entity]] = {}
        # Maps entity -> its current cell (for fast removal)
        self.entity_cells: Dict[Entity, Cell] = {}
    
    def _get_cell(self, x: float, y: float, z: float) -> Cell:
        """Convert world position to cell coordinates"""
        return (
            int(math.floor(x / self.cell_size)),
            int(math.floor(y / self.cell_size)),
            int(math.floor(z / self.cell_size))
        )
    
    def insert(self, entity: Entity, x: float, y: float, z: float) -> None:
        """
        Insert entity at position.
        
        PRECONDITION: Entity not already in grid
        """
        if entity in self.entity_cells:
            # Already in grid, move it instead
            self.update(entity, x, y, z)
            return
        
        cell = self._get_cell(x, y, z)
        
        # Add to cell
        if cell not in self.cells:
            self.cells[cell] = set()
        self.cells[cell].add(entity)
        
        # Track entity's cell
        self.entity_cells[entity] = cell
    
    def remove(self, entity: Entity) -> bool:
        """
        Remove entity from grid.
        
        Returns: True if entity was in grid
        """
        if entity not in self.entity_cells:
            return False
        
        # Get entity's cell
        cell = self.entity_cells[entity]
        
        # Remove from cell
        if cell in self.cells:
            self.cells[cell].discard(entity)
            # Clean up empty cells
            if not self.cells[cell]:
                del self.cells[cell]
        
        # Remove tracking
        del self.entity_cells[entity]
        
        return True
    
    def update(self, entity: Entity, x: float, y: float, z: float) -> None:
        """
        Update entity position.
        More efficient than remove + insert if entity stays in same cell.
        """
        new_cell = self._get_cell(x, y, z)
        
        # Check if entity is already in grid
        if entity in self.entity_cells:
            old_cell = self.entity_cells[entity]
            
            # Same cell? Nothing to do
            if old_cell == new_cell:
                return
            
            # Remove from old cell
            if old_cell in self.cells:
                self.cells[old_cell].discard(entity)
                if not self.cells[old_cell]:
                    del self.cells[old_cell]
        
        # Add to new cell
        if new_cell not in self.cells:
            self.cells[new_cell] = set()
        self.cells[new_cell].add(entity)
        
        # Update tracking
        self.entity_cells[entity] = new_cell
    
    def query_point(self, x: float, y: float, z: float) -> Set[Entity]:
        """Get all entities in the same cell as point"""
        cell = self._get_cell(x, y, z)
        return self.cells.get(cell, set()).copy()
    
    def query_radius(self, x: float, y: float, z: float, radius: float) -> Set[Entity]:
        """
        Get all entities within radius of point.
        
        Algorithm:
        1. Calculate cells that intersect sphere
        2. Check entities in those cells
        3. Filter by actual distance
        
        PERFORMANCE: O(k) where k = entities in radius
        """
        results = set()
        
        # Calculate cell bounds
        min_cell = self._get_cell(x - radius, y - radius, z - radius)
        max_cell = self._get_cell(x + radius, y + radius, z + radius)
        
        # Check all cells in range
        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                for cz in range(min_cell[2], max_cell[2] + 1):
                    cell = (cx, cy, cz)
                    if cell in self.cells:
                        results.update(self.cells[cell])
        
        return results
    
    def query_radius_precise(self, x: float, y: float, z: float, radius: float,
                            positions: Dict[Entity, Tuple[float, float, float]]) -> Set[Entity]:
        """
        Get entities within radius, with precise distance check.
        Requires position lookup dict.
        """
        candidates = self.query_radius(x, y, z, radius)
        results = set()
        radius_sq = radius * radius
        
        for entity in candidates:
            if entity not in positions:
                continue
            
            ex, ey, ez = positions[entity]
            dist_sq = (ex - x)**2 + (ey - y)**2 + (ez - z)**2
            
            if dist_sq <= radius_sq:
                results.add(entity)
        
        return results
    
    def query_aabb(self, aabb: AABB) -> Set[Entity]:
        """Get all entities within axis-aligned bounding box"""
        results = set()
        
        # Get cell range
        min_cell = self._get_cell(aabb.min_x, aabb.min_y, aabb.min_z)
        max_cell = self._get_cell(aabb.max_x, aabb.max_y, aabb.max_z)
        
        # Check cells
        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                for cz in range(min_cell[2], max_cell[2] + 1):
                    cell = (cx, cy, cz)
                    if cell in self.cells:
                        results.update(self.cells[cell])
        
        return results
    
    def get_cell_for_entity(self, entity: Entity) -> Optional[Cell]:
        """Get the cell an entity is in"""
        return self.entity_cells.get(entity)
    
    def clear(self) -> None:
        """Remove all entities"""
        self.cells.clear()
        self.entity_cells.clear()
    
    def get_stats(self) -> Dict[str, any]:
        """Get statistics about the spatial index"""
        total_entities = len(self.entity_cells)
        total_cells = len(self.cells)
        
        if total_cells > 0:
            entities_per_cell = [len(entities) for entities in self.cells.values()]
            avg_entities = sum(entities_per_cell) / len(entities_per_cell)
            max_entities = max(entities_per_cell)
        else:
            avg_entities = 0
            max_entities = 0
        
        return {
            "total_entities": total_entities,
            "total_cells": total_cells,
            "avg_entities_per_cell": avg_entities,
            "max_entities_per_cell": max_entities,
            "cell_size": self.cell_size,
        }


class QuadTree:
    """
    2D QuadTree for more memory-efficient spatial indexing when needed.
    Useful for large sparse worlds.
    """
    
    def __init__(self, bounds: AABB, capacity: int = 8, max_depth: int = 6):
        self.bounds = bounds
        self.capacity = capacity
        self.max_depth = max_depth
        self.entities: List[Tuple[Entity, float, float]] = []
        self.subdivided = False
        self.children: List[Optional['QuadTree']] = [None, None, None, None]
    
    def insert(self, entity: Entity, x: float, y: float) -> bool:
        """Insert entity at 2D position"""
        # Check if point is in bounds
        if not (self.bounds.min_x <= x <= self.bounds.max_x and
                self.bounds.min_y <= y <= self.bounds.max_y):
            return False
        
        # If not subdivided and under capacity, add here
        if not self.subdivided and len(self.entities) < self.capacity:
            self.entities.append((entity, x, y))
            return True
        
        # Need to subdivide
        if not self.subdivided and self.max_depth > 0:
            self._subdivide()
        
        # Try to insert in children
        if self.subdivided:
            for child in self.children:
                if child and child.insert(entity, x, y):
                    return True
        
        # Fallback: add to this node anyway
        self.entities.append((entity, x, y))
        return True
    
    def _subdivide(self) -> None:
        """Split this node into 4 quadrants"""
        cx = (self.bounds.min_x + self.bounds.max_x) / 2
        cy = (self.bounds.min_y + self.bounds.max_y) / 2
        
        # Create 4 children
        self.children[0] = QuadTree(
            AABB(self.bounds.min_x, self.bounds.min_y, 0,
                 cx, cy, 0),
            self.capacity, self.max_depth - 1
        )
        self.children[1] = QuadTree(
            AABB(cx, self.bounds.min_y, 0,
                 self.bounds.max_x, cy, 0),
            self.capacity, self.max_depth - 1
        )
        self.children[2] = QuadTree(
            AABB(self.bounds.min_x, cy, 0,
                 cx, self.bounds.max_y, 0),
            self.capacity, self.max_depth - 1
        )
        self.children[3] = QuadTree(
            AABB(cx, cy, 0,
                 self.bounds.max_x, self.bounds.max_y, 0),
            self.capacity, self.max_depth - 1
        )
        
        self.subdivided = True
        
        # Redistribute entities to children
        old_entities = self.entities
        self.entities = []
        
        for entity, x, y in old_entities:
            inserted = False
            for child in self.children:
                if child and child.insert(entity, x, y):
                    inserted = True
                    break
            if not inserted:
                self.entities.append((entity, x, y))
    
    def query_radius(self, x: float, y: float, radius: float) -> Set[Entity]:
        """Get entities within radius (2D)"""
        results = set()
        
        # Check if circle intersects bounds
        # Simple AABB-circle intersection test
        closest_x = max(self.bounds.min_x, min(x, self.bounds.max_x))
        closest_y = max(self.bounds.min_y, min(y, self.bounds.max_y))
        dist_sq = (x - closest_x)**2 + (y - closest_y)**2
        
        if dist_sq > radius * radius:
            return results
        
        # Check entities in this node
        radius_sq = radius * radius
        for entity, ex, ey in self.entities:
            dist_sq = (ex - x)**2 + (ey - y)**2
            if dist_sq <= radius_sq:
                results.add(entity)
        
        # Check children
        if self.subdivided:
            for child in self.children:
                if child:
                    results.update(child.query_radius(x, y, radius))
        
        return results


# Testing and examples
if __name__ == "__main__":
    print("=== Spatial Hash Grid Test ===\n")
    
    grid = SpatialHashGrid(cell_size=10.0)
    
    # Insert entities
    grid.insert(1, 5, 5, 0)
    grid.insert(2, 15, 5, 0)
    grid.insert(3, 5, 15, 0)
    grid.insert(4, 25, 25, 0)
    
    print("Inserted 4 entities")
    print(f"Stats: {grid.get_stats()}\n")
    
    # Query radius
    results = grid.query_radius(10, 10, 10)
    print(f"Entities within 10 units of (10, 10, 0): {results}")
    
    # Update entity
    grid.update(1, 25, 25, 0)
    print(f"\nMoved entity 1 to (25, 25, 0)")
    
    results = grid.query_radius(25, 25, 5)
    print(f"Entities within 5 units of (25, 25, 0): {results}")
    
    # Remove entity
    grid.remove(4)
    print(f"\nRemoved entity 4")
    results = grid.query_radius(25, 25, 5)
    print(f"Entities within 5 units of (25, 25, 0): {results}")
    
    print(f"\nFinal stats: {grid.get_stats()}")
