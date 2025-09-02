import paho.mqtt.client as mqtt
import json
import logging
import asyncio
import os
from typing import Optional, Tuple, List, Dict


def load_broker_config(config_file: str) -> Optional[Dict]:
    """Load broker configuration from JSON file"""
    try:
        if not os.path.exists(config_file):
            return None
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logging.error(
            "Failed to load broker config from %s: %s", config_file, e
        )
        return None


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
            self.logger.info("Connected to MQTT broker %s", self.broker)
            self.connected = True
            # Resubscribe to previous topics
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

    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker, self.port)
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
        
        for i, broker_config in enumerate(self.broker_list):
            try:
                self.current_broker_index = i
                self.broker = broker_config["broker"]
                self.port = broker_config.get("port", 1883)
                
                self.logger.info(
                    "[FAILOVER] Trying broker %d/%d: %s:%d",
                    i+1, len(self.broker_list), self.broker, self.port
                )
                
                self.client.connect(self.broker, self.port)
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
        return self.connect_with_failover()


class MQTTConnector:
    """Controller class for MQTT operations"""

    def __init__(self, client_id: str, broker: str, port: int = 1883,
                 broker_list: Optional[List[Dict]] = None):
        self.mqtt_logger = MQTTLogger(client_id, broker, port, broker_list)
        self.logger = logging.getLogger("MQTTConnector")
        self.response_received = False
        self.last_response = None

    async def initialize(self):
        """Initialize MQTT controller"""
        if not self.mqtt_logger.connect_with_failover():
            raise Exception("Failed to connect to any MQTT broker")

        self.mqtt_logger.start_loop()
        self.mqtt_logger.subscribe("ikg/idp/dice/response")
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
        self.mqtt_logger.publish("ikg/idp/dice/command", json.dumps(command))

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
