import asyncio
import websockets
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketServer:
    def __init__(self):
        self.clients = {}  # Store client connections with their IDs
        self.client_states = {}  # Store client states

    async def register_client(self, websocket, path):
        """Register a new client connection"""
        client_id = None

        try:
            # Wait for client to send its ID
            message = await websocket.recv()
            data = json.loads(message)
            client_id = data.get("client_id")

            if client_id:
                self.clients[client_id] = websocket
                self.client_states[client_id] = "idle"
                logger.info(
                    f"Client {client_id} connected. "
                    f"Total clients: {len(self.clients)}"
                )

                # Send confirmation
                await websocket.send(
                    json.dumps(
                        {
                            "type": "connection_confirmed",
                            "client_id": client_id,
                            "status": "connected",
                        }
                    )
                )

                # Handle messages from this client
                await self.handle_client_messages(websocket, client_id)
            else:
                logger.error("Client connected without providing client_id")
                await websocket.close()

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} connection closed")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                del self.client_states[client_id]
                logger.info(
                    f"Client {client_id} disconnected. Total clients: {len(self.clients)}"
                )

    async def handle_client_messages(self, websocket, client_id):
        """Handle incoming messages from a specific client"""
        async for message in websocket:
            try:
                data = json.loads(message)
                message_type = data.get("type")

                if message_type == "roulette_down":
                    # Handle roulette down message
                    await self.handle_roulette_down(client_id, data)
                elif message_type == "state_change":
                    # Handle state change notification
                    await self.handle_state_change(client_id, data)
                else:
                    logger.info(
                        f"Received message from {client_id}: " f"{data}"
                    )

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from client {client_id}")
            except Exception as e:
                logger.error(f"Error processing message from {client_id}: {e}")

    async def handle_roulette_down(self, client_id, data):
        """Handle roulette down message and notify other clients"""
        logger.info(f"Client {client_id} reported roulette is down")

        # Update client state to idle
        self.client_states[client_id] = "idle"

        # Notify other clients about the state change
        await self.notify_clients_state_change(client_id, "idle")

        # Find the next available client to activate
        next_client = self.find_next_available_client(client_id)
        if next_client:
            await self.activate_next_client(next_client)

    async def handle_state_change(self, client_id, data):
        """Handle state change notifications"""
        new_state = data.get("state")
        if new_state:
            self.client_states[client_id] = new_state
            logger.info(f"Client {client_id} state changed to: {new_state}")
            await self.notify_clients_state_change(client_id, new_state)

    def find_next_available_client(self, current_client_id):
        """Find the next available client to activate"""
        # Simple round-robin selection
        client_ids = list(self.clients.keys())
        if len(client_ids) <= 1:
            return None

        try:
            current_index = client_ids.index(current_client_id)
            next_index = (current_index + 1) % len(client_ids)
            return client_ids[next_index]
        except ValueError:
            return client_ids[0] if client_ids else None

    async def activate_next_client(self, client_id):
        """Activate the next client by sending activation message"""
        if client_id in self.clients:
            try:
                activation_message = {
                    "type": "activate",
                    "message": f"Activating {client_id} from idle to up state",
                }

                await self.clients[client_id].send(
                    json.dumps(activation_message)
                )
                self.client_states[client_id] = "up"
                logger.info(f"Activated client {client_id} to up state")

            except Exception as e:
                logger.error(f"Error activating client {client_id}: {e}")

    async def notify_clients_state_change(self, client_id, new_state):
        """Notify all clients about a state change"""
        notification = {
            "type": "state_change_notification",
            "client_id": client_id,
            "new_state": new_state,
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Send to all clients except the one that changed
        for cid, client_ws in self.clients.items():
            if cid != client_id:
                try:
                    await client_ws.send(json.dumps(notification))
                except Exception as e:
                    logger.error(f"Error notifying client {cid}: {e}")

    async def start_server(self, host="localhost", port=8765):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on " f"{host}:{port}")

        async with websockets.serve(self.register_client, host, port):
            logger.info(f"WebSocket server is running on ws://{host}:{port}")
            await asyncio.Future()  # Run forever


async def main():
    """Main function to start the server"""
    server = WebSocketServer()
    await server.start_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
