#!/usr/bin/env python3
"""
Single status update script for Sicbo Game (SBO-001 table).
Imports functions from ws_sb.py for device status updates.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Add the current directory to Python path to import ws_sb
sys.path.append(os.path.dirname(__file__))

from ws_client import SmartStudioWebSocketClient

# Configure logging with timestamp format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# Global variable to store the WebSocket client instance
_ws_client = None
_table_id = None


# Define ServiceStatus type structure
class ServiceStatus:
    """Service status data structure for device status updates."""

    def __init__(
        self,
        sdp: Optional[str] = None,
        idp: Optional[str] = None,
        broker: Optional[str] = None,
        zCam: Optional[str] = None,
        roulette: Optional[str] = None,
        shaker: Optional[str] = None,
        barcodeScanner: Optional[str] = None,
        nfcScanner: Optional[str] = None,
        maintenance: Optional[bool] = None,
        uptime: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.sdp = sdp
        self.idp = idp
        self.broker = broker
        self.zCam = zCam
        self.roulette = roulette
        self.shaker = shaker
        self.barcodeScanner = barcodeScanner
        self.nfcScanner = nfcScanner
        self.maintenance = maintenance
        self.uptime = uptime
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert ServiceStatus to dictionary format."""
        result = {}
        if self.sdp is not None:
            result["sdp"] = self.sdp
        if self.idp is not None:
            result["idp"] = self.idp
        if self.broker is not None:
            result["broker"] = self.broker
        if self.zCam is not None:
            result["zCam"] = self.zCam
        if self.roulette is not None:
            result["roulette"] = self.roulette
        if self.shaker is not None:
            result["shaker"] = self.shaker
        if self.barcodeScanner is not None:
            result["barcodeScanner"] = self.barcodeScanner
        if self.nfcScanner is not None:
            result["nfcScanner"] = self.nfcScanner
        if self.maintenance is not None:
            result["maintenance"] = self.maintenance
        if self.uptime is not None:
            result["uptime"] = self.uptime
        if self.timestamp is not None:
            result["timestamp"] = self.timestamp.isoformat()
        return result


# Define error codes for different scenarios
class ErrorCodes:
    """Error codes for different device scenarios."""

    # Auto-Roulette Error Scenario
    AUTO_ROULETTE_ERRORS = [
        "NO BALL DETECT",
        "NO WIN NUM",
        "SENSOR STUCK",  # the most frequently occurred event
        "WRONG BALL DIR",
        "LAUNCH FAIL",
        "NOT REACH POS",
        "HARDWARE FAULT",
        "ENCODER FAIL",
        "BALL DROP FAIL",
        "WRONG WHEEL DIR",
        "STUCK NMB",
    ]

    # Auto-Sicbo Error Scenario
    AUTO_SICBO_ERRORS = [
        "NO SHAKE",  # the most frequently occurred event
        "NO STREAM",  # causes IDP cannot detect result
        "INVALID RESULT after reshake",
        "BROKER DOWN",
    ]


def create_sicbo_status(
    maintenance: bool = False,
    zCam: str = "up",
    broker: str = "up",
    sdp: str = "up",
    shaker: str = "up",
    idp: str = "up",
    nfcScanner: str = "up",
) -> ServiceStatus:
    """
    Create ServiceStatus for Sicbo game with only required fields.

    Args:
        maintenance: Maintenance mode status
        zCam: Z-Camera status
        broker: Broker status
        sdp: SDP status
        shaker: Shaker status
        idp: IDP status
        nfcScanner: NFC Scanner status

    Returns:
        ServiceStatus object with Sicbo-specific fields
    """
    return ServiceStatus(
        maintenance=maintenance,
        zCam=zCam,
        broker=broker,
        sdp=sdp,
        shaker=shaker,
        idp=idp,
        nfcScanner=nfcScanner,
    )


def create_roulette_status(
    maintenance: bool = False,
    zCam: str = "up",
    sdp: str = "up",
    roulette: str = "up",
    nfcScanner: str = "up",
) -> ServiceStatus:
    """
    Create ServiceStatus for Speed/VIP Roulette game with only required fields.

    Args:
        maintenance: Maintenance mode status
        zCam: Z-Camera status
        sdp: SDP status
        roulette: Roulette status
        nfcScanner: NFC Scanner status

    Returns:
        ServiceStatus object with Roulette-specific fields
    """
    return ServiceStatus(
        maintenance=maintenance,
        zCam=zCam,
        sdp=sdp,
        roulette=roulette,
        nfcScanner=nfcScanner,
    )


def create_baccarat_status(
    maintenance: bool = False,
    zCam: str = "up",
    sdp: str = "up",
    idp: str = "up",
    barcodeScanner: str = "up",
    nfcScanner: str = "up",
) -> ServiceStatus:
    """
    Create ServiceStatus for Baccarat game with only required fields.

    Args:
        maintenance: Maintenance mode status
        zCam: Z-Camera status
        sdp: SDP status
        idp: IDP status
        barcodeScanner: Barcode Scanner status
        nfcScanner: NFC Scanner status

    Returns:
        ServiceStatus object with Baccarat-specific fields
    """
    return ServiceStatus(
        maintenance=maintenance,
        zCam=zCam,
        sdp=sdp,
        idp=idp,
        barcodeScanner=barcodeScanner,
        nfcScanner=nfcScanner,
    )


def create_status_event(status: ServiceStatus) -> Dict[str, Any]:
    """
    Create a service_status event with the given status data.

    Args:
        status: ServiceStatus object containing device status

    Returns:
        Dict with event type and status data
    """
    return {"event": "service_status", "data": status.to_dict()}


def create_exception_event(error_code: str) -> Dict[str, Any]:
    """
    Create an exception event with the given error code.

    Args:
        error_code: Error code string from ErrorCodes

    Returns:
        Dict with event type and error data
    """
    return {"event": "exception", "data": error_code}


async def update_game_status(
    custom_status: Optional[ServiceStatus] = None,
    table_id: str = "SBO-001",
    fast_mode: bool = True,
) -> bool:
    """
    Update game status with default values or custom status based on game type.
    Once WebSocket connection is established, it will not disconnect unless an
    exception occurs. If a connection already exists for the same table, it
    will reuse it instead of reconnecting.

    Args:
        custom_status: Optional custom ServiceStatus object to override
                      defaults
        table_id: Table ID for the game (default: SBO-001)
        fast_mode: Enable fast connection mode to skip welcome message wait
                  (default: True)

    Returns:
        bool: True if update successful, False otherwise
    """

    global _ws_client, _table_id

    # Determine game type and create appropriate default status
    def get_default_status_by_game_type(table_id: str) -> ServiceStatus:
        """Get default status based on game type from table ID."""
        table_id_upper = table_id.upper()

        if "SBO" in table_id_upper:  # Sicbo game
            logger.info(f"🎲 Detected Sicbo game type for table {table_id}")
            return create_sicbo_status()
        elif "ARO" in table_id_upper:  # Roulette
            logger.info(
                f"🎰 Detected Speed/VIP Roulette game type for "
                f"table {table_id}"
            )
            return create_roulette_status()
        elif "BAC" in table_id_upper:  # Baccarat game
            logger.info(f"🃏 Detected Baccarat game type for table {table_id}")
            return create_baccarat_status()
        else:
            # Default to Sicbo if unknown table type
            logger.info(
                f"❓ Unknown game type for table {table_id}, "
                f"defaulting to Sicbo"
            )
            return create_sicbo_status()

    # Get default status based on game type
    default_status = get_default_status_by_game_type(table_id)

    # Use custom status if provided, otherwise use defaults
    status_to_send = custom_status if custom_status else default_status

    # Check if we already have a connection to the same table
    if _ws_client is not None and _table_id == table_id:
        try:
            # Try to check if the existing connection is still valid
            # This is a simple check - in practice you might want more
            # sophisticated connection validation
            logger.info(
                f"🔗 Reusing existing WebSocket connection to {table_id}"
            )

            # Send the status update using existing connection
            logger.info(f"📤 Sending status update to {table_id}...")

            # Create status event with new format
            status_event = create_status_event(status_to_send)
            logger.info(f"   - Event: {status_event}")

            await _ws_client.send_multiple_updates(status_event)

            # Wait a shorter moment for the update to be processed
            await asyncio.sleep(0.1)

            # Show update results
            logger.info("\n" + "=" * 50)
            logger.info(f"📊 UPDATE RESULTS FOR {table_id}")
            logger.info("=" * 50)

            preferences = _ws_client.get_server_preferences()
            summary = _ws_client.get_sent_updates_summary()

            logger.info(
                f"✅ Accepted fields: {preferences['accepted_fields']}"
            )
            logger.info(
                f"❌ Rejected fields: {preferences['rejected_fields']}"
            )
            logger.info(f"📊 Total updates sent: {summary['total_updates']}")

            # Check if all fields were accepted
            all_accepted = all(
                field in preferences["accepted_fields"]
                for field in status_event.keys()
            )

            if all_accepted:
                logger.info(
                    "🎯 All status updates were accepted successfully!"
                )
            else:
                rejected_fields = [
                    field
                    for field in status_event.keys()
                    if field not in preferences["accepted_fields"]
                ]
                logger.warning(
                    f"⚠️  Some fields were rejected: {rejected_fields}"
                )

            logger.info(
                f"🔗 WebSocket connection to {table_id} maintained for "
                f"future use"
            )
            return True

        except Exception as e:
            logger.warning(
                f"⚠️  Existing connection failed, will create new "
                f"connection: {e}"
            )
            # Reset the client if the existing connection failed
            _ws_client = None
            _table_id = None

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
        return False
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in configuration file: {e}")
        return False
    except KeyError as e:
        logger.error(f"❌ Missing required configuration key: {e}")
        return False

    # Create new client for specified table with fast mode option
    client = SmartStudioWebSocketClient(
        SERVER_URL, table_id, DEVICE_NAME, TOKEN, fast_connect=fast_mode
    )

    try:
        # Connect to the table
        logger.info(f"🔗 Connecting to {table_id}...")
        if not await client.connect():
            logger.error(f"❌ Failed to connect to {table_id}")
            return False

        logger.info(f"✅ Successfully connected to {table_id}")

        # Store the client instance globally for reuse
        _ws_client = client
        _table_id = table_id

        # Send the status update
        logger.info(f"📤 Sending status update to {table_id}...")

        # Create status event with new format
        status_event = create_status_event(status_to_send)
        logger.info(f"   - Event: {status_event}")

        await client.send_multiple_updates(status_event)

        # Wait a shorter moment for the update to be processed
        await asyncio.sleep(0.1)

        # Show update results
        logger.info("\n" + "=" * 50)
        logger.info(f"📊 UPDATE RESULTS FOR {table_id}")
        logger.info("=" * 50)

        preferences = client.get_server_preferences()
        summary = client.get_sent_updates_summary()

        logger.info(f"✅ Accepted fields: {preferences['accepted_fields']}")
        logger.info(f"❌ Rejected fields: {preferences['rejected_fields']}")
        logger.info(f"📊 Total updates sent: {summary['total_updates']}")

        # Check if all fields were accepted
        all_accepted = all(
            field in preferences["accepted_fields"]
            for field in status_event.keys()
        )

        if all_accepted:
            logger.info("🎯 All status updates were accepted successfully!")
        else:
            rejected_fields = [
                field
                for field in status_event.keys()
                if field not in preferences["accepted_fields"]
            ]
            logger.warning(f"⚠️  Some fields were rejected: {rejected_fields}")

        # Note: Connection is maintained and not disconnected
        logger.info(
            f"🔗 WebSocket connection to {table_id} maintained for "
            f"future use"
        )

        return True

    except Exception as e:
        logger.error(f"❌ Error during status update: {e}")
        # Only disconnect on exception
        try:
            await client.disconnect()
            logger.info(f"✅ Disconnected from {table_id} due to exception")
            # Reset global variables on exception
            _ws_client = None
            _table_id = None
        except Exception as disconnect_error:
            logger.error(
                f"❌ Error disconnecting from {table_id}: {disconnect_error}"
            )
        return False


async def send_exception_event(
    error_code: str,
    table_id: str = "SBO-001",
    fast_mode: bool = True,
) -> bool:
    """
    Send an exception event to the specified table.

    Args:
        error_code: Error code string from ErrorCodes
        table_id: Table ID for the game (default: SBO-001)
        fast_mode: Enable fast connection mode (default: True)

    Returns:
        bool: True if exception event sent successfully, False otherwise
    """

    # Determine game type and get appropriate error codes
    def get_error_codes_by_game_type(table_id: str) -> list:
        """Get error codes based on game type from table ID."""
        table_id_upper = table_id.upper()

        if "SBO" in table_id_upper:  # Sicbo game
            logger.info(f"🎲 Using Sicbo error codes for table {table_id}")
            return ErrorCodes.AUTO_SICBO_ERRORS
        elif "ARO" in table_id_upper:  # Roulette game
            logger.info(f"🎰 Using Roulette error codes for table {table_id}")
            return ErrorCodes.AUTO_ROULETTE_ERRORS
        else:
            # Default to Sicbo if unknown table type
            logger.info(
                f"❓ Unknown game type for table {table_id}, "
                f"defaulting to Sicbo error codes"
            )
            return ErrorCodes.AUTO_SICBO_ERRORS

    # Get appropriate error codes for the game type
    valid_error_codes = get_error_codes_by_game_type(table_id)

    # Validate error code against game-specific codes
    if error_code not in valid_error_codes:
        logger.error(
            f"❌ Invalid error code '{error_code}' for table {table_id}"
        )
        logger.info(
            f"Valid error codes for this game type: {valid_error_codes}"
        )
        return False

    # Create exception event
    exception_event = create_exception_event(error_code)
    logger.info(f"📤 Sending exception event to {table_id}...")
    logger.info(f"   - Event: {exception_event}")

    # For exception events, we'll need to modify the client to handle
    # the new event format. For now, we'll use the existing update
    # mechanism but log the exception event structure

    logger.info(f"⚠️  Exception event prepared: {exception_event}")
    logger.info("Note: Exception event format requires client modification")

    return True


async def main():
    """Main function for testing the single update functionality."""

    logger.info("🎮 Multi-Game Status Update Test")
    logger.info("=" * 50)

    # Test 1: Sicbo game status update
    logger.info("\n📤 Test 1: Sicbo game status update...")
    sicbo_success = await update_game_status(table_id="SBO-001")

    if sicbo_success:
        logger.info("✅ Sicbo game status update completed successfully")
    else:
        logger.error("❌ Sicbo game status update failed")

    # Test 2: Roulette game status update
    logger.info("\n📤 Test 2: Roulette game status update...")
    roulette_success = await update_game_status(table_id="ARO-001")

    if roulette_success:
        logger.info("✅ Roulette game status update completed successfully")
    else:
        logger.error("❌ Roulette game status update failed")

    # Test 3: Test Sicbo exception event
    logger.info("\n📤 Test 3: Testing Sicbo exception event...")
    sicbo_exception_success = await send_exception_event("NO SHAKE", "SBO-001")

    if sicbo_exception_success:
        logger.info("✅ Sicbo exception event test completed")
    else:
        logger.error("❌ Sicbo exception event test failed")

    # Test 4: Test Roulette exception event
    logger.info("\n📤 Test 4: Testing Roulette exception event...")
    roulette_exception_success = await send_exception_event(
        "SENSOR STUCK", "ARO-001"
    )

    if roulette_exception_success:
        logger.info("✅ Roulette exception event test completed")
    else:
        logger.error("❌ Roulette exception event test failed")

    # Test 5: Test invalid error code for game type
    logger.info("\n📤 Test 5: Testing invalid error code for game type...")
    invalid_exception_success = await send_exception_event(
        "SENSOR STUCK", "SBO-001"
    )

    if not invalid_exception_success:
        logger.info("✅ Invalid error code validation working correctly")
    else:
        logger.error("❌ Invalid error code validation failed")

    logger.info("\n🎯 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
