import asyncio
import websockets
import logging
from typing import Optional, Callable, Dict, Any
import json


class WebSocketClient:
    """WebSocket client for real-time communication"""

    def __init__(self, uri: str, on_message: Optional[Callable] = None):
        self.uri = uri
        self.ws = None
        self.on_message = on_message
        self.is_connected = False
        self.logger = logging.getLogger("WebSocketClient")
        self.reconnect_interval = 5  # seconds

    async def connect(self) -> bool:
        """Connect to WebSocket server"""
        try:
            self.ws = await websockets.connect(self.uri)
            self.is_connected = True
            self.logger.info(f"Connected to WebSocket server: {self.uri}")
            return True
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
            return False

    async def listen(self):
        """Listen for incoming messages"""
        while True:
            try:
                if not self.is_connected:
                    await self.connect()

                async for message in self.ws:
                    try:
                        data = json.loads(message)
                        if self.on_message:
                            await self.on_message(data)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Received invalid JSON: {message}")

            except websockets.ConnectionClosed:
                self.logger.warning("WebSocket connection closed")
                self.is_connected = False
                await asyncio.sleep(self.reconnect_interval)
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(self.reconnect_interval)

    async def send(self, data: Dict[str, Any]) -> bool:
        """Send message to WebSocket server"""
        try:
            if not self.is_connected:
                if not await self.connect():
                    return False
            await self.ws.send(json.dumps(data))
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            self.is_connected = False
            return False

    async def close(self):
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            self.is_connected = False
