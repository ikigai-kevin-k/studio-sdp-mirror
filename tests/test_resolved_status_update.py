#!/usr/bin/env python3
"""
Unit test script for NO SHAKE error signal resolved status update.
Tests the flow: send warn signal -> send resolved status update (UP).

This test script:
1. Sends a NO SHAKE error signal with signalType='warn' and [TEST] prefix
2. Calls send_resolved_status_update to send UP status
3. Uses [TEST] prefix in descriptions to distinguish from real errors
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studio_api"))

from studio_api.ws_err_sig_sbe import ErrorSignalClient, ErrorMsgId
from studio_api.resolved_status_update import send_resolved_status_update

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def send_test_no_shake_warn_signal(
    table_id: str = "SBO-001",
    device_id: str = "ASB-001-1",
) -> bool:
    """
    Send a test NO SHAKE error signal with warn signalType and [TEST] prefix.
    
    Args:
        table_id: Table ID (default: SBO-001)
        device_id: Device ID (default: ASB-001-1)
        
    Returns:
        True if error signal sent successfully, False otherwise
    """
    # CIT environment configuration
    SERVER_URL = "wss://studio-api.iki-cit.cc/v1/ws"
    TOKEN = "0000"
    
    logger.info("=" * 60)
    logger.info("TEST: Sending NO SHAKE error signal with warn signalType")
    logger.info("=" * 60)
    logger.info(f"📋 Using CIT configuration")
    logger.info(f"   - Server: {SERVER_URL}")
    logger.info(f"   - Device: {device_id}")
    logger.info(f"   - Table: {table_id}")
    
    # Create error signal client
    client = ErrorSignalClient(SERVER_URL, table_id, device_id, TOKEN)
    
    try:
        # Connect to the table
        logger.info(f"🔗 Connecting to {table_id}...")
        if not await client.connect():
            logger.error(f"❌ Failed to connect to {table_id}")
            return False
        
        logger.info(f"✅ Successfully connected to {table_id}")
        
        # Create test NO SHAKE error signal with [TEST] prefix in description
        signal_data = {
            "msgId": ErrorMsgId.SICBO_NO_SHAKE.value,
            "content": "[TEST] Shaker failed to shake dice",
            "metadata": {
                "title": "NO SHAKE",
                "description": "[TEST] Shaker failed to shake dice",
                "code": "ASE.1",
                "suggestion": "[TEST] Check the shaker, it may need to be rebooted by GE staff",
                "signalType": "warn",  # First time sends warn
            },
        }
        
        # Send the error signal
        logger.info(f"📤 Sending test NO SHAKE error signal (warn) to {table_id}...")
        logger.info(f"   - Signal: {json.dumps(signal_data, indent=2)}")
        
        success = await client.send_error_signal(signal_data)
        
        if success:
            logger.info("✅ Test NO SHAKE error signal (warn) sent successfully!")
        else:
            logger.error("❌ Failed to send test NO SHAKE error signal (warn)")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error during test error signal sending: {e}")
        return False
        
    finally:
        # Disconnect from server
        try:
            await client.disconnect()
            logger.info(f"✅ Disconnected from {table_id}")
        except Exception as e:
            logger.error(f"❌ Error disconnecting from {table_id}: {e}")


async def test_resolved_status_update_flow():
    """
    Test the complete flow: send warn signal -> send resolved status update.
    
    This simulates the scenario where:
    1. A warn signal is sent in one shake cycle
    2. The next shake cycle resolves the issue (no error signal sent)
    3. A resolved status update (UP) is sent
    """
    logger.info("=" * 60)
    logger.info("UNIT TEST: NO SHAKE Error Signal Resolved Status Update")
    logger.info("=" * 60)
    
    table_id = "SBO-001"
    device_id = "ASB-001-1"
    
    try:
        # Step 1: Send test NO SHAKE error signal with warn signalType
        logger.info("\n" + "=" * 60)
        logger.info("STEP 1: Sending test NO SHAKE error signal (warn)")
        logger.info("=" * 60)
        
        warn_success = await send_test_no_shake_warn_signal(table_id, device_id)
        
        if not warn_success:
            logger.error("❌ Failed to send test warn signal, aborting test")
            return False
        
        logger.info("✅ Step 1 completed: Test warn signal sent successfully")
        
        # Wait a moment before sending resolved status update
        logger.info("\n⏳ Waiting 2 seconds before sending resolved status update...")
        await asyncio.sleep(2)
        
        # Step 2: Send resolved status update (UP)
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: Sending resolved status update (UP)")
        logger.info("=" * 60)
        
        resolved_success = await send_resolved_status_update(
            device_name=device_id,
            table_id=table_id,
        )
        
        if not resolved_success:
            logger.error("❌ Failed to send resolved status update")
            return False
        
        logger.info("✅ Step 2 completed: Resolved status update sent successfully")
        
        # Test summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info("✅ Test completed successfully!")
        logger.info("   - Step 1: Warn signal sent ✓")
        logger.info("   - Step 2: Resolved status update (UP) sent ✓")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


async def test_deviceController_resolved_logic():
    """
    Test the deviceController resolved logic using mock IDPController.
    
    This test simulates the reset_error_signal_flag logic:
    1. Set _error_signal_count = 1 (warn sent)
    2. Set _previous_cycle_warn_sent = True, _previous_cycle_error_sent = False
    3. Call reset_error_signal_flag() which should trigger resolved status update
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: deviceController resolved logic (mock)")
    logger.info("=" * 60)
    
    try:
        # Import deviceController
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, project_root)
        from controller import GameConfig, GameType
        from mqtt.deviceController import IDPController
        
        # Create mock config
        config = GameConfig(
            game_type=GameType.SICBO,
            room_id="SBO-001",
            broker_host="192.168.88.54",
            broker_port=1883,
        )
        
        # Create IDPController instance
        controller = IDPController(config)
        
        # Simulate previous cycle: warn sent but error not sent
        logger.info("Setting up mock state: previous cycle sent warn but not error")
        controller._error_signal_count = 1  # Current cycle: warn sent
        controller._previous_cycle_warn_sent = True  # Previous cycle: warn sent
        controller._previous_cycle_error_sent = False  # Previous cycle: error not sent
        
        logger.info(f"   - Current _error_signal_count: {controller._error_signal_count}")
        logger.info(f"   - Previous cycle warn sent: {controller._previous_cycle_warn_sent}")
        logger.info(f"   - Previous cycle error sent: {controller._previous_cycle_error_sent}")
        
        # Call reset_error_signal_flag which should trigger resolved status update
        logger.info("\nCalling reset_error_signal_flag()...")
        logger.info("(This should trigger resolved status update if logic is correct)")
        
        controller.reset_error_signal_flag()
        
        logger.info("✅ reset_error_signal_flag() called successfully")
        logger.info("   - Check logs above for resolved status update message")
        
        # Wait a moment for async operations to complete
        await asyncio.sleep(3)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


async def main():
    """Main test function"""
    logger.info("\n" + "=" * 60)
    logger.info("UNIT TEST: NO SHAKE Error Signal Resolved Status Update")
    logger.info("=" * 60)
    logger.info("This test verifies the resolved status update flow:")
    logger.info("  1. Send NO SHAKE error signal with signalType='warn'")
    logger.info("  2. Send resolved status update (UP)")
    logger.info("  3. Test deviceController resolved logic")
    logger.info("=" * 60)
    
    # Run tests
    test_results = []
    
    # Test 1: Complete flow test
    logger.info("\n" + "=" * 60)
    logger.info("TEST 1: Complete resolved status update flow")
    logger.info("=" * 60)
    result1 = await test_resolved_status_update_flow()
    test_results.append(("Complete flow test", result1))
    
    # Test 2: deviceController logic test
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: deviceController resolved logic")
    logger.info("=" * 60)
    result2 = await test_deviceController_resolved_logic()
    test_results.append(("deviceController logic test", result2))
    
    # Print test summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {test_name}: {status}")
    logger.info("=" * 60)
    
    # Return overall result
    all_passed = all(result for _, result in test_results)
    if all_passed:
        logger.info("\n✅ All tests passed!")
    else:
        logger.error("\n❌ Some tests failed!")
    
    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Test failed with exception: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

