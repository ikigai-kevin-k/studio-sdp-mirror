import paho.mqtt.client as mqtt
import logging
from typing import Optional, Set, List, Dict


class MQTTLogger:
    """MQTT Logger class for handling MQTT connections and messaging"""

    def __init__(self, client_id: str, broker: str, port: int = 1883,
                 broker_list: Optional[List[Dict]] = None):
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.broker_list = broker_list or [{"broker": broker, "port": port}]
        self.current_broker_index = 0
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
            self.logger.info("Connected to MQTT broker %s", self.broker)
            self.connected = True
            # 重新訂閱之前的主題
            for topic in self.subscribed_topics:
                self.client.subscribe(topic)
        else:
            self.logger.error(
                "Failed to connect to MQTT broker, return code: %d", rc
            )

    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        self.logger.debug(
            "Received message on topic %s: %s", msg.topic, msg.payload
        )
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
                "Attempting to connect to MQTT broker at %s:%d",
                self.broker, self.port
            )
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            self.logger.error("Connection error: %s", e)
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

    def set_broker_list(self, broker_list: List[Dict]):
        """Set the list of brokers for failover"""
        self.broker_list = broker_list
        self.current_broker_index = 0

    def get_current_broker(self) -> Dict:
        """Get current broker configuration"""
        return self.broker_list[self.current_broker_index]

    def connect_with_failover(self) -> bool:
        """Try connecting to brokers in order until one succeeds"""
        last_error = None
        
        # Start from current_broker_index and try all brokers
        for attempt in range(len(self.broker_list)):
            i = (self.current_broker_index + attempt) % len(self.broker_list)
            broker_config = self.broker_list[i]
            
            try:
                self.current_broker_index = i
                self.broker = broker_config["broker"]
                self.port = broker_config.get("port", 1883)
                
                # Update credentials if provided
                username = broker_config.get("username", "PFC")
                password = broker_config.get("password", "wago")
                self.client.username_pw_set(username, password)
                
                self.logger.info(
                    "[FAILOVER] Trying broker %d/%d: %s:%d",
                    i+1, len(self.broker_list), self.broker, self.port
                )
                
                self.client.connect(self.broker, self.port, keepalive=60)
                self.client.loop_start()
                self.connected = True
                
                self.logger.info(
                    "[FAILOVER] Successfully connected to %s:%d",
                    self.broker, self.port
                )
                return True
                
            except Exception as e:
                last_error = e
                self.logger.warning(
                    "[FAILOVER] Failed to connect to %s:%d - %s",
                    self.broker, self.port, e
                )
                try:
                    self.client.disconnect()
                except Exception:
                    pass
                self.connected = False
        
        self.logger.error(
            "[FAILOVER] Could not connect to any broker. Last error: %s",
            last_error
        )
        return False

    def reconnect_with_failover(self):
        """Reconnect using failover mechanism"""
        self.logger.info("[FAILOVER] Attempting reconnection with failover")
        try:
            self.stop_loop()
        except Exception:
            pass
        
        # Move to next broker for failover
        self.current_broker_index = (self.current_broker_index + 1) % len(self.broker_list)
        self.logger.info(
            "[FAILOVER] Moving to next broker index: %d/%d",
            self.current_broker_index + 1, len(self.broker_list)
        )
        
        return self.connect_with_failover()
