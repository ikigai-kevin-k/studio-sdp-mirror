import logging
import json
import asyncio
from typing import Optional, Tuple
import time
from proto.mqtt import MQTTLogger
from controller import Controller, GameConfig

class IDPConnector(Controller):
    """Controls IDP (Image Detection Processing) operations"""
    def __init__(self, config: GameConfig):
        super().__init__(config)
        self.mqtt_client = MQTTLogger(
            client_id=f"idp_controller_{config.room_id}",
            broker=config.broker_host,
            port=config.broker_port
        )
        self.response_received = False
        self.last_response = None
        self.dice_result = None

    async def initialize(self):
        """Initialize IDP controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()
        
        # Set message handling callback
        self.mqtt_client.client.on_message = self._on_message
        self.mqtt_client.subscribe("ikg/idp/dice/response")

    def _on_message(self, client, userdata, message):
        """Handle received messages"""
        try:
            payload = message.payload.decode()
            self.logger.info(f"Received message on {message.topic}: {payload}")
            
            # Process message
            self._process_message(message.topic, payload)
            
        except Exception as e:
            self.logger.error(f"Error in _on_message: {e}")

    def _process_message(self, topic, payload):
        """Process received message"""
        try:
            self.logger.info(f"Processing message from {topic}: {payload}")
            
            if topic == "ikg/idp/dice/response":
                response_data = json.loads(payload)
                if "response" in response_data and response_data["response"] == "result":
                    if "arg" in response_data and "res" in response_data["arg"]:
                        dice_result = response_data["arg"]["res"]
                        # Check if valid dice result (three numbers)
                        if isinstance(dice_result, list) and len(dice_result) == 3 and all(isinstance(x, int) for x in dice_result):
                            self.dice_result = dice_result
                            self.response_received = True
                            self.last_response = payload
                            self.logger.info(f"Got valid dice result: {self.dice_result}")
                            return  # Return immediately, don't wait for more results
                        else:
                            self.logger.info(f"Received invalid result: {dice_result}, continuing to wait...")
                    
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def detect(self, round_id: str) -> Tuple[bool, Optional[list]]:
        """Send detect command and wait for response"""
        try:
            # Reset state
            self.response_received = False
            self.last_response = None
            self.dice_result = None
            
            command = {
                "command": "detect",
                "arg": {
                    "round_id": round_id,
                    "input": "rtmp://192.168.88.213:1935/live/r456_dice",
                    "output": "https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv"
                }
            }
            
            # Set timeout limit
            timeout = 4  # for demo
            start_time = asyncio.get_event_loop().time()
            retry_interval = 4  
            attempt = 1
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                # Send detection command
                self.logger.info(f"Sending detect command (attempt {attempt})")
                self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))
                
                # Wait for response mini-loop
                wait_end = min(
                    start_time + timeout,  # Don't exceed total timeout
                    asyncio.get_event_loop().time() + retry_interval  # Wait time before next retry
                )
                
                while asyncio.get_event_loop().time() < wait_end:
                    if self.dice_result is not None:
                        self.logger.info(f"Received dice result on attempt {attempt}: {self.dice_result}")
                        return True, self.dice_result
                    time.sleep(0.5)
                
                attempt += 1
            
            # Timeout handling
            elapsed = asyncio.get_event_loop().time() - start_time
            self.logger.warning(f"No valid response received within {elapsed:.2f}s after {attempt-1} attempts")
            command = {
                "command": "timeout",
                "arg": {}
            }
            self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))
            if self.last_response:
                self.logger.warning(f"Last response was: {self.last_response}")
            return True, [""]  # Return default value on timeout
            
        except Exception as e:
            self.logger.error(f"Error in detect: {e}")
            return False, None

    async def cleanup(self):
        """Cleanup IDP controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()
