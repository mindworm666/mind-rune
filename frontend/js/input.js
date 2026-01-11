/**
 * Mind Rune - Input Handler
 * 
 * Manages all keyboard and mouse input:
 * - Keyboard input with configurable keybinds
 * - Mouse input for clicking tiles/entities
 * - Input modes (normal, chat, menu)
 * - Command buffering
 * - Input prevention/handling
 */

export class InputHandler {
  constructor(options = {}) {
    this.options = options;
    
    // Input mode
    this.mode = 'normal'; // 'normal', 'chat', 'menu', 'targeting'
    
    // Key state tracking
    this.keysDown = new Set();
    this.keysPressed = new Set(); // Keys pressed this frame
    this.keysReleased = new Set(); // Keys released this frame
    
    // Mouse state
    this.mouseX = 0;
    this.mouseY = 0;
    this.mouseDown = false;
    this.mouseButton = -1;
    
    // Command queue
    this.commandQueue = [];
    
    // Callbacks
    this.callbacks = {
      onMove: options.onMove || null,
      onAction: options.onAction || null,
      onClick: options.onClick || null,
      onChat: options.onChat || null,
      onCommand: options.onCommand || null
    };
    
    // Keybindings
    this.keybinds = new Keybindings();
    
    // Initialize
    this.setupEventListeners();
  }
  
  setupEventListeners() {
    // Keyboard events
    window.addEventListener('keydown', (e) => this.handleKeyDown(e));
    window.addEventListener('keyup', (e) => this.handleKeyUp(e));
    
    // Mouse events
    window.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    window.addEventListener('mousedown', (e) => this.handleMouseDown(e));
    window.addEventListener('mouseup', (e) => this.handleMouseUp(e));
    window.addEventListener('click', (e) => this.handleClick(e));
    
    // Prevent context menu
    window.addEventListener('contextmenu', (e) => {
      if (this.options.preventContextMenu !== false) {
        e.preventDefault();
      }
    });
    
    // Prevent default for game keys
    window.addEventListener('keydown', (e) => {
      if (this.shouldPreventDefault(e.key, e)) {
        e.preventDefault();
      }
    });
  }
  
  handleKeyDown(e) {
    const key = e.key.toLowerCase();
    
    // Track key state
    if (!this.keysDown.has(key)) {
      this.keysPressed.add(key);
    }
    this.keysDown.add(key);
    
    // Mode-specific handling
    if (this.mode === 'chat') {
      // Let chat input handle it
      return;
    }
    
    if (this.mode === 'menu') {
      this.handleMenuInput(key, e);
      return;
    }
    
    // Normal mode - process keybinds
    this.processKeybind(key, e);
  }
  
  handleKeyUp(e) {
    const key = e.key.toLowerCase();
    this.keysDown.delete(key);
    this.keysReleased.add(key);
  }
  
  handleMouseMove(e) {
    this.mouseX = e.clientX;
    this.mouseY = e.clientY;
  }
  
  handleMouseDown(e) {
    this.mouseDown = true;
    this.mouseButton = e.button;
  }
  
  handleMouseUp(e) {
    this.mouseDown = false;
  }
  
  handleClick(e) {
    if (this.mode === 'chat') return;
    
    // Get canvas element to convert coordinates
    const canvas = document.getElementById('game-canvas');
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const canvasX = e.clientX - rect.left;
    const canvasY = e.clientY - rect.top;
    
    if (this.callbacks.onClick) {
      this.callbacks.onClick({
        canvasX,
        canvasY,
        button: e.button,
        shiftKey: e.shiftKey,
        ctrlKey: e.ctrlKey
      });
    }
  }
  
  processKeybind(key, event) {
    const action = this.keybinds.getAction(key, {
      shift: event.shiftKey,
      ctrl: event.ctrlKey,
      alt: event.altKey
    });
    
    if (!action) return;
    
    // Movement
    if (action.type === 'move') {
      if (this.callbacks.onMove) {
        this.callbacks.onMove(action.direction);
      }
    }
    
    // Actions
    else if (action.type === 'action') {
      if (this.callbacks.onAction) {
        this.callbacks.onAction(action.action);
      }
    }
    
    // UI toggles
    else if (action.type === 'ui') {
      this.handleUIAction(action.ui);
    }
    
    // Chat
    else if (action.type === 'chat') {
      if (this.callbacks.onChat) {
        this.callbacks.onChat();
      }
    }
    
    // Hotbar
    else if (action.type === 'hotbar') {
      this.queueCommand({
        type: 'use_hotbar',
        slot: action.slot
      });
    }
  }
  
  handleUIAction(uiAction) {
    switch (uiAction) {
      case 'inventory':
        this.queueCommand({ type: 'toggle_inventory' });
        break;
      case 'character':
        this.queueCommand({ type: 'toggle_character' });
        break;
      case 'map':
        this.queueCommand({ type: 'toggle_map' });
        break;
      case 'help':
        this.queueCommand({ type: 'show_help' });
        break;
      case 'menu':
        this.queueCommand({ type: 'toggle_menu' });
        break;
    }
  }
  
  handleMenuInput(key, event) {
    // Handle menu navigation
    if (key === 'escape') {
      this.setMode('normal');
      this.queueCommand({ type: 'close_menu' });
    } else if (key === 'arrowup' || key === 'w') {
      this.queueCommand({ type: 'menu_up' });
    } else if (key === 'arrowdown' || key === 's') {
      this.queueCommand({ type: 'menu_down' });
    } else if (key === 'enter' || key === ' ') {
      this.queueCommand({ type: 'menu_select' });
    }
  }
  
  shouldPreventDefault(key, event) {
    // Don't prevent if in chat mode
    if (this.mode === 'chat') return false;
    
    // Prevent arrow keys
    if (key.startsWith('Arrow')) return true;
    
    // Prevent space
    if (key === ' ') return true;
    
    // Prevent tab
    if (key === 'Tab') return true;
    
    // Allow F-keys for browser functions
    if (key.startsWith('F') && key.length > 1) {
      // Allow F5 (refresh), F11 (fullscreen), F12 (devtools)
      if (key === 'F5' || key === 'F11' || key === 'F12') return false;
      return true;
    }
    
    return false;
  }
  
  queueCommand(command) {
    this.commandQueue.push(command);
    
    if (this.callbacks.onCommand) {
      this.callbacks.onCommand(command);
    }
  }
  
  getCommands() {
    const commands = [...this.commandQueue];
    this.commandQueue = [];
    return commands;
  }
  
  update() {
    // Clear per-frame key tracking
    this.keysPressed.clear();
    this.keysReleased.clear();
  }
  
  setMode(mode) {
    this.mode = mode;
  }
  
  getMode() {
    return this.mode;
  }
  
  isKeyDown(key) {
    return this.keysDown.has(key.toLowerCase());
  }
  
  isKeyPressed(key) {
    return this.keysPressed.has(key.toLowerCase());
  }
  
  isKeyReleased(key) {
    return this.keysReleased.has(key.toLowerCase());
  }
  
  getMousePosition() {
    return { x: this.mouseX, y: this.mouseY };
  }
  
  isMouseDown() {
    return this.mouseDown;
  }
  
  setCallback(name, callback) {
    if (this.callbacks.hasOwnProperty(name)) {
      this.callbacks[name] = callback;
    }
  }
  
  destroy() {
    // Remove event listeners if needed
  }
}

/**
 * Keybindings configuration
 */
export class Keybindings {
  constructor() {
    this.bindings = this.getDefaultBindings();
  }
  
  getDefaultBindings() {
    return {
      // Movement
      'w': { type: 'move', direction: { x: 0, y: -1 } },
      'a': { type: 'move', direction: { x: -1, y: 0 } },
      's': { type: 'move', direction: { x: 0, y: 1 } },
      'd': { type: 'move', direction: { x: 1, y: 0 } },
      'arrowup': { type: 'move', direction: { x: 0, y: -1 } },
      'arrowleft': { type: 'move', direction: { x: -1, y: 0 } },
      'arrowdown': { type: 'move', direction: { x: 0, y: 1 } },
      'arrowright': { type: 'move', direction: { x: 1, y: 0 } },
      
      // Diagonal movement
      'q': { type: 'move', direction: { x: -1, y: -1 } },
      'e': { type: 'move', direction: { x: 1, y: -1 } },
      'z': { type: 'move', direction: { x: -1, y: 1 } },
      'c': { type: 'move', direction: { x: 1, y: 1 } },
      
      // Actions
      ' ': { type: 'action', action: 'interact' },
      'g': { type: 'action', action: 'pickup' },
      'f': { type: 'action', action: 'auto_attack_toggle' },
      'r': { type: 'action', action: 'target_nearest' },
      'tab': { type: 'action', action: 'cycle_target' },
      
      // UI
      'i': { type: 'ui', ui: 'inventory' },
      'c': { type: 'ui', ui: 'character' },
      'm': { type: 'ui', ui: 'map' },
      'escape': { type: 'ui', ui: 'menu' },
      'h': { type: 'ui', ui: 'help' },
      
      // Chat
      't': { type: 'chat' },
      'enter': { type: 'chat' },
      
      // Hotbar (1-9)
      '1': { type: 'hotbar', slot: 0 },
      '2': { type: 'hotbar', slot: 1 },
      '3': { type: 'hotbar', slot: 2 },
      '4': { type: 'hotbar', slot: 3 },
      '5': { type: 'hotbar', slot: 4 },
      '6': { type: 'hotbar', slot: 5 },
      '7': { type: 'hotbar', slot: 6 },
      '8': { type: 'hotbar', slot: 7 },
      '9': { type: 'hotbar', slot: 8 },
      
      // Z-level movement
      '<': { type: 'action', action: 'ascend' },
      '>': { type: 'action', action: 'descend' },
      'pageup': { type: 'action', action: 'ascend' },
      'pagedown': { type: 'action', action: 'descend' },
    };
  }
  
  getAction(key, modifiers = {}) {
    // Check for modifier combinations first
    if (modifiers.shift && this.bindings[`shift+${key}`]) {
      return this.bindings[`shift+${key}`];
    }
    if (modifiers.ctrl && this.bindings[`ctrl+${key}`]) {
      return this.bindings[`ctrl+${key}`];
    }
    if (modifiers.alt && this.bindings[`alt+${key}`]) {
      return this.bindings[`alt+${key}`];
    }
    
    // Check for basic key
    return this.bindings[key] || null;
  }
  
  setBinding(key, action) {
    this.bindings[key] = action;
  }
  
  removeBinding(key) {
    delete this.bindings[key];
  }
  
  getBindings() {
    return { ...this.bindings };
  }
  
  loadBindings(bindings) {
    this.bindings = { ...this.getDefaultBindings(), ...bindings };
  }
  
  resetToDefaults() {
    this.bindings = this.getDefaultBindings();
  }
  
  exportBindings() {
    return JSON.stringify(this.bindings, null, 2);
  }
  
  importBindings(json) {
    try {
      const bindings = JSON.parse(json);
      this.loadBindings(bindings);
      return true;
    } catch (e) {
      console.error('Failed to import keybindings:', e);
      return false;
    }
  }
}
