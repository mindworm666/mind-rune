"""
Mind Rune - Game Loop

Fixed-timestep game loop running at 20 TPS (ticks per second).
Manages system execution and timing.

ARCHITECTURE:
- Server tick rate: 20 TPS (50ms per tick)
- Systems run in priority order
- Client interpolates between ticks for smooth visuals
- Actions are queued and processed each tick
"""

import time
import asyncio
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

from backend.engine.ecs import World, SystemScheduler

logger = logging.getLogger(__name__)


class GameLoopState(Enum):
    """Game loop lifecycle states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


@dataclass
class TickStats:
    """Statistics for a single tick"""
    tick_number: int
    start_time: float
    end_time: float
    target_duration: float
    actual_duration: float
    system_times: Dict[str, float] = field(default_factory=dict)
    entity_count: int = 0
    
    @property
    def overran(self) -> bool:
        """Did this tick take longer than target?"""
        return self.actual_duration > self.target_duration
    
    @property
    def efficiency(self) -> float:
        """What % of tick budget was used?"""
        return (self.actual_duration / self.target_duration) * 100.0


@dataclass
class PerformanceMonitor:
    """Tracks game loop performance"""
    target_tps: int = 20
    max_history: int = 100
    
    tick_history: List[TickStats] = field(default_factory=list)
    total_ticks: int = 0
    overrun_count: int = 0
    
    def record_tick(self, stats: TickStats) -> None:
        """Record tick statistics"""
        self.tick_history.append(stats)
        if len(self.tick_history) > self.max_history:
            self.tick_history.pop(0)
        
        self.total_ticks += 1
        if stats.overran:
            self.overrun_count += 1
    
    def get_avg_tick_time(self) -> float:
        """Get average tick duration in ms"""
        if not self.tick_history:
            return 0.0
        return sum(t.actual_duration for t in self.tick_history) / len(self.tick_history) * 1000
    
    def get_avg_fps(self) -> float:
        """Get average effective TPS"""
        if not self.tick_history:
            return 0.0
        avg_duration = sum(t.actual_duration for t in self.tick_history) / len(self.tick_history)
        if avg_duration == 0:
            return 0.0
        return 1.0 / avg_duration
    
    def get_overrun_rate(self) -> float:
        """Get % of ticks that overran"""
        if self.total_ticks == 0:
            return 0.0
        return (self.overrun_count / self.total_ticks) * 100.0
    
    def get_system_avg_times(self) -> Dict[str, float]:
        """Get average time per system in ms"""
        if not self.tick_history:
            return {}
        
        system_totals: Dict[str, float] = {}
        system_counts: Dict[str, int] = {}
        
        for tick in self.tick_history:
            for system_name, duration in tick.system_times.items():
                system_totals[system_name] = system_totals.get(system_name, 0) + duration
                system_counts[system_name] = system_counts.get(system_name, 0) + 1
        
        return {
            name: (system_totals[name] / system_counts[name]) * 1000
            for name in system_totals
        }
    
    def get_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        return {
            "target_tps": self.target_tps,
            "total_ticks": self.total_ticks,
            "avg_tick_time_ms": round(self.get_avg_tick_time(), 2),
            "avg_tps": round(self.get_avg_fps(), 2),
            "overrun_rate_pct": round(self.get_overrun_rate(), 2),
            "system_avg_times_ms": {
                name: round(time, 2)
                for name, time in self.get_system_avg_times().items()
            },
            "recent_entity_count": self.tick_history[-1].entity_count if self.tick_history else 0,
        }


class GameLoop:
    """
    Main game loop. Runs at fixed TPS with variable sleep.
    
    INVARIANTS:
    - Systems execute in same order every tick
    - Tick rate is constant (timing varies but rate target is fixed)
    - State is consistent between ticks
    """
    
    def __init__(self, tps: int = 20):
        self.tps = tps
        self.tick_duration = 1.0 / tps
        
        self.state = GameLoopState.STOPPED
        self.world = World(debug=False)
        self.scheduler = SystemScheduler()
        self.performance = PerformanceMonitor(target_tps=tps)
        
        self.current_tick = 0
        self.running = False
        
        # Callbacks
        self.on_tick_start: List[Callable[[int], None]] = []
        self.on_tick_end: List[Callable[[int, TickStats], None]] = []
        
        logger.info(f"GameLoop initialized: {tps} TPS ({self.tick_duration*1000:.1f}ms per tick)")
    
    def add_on_tick_start(self, callback: Callable[[int], None]) -> None:
        """Add callback for tick start"""
        self.on_tick_start.append(callback)
    
    def add_on_tick_end(self, callback: Callable[[int, TickStats], None]) -> None:
        """Add callback for tick end"""
        self.on_tick_end.append(callback)
    
    def _run_tick(self) -> TickStats:
        """
        Run a single game tick.
        
        Steps:
        1. Call tick start callbacks
        2. Update all systems
        3. Call tick end callbacks
        4. Record performance stats
        """
        tick_start = time.monotonic()
        
        # Tick start callbacks
        for callback in self.on_tick_start:
            try:
                callback(self.current_tick)
            except Exception as e:
                logger.error(f"Error in tick start callback: {e}", exc_info=True)
        
        # Update systems
        system_times = self.scheduler.update(self.tick_duration, self.world)
        
        tick_end = time.monotonic()
        actual_duration = tick_end - tick_start
        
        # Create stats
        stats = TickStats(
            tick_number=self.current_tick,
            start_time=tick_start,
            end_time=tick_end,
            target_duration=self.tick_duration,
            actual_duration=actual_duration,
            system_times=system_times,
            entity_count=self.world.get_entity_count(),
        )
        
        # Tick end callbacks
        for callback in self.on_tick_end:
            try:
                callback(self.current_tick, stats)
            except Exception as e:
                logger.error(f"Error in tick end callback: {e}", exc_info=True)
        
        # Record performance
        self.performance.record_tick(stats)
        
        # Log warnings for slow ticks
        if stats.overran:
            logger.warning(
                f"Tick {self.current_tick} overran: {actual_duration*1000:.2f}ms "
                f"(target: {self.tick_duration*1000:.2f}ms)"
            )
        
        return stats
    
    def start(self) -> None:
        """Start the game loop (blocking)"""
        if self.state != GameLoopState.STOPPED:
            logger.warning("Cannot start game loop: already running")
            return
        
        self.state = GameLoopState.STARTING
        logger.info("Starting game loop...")
        
        self.running = True
        self.current_tick = 0
        self.state = GameLoopState.RUNNING
        
        logger.info("Game loop running")
        
        try:
            self._run_loop()
        except KeyboardInterrupt:
            logger.info("Game loop interrupted by user")
        except Exception as e:
            logger.error(f"Game loop crashed: {e}", exc_info=True)
        finally:
            self.running = False
            self.state = GameLoopState.STOPPED
            logger.info("Game loop stopped")
    
    def _run_loop(self) -> None:
        """Main loop implementation"""
        while self.running:
            tick_start = time.monotonic()
            
            # Run tick
            stats = self._run_tick()
            
            # Increment tick counter
            self.current_tick += 1
            
            # Sleep until next tick
            elapsed = time.monotonic() - tick_start
            sleep_time = max(0, self.tick_duration - elapsed)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif elapsed > self.tick_duration * 1.5:
                # Very slow tick, log detailed info
                logger.error(
                    f"Critically slow tick {stats.tick_number}: {elapsed*1000:.2f}ms. "
                    f"System times: {[(k, f'{v*1000:.2f}ms') for k, v in stats.system_times.items()]}"
                )
    
    async def start_async(self) -> None:
        """Start the game loop (async, non-blocking)"""
        if self.state != GameLoopState.STOPPED:
            logger.warning("Cannot start game loop: already running")
            return
        
        self.state = GameLoopState.STARTING
        logger.info("Starting game loop (async)...")
        
        self.running = True
        self.current_tick = 0
        self.state = GameLoopState.RUNNING
        
        logger.info("Game loop running (async)")
        
        try:
            await self._run_loop_async()
        except asyncio.CancelledError:
            logger.info("Game loop cancelled")
        except Exception as e:
            logger.error(f"Game loop crashed: {e}", exc_info=True)
        finally:
            self.running = False
            self.state = GameLoopState.STOPPED
            logger.info("Game loop stopped")
    
    async def _run_loop_async(self) -> None:
        """Async main loop implementation"""
        while self.running:
            tick_start = time.monotonic()
            
            # Run tick (still synchronous, but yields control)
            stats = self._run_tick()
            
            # Increment tick counter
            self.current_tick += 1
            
            # Sleep until next tick (async)
            elapsed = time.monotonic() - tick_start
            sleep_time = max(0, self.tick_duration - elapsed)
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
    
    def stop(self) -> None:
        """Stop the game loop"""
        if self.state != GameLoopState.RUNNING:
            logger.warning("Cannot stop game loop: not running")
            return
        
        self.state = GameLoopState.STOPPING
        logger.info("Stopping game loop...")
        self.running = False
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self.performance.get_report()
    
    def get_world(self) -> World:
        """Get the world instance"""
        return self.world
    
    def get_scheduler(self) -> SystemScheduler:
        """Get the system scheduler"""
        return self.scheduler


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    from backend.engine.ecs import System
    
    # Create a simple test system
    class TestSystem(System):
        def _do_update(self, dt: float, world: World) -> None:
            # Simulate some work
            time.sleep(0.01)  # 10ms of "work"
    
    # Create game loop
    loop = GameLoop(tps=20)
    
    # Add test system
    loop.get_scheduler().add_system("test", TestSystem(priority=100))
    
    # Add tick callbacks
    def on_tick_start(tick: int):
        if tick % 20 == 0:  # Every second
            print(f"Tick {tick}")
    
    def on_tick_end(tick: int, stats: TickStats):
        if tick % 20 == 0:  # Every second
            report = loop.get_performance_report()
            print(f"  Avg tick time: {report['avg_tick_time_ms']:.2f}ms")
            print(f"  Avg TPS: {report['avg_tps']:.2f}")
    
    loop.add_on_tick_start(on_tick_start)
    loop.add_on_tick_end(on_tick_end)
    
    # Run for 5 seconds
    print("Running game loop for 5 seconds...")
    import threading
    
    def stop_after_5s():
        time.sleep(5)
        loop.stop()
    
    threading.Thread(target=stop_after_5s, daemon=True).start()
    
    loop.start()
    
    # Print final report
    print("\n=== Final Performance Report ===")
    report = loop.get_performance_report()
    for key, value in report.items():
        print(f"{key}: {value}")
