/**
 * Mind Rune - Entry Point
 * 
 * Bootstrap the game client
 */

import { Game } from './game.js';

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', async () => {
  console.log('Mind Rune - Starting...');
  
  // Create game instance
  const game = new Game({
    canvasId: 'game-canvas',
    targetFPS: 60,
    serverUrl: null // Will use default WebSocket URL
  });
  
  // Expose to window for debugging
  window.game = game;
  
  // Start the game
  try {
    await game.start();
    console.log('Mind Rune - Running!');
  } catch (error) {
    console.error('Failed to start game:', error);
    showFatalError(error.message);
  }
  
  // Handle F12 for debug toggle
  window.addEventListener('keydown', (e) => {
    if (e.key === 'F12') {
      game.toggleDebug();
    }
  });
  
  // Handle window unload
  window.addEventListener('beforeunload', () => {
    game.stop();
  });
});

function showFatalError(message) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'error-screen';
  errorDiv.innerHTML = `
    <div class="error-message">
      <h1>FATAL ERROR</h1>
      <p>${message}</p>
      <button onclick="location.reload()">Reload</button>
    </div>
  `;
  document.body.appendChild(errorDiv);
}
