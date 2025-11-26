import asyncio
import websockets
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SDPARO0011:
    def __init__(self, server_uri="ws://localhost:8765"):
        self.server_uri = server_uri
        self.websocket = None
        self.client_id = "ARO-001-1"
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

    async def send_roulette_down(self):
        """Send roulette down message and enter idle state"""
        if not self.connected or not self.websocket:
            logger.error("Not connected to server")
            return False

        try:
            # Send roulette down message
            message = {
                "type": "roulette_down",
                "client_id": self.client_id,
                "message": "ARO-001-1 roulette is down",
                "timestamp": time.time(),
            }

            await self.websocket.send(json.dumps(message))
            logger.info("Sent roulette down message")

            # Update local state to idle
            self.state = "idle"
            logger.info(f"State changed to: {self.state}")

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
            logger.error(f"Failed to send roulette down message: {e}")
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

                    if message_type == "state_change_notification":
                        # Handle state change notification from other clients
                        other_client = data.get("client_id")
                        new_state = data.get("new_state")
                        logger.info(
                            f"Client {other_client} state changed to: {new_state}"
                        )

                    elif message_type == "activate":
                        # Handle activation message
                        logger.info(
                            f"Received activation: {data.get('message')}"
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
            # Wait a bit for connection to stabilize
            await asyncio.sleep(2)

            # Send roulette down message
            if await self.send_roulette_down():
                logger.info(
                    "Successfully sent roulette down and entered idle state"
                )

                # Keep running to listen for messages
                while self.connected:
                    await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Stopping SDP-ARO-001-1")
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
    client = SDPARO0011()
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("SDP-ARO-001-1 stopped by user")
    except Exception as e:
        logger.error(f"SDP-ARO-001-1 error: {e}")
