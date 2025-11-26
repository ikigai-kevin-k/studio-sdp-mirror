#!/usr/bin/env python3
"""
Test script for Mock StudioAPI Server.

This script demonstrates how to use the mock server to send SDP down signals.
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from tests.mock_studio_api_server import MockStudioAPIServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def test_sdp_down_signal():
    """
    Test sending SDP down signal to connected clients.
    """
    logger.info("=" * 60)
    logger.info("Mock StudioAPI Server - SDP Down Signal Test")
    logger.info("=" * 60)

    # Create mock server
    server = MockStudioAPIServer(host="localhost", port=8080)

    # Start server in background
    logger.info("🚀 Starting mock server...")
    server_task = asyncio.create_task(server.start())

    # Wait for server to start and clients to connect
    logger.info("⏳ Waiting 5 seconds for clients to connect...")
    logger.info("💡 Make sure main_speed.py is running and connected")
    await asyncio.sleep(5)

    # List connected clients
    clients = server.list_connected_clients()
    if clients:
        logger.info(f"📋 Found {len(clients)} connected client(s):")
        for client_id, info in clients.items():
            logger.info(
                f"  - {client_id}: "
                f"table_id={info.get('table_id')}, "
                f"device={info.get('device_name')}"
            )
    else:
        logger.warning("⚠️  No clients connected yet")
        logger.info("💡 Start main_speed.py and wait for it to connect")

    # Send SDP down signal
    logger.info("\n📤 Sending SDP down signal...")
    success = await server.send_sdp_down_signal(
        table_id="ARO-001", device_name="ARO-001-1"
    )

    if success:
        logger.info("✅ SDP down signal sent successfully")
        logger.info("💡 Check main_speed.py logs to verify mode switch")
    else:
        logger.warning("⚠️  Failed to send SDP down signal")
        logger.info("💡 Make sure a client is connected")

    # Wait a bit to see the result
    await asyncio.sleep(2)

    # Optionally send alternative format
    logger.info("\n📤 Sending SDP down signal (alternative format)...")
    await server.send_sdp_down_signal_alternative_format(
        table_id="ARO-001", device_name="ARO-001-1"
    )

    logger.info("\n✅ Test completed")
    logger.info("💡 Server will continue running. Press Ctrl+C to stop")

    # Keep server running
    try:
        await server_task
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping server...")
        await server.stop()


async def test_interactive_mode():
    """
    Test interactive mode for manual signal sending.
    """
    logger.info("=" * 60)
    logger.info("Mock StudioAPI Server - Interactive Mode")
    logger.info("=" * 60)

    server = MockStudioAPIServer(host="localhost", port=8080)

    # Start server in background
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(1)

    # Import and run interactive mode
    from tests.mock_studio_api_server import interactive_mode

    await interactive_mode(server)

    await server.stop()


async def main():
    """Main test function."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Mock StudioAPI Server")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode",
    )

    args = parser.parse_args()

    if args.interactive:
        await test_interactive_mode()
    else:
        await test_sdp_down_signal()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test error: {e}")
        sys.exit(1)

