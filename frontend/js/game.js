/**
 * Mind Rune - Frontend Game Client
 * Handles authentication, WebSocket connection, and game rendering
 */

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

class MindRuneClient {
    constructor() {
        this.token = localStorage.getItem('token');
        this.username = localStorage.getItem('username');
        this.characterId = null;
        this.position = { x: 0, y: 0 };
        this.ws = null;
        this.players = [];
        
        this.initializeUI();
        
        // Check if already logged in
        if (this.token && this.username) {
            this.showGameScreen();
            this.connectWebSocket();
        }
    }
    
    initializeUI() {
        // Login/Register buttons
        document.getElementById('login-btn').addEventListener('click', () => this.login());
        document.getElementById('register-btn').addEventListener('click', () => this.register());
        
        // Enter key on password field
        document.getElementById('password').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.login();
        });
        
        // Game controls
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));
        
        // Chat input
        document.getElementById('chat-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendChat();
            }
        });
    }
    
    async login() {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        
        if (!username || !password) {
            this.showError('Please enter username and password');
            return;
        }
        
        try {
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);
            
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                this.handleAuthSuccess(data);
            } else {
                const error = await response.json();
                this.showError(error.detail || 'Login failed');
            }
        } catch (err) {
            this.showError('Connection error. Is the server running?');
            console.error(err);
        }
    }
    
    async register() {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        
        if (!username || !password) {
            this.showError('Please enter username and password');
            return;
        }
        
        if (username.length < 3) {
            this.showError('Username must be at least 3 characters');
            return;
        }
        
        if (password.length < 6) {
            this.showError('Password must be at least 6 characters');
            return;
        }
        
        try {
            const response = await fetch(`${API_URL}/auth/register?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.handleAuthSuccess(data);
            } else {
                const error = await response.json();
                this.showError(error.detail || 'Registration failed');
            }
        } catch (err) {
            this.showError('Connection error. Is the server running?');
            console.error(err);
        }
    }
    
    handleAuthSuccess(data) {
        this.token = data.access_token;
        this.username = data.username;
        this.characterId = data.character_id;
        
        localStorage.setItem('token', this.token);
        localStorage.setItem('username', this.username);
        
        this.showGameScreen();
        this.connectWebSocket();
    }
    
    showGameScreen() {
        document.getElementById('login-screen').classList.remove('active');
        document.getElementById('game-screen').classList.add('active');
        document.getElementById('player-name').textContent = this.username;
    }
    
    showError(message) {
        const errorDiv = document.getElementById('login-error');
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
        setTimeout(() => errorDiv.classList.add('hidden'), 3000);
    }
    
    connectWebSocket() {
        document.getElementById('connection-status').textContent = '🟡 Connecting...';
        
        this.ws = new WebSocket(`${WS_URL}?token=${this.token}`);
        
        this.ws.onopen = () => {
            document.getElementById('connection-status').textContent = '🟢 Connected';
            this.log('Connected to server');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleServerMessage(data);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            document.getElementById('connection-status').textContent = '🔴 Error';
        };
        
        this.ws.onclose = () => {
            document.getElementById('connection-status').textContent = '🔴 Disconnected';
            this.log('Disconnected from server');
            
            // Attempt to reconnect after 5 seconds
            setTimeout(() => {
                if (this.token) {
                    this.log('Attempting to reconnect...');
                    this.connectWebSocket();
                }
            }, 5000);
        };
    }
    
    handleServerMessage(data) {
        switch (data.type) {
            case 'init':
                this.characterId = data.character_id;
                this.position = data.position;
                this.renderWorld(data.world);
                this.updatePlayerInfo();
                this.log('Entered the world');
                break;
                
            case 'move_success':
                this.position = data.position;
                this.renderWorld(data.world);
                this.updatePlayerInfo();
                break;
                
            case 'player_joined':
                this.log(`${data.username} joined the game`);
                this.updatePlayersOnline();
                break;
                
            case 'player_left':
                this.log(`${data.username} left the game`);
                this.updatePlayersOnline();
                break;
                
            case 'player_moved':
                // Could update nearby players list here
                break;
                
            case 'chat':
                this.showChatMessage(data.username, data.message);
                this.log(`${data.username}: ${data.message}`);
                break;
                
            case 'error':
                this.log(`Error: ${data.message}`);
                break;
        }
    }
    
    handleKeyPress(e) {
        // Don't handle keys if chat is open
        if (!document.getElementById('chat-container').classList.contains('hidden')) {
            if (e.key === 'Escape') {
                this.closeChat();
            }
            return;
        }
        
        // Movement keys
        let direction = null;
        switch(e.key) {
            case 'ArrowUp':
            case 'w':
            case 'W':
                direction = 'n';
                break;
            case 'ArrowDown':
            case 's':
            case 'S':
                direction = 's';
                break;
            case 'ArrowLeft':
            case 'a':
            case 'A':
                direction = 'w';
                break;
            case 'ArrowRight':
            case 'd':
            case 'D':
                direction = 'e';
                break;
            case 't':
            case 'T':
                this.openChat();
                e.preventDefault();
                return;
        }
        
        if (direction && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'move', direction }));
            e.preventDefault();
        }
    }
    
    renderWorld(worldData) {
        const canvas = document.getElementById('game-canvas');
        
        // Convert 2D array to ASCII string
        let output = '';
        for (let row of worldData) {
            output += row.join('') + '\n';
        }
        
        canvas.textContent = output;
    }
    
    updatePlayerInfo() {
        document.getElementById('player-position').textContent = 
            `X:${this.position.x} Y:${this.position.y}`;
    }
    
    updatePlayersOnline() {
        // This would be updated from server data
        // For now, just a placeholder
    }
    
    log(message) {
        const logContainer = document.getElementById('game-log');
        const entry = document.createElement('p');
        entry.className = 'log-entry';
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logContainer.appendChild(entry);
        
        // Keep only last 50 entries
        while (logContainer.children.length > 50) {
            logContainer.removeChild(logContainer.firstChild);
        }
        
        // Scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    openChat() {
        const chatContainer = document.getElementById('chat-container');
        const chatInput = document.getElementById('chat-input');
        chatContainer.classList.remove('hidden');
        chatInput.focus();
    }
    
    closeChat() {
        const chatContainer = document.getElementById('chat-container');
        const chatInput = document.getElementById('chat-input');
        chatContainer.classList.add('hidden');
        chatInput.value = '';
    }
    
    sendChat() {
        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();
        
        if (message && this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'chat', message }));
            chatInput.value = '';
        }
    }
    
    showChatMessage(username, message) {
        const chatMessages = document.getElementById('chat-messages');
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message';
        msgDiv.innerHTML = `<strong>${username}:</strong> ${this.escapeHtml(message)}`;
        chatMessages.appendChild(msgDiv);
        
        // Auto-scroll
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Auto-show chat briefly
        const chatContainer = document.getElementById('chat-container');
        const wasHidden = chatContainer.classList.contains('hidden');
        if (wasHidden) {
            chatContainer.classList.remove('hidden');
            setTimeout(() => {
                if (document.getElementById('chat-input') !== document.activeElement) {
                    chatContainer.classList.add('hidden');
                }
            }, 3000);
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the game when page loads
window.addEventListener('DOMContentLoaded', () => {
    new MindRuneClient();
});
