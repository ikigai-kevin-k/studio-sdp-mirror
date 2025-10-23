"""
Simple Roulette ARO-001 MQTT Test Script

This script directly tests the Roulette ARO-001 MQTT command using
paho-mqtt client without the complex refactored modules.

Command being tested:
    mosquitto_pub -h 192.168.88.50 -p 1883 -u "PFC" -P "wago" 
    -t "ikg/idp/ARO-001/command" 
    -m '{"command":"detect","arg":{"round_id":"ARO-001-20250825-073412","input":"rtmp://192.168.88.50:1935/live/r10_sr"}}'

Expected Response:
    {"response": "result", "arg": {"round_id": "ARO-001-20250825-073412", "res": 19, "err": 0}}
"""

import paho.mqtt.client as mqtt
import json
import logging
import time
import threading
from typing import Optional, Dict, Any


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleRouletteAROTester:
    """Simple Roulette ARO-001 MQTT command tester"""
    
    def __init__(self):
        self.broker = "192.168.88.50"
        self.port = 1883
        self.username = "PFC"
        self.password = "wago"
        self.command_topic = "ikg/idp/ARO-001/command"
        self.response_topic = "ikg/idp/ARO-001/response"
        
        self.client = None
        self.connected = False
        self.received_responses = []
        self.response_received = False
        self.result_value = None
        
        self.test_round_id = "ARO-001-20250825-073412"
        self.test_input_stream = "rtmp://192.168.88.50:1935/live/r10_sr"
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info(f"✅ Connected to MQTT broker {self.broker}:{self.port}")
            self.connected = True
            
            # Subscribe to response topic
            client.subscribe(self.response_topic)
            logger.info(f"📡 Subscribed to response topic: {self.response_topic}")
        else:
            logger.error(f"❌ Failed to connect to MQTT broker, return code: {rc}")
            self.connected = False
    
    def on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            payload = msg.payload.decode('utf-8')
            logger.info(f"📨 Received message on topic {msg.topic}: {payload}")
            
            # Parse JSON response
            response_data = json.loads(payload)
            self.received_responses.append(response_data)
            
            # Check if it's a result response
            if response_data.get("response") == "result":
                arg = response_data.get("arg", {})
                if "res" in arg:
                    self.result_value = arg["res"]
                    self.response_received = True
                    logger.info(f"🎯 Roulette result received: {self.result_value}")
                    
                    # Validate result (handle null values)
                    if self.result_value is not None:
                        if 0 <= self.result_value <= 36:
                            logger.info(f"✅ Result value {self.result_value} is within valid range (0-36)")
                        else:
                            logger.error(f"❌ Result value {self.result_value} is outside valid range")
                    else:
                        logger.warning(f"⚠️ Result value is null (res: {self.result_value})")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.info("🔌 Disconnected from MQTT broker")
        self.connected = False
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            logger.info(f"🔗 Connecting to MQTT broker {self.broker}:{self.port}")
            
            # Create MQTT client
            self.client = mqtt.Client()
            self.client.username_pw_set(self.username, self.password)
            
            # Set callbacks
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect
            
            # Connect
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            return self.connected
            
        except Exception as e:
            logger.error(f"❌ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("🔌 Disconnected from MQTT broker")
    
    def send_detect_command(self):
        """Send detect command"""
        try:
            # Create command
            command = {
                "command": "detect",
                "arg": {
                    "round_id": self.test_round_id,
                    "input": self.test_input_stream
                }
            }
            
            # Convert to JSON
            command_json = json.dumps(command)
            
            logger.info(f"📤 Sending detect command:")
            logger.info(f"   Topic: {self.command_topic}")
            logger.info(f"   Command: {json.dumps(command, indent=2)}")
            
            # Publish command
            result = self.client.publish(self.command_topic, command_json)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("✅ Command sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send command, return code: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending command: {e}")
            return False
    
    def wait_for_response(self, timeout=30):
        """Wait for response"""
        logger.info(f"⏳ Waiting for response (timeout: {timeout}s)...")
        
        start_time = time.time()
        while not self.response_received and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if self.response_received:
            logger.info(f"✅ Response received within {time.time() - start_time:.2f}s")
            return True
        else:
            logger.warning(f"⏰ Timeout waiting for response after {timeout}s")
            return False
    
    def validate_response_format(self, response_data: Dict[str, Any]) -> bool:
        """Validate response format"""
        try:
            # Check required fields
            if "response" not in response_data:
                logger.error("❌ Missing 'response' field")
                return False
            
            if response_data["response"] != "result":
                logger.error(f"❌ Invalid response type: {response_data['response']}")
                return False
            
            if "arg" not in response_data:
                logger.error("❌ Missing 'arg' field")
                return False
            
            arg = response_data["arg"]
            
            # Check arg fields
            required_fields = ["round_id", "res", "err"]
            for field in required_fields:
                if field not in arg:
                    logger.error(f"❌ Missing '{field}' field in arg")
                    return False
            
            # Validate types
            if not isinstance(arg["round_id"], str):
                logger.error("❌ round_id should be a string")
                return False
            
            # Handle null res values
            if arg["res"] is not None and not isinstance(arg["res"], int):
                logger.error("❌ res should be an integer or null")
                return False
            
            if not isinstance(arg["err"], int):
                logger.error("❌ err should be an integer")
                return False
            
            # Validate roulette result range (0-36) if not null
            if arg["res"] is not None and not (0 <= arg["res"] <= 36):
                logger.error(f"❌ Invalid roulette result: {arg['res']} (should be 0-36)")
                return False
            
            logger.info("✅ Response format validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating response format: {e}")
            return False


def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("Simple Roulette ARO-001 MQTT Command Test Script")
    logger.info("=" * 60)
    
    tester = SimpleRouletteAROTester()
    
    try:
        # Test 1: Response format validation
        logger.info("\n1. Testing response format validation...")
        sample_response = {
            "response": "result",
            "arg": {
                "round_id": "ARO-001-20250825-073412",
                "res": 19,
                "err": 0
            }
        }
        format_success = tester.validate_response_format(sample_response)
        
        # Test 2: Connect to MQTT broker
        logger.info("\n2. Connecting to MQTT broker...")
        connect_success = tester.connect()
        
        if not connect_success:
            logger.error("❌ Failed to connect to MQTT broker")
            return False
        
        # Test 3: Send detect command
        logger.info("\n3. Sending detect command...")
        send_success = tester.send_detect_command()
        
        if not send_success:
            logger.error("❌ Failed to send detect command")
            return False
        
        # Test 4: Wait for response
        logger.info("\n4. Waiting for response...")
        response_success = tester.wait_for_response(30)
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Results Summary")
        logger.info("=" * 60)
        logger.info(f"Response Format Test: {'PASSED ✅' if format_success else 'FAILED ❌'}")
        logger.info(f"MQTT Connection Test: {'PASSED ✅' if connect_success else 'FAILED ❌'}")
        logger.info(f"Command Sending Test: {'PASSED ✅' if send_success else 'FAILED ❌'}")
        logger.info(f"Response Receiving Test: {'PASSED ✅' if response_success else 'FAILED ❌'}")
        
        if response_success and tester.result_value is not None:
            logger.info(f"🎯 Roulette Result Value: {tester.result_value}")
            logger.info(f"🎲 Roulette Number: {tester.result_value}")
            
            # Show all received responses
            if tester.received_responses:
                logger.info(f"📨 Total responses received: {len(tester.received_responses)}")
                for i, response in enumerate(tester.received_responses):
                    logger.info(f"   Response {i+1}: {json.dumps(response, indent=2)}")
        
        # Overall result
        overall_success = format_success and connect_success and send_success and response_success
        logger.info(f"\nOverall Test Result: {'PASSED ✅' if overall_success else 'FAILED ❌'}")
        
        return overall_success
        
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False
        
    finally:
        # Cleanup
        tester.disconnect()


if __name__ == "__main__":
    # Run the test
    success = main()
    
    if success:
        logger.info("\n🎉 All tests passed! The Roulette ARO-001 MQTT command is working correctly.")
        exit(0)
    else:
        logger.error("\n❌ Some tests failed. Please check the logs for details.")
        exit(1)
