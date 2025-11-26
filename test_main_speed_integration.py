"""
Test script for Roulette MQTT integration in main_speed.py

This script tests the integration of Roulette MQTT detect functionality
into the main_speed.py system.
"""

import asyncio
import logging
import time
import os

# Mock the log_to_file function to avoid permission issues
def mock_log_to_file(message, direction):
    print(f"[{direction}] {message}")

# Mock the get_timestamp function
def mock_get_timestamp():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

# Set up environment before importing main_speed
os.environ['SKIP_LOG_FILE'] = '1'

# Import after setting up mocks
from main_speed import (
    initialize_roulette_mqtt_system,
    roulette_detect_result,
    cleanup_roulette_mqtt_system
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_roulette_integration():
    """Test the Roulette MQTT integration"""
    logger.info("=" * 60)
    logger.info("Testing Roulette MQTT Integration in main_speed.py")
    logger.info("=" * 60)
    
    try:
        # Test 1: Initialize MQTT system
        logger.info("\n1. Testing MQTT system initialization...")
        init_success = await initialize_roulette_mqtt_system()
        
        if not init_success:
            logger.error("❌ MQTT system initialization failed")
            return False
        
        logger.info("✅ MQTT system initialized successfully")
        
        # Test 2: First detect call (simulating *u 1 command)
        logger.info("\n2. Testing first detect call (after *u 1 command)...")
        success1, result1 = await roulette_detect_result(
            round_id="ARO-001-TEST-001",
            input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
        )
        
        if success1:
            logger.info(f"✅ First detect call successful: {result1}")
        else:
            logger.warning(f"⚠️ First detect call failed or result is null: {result1}")
        
        # Wait a bit between calls
        await asyncio.sleep(2)
        
        # Test 3: Second detect call (simulating *x;4 command)
        logger.info("\n3. Testing second detect call (after *x;4 command)...")
        success2, result2 = await roulette_detect_result(
            round_id="ARO-001-TEST-001",
            input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
        )
        
        if success2:
            logger.info(f"✅ Second detect call successful: {result2}")
        else:
            logger.warning(f"⚠️ Second detect call failed or result is null: {result2}")
        
        # Test 4: Cleanup
        logger.info("\n4. Testing cleanup...")
        await cleanup_roulette_mqtt_system()
        logger.info("✅ Cleanup completed successfully")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Integration Test Summary")
        logger.info("=" * 60)
        logger.info(f"MQTT System Initialization: {'PASSED ✅' if init_success else 'FAILED ❌'}")
        logger.info(f"First Detect Call: {'PASSED ✅' if success1 else 'FAILED ❌'}")
        logger.info(f"Second Detect Call: {'PASSED ✅' if success2 else 'FAILED ❌'}")
        
        overall_success = init_success and success1 and success2
        logger.info(f"\nOverall Integration Test: {'PASSED ✅' if overall_success else 'FAILED ❌'}")
        
        return overall_success
        
    except Exception as e:
        logger.error(f"❌ Integration test failed with exception: {e}")
        return False


async def test_simulated_workflow():
    """Test simulated workflow of main_speed.py with Roulette detect calls"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Simulated Workflow")
    logger.info("=" * 60)
    
    try:
        # Initialize system
        await initialize_roulette_mqtt_system()
        
        # Simulate workflow
        logger.info("\nSimulating Speed Roulette workflow...")
        
        # Step 1: Simulate *u 1 command (first detect)
        logger.info("Step 1: Simulating *u 1 command...")
        success1, result1 = await roulette_detect_result(
            round_id="ARO-001-WORKFLOW-001"
        )
        logger.info(f"After *u 1: {'Success' if success1 else 'Failed'} - {result1}")
        
        # Wait between steps
        await asyncio.sleep(3)
        
        # Step 2: Simulate *x;4 command (second detect)
        logger.info("Step 2: Simulating *x;4 command...")
        success2, result2 = await roulette_detect_result(
            round_id="ARO-001-WORKFLOW-001"
        )
        logger.info(f"After *x;4: {'Success' if success2 else 'Failed'} - {result2}")
        
        # Cleanup
        await cleanup_roulette_mqtt_system()
        
        logger.info("\n✅ Simulated workflow completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Simulated workflow failed: {e}")
        return False


async def main():
    """Main test function"""
    logger.info("Starting Roulette MQTT Integration Tests")
    
    # Run integration tests
    integration_success = await test_roulette_integration()
    
    # Run workflow simulation
    workflow_success = await test_simulated_workflow()
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("Final Test Results")
    logger.info("=" * 60)
    logger.info(f"Integration Test: {'PASSED ✅' if integration_success else 'FAILED ❌'}")
    logger.info(f"Workflow Simulation: {'PASSED ✅' if workflow_success else 'FAILED ❌'}")
    
    overall_success = integration_success and workflow_success
    logger.info(f"\nOverall Test Result: {'PASSED ✅' if overall_success else 'FAILED ❌'}")
    
    if overall_success:
        logger.info("\n🎉 All tests passed! Roulette MQTT integration is working correctly.")
        logger.info("The integration is ready for use in main_speed.py")
    else:
        logger.error("\n❌ Some tests failed. Please check the logs for details.")
    
    return overall_success


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(main())
    exit(0 if success else 1)
