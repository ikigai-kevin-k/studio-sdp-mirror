"""
Simple test for Roulette MQTT integration

This script tests the Roulette MQTT detect functionality
without the complexity of main_speed.py integration.
"""

import asyncio
import logging
import time
from mqtt.complete_system import CompleteMQTTSystem
from mqtt.config_manager import GameType, Environment, BrokerConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_roulette_mqtt_direct():
    """Test Roulette MQTT functionality directly"""
    logger.info("=" * 60)
    logger.info("Testing Roulette MQTT Integration")
    logger.info("=" * 60)
    
    system = None
    
    try:
        # Test 1: Initialize MQTT system
        logger.info("\n1. Initializing Roulette MQTT system...")
        
        # Create broker configuration for ARO-001
        broker_configs = [
            BrokerConfig(
                broker="192.168.88.50",
                port=1883,
                username="PFC",
                password="wago",
                priority=1
            )
        ]
        
        # Create complete MQTT system
        system = CompleteMQTTSystem(
            game_type=GameType.ROULETTE,
            environment=Environment.DEVELOPMENT,
            enable_connection_pooling=False,
            enable_message_processing=True
        )
        
        # Override configuration
        system.config.brokers = broker_configs
        system.config.game_config.command_topic = "ikg/idp/ARO-001/command"
        system.config.game_config.response_topic = "ikg/idp/ARO-001/response"
        system.config.game_config.timeout = 30
        system.config.client_id = "roulette_test_client"
        system.config.default_username = "PFC"
        system.config.default_password = "wago"
        
        # Initialize system
        await system.initialize()
        logger.info("✅ MQTT system initialized successfully")
        
        # Test 2: First detect call (simulating *u 1 command)
        logger.info("\n2. Testing first detect call (after *u 1 command)...")
        success1, result1 = await system.detect(
            "ARO-001-TEST-001",
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
        success2, result2 = await system.detect(
            "ARO-001-TEST-001",
            input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
        )
        
        if success2:
            logger.info(f"✅ Second detect call successful: {result2}")
        else:
            logger.warning(f"⚠️ Second detect call failed or result is null: {result2}")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Summary")
        logger.info("=" * 60)
        logger.info(f"MQTT System Initialization: PASSED ✅")
        logger.info(f"First Detect Call: {'PASSED ✅' if success1 else 'FAILED ❌'}")
        logger.info(f"Second Detect Call: {'PASSED ✅' if success2 else 'FAILED ❌'}")
        
        overall_success = success1 and success2
        logger.info(f"\nOverall Test Result: {'PASSED ✅' if overall_success else 'FAILED ❌'}")
        
        return overall_success
        
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False
        
    finally:
        # Cleanup
        if system:
            try:
                logger.info("\n4. Cleaning up MQTT system...")
                await system.cleanup()
                logger.info("✅ Cleanup completed successfully")
            except Exception as e:
                logger.error(f"❌ Error during cleanup: {e}")


async def main():
    """Main test function"""
    logger.info("Starting Roulette MQTT Integration Test")
    
    # Run test
    success = await test_roulette_mqtt_direct()
    
    if success:
        logger.info("\n🎉 Test passed! Roulette MQTT integration is working correctly.")
        logger.info("The integration is ready for use in main_speed.py")
    else:
        logger.error("\n❌ Test failed. Please check the logs for details.")
    
    return success


if __name__ == "__main__":
    # Run test
    success = asyncio.run(main())
    exit(0 if success else 1)
