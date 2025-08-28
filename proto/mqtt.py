import paho.mqtt.client as mqtt
import json
import logging
import asyncio
from typing import Optional, Tuple


class MQTTLogger:
    """MQTT Logger class for handling MQTT connections and messaging"""

    def __init__(self, client_id: str, broker: str, port: int = 1883):
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(
            client_id=client_id,
            protocol=mqtt.MQTTv31,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
        )
        self.logger = logging.getLogger("MQTTLogger")

        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        self.subscribed_topics = set()
        self.last_message = None
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker {self.broker}")
            self.connected = True
            # Resubscribe to previous topics
            for topic in self.subscribed_topics:
                self.client.subscribe(topic)
        else:
            self.logger.error(
                f"Failed to connect to MQTT broker, return code: {rc}"
            )

    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        self.logger.debug(
            f"Received message on topic {msg.topic}: {msg.payload}"
        )
        self.last_message = msg.payload.decode()

    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.logger.info("Disconnected from MQTT broker")
        self.connected = False

    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker, self.port)
            return True
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.disconnect()

    def start_loop(self):
        """Start MQTT loop"""
        self.client.loop_start()

    def stop_loop(self):
        """Stop MQTT loop"""
        self.client.loop_stop()

    def subscribe(self, topic: str):
        """Subscribe to a topic"""
        self.subscribed_topics.add(topic)
        self.client.subscribe(topic)

    def publish(self, topic: str, message: str):
        """Publish message to a topic"""
        self.client.publish(topic, message)


class MQTTConnector:
    """Controller class for MQTT operations"""

    def __init__(self, client_id: str, broker: str, port: int = 1883):
        self.mqtt_logger = MQTTLogger(client_id, broker, port)
        self.logger = logging.getLogger("MQTTConnector")
        self.response_received = False
        self.last_response = None

    async def initialize(self):
        """Initialize MQTT controller"""
        if not self.mqtt_logger.connect():
            raise Exception("Failed to connect to MQTT broker")

        self.mqtt_logger.start_loop()
        self.mqtt_logger.subscribe("ikg/idp/SBO-001/response")
        self.mqtt_logger.subscribe("ikg/shaker/response")

    async def send_detect_command(
        self, round_id: str, input_stream: str, output_stream: str
    ) -> Tuple[bool, Optional[list]]:
        """Send detect command and wait for response"""
        command = {
            "command": "detect",
            "arg": {
                "round_id": round_id,
                "input_stream": input_stream,
                "output_stream": output_stream,
            },
        }

        self.response_received = False
        self.mqtt_logger.publish(
            "ikg/idp/SBO-001/command", json.dumps(command)
        )

        # Wait for response
        timeout = 10  # 10 seconds timeout
        start_time = asyncio.get_event_loop().time()

        while not self.response_received:
            if asyncio.get_event_loop().time() - start_time > timeout:
                self.logger.error("Timeout waiting for detect response")
                return False, None
            await asyncio.sleep(0.1)

            if self.mqtt_logger.last_message:
                try:
                    response = json.loads(self.mqtt_logger.last_message)
                    dice_results = response.get("data", {}).get("results", [])
                    if dice_results:
                        return True, dice_results
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse detect response")
                    return False, None

        return False, None

    async def cleanup(self):
        """Cleanup MQTT controller resources"""
        self.mqtt_logger.stop_loop()
        self.mqtt_logger.disconnect()
