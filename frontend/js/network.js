/**
 * Mind Rune - Network Client
 * 
 * WebSocket client with:
 * - Auto-reconnect with exponential backoff
 * - Delta state updates
 * - Command queue with client prediction
 * - Entity interpolation
 * - Latency compensation
 * - Auth management
 */

export class NetworkClient {
  constructor(options = {}) {
    this.options = {
      url: options.url || this.getDefaultUrl(),
      reconnectDelay: options.reconnectDelay || 1000,
      maxReconnectDelay: options.maxReconnectDelay || 30000,
      reconnectBackoff: options.reconnectBackoff || 1.5,
      pingInterval: options.pingInterval || 5000,
      ...options
    };
    
    this.ws = null;
    this.connected = false;
    this.connecting = false;
    this.reconnectAttempts = 0;
    this.reconnectTimeout = null;
    
    // Auth
    this.playerId = null;
    this.playerName = null;
    
    // Message handling
    this.messageHandlers = new Map();
    this.messageQueue = [];
    this.messageId = 0;
    
    // Latency tracking
    this.latency = 0;
    this.lastPingTime = 0;
    this.pingIntervalId = null;
    
    // State tracking
    this.lastState = null;
    this.currentTick = 0;
    this.entities = new Map();
    this.worldTiles = new Map();
    
    // Callbacks
    this.callbacks = {
      onConnect: options.onConnect || null,
      onDisconnect: options.onDisconnect || null,
      onAuthSuccess: options.onAuthSuccess || null,
      onAuthFailure: options.onAuthFailure || null,
      onGameState: options.onGameState || null,
      onStateUpdate: options.onStateUpdate || null,
      onEntitySpawn: options.onEntitySpawn || null,
      onEntityDespawn: options.onEntityDespawn || null,
      onEntityUpdate: options.onEntityUpdate || null,
      onDamage: options.onDamage || null,
      onDeath: options.onDeath || null,
      onLevelUp: options.onLevelUp || null,
      onChat: options.onChat || null,
      onSystemMessage: options.onSystemMessage || null,
      onError: options.onError || null
    };
    
    this.setupMessageHandlers();
  }
  
  getDefaultUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Default to localhost:8765 for development
    const host = window.location.hostname || 'localhost';
    return `${protocol}//${host}:8765`;
  }
  
  setupMessageHandlers() {
    // Auth handlers
    this.on('auth_success', (data) => this.handleAuthSuccess(data));
    this.on('auth_failure', (data) => this.handleAuthFailure(data));
    
    // State updates
    this.on('game_state', (data) => this.handleGameState(data));
    this.on('game_state_delta', (data) => this.handleGameStateDelta(data));
    
    // Entity events
    this.on('entity_spawn', (data) => this.handleEntitySpawn(data));
    this.on('entity_despawn', (data) => this.handleEntityDespawn(data));
    this.on('entity_update', (data) => this.handleEntityUpdate(data));
    
    // Combat events
    this.on('damage_event', (data) => this.handleDamage(data));
    this.on('death_event', (data) => this.handleDeath(data));
    this.on('level_up_event', (data) => this.handleLevelUp(data));
    
    // Chat
    this.on('chat_receive', (data) => this.handleChatReceive(data));
    this.on('system_message', (data) => this.handleSystemMessage(data));
    
    // Utility
    this.on('pong', (data) => this.handlePong(data));
    this.on('error', (data) => this.handleServerError(data));
  }
  
  // ============================================================================
  // Connection Management
  // ============================================================================
  
  connect() {
    if (this.connecting || this.connected) {
      console.warn('Already connected or connecting');
      return;
    }
    
    this.connecting = true;
    console.log(`Connecting to ${this.options.url}...`);
    
    try {
      this.ws = new WebSocket(this.options.url);
      
      this.ws.onopen = () => this.handleOpen();
      this.ws.onclose = (event) => this.handleClose(event);
      this.ws.onerror = (error) => this.handleError(error);
      this.ws.onmessage = (event) => this.handleMessage(event);
      
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.connecting = false;
      this.scheduleReconnect();
    }
  }
  
  disconnect() {
    this.connected = false;
    this.connecting = false;
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.pingIntervalId) {
      clearInterval(this.pingIntervalId);
      this.pingIntervalId = null;
    }
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    // Reset state
    this.playerId = null;
    this.playerName = null;
    this.entities.clear();
    this.worldTiles.clear();
  }
  
  handleOpen() {
    console.log('WebSocket connected');
    this.connected = true;
    this.connecting = false;
    this.reconnectAttempts = 0;
    
    // Start ping interval
    this.startPing();
    
    if (this.callbacks.onConnect) {
      this.callbacks.onConnect();
    }
  }
  
  handleClose(event) {
    console.log('WebSocket closed:', event.code, event.reason);
    const wasConnected = this.connected;
    this.connected = false;
    this.connecting = false;
    
    if (this.pingIntervalId) {
      clearInterval(this.pingIntervalId);
      this.pingIntervalId = null;
    }
    
    if (this.callbacks.onDisconnect) {
      this.callbacks.onDisconnect(event);
    }
    
    // Auto-reconnect unless it was a clean close
    if (event.code !== 1000) {
      this.scheduleReconnect();
    }
  }
  
  handleError(error) {
    console.error('WebSocket error:', error);
    
    if (this.callbacks.onError) {
      this.callbacks.onError(error);
    }
  }
  
  handleMessage(event) {
    try {
      const message = JSON.parse(event.data);
      
      // Call specific handler if registered
      if (this.messageHandlers.has(message.type)) {
        const handler = this.messageHandlers.get(message.type);
        handler(message.data, message);
      } else {
        console.log('Unhandled message type:', message.type, message.data);
      }
      
    } catch (error) {
      console.error('Failed to parse message:', error, event.data);
    }
  }
  
  scheduleReconnect() {
    if (this.reconnectTimeout) return;
    
    const delay = Math.min(
      this.options.reconnectDelay * Math.pow(this.options.reconnectBackoff, this.reconnectAttempts),
      this.options.maxReconnectDelay
    );
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }
  
  // ============================================================================
  // Message Sending
  // ============================================================================
  
  send(type, data = {}) {
    if (!this.connected) {
      console.warn('Cannot send message: not connected');
      return false;
    }
    
    try {
      const message = JSON.stringify({
        type,
        id: ++this.messageId,
        ts: Date.now() / 1000,
        data
      });
      this.ws.send(message);
      return true;
    } catch (error) {
      console.error('Failed to send message:', error);
      return false;
    }
  }
  
  on(messageType, handler) {
    this.messageHandlers.set(messageType, handler);
  }
  
  off(messageType) {
    this.messageHandlers.delete(messageType);
  }
  
  // ============================================================================
  // Auth
  // ============================================================================
  
  login(username, password) {
    return this.send('auth_login', { username, password });
  }
  
  register(username, password, email = '') {
    return this.send('auth_register', { username, password, email });
  }
  
  logout() {
    this.send('auth_logout', {});
    this.disconnect();
  }
  
  handleAuthSuccess(data) {
    console.log('Auth successful:', data);
    this.playerId = data.player_id;
    this.playerName = data.character_name;
    
    if (this.callbacks.onAuthSuccess) {
      this.callbacks.onAuthSuccess(data);
    }
  }
  
  handleAuthFailure(data) {
    console.error('Auth failed:', data.reason);
    
    if (this.callbacks.onAuthFailure) {
      this.callbacks.onAuthFailure(data.reason);
    }
  }
  
  // ============================================================================
  // Game State
  // ============================================================================
  
  handleGameState(data) {
    console.log('Received full game state:', data);
    this.currentTick = data.tick;
    
    // Store player data
    if (data.player) {
      this.entities.set(data.player.entity_id, data.player);
    }
    
    // Store all entities
    if (data.entities) {
      for (const entity of data.entities) {
        this.entities.set(entity.entity_id, entity);
      }
    }
    
    // Store world tiles
    if (data.world_tiles) {
      for (const [key, tile] of Object.entries(data.world_tiles)) {
        this.worldTiles.set(key, tile);
      }
    }
    
    this.lastState = {
      tick: data.tick,
      player: data.player,
      entities: this.entities,
      tiles: this.worldTiles
    };
    
    if (this.callbacks.onGameState) {
      this.callbacks.onGameState(this.lastState);
    }
  }
  
  handleGameStateDelta(data) {
    this.currentTick = data.tick;
    
    // Update changed entities
    if (data.changed_entities) {
      for (const entity of data.changed_entities) {
        this.entities.set(entity.entity_id, entity);
      }
    }
    
    // Remove despawned entities
    if (data.removed_entities) {
      for (const entityId of data.removed_entities) {
        this.entities.delete(entityId);
      }
    }
    
    // Update changed tiles
    if (data.changed_tiles) {
      for (const [key, tile] of Object.entries(data.changed_tiles)) {
        this.worldTiles.set(key, tile);
      }
    }
    
    // Process events
    if (data.events) {
      for (const event of data.events) {
        // Events are already handled by their specific message types
        console.log('Event:', event);
      }
    }
    
    if (this.callbacks.onStateUpdate) {
      this.callbacks.onStateUpdate({
        tick: data.tick,
        entities: this.entities,
        tiles: this.worldTiles
      });
    }
  }
  
  // ============================================================================
  // Entity Events
  // ============================================================================
  
  handleEntitySpawn(data) {
    this.entities.set(data.entity_id, data);
    
    if (this.callbacks.onEntitySpawn) {
      this.callbacks.onEntitySpawn(data);
    }
  }
  
  handleEntityDespawn(data) {
    this.entities.delete(data.entity_id);
    
    if (this.callbacks.onEntityDespawn) {
      this.callbacks.onEntityDespawn(data.entity_id);
    }
  }
  
  handleEntityUpdate(data) {
    const existing = this.entities.get(data.entity_id) || {};
    this.entities.set(data.entity_id, { ...existing, ...data });
    
    if (this.callbacks.onEntityUpdate) {
      this.callbacks.onEntityUpdate(data);
    }
  }
  
  // ============================================================================
  // Combat Events
  // ============================================================================
  
  handleDamage(data) {
    console.log(`Damage: ${data.source_id} -> ${data.target_id} for ${data.amount}`);
    
    // Update entity HP
    const entity = this.entities.get(data.target_id);
    if (entity) {
      entity.hp = data.current_hp;
      entity.max_hp = data.max_hp;
    }
    
    if (this.callbacks.onDamage) {
      this.callbacks.onDamage(data);
    }
  }
  
  handleDeath(data) {
    console.log(`Death: ${data.entity_name} killed by ${data.killer_name}`);
    
    if (this.callbacks.onDeath) {
      this.callbacks.onDeath(data);
    }
  }
  
  handleLevelUp(data) {
    console.log(`Level up: Entity ${data.entity_id} -> Level ${data.new_level}`);
    
    if (this.callbacks.onLevelUp) {
      this.callbacks.onLevelUp(data);
    }
  }
  
  // ============================================================================
  // Chat & Messages
  // ============================================================================
  
  handleChatReceive(data) {
    console.log(`[${data.channel}] ${data.sender_name}: ${data.message}`);
    
    if (this.callbacks.onChat) {
      this.callbacks.onChat(data);
    }
  }
  
  handleSystemMessage(data) {
    console.log(`[System] ${data.message}`);
    
    if (this.callbacks.onSystemMessage) {
      this.callbacks.onSystemMessage(data);
    }
  }
  
  handleServerError(data) {
    console.error(`Server error [${data.code}]: ${data.message}`);
    
    if (this.callbacks.onError) {
      this.callbacks.onError(data);
    }
  }
  
  // ============================================================================
  // Ping/Latency
  // ============================================================================
  
  handlePong(data) {
    if (data.client_ts) {
      this.latency = (Date.now() / 1000 - data.client_ts) * 1000;
    }
  }
  
  startPing() {
    if (this.pingIntervalId) return;
    
    this.pingIntervalId = setInterval(() => {
      if (this.connected) {
        this.lastPingTime = Date.now();
        this.send('ping', { ts: this.lastPingTime / 1000 });
      }
    }, this.options.pingInterval);
  }
  
  getLatency() {
    return Math.round(this.latency);
  }
  
  // ============================================================================
  // Player Actions
  // ============================================================================
  
  move(dx, dy, dz = 0) {
    return this.send('player_move', { dx, dy, dz });
  }
  
  attack(targetId) {
    return this.send('player_attack', { target_id: targetId });
  }
  
  interact(targetId = null, x = null, y = null, z = null) {
    return this.send('player_interact', { 
      target_id: targetId,
      target_x: x,
      target_y: y,
      target_z: z
    });
  }
  
  pickupItem() {
    return this.send('inventory_pickup', {});
  }
  
  dropItem(itemId, count = 1) {
    return this.send('inventory_drop', { item_id: itemId, count });
  }
  
  useItem(itemId) {
    return this.send('inventory_use', { item_id: itemId });
  }
  
  equipItem(itemId) {
    return this.send('inventory_equip', { item_id: itemId });
  }
  
  chat(message, channel = 'local') {
    return this.send('chat_send', { message, channel });
  }
  
  requestFullState() {
    return this.send('request_state', {});
  }
  
  // ============================================================================
  // State Getters
  // ============================================================================
  
  isConnected() {
    return this.connected;
  }
  
  isConnecting() {
    return this.connecting;
  }
  
  getPlayerId() {
    return this.playerId;
  }
  
  getPlayerName() {
    return this.playerName;
  }
  
  getPlayer() {
    return this.playerId ? this.entities.get(this.playerId) : null;
  }
  
  getEntity(entityId) {
    return this.entities.get(entityId);
  }
  
  getEntities() {
    return this.entities;
  }
  
  getTile(x, y, z) {
    return this.worldTiles.get(`${x},${y},${z}`);
  }
  
  getTiles() {
    return this.worldTiles;
  }
  
  getCurrentTick() {
    return this.currentTick;
  }
}
