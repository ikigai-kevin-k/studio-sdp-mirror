#!/usr/bin/env python3
"""
Mock ARO-001-2 WebSocket client for testing error signal handling.
This client stays in idle state and listens for error signals from the server.
When it receives an error signal from ARO-001-1, it transitions from idle to running state.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
import subprocess
import threading
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Add the current directory to Python path to import ws_client
sys.path.append(os.path.dirname(__file__))

from ws_client import (
    SmartStudioWebSocketClient,
    StudioServiceStatusEnum,
    StudioMaintenanceStatusEnum,
)

# Configure logging with timestamp format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class DeviceState(Enum):
    """Device state enumeration."""

    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class StandbyClient:
    """Mock ARO-001-2 WebSocket client that listens for error signals."""

    def __init__(
        self, server_url: str, table_id: str, device_name: str, token: str
    ):
        self.server_url = server_url
        self.table_id = table_id
        self.device_name = device_name
        self.token = token
        self.websocket = None
        self.current_state = DeviceState.IDLE
        self.running = False
        self.error_signal_received = False

    async def connect(self):
        """Connect to the WebSocket server."""
        try:
            import websockets

            # Create connection URL for ARO-001-2 standby device
            # Format: ?id=TABLE_ID-DEVICE_NAME&token=TOKEN&gameCode=TABLE_ID
            # Connect as ARO-001-2-SDP to receive backup signals from ARO-001-1-SDP
            connection_id = f"{self.table_id}-{self.device_name}"
            connection_url = f"{self.server_url}?id={connection_id}&token={self.token}&gameCode={self.table_id}"

            logger.info(f"🔗 Connecting ARO-001-2 to {connection_url}")
            self.websocket = await websockets.connect(connection_url)
            logger.info("✅ ARO-001-2 WebSocket connection established")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect ARO-001-2: {e}")
            return False

    async def send_idle_status(self):
        """Send idle status update to the server."""
        if not self.websocket:
            logger.error("Not connected to server")
            return False

        try:
            # Send idle status with sdp information using proper WebSocket format
            status_data = {
                "sdp": "idle",
                # "timestamp": datetime.now(),  # Remove timestamp to avoid parsing issues
                # "message": "Device is in idle state, waiting for error signals",
            }
            
            # Use proper WebSocket message format: { event: string, data: any }
            ws_message = {
                "event": "service_status",
                "data": status_data
            }

            message = json.dumps(ws_message, cls=DateTimeEncoder)
            await self.websocket.send(message)
            logger.info(f"📤 ARO-001-2 sent idle status: {status_data}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send idle status: {e}")
            return False

    async def send_running_status(self):
        """Send running status update to the server."""
        if not self.websocket:
            logger.error("Not connected to server")
            return False

        try:
            # Send running status with sdp information using proper WebSocket format
            status_data = {
                "sdp": "up",
                # "timestamp": datetime.now(),  # Remove timestamp to avoid parsing issues
                # "message": "Device is now running after receiving error signal",  # Remove message field - not in StudioStatus entity
            }
            
            # Use proper WebSocket message format: { event: string, data: any }
            ws_message = {
                "event": "service_status",
                "data": status_data
            }

            message = json.dumps(ws_message, cls=DateTimeEncoder)
            await self.websocket.send(message)
            logger.info(f"📤 ARO-001-2 sent running status: {status_data}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send running status: {e}")
            return False

    def start_main_speed_2(self):
        """Start main_speed_2.py process in tmux session 'dp' window 'sdp'."""
        try:
            # Get the home directory and construct the full path
            home_dir = os.path.expanduser("~")
            studio_dir = os.path.join(home_dir, "studio-sdp-roulette")
            main_speed_2_path = os.path.join(studio_dir, "main_speed_2.py")
            
            if not os.path.exists(main_speed_2_path):
                logger.error(f"❌ main_speed_2.py not found at {main_speed_2_path}")
                return False
            
            logger.info(f"🚀 Starting main_speed_2.py in tmux session 'dp' window 'sdp' from {studio_dir}")
            
            # Create tmux command to run main_speed_2.py in the 'dp:sdp' session/window
            tmux_command = [
                "tmux", "send-keys", "-t", "dp:sdp",
                f"cd {studio_dir} && sudo venv/bin/python main_speed_2.py",
                "Enter"
            ]
            
            # Execute tmux command
            result = subprocess.run(
                tmux_command,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("✅ main_speed_2.py command sent to tmux session 'dp' window 'sdp' successfully")
                
                # Wait a moment for main_speed_2.py to start up
                import time
                time.sleep(2)
                
                # Send "*P 1\n" command to tmux session
                logger.info("🎯 Sending '*P 1' command to tmux session 'dp' window 'sdp'...")
                send_p1_command = [
                    "tmux", "send-keys", "-t", "dp:sdp",
                    "*P 1",
                    "Enter"
                ]
                
                # Execute the *P 1 command
                p1_result = subprocess.run(
                    send_p1_command,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if p1_result.returncode == 0:
                    logger.info("✅ '*P 1' command sent to tmux session 'dp' window 'sdp' successfully")
                else:
                    logger.error(f"❌ Failed to send '*P 1' command to tmux session: {p1_result.stderr}")
                
                return True
            else:
                logger.error(f"❌ Failed to send command to tmux session: {result.stderr}")
                return False
            
        except subprocess.TimeoutExpired:
            logger.error("❌ tmux command timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to start main_speed_2.py in tmux: {e}")
            return False

    def stop_main_speed_2(self):
        """Stop main_speed_2.py process in tmux session 'dp' window 'sdp'."""
        try:
            logger.info("🛑 Stopping main_speed_2.py in tmux session 'dp' window 'sdp'...")
            
            # Send Ctrl+C to tmux session to stop the running process
            tmux_stop_command = [
                "tmux", "send-keys", "-t", "dp:sdp",
                "C-c"  # Send Ctrl+C to interrupt the process
            ]
            
            # Execute tmux stop command
            result = subprocess.run(
                tmux_stop_command,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info("✅ Stop command sent to tmux session 'dp' window 'sdp' successfully")
                return True
            else:
                logger.error(f"❌ Failed to send stop command to tmux session: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ tmux stop command timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Error stopping main_speed_2.py in tmux: {e}")
            return False

    async def handle_error_signal(self, error_data: Dict[str, Any]):
        """Handle incoming error signal from the server."""
        try:
            logger.info(f"🚨 ARO-001-2 received error signal: {error_data}")

            # Check different signal formats from server
            signal = None
            
            # Format 1: { event: "exception", data: { signal: {...} } }
            if "data" in error_data and "signal" in error_data["data"]:
                signal = error_data["data"]["signal"]
            # Format 2: { cmd: { signal: {...} } }
            elif "cmd" in error_data and "signal" in error_data["cmd"]:
                signal = error_data["cmd"]["signal"]
            # Format 3: Direct signal object
            elif "signal" in error_data:
                signal = error_data["signal"]
            
            if signal:
                logger.info(f"📋 Error signal details: {signal}")

                # Transition from idle to running state
                if self.current_state == DeviceState.IDLE:
                    logger.info(
                        "🔄 ARO-001-2 transitioning from IDLE to RUNNING state"
                    )
                    self.current_state = DeviceState.RUNNING
                    self.error_signal_received = True

                    # Send running status update
                    await self.send_running_status()

                    # Start main_speed_2.py when transitioning to running state
                    logger.info("🎯 Starting main_speed_2.py due to error signal...")
                    self.start_main_speed_2()

                    # Send acknowledgment back to server
                    ack_data = {
                        "sdp": "up",
                        "action": "error_signal_acknowledged",
                        # "timestamp": datetime.now(),  # Remove timestamp to avoid parsing issues
                        # "original_signal": signal,  # Remove custom fields not in StudioStatus entity
                        # "new_state": self.current_state.value,  # Remove custom fields not in StudioStatus entity
                    }

                    ack_message = json.dumps(ack_data, cls=DateTimeEncoder)
                    await self.websocket.send(ack_message)
                    logger.info(
                        f"📤 ARO-001-2 sent acknowledgment: {ack_data}"
                    )

                    return True
                else:
                    logger.warning(
                        f"⚠️ ARO-001-2 received error signal but is not in IDLE state (current: {self.current_state.value})"
                    )
                    return False
            else:
                logger.warning("⚠️ ARO-001-2 received malformed error signal")
                return False

        except Exception as e:
            logger.error(f"❌ Error handling error signal: {e}")
            return False

    async def listen_for_messages(self):
        """Listen for incoming messages from the server."""
        try:
            while self.running and self.websocket:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(), timeout=1.0
                    )

                    if message:
                        try:
                            # Parse JSON message
                            data = json.loads(message)
                            logger.info(
                                f"📨 ARO-001-2 received message: {data}"
                            )

                            # Check if it's an error signal
                            # Server sends direct JSON with signal field, not wrapped in event/data format
                            if (
                                isinstance(data, dict)
                                and "signal" in data
                            ):
                                # Wrap the message in the expected format for handle_error_signal
                                wrapped_data = {
                                    "event": "exception",
                                    "data": data
                                }
                                await self.handle_error_signal(wrapped_data)
                            # Also check for direct signal messages from server
                            elif (
                                isinstance(data, dict)
                                and "cmd" in data
                                and "signal" in data.get("cmd", {})
                            ):
                                # Handle direct signal from server
                                await self.handle_error_signal(data)
                            else:
                                logger.info(
                                    f"📝 ARO-001-2 received other message: {data}"
                                )

                        except json.JSONDecodeError:
                            logger.info(
                                f"📝 ARO-001-2 received non-JSON message: {message}"
                            )

                except asyncio.TimeoutError:
                    # Timeout is expected, continue listening
                    continue
                except Exception as e:
                    if "ConnectionClosed" in str(type(e)):
                        logger.warning(
                            "🔌 ARO-001-2 WebSocket connection closed"
                        )
                        break

        except Exception as e:
            logger.error(f"❌ Error in message listener: {e}")

    async def idle_loop(self):
        """Main idle loop that sends periodic status updates."""
        try:
            logger.info("🔄 ARO-001-2 starting idle loop")

            while self.running and not self.error_signal_received:
                # Send idle status every 5 seconds
                await self.send_idle_status()

                # Wait for 5 seconds or until error signal received
                for _ in range(50):  # 5 seconds = 50 * 0.1 second intervals
                    if self.error_signal_received:
                        break
                    await asyncio.sleep(0.1)

            if self.error_signal_received:
                logger.info(
                    "🎯 ARO-001-2 error signal received, transitioning to running state"
                )
                # Keep running for a while to show the running state
                for _ in range(30):  # Run for 3 seconds
                    await self.send_running_status()
                    await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"❌ Error in idle loop: {e}")

    async def start(self):
        """Start the ARO-001-2 standby client."""
        try:
            # Connect to server
            if not await self.connect():
                return False

            self.running = True
            logger.info("🚀 ARO-001-2 standby client started")

            # Start message listener and idle loop concurrently
            await asyncio.gather(self.listen_for_messages(), self.idle_loop())

            return True

        except Exception as e:
            logger.error(f"❌ Error starting ARO-001-2 standby client: {e}")
            return False

    async def stop(self):
        """Stop the ARO-001-2 standby client."""
        self.running = False
        
        # Stop main_speed_2.py if running
        self.stop_main_speed_2()
        
        if self.websocket:
            await self.websocket.close()
            logger.info("🛑 ARO-001-2 standby client stopped")

    async def disconnect(self):
        """Disconnect from the server."""
        await self.stop()


async def main():
    """Main function for ARO-001-2 standby client."""

    # Load configuration from ws.json
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "conf", "ws.json"
    )

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        SERVER_URL = config["server_url"]
        TABLE_ID = "ARO-001-2"  # Connect as ARO-001-2 to receive backup signals
        DEVICE_NAME = "SDP"  # Override device name for SDP
        TOKEN = config["token"]


        logger.info(f"📋 Loaded configuration from {config_path}")
        logger.info(f"   - Server: {SERVER_URL}")
        logger.info(f"   - Device: {DEVICE_NAME}")
        logger.info(f"   - Table: {TABLE_ID}")

    except FileNotFoundError:
        logger.error(f"❌ Configuration file not found: {config_path}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in configuration file: {e}")
        return
    except KeyError as e:
        logger.error(f"❌ Missing required configuration key: {e}")
        return

    # Create ARO-001-2 standby client
    client = StandbyClient(SERVER_URL, TABLE_ID, DEVICE_NAME, TOKEN)

    try:
        logger.info("🎰 ARO-001-2 standby client - Error Signal Listener")
        logger.info("=" * 60)
        logger.info("📋 This client will:")
        logger.info("   1. Connect as ARO-001-2 device")
        logger.info(
            "   2. Stay in IDLE state and send periodic status updates"
        )
        logger.info("   3. Listen for error signals from the server")
        logger.info(
            "   4. Transition to RUNNING state when error signal received"
        )
        logger.info("=" * 60)

        # Start the standby client
        await client.start()

    except KeyboardInterrupt:
        logger.info("\n🛑 ARO-001-2 standby client interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error in ARO-001-2 standby client: {e}")
    finally:
        # Clean up
        await client.disconnect()
        logger.info("✅ ARO-001-2 standby client cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
