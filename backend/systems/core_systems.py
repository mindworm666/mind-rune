"""
Mind Rune - Core Game Systems

Systems implement game logic by operating on components.
All systems are stateless - state lives in components.
"""

import time
import math
from typing import Set, Optional, Dict, List
import logging

from backend.engine.ecs import System, World, Entity
from backend.engine.spatial import SpatialHashGrid
from backend.components.core import (
    Position, Velocity, Stats, CombatState, Cooldowns, Cooldown,
    AI, AIState, Faction, StatusEffects, StatusEffect, StatusType,
    Dead, Lifetime, Player
)

logger = logging.getLogger(__name__)


# ============================================================================
# COOLDOWN SYSTEM
# ============================================================================

class CooldownSystem(System):
    """
    Ticks down all cooldowns.
    Priority: 100 (runs first)
    """
    
    def __init__(self):
        super().__init__(priority=100)
        self.current_time = 0.0
    
    def _do_update(self, dt: float, world: World) -> None:
        self.current_time += dt
        
        for entity, (cooldowns,) in world.query(Cooldowns):
            # Tick GCD
            if cooldowns.gcd_expires_at > 0 and cooldowns.gcd_expires_at <= self.current_time:
                cooldowns.gcd_expires_at = 0.0
            
            # Tick individual cooldowns
            expired = []
            for action_name, cooldown in cooldowns.active.items():
                if cooldown.expires_at <= self.current_time:
                    expired.append(action_name)
            
            # Remove expired cooldowns
            for action_name in expired:
                del cooldowns.active[action_name]
    
    def can_act(self, entity: Entity, action_name: str, world: World) -> bool:
        """Check if entity can perform action"""
        cooldowns = world.get_component(entity, Cooldowns)
        if cooldowns is None:
            return True
        
        # Check GCD
        if cooldowns.gcd_expires_at > self.current_time:
            return False
        
        # Check specific cooldown
        if action_name in cooldowns.active:
            cd = cooldowns.active[action_name]
            if cd.expires_at > self.current_time:
                return False
        
        return True
    
    def trigger_cooldown(self, entity: Entity, action_name: str, duration: float,
                        world: World, gcd: float = 0.5) -> None:
        """Trigger a cooldown"""
        cooldowns = world.get_component(entity, Cooldowns)
        if cooldowns is None:
            return
        
        # Set action cooldown
        cooldowns.active[action_name] = Cooldown(
            action_name=action_name,
            expires_at=self.current_time + duration,
            duration=duration
        )
        
        # Set GCD
        cooldowns.gcd_expires_at = self.current_time + gcd


# ============================================================================
# MOVEMENT SYSTEM
# ============================================================================

class MovementSystem(System):
    """
    Handles entity movement and collision.
    Priority: 90
    
    INVARIANTS:
    - Position component matches spatial index
    - Entities don't overlap (if both solid)
    - Entities stay within world bounds
    """
    
    def __init__(self, spatial_index: SpatialHashGrid, world_bounds: tuple = (-1000, 1000)):
        super().__init__(priority=90)
        self.spatial_index = spatial_index
        self.min_coord, self.max_coord = world_bounds
    
    def _do_update(self, dt: float, world: World) -> None:
        # Apply velocity to position
        for entity, (pos, vel) in world.query(Position, Velocity):
            new_x = pos.x + vel.dx * dt
            new_y = pos.y + vel.dy * dt
            new_z = pos.z + vel.dz * dt
            
            # Clamp to world bounds
            new_x = max(self.min_coord, min(self.max_coord, new_x))
            new_y = max(self.min_coord, min(self.max_coord, new_y))
            new_z = max(0, min(100, new_z))  # Z is always positive
            
            # Check collision (simplified - actual game needs proper collision)
            # TODO: Check world terrain collision
            # TODO: Check entity collision with spatial index
            
            # Update position
            pos.x = new_x
            pos.y = new_y
            pos.z = new_z
            
            # Update spatial index
            self.spatial_index.update(entity, new_x, new_y, new_z)
    
    def can_move_to(self, entity: Entity, x: float, y: float, z: float, world: World) -> bool:
        """Check if entity can move to position"""
        # Bounds check
        if not (self.min_coord <= x <= self.max_coord and
                self.min_coord <= y <= self.max_coord and
                0 <= z <= 100):
            return False
        
        # TODO: Check world terrain
        # TODO: Check entity collision
        
        return True
    
    def teleport(self, entity: Entity, x: float, y: float, z: float, world: World) -> bool:
        """Instantly move entity to position"""
        if not self.can_move_to(entity, x, y, z, world):
            return False
        
        pos = world.get_component(entity, Position)
        if pos is None:
            return False
        
        pos.x = x
        pos.y = y
        pos.z = z
        
        self.spatial_index.update(entity, x, y, z)
        return True


# ============================================================================
# COMBAT SYSTEM
# ============================================================================

class CombatSystem(System):
    """
    Handles combat, damage, death.
    Priority: 80
    """
    
    def __init__(self, cooldown_system: CooldownSystem):
        super().__init__(priority=80)
        self.cooldown_system = cooldown_system
        self.current_time = 0.0
    
    def _do_update(self, dt: float, world: World) -> None:
        self.current_time += dt
        
        # Process auto-attacks
        for entity, (combat, stats) in world.query(CombatState, Stats):
            if combat.target is None:
                continue
            
            # Check if target is valid
            if not world.is_alive(combat.target):
                combat.target = None
                continue
            
            # Check cooldown
            if not self.cooldown_system.can_act(entity, "attack", world):
                continue
            
            # Check range
            pos = world.get_component(entity, Position)
            target_pos = world.get_component(combat.target, Position)
            if pos is None or target_pos is None:
                continue
            
            distance = math.sqrt(
                (pos.x - target_pos.x)**2 +
                (pos.y - target_pos.y)**2 +
                (pos.z - target_pos.z)**2
            )
            
            # Attack range check (melee = 1.5 units)
            if distance > 1.5:
                continue
            
            # Execute attack
            damage = stats.attack_power
            self.apply_damage(combat.target, entity, damage, world)
            
            # Trigger attack cooldown
            attack_speed = stats.attack_speed
            cooldown = 1.0 / attack_speed  # e.g., 1.0 / 1.5 = 0.67s
            self.cooldown_system.trigger_cooldown(entity, "attack", cooldown, world)
            
            combat.in_combat = True
            combat.last_combat_time = self.current_time
    
    def apply_damage(self, target: Entity, source: Optional[Entity], 
                    amount: int, world: World) -> None:
        """Apply damage to target"""
        combat = world.get_component(target, CombatState)
        stats = world.get_component(target, Stats)
        
        if combat is None or stats is None:
            return
        
        # Calculate actual damage (armor reduction)
        actual_damage = max(1, amount - stats.armor)
        
        # Apply damage
        combat.hp = max(0, combat.hp - actual_damage)
        
        # Update threat table (for AI)
        if source is not None and source != target:
            if source not in combat.threat_table:
                combat.threat_table[source] = 0.0
            combat.threat_table[source] += actual_damage
            
            combat.targeted_by.add(source)
        
        # Check death
        if combat.hp == 0:
            self.handle_death(target, source, world)
        
        logger.debug(f"Entity {source} dealt {actual_damage} damage to {target} (HP: {combat.hp}/{stats.max_hp})")
    
    def handle_death(self, entity: Entity, killer: Optional[Entity], world: World) -> None:
        """Handle entity death"""
        # Add death marker
        world.add_component(entity, Dead, Dead(
            time_of_death=self.current_time,
            killer=killer
        ))
        
        # Award XP to killer
        if killer is not None:
            self.award_experience(killer, entity, world)
        
        # TODO: Drop loot
        # TODO: Play death animation
        # TODO: Handle respawn for players
        
        logger.info(f"Entity {entity} died (killed by {killer})")
    
    def award_experience(self, recipient: Entity, victim: Entity, world: World) -> None:
        """Award experience to recipient for killing victim"""
        recipient_stats = world.get_component(recipient, Stats)
        victim_stats = world.get_component(victim, Stats)
        
        if recipient_stats is None or victim_stats is None:
            return
        
        # Base XP = victim level * 10
        xp = victim_stats.level * 10
        
        recipient_stats.experience += xp
        
        # Check level up
        while recipient_stats.experience >= recipient_stats.experience_to_next:
            recipient_stats.experience -= recipient_stats.experience_to_next
            recipient_stats.level += 1
            recipient_stats.experience_to_next = int(recipient_stats.experience_to_next * 1.5)
            
            # Grant stat increases
            self.level_up(recipient, world)
            
            logger.info(f"Entity {recipient} leveled up to {recipient_stats.level}!")
    
    def level_up(self, entity: Entity, world: World) -> None:
        """Apply level up bonuses"""
        stats = world.get_component(entity, Stats)
        combat = world.get_component(entity, CombatState)
        
        if stats is None:
            return
        
        # Increase base stats
        stats.strength += 2
        stats.constitution += 2
        stats.dexterity += 1
        
        # Recalculate derived stats
        stats.max_hp = 100 + (stats.constitution * 10) + (stats.level * 5)
        stats.max_mp = 50 + (stats.intelligence * 5) + (stats.level * 3)
        stats.attack_power = 10 + (stats.strength * 2)
        stats.armor = stats.constitution // 2
        
        # Heal to full
        if combat is not None:
            combat.hp = stats.max_hp
            combat.mp = stats.max_mp


# ============================================================================
# STATUS EFFECT SYSTEM
# ============================================================================

class StatusEffectSystem(System):
    """
    Manages status effects (buffs/debuffs).
    Priority: 85
    """
    
    def __init__(self):
        super().__init__(priority=85)
    
    def _do_update(self, dt: float, world: World) -> None:
        for entity, (effects,) in world.query(StatusEffects):
            # Tick down durations
            expired = []
            for i, effect in enumerate(effects.active):
                effect.duration -= dt
                if effect.duration <= 0:
                    expired.append(i)
            
            # Remove expired effects (reverse order to maintain indices)
            for i in reversed(expired):
                removed = effects.active.pop(i)
                self._on_effect_removed(entity, removed, world)
    
    def _on_effect_removed(self, entity: Entity, effect: StatusEffect, world: World) -> None:
        """Handle effect removal"""
        # Clean up any effect-specific state
        pass


# ============================================================================
# LIFETIME SYSTEM
# ============================================================================

class LifetimeSystem(System):
    """
    Destroys entities after lifetime expires.
    Priority: 10 (runs late)
    """
    
    def __init__(self):
        super().__init__(priority=10)
        self.current_time = 0.0
    
    def _do_update(self, dt: float, world: World) -> None:
        self.current_time += dt
        
        to_destroy = []
        
        for entity, (lifetime,) in world.query(Lifetime):
            if lifetime.is_expired(self.current_time):
                to_destroy.append(entity)
        
        # Destroy expired entities
        for entity in to_destroy:
            world.destroy_entity(entity)
            logger.debug(f"Destroyed entity {entity} (lifetime expired)")


# ============================================================================
# PLAYER PERSISTENCE SYSTEM
# ============================================================================

class PlayerPersistenceSystem(System):
    """
    Auto-saves player data periodically.
    Priority: 5 (runs last)
    """
    
    def __init__(self):
        super().__init__(priority=5)
        self.current_time = 0.0
    
    def _do_update(self, dt: float, world: World) -> None:
        self.current_time += dt
        
        for entity, (player, pos, stats, combat) in world.query(
            Player, Position, Stats, CombatState
        ):
            # Check if save is needed
            if self.current_time - player.last_save_time >= player.save_interval:
                self.save_player(entity, player, pos, stats, combat)
                player.last_save_time = self.current_time
    
    def save_player(self, entity: Entity, player: Player, pos: Position,
                   stats: Stats, combat: CombatState) -> None:
        """Save player to database"""
        # TODO: Implement database save
        logger.debug(f"Saved player {player.character_name} (entity {entity})")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    from backend.engine.spatial import SpatialHashGrid
    
    # Create world and systems
    world = World(debug=True)
    spatial_index = SpatialHashGrid(cell_size=10.0)
    
    # Register components
    world.register_component(Position)
    world.register_component(Velocity)
    world.register_component(Stats)
    world.register_component(CombatState, dependencies=[Stats])
    world.register_component(Cooldowns)
    
    # Create systems
    cooldown_sys = CooldownSystem()
    movement_sys = MovementSystem(spatial_index)
    combat_sys = CombatSystem(cooldown_sys)
    
    # Create test entities
    player = world.create_entity()
    world.add_component(player, Position, Position(0, 0, 0))
    world.add_component(player, Velocity, Velocity(1, 0, 0))
    world.add_component(player, Stats, Stats(strength=20, level=5))
    world.add_component(player, CombatState, CombatState(hp=100, mp=50))
    world.add_component(player, Cooldowns, Cooldowns())
    
    enemy = world.create_entity()
    world.add_component(enemy, Position, Position(2, 0, 0))
    world.add_component(enemy, Stats, Stats(strength=15, level=3))
    world.add_component(enemy, CombatState, CombatState(hp=80, mp=0))
    world.add_component(enemy, Cooldowns, Cooldowns())
    
    spatial_index.insert(player, 0, 0, 0)
    spatial_index.insert(enemy, 2, 0, 0)
    
    # Set combat target
    player_combat = world.get_component(player, CombatState)
    player_combat.target = enemy
    
    print("\n=== Running Systems ===\n")
    
    # Run a few ticks
    for i in range(10):
        print(f"Tick {i}")
        cooldown_sys.update(0.05, world)
        movement_sys.update(0.05, world)
        combat_sys.update(0.05, world)
        
        player_pos = world.get_component(player, Position)
        enemy_combat = world.get_component(enemy, CombatState)
        
        if enemy_combat:
            print(f"  Player at ({player_pos.x:.2f}, {player_pos.y:.2f})")
            print(f"  Enemy HP: {enemy_combat.hp}")
        else:
            print(f"  Enemy is dead!")
            break
        
        time.sleep(0.1)
