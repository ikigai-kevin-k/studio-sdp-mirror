#!/usr/bin/env python3
"""
Generic resolved status update module for error signal resolution.
Compatible with main_sicbo.py, main_speed.py, and main_vip.py.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Optional

# Add the current directory to Python path to import WebSocket client
sys.path.append(os.path.dirname(__file__))

from ws_client import SmartStudioWebSocketClient, StudioDeviceStatusEnum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def send_resolved_status_update(
    device_name: str,
    table_id: str = "SBO-001",
    server_url: str = "wss://studio-api.iki-cit.cc/v1/ws",
    token: str = "0000",
) -> bool:
    """
    Send resolved status update (UP) when an error signal is resolved.
    
    This function sends a status update indicating that a device/service
    has recovered from a previous error state.
    
    Args:
        device_name: Device name (e.g., "ASB-001-1", "ARO-001-1", "ARO-002-2")
        table_id: Table ID (default: SBO-001 for Sicbo)
        server_url: WebSocket server URL (default: wss://studio-api.iki-cit.cc/v1/ws)
        token: Authentication token (default: 0000)
        
    Returns:
        True if status update sent successfully, False otherwise
    """
    try:
        # Create WebSocket connection URL according to spec
        # Format: wss://studio-api.iki-cit.cc/v1/ws?id={device_name}&token={token}
        connection_url = f"{server_url}?id={device_name}&token={token}"
        
        # Create WebSocket client
        client = SmartStudioWebSocketClient(
            server_url=server_url,
            table_id=table_id,
            device_name=device_name,
            token=token,
            fast_connect=True,
        )
        
        # Connect to the server
        logger.info(f"Connecting to {table_id} for resolved status update...")
        logger.info(f"   - Connection URL: {connection_url}")
        if not await client.connect():
            logger.error(f"Failed to connect to {table_id}")
            return False
        
        logger.info(f"Successfully connected to {table_id}")
        
        # Create status update message according to spec
        # Format: { event: 'status', data: { status: 'up' } }
        status_message = {
            "event": "status",
            "data": {
                "status": StudioDeviceStatusEnum.UP,
            },
        }
        
        # Send the status update
        logger.info(
            f"Sending resolved status update (UP) for {device_name} on {table_id}..."
        )
        logger.info(f"   - Message: {json.dumps(status_message, indent=2)}")
        
        # Send status update using the client's send_status_update method
        # The status_message already has the correct format: { event: 'status', data: { status: 'up' } }
        try:
            # Send the status message directly via websocket
            await client.websocket.send(json.dumps(status_message))
            logger.info("✅ Resolved status update sent successfully")
            
            # Wait briefly for response
            try:
                response = await asyncio.wait_for(
                    client.websocket.recv(), timeout=2.0
                )
                logger.info(f"📥 Server response: {response}")
            except asyncio.TimeoutError:
                logger.warning("⏰ No response received for resolved status update")
            
            return True
            
        except Exception as send_error:
            logger.error(f"Failed to send resolved status update: {send_error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during resolved status update: {e}")
        return False
        
    finally:
        # Disconnect from server
        try:
            if client and client.websocket:
                await client.disconnect()
                logger.info(f"✅ Disconnected from {table_id}")
        except Exception as e:
            logger.error(f"❌ Error disconnecting from {table_id}: {e}")


def send_resolved_status_update_sync(
    device_name: str,
    table_id: str = "SBO-001",
    server_url: str = "wss://studio-api.iki-cit.cc/v1/ws",
    token: str = "0000",
) -> bool:
    """
    Synchronous wrapper for send_resolved_status_update.
    
    Args:
        device_name: Device name
        table_id: Table ID
        server_url: WebSocket server URL
        token: Authentication token
        
    Returns:
        True if status update sent successfully, False otherwise
    """
    try:
        return asyncio.run(
            send_resolved_status_update(device_name, table_id, server_url, token)
        )
    except Exception as e:
        logger.error(f"Failed to send resolved status update (sync): {e}")
        return False

