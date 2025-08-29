import paho.mqtt.client as mqtt
import logging
import threading
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
        self.auto_reconnect: bool = True
        self.reconnect_delay: int = 5  # seconds
        self.max_reconnect_attempts: int = 10
        self.reconnect_attempts: int = 0
        self.reconnect_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.logger.info(f"Connected to MQTT broker {self.broker}")
            self.connected = True
            # Reset reconnect attempts on successful connection
            self.reconnect_attempts = 0

            # 重新訂閱之前的主題
            for topic in self.subscribed_topics:
                self.client.subscribe(topic)
                self.logger.info(f"Resubscribed to: {topic}")
        else:
            self.logger.error(
                f"Failed to connect to MQTT broker, return code: {rc}"
            )
            self.connected = False

    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        self.logger.debug(
            f"Received message on topic {msg.topic}: {msg.payload}"
        )
        self.last_message = msg.payload.decode()

    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.logger.info(f"Disconnected from MQTT broker (RC: {rc})")
        self.connected = False

        # Handle different disconnect reasons
        if rc == 0:
            self.logger.info("Clean disconnect - no reconnection needed")
            return

        # Attempt to reconnect if auto_reconnect is enabled
        if (
            self.auto_reconnect
            and self.reconnect_attempts < self.max_reconnect_attempts
        ):
            self.logger.info(
                f"Attempting to reconnect in {self.reconnect_delay} seconds..."
            )
            self._schedule_reconnect()
        else:
            self.logger.error(
                "Max reconnection attempts reached or auto_reconnect disabled"
            )

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt"""
        if self.reconnect_timer:
            self.reconnect_timer.cancel()

        self.reconnect_timer = threading.Timer(
            self.reconnect_delay, self._attempt_reconnect
        )
        self.reconnect_timer.daemon = True
        self.reconnect_timer.start()

    def _attempt_reconnect(self):
        """Attempt to reconnect to MQTT broker"""
        with self._lock:
            if self.connected:
                return

            self.reconnect_attempts += 1
            self.logger.info(
                f"Reconnection attempt {self.reconnect_attempts}/"
                f"{self.max_reconnect_attempts}"
            )

            try:
                if self.connect():
                    self.logger.info("Reconnection successful")
                else:
                    self.logger.warning("Reconnection failed")
                    if self.reconnect_attempts < self.max_reconnect_attempts:
                        # Exponential backoff for reconnection attempts
                        delay = min(
                            self.reconnect_delay
                            * (2 ** (self.reconnect_attempts - 1)),
                            60,
                        )
                        self.logger.info(
                            f"Scheduling next reconnection attempt in "
                            f"{delay} seconds..."
                        )
                        self.reconnect_timer = threading.Timer(
                            delay, self._attempt_reconnect
                        )
                        self.reconnect_timer.daemon = True
                        self.reconnect_timer.start()
            except Exception as e:
                self.logger.error(f"Error during reconnection attempt: {e}")

    def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            # self.client.connect(self.broker, self.port) # original
            self.logger.info(
                f"Attempting to connect to MQTT broker at "
                f"{self.broker}:{self.port}"
            )

            # Set connection parameters for better stability
            self.client.connect(
                self.broker, self.port, keepalive=60, bind_address=""
            )

            # Start the loop after successful connection
            self.client.loop_start()

            return True
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker"""
        try:
            # Disable auto-reconnect during manual disconnect
            self.auto_reconnect = False
            if self.reconnect_timer:
                self.reconnect_timer.cancel()
                self.reconnect_timer = None

            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            self.logger.info("Disconnected from MQTT broker")
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")

    def start_loop(self):
        """Start MQTT loop"""
        self.client.loop_start()

    def stop_loop(self):
        """Stop MQTT loop"""
        self.client.loop_stop()

    def subscribe(self, topic: str):
        """Subscribe to a topic"""
        self.subscribed_topics.add(topic)
        if self.connected:
            self.client.subscribe(topic)
            self.logger.info(f"Subscribed to: {topic}")
        else:
            self.logger.warning(
                f"Not connected, topic {topic} will be subscribed "
                f"after reconnection"
            )

    def publish(self, topic: str, message: str):
        """Publish message to a topic"""
        if self.connected:
            try:
                result = self.client.publish(topic, message)
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    self.logger.error(
                        f"Failed to publish message: {result.rc}"
                    )
            except Exception as e:
                self.logger.error(f"Error publishing message: {e}")
        else:
            self.logger.warning(
                "Cannot publish message - not connected to MQTT broker"
            )

    def is_connected(self) -> bool:
        """Check if connected to MQTT broker"""
        return self.connected

    def get_connection_info(self) -> dict:
        """Get current connection information"""
        return {
            "connected": self.connected,
            "broker": self.broker,
            "port": self.port,
            "client_id": self.client_id,
            "reconnect_attempts": self.reconnect_attempts,
            "subscribed_topics": list(self.subscribed_topics),
        }
