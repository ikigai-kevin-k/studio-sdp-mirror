import logging
import json
import asyncio
from typing import Optional, Tuple, List
from dataclasses import dataclass

from mqtt_wrapper import MQTTLogger
from controller import Controller, GameConfig

class IDPController(Controller):
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
        
        # 設置訊息處理回調
        self.mqtt_client.client.on_message = self._on_message
        self.mqtt_client.subscribe("ikg/idp/dice/response")

    def _on_message(self, client, userdata, message):
        """Handle received messages"""
        try:
            payload = message.payload.decode()
            self.logger.info(f"Received message on {message.topic}: {payload}")
            
            # 處理訊息
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
                        dice_result_str = response_data["arg"]["res"]
                        self.dice_result = json.loads(dice_result_str)
                        self.response_received = True
                        self.last_response = payload
                        self.logger.info(f"Updated dice_result: {self.dice_result}")
                    
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message JSON: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    async def detect(self, round_id: str) -> Tuple[bool, Optional[list]]:
        """Send detect command and wait for response"""
        try:
            # 重置狀態
            self.response_received = False
            self.last_response = None
            self.dice_result = None
            
            command = {
                "command": "detect",
                "arg": {
                    "round_id": round_id,
                    "input": "https://192.168.88.213:8088/live/r1234_dice.flv",
                    "output": ""
                }
            }
            
            self.logger.info(f"Sending detect command for round {round_id}")
            self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))
            self.logger.info("Command sent successfully")
            
            # 等待回應
            timeout = 7
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                if self.dice_result is not None:
                    self.logger.info(f"Received dice result: {self.dice_result}")
                    return True, self.dice_result
                await asyncio.sleep(0.1)
            
            self.logger.warning("No valid response received within timeout")
            if self.last_response:
                self.logger.warning(f"Last response was: {self.last_response}")
            return True, [-1, -1, -1]  # 超時時返回預設值
            
        except Exception as e:
            self.logger.error(f"Error in detect: {e}")
            return False, None

    async def cleanup(self):
        """Cleanup IDP controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()

class ShakerController(Controller):
    """Controls dice shaker operations"""
    def __init__(self, config: GameConfig):
        super().__init__(config)
        self.mqtt_client = MQTTLogger(
            client_id=f"shaker_controller_{config.room_id}",
            broker=config.broker_host,
            port=config.broker_port
        )

    async def initialize(self):
        """Initialize shaker controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()
        self.mqtt_client.subscribe("ikg/shaker/response")

    async def shake(self, round_id: str):
        """Shake the dice"""
        command = {
            "command": "shake",
            "arg": {
                "round_id": round_id
            }
        }
        self.mqtt_client.publish("ikg/shaker/command", json.dumps(command))
        self.logger.info(f"Shake command sent for round {round_id}")

    async def cleanup(self):
        """Cleanup shaker controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect() 