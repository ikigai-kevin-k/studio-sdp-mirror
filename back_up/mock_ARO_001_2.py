import asyncio
import websockets
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SDPARO0012:
    def __init__(self, server_uri="ws://localhost:8765"):
        self.server_uri = server_uri
        self.websocket = None
        self.client_id = "ARO-001-2"
        self.state = "idle"
        self.connected = False

    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.server_uri)
            logger.info(f"Connected to server at {self.server_uri}")

            # Send client identification
            await self.websocket.send(
                json.dumps({"client_id": self.client_id})
            )

            # Wait for connection confirmation
            response = await self.websocket.recv()
            data = json.loads(response)

            if data.get("type") == "connection_confirmed":
                self.connected = True
                logger.info(f"Connection confirmed for {self.client_id}")
                return True
            else:
                logger.error("Connection not confirmed")
                return False

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def change_state_to_up(self):
        """Change state from idle to up"""
        if self.state != "idle":
            logger.warning(f"Cannot change state to up from {self.state}")
            return False

        try:
            self.state = "up"
            logger.info(f"State changed from idle to: {self.state}")

            # Notify server about state change
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "state_change",
                        "client_id": self.client_id,
                        "state": self.state,
                    }
                )
            )

            return True

        except Exception as e:
            logger.error(f"Failed to change state to up: {e}")
            return False

    async def listen_for_messages(self):
        """Listen for incoming messages from server"""
        if not self.websocket:
            return

        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type")

                    if message_type == "activate":
                        # Handle activation message from server
                        activation_msg = data.get("message", "")
                        logger.info(f"Received activation: {activation_msg}")

                        # Change state to up
                        if await self.change_state_to_up():
                            logger.info(
                                "Successfully activated and changed to up state"
                            )

                    elif message_type == "state_change_notification":
                        # Handle state change notification from other clients
                        other_client = data.get("client_id")
                        new_state = data.get("new_state")
                        logger.info(
                            f"Client {other_client} state changed to: {new_state}"
                        )

                    else:
                        logger.info(f"Received message: {data}")

                except json.JSONDecodeError:
                    logger.error("Invalid JSON message received")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server")
            self.connected = False
        except Exception as e:
            logger.error(f"Error listening for messages: {e}")

    async def run(self):
        """Main run loop"""
        # Connect to server
        if not await self.connect():
            return

        # Start listening for messages in background
        listen_task = asyncio.create_task(self.listen_for_messages())

        try:
            logger.info(
                f"{self.client_id} is running in idle state, waiting for activation"
            )

            # Keep running to listen for messages
            while self.connected:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Stopping SDP-ARO-001-2")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            # Cancel listening task
            listen_task.cancel()

            # Close connection
            if self.websocket:
                await self.websocket.close()
                logger.info("Connection closed")


async def main():
    """Main function"""
    client = SDPARO0012()
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SDP-ARO-001-2 stopped by user")
    except Exception as e:
        logger.error(f"SDP-ARO-001-2 error: {e}")
