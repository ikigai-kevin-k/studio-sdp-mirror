"""
Final Demo for Complete MQTT System

This module demonstrates the complete MQTT system integrating all four
refactoring phases for Sicbo, Baccarat, and Roulette game types.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any
from mqtt.complete_system import (
    CompleteMQTTSystem, create_complete_sicbo_system,
    create_complete_baccarat_system, create_complete_roulette_system
)
from mqtt.config_manager import GameType, Environment
from mqtt.message_processor import Message, MessageType


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_complete_sicbo_system():
    """Demonstrate complete Sicbo system"""
    logger.info("=== Complete Sicbo System Demo ===")
    
    system = None
    try:
        # Create complete system with all features
        system = await create_complete_sicbo_system(
            environment=Environment.DEVELOPMENT,
            enable_connection_pooling=True,
            enable_message_processing=True
        )
        
        # Add custom callbacks
        def message_callback(message: Message):
            logger.info(f"Sicbo message: {message.id} - {message.message_type.value}")
        
        def error_callback(message: Message, error: str):
            logger.error(f"Sicbo error: {message.id} - {error}")
        
        system.add_message_callback(message_callback)
        system.add_error_callback(error_callback)
        
        # Show complete system status
        status = system.get_system_status()
        logger.info(f"Complete Sicbo system status:")
        logger.info(f"  Game Type: {status['game_type']}")
        logger.info(f"  Environment: {status['environment']}")
        logger.info(f"  Initialized: {status['is_initialized']}")
        logger.info(f"  Running: {status['is_running']}")
        
        # Show connection manager stats
        if "connection_manager" in status:
            conn_stats = status["connection_manager"]
            logger.info(f"  Connections: {conn_stats['total_connections']}")
            logger.info(f"  Healthy: {conn_stats['healthy_connections']}")
            logger.info(f"  Messages: {conn_stats['total_messages']}")
        
        # Show message processor stats
        if "message_processor" in status:
            msg_stats = status["message_processor"]
            logger.info(f"  Message Queue: {msg_stats['queue_status']}")
            logger.info(f"  Processing: {msg_stats['is_processing']}")
        
        # Test detection
        success, result = await system.detect(
            "complete_sicbo_001",
            input_stream="rtmp://192.168.88.54:1935/live/r14_asb0011",
            output_stream="https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv"
        )
        
        if success:
            logger.info(f"Sicbo detection result: {result}")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Show final stats
        final_status = system.get_system_status()
        logger.info(f"Final Sicbo stats: {json.dumps(final_status, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in complete Sicbo demo: {e}")
    finally:
        if system:
            await system.cleanup()


async def demo_complete_baccarat_system():
    """Demonstrate complete Baccarat system"""
    logger.info("=== Complete Baccarat System Demo ===")
    
    system = None
    try:
        # Create complete system
        system = await create_complete_baccarat_system(
            environment=Environment.DEVELOPMENT,
            enable_connection_pooling=True,
            enable_message_processing=True
        )
        
        # Add callbacks
        def message_callback(message: Message):
            logger.info(f"Baccarat message: {message.id} - {message.message_type.value}")
        
        def error_callback(message: Message, error: str):
            logger.error(f"Baccarat error: {message.id} - {error}")
        
        system.add_message_callback(message_callback)
        system.add_error_callback(error_callback)
        
        # Show system status
        status = system.get_system_status()
        logger.info(f"Complete Baccarat system status:")
        logger.info(f"  Game Type: {status['game_type']}")
        logger.info(f"  Environment: {status['environment']}")
        
        # Test detection
        success, result = await system.detect(
            "complete_baccarat_001",
            input="rtmp://192.168.20.10:1935/live/r111_baccarat"
        )
        
        if success:
            logger.info(f"Baccarat detection result: {result}")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Show final stats
        final_status = system.get_system_status()
        logger.info(f"Final Baccarat stats: {json.dumps(final_status, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in complete Baccarat demo: {e}")
    finally:
        if system:
            await system.cleanup()


async def demo_complete_roulette_system():
    """Demonstrate complete Roulette system"""
    logger.info("=== Complete Roulette System Demo ===")
    
    system = None
    try:
        # Create complete system
        system = await create_complete_roulette_system(
            environment=Environment.DEVELOPMENT,
            enable_connection_pooling=True,
            enable_message_processing=True
        )
        
        # Add callbacks
        def message_callback(message: Message):
            logger.info(f"Roulette message: {message.id} - {message.message_type.value}")
        
        def error_callback(message: Message, error: str):
            logger.error(f"Roulette error: {message.id} - {error}")
        
        system.add_message_callback(message_callback)
        system.add_error_callback(error_callback)
        
        # Show system status
        status = system.get_system_status()
        logger.info(f"Complete Roulette system status:")
        logger.info(f"  Game Type: {status['game_type']}")
        logger.info(f"  Environment: {status['environment']}")
        
        # Test detection
        success, result = await system.detect(
            "complete_roulette_001",
            input_stream="rtmp://192.168.20.10:1935/live/r111_roulette"
        )
        
        if success:
            logger.info(f"Roulette detection result: {result}")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Show final stats
        final_status = system.get_system_status()
        logger.info(f"Final Roulette stats: {json.dumps(final_status, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in complete Roulette demo: {e}")
    finally:
        if system:
            await system.cleanup()


async def demo_multiple_complete_systems():
    """Demonstrate multiple complete systems running concurrently"""
    logger.info("=== Multiple Complete Systems Demo ===")
    
    systems = []
    try:
        # Create all three systems
        sicbo_system = CompleteMQTTSystem(
            GameType.SICBO,
            Environment.DEVELOPMENT,
            enable_connection_pooling=True,
            enable_message_processing=True
        )
        
        baccarat_system = CompleteMQTTSystem(
            GameType.BACCARAT,
            Environment.DEVELOPMENT,
            enable_connection_pooling=True,
            enable_message_processing=True
        )
        
        roulette_system = CompleteMQTTSystem(
            GameType.ROULETTE,
            Environment.DEVELOPMENT,
            enable_connection_pooling=True,
            enable_message_processing=True
        )
        
        systems = [sicbo_system, baccarat_system, roulette_system]
        
        # Initialize all systems
        for system in systems:
            await system.initialize()
            logger.info(f"Initialized {system.game_type.value} system")
        
        # Run detection on all systems concurrently
        tasks = []
        
        # Sicbo detection
        tasks.append(sicbo_system.detect("multi_sicbo_001"))
        
        # Baccarat detection
        tasks.append(baccarat_system.detect("multi_baccarat_001"))
        
        # Roulette detection
        tasks.append(roulette_system.detect("multi_roulette_001"))
        
        # Wait for all detections to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Detection {i} failed: {result}")
            else:
                success, data = result
                game_type = systems[i].game_type.value
                logger.info(f"{game_type} detection: {'Success' if success else 'Failed'} - {data}")
        
        # Show combined stats
        logger.info("\nCombined system statistics:")
        for system in systems:
            stats = system.get_system_status()
            logger.info(f"{system.game_type.value}:")
            
            if "connection_manager" in stats:
                conn_stats = stats["connection_manager"]
                logger.info(f"  Connections: {conn_stats['total_connections']}")
                logger.info(f"  Messages: {conn_stats['total_messages']}")
            
            if "message_processor" in stats:
                msg_stats = stats["message_processor"]
                logger.info(f"  Messages processed: {msg_stats['total_messages']}")
        
    except Exception as e:
        logger.error(f"Error in multiple systems demo: {e}")
    finally:
        # Cleanup all systems
        for system in systems:
            try:
                await system.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up {system.game_type.value} system: {e}")


async def demo_system_features():
    """Demonstrate various system features"""
    logger.info("=== System Features Demo ===")
    
    system = None
    try:
        # Create system with all features
        system = CompleteMQTTSystem(
            GameType.SICBO,
            Environment.DEVELOPMENT,
            enable_connection_pooling=True,
            enable_message_processing=True
        )
        
        await system.initialize()
        
        # Test different features
        logger.info("Testing system features...")
        
        # Test command sending
        command = {
            "command": "test",
            "arg": {
                "round_id": "feature_test_001",
                "test_data": "system features test"
            }
        }
        
        success = await system.send_command(command)
        logger.info(f"Command sending: {'Success' if success else 'Failed'}")
        
        # Test with connection pool
        success = await system.send_command(command, use_connection_pool=True)
        logger.info(f"Command with connection pool: {'Success' if success else 'Failed'}")
        
        # Test without connection pool
        success = await system.send_command(command, use_connection_pool=False)
        logger.info(f"Command without connection pool: {'Success' if success else 'Failed'}")
        
        # Show system capabilities
        status = system.get_system_status()
        logger.info(f"System capabilities:")
        logger.info(f"  Connection pooling: {system.enable_connection_pooling}")
        logger.info(f"  Message processing: {system.enable_message_processing}")
        logger.info(f"  Connection manager: {'Enabled' if 'connection_manager' in status else 'Disabled'}")
        logger.info(f"  Message processor: {'Enabled' if 'message_processor' in status else 'Disabled'}")
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Show final status
        final_status = system.get_system_status()
        logger.info(f"Final system status: {json.dumps(final_status, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in features demo: {e}")
    finally:
        if system:
            await system.cleanup()


async def demo_production_ready():
    """Demonstrate production-ready configuration"""
    logger.info("=== Production Ready Demo ===")
    
    system = None
    try:
        # Create production system
        system = CompleteMQTTSystem(
            GameType.SICBO,
            Environment.PRODUCTION,
            enable_connection_pooling=True,
            enable_message_processing=True
        )
        
        await system.initialize()
        
        # Show production configuration
        status = system.get_system_status()
        logger.info(f"Production system configuration:")
        logger.info(f"  Environment: {status['environment']}")
        logger.info(f"  Game Type: {status['game_type']}")
        logger.info(f"  Client ID: {status['config_info']['client_id']}")
        logger.info(f"  Game Code: {status['config_info']['game_code']}")
        
        # Test production operations
        logger.info("Testing production operations...")
        
        # Simulate multiple operations
        for i in range(5):
            success, result = await system.detect(f"prod_round_{i:03d}")
            logger.info(f"Production operation {i+1}: {'Success' if success else 'Failed'}")
            await asyncio.sleep(0.5)
        
        # Show production stats
        final_status = system.get_system_status()
        logger.info(f"Production system stats:")
        
        if "connection_manager" in final_status:
            conn_stats = final_status["connection_manager"]
            logger.info(f"  Total connections: {conn_stats['total_connections']}")
            logger.info(f"  Healthy connections: {conn_stats['healthy_connections']}")
            logger.info(f"  Total messages: {conn_stats['total_messages']}")
            logger.info(f"  Average response time: {conn_stats['avg_response_time']:.3f}s")
        
        if "message_processor" in final_status:
            msg_stats = final_status["message_processor"]
            logger.info(f"  Messages processed: {msg_stats['total_messages']}")
            logger.info(f"  Processing active: {msg_stats['is_processing']}")
        
    except Exception as e:
        logger.error(f"Error in production demo: {e}")
    finally:
        if system:
            await system.cleanup()


async def main():
    """Main demo function"""
    logger.info("Starting Complete MQTT System Demo")
    logger.info("This demo showcases all four refactoring phases:")
    logger.info("1. Unified MQTT Base Client")
    logger.info("2. Unified Configuration Manager")
    logger.info("3. Unified Message Processor")
    logger.info("4. Unified Connection Manager")
    
    # Run individual system demos
    await demo_complete_sicbo_system()
    await asyncio.sleep(1)
    
    await demo_complete_baccarat_system()
    await asyncio.sleep(1)
    
    await demo_complete_roulette_system()
    await asyncio.sleep(1)
    
    # Run advanced demos
    await demo_multiple_complete_systems()
    await asyncio.sleep(1)
    
    await demo_system_features()
    await asyncio.sleep(1)
    
    await demo_production_ready()
    
    logger.info("Complete MQTT System Demo completed")
    logger.info("All four refactoring phases have been successfully integrated!")


if __name__ == "__main__":
    asyncio.run(main())
