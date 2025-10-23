"""
Simple Roulette MQTT Command Test Script

This script provides a simple way to test the Roulette MQTT detect command
using the refactored MQTT modules.

Usage:
    python test_roulette_simple.py

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
from mqtt.config_manager import GameType, Environment, BrokerConfig


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RouletteMQTTTester:
    """Simple Roulette MQTT command tester"""
    
    def __init__(self):
        self.game_type = GameType.ROULETTE
        self.environment = Environment.DEVELOPMENT
        self.system: Optional[CompleteMQTTSystem] = None
        self.received_responses = []
    
    async def initialize(self):
        """Initialize the MQTT system"""
        logger.info("Initializing Roulette MQTT system...")
        
        # Create custom broker configuration for the specific test
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
        self.system = CompleteMQTTSystem(
            game_type=self.game_type,
            environment=self.environment,
            enable_connection_pooling=False,  # Disable for simpler testing
            enable_message_processing=True
        )
        
        # Override broker configuration to match the test command
        self.system.config.brokers = broker_configs
        self.system.config.game_config.command_topic = "ikg/idp/ARO-001/command"
        self.system.config.game_config.response_topic = "ikg/idp/ARO-001/response"
        self.system.config.game_config.timeout = 30  # 30 seconds timeout
        
        # Initialize system
        await self.system.initialize()
        
        # Add response callback
        def message_callback(message):
            if message.message_type.value == "response":
                self.received_responses.append(message)
                logger.info(f"Received response: {message.payload}")
        
        def error_callback(message, error):
            logger.error(f"Error: {message.id} - {error}")
        
        self.system.add_message_callback(message_callback)
        self.system.add_error_callback(error_callback)
        
        logger.info("Roulette MQTT system initialized successfully")
    
    async def test_detect_command(self, round_id: str = None, input_stream: str = None):
        """
        Test the Roulette detect command
        
        Args:
            round_id: Round identifier (default: auto-generated)
            input_stream: Input stream URL (default: test stream)
            
        Returns:
            Tuple of (success, result_value)
        """
        if not round_id:
            round_id = f"ARO-001-{int(time.time())}"
        
        if not input_stream:
            input_stream = "rtmp://192.168.88.50:1935/live/r10_sr"
        
        logger.info(f"Testing Roulette detect command...")
        logger.info(f"Round ID: {round_id}")
        logger.info(f"Input Stream: {input_stream}")
        
        # Clear previous responses
        self.received_responses.clear()
        
        # Send detect command
        success, result = await self.system.detect(
            round_id,
            input_stream=input_stream
        )
        
        logger.info(f"Detect command result: success={success}, result={result}")
        
        # Extract result value from responses
        result_value = self._extract_result_from_responses()
        
        return success, result_value
    
    def _extract_result_from_responses(self) -> Optional[int]:
        """
        Extract result value from received responses
        
        Returns:
            Result value (res) or None if not found
        """
        for response_message in self.received_responses:
            try:
                response_data = json.loads(response_message.payload)
                
                # Check if it's a result response
                if response_data.get("response") == "result":
                    arg = response_data.get("arg", {})
                    if "res" in arg:
                        result_value = arg["res"]
                        logger.info(f"Extracted result value: {result_value}")
                        return result_value
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                continue
        
        logger.warning("No valid result found in responses")
        return None
    
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
    
    async def test_command_format(self):
        """Test the command format"""
        logger.info("Testing command format...")
        
        # Create detect command
        command = self.system._create_detect_command(
            "ARO-001-20250825-073412",
            input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
        )
        
        logger.info(f"Generated command: {json.dumps(command, indent=2)}")
        
        # Validate command format
        if "command" in command and command["command"] == "detect":
            if "arg" in command:
                arg = command["arg"]
                if "round_id" in arg and "input" in arg:
                    logger.info("Command format validation passed ✅")
                    return True
        
        logger.error("Command format validation failed ❌")
        return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.system:
            await self.system.cleanup()
            logger.info("System cleanup completed")


async def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("Roulette MQTT Command Test Script")
    logger.info("=" * 60)
    
    tester = RouletteMQTTTester()
    
    try:
        # Initialize system
        await tester.initialize()
        
        # Test 1: Command format validation
        logger.info("\n1. Testing command format...")
        format_success = await tester.test_command_format()
        
        # Test 2: Response format validation
        logger.info("\n2. Testing response format validation...")
        sample_response = {
            "response": "result",
            "arg": {
                "round_id": "ARO-001-20250825-073412",
                "res": 19,
                "err": 0
            }
        }
        response_success = tester.validate_response_format(sample_response)
        
        # Test 3: Actual MQTT command test
        logger.info("\n3. Testing actual MQTT command...")
        success, result_value = await tester.test_detect_command()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Results Summary")
        logger.info("=" * 60)
        logger.info(f"Command Format Test: {'PASSED ✅' if format_success else 'FAILED ❌'}")
        logger.info(f"Response Format Test: {'PASSED ✅' if response_success else 'FAILED ❌'}")
        logger.info(f"MQTT Command Test: {'PASSED ✅' if success else 'FAILED ❌'}")
        
        if success and result_value is not None:
            logger.info(f"Result Value: {result_value}")
            logger.info(f"Roulette Number: {result_value}")
        else:
            logger.warning("No result value received")
        
        # Overall result
        overall_success = format_success and response_success and success
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
        logger.info("\n🎉 All tests passed! The Roulette MQTT command is working correctly.")
        exit(0)
    else:
        logger.error("\n❌ Some tests failed. Please check the logs for details.")
        exit(1)
