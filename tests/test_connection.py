#!/usr/bin/env python3
"""
Test script to verify WebSocket connection between mock server and client.
"""

import asyncio
import json
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def test_client_connection():
    """Test connecting to mock server with the same format as main_speed.py."""
    # Use the same connection format as SmartStudioWebSocketClient
    server_url = "ws://localhost:8081/v1/ws"
    token = "0000"
    table_id = "ARO-001"
    device_name = "ARO-001-1"
    
    connection_url = f"{server_url}?token={token}&id={table_id}&device={device_name}"
    
    logger.info(f"🔗 Connecting to: {connection_url}")
    
    try:
        async with websockets.connect(connection_url) as websocket:
            logger.info("✅ Connected successfully!")
            
            # Wait for welcome message
            try:
                welcome = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                welcome_data = json.loads(welcome)
                logger.info(f"📨 Received welcome: {welcome_data}")
            except asyncio.TimeoutError:
                logger.warning("⏰ No welcome message received")
            
            # Wait for SDP down signal
            logger.info("⏳ Waiting for SDP down signal...")
            logger.info("💡 In another terminal, run:")
            logger.info("   python tests/mock_studio_api_server.py --send-sdp-down --table-id ARO-001 --device-name ARO-001-1 --port 8081")
            
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(message)
                logger.info(f"📨 Received message: {data}")
                
                # Check if it's SDP down signal
                if data.get("sdp") == "down":
                    logger.info("✅ Received SDP down signal!")
                    return True
                else:
                    logger.warning(f"⚠️  Received message but not SDP down: {data}")
                    return False
            except asyncio.TimeoutError:
                logger.warning("⏰ No message received within 30 seconds")
                return False
                
    except Exception as e:
        logger.error(f"❌ Connection error: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("WebSocket Connection Test")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This script tests the connection format used by main_speed.py")
    logger.info("Make sure mock_studio_api_server.py is running on port 8081")
    logger.info("")
    
    success = await test_client_connection()
    
    if success:
        logger.info("")
        logger.info("✅ Test passed!")
    else:
        logger.info("")
        logger.info("❌ Test failed or timeout")
        logger.info("💡 Check if mock server is running and try again")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test error: {e}")
        sys.exit(1)

