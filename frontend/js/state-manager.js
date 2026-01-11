/**
 * Mind Rune - State Manager
 * 
 * Client-side game state management:
 * - Entity cache with spatial indexing
 * - World chunk cache with LRU eviction
 * - Player state tracking
 * - Event system for state changes
 * - Client-side validation
 */

export class StateManager {
  constructor(options = {}) {
    this.options = {
      maxCachedChunks: options.maxCachedChunks || 100,
      chunkSize: options.chunkSize || 16,
      ...options
    };
    
    // State
    this.player = null;
    this.entities = new Map();
    this.chunks = new Map();
    this.effects = [];
    
    // Chunk LRU cache
    this.chunkAccessOrder = [];
    
    // Spatial index for fast queries
    this.spatialIndex = new Map(); // z -> Map<chunkKey, Set<entityId>>
    
    // Event listeners
    this.listeners = new Map();
    
    // Connection state
    this.connectionState = {
      status: 'disconnected', // 'disconnected', 'connecting', 'connected'
      latency: 0,
      lastUpdate: 0
    };
  }
  
  // ============================================================================
  // State Updates
  // ============================================================================
  
  updateState(newState, isDelta = false) {
    if (!isDelta) {
      // Full state replacement
      this.player = newState.player || null;
      this.entities = new Map(newState.entities || []);
      this.chunks = new Map(newState.chunks || []);
      this.effects = newState.effects || [];
    } else {
      // Delta update - merge changes
      if (newState.player) {
        this.updatePlayer(newState.player);
      }
      if (newState.entities) {
        this.updateEntities(newState.entities);
      }
      if (newState.chunks) {
        this.updateChunks(newState.chunks);
      }
      if (newState.effects) {
        this.updateEffects(newState.effects);
      }
    }
    
    this.connectionState.lastUpdate = Date.now();
    this.emit('stateUpdated', { state: this.getState(), isDelta });
  }
  
  updatePlayer(playerData) {
    if (!this.player) {
      this.player = playerData;
    } else {
      const oldPosition = this.player.position;
      Object.assign(this.player, playerData);
      
      // Emit position change event
      if (oldPosition && playerData.position &&
          (oldPosition.x !== playerData.position.x ||
           oldPosition.y !== playerData.position.y ||
           oldPosition.z !== playerData.position.z)) {
        this.emit('playerMoved', { 
          from: oldPosition, 
          to: playerData.position 
        });
      }
    }
  }
  
  updateEntities(entityUpdates) {
    for (const [entityId, data] of Object.entries(entityUpdates)) {
      const id = parseInt(entityId);
      
      if (data === null) {
        // Entity removed
        this.removeEntity(id);
      } else {
        // Entity added/updated
        const existing = this.entities.get(id);
        if (existing) {
          Object.assign(existing, data);
          this.emit('entityUpdated', { entityId: id, entity: existing });
        } else {
          this.entities.set(id, data);
          this.emit('entitySpawned', { entityId: id, entity: data });
          this.indexEntity(id, data);
        }
      }
    }
  }
  
  removeEntity(entityId) {
    const entity = this.entities.get(entityId);
    if (entity) {
      this.unindexEntity(entityId, entity);
      this.entities.delete(entityId);
      this.emit('entityDespawned', { entityId, entity });
    }
  }
  
  updateChunks(chunkUpdates) {
    for (const [chunkKey, chunkData] of Object.entries(chunkUpdates)) {
      if (chunkData === null) {
        // Chunk unloaded
        this.chunks.delete(chunkKey);
        this.chunkAccessOrder = this.chunkAccessOrder.filter(k => k !== chunkKey);
      } else {
        // Chunk loaded/updated
        this.chunks.set(chunkKey, chunkData);
        this.touchChunk(chunkKey);
        this.emit('chunkLoaded', { chunkKey, chunk: chunkData });
      }
    }
    
    // Evict old chunks if over limit
    this.evictOldChunks();
  }
  
  updateEffects(effectUpdates) {
    // Effects are short-lived, so just replace
    this.effects = effectUpdates;
  }
  
  // ============================================================================
  // Spatial Indexing
  // ============================================================================
  
  indexEntity(entityId, entity) {
    if (!entity.position) return;
    
    const { x, y, z } = entity.position;
    const chunkKey = this.getChunkKey(x, y, z);
    
    if (!this.spatialIndex.has(z)) {
      this.spatialIndex.set(z, new Map());
    }
    
    const zIndex = this.spatialIndex.get(z);
    if (!zIndex.has(chunkKey)) {
      zIndex.set(chunkKey, new Set());
    }
    
    zIndex.get(chunkKey).add(entityId);
  }
  
  unindexEntity(entityId, entity) {
    if (!entity.position) return;
    
    const { x, y, z } = entity.position;
    const chunkKey = this.getChunkKey(x, y, z);
    
    const zIndex = this.spatialIndex.get(z);
    if (zIndex && zIndex.has(chunkKey)) {
      zIndex.get(chunkKey).delete(entityId);
    }
  }
  
  // ============================================================================
  // Queries
  // ============================================================================
  
  getEntity(entityId) {
    return this.entities.get(entityId);
  }
  
  getEntitiesInChunk(chunkKey, z) {
    const zIndex = this.spatialIndex.get(z);
    if (!zIndex || !zIndex.has(chunkKey)) {
      return [];
    }
    
    const entityIds = zIndex.get(chunkKey);
    return Array.from(entityIds).map(id => this.entities.get(id)).filter(Boolean);
  }
  
  getEntitiesNear(x, y, z, radius) {
    const entities = [];
    const radiusSquared = radius * radius;
    
    // Check entities in nearby chunks
    const minChunkX = Math.floor((x - radius) / this.options.chunkSize);
    const maxChunkX = Math.floor((x + radius) / this.options.chunkSize);
    const minChunkY = Math.floor((y - radius) / this.options.chunkSize);
    const maxChunkY = Math.floor((y + radius) / this.options.chunkSize);
    const chunkZ = Math.floor(z / this.options.chunkSize);
    
    for (let cy = minChunkY; cy <= maxChunkY; cy++) {
      for (let cx = minChunkX; cx <= maxChunkX; cx++) {
        const chunkKey = `${cx},${cy},${chunkZ}`;
        const chunkEntities = this.getEntitiesInChunk(chunkKey, z);
        
        for (const entity of chunkEntities) {
          if (!entity.position) continue;
          
          const dx = entity.position.x - x;
          const dy = entity.position.y - y;
          const distSquared = dx * dx + dy * dy;
          
          if (distSquared <= radiusSquared) {
            entities.push(entity);
          }
        }
      }
    }
    
    return entities;
  }
  
  getEntitiesAt(x, y, z) {
    return Array.from(this.entities.values()).filter(entity => {
      return entity.position &&
             entity.position.x === x &&
             entity.position.y === y &&
             entity.position.z === z;
    });
  }
  
  getTile(x, y, z) {
    const chunkKey = this.getChunkKey(x, y, z);
    const chunk = this.chunks.get(chunkKey);
    
    if (!chunk || !chunk.tiles) return null;
    
    const localX = ((x % this.options.chunkSize) + this.options.chunkSize) % this.options.chunkSize;
    const localY = ((y % this.options.chunkSize) + this.options.chunkSize) % this.options.chunkSize;
    const localZ = ((z % this.options.chunkSize) + this.options.chunkSize) % this.options.chunkSize;
    
    return chunk.tiles[localZ]?.[localY]?.[localX] || null;
  }
  
  getChunk(chunkKey) {
    this.touchChunk(chunkKey);
    return this.chunks.get(chunkKey);
  }
  
  // ============================================================================
  // Chunk Management
  // ============================================================================
  
  getChunkKey(x, y, z) {
    const chunkX = Math.floor(x / this.options.chunkSize);
    const chunkY = Math.floor(y / this.options.chunkSize);
    const chunkZ = Math.floor(z / this.options.chunkSize);
    return `${chunkX},${chunkY},${chunkZ}`;
  }
  
  touchChunk(chunkKey) {
    // Move to end of LRU list
    this.chunkAccessOrder = this.chunkAccessOrder.filter(k => k !== chunkKey);
    this.chunkAccessOrder.push(chunkKey);
  }
  
  evictOldChunks() {
    while (this.chunks.size > this.options.maxCachedChunks) {
      const oldestKey = this.chunkAccessOrder.shift();
      if (oldestKey) {
        this.chunks.delete(oldestKey);
        this.emit('chunkEvicted', { chunkKey: oldestKey });
      }
    }
  }
  
  // ============================================================================
  // Player
  // ============================================================================
  
  getPlayer() {
    return this.player;
  }
  
  getPlayerPosition() {
    return this.player?.position || { x: 0, y: 0, z: 0 };
  }
  
  getPlayerStats() {
    return this.player?.stats || {};
  }
  
  // ============================================================================
  // State Export
  // ============================================================================
  
  getState() {
    return {
      player: this.player,
      entities: this.entities,
      chunks: this.chunks,
      effects: this.effects,
      connection: this.connectionState
    };
  }
  
  // ============================================================================
  // Connection State
  // ============================================================================
  
  setConnectionStatus(status, latency = 0) {
    this.connectionState.status = status;
    this.connectionState.latency = latency;
    this.emit('connectionChanged', { status, latency });
  }
  
  getConnectionStatus() {
    return this.connectionState.status;
  }
  
  getLatency() {
    return this.connectionState.latency;
  }
  
  // ============================================================================
  // Events
  // ============================================================================
  
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }
  
  off(event, callback) {
    if (!this.listeners.has(event)) return;
    
    const callbacks = this.listeners.get(event);
    const index = callbacks.indexOf(callback);
    if (index !== -1) {
      callbacks.splice(index, 1);
    }
  }
  
  emit(event, data) {
    if (!this.listeners.has(event)) return;
    
    const callbacks = this.listeners.get(event);
    for (const callback of callbacks) {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in event listener for ${event}:`, error);
      }
    }
  }
  
  // ============================================================================
  // Validation (Client-side invariant checking)
  // ============================================================================
  
  validatePlayerState() {
    if (!this.player) return true;
    
    const stats = this.player.stats;
    if (!stats) return true;
    
    // Check HP bounds
    if (stats.hp < 0 || stats.hp > stats.maxHp) {
      console.warn('Invalid HP:', stats.hp, '/', stats.maxHp);
      stats.hp = Math.max(0, Math.min(stats.maxHp, stats.hp));
    }
    
    // Check MP bounds
    if (stats.mp < 0 || stats.mp > stats.maxMp) {
      console.warn('Invalid MP:', stats.mp, '/', stats.maxMp);
      stats.mp = Math.max(0, Math.min(stats.maxMp, stats.mp));
    }
    
    return true;
  }
  
  // ============================================================================
  // Cleanup
  // ============================================================================
  
  clear() {
    this.player = null;
    this.entities.clear();
    this.chunks.clear();
    this.effects = [];
    this.spatialIndex.clear();
    this.chunkAccessOrder = [];
    this.emit('stateCleared');
  }
}
