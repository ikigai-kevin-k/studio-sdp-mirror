import paho.mqtt.client as mqtt
import logging
import json
from typing import Optional, Set


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
            # mqtt.CallbackAPIVersion.VERSION2,
            # client_id=client_id
        )
        self.logger = logging.getLogger(f"MQTT-{client_id}")

        # 設置認證資訊
        self.client.username_pw_set("PFC", "wago")

        # 設置回調
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        self.subscribed_topics: Set[str] = set()
        self.last_message: Optional[str] = None
        self.connected: bool = False

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker {self.broker}")
            self.connected = True
            # 重新訂閱之前的主題
            for topic in self.subscribed_topics:
                self.client.subscribe(topic)
        else:
            self.logger.error(f"Failed to connect to MQTT broker, return code: {rc}")

    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        self.logger.debug(f"Received message on topic {msg.topic}: {msg.payload}")
        self.last_message = msg.payload.decode()

    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.logger.info("Disconnected from MQTT broker")
        self.connected = False

    def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            # self.client.connect(self.broker, self.port) # original
            self.logger.info(
                f"Attempting to connect to MQTT broker at {self.broker}:{self.port}"
            )
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
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
