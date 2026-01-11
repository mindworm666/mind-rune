/**
 * Mind Rune - Viewport Manager
 * 
 * Manages the visible portion of the world:
 * - Camera positioning and following
 * - Smooth scrolling
 * - Viewport bounds calculation
 * - Culling optimization
 */

export class Viewport {
  constructor(width, height) {
    this.width = width;
    this.height = height;
    
    // Camera position (center of viewport in world coordinates)
    this.cameraX = 0;
    this.cameraY = 0;
    this.cameraZ = 0;
    
    // Target position for smooth following
    this.targetX = 0;
    this.targetY = 0;
    
    // Follow parameters
    this.followSpeed = 0.15; // 0 = instant, 1 = never catch up
    this.followEnabled = true;
    
    // Bounds caching
    this.cachedBounds = null;
    this.boundsInvalidated = true;
  }
  
  /**
   * Set viewport dimensions
   */
  resize(width, height) {
    this.width = width;
    this.height = height;
    this.boundsInvalidated = true;
  }
  
  /**
   * Center camera on world coordinates instantly
   */
  centerOn(x, y, z = 0) {
    this.cameraX = x;
    this.cameraY = y;
    this.cameraZ = z;
    this.targetX = x;
    this.targetY = y;
    this.boundsInvalidated = true;
  }
  
  /**
   * Set target position for smooth following
   */
  setTarget(x, y) {
    this.targetX = x;
    this.targetY = y;
  }
  
  /**
   * Update camera position (call every frame for smooth following)
   */
  update(deltaTime) {
    if (!this.followEnabled) return;
    
    // Smooth camera movement using lerp
    const dx = this.targetX - this.cameraX;
    const dy = this.targetY - this.cameraY;
    
    // Only move if difference is significant
    if (Math.abs(dx) > 0.01 || Math.abs(dy) > 0.01) {
      this.cameraX += dx * this.followSpeed;
      this.cameraY += dy * this.followSpeed;
      this.boundsInvalidated = true;
    } else {
      // Snap to target if very close
      this.cameraX = this.targetX;
      this.cameraY = this.targetY;
    }
  }
  
  /**
   * Get visible world bounds
   * Returns {minX, maxX, minY, maxY}
   */
  getVisibleBounds() {
    if (!this.boundsInvalidated && this.cachedBounds) {
      return this.cachedBounds;
    }
    
    const halfWidth = Math.floor(this.width / 2);
    const halfHeight = Math.floor(this.height / 2);
    
    this.cachedBounds = {
      minX: Math.floor(this.cameraX - halfWidth),
      maxX: Math.floor(this.cameraX + halfWidth),
      minY: Math.floor(this.cameraY - halfHeight),
      maxY: Math.floor(this.cameraY + halfHeight),
      z: this.cameraZ
    };
    
    this.boundsInvalidated = false;
    return this.cachedBounds;
  }
  
  /**
   * Check if world position is visible
   */
  isVisible(x, y, z = 0) {
    if (z !== this.cameraZ) return false;
    
    const bounds = this.getVisibleBounds();
    return x >= bounds.minX && x <= bounds.maxX &&
           y >= bounds.minY && y <= bounds.maxY;
  }
  
  /**
   * Get camera offset from world coordinates
   */
  getOffset() {
    const bounds = this.getVisibleBounds();
    return {
      x: bounds.minX,
      y: bounds.minY,
      z: this.cameraZ
    };
  }
  
  /**
   * Scroll camera by delta
   */
  scroll(dx, dy) {
    this.cameraX += dx;
    this.cameraY += dy;
    this.targetX = this.cameraX;
    this.targetY = this.cameraY;
    this.boundsInvalidated = true;
  }
  
  /**
   * Change Z-level
   */
  setZLevel(z) {
    this.cameraZ = z;
    this.boundsInvalidated = true;
  }
  
  /**
   * Enable/disable smooth following
   */
  setFollowEnabled(enabled) {
    this.followEnabled = enabled;
  }
  
  /**
   * Set follow speed (0 = instant, 1 = never)
   */
  setFollowSpeed(speed) {
    this.followSpeed = Math.max(0, Math.min(1, speed));
  }
  
  /**
   * Get camera position
   */
  getPosition() {
    return {
      x: this.cameraX,
      y: this.cameraY,
      z: this.cameraZ
    };
  }
  
  /**
   * Convert world coordinates to screen coordinates
   */
  worldToScreen(worldX, worldY) {
    const bounds = this.getVisibleBounds();
    return {
      x: worldX - bounds.minX,
      y: worldY - bounds.minY
    };
  }
  
  /**
   * Convert screen coordinates to world coordinates
   */
  screenToWorld(screenX, screenY) {
    const bounds = this.getVisibleBounds();
    return {
      x: screenX + bounds.minX,
      y: screenY + bounds.minY,
      z: this.cameraZ
    };
  }
  
  /**
   * Clamp camera to world bounds
   */
  clampToBounds(minX, minY, maxX, maxY) {
    const halfWidth = Math.floor(this.width / 2);
    const halfHeight = Math.floor(this.height / 2);
    
    const clampedX = Math.max(minX + halfWidth, Math.min(maxX - halfWidth, this.cameraX));
    const clampedY = Math.max(minY + halfHeight, Math.min(maxY - halfHeight, this.cameraY));
    
    if (clampedX !== this.cameraX || clampedY !== this.cameraY) {
      this.cameraX = clampedX;
      this.cameraY = clampedY;
      this.targetX = clampedX;
      this.targetY = clampedY;
      this.boundsInvalidated = true;
    }
  }
  
  /**
   * Get visible chunk keys for chunk-based loading
   */
  getVisibleChunks(chunkSize = 16) {
    const bounds = this.getVisibleBounds();
    const chunks = [];
    
    const minChunkX = Math.floor(bounds.minX / chunkSize);
    const maxChunkX = Math.floor(bounds.maxX / chunkSize);
    const minChunkY = Math.floor(bounds.minY / chunkSize);
    const maxChunkY = Math.floor(bounds.maxY / chunkSize);
    const chunkZ = Math.floor(this.cameraZ / chunkSize);
    
    for (let cy = minChunkY; cy <= maxChunkY; cy++) {
      for (let cx = minChunkX; cx <= maxChunkX; cx++) {
        chunks.push({
          x: cx,
          y: cy,
          z: chunkZ,
          key: `${cx},${cy},${chunkZ}`
        });
      }
    }
    
    return chunks;
  }
  
  /**
   * Calculate distance from camera to world position
   */
  distanceToCamera(x, y) {
    const dx = x - this.cameraX;
    const dy = y - this.cameraY;
    return Math.sqrt(dx * dx + dy * dy);
  }
  
  /**
   * Get zoom level (for future implementation)
   */
  getZoom() {
    return 1.0; // Default zoom, can be extended
  }
  
  /**
   * Set zoom level (for future implementation)
   */
  setZoom(zoom) {
    // TODO: Implement zoom functionality
    // Would require adjusting viewport dimensions
  }
  
  /**
   * Shake camera for effects (earthquakes, explosions)
   */
  shake(intensity, duration) {
    // TODO: Implement camera shake
    // Store shake parameters and apply in update()
  }
}
