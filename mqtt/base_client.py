"""
Unified MQTT Base Client Class

This module provides a unified MQTT client implementation that consolidates
all MQTT-related functionality across different game types (Sicbo, Baccarat, Roulette).

Features:
- Unified connection management with failover support
- Standardized message handling
- Configurable authentication and broker settings
- Async/await support for modern Python applications
- Comprehensive logging and error handling
"""

import paho.mqtt.client as mqtt
import json
import logging
import asyncio
import time
from typing import Optional, Set, List, Dict, Callable, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class ConnectionState(Enum):
    """MQTT connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class BrokerConfig:
    """Broker configuration data class"""
    broker: str
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    priority: int = 1
    keepalive: int = 60


@dataclass
class MessageHandler:
    """Message handler configuration"""
    topic_pattern: str
    handler: Callable[[str, str, Dict[str, Any]], None]
    description: str = ""


class UnifiedMQTTClient:
    """
    Unified MQTT Client for all game types
    
    This class provides a single, consistent interface for MQTT operations
    across different games (Sicbo, Baccarat, Roulette).
    """

    def __init__(
        self,
        client_id: str,
        broker_configs: List[BrokerConfig],
        default_username: str = "PFC",
        default_password: str = "wago",
        protocol_version: int = mqtt.MQTTv31,
        callback_api_version: int = mqtt.CallbackAPIVersion.VERSION1
    ):
        """
        Initialize unified MQTT client
        
        Args:
            client_id: Unique client identifier
            broker_configs: List of broker configurations for failover
            default_username: Default username for authentication
            default_password: Default password for authentication
            protocol_version: MQTT protocol version
            callback_api_version: MQTT callback API version
        """
        self.client_id = client_id
        self.broker_configs = sorted(broker_configs, key=lambda x: x.priority)
        self.default_username = default_username
        self.default_password = default_password
        
        # Initialize MQTT client
        self.client = mqtt.Client(
            client_id=client_id,
            protocol=protocol_version,
            callback_api_version=callback_api_version
        )
        
        # Setup logging
        self.logger = logging.getLogger(f"UnifiedMQTT-{client_id}")
        
        # Connection state management
        self.connection_state = ConnectionState.DISCONNECTED
        self.current_broker_index = 0
        self.connected_broker: Optional[BrokerConfig] = None
        
        # Subscription management
        self.subscribed_topics: Set[str] = set()
        self.message_handlers: List[MessageHandler] = []
        
        # Message storage and processing
        self.last_message: Optional[str] = None
        self.message_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # Callback management
        self._setup_callbacks()
        
        # Connection monitoring
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.reconnect_delay = 5.0

    def _setup_callbacks(self):
        """Setup MQTT client callbacks"""
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_log = self._on_log

    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection callback"""
        if rc == 0:
            self.connection_state = ConnectionState.CONNECTED
            self.connected_broker = self.broker_configs[self.current_broker_index]
            self.connection_attempts = 0
            
            self.logger.info(
                f"Successfully connected to MQTT broker {self.connected_broker.broker}:{self.connected_broker.port}"
            )
            
            # Resubscribe to previously subscribed topics
            for topic in self.subscribed_topics:
                result = self.client.subscribe(topic)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.debug(f"Resubscribed to topic: {topic}")
                else:
                    self.logger.warning(f"Failed to resubscribe to topic: {topic}")
        else:
            self.connection_state = ConnectionState.FAILED
            self.logger.error(
                f"Failed to connect to MQTT broker, return code: {rc}"
            )

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            self.logger.debug(f"Received message on topic {topic}: {payload}")
            
            # Store message
            self.last_message = payload
            message_data = {
                "topic": topic,
                "payload": payload,
                "timestamp": time.time(),
                "qos": msg.qos,
                "retain": msg.retain
            }
            
            # Add to history
            self.message_history.append(message_data)
            if len(self.message_history) > self.max_history_size:
                self.message_history.pop(0)
            
            # Process message with registered handlers
            self._process_message(topic, payload)
            
        except Exception as e:
            self.logger.error(f"Error processing incoming message: {e}")

    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection callback"""
        self.connection_state = ConnectionState.DISCONNECTED
        self.connected_broker = None
        
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker, return code: {rc}")
        else:
            self.logger.info("Disconnected from MQTT broker")

    def _on_log(self, client, userdata, level, buf):
        """Handle MQTT logging callback"""
        if level == mqtt.MQTT_LOG_ERR:
            self.logger.error(f"MQTT Error: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            self.logger.warning(f"MQTT Warning: {buf}")
        elif level == mqtt.MQTT_LOG_INFO:
            self.logger.info(f"MQTT Info: {buf}")
        else:
            self.logger.debug(f"MQTT Debug: {buf}")

    def _process_message(self, topic: str, payload: str):
        """Process incoming message with registered handlers"""
        try:
            # Try to parse as JSON
            try:
                message_data = json.loads(payload)
            except json.JSONDecodeError:
                message_data = {"raw": payload}
            
            # Call registered handlers
            for handler in self.message_handlers:
                if self._topic_matches(topic, handler.topic_pattern):
                    try:
                        handler.handler(topic, payload, message_data)
                    except Exception as e:
                        self.logger.error(
                            f"Error in message handler for topic {handler.topic_pattern}: {e}"
                        )
                        
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (supports wildcards)"""
        if pattern == topic:
            return True
        
        # Simple wildcard matching
        if "#" in pattern:
            prefix = pattern.replace("#", "")
            return topic.startswith(prefix)
        
        if "+" in pattern:
            # More complex single-level wildcard matching
            pattern_parts = pattern.split("/")
            topic_parts = topic.split("/")
            
            if len(pattern_parts) != len(topic_parts):
                return False
            
            for p, t in zip(pattern_parts, topic_parts):
                if p != "+" and p != t:
                    return False
            return True
        
        return False

    def add_message_handler(
        self,
        topic_pattern: str,
        handler: Callable[[str, str, Dict[str, Any]], None],
        description: str = ""
    ):
        """
        Add a message handler for specific topic patterns
        
        Args:
            topic_pattern: Topic pattern to match (supports + and # wildcards)
            handler: Function to call when message is received
            description: Description of the handler for logging
        """
        message_handler = MessageHandler(
            topic_pattern=topic_pattern,
            handler=handler,
            description=description
        )
        self.message_handlers.append(message_handler)
        self.logger.info(f"Added message handler for pattern: {topic_pattern}")

    def remove_message_handler(self, topic_pattern: str):
        """Remove message handler for specific topic pattern"""
        self.message_handlers = [
            h for h in self.message_handlers 
            if h.topic_pattern != topic_pattern
        ]
        self.logger.info(f"Removed message handler for pattern: {topic_pattern}")

    async def connect_with_failover(self) -> bool:
        """
        Connect to MQTT broker with failover support
        
        Returns:
            True if connection successful, False otherwise
        """
        self.connection_state = ConnectionState.CONNECTING
        
        for attempt in range(len(self.broker_configs)):
            broker_index = (self.current_broker_index + attempt) % len(self.broker_configs)
            broker_config = self.broker_configs[broker_index]
            
            try:
                self.current_broker_index = broker_index
                
                # Set authentication
                username = broker_config.username or self.default_username
                password = broker_config.password or self.default_password
                self.client.username_pw_set(username, password)
                
                self.logger.info(
                    f"Attempting connection to broker {broker_index + 1}/{len(self.broker_configs)}: "
                    f"{broker_config.broker}:{broker_config.port}"
                )
                
                # Connect to broker
                self.client.connect(
                    broker_config.broker,
                    broker_config.port,
                    keepalive=broker_config.keepalive
                )
                
                # Start the loop
                self.client.loop_start()
                
                # Wait for connection to be established
                await asyncio.sleep(1)
                
                if self.connection_state == ConnectionState.CONNECTED:
                    self.logger.info(
                        f"Successfully connected to {broker_config.broker}:{broker_config.port}"
                    )
                    return True
                else:
                    self.logger.warning(
                        f"Connection attempt failed for {broker_config.broker}:{broker_config.port}"
                    )
                    self.client.disconnect()
                    
            except Exception as e:
                self.logger.error(
                    f"Connection error for {broker_config.broker}:{broker_config.port}: {e}"
                )
                try:
                    self.client.disconnect()
                except Exception:
                    pass
        
        self.connection_state = ConnectionState.FAILED
        self.logger.error("Failed to connect to any MQTT broker")
        return False

    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.connection_state == ConnectionState.CONNECTED:
            self.logger.info("Disconnecting from MQTT broker")
            self.client.loop_stop()
            self.client.disconnect()
            self.connection_state = ConnectionState.DISCONNECTED

    def subscribe(self, topic: str, qos: int = 0) -> bool:
        """
        Subscribe to MQTT topic
        
        Args:
            topic: Topic to subscribe to
            qos: Quality of Service level
            
        Returns:
            True if subscription successful, False otherwise
        """
        if self.connection_state != ConnectionState.CONNECTED:
            self.logger.warning("Cannot subscribe: not connected to MQTT broker")
            return False
        
        try:
            result = self.client.subscribe(topic, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.subscribed_topics.add(topic)
                self.logger.info(f"Subscribed to topic: {topic}")
                return True
            else:
                self.logger.error(f"Failed to subscribe to topic: {topic}")
                return False
        except Exception as e:
            self.logger.error(f"Error subscribing to topic {topic}: {e}")
            return False

    def unsubscribe(self, topic: str) -> bool:
        """
        Unsubscribe from MQTT topic
        
        Args:
            topic: Topic to unsubscribe from
            
        Returns:
            True if unsubscription successful, False otherwise
        """
        if self.connection_state != ConnectionState.CONNECTED:
            self.logger.warning("Cannot unsubscribe: not connected to MQTT broker")
            return False
        
        try:
            result = self.client.unsubscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.subscribed_topics.discard(topic)
                self.logger.info(f"Unsubscribed from topic: {topic}")
                return True
            else:
                self.logger.error(f"Failed to unsubscribe from topic: {topic}")
                return False
        except Exception as e:
            self.logger.error(f"Error unsubscribing from topic {topic}: {e}")
            return False

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> bool:
        """
        Publish message to MQTT topic
        
        Args:
            topic: Topic to publish to
            payload: Message payload
            qos: Quality of Service level
            retain: Whether to retain the message
            
        Returns:
            True if publish successful, False otherwise
        """
        if self.connection_state != ConnectionState.CONNECTED:
            self.logger.warning("Cannot publish: not connected to MQTT broker")
            return False
        
        try:
            result = self.client.publish(topic, payload, qos, retain)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"Published message to topic {topic}: {payload}")
                return True
            else:
                self.logger.error(f"Failed to publish to topic: {topic}")
                return False
        except Exception as e:
            self.logger.error(f"Error publishing to topic {topic}: {e}")
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection information"""
        return {
            "client_id": self.client_id,
            "connection_state": self.connection_state.value,
            "connected_broker": {
                "broker": self.connected_broker.broker,
                "port": self.connected_broker.port
            } if self.connected_broker else None,
            "subscribed_topics": list(self.subscribed_topics),
            "message_handlers_count": len(self.message_handlers),
            "last_message_time": self.message_history[-1]["timestamp"] if self.message_history else None
        }

    def get_message_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent message history"""
        return self.message_history[-limit:] if self.message_history else []

    def clear_message_history(self):
        """Clear message history"""
        self.message_history.clear()
        self.logger.info("Message history cleared")

    async def wait_for_message(
        self,
        topic_pattern: str,
        timeout: float = 10.0,
        expected_count: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Wait for specific messages with timeout
        
        Args:
            topic_pattern: Topic pattern to wait for
            timeout: Maximum time to wait in seconds
            expected_count: Number of messages to wait for
            
        Returns:
            List of received messages
        """
        received_messages = []
        start_time = time.time()
        
        while len(received_messages) < expected_count and (time.time() - start_time) < timeout:
            # Check if any new messages match the pattern
            for message in self.message_history:
                if self._topic_matches(message["topic"], topic_pattern):
                    if message not in received_messages:
                        received_messages.append(message)
            
            await asyncio.sleep(0.1)
        
        return received_messages

    def __del__(self):
        """Cleanup on object destruction"""
        try:
            if self.connection_state == ConnectionState.CONNECTED:
                self.client.loop_stop()
                self.client.disconnect()
        except Exception:
            pass
