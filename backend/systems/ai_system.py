"""
Mind Rune - AI System

NPC decision making and behavior.
Uses state machines for different AI behaviors.

AI STATES:
- IDLE: Standing still, occasionally looking around
- WANDERING: Moving randomly within spawn area  
- CHASING: Pursuing a target
- ATTACKING: In melee range, attacking target
- FLEEING: Running away from threat
- RETURNING: Going back to spawn point

BEHAVIOR TYPES:
- Passive: Never attacks (wildlife)
- Defensive: Only attacks if attacked first
- Aggressive: Attacks players on sight
- Territorial: Attacks if player enters area
"""

import math
import random
from typing import Optional, Tuple, List, Dict, Set
import logging

from backend.engine.ecs import System, World, Entity
from backend.engine.spatial import SpatialHashGrid
from backend.components.core import (
    Position, Velocity, Stats, CombatState, AI, AIState, Faction,
    Player, Dead, Identity
)

logger = logging.getLogger(__name__)


class AISystem(System):
    """
    Processes AI decisions for all NPCs.
    Priority: 70 (after cooldowns, before combat)
    """
    
    def __init__(self, spatial_index: SpatialHashGrid):
        super().__init__(priority=70)
        self.spatial_index = spatial_index
        self.current_time = 0.0
    
    def _do_update(self, dt: float, world: World) -> None:
        self.current_time += dt
        
        for entity, (ai, pos, stats, combat) in world.query(AI, Position, Stats, CombatState):
            # Skip dead entities
            if world.get_component(entity, Dead):
                continue
            
            # Update state timer
            ai.state_time += dt
            
            # Only make decisions at decision interval
            if self.current_time - ai.last_decision_time < ai.decision_interval:
                continue
            
            ai.last_decision_time = self.current_time
            
            # Process AI based on current state
            self._process_ai_state(entity, ai, pos, stats, combat, world)
    
    def _process_ai_state(self, entity: Entity, ai: AI, pos: Position,
                          stats: Stats, combat: CombatState, world: World) -> None:
        """Process AI state machine"""
        
        if ai.state == AIState.IDLE:
            self._process_idle(entity, ai, pos, stats, combat, world)
        
        elif ai.state == AIState.WANDERING:
            self._process_wandering(entity, ai, pos, stats, combat, world)
        
        elif ai.state == AIState.CHASING:
            self._process_chasing(entity, ai, pos, stats, combat, world)
        
        elif ai.state == AIState.ATTACKING:
            self._process_attacking(entity, ai, pos, stats, combat, world)
        
        elif ai.state == AIState.FLEEING:
            self._process_fleeing(entity, ai, pos, stats, combat, world)
        
        elif ai.state == AIState.RETURNING:
            self._process_returning(entity, ai, pos, stats, combat, world)
    
    def _process_idle(self, entity: Entity, ai: AI, pos: Position,
                      stats: Stats, combat: CombatState, world: World) -> None:
        """Process IDLE state"""
        # Check for nearby threats
        target = self._find_target(entity, ai, pos, world)
        
        if target:
            ai.current_target = target
            self._change_state(ai, AIState.CHASING)
            return
        
        # Random chance to start wandering
        if ai.state_time > 3.0 and random.random() < 0.3:
            self._change_state(ai, AIState.WANDERING)
    
    def _process_wandering(self, entity: Entity, ai: AI, pos: Position,
                           stats: Stats, combat: CombatState, world: World) -> None:
        """Process WANDERING state"""
        # Check for nearby threats
        target = self._find_target(entity, ai, pos, world)
        
        if target:
            ai.current_target = target
            self._change_state(ai, AIState.CHASING)
            return
        
        # Check if too far from spawn
        dist_from_spawn = self._distance(pos.x, pos.y, pos.z,
                                         ai.spawn_x, ai.spawn_y, ai.spawn_z)
        
        if dist_from_spawn > ai.chase_radius:
            self._change_state(ai, AIState.RETURNING)
            return
        
        # Random movement
        vel = world.get_component(entity, Velocity)
        if vel:
            if ai.state_time > 2.0 or (vel.dx == 0 and vel.dy == 0):
                # Pick new random direction
                angle = random.random() * 2 * math.pi
                speed = stats.move_speed * 0.5  # Half speed when wandering
                vel.dx = math.cos(angle) * speed
                vel.dy = math.sin(angle) * speed
                ai.state_time = 0.0
        
        # Random chance to return to idle
        if ai.state_time > 5.0 and random.random() < 0.2:
            self._stop_movement(entity, world)
            self._change_state(ai, AIState.IDLE)
    
    def _process_chasing(self, entity: Entity, ai: AI, pos: Position,
                         stats: Stats, combat: CombatState, world: World) -> None:
        """Process CHASING state"""
        # Validate target
        if not self._is_valid_target(ai.current_target, world):
            ai.current_target = None
            self._stop_movement(entity, world)
            self._change_state(ai, AIState.RETURNING)
            return
        
        target_pos = world.get_component(ai.current_target, Position)
        if not target_pos:
            ai.current_target = None
            self._change_state(ai, AIState.RETURNING)
            return
        
        # Update last seen position
        ai.last_seen_target_x = target_pos.x
        ai.last_seen_target_y = target_pos.y
        ai.last_seen_target_z = target_pos.z
        
        # Calculate distance to target
        dist = self._distance(pos.x, pos.y, pos.z,
                              target_pos.x, target_pos.y, target_pos.z)
        
        # Check if in attack range
        if dist <= ai.attack_range:
            self._stop_movement(entity, world)
            self._change_state(ai, AIState.ATTACKING)
            combat.target = ai.current_target
            return
        
        # Check if target out of chase range
        dist_from_spawn = self._distance(pos.x, pos.y, pos.z,
                                         ai.spawn_x, ai.spawn_y, ai.spawn_z)
        
        if dist_from_spawn > ai.chase_radius:
            ai.current_target = None
            self._stop_movement(entity, world)
            self._change_state(ai, AIState.RETURNING)
            return
        
        # Move toward target
        self._move_toward(entity, pos, target_pos.x, target_pos.y, target_pos.z,
                          stats.move_speed, world)
    
    def _process_attacking(self, entity: Entity, ai: AI, pos: Position,
                           stats: Stats, combat: CombatState, world: World) -> None:
        """Process ATTACKING state"""
        # Validate target
        if not self._is_valid_target(ai.current_target, world):
            ai.current_target = None
            combat.target = None
            self._change_state(ai, AIState.IDLE)
            return
        
        target_pos = world.get_component(ai.current_target, Position)
        if not target_pos:
            ai.current_target = None
            combat.target = None
            self._change_state(ai, AIState.IDLE)
            return
        
        # Check distance
        dist = self._distance(pos.x, pos.y, pos.z,
                              target_pos.x, target_pos.y, target_pos.z)
        
        # If target moved out of range, chase
        if dist > ai.attack_range:
            self._change_state(ai, AIState.CHASING)
            return
        
        # Combat system handles actual attacks
        combat.target = ai.current_target
        combat.in_combat = True
    
    def _process_fleeing(self, entity: Entity, ai: AI, pos: Position,
                         stats: Stats, combat: CombatState, world: World) -> None:
        """Process FLEEING state"""
        # Move away from threat
        if ai.current_target and world.is_alive(ai.current_target):
            target_pos = world.get_component(ai.current_target, Position)
            if target_pos:
                # Move in opposite direction
                dx = pos.x - target_pos.x
                dy = pos.y - target_pos.y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist > 0:
                    vel = world.get_component(entity, Velocity)
                    if vel:
                        vel.dx = (dx / dist) * stats.move_speed
                        vel.dy = (dy / dist) * stats.move_speed
        
        # Check if safe (far enough)
        if ai.current_target:
            target_pos = world.get_component(ai.current_target, Position)
            if target_pos:
                dist = self._distance(pos.x, pos.y, pos.z,
                                      target_pos.x, target_pos.y, target_pos.z)
                if dist > ai.chase_radius:
                    ai.current_target = None
                    self._stop_movement(entity, world)
                    self._change_state(ai, AIState.RETURNING)
    
    def _process_returning(self, entity: Entity, ai: AI, pos: Position,
                           stats: Stats, combat: CombatState, world: World) -> None:
        """Process RETURNING state"""
        # Move toward spawn point
        dist = self._distance(pos.x, pos.y, pos.z,
                              ai.spawn_x, ai.spawn_y, ai.spawn_z)
        
        if dist <= 2.0:
            self._stop_movement(entity, world)
            self._change_state(ai, AIState.IDLE)
            return
        
        self._move_toward(entity, pos, ai.spawn_x, ai.spawn_y, ai.spawn_z,
                          stats.move_speed * 0.7, world)
    
    # ========================================================================
    # HELPERS
    # ========================================================================
    
    def _find_target(self, entity: Entity, ai: AI, pos: Position, 
                     world: World) -> Optional[Entity]:
        """Find a valid target based on faction"""
        if ai.faction not in {Faction.HOSTILE, Faction.NEUTRAL}:
            return None
        
        # Query nearby entities
        nearby = self.spatial_index.query_radius(pos.x, pos.y, pos.z, ai.aggro_radius)
        
        best_target = None
        best_dist = float('inf')
        
        for other in nearby:
            if other == entity:
                continue
            
            # Skip dead entities
            if world.get_component(other, Dead):
                continue
            
            # Check if valid target based on faction
            other_ai = world.get_component(other, AI)
            is_player = world.get_component(other, Player) is not None
            
            # Hostile NPCs attack players
            if ai.faction == Faction.HOSTILE and is_player:
                other_pos = world.get_component(other, Position)
                if other_pos:
                    dist = self._distance(pos.x, pos.y, pos.z,
                                          other_pos.x, other_pos.y, other_pos.z)
                    if dist < best_dist:
                        best_dist = dist
                        best_target = other
            
            # Neutral NPCs attack if attacked (check threat table)
            elif ai.faction == Faction.NEUTRAL:
                combat = world.get_component(entity, CombatState)
                if combat and other in combat.threat_table:
                    other_pos = world.get_component(other, Position)
                    if other_pos:
                        dist = self._distance(pos.x, pos.y, pos.z,
                                              other_pos.x, other_pos.y, other_pos.z)
                        if dist < best_dist:
                            best_dist = dist
                            best_target = other
        
        return best_target
    
    def _is_valid_target(self, target: Optional[Entity], world: World) -> bool:
        """Check if target is still valid"""
        if target is None:
            return False
        
        if not world.is_alive(target):
            return False
        
        if world.get_component(target, Dead):
            return False
        
        return True
    
    def _change_state(self, ai: AI, new_state: AIState) -> None:
        """Change AI state"""
        if ai.state != new_state:
            ai.state = new_state
            ai.state_time = 0.0
    
    def _move_toward(self, entity: Entity, pos: Position, 
                     target_x: float, target_y: float, target_z: float,
                     speed: float, world: World) -> None:
        """Set velocity toward target"""
        vel = world.get_component(entity, Velocity)
        if not vel:
            return
        
        dx = target_x - pos.x
        dy = target_y - pos.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0:
            vel.dx = (dx / dist) * speed
            vel.dy = (dy / dist) * speed
    
    def _stop_movement(self, entity: Entity, world: World) -> None:
        """Stop entity movement"""
        vel = world.get_component(entity, Velocity)
        if vel:
            vel.dx = 0
            vel.dy = 0
            vel.dz = 0
    
    @staticmethod
    def _distance(x1: float, y1: float, z1: float, 
                  x2: float, y2: float, z2: float) -> float:
        """Calculate 3D distance"""
        return math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    from backend.engine.ecs import World
    from backend.engine.spatial import SpatialHashGrid
    
    print("=== AI System Test ===")
    
    world = World(debug=True)
    spatial = SpatialHashGrid(cell_size=16.0)
    
    # Register components
    world.register_component(Position)
    world.register_component(Velocity)
    world.register_component(Stats)
    world.register_component(CombatState, dependencies=[Stats])
    world.register_component(AI)
    world.register_component(Player)
    world.register_component(Identity)
    
    # Create player
    player = world.create_entity()
    world.add_component(player, Position, Position(x=5, y=5, z=0))
    world.add_component(player, Stats, Stats())
    world.add_component(player, CombatState, CombatState(hp=100, mp=50))
    world.add_component(player, Player, Player(account_id=1, character_name="Hero"))
    world.add_component(player, Identity, Identity(EntityType.PLAYER, "Hero"))
    spatial.insert(player, 5, 5, 0)
    
    # Create hostile NPC
    npc = world.create_entity()
    world.add_component(npc, Position, Position(x=10, y=10, z=0))
    world.add_component(npc, Velocity, Velocity())
    world.add_component(npc, Stats, Stats(move_speed=3.0))
    world.add_component(npc, CombatState, CombatState(hp=50, mp=0))
    world.add_component(npc, AI, AI(
        state=AIState.IDLE,
        faction=Faction.HOSTILE,
        aggro_radius=15.0,
        spawn_x=10, spawn_y=10, spawn_z=0
    ))
    world.add_component(npc, Identity, Identity(EntityType.NPC, "Goblin"))
    spatial.insert(npc, 10, 10, 0)
    
    # Create AI system
    ai_system = AISystem(spatial)
    
    # Run a few updates
    for i in range(10):
        print(f"\nTick {i}:")
        ai_system.update(0.5, world)  # 500ms per tick for testing
        
        ai = world.get_component(npc, AI)
        pos = world.get_component(npc, Position)
        vel = world.get_component(npc, Velocity)
        
        print(f"  NPC State: {ai.state.value}")
        print(f"  NPC Position: ({pos.x:.1f}, {pos.y:.1f})")
        print(f"  NPC Velocity: ({vel.dx:.1f}, {vel.dy:.1f})")
        print(f"  NPC Target: {ai.current_target}")
