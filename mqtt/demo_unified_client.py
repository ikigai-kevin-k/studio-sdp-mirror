"""
Example usage of UnifiedMQTTClient

This module demonstrates how to use the UnifiedMQTTClient for different game types.
"""

import asyncio
import json
import logging
from typing import Dict, Any
from mqtt.base_client import UnifiedMQTTClient, BrokerConfig


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sicbo_message_handler(topic: str, payload: str, data: Dict[str, Any]):
    """Handle Sicbo game messages"""
    logger.info(f"[SICBO] Received message on {topic}: {data}")
    
    if "response" in data and data["response"] == "result":
        if "arg" in data and "res" in data["arg"]:
            dice_result = data["arg"]["res"]
            if isinstance(dice_result, list) and len(dice_result) == 3:
                logger.info(f"[SICBO] Valid dice result: {dice_result}")


def baccarat_message_handler(topic: str, payload: str, data: Dict[str, Any]):
    """Handle Baccarat game messages"""
    logger.info(f"[BACCARAT] Received message on {topic}: {data}")
    
    if "response" in data and data["response"] == "result":
        if "arg" in data and "res" in data["arg"]:
            baccarat_result = data["arg"]["res"]
            if isinstance(baccarat_result, list) and len(baccarat_result) == 6:
                logger.info(f"[BACCARAT] Valid baccarat result: {baccarat_result}")


def roulette_message_handler(topic: str, payload: str, data: Dict[str, Any]):
    """Handle Roulette game messages"""
    logger.info(f"[ROULETTE] Received message on {topic}: {data}")
    
    if "response" in data and data["response"] == "result":
        if "arg" in data and "res" in data["arg"]:
            roulette_result = data["arg"]["res"]
            logger.info(f"[ROULETTE] Valid roulette result: {roulette_result}")


async def demo_sicbo_client():
    """Demonstrate Sicbo MQTT client usage"""
    logger.info("=== Sicbo MQTT Client Demo ===")
    
    # Configure brokers for Sicbo
    broker_configs = [
        BrokerConfig(
            broker="192.168.20.9",
            port=1883,
            username="PFC",
            password="wago",
            priority=1
        ),
        BrokerConfig(
            broker="192.168.20.10",
            port=1883,
            username="PFC",
            password="wago",
            priority=2
        )
    ]
    
    # Create unified MQTT client
    client = UnifiedMQTTClient(
        client_id="sicbo_demo_client",
        broker_configs=broker_configs
    )
    
    # Add message handler
    client.add_message_handler(
        topic_pattern="ikg/idp/SBO-001/response",
        handler=sicbo_message_handler,
        description="Sicbo detection response handler"
    )
    
    try:
        # Connect with failover
        if await client.connect_with_failover():
            logger.info("Successfully connected to MQTT broker")
            
            # Subscribe to Sicbo topics
            client.subscribe("ikg/idp/SBO-001/response")
            client.subscribe("ikg/shaker/response")
            
            # Send a test command
            command = {
                "command": "detect",
                "arg": {
                    "round_id": "test_round_001",
                    "input_stream": "rtmp://192.168.88.54:1935/live/r14_asb0011",
                    "output_stream": "https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv"
                }
            }
            
            client.publish("ikg/idp/SBO-001/command", json.dumps(command))
            logger.info("Sent Sicbo detect command")
            
            # Wait for response
            messages = await client.wait_for_message("ikg/idp/SBO-001/response", timeout=5.0)
            logger.info(f"Received {len(messages)} messages")
            
            # Show connection info
            info = client.get_connection_info()
            logger.info(f"Connection info: {info}")
            
        else:
            logger.error("Failed to connect to any MQTT broker")
            
    except Exception as e:
        logger.error(f"Error in Sicbo demo: {e}")
    finally:
        await client.disconnect()


async def demo_baccarat_client():
    """Demonstrate Baccarat MQTT client usage"""
    logger.info("=== Baccarat MQTT Client Demo ===")
    
    # Configure brokers for Baccarat
    broker_configs = [
        BrokerConfig(
            broker="192.168.20.10",
            port=1883,
            username="PFC",
            password="wago",
            priority=1
        ),
        BrokerConfig(
            broker="192.168.20.9",
            port=1883,
            username="PFC",
            password="wago",
            priority=2
        )
    ]
    
    # Create unified MQTT client
    client = UnifiedMQTTClient(
        client_id="baccarat_demo_client",
        broker_configs=broker_configs
    )
    
    # Add message handler
    client.add_message_handler(
        topic_pattern="ikg/idp/BAC-001/response",
        handler=baccarat_message_handler,
        description="Baccarat detection response handler"
    )
    
    try:
        # Connect with failover
        if await client.connect_with_failover():
            logger.info("Successfully connected to MQTT broker")
            
            # Subscribe to Baccarat topics
            client.subscribe("ikg/idp/BAC-001/response")
            
            # Send a test command
            command = {
                "command": "detect",
                "arg": {
                    "round_id": "test_round_002",
                    "input": "rtmp://192.168.20.10:1935/live/r111_baccarat"
                }
            }
            
            client.publish("ikg/idp/BAC-001/command", json.dumps(command))
            logger.info("Sent Baccarat detect command")
            
            # Wait for response
            messages = await client.wait_for_message("ikg/idp/BAC-001/response", timeout=5.0)
            logger.info(f"Received {len(messages)} messages")
            
        else:
            logger.error("Failed to connect to any MQTT broker")
            
    except Exception as e:
        logger.error(f"Error in Baccarat demo: {e}")
    finally:
        await client.disconnect()


async def demo_roulette_client():
    """Demonstrate Roulette MQTT client usage (future implementation)"""
    logger.info("=== Roulette MQTT Client Demo ===")
    
    # Configure brokers for Roulette (using same as Sicbo for now)
    broker_configs = [
        BrokerConfig(
            broker="192.168.20.9",
            port=1883,
            username="PFC",
            password="wago",
            priority=1
        ),
        BrokerConfig(
            broker="192.168.20.10",
            port=1883,
            username="PFC",
            password="wago",
            priority=2
        )
    ]
    
    # Create unified MQTT client
    client = UnifiedMQTTClient(
        client_id="roulette_demo_client",
        broker_configs=broker_configs
    )
    
    # Add message handler
    client.add_message_handler(
        topic_pattern="ikg/idp/ROU-001/response",
        handler=roulette_message_handler,
        description="Roulette detection response handler"
    )
    
    try:
        # Connect with failover
        if await client.connect_with_failover():
            logger.info("Successfully connected to MQTT broker")
            
            # Subscribe to Roulette topics
            client.subscribe("ikg/idp/ROU-001/response")
            
            # Send a test command
            command = {
                "command": "detect",
                "arg": {
                    "round_id": "test_round_003",
                    "input_stream": "rtmp://192.168.20.10:1935/live/r111_roulette"
                }
            }
            
            client.publish("ikg/idp/ROU-001/command", json.dumps(command))
            logger.info("Sent Roulette detect command")
            
            # Wait for response
            messages = await client.wait_for_message("ikg/idp/ROU-001/response", timeout=5.0)
            logger.info(f"Received {len(messages)} messages")
            
        else:
            logger.error("Failed to connect to any MQTT broker")
            
    except Exception as e:
        logger.error(f"Error in Roulette demo: {e}")
    finally:
        await client.disconnect()


async def main():
    """Main demo function"""
    logger.info("Starting Unified MQTT Client Demo")
    
    # Run demos sequentially
    await demo_sicbo_client()
    await asyncio.sleep(1)
    
    await demo_baccarat_client()
    await asyncio.sleep(1)
    
    await demo_roulette_client()
    
    logger.info("Demo completed")


if __name__ == "__main__":
    asyncio.run(main())
