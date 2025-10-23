"""
Demo for MQTT Configuration Manager

This module demonstrates how to use the MQTTConfigManager for different
game types and environments.
"""

import asyncio
import json
import logging
from typing import Dict, Any
from mqtt.config_manager import (
    MQTTConfigManager, GameType, Environment, 
    get_config, create_config_template
)
from mqtt.base_client import UnifiedMQTTClient


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def demo_config_loading():
    """Demonstrate configuration loading"""
    logger.info("=== Configuration Loading Demo ===")
    
    # Create configuration manager
    config_manager = MQTTConfigManager("conf")
    
    # Load configurations for different game types
    game_types = [GameType.SICBO, GameType.BACCARAT, GameType.ROULETTE]
    
    for game_type in game_types:
        try:
            logger.info(f"\n--- Loading {game_type.value.upper()} Configuration ---")
            
            # Load configuration from file
            config = config_manager.load_config_from_file(game_type, Environment.DEVELOPMENT)
            
            # Display configuration info
            info = config_manager.get_config_info(config)
            logger.info(f"Configuration Info: {json.dumps(info, indent=2)}")
            
            # Show broker details
            logger.info(f"Brokers configured: {len(config.brokers)}")
            for i, broker in enumerate(config.brokers):
                logger.info(f"  Broker {i+1}: {broker.broker}:{broker.port} (priority: {broker.priority})")
            
            # Show game configuration
            game_config = config.game_config
            logger.info(f"Game Code: {game_config.game_code}")
            logger.info(f"Command Topic: {game_config.command_topic}")
            logger.info(f"Response Topic: {game_config.response_topic}")
            if game_config.shaker_topic:
                logger.info(f"Shaker Topic: {game_config.shaker_topic}")
            
        except Exception as e:
            logger.error(f"Error loading {game_type.value} configuration: {e}")


def demo_config_templates():
    """Demonstrate configuration template creation"""
    logger.info("\n=== Configuration Template Demo ===")
    
    config_manager = MQTTConfigManager("conf")
    
    # Create templates for different game types
    game_types = [GameType.SICBO, GameType.BACCARAT, GameType.ROULETTE]
    
    for game_type in game_types:
        try:
            logger.info(f"\n--- Creating {game_type.value.upper()} Template ---")
            
            # Create template
            template = config_manager.create_config_template(
                game_type, 
                Environment.DEVELOPMENT
            )
            
            # Save template to file
            template_file = f"conf/{game_type.value}-template.json"
            config_manager.create_config_template(
                game_type,
                Environment.DEVELOPMENT,
                template_file
            )
            
            logger.info(f"Template created: {template_file}")
            logger.info(f"Template preview:\n{template[:200]}...")
            
        except Exception as e:
            logger.error(f"Error creating {game_type.value} template: {e}")


def demo_default_configs():
    """Demonstrate default configuration usage"""
    logger.info("\n=== Default Configuration Demo ===")
    
    config_manager = MQTTConfigManager("conf")
    
    # Get default configurations
    game_types = [GameType.SICBO, GameType.BACCARAT, GameType.ROULETTE]
    
    for game_type in game_types:
        try:
            logger.info(f"\n--- Default {game_type.value.upper()} Configuration ---")
            
            # Get default configuration
            config = config_manager.get_default_config(game_type)
            
            # Display configuration info
            info = config_manager.get_config_info(config)
            logger.info(f"Default Configuration Info: {json.dumps(info, indent=2)}")
            
        except Exception as e:
            logger.error(f"Error getting default {game_type.value} configuration: {e}")


async def demo_integration_with_client():
    """Demonstrate integration with UnifiedMQTTClient"""
    logger.info("\n=== Integration with UnifiedMQTTClient Demo ===")
    
    try:
        # Load Sicbo configuration
        config = get_config(GameType.SICBO, Environment.DEVELOPMENT, "conf")
        logger.info(f"Loaded configuration: {config.client_id}")
        
        # Create MQTT client using configuration
        client = UnifiedMQTTClient(
            client_id=config.client_id,
            broker_configs=config.brokers,
            default_username=config.default_username,
            default_password=config.default_password
        )
        
        # Add message handler for Sicbo
        def sicbo_handler(topic: str, payload: str, data: Dict[str, Any]):
            logger.info(f"[SICBO] Received message on {topic}: {data}")
        
        client.add_message_handler(
            config.game_config.response_topic,
            sicbo_handler,
            "Sicbo detection response handler"
        )
        
        # Connect and test
        if await client.connect_with_failover():
            logger.info("Successfully connected using configuration")
            
            # Subscribe to response topic
            client.subscribe(config.game_config.response_topic)
            logger.info(f"Subscribed to: {config.game_config.response_topic}")
            
            # Send test command
            command = {
                "command": "detect",
                "arg": {
                    "round_id": "config_demo_001",
                    "input_stream": "rtmp://192.168.88.54:1935/live/r14_asb0011",
                    "output_stream": "https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv"
                }
            }
            
            client.publish(config.game_config.command_topic, json.dumps(command))
            logger.info(f"Sent command to: {config.game_config.command_topic}")
            
            # Wait for response
            messages = await client.wait_for_message(
                config.game_config.response_topic,
                timeout=5.0
            )
            logger.info(f"Received {len(messages)} messages")
            
            # Show connection info
            info = client.get_connection_info()
            logger.info(f"Client connection info: {json.dumps(info, indent=2)}")
            
        else:
            logger.error("Failed to connect using configuration")
            
    except Exception as e:
        logger.error(f"Error in integration demo: {e}")
    finally:
        if 'client' in locals():
            await client.disconnect()


def demo_environment_switching():
    """Demonstrate environment-based configuration switching"""
    logger.info("\n=== Environment Switching Demo ===")
    
    config_manager = MQTTConfigManager("conf")
    
    # Test different environments
    environments = [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]
    
    for env in environments:
        try:
            logger.info(f"\n--- {env.value.upper()} Environment ---")
            
            # Load configuration for each environment
            config = config_manager.load_config_from_file(GameType.SICBO, env)
            
            # Display environment-specific info
            info = config_manager.get_config_info(config)
            logger.info(f"Environment: {info['environment']}")
            logger.info(f"Client ID: {info['client_id']}")
            logger.info(f"Primary Broker: {info['primary_broker']}")
            
        except Exception as e:
            logger.error(f"Error loading {env.value} configuration: {e}")


def demo_config_validation():
    """Demonstrate configuration validation"""
    logger.info("\n=== Configuration Validation Demo ===")
    
    config_manager = MQTTConfigManager("conf")
    
    # Test with invalid configuration
    try:
        # Create invalid configuration
        from mqtt.config_manager import MQTTConfig, BrokerConfig, GameConfig
        
        invalid_config = MQTTConfig(
            client_id="test_client",
            brokers=[],  # Empty brokers list - should fail validation
            game_config=GameConfig(
                game_type=GameType.SICBO,
                game_code="",  # Empty game code - should fail validation
                command_topic="",
                response_topic=""
            )
        )
        
        # This should raise an exception
        config_manager._validate_config(invalid_config)
        logger.error("Validation should have failed!")
        
    except ValueError as e:
        logger.info(f"Configuration validation correctly failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in validation: {e}")


async def main():
    """Main demo function"""
    logger.info("Starting MQTT Configuration Manager Demo")
    
    # Run demos
    demo_config_loading()
    demo_config_templates()
    demo_default_configs()
    demo_environment_switching()
    demo_config_validation()
    
    # Integration demo
    await demo_integration_with_client()
    
    logger.info("Configuration Manager Demo completed")


if __name__ == "__main__":
    asyncio.run(main())
