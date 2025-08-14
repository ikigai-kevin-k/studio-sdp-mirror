"""
WebSocket client for sending table/device status updates to the server.

This module provides a WebSocket client that connects to the StudioWebSocketServer
and sends status updates for services and devices.
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StudioServiceStatusEnum:
    """Enumeration for Studio service status."""
    UP = 'up'
    DOWN = 'down'
    STANDBY = 'standby'
    CALIBRATION = 'calibration'
    EXCEPTION = 'exception'


class StudioDeviceStatusEnum:
    """Enumeration for Studio device status."""
    UP = 'up'
    DOWN = 'down'


class StudioWebSocketClient:
    """WebSocket client for sending table/device status updates."""
    
    def __init__(self, server_url: str, table_id: str, device_name: str, token: str):
        self.server_url = server_url
        self.table_id = table_id
        self.device_name = device_name
        self.token = token
        self.websocket = None
        
    async def connect(self):
        """Connect to the WebSocket server."""
        try:
            # Create connection URL (without query parameters for now)
            connection_url = self.server_url
            
            logger.info(f"Connecting to {connection_url}")
            self.websocket = await websockets.connect(connection_url)
            
            # Wait for welcome message
            welcome_message = await self.websocket.recv()
            welcome_data = json.loads(welcome_message)
            logger.info(f"Connected! Received welcome: {welcome_data}")
            
            # Send authentication message
            auth_data = {
                "id": f"{self.table_id}_{self.device_name}",
                "token": self.token
            }
            await self.websocket.send(json.dumps(auth_data))
            logger.info(f"Sent authentication: {auth_data}")
            
            # Wait for initial status message
            initial_message = await self.websocket.recv()
            initial_status = json.loads(initial_message)
            logger.info(f"Authentication successful! Received initial status: {initial_status}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def send_status_update(self, status_data: Dict[str, Any]):
        """Send status update to the server."""
        if not self.websocket:
            logger.error("Not connected to server")
            return False
        
        try:
            # Send status update
            message = json.dumps(status_data)
            await self.websocket.send(message)
            logger.info(f"Sent status update: {status_data}")
            
            # Wait for confirmation
            response = await self.websocket.recv()
            confirmation = json.loads(response)
            logger.info(f"Received confirmation: {confirmation}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")
            return False
    
    async def send_service_status(self, service: str, status: str):
        """Send service status update."""
        status_data = {service.lower(): status}
        return await self.send_status_update(status_data)
    
    async def send_device_status(self, device: str, status: str):
        """Send device status update."""
        status_data = {device.lower(): status}
        return await self.send_status_update(status_data)
    
    async def send_multiple_updates(self, updates: Dict[str, str]):
        """Send multiple status updates at once."""
        return await self.send_status_update(updates)
    
    async def disconnect(self):
        """Disconnect from the server."""
        if self.websocket:
            await self.websocket.close()
            logger.info("Disconnected from server")


async def demo_status_updates():
    """Demonstrate various status update scenarios."""
    
    # Client configuration
    SERVER_URL = "ws://localhost:8080"
    TABLE_ID = "ARO-001"
    DEVICE_NAME = "dealerPC"
    TOKEN = "MY_TOKEN"
    
    # Create client
    client = StudioWebSocketClient(SERVER_URL, TABLE_ID, DEVICE_NAME, TOKEN)
    
    try:
        # Connect to server
        if not await client.connect():
            logger.error("Failed to connect to server")
            return
        
        logger.info("Starting status update demonstration...")
        
        # 1. Send service status updates
        logger.info("\n--- Service Status Updates ---")
        await client.send_service_status("SDP", StudioServiceStatusEnum.UP)
        await asyncio.sleep(1)
        
        await client.send_service_status("IDP", StudioServiceStatusEnum.STANDBY)
        await asyncio.sleep(1)
        
        # 2. Send device status updates
        logger.info("\n--- Device Status Updates ---")
        await client.send_device_status("ROULETTE", StudioDeviceStatusEnum.UP)
        await asyncio.sleep(1)
        
        await client.send_device_status("SHAKER", StudioDeviceStatusEnum.DOWN)
        await asyncio.sleep(1)
        
        await client.send_device_status("BROKER", StudioDeviceStatusEnum.UP)
        await asyncio.sleep(1)
        
        # 3. Send multiple updates at once
        logger.info("\n--- Multiple Updates ---")
        multiple_updates = {
            "zcam": StudioDeviceStatusEnum.UP,
            "barcode_scanner": StudioDeviceStatusEnum.UP,
            "nfc_scanner": StudioDeviceStatusEnum.DOWN
        }
        await client.send_multiple_updates(multiple_updates)
        await asyncio.sleep(1)
        
        # 4. Send maintenance mode
        logger.info("\n--- Maintenance Mode ---")
        await client.send_status_update({"maintenance": True})
        await asyncio.sleep(1)
        
        # 5. Send calibration status
        logger.info("\n--- Calibration Status ---")
        await client.send_service_status("SDP", StudioServiceStatusEnum.CALIBRATION)
        await asyncio.sleep(1)
        
        logger.info("\nStatus update demonstration completed!")
        
    except Exception as e:
        logger.error(f"Error during demonstration: {e}")
    
    finally:
        # Disconnect from server
        await client.disconnect()


async def interactive_mode():
    """Interactive mode for manual status updates."""
    
    # Client configuration
    SERVER_URL = "ws://localhost:8080"
    TABLE_ID = "ARO-001"
    DEVICE_NAME = "dealerPC"
    TOKEN = "MY_TOKEN"
    
    # Create client
    client = StudioWebSocketClient(SERVER_URL, TABLE_ID, DEVICE_NAME, TOKEN)
    
    try:
        # Connect to server
        if not await client.connect():
            logger.error("Failed to connect to server")
            return
        
        logger.info("Interactive mode started. Type 'quit' to exit.")
        logger.info("Available commands:")
        logger.info("  sdp <status>     - Update SDP service status")
        logger.info("  idp <status>     - Update IDP service status")
        logger.info("  roulette <status> - Update roulette device status")
        logger.info("  shaker <status>  - Update shaker device status")
        logger.info("  broker <status>  - Update broker device status")
        logger.info("  zcam <status>    - Update ZCam device status")
        logger.info("  barcode <status> - Update barcode scanner status")
        logger.info("  nfc <status>     - Update NFC scanner status")
        logger.info("  custom <json>    - Send custom JSON update")
        logger.info("  quit             - Exit")
        
        while True:
            try:
                command = input("\nEnter command: ").strip()
                
                if command.lower() == 'quit':
                    break
                
                parts = command.split()
                if len(parts) < 2:
                    logger.info("Invalid command format. Use: <device> <status>")
                    continue
                
                device = parts[0].lower()
                status = parts[1].lower()
                
                # Validate status values
                valid_service_statuses = ['up', 'down', 'standby', 'calibration', 'exception']
                valid_device_statuses = ['up', 'down']
                
                if device in ['sdp', 'idp']:
                    if status not in valid_service_statuses:
                        logger.error(f"Invalid service status. Use: {', '.join(valid_service_statuses)}")
                        continue
                else:
                    if status not in valid_device_statuses:
                        logger.error(f"Invalid device status. Use: {', '.join(valid_device_statuses)}")
                        continue
                
                # Send status update
                if device == 'custom':
                    try:
                        custom_data = json.loads(status)
                        await client.send_status_update(custom_data)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON format")
                else:
                    await client.send_device_status(device, status)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error processing command: {e}")
        
    except Exception as e:
        logger.error(f"Error in interactive mode: {e}")
    
    finally:
        # Disconnect from server
        await client.disconnect()


async def main():
    """Main function."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        await interactive_mode()
    else:
        await demo_status_updates()


if __name__ == "__main__":
    asyncio.run(main())
