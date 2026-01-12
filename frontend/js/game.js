/**
 * Mind Rune - Main Game Client
 * 
 * Ties everything together:
 * - Initialization
 * - Game loop (60 FPS)
 * - Input -> Network -> State -> Render pipeline
 * - Scene management
 * - Login/Auth flow
 */

import { Renderer } from './renderer.js';
import { InputHandler } from './input.js';
import { NetworkClient } from './network.js';
import { StateManager } from './state-manager.js';
import {
  StatusPanel,
  MessageLog,
  InventoryPanel,
  Minimap,
  CharacterSheet,
  ChatInput
} from './components/ui-components.js';

export class Game {
  constructor(options = {}) {
    this.options = {
      ...options,
      targetFPS: options.targetFPS || 60,
      serverUrl: options.serverUrl || 'ws://localhost:8765',
      canvasId: options.canvasId || 'game-canvas'
    };
    
    // Core systems
    this.renderer = null;
    this.input = null;
    this.network = null;
    this.state = null;
    
    // UI components
    this.ui = {
      statusPanel: null,
      messageLog: null,
      inventoryPanel: null,
      minimap: null,
      characterSheet: null,
      chatInput: null,
      loginForm: null
    };
    
    // Game loop
    this.running = false;
    this.lastFrameTime = 0;
    this.deltaTime = 0;
    this.frameCount = 0;
    this.fps = 0;
    
    // Scene
    this.currentScene = 'loading'; // 'loading', 'login', 'game', 'death'
    
    // Debug
    this.debug = {
      enabled: true,
      showFPS: true,
      showLatency: true,
      showEntityCount: true,
      showPosition: true
    };
  }
  
  async initialize() {
    try {
      console.log('Initializing Mind Rune...');
      
      // Initialize state manager
      this.state = new StateManager();
      
      // Initialize renderer
      this.renderer = new Renderer(this.options.canvasId, {
        viewportWidth: 80,
        viewportHeight: 40,
        font: '16px "IBM Plex Mono", monospace',
        charWidth: 10,
        charHeight: 20
      });
      
      // Initialize input handler
      this.input = new InputHandler({
        onMove: (direction) => this.handleMove(direction),
        onAction: (action) => this.handleAction(action),
        onClick: (data) => this.handleClick(data),
        onChat: () => this.handleChatActivate(),
        onCommand: (cmd) => this.handleCommand(cmd)
      });
      
      // Initialize network client
      this.network = new NetworkClient({
        url: this.options.serverUrl,
        onConnect: () => this.handleConnect(),
        onDisconnect: (event) => this.handleDisconnect(event),
        onAuthSuccess: (data) => this.handleAuthSuccess(data),
        onAuthFailure: (reason) => this.handleAuthFailure(reason),
        onGameState: (state) => this.handleGameState(state),
        onStateUpdate: (state) => this.handleStateUpdate(state),
        onEntitySpawn: (data) => this.handleEntitySpawn(data),
        onEntityDespawn: (id) => this.handleEntityDespawn(id),
        onEntityUpdate: (data) => this.handleEntityUpdate(data),
        onDamage: (data) => this.handleDamage(data),
        onDeath: (data) => this.handleDeath(data),
        onLevelUp: (data) => this.handleLevelUp(data),
        onChat: (data) => this.handleChatReceive(data),
        onSystemMessage: (data) => this.handleSystemMessage(data),
        onError: (error) => this.handleNetworkError(error)
      });
      
      // Initialize UI components
      this.initializeUI();
      
      // Enable CRT effects
      document.body.setAttribute('data-crt', 'true');
      
      console.log('Initialization complete!');
      return true;
      
    } catch (error) {
      console.error('Failed to initialize:', error);
      this.showError('Initialization failed: ' + error.message);
      return false;
    }
  }
  
  initializeUI() {
    // Create login form
    this.createLoginForm();
    
    // Status panel
    this.ui.statusPanel = new StatusPanel('status-panel');
    
    // Message log
    this.ui.messageLog = new MessageLog('message-log', {
      maxMessages: 1000
    });
    
    // Inventory panel
    this.ui.inventoryPanel = new InventoryPanel('inventory-panel', {
      slots: 20
    });
    this.ui.inventoryPanel.hide();
    
    // Minimap
    this.ui.minimap = new Minimap('minimap-container', {
      size: 16,
      zoom: 1
    });
    
    // Character sheet
    this.ui.characterSheet = new CharacterSheet('character-sheet-overlay');
    
    // Chat input
    this.ui.chatInput = new ChatInput('chat-container', {
      onSubmit: (msg) => this.sendChat(msg)
    });
  }
  
  createLoginForm() {
    // Create login overlay
    const overlay = document.createElement('div');
    overlay.id = 'login-overlay';
    overlay.className = 'login-overlay';
    overlay.innerHTML = `
      <div class="login-form crt-panel">
        <h1 class="game-title">MIND RUNE</h1>
        <p class="tagline">A Real-Time Roguelike Adventure</p>
        
        <div class="form-group">
          <label for="username">Username</label>
          <input type="text" id="login-username" autocomplete="off" placeholder="Enter username">
        </div>
        
        <div class="form-group">
          <label for="password">Password</label>
          <input type="password" id="login-password" placeholder="Enter password">
        </div>
        
        <div class="button-group">
          <button id="login-btn" class="btn primary">LOGIN</button>
          <button id="register-btn" class="btn secondary">REGISTER</button>
        </div>
        
        <div id="login-status" class="login-status"></div>
        
        <div class="help-text">
          <p>Test accounts: test/test, player1/password1</p>
        </div>
      </div>
    `;
    
    document.body.appendChild(overlay);
    
    // Add styles
    const style = document.createElement('style');
    style.textContent = `
      .login-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.9);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
      }
      
      .login-overlay.hidden {
        display: none;
      }
      
      .login-form {
        background: #0a0a0a;
        border: 2px solid #33ff33;
        padding: 40px;
        min-width: 350px;
        text-align: center;
        box-shadow: 0 0 30px rgba(51, 255, 51, 0.3);
      }
      
      .game-title {
        color: #33ff33;
        font-size: 48px;
        margin: 0;
        text-shadow: 0 0 20px #33ff33;
        font-family: 'IBM Plex Mono', monospace;
        letter-spacing: 8px;
      }
      
      .tagline {
        color: #666;
        margin: 10px 0 30px;
        font-size: 14px;
      }
      
      .form-group {
        margin: 15px 0;
        text-align: left;
      }
      
      .form-group label {
        display: block;
        color: #33ff33;
        margin-bottom: 5px;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 2px;
      }
      
      .form-group input {
        width: 100%;
        padding: 12px;
        background: #0a0a0a;
        border: 1px solid #33ff33;
        color: #33ff33;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 16px;
        outline: none;
        box-sizing: border-box;
      }
      
      .form-group input:focus {
        border-color: #66ff66;
        box-shadow: 0 0 10px rgba(51, 255, 51, 0.3);
      }
      
      .button-group {
        margin: 25px 0 15px;
        display: flex;
        gap: 10px;
      }
      
      .btn {
        flex: 1;
        padding: 12px;
        border: none;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 14px;
        cursor: pointer;
        text-transform: uppercase;
        letter-spacing: 2px;
        transition: all 0.2s;
      }
      
      .btn.primary {
        background: #33ff33;
        color: #000;
      }
      
      .btn.primary:hover {
        background: #66ff66;
        box-shadow: 0 0 20px rgba(51, 255, 51, 0.5);
      }
      
      .btn.secondary {
        background: transparent;
        color: #33ff33;
        border: 1px solid #33ff33;
      }
      
      .btn.secondary:hover {
        background: rgba(51, 255, 51, 0.1);
      }
      
      .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      
      .login-status {
        min-height: 20px;
        color: #ff3333;
        font-size: 14px;
        margin: 10px 0;
      }
      
      .login-status.success {
        color: #33ff33;
      }
      
      .help-text {
        color: #444;
        font-size: 12px;
        margin-top: 20px;
      }
    `;
    document.head.appendChild(style);
    
    // Event listeners
    document.getElementById('login-btn').addEventListener('click', () => this.doLogin());
    document.getElementById('register-btn').addEventListener('click', () => this.doRegister());
    
    // Enter key to login
    document.getElementById('login-password').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.doLogin();
    });
    document.getElementById('login-username').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') document.getElementById('login-password').focus();
    });
    
    this.ui.loginForm = overlay;
  }
  
  doLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const status = document.getElementById('login-status');
    
    if (!username || !password) {
      status.textContent = 'Please enter username and password';
      status.className = 'login-status';
      return;
    }
    
    status.textContent = 'Connecting...';
    status.className = 'login-status';
    
    // Connect and login
    if (!this.network.isConnected()) {
      this.network.connect();
      // Wait for connection, then login
      this._pendingLogin = { username, password };
    } else {
      this.network.login(username, password);
    }
  }
  
  doRegister() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const status = document.getElementById('login-status');
    
    if (!username || !password) {
      status.textContent = 'Please enter username and password';
      return;
    }
    
    if (username.length < 3) {
      status.textContent = 'Username must be at least 3 characters';
      return;
    }
    
    if (password.length < 4) {
      status.textContent = 'Password must be at least 4 characters';
      return;
    }
    
    status.textContent = 'Registering...';
    
    if (!this.network.isConnected()) {
      this.network.connect();
      this._pendingRegister = { username, password };
    } else {
      this.network.register(username, password);
    }
  }
  
  async start() {
    const initialized = await this.initialize();
    if (!initialized) return;
    
    // Start game loop
    this.running = true;
    this.lastFrameTime = performance.now();
    this.gameLoop();
    
    // Show login scene
    this.setScene('login');
    this.ui.messageLog.addMessage('Mind Rune initialized', 'system');
    this.ui.messageLog.addMessage('Welcome! Please login to play.', 'system');
  }
  
  stop() {
    this.running = false;
    if (this.network) {
      this.network.disconnect();
    }
  }
  
  gameLoop() {
    if (!this.running) return;
    
    const now = performance.now();
    this.deltaTime = (now - this.lastFrameTime) / 1000;
    this.lastFrameTime = now;
    
    // Update
    this.update(this.deltaTime);
    
    // Render
    this.render();
    
    // Update FPS counter
    this.frameCount++;
    if (this.frameCount % 60 === 0) {
      this.fps = Math.round(1 / this.deltaTime);
    }
    
    requestAnimationFrame(() => this.gameLoop());
  }
  
  update(deltaTime) {
    // Update input
    if (this.input) {
      this.input.update();
    }
    
    // Update viewport
    if (this.renderer && this.currentScene === 'game') {
      const player = this.network.getPlayer();
      if (player) {
        this.renderer.viewport.setTarget(player.x, player.y);
        this.renderer.viewport.setZLevel(player.z);
        this.renderer.viewport.update(deltaTime);
      }
    }
    
    // Update effects
    this.updateEffects(deltaTime);
    
    // Update UI
    this.updateUI();
  }
  
  render() {
    if (!this.renderer) return;
    
    if (this.currentScene === 'game') {
      // Render game world
      const gameState = {
        entities: this.network.getEntities(),
        tiles: this.network.getTiles(),
        player: this.network.getPlayer(),
        effects: this.state.effects
      };
      
      this.renderer.render(gameState, this.network.getPlayer());
      
      // Render debug info
      if (this.debug.enabled) {
        this.renderDebugInfo();
      }
    }
  }
  
  updateUI() {
    const player = this.network.getPlayer();
    
    // Update status panel
    if (this.ui.statusPanel && player) {
      this.ui.statusPanel.update({
        hp: player.hp,
        maxHp: player.max_hp,
        mp: 50, // TODO: Get from player
        maxMp: 50,
        level: player.level || 1,
        name: player.name
      });
    }
    
    // Update minimap
    if (this.ui.minimap && player) {
      this.ui.minimap.update(
        { tiles: this.network.getTiles(), entities: this.network.getEntities() },
        { x: player.x, y: player.y, z: player.z }
      );
    }
  }
  
  updateEffects(deltaTime) {
    const effects = this.state.effects;
    for (let i = effects.length - 1; i >= 0; i--) {
      const effect = effects[i];
      effect.age = (effect.age || 0) + deltaTime * 60;
      
      if (effect.age > effect.maxAge) {
        effects.splice(i, 1);
      }
    }
  }
  
  // ============================================================================
  // Input Handlers
  // ============================================================================
  
  handleMove(direction) {
    if (this.currentScene !== 'game') return;
    if (!this.network.isConnected()) return;
    
    this.network.move(direction.x, direction.y, 0);
  }
  
  handleAction(action) {
    if (this.currentScene !== 'game') return;
    
    switch (action) {
      case 'interact':
        this.interact();
        break;
      case 'pickup':
        this.pickup();
        break;
      case 'attack':
        this.attackTarget();
        break;
      case 'ascend':
        this.changeZLevel(1);
        break;
      case 'descend':
        this.changeZLevel(-1);
        break;
    }
  }
  
  handleClick(data) {
    if (this.currentScene !== 'game') return;
    
    const worldPos = this.renderer.screenToWorld(data.canvasX, data.canvasY);
    this.ui.messageLog.addMessage(`Clicked: (${worldPos.x}, ${worldPos.y})`, 'system', false);
  }
  
  handleChatActivate() {
    if (this.ui.chatInput.isActive()) {
      this.ui.chatInput.deactivate();
      this.input.setMode('normal');
    } else {
      this.ui.chatInput.activate();
      this.input.setMode('chat');
    }
  }
  
  handleCommand(cmd) {
    switch (cmd.type) {
      case 'toggle_inventory':
        this.ui.inventoryPanel.toggle();
        break;
      case 'toggle_character':
        this.ui.characterSheet.toggle();
        break;
      case 'toggle_map':
        this.ui.minimap.toggle();
        break;
      case 'show_help':
        this.showHelp();
        break;
      case 'toggle_debug':
        this.toggleDebug();
        break;
    }
  }
  
  // ============================================================================
  // Network Handlers
  // ============================================================================
  
  handleConnect() {
    console.log('Connected to server');
    const status = document.getElementById('login-status');
    if (status) {
      status.textContent = 'Connected! Authenticating...';
      status.className = 'login-status success';
    }
    
    // Handle pending login/register
    if (this._pendingLogin) {
      this.network.login(this._pendingLogin.username, this._pendingLogin.password);
      this._pendingLogin = null;
    } else if (this._pendingRegister) {
      this.network.register(this._pendingRegister.username, this._pendingRegister.password);
      this._pendingRegister = null;
    }
  }
  
  handleDisconnect(event) {
    console.log('Disconnected from server:', event);
    
    if (this.currentScene === 'game') {
      this.ui.messageLog.addMessage('Connection lost. Reconnecting...', 'error');
    }
    
    const status = document.getElementById('login-status');
    if (status) {
      status.textContent = 'Disconnected from server';
      status.className = 'login-status';
    }
  }
  
  handleAuthSuccess(data) {
    console.log('Auth success:', data);
    
    // Hide login form
    if (this.ui.loginForm) {
      this.ui.loginForm.classList.add('hidden');
    }
    
    // Switch to game scene
    this.setScene('game');
    
    this.ui.messageLog.addMessage(`Welcome, ${data.character_name}!`, 'system');
    this.ui.messageLog.addMessage('Use WASD or arrow keys to move.', 'system');
    this.ui.messageLog.addMessage('Press H for help.', 'system');
  }
  
  handleAuthFailure(reason) {
    console.log('Auth failure:', reason);
    
    const status = document.getElementById('login-status');
    if (status) {
      status.textContent = reason;
      status.className = 'login-status';
    }
  }
  
  handleGameState(state) {
    console.log('Received game state:', state);
    this.ui.messageLog.addMessage('Game state received', 'system', false);
  }
  
  handleStateUpdate(state) {
    // State updates are handled automatically by network client
  }
  
  handleEntitySpawn(data) {
    this.ui.messageLog.addMessage(`${data.name} appeared`, 'system', false);
  }
  
  handleEntityDespawn(entityId) {
    // Entity removed
  }
  
  handleEntityUpdate(data) {
    // Entity updated
  }
  
  handleDamage(data) {
    const targetName = this.network.getEntity(data.target_id)?.name || 'target';
    const sourceName = data.source_id ? (this.network.getEntity(data.source_id)?.name || 'something') : 'something';
    
    this.ui.messageLog.addMessage(
      `${sourceName} dealt ${data.amount} damage to ${targetName}`,
      'damage'
    );
    
    // Add visual effect
    const target = this.network.getEntity(data.target_id);
    if (target) {
      this.state.effects.push({
        type: 'damage',
        position: { x: target.x, y: target.y },
        value: data.amount,
        age: 0,
        maxAge: 60
      });
    }
  }
  
  handleDeath(data) {
    this.ui.messageLog.addMessage(
      `${data.entity_name} was slain${data.killer_name ? ` by ${data.killer_name}` : ''}!`,
      'combat'
    );
    
    // Check if player died
    if (data.entity_id === this.network.getPlayerId()) {
      this.handlePlayerDeath();
    }
  }
  
  handleLevelUp(data) {
    this.ui.messageLog.addMessage(
      `Level up! You are now level ${data.new_level}!`,
      'important'
    );
  }
  
  handleChatReceive(data) {
    this.ui.messageLog.addMessage(
      `[${data.channel}] ${data.sender_name}: ${data.message}`,
      'chat'
    );
  }
  
  handleSystemMessage(data) {
    this.ui.messageLog.addMessage(data.message, data.level === 'error' ? 'error' : 'system');
  }
  
  handleNetworkError(error) {
    console.error('Network error:', error);
    this.ui.messageLog.addMessage(`Error: ${error.message}`, 'error');
  }
  
  // ============================================================================
  // Actions
  // ============================================================================
  
  interact() {
    this.network.interact();
    this.ui.messageLog.addMessage('Interacting...', 'system', false);
  }
  
  pickup() {
    this.network.pickupItem();
    this.ui.messageLog.addMessage('Picking up item...', 'system', false);
  }
  
  attackTarget() {
    // TODO: Attack selected target
    this.ui.messageLog.addMessage('Attacking...', 'system', false);
  }
  
  changeZLevel(delta) {
    // TODO: Check for stairs
    this.network.move(0, 0, delta);
  }
  
  sendChat(message) {
    if (!message.trim()) return;
    this.network.chat(message);
    this.ui.chatInput.clear();
  }
  
  // ============================================================================
  // Scene Management
  // ============================================================================
  
  setScene(scene) {
    this.currentScene = scene;
    console.log('Scene changed to:', scene);
    
    if (scene === 'game') {
      this.ui.statusPanel.show();
      this.ui.messageLog.show();
      this.ui.minimap.show();
      if (this.ui.loginForm) {
        this.ui.loginForm.classList.add('hidden');
      }
    } else if (scene === 'login') {
      this.ui.statusPanel.hide();
      this.ui.inventoryPanel.hide();
      if (this.ui.loginForm) {
        this.ui.loginForm.classList.remove('hidden');
      }
    }
  }
  
  handlePlayerDeath() {
    this.ui.messageLog.addMessage('You have died! Respawning...', 'error');
    // TODO: Show death screen, respawn
  }
  
  // ============================================================================
  // Utilities
  // ============================================================================
  
  showHelp() {
    this.ui.messageLog.addMessage('=== CONTROLS ===', 'system');
    this.ui.messageLog.addMessage('WASD / Arrows - Move', 'system');
    this.ui.messageLog.addMessage('Space - Interact', 'system');
    this.ui.messageLog.addMessage('G - Pick up item', 'system');
    this.ui.messageLog.addMessage('I - Inventory', 'system');
    this.ui.messageLog.addMessage('C - Character sheet', 'system');
    this.ui.messageLog.addMessage('M - Toggle map', 'system');
    this.ui.messageLog.addMessage('T - Chat', 'system');
    this.ui.messageLog.addMessage('H - Help', 'system');
    this.ui.messageLog.addMessage('F3 - Debug info', 'system');
    this.ui.messageLog.addMessage('< > - Use stairs', 'system');
  }
  
  showError(message) {
    console.error(message);
    if (this.ui.messageLog) {
      this.ui.messageLog.addMessage(message, 'error');
    }
  }
  
  toggleDebug() {
    this.debug.enabled = !this.debug.enabled;
    this.ui.messageLog.addMessage(
      `Debug mode: ${this.debug.enabled ? 'ON' : 'OFF'}`,
      'system'
    );
  }
  
  renderDebugInfo() {
    const ctx = this.renderer.ctx;
    const player = this.network.getPlayer();
    
    ctx.save();
    ctx.fillStyle = '#33ff33';
    ctx.font = '12px monospace';
    
    let y = 20;
    const lines = [];
    
    if (this.debug.showFPS) {
      lines.push(`FPS: ${this.fps}`);
    }
    if (this.debug.showLatency) {
      lines.push(`Latency: ${this.network.getLatency()}ms`);
    }
    if (this.debug.showEntityCount) {
      lines.push(`Entities: ${this.network.getEntities().size}`);
      lines.push(`Tiles: ${this.network.getTiles().size}`);
    }
    if (this.debug.showPosition && player) {
      lines.push(`Pos: (${player.x.toFixed(1)}, ${player.y.toFixed(1)}, ${player.z})`);
    }
    lines.push(`Tick: ${this.network.getCurrentTick()}`);
    
    lines.forEach((line, i) => {
      ctx.fillText(line, 10, y + i * 15);
    });
    
    ctx.restore();
  }
}
