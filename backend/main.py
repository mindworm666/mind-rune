"""
Mind Rune - Main Server Entry Point

Starts the game server with all systems.

USAGE:
    python -m backend.main
    python backend/main.py
"""

import asyncio
import logging
import signal
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.engine.ecs import World
from backend.engine.game_loop import GameLoop
from backend.engine.spatial import SpatialHashGrid
from backend.server.game_server import GameServer
from backend.world.starter_world import create_starter_world
from backend.systems.core_systems import (
    CooldownSystem, MovementSystem, CombatSystem, 
    StatusEffectSystem, LifetimeSystem
)
from backend.systems.ai_system import AISystem
from backend.systems.inventory_system import InventorySystem
from backend.systems.visibility_system import VisibilitySystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MindRuneServer:
    """Main game server orchestrator"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765, tps: int = 20):
        self.host = host
        self.port = port
        self.tps = tps
        
        # Core components
        self.game_loop: GameLoop = None
        self.ecs_world: World = None
        self.world_3d = None
        self.spatial_index: SpatialHashGrid = None
        self.server: GameServer = None
        
        # Systems
        self.systems = {}
        
        # State
        self.running = False
    
    def setup(self) -> None:
        """Initialize all game components"""
        logger.info("Setting up Mind Rune server...")
        
        # Create game loop with ECS world
        self.game_loop = GameLoop(tps=self.tps)
        self.ecs_world = self.game_loop.get_world()
        
        # Generate starter world
        logger.info("Generating starter world...")
        self.world_3d, self.spatial_index = create_starter_world(self.ecs_world, seed=12345)
        
        # Initialize systems
        logger.info("Initializing game systems...")
        self._setup_systems()
        
        # Create network server
        self.server = GameServer(host=self.host, port=self.port)
        
        logger.info("Server setup complete!")
    
    def _setup_systems(self) -> None:
        """Initialize and register all game systems"""
        scheduler = self.game_loop.get_scheduler()
        
        # Create systems
        self.systems['cooldown'] = CooldownSystem()
        self.systems['movement'] = MovementSystem(self.spatial_index)
        self.systems['combat'] = CombatSystem(self.systems['cooldown'])
        self.systems['status_effect'] = StatusEffectSystem()
        self.systems['lifetime'] = LifetimeSystem()
        self.systems['ai'] = AISystem(self.spatial_index)
        self.systems['inventory'] = InventorySystem(self.spatial_index)
        self.systems['visibility'] = VisibilitySystem(self.world_3d)
        
        # Register with scheduler (in priority order)
        scheduler.add_system("cooldown", self.systems['cooldown'])
        scheduler.add_system("movement", self.systems['movement'])
        scheduler.add_system("ai", self.systems['ai'])
        scheduler.add_system("combat", self.systems['combat'])
        scheduler.add_system("status_effect", self.systems['status_effect'])
        scheduler.add_system("inventory", self.systems['inventory'])
        scheduler.add_system("visibility", self.systems['visibility'])
        scheduler.add_system("lifetime", self.systems['lifetime'])
        
        logger.info(f"Registered {len(self.systems)} systems")
    
    async def start(self) -> None:
        """Start the server"""
        self.setup()
        self.running = True
        
        # Start WebSocket server
        await self.server.start(self.game_loop, self.world_3d)
        
        # Update server's spatial index reference
        self.server.spatial_index = self.spatial_index
        
        logger.info(f"Mind Rune server starting on ws://{self.host}:{self.port}")
        logger.info("Press Ctrl+C to stop")
        
        # Start game loop in background
        game_loop_task = asyncio.create_task(self.game_loop.start_async())
        
        try:
            # Keep server running
            while self.running:
                await asyncio.sleep(1)
                
                # Log stats periodically
                if self.game_loop.current_tick % 200 == 0:  # Every 10 seconds
                    self._log_stats()
                    
        except asyncio.CancelledError:
            logger.info("Server cancelled")
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop the server"""
        logger.info("Stopping server...")
        self.running = False
        
        # Stop game loop
        if self.game_loop:
            self.game_loop.stop()
        
        # Stop WebSocket server
        if self.server:
            await self.server.stop()
        
        logger.info("Server stopped")
    
    def _log_stats(self) -> None:
        """Log server statistics"""
        game_stats = self.game_loop.get_performance_report()
        server_stats = self.server.get_stats()
        
        logger.info(
            f"Stats - Tick: {self.game_loop.current_tick}, "
            f"TPS: {game_stats['avg_tps']:.1f}, "
            f"Entities: {self.ecs_world.get_entity_count()}, "
            f"Players: {server_stats['players_in_game']}"
        )


async def main():
    """Main entry point"""
    server = MindRuneServer(
        host="0.0.0.0",
        port=8765,
        tps=20
    )
    
    # Handle shutdown signals (Unix only - Windows uses KeyboardInterrupt)
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(server.stop())
    
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
    except NotImplementedError:
        # Windows doesn't support add_signal_handler
        pass
    
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server crashed: {e}", exc_info=True)
        sys.exit(1)
