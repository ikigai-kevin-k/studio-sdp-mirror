"""
Roulette ARO-001 MQTT Command Test Script

This script tests the specific Roulette ARO-001 MQTT command using the
refactored MQTT modules with the specific broker configuration.

Command being tested:
    mosquitto_pub -h 192.168.88.50 -p 1883 -u "PFC" -P "wago" 
    -t "ikg/idp/ARO-001/command" 
    -m '{"command":"detect","arg":{"round_id":"ARO-001-20250825-073412","input":"rtmp://192.168.88.50:1935/live/r10_sr"}}'

Expected Response:
    {"response": "result", "arg": {"round_id": "ARO-001-20250825-073412", "res": 19, "err": 0}}
"""

import asyncio
import json
import logging
import time
from typing import Optional, Any, Dict
from mqtt.complete_system import CompleteMQTTSystem
from mqtt.config_manager import GameType, Environment, MQTTConfigManager


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RouletteAROTester:
    """Roulette ARO-001 MQTT command tester"""
    
    def __init__(self):
        self.game_type = GameType.ROULETTE
        self.environment = Environment.DEVELOPMENT
        self.system: Optional[CompleteMQTTSystem] = None
        self.received_responses = []
        self.test_round_id = "ARO-001-20250825-073412"
        self.test_input_stream = "rtmp://192.168.88.50:1935/live/r10_sr"
    
    async def initialize(self):
        """Initialize the MQTT system with ARO-001 configuration"""
        logger.info("Initializing Roulette ARO-001 MQTT system...")
        
        # Load configuration from file
        config_manager = MQTTConfigManager("conf")
        
        # Load ARO-001 specific configuration
        try:
            # Try to load from roulette-aro-broker.json file
            config = config_manager.load_config_from_file("roulette-aro", self.environment)
            logger.info("Loaded ARO-001 specific configuration from roulette-aro-broker.json")
        except Exception as e:
            logger.warning(f"Failed to load ARO-001 config: {e}")
            # Fallback to default roulette configuration
            config = config_manager.load_config_from_file(self.game_type, self.environment)
            logger.info("Using default roulette configuration")
        
        # Create complete MQTT system
        self.system = CompleteMQTTSystem(
            game_type=self.game_type,
            environment=self.environment,
            enable_connection_pooling=False,
            enable_message_processing=True
        )
        
        # Override configuration
        self.system.config = config
        self.system.config.game_config.command_topic = "ikg/idp/ARO-001/command"
        self.system.config.game_config.response_topic = "ikg/idp/ARO-001/response"
        self.system.config.game_config.timeout = 30
        
        # Initialize system
        await self.system.initialize()
        
        # Add response callback
        def message_callback(message):
            if message.message_type.value == "response":
                self.received_responses.append(message)
                logger.info(f"Received response: {message.payload}")
                
                # Try to extract result immediately
                result_value = self._extract_result_from_message(message)
                if result_value is not None:
                    logger.info(f"🎯 Roulette result extracted: {result_value}")
        
        def error_callback(message, error):
            logger.error(f"Error: {message.id} - {error}")
        
        self.system.add_message_callback(message_callback)
        self.system.add_error_callback(error_callback)
        
        logger.info("Roulette ARO-001 MQTT system initialized successfully")
    
    def _extract_result_from_message(self, message) -> Optional[int]:
        """
        Extract result value from a single message
        
        Args:
            message: Message object
            
        Returns:
            Result value (res) or None if not found
        """
        try:
            response_data = json.loads(message.payload)
            
            # Check if it's a result response
            if response_data.get("response") == "result":
                arg = response_data.get("arg", {})
                if "res" in arg:
                    result_value = arg["res"]
                    logger.info(f"Extracted result value: {result_value}")
                    return result_value
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
        
        return None
    
    async def test_aro_command(self):
        """
        Test the ARO-001 detect command
        
        Returns:
            Tuple of (success, result_value)
        """
        logger.info("Testing ARO-001 detect command...")
        logger.info(f"Round ID: {self.test_round_id}")
        logger.info(f"Input Stream: {self.test_input_stream}")
        
        # Clear previous responses
        self.received_responses.clear()
        
        # Create command manually to match the exact format
        command = {
            "command": "detect",
            "arg": {
                "round_id": self.test_round_id,
                "input": self.test_input_stream
            }
        }
        
        logger.info(f"Sending command: {json.dumps(command, indent=2)}")
        
        # Send command
        success = await self.system.send_command(command)
        
        if not success:
            logger.error("Failed to send command")
            return False, None
        
        logger.info("Command sent successfully, waiting for response...")
        
        # Wait for response
        timeout = 30
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.received_responses:
                # Extract result from the latest response
                latest_response = self.received_responses[-1]
                result_value = self._extract_result_from_message(latest_response)
                
                if result_value is not None:
                    logger.info(f"✅ Received valid result: {result_value}")
                    return True, result_value
            
            await asyncio.sleep(0.1)
        
        logger.warning("Timeout waiting for response")
        return False, None
    
    def validate_response_format(self, response_data: Dict[str, Any]) -> bool:
        """
        Validate response format
        
        Args:
            response_data: Response data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            if "response" not in response_data:
                logger.error("Missing 'response' field")
                return False
            
            if response_data["response"] != "result":
                logger.error(f"Invalid response type: {response_data['response']}")
                return False
            
            if "arg" not in response_data:
                logger.error("Missing 'arg' field")
                return False
            
            arg = response_data["arg"]
            
            # Check arg fields
            required_fields = ["round_id", "res", "err"]
            for field in required_fields:
                if field not in arg:
                    logger.error(f"Missing '{field}' field in arg")
                    return False
            
            # Validate types
            if not isinstance(arg["round_id"], str):
                logger.error("round_id should be a string")
                return False
            
            if not isinstance(arg["res"], int):
                logger.error("res should be an integer")
                return False
            
            if not isinstance(arg["err"], int):
                logger.error("err should be an integer")
                return False
            
            # Validate roulette result range (0-36)
            if not (0 <= arg["res"] <= 36):
                logger.error(f"Invalid roulette result: {arg['res']} (should be 0-36)")
                return False
            
            logger.info("Response format validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Error validating response format: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.system:
            await self.system.cleanup()
            logger.info("System cleanup completed")


async def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("Roulette ARO-001 MQTT Command Test Script")
    logger.info("=" * 60)
    
    tester = RouletteAROTester()
    
    try:
        # Initialize system
        await tester.initialize()
        
        # Test response format validation
        logger.info("\n1. Testing response format validation...")
        sample_response = {
            "response": "result",
            "arg": {
                "round_id": "ARO-001-20250825-073412",
                "res": 19,
                "err": 0
            }
        }
        response_success = tester.validate_response_format(sample_response)
        
        # Test actual MQTT command
        logger.info("\n2. Testing actual ARO-001 MQTT command...")
        success, result_value = await tester.test_aro_command()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Results Summary")
        logger.info("=" * 60)
        logger.info(f"Response Format Test: {'PASSED ✅' if response_success else 'FAILED ❌'}")
        logger.info(f"ARO-001 Command Test: {'PASSED ✅' if success else 'FAILED ❌'}")
        
        if success and result_value is not None:
            logger.info(f"🎯 Roulette Result Value: {result_value}")
            logger.info(f"🎲 Roulette Number: {result_value}")
            
            # Additional validation
            if 0 <= result_value <= 36:
                logger.info("✅ Result value is within valid range (0-36)")
            else:
                logger.error("❌ Result value is outside valid range")
        else:
            logger.warning("⚠️ No result value received")
        
        # Overall result
        overall_success = response_success and success and result_value is not None
        logger.info(f"\nOverall Test Result: {'PASSED ✅' if overall_success else 'FAILED ❌'}")
        
        return overall_success
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        return False
        
    finally:
        # Cleanup
        await tester.cleanup()


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(main())
    
    if success:
        logger.info("\n🎉 All tests passed! The Roulette ARO-001 MQTT command is working correctly.")
        exit(0)
    else:
        logger.error("\n❌ Some tests failed. Please check the logs for details.")
        exit(1)
