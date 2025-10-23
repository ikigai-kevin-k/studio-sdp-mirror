"""
Integrated MQTT System with Message Processing

This module integrates the UnifiedMQTTClient, MQTTConfigManager, and
UnifiedMessageProcessor to provide a complete MQTT solution.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from mqtt.base_client import UnifiedMQTTClient
from mqtt.config_manager import MQTTConfigManager, GameType, Environment, get_config
from mqtt.message_processor import (
    UnifiedMessageProcessor, Message, MessageType, MessagePriority,
    JSONMessageValidator, GameMessageValidator, MessageLogger,
    GameResultProcessor, ProcessingResult
)


class IntegratedMQTTSystem:
    """
    Integrated MQTT System
    
    This class combines the unified MQTT client, configuration manager,
    and message processor into a complete MQTT solution.
    """

    def __init__(
        self,
        game_type: GameType,
        environment: Environment = Environment.DEVELOPMENT,
        config_dir: str = "conf"
    ):
        """
        Initialize integrated MQTT system
        
        Args:
            game_type: Game type (SICBO, BACCARAT, ROULETTE)
            environment: Environment (DEVELOPMENT, STAGING, PRODUCTION)
            config_dir: Configuration directory
        """
        self.game_type = game_type
        self.environment = environment
        
        # Initialize components
        self.config_manager = MQTTConfigManager(config_dir)
        self.config = get_config(game_type, environment, config_dir)
        
        self.mqtt_client = UnifiedMQTTClient(
            client_id=self.config.client_id,
            broker_configs=self.config.brokers,
            default_username=self.config.default_username,
            default_password=self.config.default_password
        )
        
        self.message_processor = UnifiedMessageProcessor()
        
        # Setup logging
        self.logger = logging.getLogger(f"IntegratedMQTT-{game_type.value}")
        
        # State management
        self.is_initialized = False
        self.is_processing = False
        self.processing_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.message_callbacks: List[Callable[[Message], None]] = []
        self.error_callbacks: List[Callable[[Message, str], None]] = []
        
        # Setup message processing pipeline
        self._setup_message_processing()

    def _setup_message_processing(self):
        """Setup message processing pipeline"""
        # Add validators
        self.message_processor.add_validator(JSONMessageValidator())
        self.message_processor.add_validator(GameMessageValidator(self.game_type.value))
        
        # Add processors
        self.message_processor.add_processor(MessageLogger(self.logger))
        self.message_processor.add_processor(GameResultProcessor(self.game_type.value))
        
        # Add callbacks
        def message_callback(message: Message):
            self.logger.debug(f"Message processed: {message.id}")
            for callback in self.message_callbacks:
                try:
                    callback(message)
                except Exception as e:
                    self.logger.error(f"Error in message callback: {e}")
        
        def error_callback(message: Message, error: str):
            self.logger.error(f"Message processing error: {error}")
            for callback in self.error_callbacks:
                try:
                    callback(message, error)
                except Exception as e:
                    self.logger.error(f"Error in error callback: {e}")
        
        self.message_processor.add_message_callback(message_callback)
        self.message_processor.add_error_callback(error_callback)

    async def initialize(self):
        """Initialize the integrated MQTT system"""
        try:
            self.logger.info(f"Initializing {self.game_type.value} MQTT system")
            
            # Connect MQTT client
            if not await self.mqtt_client.connect_with_failover():
                raise Exception("Failed to connect to MQTT broker")
            
            # Subscribe to topics
            self.mqtt_client.subscribe(self.config.game_config.response_topic)
            
            if self.config.game_config.shaker_topic:
                self.mqtt_client.subscribe(self.config.game_config.shaker_topic)
            
            if self.config.game_config.status_topic:
                self.mqtt_client.subscribe(self.config.game_config.status_topic)
            
            # Setup MQTT message handler
            self.mqtt_client.add_message_handler(
                self._handle_mqtt_message,
                f"{self.game_type.value} MQTT message handler"
            )
            
            # Start message processing
            self.processing_task = asyncio.create_task(self.message_processor.process_messages())
            self.is_processing = True
            
            self.is_initialized = True
            self.logger.info(f"{self.game_type.value} MQTT system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MQTT system: {e}")
            raise

    def _handle_mqtt_message(self, topic: str, payload: str, data: Dict[str, Any]):
        """Handle incoming MQTT messages"""
        try:
            # Determine message type based on topic
            message_type = self._determine_message_type(topic)
            
            # Determine priority based on message content
            priority = self._determine_message_priority(data)
            
            # Create message
            message = self.message_processor.create_message(
                topic=topic,
                payload=payload,
                message_type=message_type,
                priority=priority,
                metadata={
                    "game_type": self.game_type.value,
                    "environment": self.environment.value,
                    "config_client_id": self.config.client_id
                }
            )
            
            # Enqueue for processing
            self.message_processor.enqueue_message(message)
            
        except Exception as e:
            self.logger.error(f"Error handling MQTT message: {e}")

    def _determine_message_type(self, topic: str) -> MessageType:
        """Determine message type from topic"""
        if "command" in topic:
            return MessageType.COMMAND
        elif "response" in topic:
            return MessageType.RESPONSE
        elif "status" in topic:
            return MessageType.STATUS
        elif "error" in topic:
            return MessageType.ERROR
        elif "heartbeat" in topic:
            return MessageType.HEARTBEAT
        else:
            return MessageType.NOTIFICATION

    def _determine_message_priority(self, data: Dict[str, Any]) -> MessagePriority:
        """Determine message priority from content"""
        if "error" in data or "failed" in str(data).lower():
            return MessagePriority.CRITICAL
        elif "result" in data:
            return MessagePriority.HIGH
        elif "status" in data:
            return MessagePriority.NORMAL
        else:
            return MessagePriority.LOW

    async def send_command(
        self,
        command: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Send command via MQTT
        
        Args:
            command: Command to send
            priority: Message priority
            correlation_id: Correlation ID for tracking
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            message = self.message_processor.create_message(
                topic=self.config.game_config.command_topic,
                payload=json.dumps(command),
                message_type=MessageType.COMMAND,
                priority=priority,
                correlation_id=correlation_id,
                metadata={
                    "game_type": self.game_type.value,
                    "command_type": command.get("command", "unknown")
                }
            )
            
            # Publish via MQTT
            success = self.mqtt_client.publish(
                self.config.game_config.command_topic,
                json.dumps(command)
            )
            
            if success:
                # Also enqueue for processing (for logging, etc.)
                self.message_processor.enqueue_message(message)
                self.logger.info(f"Sent command: {command.get('command', 'unknown')}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending command: {e}")
            return False

    async def detect(
        self,
        round_id: str,
        **kwargs
    ) -> tuple[bool, Optional[Any]]:
        """
        Send detect command and wait for result
        
        Args:
            round_id: Round identifier
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (success, result)
        """
        try:
            # Create detect command
            command = self._create_detect_command(round_id, **kwargs)
            
            # Send command
            correlation_id = f"detect_{round_id}_{int(time.time())}"
            success = await self.send_command(command, correlation_id=correlation_id)
            
            if not success:
                return False, None
            
            # Wait for response
            timeout = self.config.game_config.timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # Check for completed messages with matching correlation ID
                history = self.message_processor.get_message_history(50)
                
                for message in history:
                    if (message.correlation_id == correlation_id and 
                        message.message_type == MessageType.RESPONSE and
                        message.processing_status.value == "completed"):
                        
                        # Extract result from message
                        try:
                            data = json.loads(message.payload)
                            if "response" in data and data["response"] == "result":
                                if "arg" in data and "res" in data["arg"]:
                                    result = data["arg"]["res"]
                                    self.logger.info(f"Received {self.game_type.value} result: {result}")
                                    return True, result
                        except Exception as e:
                            self.logger.error(f"Error parsing result: {e}")
                
                await asyncio.sleep(0.1)
            
            self.logger.warning(f"Timeout waiting for detect result: {round_id}")
            return True, self._get_default_result()
            
        except Exception as e:
            self.logger.error(f"Error in detect: {e}")
            return False, None

    def _create_detect_command(self, round_id: str, **kwargs) -> Dict[str, Any]:
        """Create detect command based on game type"""
        if self.game_type == GameType.SICBO:
            return {
                "command": "detect",
                "arg": {
                    "round_id": round_id,
                    "input_stream": kwargs.get("input_stream", "rtmp://192.168.88.54:1935/live/r14_asb0011"),
                    "output_stream": kwargs.get("output_stream", "https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv")
                }
            }
        elif self.game_type == GameType.BACCARAT:
            return {
                "command": "detect",
                "arg": {
                    "round_id": round_id,
                    "input": kwargs.get("input", "rtmp://192.168.20.10:1935/live/r111_baccarat")
                }
            }
        elif self.game_type == GameType.ROULETTE:
            return {
                "command": "detect",
                "arg": {
                    "round_id": round_id,
                    "input_stream": kwargs.get("input_stream", "rtmp://192.168.20.10:1935/live/r111_roulette")
                }
            }
        else:
            return {
                "command": "detect",
                "arg": {
                    "round_id": round_id
                }
            }

    def _get_default_result(self) -> List[str]:
        """Get default result based on game type"""
        if self.game_type == GameType.SICBO:
            return [0, 0, 0]
        elif self.game_type == GameType.BACCARAT:
            return [""] * 6
        elif self.game_type == GameType.ROULETTE:
            return [""]
        else:
            return []

    def add_message_callback(self, callback: Callable[[Message], None]):
        """Add message callback"""
        self.message_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[Message, str], None]):
        """Add error callback"""
        self.error_callbacks.append(callback)

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            "game_type": self.game_type.value,
            "environment": self.environment.value,
            "is_initialized": self.is_initialized,
            "is_processing": self.is_processing,
            "mqtt_connection": self.mqtt_client.get_connection_info(),
            "processing_stats": self.message_processor.get_processing_stats(),
            "config_info": {
                "client_id": self.config.client_id,
                "game_code": self.config.game_config.game_code,
                "command_topic": self.config.game_config.command_topic,
                "response_topic": self.config.game_config.response_topic
            }
        }

    async def cleanup(self):
        """Cleanup system resources"""
        try:
            self.logger.info("Cleaning up MQTT system")
            
            # Stop message processing
            if self.is_processing:
                self.message_processor.stop_processing()
                if self.processing_task:
                    self.processing_task.cancel()
                self.is_processing = False
            
            # Disconnect MQTT client
            await self.mqtt_client.disconnect()
            
            self.is_initialized = False
            self.logger.info("MQTT system cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# Convenience functions for easy access
async def create_sicbo_system(environment: Environment = Environment.DEVELOPMENT) -> IntegratedMQTTSystem:
    """Create Sicbo MQTT system"""
    system = IntegratedMQTTSystem(GameType.SICBO, environment)
    await system.initialize()
    return system


async def create_baccarat_system(environment: Environment = Environment.DEVELOPMENT) -> IntegratedMQTTSystem:
    """Create Baccarat MQTT system"""
    system = IntegratedMQTTSystem(GameType.BACCARAT, environment)
    await system.initialize()
    return system


async def create_roulette_system(environment: Environment = Environment.DEVELOPMENT) -> IntegratedMQTTSystem:
    """Create Roulette MQTT system"""
    system = IntegratedMQTTSystem(GameType.ROULETTE, environment)
    await system.initialize()
    return system
