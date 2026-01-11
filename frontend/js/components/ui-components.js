/**
 * Mind Rune - UI Components
 * 
 * Reusable terminal-style UI components:
 * - Status panels (HP/MP/XP)
 * - Message log
 * - Inventory panel
 * - Character sheet
 * - Minimap
 * 
 * All components use ASCII art and terminal aesthetics
 */

/**
 * Base UI Component
 */
export class UIComponent {
  constructor(container, options = {}) {
    this.container = typeof container === 'string' 
      ? document.getElementById(container)
      : container;
    
    if (!this.container) {
      throw new Error('Container element not found');
    }
    
    this.visible = options.visible !== false;
    this.dirty = true;
    this.options = options;
    
    this.initialize();
  }
  
  initialize() {
    // Override in subclass
  }
  
  update(state) {
    // Override in subclass
    this.dirty = true;
  }
  
  render() {
    if (!this.visible || !this.dirty) return;
    // Override in subclass
    this.dirty = false;
  }
  
  show() {
    this.visible = true;
    this.container.classList.remove('hidden');
    this.dirty = true;
  }
  
  hide() {
    this.visible = false;
    this.container.classList.add('hidden');
  }
  
  toggle() {
    if (this.visible) {
      this.hide();
    } else {
      this.show();
    }
  }
  
  markDirty() {
    this.dirty = true;
  }
  
  destroy() {
    if (this.container) {
      this.container.innerHTML = '';
    }
  }
}

/**
 * Status Panel - Shows HP, MP, XP, and stats
 */
export class StatusPanel extends UIComponent {
  initialize() {
    this.container.innerHTML = `
      <div class="status-panel">
        <div class="box-title">STATUS</div>
        <div class="box-content">
          <div class="progress-bar progress-bar-hp" id="hp-bar">
            <span class="progress-bar-label">HP</span>
            <div class="progress-bar-container">
              <div class="progress-bar-fill" style="width: 100%"></div>
              <span class="progress-bar-text">100/100</span>
            </div>
          </div>
          <div class="progress-bar progress-bar-mp" id="mp-bar">
            <span class="progress-bar-label">MP</span>
            <div class="progress-bar-container">
              <div class="progress-bar-fill" style="width: 100%"></div>
              <span class="progress-bar-text">100/100</span>
            </div>
          </div>
          <div class="progress-bar progress-bar-xp" id="xp-bar">
            <span class="progress-bar-label">XP</span>
            <div class="progress-bar-container">
              <div class="progress-bar-fill" style="width: 0%"></div>
              <span class="progress-bar-text">0/100</span>
            </div>
          </div>
          
          <div class="stats-grid" id="stats-grid">
            <div class="stat-item">
              <span class="stat-label">STR</span>
              <span class="stat-value">10</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">DEX</span>
              <span class="stat-value">10</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">INT</span>
              <span class="stat-value">10</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">VIT</span>
              <span class="stat-value">10</span>
            </div>
          </div>
          
          <div class="level-info" id="level-info">
            <div class="stat-item">
              <span class="stat-label">Level</span>
              <span class="stat-value">1</span>
            </div>
          </div>
        </div>
      </div>
    `;
    
    this.hpBar = this.container.querySelector('#hp-bar .progress-bar-fill');
    this.hpText = this.container.querySelector('#hp-bar .progress-bar-text');
    this.mpBar = this.container.querySelector('#mp-bar .progress-bar-fill');
    this.mpText = this.container.querySelector('#mp-bar .progress-bar-text');
    this.xpBar = this.container.querySelector('#xp-bar .progress-bar-fill');
    this.xpText = this.container.querySelector('#xp-bar .progress-bar-text');
    this.statsGrid = this.container.querySelector('#stats-grid');
    this.levelInfo = this.container.querySelector('#level-info');
  }
  
  update(playerState) {
    if (!playerState || !playerState.stats) return;
    
    const stats = playerState.stats;
    
    // Update HP
    const hpPercent = (stats.hp / stats.maxHp) * 100;
    this.hpBar.style.width = `${hpPercent}%`;
    this.hpText.textContent = `${stats.hp}/${stats.maxHp}`;
    
    // Update MP
    const mpPercent = (stats.mp / stats.maxMp) * 100;
    this.mpBar.style.width = `${mpPercent}%`;
    this.mpText.textContent = `${stats.mp}/${stats.maxMp}`;
    
    // Update XP
    const xpPercent = (stats.xp / stats.xpToLevel) * 100;
    this.xpBar.style.width = `${xpPercent}%`;
    this.xpText.textContent = `${stats.xp}/${stats.xpToLevel}`;
    
    // Update stats
    this.statsGrid.innerHTML = `
      <div class="stat-item">
        <span class="stat-label">STR</span>
        <span class="stat-value">${stats.strength || 10}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">DEX</span>
        <span class="stat-value">${stats.dexterity || 10}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">INT</span>
        <span class="stat-value">${stats.intelligence || 10}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">VIT</span>
        <span class="stat-value">${stats.vitality || 10}</span>
      </div>
    `;
    
    // Update level
    this.levelInfo.innerHTML = `
      <div class="stat-item">
        <span class="stat-label">Level</span>
        <span class="stat-value">${stats.level || 1}</span>
      </div>
    `;
    
    this.dirty = true;
  }
}

/**
 * Message Log - Shows combat messages, system notifications, chat
 */
export class MessageLog extends UIComponent {
  initialize() {
    this.maxMessages = this.options.maxMessages || 1000;
    this.messages = [];
    this.autoScroll = true;
    
    this.container.innerHTML = `
      <div class="message-log" id="message-log-content"></div>
    `;
    
    this.logContent = this.container.querySelector('#message-log-content');
    
    // Auto-scroll detection
    this.logContent.addEventListener('scroll', () => {
      const atBottom = this.logContent.scrollHeight - this.logContent.scrollTop <= this.logContent.clientHeight + 10;
      this.autoScroll = atBottom;
    });
  }
  
  addMessage(text, type = 'system', timestamp = true) {
    const message = {
      text,
      type,
      timestamp: timestamp ? new Date() : null,
      id: Date.now() + Math.random()
    };
    
    this.messages.push(message);
    
    // Trim old messages
    if (this.messages.length > this.maxMessages) {
      this.messages = this.messages.slice(-this.maxMessages);
    }
    
    this.appendMessage(message);
    
    if (this.autoScroll) {
      this.scrollToBottom();
    }
  }
  
  appendMessage(message) {
    const div = document.createElement('div');
    div.className = `message message-${message.type}`;
    
    let html = '';
    if (message.timestamp) {
      const time = message.timestamp.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit' 
      });
      html += `<span class="message-timestamp">[${time}]</span> `;
    }
    
    html += this.escapeHtml(message.text);
    div.innerHTML = html;
    
    this.logContent.appendChild(div);
  }
  
  clear() {
    this.messages = [];
    this.logContent.innerHTML = '';
  }
  
  scrollToBottom() {
    this.logContent.scrollTop = this.logContent.scrollHeight;
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  update(messages) {
    // Batch add new messages
    if (Array.isArray(messages)) {
      messages.forEach(msg => {
        if (typeof msg === 'string') {
          this.addMessage(msg);
        } else {
          this.addMessage(msg.text, msg.type, msg.timestamp);
        }
      });
    }
  }
}

/**
 * Inventory Panel - Shows items in grid/list
 */
export class InventoryPanel extends UIComponent {
  initialize() {
    this.selectedSlot = null;
    this.slots = this.options.slots || 20;
    
    this.container.innerHTML = `
      <div class="inventory-panel">
        <div class="box-title">INVENTORY</div>
        <div class="box-content">
          <div class="inventory-grid" id="inventory-grid"></div>
          <div class="inventory-details" id="inventory-details">
            <div class="muted">Select an item</div>
          </div>
        </div>
      </div>
    `;
    
    this.grid = this.container.querySelector('#inventory-grid');
    this.details = this.container.querySelector('#inventory-details');
    
    this.renderSlots();
  }
  
  renderSlots() {
    this.grid.innerHTML = '';
    
    for (let i = 0; i < this.slots; i++) {
      const slot = document.createElement('div');
      slot.className = 'inventory-slot';
      slot.dataset.slot = i;
      slot.innerHTML = `
        <div class="inventory-slot-bg">[ ]</div>
        <div class="inventory-slot-item"></div>
        <div class="inventory-slot-count"></div>
      `;
      
      slot.addEventListener('click', () => this.selectSlot(i));
      this.grid.appendChild(slot);
    }
  }
  
  update(inventory) {
    if (!inventory || !inventory.items) return;
    
    // Clear all slots
    const slots = this.grid.querySelectorAll('.inventory-slot');
    slots.forEach(slot => {
      slot.classList.remove('has-item');
      slot.querySelector('.inventory-slot-item').textContent = '';
      slot.querySelector('.inventory-slot-count').textContent = '';
    });
    
    // Fill slots with items
    inventory.items.forEach((item, index) => {
      if (index >= this.slots) return;
      
      const slot = slots[index];
      slot.classList.add('has-item');
      slot.querySelector('.inventory-slot-item').textContent = item.icon || '?';
      
      if (item.count > 1) {
        slot.querySelector('.inventory-slot-count').textContent = item.count;
      }
    });
    
    this.dirty = true;
  }
  
  selectSlot(index) {
    this.selectedSlot = index;
    
    // Update visual selection
    const slots = this.grid.querySelectorAll('.inventory-slot');
    slots.forEach((slot, i) => {
      if (i === index) {
        slot.classList.add('selected');
      } else {
        slot.classList.remove('selected');
      }
    });
    
    // Show item details (if item exists)
    // TODO: Get item data and display
    this.details.innerHTML = `<div class="muted">Slot ${index}</div>`;
  }
}

/**
 * Minimap - Shows local area overview
 */
export class Minimap extends UIComponent {
  initialize() {
    this.size = this.options.size || 16;
    this.zoom = this.options.zoom || 1;
    
    this.container.innerHTML = `
      <div class="minimap-panel">
        <div class="box-title">MAP</div>
        <div class="box-content">
          <canvas id="minimap-canvas" width="${this.size}" height="${this.size}"></canvas>
        </div>
      </div>
    `;
    
    this.canvas = this.container.querySelector('#minimap-canvas');
    this.ctx = this.canvas.getContext('2d');
    
    // Style canvas
    this.canvas.style.width = '100%';
    this.canvas.style.height = 'auto';
    this.canvas.style.imageRendering = 'pixelated';
  }
  
  update(worldState, playerPosition) {
    if (!playerPosition) return;
    
    this.ctx.fillStyle = '#000000';
    this.ctx.fillRect(0, 0, this.size, this.size);
    
    const halfSize = Math.floor(this.size / 2);
    
    // Draw tiles around player
    for (let dy = -halfSize; dy < halfSize; dy++) {
      for (let dx = -halfSize; dx < halfSize; dx++) {
        const worldX = playerPosition.x + dx;
        const worldY = playerPosition.y + dy;
        
        const tile = this.getTile(worldState, worldX, worldY, playerPosition.z);
        if (!tile) continue;
        
        const screenX = dx + halfSize;
        const screenY = dy + halfSize;
        
        const color = this.getTileColor(tile);
        this.ctx.fillStyle = color;
        this.ctx.fillRect(screenX, screenY, 1, 1);
      }
    }
    
    // Draw player in center
    this.ctx.fillStyle = '#33ff33';
    this.ctx.fillRect(halfSize, halfSize, 1, 1);
    
    this.dirty = true;
  }
  
  getTile(worldState, x, y, z) {
    // Same as renderer getTile logic
    if (worldState.getTile) {
      return worldState.getTile(x, y, z);
    }
    return null;
  }
  
  getTileColor(tile) {
    const colors = {
      'ground': '#669966',
      'grass': '#66aa66',
      'wall': '#888888',
      'water': '#3366ff',
      'mountain': '#999999',
      'tree': '#44aa44',
      'void': '#000000'
    };
    return colors[tile.type] || '#666666';
  }
}

/**
 * Character Sheet - Full stats display
 */
export class CharacterSheet extends UIComponent {
  initialize() {
    this.container.classList.add('character-sheet-overlay');
    this.container.innerHTML = `
      <div class="character-sheet box">
        <div class="box-title">CHARACTER</div>
        <div class="box-content">
          <div id="character-stats"></div>
          <button id="close-character">Close [C]</button>
        </div>
      </div>
    `;
    
    this.statsDiv = this.container.querySelector('#character-stats');
    this.closeBtn = this.container.querySelector('#close-character');
    
    this.closeBtn.addEventListener('click', () => this.hide());
    
    // Start hidden
    this.hide();
  }
  
  update(playerState) {
    if (!playerState || !playerState.stats) return;
    
    const stats = playerState.stats;
    
    this.statsDiv.innerHTML = `
      <div class="character-info">
        <h3>${playerState.name || 'Unknown'}</h3>
        <div class="stat-item">
          <span class="stat-label">Level</span>
          <span class="stat-value">${stats.level || 1}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Experience</span>
          <span class="stat-value">${stats.xp || 0} / ${stats.xpToLevel || 100}</span>
        </div>
      </div>
      
      <div class="character-stats-section">
        <h4>Attributes</h4>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-label">Strength</span>
            <span class="stat-value">${stats.strength || 10}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Dexterity</span>
            <span class="stat-value">${stats.dexterity || 10}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Intelligence</span>
            <span class="stat-value">${stats.intelligence || 10}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Vitality</span>
            <span class="stat-value">${stats.vitality || 10}</span>
          </div>
        </div>
      </div>
      
      <div class="character-stats-section">
        <h4>Combat</h4>
        <div class="stat-item">
          <span class="stat-label">Attack</span>
          <span class="stat-value">${stats.attack || 10}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Defense</span>
          <span class="stat-value">${stats.defense || 10}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Attack Speed</span>
          <span class="stat-value">${stats.attackSpeed || 1.0}</span>
        </div>
      </div>
    `;
    
    this.dirty = true;
  }
}

/**
 * Chat Input - For typing chat messages
 */
export class ChatInput extends UIComponent {
  initialize() {
    this.container.innerHTML = `
      <div class="chat-input-container">
        <input type="text" id="chat-input" class="chat-input" placeholder="Type to chat... (press T)" />
      </div>
    `;
    
    this.input = this.container.querySelector('#chat-input');
    this.active = false;
    
    this.input.addEventListener('blur', () => {
      if (this.active) {
        this.deactivate();
      }
    });
    
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        this.submit();
      } else if (e.key === 'Escape') {
        this.deactivate();
      }
    });
    
    // Start hidden
    this.hide();
  }
  
  activate() {
    this.active = true;
    this.show();
    this.input.focus();
  }
  
  deactivate() {
    this.active = false;
    this.input.value = '';
    this.input.blur();
    this.hide();
  }
  
  submit() {
    const message = this.input.value.trim();
    if (message && this.options.onSubmit) {
      this.options.onSubmit(message);
    }
    this.deactivate();
  }
  
  isActive() {
    return this.active;
  }
}
