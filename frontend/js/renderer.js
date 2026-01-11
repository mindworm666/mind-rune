/**
 * Mind Rune - Rendering Engine
 * 
 * Renders the 3D world in 2D ASCII with:
 * - Character-based tile rendering
 * - Entity sprite rendering
 * - Color coding
 * - Layered rendering (terrain -> entities -> effects)
 * - Double buffering for smooth updates
 * - Viewport clipping and culling
 * 
 * Performance target: 60 FPS at 100x50 viewport
 */

import { Viewport } from './viewport.js';

export class Renderer {
  constructor(canvasId, options = {}) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) {
      throw new Error(`Canvas element #${canvasId} not found`);
    }
    
    this.ctx = this.canvas.getContext('2d', {
      alpha: false,
      desynchronized: true // Hint for better performance
    });
    
    // Configuration
    this.config = {
      charWidth: options.charWidth || 10,
      charHeight: options.charHeight || 20,
      font: options.font || '16px "IBM Plex Mono", monospace',
      backgroundColor: options.backgroundColor || '#0a0a0a',
      viewportWidth: options.viewportWidth || 80,
      viewportHeight: options.viewportHeight || 40,
      showGrid: options.showGrid || false,
      ...options
    };
    
    // Viewport manager
    this.viewport = new Viewport(
      this.config.viewportWidth,
      this.config.viewportHeight
    );
    
    // Double buffering
    this.backBuffer = document.createElement('canvas');
    this.backCtx = this.backBuffer.getContext('2d', { alpha: false });
    
    // Cell buffer - tracks what's rendered in each cell
    this.cellBuffer = [];
    this.resetCellBuffer();
    
    // Tile/entity sprite cache
    this.spriteCache = new Map();
    
    // Animation state
    this.animationFrame = 0;
    this.lastRenderTime = 0;
    this.fps = 0;
    
    // Dirty rectangles for partial redraws
    this.dirtyRegions = [];
    this.fullRedraw = true;
    
    // Stats
    this.stats = {
      tilesRendered: 0,
      entitiesRendered: 0,
      renderTime: 0,
      culledTiles: 0
    };
    
    this.initialize();
  }
  
  initialize() {
    this.resize();
    this.setupFont();
    this.clear();
    
    // Handle window resize
    window.addEventListener('resize', () => this.resize());
  }
  
  resize() {
    // Calculate canvas size based on character dimensions
    const width = this.config.viewportWidth * this.config.charWidth;
    const height = this.config.viewportHeight * this.config.charHeight;
    
    // Set canvas resolution
    this.canvas.width = width;
    this.canvas.height = height;
    this.backBuffer.width = width;
    this.backBuffer.height = height;
    
    // Set display size (can be scaled by CSS)
    this.canvas.style.width = `${width}px`;
    this.canvas.style.height = `${height}px`;
    
    this.setupFont();
    this.fullRedraw = true;
  }
  
  setupFont() {
    this.ctx.font = this.config.font;
    this.ctx.textBaseline = 'top';
    this.ctx.textAlign = 'left';
    
    this.backCtx.font = this.config.font;
    this.backCtx.textBaseline = 'top';
    this.backCtx.textAlign = 'left';
  }
  
  resetCellBuffer() {
    this.cellBuffer = Array(this.config.viewportHeight)
      .fill(null)
      .map(() => Array(this.config.viewportWidth).fill(null));
  }
  
  /**
   * Main render function
   * @param {Object} worldState - Current world state with tiles and entities
   * @param {Object} player - Player entity for camera positioning
   */
  render(worldState, player) {
    const startTime = performance.now();
    this.stats.tilesRendered = 0;
    this.stats.entitiesRendered = 0;
    this.stats.culledTiles = 0;
    
    // Update viewport to follow player
    if (player && player.position) {
      this.viewport.centerOn(player.position.x, player.position.y);
    }
    
    // Clear back buffer
    this.backCtx.fillStyle = this.config.backgroundColor;
    this.backCtx.fillRect(0, 0, this.backBuffer.width, this.backBuffer.height);
    
    // Render layers
    this.renderTerrain(worldState);
    this.renderEntities(worldState);
    this.renderEffects(worldState);
    
    // Optional: Grid overlay for debugging
    if (this.config.showGrid) {
      this.renderGrid();
    }
    
    // Swap buffers
    this.ctx.drawImage(this.backBuffer, 0, 0);
    
    // Update stats
    this.stats.renderTime = performance.now() - startTime;
    this.updateFPS();
    this.animationFrame++;
  }
  
  /**
   * Render terrain tiles
   */
  renderTerrain(worldState) {
    const bounds = this.viewport.getVisibleBounds();
    
    // Get Z-level from player (handle both formats)
    const player = worldState.player;
    const z = player?.z ?? player?.position?.z ?? 0;
    
    for (let y = bounds.minY; y <= bounds.maxY; y++) {
      for (let x = bounds.minX; x <= bounds.maxX; x++) {
        const screenX = x - bounds.minX;
        const screenY = y - bounds.minY;
        
        // Try to get tile from tiles Map (new format)
        let tile = null;
        if (worldState.tiles instanceof Map) {
          const key = `${x},${y},${Math.floor(z)}`;
          tile = worldState.tiles.get(key);
        } else if (worldState.tiles) {
          const key = `${x},${y},${Math.floor(z)}`;
          tile = worldState.tiles[key];
        }
        
        if (tile) {
          this.renderTileData(tile, screenX, screenY);
          this.stats.tilesRendered++;
        } else {
          // Render void/unexplored
          this.drawChar(' ', screenX, screenY, '#222', '#0a0a0a');
          this.stats.culledTiles++;
        }
      }
    }
  }
  
  /**
   * Render a tile from raw server data
   */
  renderTileData(tile, screenX, screenY) {
    const char = tile.char || '.';
    const color = tile.color || '#666666';
    const bgColor = tile.solid ? '#1a1a1a' : '#0a0a0a';
    this.drawChar(char, screenX, screenY, color, bgColor);
  }
  
  /**
   * Render entities (players, NPCs, items)
   */
  renderEntities(worldState) {
    if (!worldState.entities) return;
    
    const bounds = this.viewport.getVisibleBounds();
    const player = worldState.player;
    const z = player?.z ?? player?.position?.z ?? 0;
    
    // Group entities by layer for proper z-ordering
    const layers = {
      items: [],
      npcs: [],
      players: []
    };
    
    // Handle both Map and plain object
    const entityIterable = worldState.entities instanceof Map 
      ? worldState.entities.values() 
      : Object.values(worldState.entities);
    
    for (const entity of entityIterable) {
      // Handle both position formats
      const ex = entity.x ?? entity.position?.x;
      const ey = entity.y ?? entity.position?.y;
      const ez = entity.z ?? entity.position?.z ?? 0;
      
      if (ex === undefined || ey === undefined) continue;
      if (Math.floor(ez) !== Math.floor(z)) continue;
      
      // Cull entities outside viewport
      if (ex < bounds.minX || ex > bounds.maxX || 
          ey < bounds.minY || ey > bounds.maxY) {
        continue;
      }
      
      // Categorize entity
      const entityType = entity.entity_type || entity.type;
      if (entityType === 'item') {
        layers.items.push(entity);
      } else if (entityType === 'player') {
        layers.players.push(entity);
      } else {
        layers.npcs.push(entity);
      }
    }
    
    // Render in order: items -> npcs -> players
    for (const entity of [...layers.items, ...layers.npcs, ...layers.players]) {
      const ex = entity.x ?? entity.position?.x;
      const ey = entity.y ?? entity.position?.y;
      const screenX = ex - bounds.minX;
      const screenY = ey - bounds.minY;
      
      this.renderEntityData(entity, screenX, screenY);
      this.stats.entitiesRendered++;
    }
  }
  
  /**
   * Render entity from raw server data
   */
  renderEntityData(entity, screenX, screenY) {
    const char = entity.char || '?';
    const color = entity.color || '#ffffff';
    this.drawChar(char, screenX, screenY, color, null, true);
    
    // Render HP bar if entity has health
    if (entity.hp !== undefined && entity.max_hp !== undefined && entity.hp < entity.max_hp) {
      this.renderHealthBar(screenX, screenY, entity.hp, entity.max_hp);
    }
  }
  
  /**
   * Render visual effects (damage numbers, particles, etc.)
   */
  renderEffects(worldState) {
    if (!worldState.effects) return;
    
    const bounds = this.viewport.getVisibleBounds();
    
    for (const effect of worldState.effects) {
      if (!effect.position) continue;
      
      const { x, y } = effect.position;
      
      // Cull effects outside viewport
      if (x < bounds.minX || x > bounds.maxX || 
          y < bounds.minY || y > bounds.maxY) {
        continue;
      }
      
      const screenX = x - bounds.minX;
      const screenY = y - bounds.minY;
      
      this.renderEffect(effect, screenX, screenY);
    }
  }
  
  /**
   * Render a single tile
   */
  renderTile(tile, screenX, screenY) {
    const sprite = this.getTileSprite(tile);
    this.drawChar(
      sprite.char,
      screenX,
      screenY,
      sprite.color,
      sprite.backgroundColor
    );
  }
  
  /**
   * Render a single entity
   */
  renderEntity(entity, screenX, screenY) {
    const sprite = this.getEntitySprite(entity);
    this.drawChar(
      sprite.char,
      screenX,
      screenY,
      sprite.color,
      sprite.backgroundColor,
      sprite.bold
    );
    
    // Render HP bar if entity has health
    if (entity.components?.has('Stats')) {
      const stats = entity.components.get('Stats');
      if (stats.hp < stats.maxHp) {
        this.renderHealthBar(screenX, screenY, stats.hp, stats.maxHp);
      }
    }
  }
  
  /**
   * Render a visual effect
   */
  renderEffect(effect, screenX, screenY) {
    switch (effect.type) {
      case 'damage':
        this.renderDamageNumber(screenX, screenY, effect.value, effect.age);
        break;
      case 'heal':
        this.renderHealNumber(screenX, screenY, effect.value, effect.age);
        break;
      case 'particle':
        this.renderParticle(screenX, screenY, effect);
        break;
    }
  }
  
  /**
   * Draw a character at screen coordinates
   */
  drawChar(char, screenX, screenY, color, backgroundColor = null, bold = false) {
    const pixelX = screenX * this.config.charWidth;
    const pixelY = screenY * this.config.charHeight;
    
    // Draw background if specified
    if (backgroundColor) {
      this.backCtx.fillStyle = backgroundColor;
      this.backCtx.fillRect(
        pixelX,
        pixelY,
        this.config.charWidth,
        this.config.charHeight
      );
    }
    
    // Draw character
    this.backCtx.fillStyle = color;
    if (bold) {
      this.backCtx.font = `bold ${this.config.font}`;
    }
    this.backCtx.fillText(char, pixelX, pixelY);
    if (bold) {
      this.backCtx.font = this.config.font; // Reset
    }
  }
  
  /**
   * Get tile sprite information
   */
  getTileSprite(tile) {
    const cacheKey = `tile_${tile.type}`;
    
    if (this.spriteCache.has(cacheKey)) {
      return this.spriteCache.get(cacheKey);
    }
    
    const sprite = this.createTileSprite(tile);
    this.spriteCache.set(cacheKey, sprite);
    return sprite;
  }
  
  createTileSprite(tile) {
    // Default sprites for terrain types
    const sprites = {
      'void': { char: ' ', color: '#000000', backgroundColor: '#000000' },
      'ground': { char: '.', color: '#669966', backgroundColor: null },
      'grass': { char: ',', color: '#66aa66', backgroundColor: null },
      'wall': { char: '#', color: '#888888', backgroundColor: null },
      'water': { char: '~', color: '#3366ff', backgroundColor: null },
      'mountain': { char: '^', color: '#999999', backgroundColor: null },
      'tree': { char: '♣', color: '#44aa44', backgroundColor: null },
      'stone': { char: '░', color: '#777777', backgroundColor: null },
      'door_closed': { char: '+', color: '#aa8844', backgroundColor: null },
      'door_open': { char: '/', color: '#aa8844', backgroundColor: null },
      'stairs_up': { char: '<', color: '#ffff66', backgroundColor: null },
      'stairs_down': { char: '>', color: '#ffff66', backgroundColor: null },
    };
    
    return sprites[tile.type] || sprites['ground'];
  }
  
  /**
   * Get entity sprite information
   */
  getEntitySprite(entity) {
    const cacheKey = `entity_${entity.type}_${this.animationFrame % 4}`;
    
    if (this.spriteCache.has(cacheKey)) {
      return this.spriteCache.get(cacheKey);
    }
    
    const sprite = this.createEntitySprite(entity);
    this.spriteCache.set(cacheKey, sprite);
    return sprite;
  }
  
  createEntitySprite(entity) {
    // Player sprites
    if (entity.components?.has('Player')) {
      return {
        char: '@',
        color: '#33ff33',
        backgroundColor: null,
        bold: true
      };
    }
    
    // NPC/Monster sprites
    const sprites = {
      'goblin': { char: 'g', color: '#66ff66', bold: false },
      'orc': { char: 'o', color: '#88ff88', bold: false },
      'skeleton': { char: 's', color: '#cccccc', bold: false },
      'dragon': { char: 'D', color: '#ff3333', bold: true },
      'rat': { char: 'r', color: '#999966', bold: false },
      'bat': { char: 'b', color: '#aa99aa', bold: false },
    };
    
    // Item sprites
    const itemSprites = {
      'potion': { char: '!', color: '#ff66ff', bold: false },
      'sword': { char: '/', color: '#aaaaaa', bold: false },
      'shield': { char: '[', color: '#9999aa', bold: false },
      'gold': { char: '$', color: '#ffff00', bold: true },
      'scroll': { char: '?', color: '#ffaa66', bold: false },
    };
    
    const type = entity.type || 'unknown';
    const sprite = sprites[type] || itemSprites[type] || {
      char: '?',
      color: '#ff33ff',
      bold: false
    };
    
    return {
      ...sprite,
      backgroundColor: null
    };
  }
  
  /**
   * Render HP bar above entity
   */
  renderHealthBar(screenX, screenY, hp, maxHp) {
    const pixelX = screenX * this.config.charWidth;
    const pixelY = screenY * this.config.charHeight - 4;
    
    const barWidth = this.config.charWidth;
    const barHeight = 2;
    const fillWidth = (hp / maxHp) * barWidth;
    
    // Background
    this.backCtx.fillStyle = '#330000';
    this.backCtx.fillRect(pixelX, pixelY, barWidth, barHeight);
    
    // HP fill
    const color = hp > maxHp * 0.5 ? '#33ff33' : 
                  hp > maxHp * 0.25 ? '#ffff33' : '#ff3333';
    this.backCtx.fillStyle = color;
    this.backCtx.fillRect(pixelX, pixelY, fillWidth, barHeight);
  }
  
  /**
   * Render floating damage number
   */
  renderDamageNumber(screenX, screenY, value, age) {
    const pixelX = screenX * this.config.charWidth;
    const pixelY = screenY * this.config.charHeight - age * 2; // Float up
    
    const opacity = Math.max(0, 1 - age / 30); // Fade out over 30 frames
    
    this.backCtx.save();
    this.backCtx.globalAlpha = opacity;
    this.backCtx.fillStyle = '#ff6666';
    this.backCtx.font = `bold ${this.config.font}`;
    this.backCtx.fillText(`-${value}`, pixelX, pixelY);
    this.backCtx.restore();
  }
  
  /**
   * Render floating heal number
   */
  renderHealNumber(screenX, screenY, value, age) {
    const pixelX = screenX * this.config.charWidth;
    const pixelY = screenY * this.config.charHeight - age * 2; // Float up
    
    const opacity = Math.max(0, 1 - age / 30);
    
    this.backCtx.save();
    this.backCtx.globalAlpha = opacity;
    this.backCtx.fillStyle = '#66ff66';
    this.backCtx.font = `bold ${this.config.font}`;
    this.backCtx.fillText(`+${value}`, pixelX, pixelY);
    this.backCtx.restore();
  }
  
  /**
   * Render particle effect
   */
  renderParticle(screenX, screenY, particle) {
    const pixelX = screenX * this.config.charWidth + particle.offsetX;
    const pixelY = screenY * this.config.charHeight + particle.offsetY;
    
    const opacity = Math.max(0, 1 - particle.age / particle.maxAge);
    
    this.backCtx.save();
    this.backCtx.globalAlpha = opacity;
    this.backCtx.fillStyle = particle.color;
    this.backCtx.fillRect(pixelX, pixelY, 2, 2);
    this.backCtx.restore();
  }
  
  /**
   * Render debug grid
   */
  renderGrid() {
    this.backCtx.strokeStyle = '#ffffff11';
    this.backCtx.lineWidth = 1;
    
    // Vertical lines
    for (let x = 0; x <= this.config.viewportWidth; x++) {
      const pixelX = x * this.config.charWidth;
      this.backCtx.beginPath();
      this.backCtx.moveTo(pixelX, 0);
      this.backCtx.lineTo(pixelX, this.backBuffer.height);
      this.backCtx.stroke();
    }
    
    // Horizontal lines
    for (let y = 0; y <= this.config.viewportHeight; y++) {
      const pixelY = y * this.config.charHeight;
      this.backCtx.beginPath();
      this.backCtx.moveTo(0, pixelY);
      this.backCtx.lineTo(this.backBuffer.width, pixelY);
      this.backCtx.stroke();
    }
  }
  
  /**
   * Clear entire canvas
   */
  clear() {
    this.ctx.fillStyle = this.config.backgroundColor;
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    this.backCtx.fillStyle = this.config.backgroundColor;
    this.backCtx.fillRect(0, 0, this.backBuffer.width, this.backBuffer.height);
    this.resetCellBuffer();
    this.fullRedraw = true;
  }
  
  /**
   * Get tile from world state
   */
  getTile(worldState, x, y, z) {
    // World state should provide a way to get tiles
    if (worldState.getTile) {
      return worldState.getTile(x, y, z);
    }
    
    // Fallback to chunks if available
    if (worldState.chunks) {
      const chunkKey = this.getChunkKey(x, y, z);
      const chunk = worldState.chunks.get(chunkKey);
      if (!chunk) return null;
      
      const localX = ((x % 16) + 16) % 16;
      const localY = ((y % 16) + 16) % 16;
      const localZ = ((z % 16) + 16) % 16;
      
      return chunk.tiles[localZ]?.[localY]?.[localX];
    }
    
    return null;
  }
  
  getChunkKey(x, y, z) {
    const chunkX = Math.floor(x / 16);
    const chunkY = Math.floor(y / 16);
    const chunkZ = Math.floor(z / 16);
    return `${chunkX},${chunkY},${chunkZ}`;
  }
  
  /**
   * Update FPS counter
   */
  updateFPS() {
    const now = performance.now();
    if (this.lastRenderTime) {
      const delta = now - this.lastRenderTime;
      this.fps = Math.round(1000 / delta);
    }
    this.lastRenderTime = now;
  }
  
  /**
   * Get rendering statistics
   */
  getStats() {
    return {
      ...this.stats,
      fps: this.fps,
      viewportBounds: this.viewport.getVisibleBounds()
    };
  }
  
  /**
   * Convert screen coordinates to world coordinates
   */
  screenToWorld(screenX, screenY) {
    const bounds = this.viewport.getVisibleBounds();
    return {
      x: bounds.minX + Math.floor(screenX / this.config.charWidth),
      y: bounds.minY + Math.floor(screenY / this.config.charHeight)
    };
  }
  
  /**
   * Convert world coordinates to screen coordinates
   */
  worldToScreen(worldX, worldY) {
    const bounds = this.viewport.getVisibleBounds();
    return {
      x: (worldX - bounds.minX) * this.config.charWidth,
      y: (worldY - bounds.minY) * this.config.charHeight
    };
  }
}
