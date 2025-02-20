import logging
from paho.mqtt.client import Client as MQTTClient

class MQTTClientWrapper:
    """A generic MQTT client wrapper for subscribing, publishing, and handling messages"""

    def __init__(self, client_id: str, broker: str, port: int, topic=None, keepalive=60):
        """Initialize MQTT client"""
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.keepalive = keepalive
        self.topic = topic

        self.logger = logging.getLogger("MQTTClient")
        self.client = MQTTClient(client_id=self.client_id)


        # Attach event callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    """In Paho MQTT, on_connect, on_message, and on_disconnect are callback functions 
    that the MQTT client automatically triggers based on specific MQTT events."""

    def on_connect(self, client, userdata, flags, rc):
        """Handle connection to the broker"""
        if rc == 0:
            self.logger.info("Connected successfully to MQTT broker")
            # Subscribe to topics if provided
            if self.topic is not None: 
                client.subscribe(self.topic)
                self.logger.info(f"Subscribed to topic: {self.topic}")

        else:
            self.logger.error(f"Failed to connect to MQTT broker, return code {rc}")


    def on_message(self, client, userdata, msg):
        """Handle incoming messages"""
        payload = msg.payload.decode("utf-8")
        self.logger.info(f"Received message on {msg.topic}: {payload}")

        # Custom message processing
        self.process_message(msg.topic, payload)


    def on_disconnect(self, client, userdata, rc):
        """Handle disconnection from the broker"""
        if rc == 0:
            self.logger.info("Disconnected from MQTT broker gracefully")
        else:
            self.logger.warning(f"Unexpected disconnection (rc: {rc})")

    """MQTT Callback function FIN."""

    def process_message(self, topic, payload):
        """Custom processing logic for received messages (can be overridden)"""
        self.logger.info(f"Processing message from {topic}: {payload}")

    def connect(self):
        """Connect to MQTT broker"""
        self.client.connect(self.broker, self.port, self.keepalive)

    def start_loop(self):
        """Start MQTT network loop in a separate thread"""
        self.client.loop_start()

    def stop_loop(self):
        """Stop MQTT network loop"""
        self.client.loop_stop()

    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.disconnect()

    def subscribe(self, topic):
        """Subscribe to a new topic"""
        self.client.subscribe(topic)
        self.logger.info(f"Subscribed to topic: {topic}")

    def unsubscribe(self, topic):
        """Subscribe to a new topic"""
        self.client.unsubscribe(topic)
        self.logger.info(f"Unsubscribed to topic: {topic}")

    def publish(self, topic = None, message = None, qos=0, retain=False):
        """Publish a message to a given topic"""
        topic = self.topic if topic is None else topic
        if topic is not None:
            self.client.publish(topic, message, qos=qos, retain=retain)
            self.logger.info(f"Published message: {message} to topic: {topic}")
        else:
            self.logger.info(f"Failed to send message. Please subscribe at least one topic first.")
