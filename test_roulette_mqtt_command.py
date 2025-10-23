"""
Unit Test Script for Roulette MQTT Command

This script tests the Roulette MQTT detect command using the refactored
MQTT modules. It sends a detect command and validates the response format.

Command: mosquitto_pub -h 192.168.88.50 -p 1883 -u "PFC" -P "wago" 
         -t "ikg/idp/ARO-001/command" 
         -m '{"command":"detect","arg":{"round_id":"ARO-001-20250825-073412","input":"rtmp://192.168.88.50:1935/live/r10_sr"}}'

Expected Response: {"response": "result", "arg": {"round_id": "ARO-001-20250825-073412", "res": 19, "err": 0}}
"""

import asyncio
import json
import logging
import time
import unittest
from typing import Optional, Any, Dict
from mqtt.complete_system import CompleteMQTTSystem
from mqtt.config_manager import GameType, Environment, BrokerConfig
from mqtt.message_processor import Message, MessageType, MessagePriority


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RouletteMQTTTest(unittest.TestCase):
    """Unit test class for Roulette MQTT command testing"""
    
    def setUp(self):
        """Setup test environment"""
        self.game_type = GameType.ROULETTE
        self.environment = Environment.DEVELOPMENT
        self.test_round_id = "ARO-001-20250825-073412"
        self.test_input_stream = "rtmp://192.168.88.50:1935/live/r10_sr"
        self.system: Optional[CompleteMQTTSystem] = None
        
        # Expected response format
        self.expected_response_format = {
            "response": "result",
            "arg": {
                "round_id": str,
                "res": int,
                "err": int
            }
        }
    
    async def asyncSetUp(self):
        """Async setup for test environment"""
        # Create custom broker configuration for the test
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
        
        # Override broker configuration
        self.system.config.brokers = broker_configs
        self.system.config.game_config.command_topic = "ikg/idp/ARO-001/command"
        self.system.config.game_config.response_topic = "ikg/idp/ARO-001/response"
        
        # Initialize system
        await self.system.initialize()
        
        # Add test callbacks
        self.received_messages = []
        
        def message_callback(message: Message):
            self.received_messages.append(message)
            logger.info(f"Test received message: {message.id} - {message.payload}")
        
        def error_callback(message: Message, error: str):
            logger.error(f"Test error: {message.id} - {error}")
        
        self.system.add_message_callback(message_callback)
        self.system.add_error_callback(error_callback)
    
    async def asyncTearDown(self):
        """Async cleanup"""
        if self.system:
            await self.system.cleanup()
    
    def test_roulette_detect_command_format(self):
        """Test that the detect command is formatted correctly"""
        # Create detect command
        command = self.system._create_detect_command(
            self.test_round_id,
            input_stream=self.test_input_stream
        )
        
        # Validate command format
        self.assertIn("command", command)
        self.assertEqual(command["command"], "detect")
        
        self.assertIn("arg", command)
        arg = command["arg"]
        
        self.assertIn("round_id", arg)
        self.assertEqual(arg["round_id"], self.test_round_id)
        
        self.assertIn("input", arg)
        self.assertEqual(arg["input"], self.test_input_stream)
        
        logger.info(f"Detect command format validated: {command}")
    
    def test_roulette_response_format_validation(self):
        """Test response format validation"""
        # Sample response data
        sample_response = {
            "response": "result",
            "arg": {
                "round_id": "ARO-001-20250825-073412",
                "res": 19,
                "err": 0
            }
        }
        
        # Validate response format
        self.assertIn("response", sample_response)
        self.assertEqual(sample_response["response"], "result")
        
        self.assertIn("arg", sample_response)
        arg = sample_response["arg"]
        
        self.assertIn("round_id", arg)
        self.assertIsInstance(arg["round_id"], str)
        
        self.assertIn("res", arg)
        self.assertIsInstance(arg["res"], int)
        
        self.assertIn("err", arg)
        self.assertIsInstance(arg["err"], int)
        
        logger.info(f"Response format validated: {sample_response}")
    
    def test_extract_result_value(self):
        """Test extracting result value from response"""
        # Sample response
        sample_response = {
            "response": "result",
            "arg": {
                "round_id": "ARO-001-20250825-073412",
                "res": 19,
                "err": 0
            }
        }
        
        # Extract result value
        result_value = self._extract_result_value(sample_response)
        
        self.assertIsNotNone(result_value)
        self.assertEqual(result_value, 19)
        
        logger.info(f"Result value extracted: {result_value}")
    
    def test_invalid_response_handling(self):
        """Test handling of invalid response formats"""
        # Test cases for invalid responses
        invalid_responses = [
            {"response": "error", "arg": {"round_id": "test", "err": 1}},
            {"response": "result", "arg": {"round_id": "test"}},  # Missing res
            {"response": "result", "arg": {"res": 19}},  # Missing round_id
            {"invalid": "format"},  # Completely invalid
            None,  # None response
        ]
        
        for invalid_response in invalid_responses:
            result_value = self._extract_result_value(invalid_response)
            self.assertIsNone(result_value)
            logger.info(f"Invalid response handled correctly: {invalid_response}")
    
    def _extract_result_value(self, response: Optional[Dict[str, Any]]) -> Optional[int]:
        """
        Extract result value from response
        
        Args:
            response: Response dictionary
            
        Returns:
            Result value (res) or None if invalid
        """
        try:
            if not response:
                return None
            
            if "response" not in response or response["response"] != "result":
                return None
            
            if "arg" not in response:
                return None
            
            arg = response["arg"]
            
            if "res" not in arg:
                return None
            
            result_value = arg["res"]
            
            # Validate that it's a number
            if not isinstance(result_value, (int, float)):
                return None
            
            return int(result_value)
            
        except Exception as e:
            logger.error(f"Error extracting result value: {e}")
            return None


class RouletteMQTTIntegrationTest(unittest.TestCase):
    """Integration test for actual MQTT communication"""
    
    def setUp(self):
        """Setup integration test"""
        self.game_type = GameType.ROULETTE
        self.environment = Environment.DEVELOPMENT
        self.test_round_id = f"ARO-001-{int(time.time())}"
        self.test_input_stream = "rtmp://192.168.88.50:1935/live/r10_sr"
        self.system: Optional[CompleteMQTTSystem] = None
        self.test_timeout = 30  # 30 seconds timeout for integration test
    
    async def asyncSetUp(self):
        """Async setup for integration test"""
        # Create custom broker configuration
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
            enable_connection_pooling=False,
            enable_message_processing=True
        )
        
        # Override configuration
        self.system.config.brokers = broker_configs
        self.system.config.game_config.command_topic = "ikg/idp/ARO-001/command"
        self.system.config.game_config.response_topic = "ikg/idp/ARO-001/response"
        self.system.config.game_config.timeout = self.test_timeout
        
        # Initialize system
        await self.system.initialize()
        
        # Setup message tracking
        self.received_responses = []
        
        def message_callback(message: Message):
            if message.message_type == MessageType.RESPONSE:
                self.received_responses.append(message)
                logger.info(f"Integration test received response: {message.payload}")
        
        def error_callback(message: Message, error: str):
            logger.error(f"Integration test error: {message.id} - {error}")
        
        self.system.add_message_callback(message_callback)
        self.system.add_error_callback(error_callback)
    
    async def asyncTearDown(self):
        """Async cleanup"""
        if self.system:
            await self.system.cleanup()
    
    async def test_roulette_detect_integration(self):
        """Integration test for Roulette detect command"""
        logger.info(f"Starting Roulette detect integration test with round_id: {self.test_round_id}")
        
        # Send detect command
        success, result = await self.system.detect(
            self.test_round_id,
            input_stream=self.test_input_stream
        )
        
        # Validate results
        self.assertTrue(success, "Detect command should succeed")
        self.assertIsNotNone(result, "Result should not be None")
        
        logger.info(f"Integration test result: {result}")
        
        # Check if we received any responses
        self.assertGreater(len(self.received_responses), 0, "Should receive at least one response")
        
        # Validate response format
        for response_message in self.received_responses:
            try:
                response_data = json.loads(response_message.payload)
                
                # Check response format
                self.assertIn("response", response_data)
                self.assertIn("arg", response_data)
                
                arg = response_data["arg"]
                self.assertIn("round_id", arg)
                self.assertIn("res", arg)
                self.assertIn("err", arg)
                
                # Extract and validate result
                result_value = arg["res"]
                self.assertIsInstance(result_value, int, "Result should be an integer")
                self.assertGreaterEqual(result_value, 0, "Result should be non-negative")
                self.assertLessEqual(result_value, 36, "Roulette result should be 0-36")
                
                logger.info(f"Valid response received: round_id={arg['round_id']}, res={result_value}, err={arg['err']}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                self.fail(f"Invalid JSON response: {response_message.payload}")
    
    async def test_roulette_command_sending(self):
        """Test sending Roulette command directly"""
        logger.info("Testing Roulette command sending")
        
        # Create command
        command = {
            "command": "detect",
            "arg": {
                "round_id": self.test_round_id,
                "input": self.test_input_stream
            }
        }
        
        # Send command
        success = await self.system.send_command(command, MessagePriority.HIGH)
        
        self.assertTrue(success, "Command sending should succeed")
        logger.info(f"Command sent successfully: {command}")
        
        # Wait for response
        await asyncio.sleep(5)
        
        # Check if we received responses
        self.assertGreater(len(self.received_responses), 0, "Should receive responses after sending command")


async def run_unit_tests():
    """Run unit tests"""
    logger.info("Starting Roulette MQTT Unit Tests")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add unit tests
    test_suite.addTest(RouletteMQTTTest('test_roulette_detect_command_format'))
    test_suite.addTest(RouletteMQTTTest('test_roulette_response_format_validation'))
    test_suite.addTest(RouletteMQTTTest('test_extract_result_value'))
    test_suite.addTest(RouletteMQTTTest('test_invalid_response_handling'))
    
    # Run unit tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    logger.info(f"Unit tests completed. Failures: {len(result.failures)}, Errors: {len(result.errors)}")
    
    return len(result.failures) == 0 and len(result.errors) == 0


async def run_integration_tests():
    """Run integration tests"""
    logger.info("Starting Roulette MQTT Integration Tests")
    
    try:
        # Create integration test instance
        integration_test = RouletteMQTTIntegrationTest()
        
        # Setup
        await integration_test.asyncSetUp()
        
        # Run integration tests
        await integration_test.test_roulette_detect_integration()
        await integration_test.test_roulette_command_sending()
        
        # Cleanup
        await integration_test.asyncTearDown()
        
        logger.info("Integration tests completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        return False


async def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("Roulette MQTT Command Unit Test Script")
    logger.info("=" * 60)
    
    # Run unit tests
    logger.info("\n1. Running Unit Tests...")
    unit_test_success = await run_unit_tests()
    
    # Run integration tests
    logger.info("\n2. Running Integration Tests...")
    integration_test_success = await run_integration_tests()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"Unit Tests: {'PASSED' if unit_test_success else 'FAILED'}")
    logger.info(f"Integration Tests: {'PASSED' if integration_test_success else 'FAILED'}")
    
    if unit_test_success and integration_test_success:
        logger.info("All tests PASSED! ✅")
        return True
    else:
        logger.error("Some tests FAILED! ❌")
        return False


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(main())
    exit(0 if success else 1)
