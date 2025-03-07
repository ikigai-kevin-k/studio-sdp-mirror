import logging
from proto.mqtt import MQTTLogger
from controller import Controller, GameConfig
import json

class ShakerConnector(Controller):
    """Controls dice shaker operations"""
    def __init__(self, config: GameConfig):
        super().__init__(config)
        # Use different MQTT settings for shaker
        self.mqtt_client = MQTTLogger(
            client_id=f"shaker_controller_{config.room_id}",
            broker="192.168.88.250",  # Specific broker for shaker
            port=config.broker_port
        )
        self.mqtt_client.client.username_pw_set("PFC", "wago")  # Specific credentials for shaker

    async def initialize(self):
        """Initialize shaker controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()
        self.mqtt_client.subscribe("ikg/shaker/response")

    async def shake(self, round_id: str):
        """Shake the dice using Billy-II settings"""
        # Use the same command format as in quick_shaker_test.py
        cmd = "/cycle/?pattern=0&parameter1=10&parameter2=0&amplitude=0.41&duration=6"
        topic = "ikg/sicbo/Billy-II/listens"
        
        self.mqtt_client.publish(topic, cmd)
        self.mqtt_client.publish(topic, "/state")
        self.logger.info(f"Shake command sent for round {round_id}")

    async def shake_rpi(self, round_id: str):
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
