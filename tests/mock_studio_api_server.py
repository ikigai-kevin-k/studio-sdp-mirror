#!/usr/bin/env python3
"""
Mock StudioAPI WebSocket Server for testing.

This server simulates the StudioAPI WebSocket server and can send
SDP down signals to connected clients (e.g., main_speed.py).

The server is designed to be easily replaceable with the real StudioAPI server
by using configuration files or environment variables.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Optional, Set
from urllib.parse import parse_qs, urlparse
from datetime import datetime

import websockets
# Note: WebSocketServerProtocol is deprecated in newer websockets versions
# We use websockets.WebSocketServerProtocol for type hints, but it's optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class MockStudioAPIServer:
    """
    Mock StudioAPI WebSocket Server.

    This server accepts connections from clients (e.g., main_speed.py) and
    can send SDP down signals to trigger mode switching from running to idle.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        server_path: str = "/v1/ws",
    ):
        """
        Initialize the mock StudioAPI server.

        Args:
            host: Server host address (default: localhost)
            port: Server port (default: 8080)
            server_path: WebSocket server path (default: /v1/ws)
        """
        self.host = host
        self.port = port
        self.server_path = server_path
        self.clients: Dict = {}  # Store WebSocket connections
        self.client_info: Dict[str, Dict] = {}  # Store client metadata
        self.running = False

    def _parse_query_params(self, path: str) -> Dict[str, str]:
        """Parse query parameters from WebSocket path."""
        params = {}
        if "?" in path:
            query_string = path.split("?")[1]
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key] = value
        return params

    async def handle_connection(
        self, websocket
    ):
        """
        Handle new WebSocket connection.

        Args:
            websocket: WebSocket connection object
        """
        # Log connection attempt immediately
        try:
            remote_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        except Exception:
            remote_addr = "unknown"
        logger.info(f"🔌 New connection attempt from {remote_addr}")
        
        client_id = None
        try:
            # Get path from websocket object (new websockets API)
            # In websockets 12.0+, handler only receives connection object
            # Path is available as connection.path attribute
            try:
                # New API (websockets 12.0+): path is an attribute
                path = websocket.path
                logger.debug(f"📋 Got path from websocket.path: {path}")
            except AttributeError:
                # Fallback for older versions or if path attribute doesn't exist
                # Try to get from request object
                if hasattr(websocket, "request"):
                    path = websocket.request.path
                    logger.debug(f"📋 Got path from websocket.request.path: {path}")
                elif hasattr(websocket, "request_headers"):
                    # Try to get from headers (less reliable)
                    path = websocket.request_headers.get(":path", "/v1/ws")
                    logger.debug(f"📋 Got path from request_headers: {path}")
                else:
                    # Last resort: use default path
                    path = "/v1/ws"
                    logger.warning("⚠️  Could not get path from websocket, using default")
            
            logger.info(f"📋 Connection path: {path}")
            
            # Parse query parameters from path
            query_params = self._parse_query_params(path)
            logger.info(f"📋 Parsed query params: {query_params}")

            # Extract connection information
            # Support multiple connection formats for compatibility:
            # Format 1: ?token=TOKEN&id=TABLE_ID&device=DEVICE_NAME (SmartStudioWebSocketClient)
            # Format 2: ?id=TABLE_ID-DEVICE_NAME&token=TOKEN&gameCode=TABLE_ID (real StudioAPI)
            token = query_params.get("token", "")
            table_id = query_params.get("id", "")
            device_name = query_params.get("device", "")
            game_code = query_params.get("gameCode", "")

            # Handle Format 2: id might be "TABLE_ID-DEVICE_NAME"
            if table_id and "-" in table_id and not device_name:
                # Parse TABLE_ID-DEVICE_NAME format
                parts = table_id.split("-", 1)
                if len(parts) == 2:
                    table_id = parts[0]
                    device_name = parts[1]
                elif game_code:
                    # Use gameCode as table_id if available
                    device_name = table_id.replace(game_code + "-", "", 1)
                    table_id = game_code

            # Generate client ID from connection info
            if table_id and device_name:
                client_id = f"{table_id}-{device_name}"
            elif table_id:
                client_id = table_id
            else:
                # Use remote address as fallback
                client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"

            logger.info(
                f"🔗 New connection: {client_id} "
                f"(table_id={table_id}, device={device_name}, token={token})"
            )

            # Store client connection and metadata
            self.clients[client_id] = websocket
            self.client_info[client_id] = {
                "table_id": table_id,
                "device_name": device_name,
                "token": token,
                "connected_at": datetime.now().isoformat(),
            }

            # Send welcome message (optional, for compatibility)
            welcome_msg = {
                "message": "Connected to Mock StudioAPI Server",
                "status": "ready",
                "client_id": client_id,
            }
            await websocket.send(json.dumps(welcome_msg))
            logger.info(f"✅ Sent welcome message to {client_id}")

            # Handle incoming messages from client
            async for message in websocket:
                await self._handle_client_message(websocket, client_id, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Connection closed: {client_id}")
        except Exception as e:
            logger.error(f"❌ Error handling connection {client_id}: {e}")
        finally:
            # Clean up on disconnect
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                if client_id in self.client_info:
                    del self.client_info[client_id]
                logger.info(
                    f"🧹 Cleaned up connection: {client_id} "
                    f"(remaining: {len(self.clients)})"
                )

    async def _handle_client_message(
        self, websocket, client_id: str, message: str
    ):
        """
        Handle incoming message from client.

        Args:
            websocket: WebSocket connection
            client_id: Client identifier
            message: Received message
        """
        try:
            # Try to parse as JSON
            data = json.loads(message)
            logger.info(f"📨 Received from {client_id}: {data}")

            # Echo back confirmation (optional, for compatibility)
            response = {"status": "received", "client_id": client_id}
            await websocket.send(json.dumps(response))

        except json.JSONDecodeError:
            # Non-JSON message, log it
            logger.info(f"📝 Received non-JSON from {client_id}: {message}")
        except Exception as e:
            logger.error(f"❌ Error handling message from {client_id}: {e}")

    async def send_sdp_down_signal(
        self,
        client_id: Optional[str] = None,
        table_id: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> bool:
        """
        Send SDP down signal to a specific client or all matching clients.

        Args:
            client_id: Specific client ID to send to (optional)
            table_id: Table ID to filter clients (optional)
            device_name: Device name to filter clients (optional)

        Returns:
            bool: True if signal was sent successfully, False otherwise
        """
        targets = []

        # Find target clients
        if client_id:
            if client_id in self.clients:
                targets.append(client_id)
        elif table_id or device_name:
            # Find clients matching table_id and/or device_name
            for cid, info in self.client_info.items():
                if table_id and info.get("table_id") != table_id:
                    continue
                if device_name and info.get("device_name") != device_name:
                    continue
                if cid in self.clients:
                    targets.append(cid)
        else:
            # Send to all connected clients
            targets = list(self.clients.keys())

        if not targets:
            logger.warning("⚠️  No clients found to send SDP down signal")
            return False

        # Send SDP down signal in the format expected by main_speed.py
        # Format 1: Simple format (most compatible)
        sdp_down_message = {"sdp": "down"}

        success_count = 0
        for target_id in targets:
            try:
                websocket = self.clients[target_id]
                await websocket.send(json.dumps(sdp_down_message))
                logger.info(
                    f"📤 Sent SDP down signal to {target_id}: {sdp_down_message}"
                )
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to send to {target_id}: {e}")

        logger.info(
            f"✅ SDP down signal sent to {success_count}/{len(targets)} clients"
        )
        return success_count > 0

    async def send_sdp_down_signal_alternative_format(
        self,
        client_id: Optional[str] = None,
        table_id: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> bool:
        """
        Send SDP down signal using alternative format (with signal wrapper).

        This method sends the signal in a nested format that main_speed.py
        also supports.

        Args:
            client_id: Specific client ID to send to (optional)
            table_id: Table ID to filter clients (optional)
            device_name: Device name to filter clients (optional)

        Returns:
            bool: True if signal was sent successfully, False otherwise
        """
        targets = []

        # Find target clients (same logic as send_sdp_down_signal)
        if client_id:
            if client_id in self.clients:
                targets.append(client_id)
        elif table_id or device_name:
            for cid, info in self.client_info.items():
                if table_id and info.get("table_id") != table_id:
                    continue
                if device_name and info.get("device_name") != device_name:
                    continue
                if cid in self.clients:
                    targets.append(cid)
        else:
            targets = list(self.clients.keys())

        if not targets:
            logger.warning("⚠️  No clients found to send SDP down signal")
            return False

        # Format 2: Nested signal format
        sdp_down_message = {
            "signal": {
                "msgId": "SDP_DOWN",
                "content": "DOWN",
                "device": "sdp",
                "status": "down",
            }
        }

        success_count = 0
        for target_id in targets:
            try:
                websocket = self.clients[target_id]
                await websocket.send(json.dumps(sdp_down_message))
                logger.info(
                    f"📤 Sent SDP down signal (alternative format) to {target_id}: "
                    f"{sdp_down_message}"
                )
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to send to {target_id}: {e}")

        logger.info(
            f"✅ SDP down signal (alternative) sent to "
            f"{success_count}/{len(targets)} clients"
        )
        return success_count > 0

    def list_connected_clients(self) -> Dict[str, Dict]:
        """
        List all connected clients.

        Returns:
            Dict mapping client_id to client info
        """
        return self.client_info.copy()

    async def start(self):
        """Start the WebSocket server."""
        self.running = True
        server_url = f"ws://{self.host}:{self.port}{self.server_path}"
        logger.info(f"🚀 Starting Mock StudioAPI Server on {server_url}")

        try:
            async with websockets.serve(
                self.handle_connection, self.host, self.port
            ):
                logger.info(
                    f"✅ Mock StudioAPI Server is running on {server_url}"
                )
                logger.info("📋 Waiting for client connections...")
                logger.info("💡 Use send_sdp_down() method or CLI to send signals")
                await asyncio.Future()  # Run forever
        except OSError as e:
            if e.errno == 98:  # Address already in use
                logger.error(
                    f"❌ Port {self.port} is already in use. "
                    f"Please use a different port with --port option, "
                    f"or stop the process using port {self.port}"
                )
                logger.info(f"💡 Try: python tests/mock_studio_api_server.py --port 8081")
                raise
            else:
                raise

    async def stop(self):
        """Stop the WebSocket server."""
        self.running = False
        # Close all client connections
        for client_id, websocket in list(self.clients.items()):
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing connection {client_id}: {e}")
        self.clients.clear()
        self.client_info.clear()
        logger.info("🛑 Mock StudioAPI Server stopped")


# Global server instance for CLI usage
_server_instance: Optional[MockStudioAPIServer] = None


async def send_sdp_down(
    client_id: Optional[str] = None,
    table_id: Optional[str] = None,
    device_name: Optional[str] = None,
):
    """
    Helper function to send SDP down signal.

    This function can be called from external scripts or CLI.

    Args:
        client_id: Specific client ID (optional)
        table_id: Table ID filter (optional, e.g., "ARO-001")
        device_name: Device name filter (optional, e.g., "ARO-001-1")
    """
    global _server_instance
    if _server_instance is None:
        logger.error("❌ Server instance not initialized")
        return False

    return await _server_instance.send_sdp_down_signal(
        client_id=client_id, table_id=table_id, device_name=device_name
    )


async def interactive_mode(server: MockStudioAPIServer):
    """
    Interactive mode for sending SDP down signals.

    Args:
        server: MockStudioAPIServer instance
    """
    logger.info("🎮 Interactive mode started")
    logger.info("Commands:")
    logger.info("  'list' - List connected clients")
    logger.info("  'send <table_id> [device_name]' - Send SDP down signal")
    logger.info("  'send-all' - Send SDP down to all clients")
    logger.info("  'quit' - Exit interactive mode")

    while server.running:
        try:
            # Read command from stdin (non-blocking)
            command = await asyncio.get_event_loop().run_in_executor(
                None, input, "\n> "
            )

            command = command.strip().lower()

            if command == "quit" or command == "exit":
                logger.info("👋 Exiting interactive mode")
                break
            elif command == "list":
                clients = server.list_connected_clients()
                if clients:
                    logger.info(f"📋 Connected clients ({len(clients)}):")
                    for cid, info in clients.items():
                        logger.info(
                            f"  - {cid}: table_id={info.get('table_id')}, "
                            f"device={info.get('device_name')}"
                        )
                else:
                    logger.info("📋 No clients connected")
            elif command.startswith("send "):
                parts = command.split()
                if len(parts) >= 2:
                    table_id = parts[1]
                    device_name = parts[2] if len(parts) > 2 else None
                    await server.send_sdp_down_signal(
                        table_id=table_id, device_name=device_name
                    )
                else:
                    logger.warning("⚠️  Usage: send <table_id> [device_name]")
            elif command == "send-all":
                await server.send_sdp_down_signal()
            else:
                logger.warning(f"⚠️  Unknown command: {command}")

        except EOFError:
            # Handle Ctrl+D
            break
        except KeyboardInterrupt:
            logger.info("\n👋 Exiting interactive mode")
            break
        except Exception as e:
            logger.error(f"❌ Error in interactive mode: {e}")


async def main():
    """Main function to run the mock server."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Mock StudioAPI WebSocket Server"
    )
    parser.add_argument(
        "--host", default="localhost", help="Server host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Server port (default: 8080)"
    )
    parser.add_argument(
        "--path",
        default="/v1/ws",
        help="WebSocket path (default: /v1/ws)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive mode for sending signals",
    )
    parser.add_argument(
        "--send-sdp-down",
        action="store_true",
        help="Send SDP down signal after startup (for testing)",
    )
    parser.add_argument(
        "--table-id",
        help="Table ID for sending SDP down signal (e.g., ARO-001)",
    )
    parser.add_argument(
        "--device-name",
        help="Device name for sending SDP down signal (e.g., ARO-001-1)",
    )
    parser.add_argument(
        "--wait-time",
        type=int,
        default=10,
        help="Wait time in seconds for clients to connect before sending signal (default: 10)",
    )
    parser.add_argument(
        "--wait-until-connected",
        action="store_true",
        help="Wait until at least one client connects before sending signal",
    )

    args = parser.parse_args()

    global _server_instance
    _server_instance = MockStudioAPIServer(
        host=args.host, port=args.port, server_path=args.path
    )

    # Start server in background
    server_task = asyncio.create_task(_server_instance.start())

    # Wait a bit for server to start
    await asyncio.sleep(1)

    # Handle CLI options
    if args.send_sdp_down:
        if args.wait_until_connected:
            # Wait until at least one client connects
            logger.info("⏳ Waiting for clients to connect...")
            logger.info("💡 Make sure main_speed.py is running and connected")
            max_wait = 60  # Maximum 60 seconds
            waited = 0
            while waited < max_wait:
                clients = _server_instance.list_connected_clients()
                if clients:
                    logger.info(
                        f"✅ Found {len(clients)} connected client(s), proceeding to send signal..."
                    )
                    break
                await asyncio.sleep(1)
                waited += 1
                if waited % 5 == 0:
                    logger.info(f"⏳ Still waiting... ({waited}s/{max_wait}s)")
            else:
                logger.warning(
                    f"⚠️  No clients connected after {max_wait} seconds"
                )
                logger.info("💡 Server will continue running. Connect a client and use interactive mode to send signal")
        else:
            # Wait for specified time
            logger.info(
                f"⏳ Waiting {args.wait_time} seconds for clients to connect..."
            )
            logger.info("💡 Make sure main_speed.py is running and connected")
            await asyncio.sleep(args.wait_time)

        # Send SDP down signal
        clients_before = _server_instance.list_connected_clients()
        if clients_before:
            logger.info(
                f"📤 Sending SDP down signal to {len(clients_before)} client(s)..."
            )
        success = await _server_instance.send_sdp_down_signal(
            table_id=args.table_id, device_name=args.device_name
        )
        
        if success:
            logger.info("✅ SDP down signal sent successfully")
            logger.info("💡 Check main_speed.py logs to verify mode switch")
        else:
            logger.warning("⚠️  No clients found to send SDP down signal")
            logger.info("💡 Server will continue running. Connect a client and try again")
            logger.info("💡 Or use interactive mode: python tests/mock_studio_api_server.py --interactive --port 8081")

    if args.interactive:
        # Run interactive mode
        await interactive_mode(_server_instance)
    else:
        # Keep server running
        try:
            await server_task
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutting down server...")
            await _server_instance.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Server stopped by user")
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logger.error(
                f"❌ Port is already in use. "
                f"Please use --port option to specify a different port"
            )
        else:
            logger.error(f"❌ Server error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

