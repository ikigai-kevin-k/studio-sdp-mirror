#!/usr/bin/env python3
"""
Test script for sending WebSocket device info to SBO-001 table.
Uses functions defined in ws_client.py
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

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


async def test_sbo_001_device_info():
    """Test sending device info to SBO-001 table (Sicbo Game)."""

    # Load configuration from ws.json
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "conf", "ws.json"
    )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        SERVER_URL = config["server_url"]
        DEVICE_NAME = config["device_name"]
        TOKEN = config["token"]

        logger.info(f"📋 Loaded configuration from {config_path}")
        logger.info(f"   - Server: {SERVER_URL}")
        logger.info(f"   - Device: {DEVICE_NAME}")

    except FileNotFoundError:
        logger.error(f"❌ Configuration file not found: {config_path}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in configuration file: {e}")
        return
    except KeyError as e:
        logger.error(f"❌ Missing required configuration key: {e}")
        return

    # Create client for SBO-001
    table_id = "SBO-001"
    client = SmartStudioWebSocketClient(
        SERVER_URL, table_id, DEVICE_NAME, TOKEN
    )

    try:
        # Connect to SBO-001
        logger.info(f"🔗 Connecting to {table_id}...")
        if not await client.connect():
            logger.error(f"❌ Failed to connect to {table_id}")
            return

        logger.info(f"✅ Successfully connected to {table_id}")
        logger.info(
            "🎲 SBO-001 is a Sicbo Game table - testing relevant devices only"
        )

        # Test 1: Send individual device status updates (Sicbo Game devices)
        logger.info(
            "\n📤 Test 1: Sending individual device status updates (Sicbo Game)..."
        )

        # Send SDP status
        sdp_status = StudioServiceStatusEnum.get_random_status()
        await client.send_device_status("sdp", sdp_status)
        logger.info(f"   - SDP status: {sdp_status}")

        await asyncio.sleep(0.5)

        # Send IDP status
        idp_status = StudioServiceStatusEnum.get_random_status()
        await client.send_device_status("idp", idp_status)
        logger.info(f"   - IDP status: {idp_status}")

        await asyncio.sleep(0.5)

        # Send Shaker status (for dice)
        shaker_status = StudioServiceStatusEnum.get_random_status()
        await client.send_device_status("shaker", shaker_status)
        logger.info(f"   - Shaker status: {shaker_status}")

        await asyncio.sleep(0.5)

        # Send Broker status
        broker_status = StudioServiceStatusEnum.get_random_status()
        await client.send_device_status("broker", broker_status)
        logger.info(f"   - Broker status: {broker_status}")

        await asyncio.sleep(0.5)

        # Send Z-Camera status
        zcam_status = StudioServiceStatusEnum.get_random_status()
        await client.send_device_status("zCam", zcam_status)
        logger.info(f"   - Z-Camera status: {zcam_status}")

        await asyncio.sleep(0.5)

        # Send Maintenance status
        maintenance_status = StudioMaintenanceStatusEnum.get_random_status()
        await client.send_status_update({"maintenance": maintenance_status})
        logger.info(f"   - Maintenance status: {maintenance_status}")

        await asyncio.sleep(1.0)

        # Test 2: Send multiple updates at once (Sicbo Game devices)
        logger.info(
            "\n📤 Test 2: Sending multiple updates at once (Sicbo Game)..."
        )

        multiple_updates = {
            "sdp": StudioServiceStatusEnum.get_random_status(),
            "idp": StudioServiceStatusEnum.get_random_status(),
            "shaker": StudioServiceStatusEnum.get_random_status(),
            "broker": StudioServiceStatusEnum.get_random_status(),
            "zCam": StudioServiceStatusEnum.get_random_status(),
            "maintenance": StudioMaintenanceStatusEnum.get_random_status(),
        }

        await client.send_multiple_updates(multiple_updates)
        logger.info(
            f"   - Sent {len(multiple_updates)} updates simultaneously"
        )

        await asyncio.sleep(1.0)

        # Test 3: Send specific status combinations (Sicbo Game devices)
        logger.info(
            "\n📤 Test 3: Sending specific status combinations (Sicbo Game)..."
        )

        # All devices UP
        all_up = {
            "sdp": "up",
            "idp": "up",
            "shaker": "up",
            "broker": "up",
            "zCam": "up",
            "maintenance": False,
        }

        await client.send_multiple_updates(all_up)
        logger.info("   - Sent all devices UP status")

        await asyncio.sleep(1.0)

        # All devices DOWN
        all_down = {
            "sdp": "down",
            "idp": "down",
            "shaker": "down",
            "broker": "down",
            "zCam": "down",
            "maintenance": True,
        }

        await client.send_multiple_updates(all_down)
        logger.info("   - Sent all devices DOWN status")

        await asyncio.sleep(1.0)

        # Show results
        logger.info("\n" + "=" * 60)
        logger.info(f"📊 TEST RESULTS FOR {table_id}")
        logger.info("=" * 60)

        preferences = client.get_server_preferences()
        summary = client.get_sent_updates_summary()

        logger.info(f"✅ Accepted fields: {preferences['accepted_fields']}")
        logger.info(f"❌ Rejected fields: {preferences['rejected_fields']}")
        logger.info(f"📊 Total updates sent: {summary['total_updates']}")

        logger.info(f"\n📋 Detailed Update Analysis:")
        for i, update in enumerate(summary["updates"], 1):
            field = list(update["data"].keys())[0]
            value = list(update["data"].values())[0]
            status = "✅" if field in preferences["accepted_fields"] else "❌"
            logger.info(f"  {i:2d}. {status} {field}: {value}")

        logger.info("\n🎯 Test completed successfully!")

    except Exception as e:
        logger.error(f"❌ Error during test: {e}")

    finally:
        # Disconnect from server
        try:
            await client.disconnect()
            logger.info(f"✅ Disconnected from {table_id}")
        except Exception as e:
            logger.error(f"❌ Error disconnecting from {table_id}: {e}")


async def main():
    """Main function."""
    await test_sbo_001_device_info()


if __name__ == "__main__":
    asyncio.run(main())
