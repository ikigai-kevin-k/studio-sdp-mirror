"""
Unified Game Controllers using MQTT Configuration Manager

This module demonstrates how to create unified game controllers using
the MQTT configuration manager and base client.
"""

import asyncio
import json
import logging
from typing import Optional, Tuple, Dict, Any
from mqtt.config_manager import MQTTConfigManager, GameType, Environment, get_config
from mqtt.base_client import UnifiedMQTTClient


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedGameController:
    """
    Unified game controller base class
    
    This class provides a common interface for all game controllers
    using the unified MQTT configuration and client system.
    """

    def __init__(self, game_type: GameType, environment: Environment = Environment.DEVELOPMENT):
        """
        Initialize unified game controller
        
        Args:
            game_type: Game type (SICBO, BACCARAT, ROULETTE)
            environment: Environment (DEVELOPMENT, STAGING, PRODUCTION)
        """
        self.game_type = game_type
        self.environment = environment
        
        # Load configuration
        self.config = get_config(game_type, environment)
        
        # Create MQTT client
        self.mqtt_client = UnifiedMQTTClient(
            client_id=self.config.client_id,
            broker_configs=self.config.brokers,
            default_username=self.config.default_username,
            default_password=self.config.default_password
        )
        
        # Game-specific state
        self.response_received = False
        self.last_response = None
        self.game_result = None
        
        # Setup logging
        self.logger = logging.getLogger(f"UnifiedGameController-{game_type.value}")
        
        # Register message handlers
        self._register_message_handlers()

    def _register_message_handlers(self):
        """Register message handlers for the game type"""
        self.mqtt_client.add_message_handler(
            self.config.game_config.response_topic,
            self._handle_response_message,
            f"{self.game_type.value} response handler"
        )

    def _handle_response_message(self, topic: str, payload: str, data: Dict[str, Any]):
        """Handle response messages"""
        try:
            self.logger.info(f"Received response on {topic}: {data}")
            
            if "response" in data and data["response"] == "result":
                if "arg" in data and "res" in data["arg"]:
                    result = data["arg"]["res"]
                    if self._validate_result(result):
                        self.game_result = result
                        self.response_received = True
                        self.last_response = payload
                        self.logger.info(f"Valid {self.game_type.value} result: {result}")
                    else:
                        self.logger.warning(f"Invalid result format: {result}")
                        
        except Exception as e:
            self.logger.error(f"Error handling response message: {e}")

    def _validate_result(self, result: Any) -> bool:
        """Validate game result format - to be overridden by subclasses"""
        return True

    async def initialize(self):
        """Initialize the game controller"""
        try:
            self.logger.info(f"Initializing {self.game_type.value} controller")
            
            # Connect to MQTT broker
            if not await self.mqtt_client.connect_with_failover():
                raise Exception("Failed to connect to MQTT broker")
            
            # Subscribe to response topic
            self.mqtt_client.subscribe(self.config.game_config.response_topic)
            
            # Subscribe to additional topics if configured
            if self.config.game_config.shaker_topic:
                self.mqtt_client.subscribe(self.config.game_config.shaker_topic)
            if self.config.game_config.status_topic:
                self.mqtt_client.subscribe(self.config.game_config.status_topic)
            
            self.logger.info(f"{self.game_type.value} controller initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.game_type.value} controller: {e}")
            raise

    async def detect(self, round_id: str, **kwargs) -> Tuple[bool, Optional[list]]:
        """
        Send detect command and wait for response
        
        Args:
            round_id: Round identifier
            **kwargs: Additional game-specific parameters
            
        Returns:
            Tuple of (success, result)
        """
        try:
            # Reset state
            self.response_received = False
            self.last_response = None
            self.game_result = None
            
            # Create command
            command = self._create_detect_command(round_id, **kwargs)
            
            # Send command
            self.logger.info(f"Sending detect command for round {round_id}")
            self.mqtt_client.publish(
                self.config.game_config.command_topic,
                json.dumps(command)
            )
            
            # Wait for response
            messages = await self.mqtt_client.wait_for_message(
                self.config.game_config.response_topic,
                timeout=self.config.game_config.timeout
            )
            
            if self.game_result is not None:
                self.logger.info(f"Received {self.game_type.value} result: {self.game_result}")
                return True, self.game_result
            else:
                self.logger.warning(f"No valid result received for round {round_id}")
                return True, self._get_default_result()
                
        except Exception as e:
            self.logger.error(f"Error in detect: {e}")
            return False, None

    def _create_detect_command(self, round_id: str, **kwargs) -> Dict[str, Any]:
        """Create detect command - to be overridden by subclasses"""
        return {
            "command": "detect",
            "arg": {
                "round_id": round_id
            }
        }

    def _get_default_result(self) -> list:
        """Get default result - to be overridden by subclasses"""
        return []

    async def cleanup(self):
        """Cleanup controller resources"""
        try:
            await self.mqtt_client.disconnect()
            self.logger.info(f"{self.game_type.value} controller cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


class UnifiedSicboController(UnifiedGameController):
    """Unified Sicbo game controller"""

    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        super().__init__(GameType.SICBO, environment)

    def _validate_result(self, result: Any) -> bool:
        """Validate Sicbo dice result (3 numbers)"""
        return (
            isinstance(result, list) and 
            len(result) == 3 and 
            all(isinstance(x, int) for x in result)
        )

    def _create_detect_command(self, round_id: str, **kwargs) -> Dict[str, Any]:
        """Create Sicbo detect command"""
        return {
            "command": "detect",
            "arg": {
                "round_id": round_id,
                "input_stream": kwargs.get("input_stream", "rtmp://192.168.88.54:1935/live/r14_asb0011"),
                "output_stream": kwargs.get("output_stream", "https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv")
            }
        }

    def _get_default_result(self) -> list:
        """Get default Sicbo result"""
        return [0, 0, 0]

    async def shake_dice(self, round_id: str) -> bool:
        """Shake dice using shaker"""
        try:
            if not self.config.game_config.shaker_topic:
                self.logger.warning("Shaker topic not configured")
                return False
            
            # Send shake command
            shake_command = "/cycle/?pattern=0&parameter1=10&parameter2=0&amplitude=0.41&duration=9.59"
            self.mqtt_client.publish(self.config.game_config.shaker_topic, shake_command)
            self.logger.info(f"Sent shake command for round {round_id}")
            
            # Wait for shake completion (simplified)
            await asyncio.sleep(10)  # Wait for shake duration
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error shaking dice: {e}")
            return False


class UnifiedBaccaratController(UnifiedGameController):
    """Unified Baccarat game controller"""

    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        super().__init__(GameType.BACCARAT, environment)

    def _validate_result(self, result: Any) -> bool:
        """Validate Baccarat result (6 cards)"""
        return (
            isinstance(result, list) and 
            len(result) == 6
        )

    def _create_detect_command(self, round_id: str, **kwargs) -> Dict[str, Any]:
        """Create Baccarat detect command"""
        return {
            "command": "detect",
            "arg": {
                "round_id": round_id,
                "input": kwargs.get("input", "rtmp://192.168.20.10:1935/live/r111_baccarat")
            }
        }

    def _get_default_result(self) -> list:
        """Get default Baccarat result"""
        return [""] * 6


class UnifiedRouletteController(UnifiedGameController):
    """Unified Roulette game controller"""

    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        super().__init__(GameType.ROULETTE, environment)

    def _validate_result(self, result: Any) -> bool:
        """Validate Roulette result"""
        return isinstance(result, (str, int, list))

    def _create_detect_command(self, round_id: str, **kwargs) -> Dict[str, Any]:
        """Create Roulette detect command"""
        return {
            "command": "detect",
            "arg": {
                "round_id": round_id,
                "input_stream": kwargs.get("input_stream", "rtmp://192.168.20.10:1935/live/r111_roulette")
            }
        }

    def _get_default_result(self) -> list:
        """Get default Roulette result"""
        return [""]


# Demo functions
async def demo_sicbo_controller():
    """Demonstrate Sicbo controller"""
    logger.info("=== Unified Sicbo Controller Demo ===")
    
    controller = UnifiedSicboController(Environment.DEVELOPMENT)
    
    try:
        await controller.initialize()
        
        # Test detection
        success, result = await controller.detect(
            "demo_round_001",
            input_stream="rtmp://192.168.88.54:1935/live/r14_asb0011",
            output_stream="https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv"
        )
        
        if success:
            logger.info(f"Sicbo detection result: {result}")
        
        # Test shaker
        shake_success = await controller.shake_dice("demo_round_001")
        logger.info(f"Shake operation: {'Success' if shake_success else 'Failed'}")
        
    except Exception as e:
        logger.error(f"Error in Sicbo demo: {e}")
    finally:
        await controller.cleanup()


async def demo_baccarat_controller():
    """Demonstrate Baccarat controller"""
    logger.info("=== Unified Baccarat Controller Demo ===")
    
    controller = UnifiedBaccaratController(Environment.DEVELOPMENT)
    
    try:
        await controller.initialize()
        
        # Test detection
        success, result = await controller.detect(
            "demo_round_002",
            input="rtmp://192.168.20.10:1935/live/r111_baccarat"
        )
        
        if success:
            logger.info(f"Baccarat detection result: {result}")
        
    except Exception as e:
        logger.error(f"Error in Baccarat demo: {e}")
    finally:
        await controller.cleanup()


async def demo_roulette_controller():
    """Demonstrate Roulette controller"""
    logger.info("=== Unified Roulette Controller Demo ===")
    
    controller = UnifiedRouletteController(Environment.DEVELOPMENT)
    
    try:
        await controller.initialize()
        
        # Test detection
        success, result = await controller.detect(
            "demo_round_003",
            input_stream="rtmp://192.168.20.10:1935/live/r111_roulette"
        )
        
        if success:
            logger.info(f"Roulette detection result: {result}")
        
    except Exception as e:
        logger.error(f"Error in Roulette demo: {e}")
    finally:
        await controller.cleanup()


async def main():
    """Main demo function"""
    logger.info("Starting Unified Game Controllers Demo")
    
    # Run demos
    await demo_sicbo_controller()
    await asyncio.sleep(1)
    
    await demo_baccarat_controller()
    await asyncio.sleep(1)
    
    await demo_roulette_controller()
    
    logger.info("Unified Game Controllers Demo completed")


if __name__ == "__main__":
    asyncio.run(main())
