import logging
import json
from typing import Optional
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

    async def initialize(self):
        """Initialize IDP controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()
        self.mqtt_client.subscribe("ikg/idp/dice/response")

    async def detect(self, round_id: str) -> Optional[list]:
        """Detect dice result"""
        command = {
            "command": "detect",
            "arg": {
                "round_id": round_id,
                "input_stream": "https://192.168.88.213:8088/live/r1234_dice.flv",
                "output_stream": ""
            }
        }
        self.mqtt_client.publish("ikg/idp/dice/command", json.dumps(command))
        return [1, 2, 3]  # 模擬結果，實際應等待回應

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

    async def cleanup(self):
        """Cleanup shaker controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect() 