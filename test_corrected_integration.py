"""
Test script for corrected Roulette MQTT integration

This script tests the corrected integration without circular import issues.
"""

import asyncio
import logging
import time
from roulette_mqtt_detect import (
    initialize_roulette_mqtt_system,
    roulette_detect_result,
    cleanup_roulette_mqtt_system,
    call_roulette_detect_async
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_corrected_integration():
    """Test the corrected Roulette MQTT integration"""
    logger.info("=" * 60)
    logger.info("Testing Corrected Roulette MQTT Integration")
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
        
        # Wait between calls
        await asyncio.sleep(3)
        
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
        
        # Test 4: Test synchronous wrapper
        logger.info("\n4. Testing synchronous wrapper function...")
        success3, result3 = call_roulette_detect_async(
            round_id="ARO-001-TEST-002",
            input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
        )
        
        if success3:
            logger.info(f"✅ Synchronous detect call successful: {result3}")
        else:
            logger.warning(f"⚠️ Synchronous detect call failed or result is null: {result3}")
        
        # Test 5: Cleanup
        logger.info("\n5. Testing cleanup...")
        await cleanup_roulette_mqtt_system()
        logger.info("✅ Cleanup completed successfully")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Corrected Integration Test Summary")
        logger.info("=" * 60)
        logger.info(f"MQTT System Initialization: {'PASSED ✅' if init_success else 'FAILED ❌'}")
        logger.info(f"First Detect Call: {'PASSED ✅' if success1 else 'FAILED ❌'}")
        logger.info(f"Second Detect Call: {'PASSED ✅' if success2 else 'FAILED ❌'}")
        logger.info(f"Synchronous Wrapper: {'PASSED ✅' if success3 else 'FAILED ❌'}")
        
        overall_success = init_success and success1 and success2 and success3
        logger.info(f"\nOverall Integration Test: {'PASSED ✅' if overall_success else 'FAILED ❌'}")
        
        return overall_success
        
    except Exception as e:
        logger.error(f"❌ Integration test failed with exception: {e}")
        return False


def test_import_structure():
    """Test that imports work correctly without circular dependencies"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Import Structure")
    logger.info("=" * 60)
    
    try:
        # Test importing roulette_mqtt_detect
        logger.info("1. Testing roulette_mqtt_detect import...")
        from roulette_mqtt_detect import (
            initialize_roulette_mqtt_system,
            roulette_detect_result,
            cleanup_roulette_mqtt_system,
            call_roulette_detect_async
        )
        logger.info("✅ roulette_mqtt_detect imported successfully")
        
        # Test that we can import main_speed without circular import
        logger.info("2. Testing main_speed import...")
        import main_speed
        logger.info("✅ main_speed imported successfully")
        
        # Test that we can import serialIO without circular import
        logger.info("3. Testing serialIO import...")
        import serial_comm.serialIO
        logger.info("✅ serialIO imported successfully")
        
        logger.info("\n✅ All imports successful - no circular dependency issues")
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        return False


async def main():
    """Main test function"""
    logger.info("Starting Corrected Roulette MQTT Integration Tests")
    
    # Test import structure first
    import_success = test_import_structure()
    
    if not import_success:
        logger.error("❌ Import structure test failed, stopping tests")
        return False
    
    # Run integration tests
    integration_success = await test_corrected_integration()
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("Final Test Results")
    logger.info("=" * 60)
    logger.info(f"Import Structure Test: {'PASSED ✅' if import_success else 'FAILED ❌'}")
    logger.info(f"Integration Test: {'PASSED ✅' if integration_success else 'FAILED ❌'}")
    
    overall_success = import_success and integration_success
    logger.info(f"\nOverall Test Result: {'PASSED ✅' if overall_success else 'FAILED ❌'}")
    
    if overall_success:
        logger.info("\n🎉 All tests passed! Roulette MQTT integration is working correctly.")
        logger.info("The corrected integration is ready for use in main_speed.py")
        logger.info("\nIntegration Summary:")
        logger.info("- ✅ No circular import issues")
        logger.info("- ✅ MQTT system initializes correctly")
        logger.info("- ✅ Detect calls work as expected")
        logger.info("- ✅ Synchronous wrapper functions correctly")
        logger.info("- ✅ Cleanup works properly")
    else:
        logger.error("\n❌ Some tests failed. Please check the logs for details.")
    
    return overall_success


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(main())
    exit(0 if success else 1)
