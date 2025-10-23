"""
Test script to verify MQTT command format for Roulette

This script tests the exact MQTT command format that will be sent to IDP.
"""

import asyncio
import json
import logging
from mqtt.complete_system import CompleteMQTTSystem
from mqtt.config_manager import GameType, Environment, BrokerConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mqtt_command_format():
    """Test the exact MQTT command format"""
    logger.info("=" * 60)
    logger.info("Testing MQTT Command Format for Roulette")
    logger.info("=" * 60)
    
    system = None
    
    try:
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
        system.config.client_id = "roulette_command_test_client"
        system.config.default_username = "PFC"
        system.config.default_password = "wago"
        
        # Initialize system
        await system.initialize()
        logger.info("✅ MQTT system initialized successfully")
        
        # Test 1: Check command format without explicit input_stream
        logger.info("\n1. Testing command format with default input_stream...")
        command1 = system._create_detect_command("ARO-001-TEST-001")
        logger.info(f"Command 1: {json.dumps(command1, indent=2)}")
        
        # Test 2: Check command format with explicit input_stream
        logger.info("\n2. Testing command format with explicit input_stream...")
        command2 = system._create_detect_command(
            "ARO-001-TEST-002", 
            input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
        )
        logger.info(f"Command 2: {json.dumps(command2, indent=2)}")
        
        # Test 3: Compare with expected format
        logger.info("\n3. Comparing with expected format...")
        expected_command = {
            "command": "detect",
            "arg": {
                "round_id": "ARO-001-TEST-003",
                "input": "rtmp://192.168.88.50:1935/live/r10_sr"
            }
        }
        logger.info(f"Expected: {json.dumps(expected_command, indent=2)}")
        
        # Test 4: Verify command format matches
        command3 = system._create_detect_command(
            "ARO-001-TEST-003", 
            input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
        )
        
        if command3 == expected_command:
            logger.info("✅ Command format matches expected format!")
        else:
            logger.error("❌ Command format does not match expected format!")
            logger.error(f"Actual: {json.dumps(command3, indent=2)}")
            logger.error(f"Expected: {json.dumps(expected_command, indent=2)}")
        
        # Test 5: Send actual command (optional)
        logger.info("\n4. Testing actual command sending...")
        try:
            success, result = await system.detect(
                "ARO-001-TEST-004",
                input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
            )
            if success:
                logger.info(f"✅ Command sent successfully, result: {result}")
            else:
                logger.warning(f"⚠️ Command sent but no result received: {result}")
        except Exception as e:
            logger.error(f"❌ Error sending command: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False
        
    finally:
        # Cleanup
        if system:
            try:
                logger.info("\n5. Cleaning up MQTT system...")
                await system.cleanup()
                logger.info("✅ Cleanup completed successfully")
            except Exception as e:
                logger.error(f"❌ Error during cleanup: {e}")


async def main():
    """Main test function"""
    logger.info("Starting MQTT Command Format Test")
    
    # Run test
    success = await test_mqtt_command_format()
    
    if success:
        logger.info("\n🎉 Command format test completed!")
    else:
        logger.error("\n❌ Command format test failed!")
    
    return success


if __name__ == "__main__":
    # Run test
    success = asyncio.run(main())
    exit(0 if success else 1)
