"""
Mind Rune - Standalone WebSocket Server

A minimal WebSocket implementation using only standard library.
No external dependencies required.
"""

import asyncio
import hashlib
import base64
import struct
import json
import logging
from typing import Dict, Set, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger(__name__)


class WSOpcode(IntEnum):
    """WebSocket frame opcodes"""
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


@dataclass
class WebSocketFrame:
    """A WebSocket frame"""
    fin: bool
    opcode: int
    payload: bytes
    
    @classmethod
    def parse(cls, data: bytes) -> tuple['WebSocketFrame', int]:
        """Parse a WebSocket frame from bytes. Returns (frame, bytes_consumed)."""
        if len(data) < 2:
            raise ValueError("Not enough data for frame header")
        
        fin = bool(data[0] & 0x80)
        opcode = data[0] & 0x0F
        masked = bool(data[1] & 0x80)
        payload_len = data[1] & 0x7F
        
        pos = 2
        
        if payload_len == 126:
            if len(data) < 4:
                raise ValueError("Not enough data for extended length")
            payload_len = struct.unpack(">H", data[2:4])[0]
            pos = 4
        elif payload_len == 127:
            if len(data) < 10:
                raise ValueError("Not enough data for extended length")
            payload_len = struct.unpack(">Q", data[2:10])[0]
            pos = 10
        
        if masked:
            if len(data) < pos + 4:
                raise ValueError("Not enough data for mask")
            mask = data[pos:pos+4]
            pos += 4
        else:
            mask = None
        
        if len(data) < pos + payload_len:
            raise ValueError("Not enough data for payload")
        
        payload = data[pos:pos+payload_len]
        
        if mask:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        
        return cls(fin=fin, opcode=opcode, payload=payload), pos + payload_len
    
    def encode(self) -> bytes:
        """Encode frame to bytes (server -> client, no masking)"""
        header = bytes([
            (0x80 if self.fin else 0) | self.opcode
        ])
        
        payload_len = len(self.payload)
        
        if payload_len <= 125:
            header += bytes([payload_len])
        elif payload_len <= 65535:
            header += bytes([126]) + struct.pack(">H", payload_len)
        else:
            header += bytes([127]) + struct.pack(">Q", payload_len)
        
        return header + self.payload


class WebSocketConnection:
    """A single WebSocket connection"""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 connection_id: str):
        self.reader = reader
        self.writer = writer
        self.connection_id = connection_id
        self.closed = False
        self.buffer = b""
    
    async def send(self, message: str) -> None:
        """Send a text message"""
        if self.closed:
            return
        
        frame = WebSocketFrame(fin=True, opcode=WSOpcode.TEXT, payload=message.encode('utf-8'))
        try:
            self.writer.write(frame.encode())
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Error sending to {self.connection_id}: {e}")
            self.closed = True
    
    async def send_bytes(self, data: bytes) -> None:
        """Send binary data"""
        if self.closed:
            return
        
        frame = WebSocketFrame(fin=True, opcode=WSOpcode.BINARY, payload=data)
        try:
            self.writer.write(frame.encode())
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Error sending to {self.connection_id}: {e}")
            self.closed = True
    
    async def recv(self) -> Optional[str]:
        """Receive a text message"""
        while not self.closed:
            try:
                # Read more data if needed
                if len(self.buffer) < 2:
                    chunk = await asyncio.wait_for(self.reader.read(4096), timeout=30.0)
                    if not chunk:
                        self.closed = True
                        return None
                    self.buffer += chunk
                    continue
                
                # Try to parse a frame
                try:
                    frame, consumed = WebSocketFrame.parse(self.buffer)
                    self.buffer = self.buffer[consumed:]
                except ValueError:
                    # Need more data
                    chunk = await asyncio.wait_for(self.reader.read(4096), timeout=30.0)
                    if not chunk:
                        self.closed = True
                        return None
                    self.buffer += chunk
                    continue
                
                # Handle frame
                if frame.opcode == WSOpcode.TEXT:
                    return frame.payload.decode('utf-8')
                elif frame.opcode == WSOpcode.BINARY:
                    return frame.payload.decode('utf-8')
                elif frame.opcode == WSOpcode.PING:
                    # Send pong
                    pong = WebSocketFrame(fin=True, opcode=WSOpcode.PONG, payload=frame.payload)
                    self.writer.write(pong.encode())
                    await self.writer.drain()
                elif frame.opcode == WSOpcode.CLOSE:
                    self.closed = True
                    # Send close response
                    close = WebSocketFrame(fin=True, opcode=WSOpcode.CLOSE, payload=b"")
                    try:
                        self.writer.write(close.encode())
                        await self.writer.drain()
                    except:
                        pass
                    return None
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                ping = WebSocketFrame(fin=True, opcode=WSOpcode.PING, payload=b"ping")
                try:
                    self.writer.write(ping.encode())
                    await self.writer.drain()
                except:
                    self.closed = True
                    return None
            except Exception as e:
                logger.error(f"Error receiving from {self.connection_id}: {e}")
                self.closed = True
                return None
        
        return None
    
    async def close(self) -> None:
        """Close the connection"""
        if self.closed:
            return
        
        self.closed = True
        
        # Send close frame
        close = WebSocketFrame(fin=True, opcode=WSOpcode.CLOSE, payload=b"")
        try:
            self.writer.write(close.encode())
            await self.writer.drain()
        except:
            pass
        
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except:
            pass


class WebSocketServer:
    """Simple WebSocket server using asyncio"""
    
    WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.connections: Dict[str, WebSocketConnection] = {}
        self.server = None
        self.running = False
        self._conn_counter = 0
        
        # Callbacks
        self.on_connect: Optional[Callable[[WebSocketConnection], Awaitable[None]]] = None
        self.on_disconnect: Optional[Callable[[WebSocketConnection], Awaitable[None]]] = None
        self.on_message: Optional[Callable[[WebSocketConnection, str], Awaitable[None]]] = None
    
    async def start(self) -> None:
        """Start the server"""
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )
        self.running = True
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
    
    async def stop(self) -> None:
        """Stop the server"""
        self.running = False
        
        # Close all connections
        for conn in list(self.connections.values()):
            await conn.close()
        self.connections.clear()
        
        # Stop server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
    
    async def _handle_client(self, reader: asyncio.StreamReader, 
                            writer: asyncio.StreamWriter) -> None:
        """Handle a new client connection"""
        # Read HTTP request
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=10.0)
            headers = {}
            
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=10.0)
                if line == b"\r\n" or not line:
                    break
                if b":" in line:
                    key, value = line.decode().split(":", 1)
                    headers[key.lower().strip()] = value.strip()
        except Exception as e:
            logger.error(f"Error reading HTTP request: {e}")
            writer.close()
            return
        
        # Validate WebSocket upgrade request
        if "sec-websocket-key" not in headers:
            writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await writer.drain()
            writer.close()
            return
        
        # Generate accept key
        ws_key = headers["sec-websocket-key"]
        accept_key = base64.b64encode(
            hashlib.sha1((ws_key + self.WEBSOCKET_GUID).encode()).digest()
        ).decode()
        
        # Send upgrade response
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_key}\r\n"
            "\r\n"
        )
        writer.write(response.encode())
        await writer.drain()
        
        # Create connection
        self._conn_counter += 1
        conn_id = f"conn_{self._conn_counter}"
        conn = WebSocketConnection(reader, writer, conn_id)
        self.connections[conn_id] = conn
        
        logger.info(f"WebSocket connection established: {conn_id}")
        
        # Call connect callback
        if self.on_connect:
            await self.on_connect(conn)
        
        # Message loop
        try:
            while not conn.closed and self.running:
                message = await conn.recv()
                if message is None:
                    break
                
                if self.on_message:
                    await self.on_message(conn, message)
        except Exception as e:
            logger.error(f"Error in connection {conn_id}: {e}")
        finally:
            # Clean up
            if conn_id in self.connections:
                del self.connections[conn_id]
            
            if self.on_disconnect:
                await self.on_disconnect(conn)
            
            await conn.close()
            logger.info(f"WebSocket connection closed: {conn_id}")
    
    async def broadcast(self, message: str, exclude: Optional[Set[str]] = None) -> None:
        """Broadcast message to all connections"""
        exclude = exclude or set()
        for conn_id, conn in list(self.connections.items()):
            if conn_id not in exclude and not conn.closed:
                await conn.send(message)


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def on_connect(conn):
        print(f"Connected: {conn.connection_id}")
        await conn.send(json.dumps({"type": "welcome", "data": {"message": "Hello!"}}))
    
    async def on_message(conn, message):
        print(f"Received from {conn.connection_id}: {message}")
        await conn.send(json.dumps({"type": "echo", "data": {"message": message}}))
    
    async def on_disconnect(conn):
        print(f"Disconnected: {conn.connection_id}")
    
    async def main():
        server = WebSocketServer("0.0.0.0", 8765)
        server.on_connect = on_connect
        server.on_message = on_message
        server.on_disconnect = on_disconnect
        
        await server.start()
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        
        await server.stop()
    
    asyncio.run(main())
