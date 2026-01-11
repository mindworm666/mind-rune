"""
Mind Rune - Inventory System

Handles item management, equipment, and loot.

FEATURES:
- Inventory slots with weight limit
- Equipment slots
- Item stacking
- Item dropping/pickup
- Loot generation on death
"""

import random
from typing import Optional, List, Dict, Tuple
import logging

from backend.engine.ecs import System, World, Entity
from backend.engine.spatial import SpatialHashGrid
from backend.components.core import (
    Position, Stats, Inventory, Item, EquipSlot, Loot, Dead,
    Sprite, Identity, EntityType
)

logger = logging.getLogger(__name__)


# Item templates
ITEM_TEMPLATES: Dict[str, Dict] = {
    # Weapons
    "rusty_sword": {
        "name": "Rusty Sword",
        "description": "A worn blade with rust spots.",
        "weight": 3.0,
        "value": 10,
        "char": "/",
        "color": "#8b4513",
        "slot": EquipSlot.WEAPON,
        "stat_bonuses": {"attack_power": 5}
    },
    "iron_sword": {
        "name": "Iron Sword",
        "description": "A sturdy iron blade.",
        "weight": 4.0,
        "value": 50,
        "char": "/",
        "color": "#c0c0c0",
        "slot": EquipSlot.WEAPON,
        "stat_bonuses": {"attack_power": 10}
    },
    "wooden_staff": {
        "name": "Wooden Staff",
        "description": "A gnarled wooden staff.",
        "weight": 2.0,
        "value": 15,
        "char": "|",
        "color": "#8b4513",
        "slot": EquipSlot.WEAPON,
        "stat_bonuses": {"magic_power": 5}
    },
    
    # Armor
    "leather_armor": {
        "name": "Leather Armor",
        "description": "Basic protection from hardened leather.",
        "weight": 5.0,
        "value": 30,
        "char": "[",
        "color": "#8b4513",
        "slot": EquipSlot.CHEST,
        "stat_bonuses": {"armor": 3}
    },
    "iron_helm": {
        "name": "Iron Helm",
        "description": "A simple iron helmet.",
        "weight": 2.0,
        "value": 25,
        "char": "^",
        "color": "#c0c0c0",
        "slot": EquipSlot.HEAD,
        "stat_bonuses": {"armor": 2}
    },
    
    # Consumables
    "health_potion": {
        "name": "Health Potion",
        "description": "Restores 50 HP.",
        "weight": 0.5,
        "value": 20,
        "char": "!",
        "color": "#ff0000",
        "stackable": True,
        "max_stack": 10,
        "effect": {"heal": 50}
    },
    "mana_potion": {
        "name": "Mana Potion",
        "description": "Restores 30 MP.",
        "weight": 0.5,
        "value": 25,
        "char": "!",
        "color": "#0000ff",
        "stackable": True,
        "max_stack": 10,
        "effect": {"restore_mana": 30}
    },
    
    # Misc
    "gold_coin": {
        "name": "Gold Coin",
        "description": "Shiny gold currency.",
        "weight": 0.01,
        "value": 1,
        "char": "$",
        "color": "#ffd700",
        "stackable": True,
        "max_stack": 999
    },
    "bone": {
        "name": "Bone",
        "description": "A bleached bone.",
        "weight": 0.2,
        "value": 1,
        "char": "-",
        "color": "#f5f5dc",
        "stackable": True,
        "max_stack": 20
    },
    "goblin_ear": {
        "name": "Goblin Ear",
        "description": "A trophy from a slain goblin.",
        "weight": 0.1,
        "value": 5,
        "char": "e",
        "color": "#228b22",
        "stackable": True,
        "max_stack": 50
    },
}


class ItemFactory:
    """Creates item instances from templates"""
    
    _next_item_id = 1
    
    @classmethod
    def create_item(cls, template_id: str, count: int = 1) -> Optional[Item]:
        """Create item from template"""
        template = ITEM_TEMPLATES.get(template_id)
        if not template:
            logger.warning(f"Unknown item template: {template_id}")
            return None
        
        item = Item(
            item_id=cls._next_item_id,
            template_id=template_id,
            name=template["name"],
            description=template.get("description", ""),
            weight=template.get("weight", 1.0),
            stackable=template.get("stackable", False),
            stack_count=count if template.get("stackable", False) else 1,
            max_stack=template.get("max_stack", 1),
            value=template.get("value", 0),
            char=template.get("char", "?"),
            color=template.get("color", "white"),
            stat_bonuses=template.get("stat_bonuses", {}).copy()
        )
        
        cls._next_item_id += 1
        return item


class InventorySystem(System):
    """
    Manages entity inventories.
    Priority: 60
    """
    
    def __init__(self, spatial_index: SpatialHashGrid):
        super().__init__(priority=60)
        self.spatial_index = spatial_index
        self.ground_items: Dict[Tuple[int, int, int], List[Item]] = {}
    
    def _do_update(self, dt: float, world: World) -> None:
        # Process dead entities to drop loot
        for entity, (dead, pos) in world.query(Dead, Position):
            loot = world.get_component(entity, Loot)
            if loot and not hasattr(dead, '_loot_dropped'):
                self._drop_loot(entity, pos, loot, world)
                dead._loot_dropped = True
    
    def _drop_loot(self, entity: Entity, pos: Position, loot: Loot, world: World) -> None:
        """Drop loot from dead entity"""
        tile_key = (int(pos.x), int(pos.y), int(pos.z))
        
        if tile_key not in self.ground_items:
            self.ground_items[tile_key] = []
        
        # Drop guaranteed items
        for template_id in loot.guaranteed_items:
            item = ItemFactory.create_item(template_id)
            if item:
                self.ground_items[tile_key].append(item)
                logger.debug(f"Dropped {item.name} at {tile_key}")
        
        # Roll for possible items
        for template_id, chance in loot.possible_items.items():
            if random.random() < chance:
                item = ItemFactory.create_item(template_id)
                if item:
                    self.ground_items[tile_key].append(item)
                    logger.debug(f"Dropped {item.name} at {tile_key}")
        
        # Drop gold
        if loot.gold_max > 0:
            gold_amount = random.randint(loot.gold_min, loot.gold_max)
            if gold_amount > 0:
                gold = ItemFactory.create_item("gold_coin", gold_amount)
                if gold:
                    self.ground_items[tile_key].append(gold)
                    logger.debug(f"Dropped {gold_amount} gold at {tile_key}")
    
    def add_item_to_inventory(self, entity: Entity, item: Item, world: World) -> bool:
        """Add item to entity's inventory"""
        inv = world.get_component(entity, Inventory)
        if not inv:
            return False
        
        # Check weight
        if inv.total_weight + item.weight > inv.max_weight:
            return False
        
        # Check slots
        if len(inv.items) >= inv.max_items and not item.stackable:
            return False
        
        # Try to stack if stackable
        if item.stackable:
            for existing in inv.items:
                if existing.template_id == item.template_id:
                    space = existing.max_stack - existing.stack_count
                    if space > 0:
                        transfer = min(space, item.stack_count)
                        existing.stack_count += transfer
                        item.stack_count -= transfer
                        
                        if item.stack_count == 0:
                            inv.total_weight += item.weight * transfer
                            return True
        
        # Add as new item
        if len(inv.items) < inv.max_items:
            inv.items.append(item)
            inv.total_weight += item.weight * item.stack_count
            return True
        
        return False
    
    def remove_item_from_inventory(self, entity: Entity, item_id: int, 
                                   count: int, world: World) -> Optional[Item]:
        """Remove item from inventory"""
        inv = world.get_component(entity, Inventory)
        if not inv:
            return None
        
        for i, item in enumerate(inv.items):
            if item.item_id == item_id:
                if item.stackable and item.stack_count > count:
                    # Remove partial stack
                    item.stack_count -= count
                    inv.total_weight -= item.weight * count
                    
                    # Create new item for removed portion
                    removed = ItemFactory.create_item(item.template_id, count)
                    return removed
                else:
                    # Remove entire item
                    inv.items.pop(i)
                    inv.total_weight -= item.weight * item.stack_count
                    return item
        
        return None
    
    def drop_item(self, entity: Entity, item_id: int, count: int, world: World) -> bool:
        """Drop item from inventory to ground"""
        pos = world.get_component(entity, Position)
        if not pos:
            return False
        
        item = self.remove_item_from_inventory(entity, item_id, count, world)
        if not item:
            return False
        
        tile_key = (int(pos.x), int(pos.y), int(pos.z))
        if tile_key not in self.ground_items:
            self.ground_items[tile_key] = []
        
        self.ground_items[tile_key].append(item)
        logger.debug(f"Player dropped {item.name} at {tile_key}")
        return True
    
    def pickup_item(self, entity: Entity, world: World) -> Optional[Item]:
        """Pick up item from ground"""
        pos = world.get_component(entity, Position)
        if not pos:
            return None
        
        tile_key = (int(pos.x), int(pos.y), int(pos.z))
        items = self.ground_items.get(tile_key, [])
        
        if not items:
            return None
        
        # Try to pick up first item
        item = items[0]
        if self.add_item_to_inventory(entity, item, world):
            items.pop(0)
            if not items:
                del self.ground_items[tile_key]
            logger.debug(f"Picked up {item.name}")
            return item
        
        return None
    
    def equip_item(self, entity: Entity, item_id: int, world: World) -> bool:
        """Equip item from inventory"""
        inv = world.get_component(entity, Inventory)
        stats = world.get_component(entity, Stats)
        if not inv or not stats:
            return False
        
        # Find item
        item = None
        for i in inv.items:
            if i.item_id == item_id:
                item = i
                break
        
        if not item:
            return False
        
        # Check if equippable
        template = ITEM_TEMPLATES.get(item.template_id, {})
        slot = template.get("slot")
        if not slot:
            return False
        
        # Unequip current item in slot
        if slot in inv.equipped and inv.equipped[slot]:
            self._unequip_item(entity, slot, world)
        
        # Remove from inventory
        inv.items.remove(item)
        
        # Equip
        inv.equipped[slot] = item
        
        # Apply bonuses
        for stat, bonus in item.stat_bonuses.items():
            current = getattr(stats, stat, 0)
            setattr(stats, stat, current + bonus)
        
        logger.debug(f"Equipped {item.name} to {slot.value}")
        return True
    
    def _unequip_item(self, entity: Entity, slot: EquipSlot, world: World) -> bool:
        """Unequip item to inventory"""
        inv = world.get_component(entity, Inventory)
        stats = world.get_component(entity, Stats)
        if not inv or not stats:
            return False
        
        item = inv.equipped.get(slot)
        if not item:
            return False
        
        # Check inventory space
        if len(inv.items) >= inv.max_items:
            return False
        
        # Remove bonuses
        for stat, bonus in item.stat_bonuses.items():
            current = getattr(stats, stat, 0)
            setattr(stats, stat, current - bonus)
        
        # Move to inventory
        inv.equipped[slot] = None
        inv.items.append(item)
        
        logger.debug(f"Unequipped {item.name} from {slot.value}")
        return True
    
    def get_items_at(self, x: int, y: int, z: int) -> List[Item]:
        """Get items at position"""
        return self.ground_items.get((x, y, z), [])
    
    def get_ground_items_in_radius(self, x: float, y: float, z: float, 
                                   radius: float) -> Dict[Tuple[int, int, int], List[Item]]:
        """Get all ground items within radius"""
        result = {}
        for pos, items in self.ground_items.items():
            dx = pos[0] - x
            dy = pos[1] - y
            dz = pos[2] - z
            if dx*dx + dy*dy + dz*dz <= radius*radius:
                result[pos] = items
        return result


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    from backend.engine.ecs import World
    from backend.engine.spatial import SpatialHashGrid
    
    print("=== Inventory System Test ===")
    
    world = World(debug=True)
    spatial = SpatialHashGrid(cell_size=16.0)
    
    # Register components
    world.register_component(Position)
    world.register_component(Stats)
    world.register_component(Inventory, dependencies=[Stats])
    
    # Create player with inventory
    player = world.create_entity()
    world.add_component(player, Position, Position(x=5, y=5, z=0))
    world.add_component(player, Stats, Stats())
    world.add_component(player, Inventory, Inventory())
    
    # Create inventory system
    inv_system = InventorySystem(spatial)
    
    # Create some items
    sword = ItemFactory.create_item("iron_sword")
    potion = ItemFactory.create_item("health_potion", 5)
    
    print(f"\nCreated: {sword.name} (id: {sword.item_id})")
    print(f"Created: {potion.name} x{potion.stack_count} (id: {potion.item_id})")
    
    # Add to inventory
    inv_system.add_item_to_inventory(player, sword, world)
    inv_system.add_item_to_inventory(player, potion, world)
    
    inv = world.get_component(player, Inventory)
    print(f"\nInventory: {len(inv.items)} items, {inv.total_weight:.1f} weight")
    for item in inv.items:
        print(f"  - {item.name} x{item.stack_count}")
    
    # Equip sword
    print("\nEquipping sword...")
    inv_system.equip_item(player, sword.item_id, world)
    
    stats = world.get_component(player, Stats)
    print(f"Attack power after equip: {stats.attack_power}")
    print(f"Equipped items: {[s.value for s in inv.equipped if inv.equipped.get(s)]}")
