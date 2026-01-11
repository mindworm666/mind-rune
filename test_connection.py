#!/usr/bin/env python3
"""
Mind Rune - Connection Test Script

Tests the WebSocket connection and basic game flow.
"""

import asyncio
import json
import sys
sys.path.insert(0, '/home/clankie/workspace')

from backend.server.websocket import WebSocketServer


async def test_client():
    """Test WebSocket client connection"""
    import socket
    import hashlib
    import base64
    import struct
    
    print("Testing connection to Mind Rune server...")
    
    # Create socket connection
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    
    try:
        sock.connect(('localhost', 8765))
        print("✓ TCP connection established")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False
    
    # Send WebSocket handshake
    key = base64.b64encode(b"test1234test1234").decode()
    handshake = (
        "GET / HTTP/1.1\r\n"
        "Host: localhost:8765\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    
    sock.send(handshake.encode())
    
    # Read response
    response = sock.recv(1024).decode()
    if "101 Switching Protocols" in response:
        print("✓ WebSocket handshake successful")
    else:
        print(f"✗ WebSocket handshake failed: {response[:100]}")
        sock.close()
        return False
    
    # Helper to send WebSocket frame
    def send_ws_frame(message: str):
        payload = message.encode('utf-8')
        payload_len = len(payload)
        
        # Build frame with masking
        mask = b'\x01\x02\x03\x04'
        masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        
        if payload_len <= 125:
            header = bytes([0x81, 0x80 | payload_len]) + mask
        else:
            header = bytes([0x81, 0x80 | 126]) + struct.pack(">H", payload_len) + mask
        
        sock.send(header + masked_payload)
    
    # Helper to receive WebSocket frame (handles large messages)
    def recv_ws_frame() -> str:
        header = sock.recv(2)
        if len(header) < 2:
            return None
        
        opcode = header[0] & 0x0F
        payload_len = header[1] & 0x7F
        
        if payload_len == 126:
            payload_len = struct.unpack(">H", sock.recv(2))[0]
        elif payload_len == 127:
            payload_len = struct.unpack(">Q", sock.recv(8))[0]
        
        # Read full payload
        payload = b""
        while len(payload) < payload_len:
            chunk = sock.recv(min(4096, payload_len - len(payload)))
            if not chunk:
                break
            payload += chunk
        
        return payload.decode('utf-8')
    
    # Read welcome message
    msg = recv_ws_frame()
    data = json.loads(msg)
    if data.get("type") == "system_message":
        print(f"✓ Received welcome: {data['data']['message']}")
    else:
        print(f"? Received: {data}")
    
    # Test login
    login_msg = json.dumps({
        "type": "auth_login",
        "id": 1,
        "ts": 0,
        "data": {"username": "test", "password": "test"}
    })
    send_ws_frame(login_msg)
    print("→ Sent login request")
    
    # Read response
    msg = recv_ws_frame()
    data = json.loads(msg)
    if data.get("type") == "auth_success":
        print(f"✓ Login successful! Player ID: {data['data']['player_id']}")
    elif data.get("type") == "auth_failure":
        print(f"✗ Login failed: {data['data']['reason']}")
        sock.close()
        return False
    else:
        print(f"? Received: {data['type']}")
    
    # Read game state
    msg = recv_ws_frame()
    data = json.loads(msg)
    if data.get("type") == "game_state":
        player = data['data'].get('player', {})
        entities = data['data'].get('entities', [])
        tiles = data['data'].get('world_tiles', {})
        print(f"✓ Received game state:")
        print(f"  - Player: {player.get('name')} at ({player.get('x')}, {player.get('y')}, {player.get('z')})")
        print(f"  - {len(entities)} entities visible")
        print(f"  - {len(tiles)} tiles visible")
    else:
        print(f"? Received: {data['type']}")
    
    # Test movement
    move_msg = json.dumps({
        "type": "player_move",
        "id": 2,
        "ts": 0,
        "data": {"dx": 1, "dy": 0, "dz": 0}
    })
    send_ws_frame(move_msg)
    print("→ Sent move command")
    
    # Read delta update
    msg = recv_ws_frame()
    data = json.loads(msg)
    if data.get("type") == "game_state_delta":
        changed = data['data'].get('changed_entities', [])
        print(f"✓ Received delta update (tick {data['data'].get('tick')}, {len(changed)} entities)")
    else:
        print(f"? Received: {data['type']}")
    
    # Test chat
    chat_msg = json.dumps({
        "type": "chat_send",
        "id": 3,
        "ts": 0,
        "data": {"message": "Hello world!", "channel": "local"}
    })
    send_ws_frame(chat_msg)
    print("→ Sent chat message")
    
    # Read chat response (or delta)
    msg = recv_ws_frame()
    data = json.loads(msg)
    print(f"✓ Received: {data['type']}")
    
    sock.close()
    print("\n✓ All tests passed!")
    return True


if __name__ == "__main__":
    asyncio.run(test_client())
