"""
Demo for Integrated MQTT System

This module demonstrates how to use the IntegratedMQTTSystem for different
game types with complete message processing capabilities.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any
from mqtt.integrated_system import (
    IntegratedMQTTSystem, create_sicbo_system, create_baccarat_system,
    create_roulette_system
)
from mqtt.config_manager import GameType, Environment
from mqtt.message_processor import Message, MessageType


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_sicbo_system():
    """Demonstrate Sicbo integrated system"""
    logger.info("=== Sicbo Integrated System Demo ===")
    
    system = None
    try:
        # Create and initialize system
        system = await create_sicbo_system(Environment.DEVELOPMENT)
        
        # Add custom callbacks
        def message_callback(message: Message):
            logger.info(f"Sicbo message callback: {message.id} - {message.message_type.value}")
        
        def error_callback(message: Message, error: str):
            logger.error(f"Sicbo error callback: {message.id} - {error}")
        
        system.add_message_callback(message_callback)
        system.add_error_callback(error_callback)
        
        # Show system status
        status = system.get_system_status()
        logger.info(f"Sicbo system status: {json.dumps(status, indent=2)}")
        
        # Test detection
        success, result = await system.detect(
            "demo_sicbo_001",
            input_stream="rtmp://192.168.88.54:1935/live/r14_asb0011",
            output_stream="https://pull-tc.stream.iki-utl.cc/live/r456_dice.flv"
        )
        
        if success:
            logger.info(f"Sicbo detection result: {result}")
        
        # Wait for any additional processing
        await asyncio.sleep(2)
        
        # Show processing stats
        stats = system.message_processor.get_processing_stats()
        logger.info(f"Sicbo processing stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in Sicbo demo: {e}")
    finally:
        if system:
            await system.cleanup()


async def demo_baccarat_system():
    """Demonstrate Baccarat integrated system"""
    logger.info("=== Baccarat Integrated System Demo ===")
    
    system = None
    try:
        # Create and initialize system
        system = await create_baccarat_system(Environment.DEVELOPMENT)
        
        # Add custom callbacks
        def message_callback(message: Message):
            logger.info(f"Baccarat message callback: {message.id} - {message.message_type.value}")
        
        def error_callback(message: Message, error: str):
            logger.error(f"Baccarat error callback: {message.id} - {error}")
        
        system.add_message_callback(message_callback)
        system.add_error_callback(error_callback)
        
        # Show system status
        status = system.get_system_status()
        logger.info(f"Baccarat system status: {json.dumps(status, indent=2)}")
        
        # Test detection
        success, result = await system.detect(
            "demo_baccarat_001",
            input="rtmp://192.168.20.10:1935/live/r111_baccarat"
        )
        
        if success:
            logger.info(f"Baccarat detection result: {result}")
        
        # Wait for any additional processing
        await asyncio.sleep(2)
        
        # Show processing stats
        stats = system.message_processor.get_processing_stats()
        logger.info(f"Baccarat processing stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in Baccarat demo: {e}")
    finally:
        if system:
            await system.cleanup()


async def demo_roulette_system():
    """Demonstrate Roulette integrated system"""
    logger.info("=== Roulette Integrated System Demo ===")
    
    system = None
    try:
        # Create and initialize system
        system = await create_roulette_system(Environment.DEVELOPMENT)
        
        # Add custom callbacks
        def message_callback(message: Message):
            logger.info(f"Roulette message callback: {message.id} - {message.message_type.value}")
        
        def error_callback(message: Message, error: str):
            logger.error(f"Roulette error callback: {message.id} - {error}")
        
        system.add_message_callback(message_callback)
        system.add_error_callback(error_callback)
        
        # Show system status
        status = system.get_system_status()
        logger.info(f"Roulette system status: {json.dumps(status, indent=2)}")
        
        # Test detection
        success, result = await system.detect(
            "demo_roulette_001",
            input_stream="rtmp://192.168.20.10:1935/live/r111_roulette"
        )
        
        if success:
            logger.info(f"Roulette detection result: {result}")
        
        # Wait for any additional processing
        await asyncio.sleep(2)
        
        # Show processing stats
        stats = system.message_processor.get_processing_stats()
        logger.info(f"Roulette processing stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in Roulette demo: {e}")
    finally:
        if system:
            await system.cleanup()


async def demo_multiple_systems():
    """Demonstrate multiple systems running concurrently"""
    logger.info("=== Multiple Systems Demo ===")
    
    systems = []
    try:
        # Create multiple systems
        sicbo_system = IntegratedMQTTSystem(GameType.SICBO, Environment.DEVELOPMENT)
        baccarat_system = IntegratedMQTTSystem(GameType.BACCARAT, Environment.DEVELOPMENT)
        roulette_system = IntegratedMQTTSystem(GameType.ROULETTE, Environment.DEVELOPMENT)
        
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
        for system in systems:
            stats = system.message_processor.get_processing_stats()
            logger.info(f"{system.game_type.value} stats: {stats['total_messages']} messages processed")
        
    except Exception as e:
        logger.error(f"Error in multiple systems demo: {e}")
    finally:
        # Cleanup all systems
        for system in systems:
            try:
                await system.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up {system.game_type.value} system: {e}")


async def demo_custom_message_processing():
    """Demonstrate custom message processing"""
    logger.info("=== Custom Message Processing Demo ===")
    
    system = None
    try:
        # Create system
        system = IntegratedMQTTSystem(GameType.SICBO, Environment.DEVELOPMENT)
        await system.initialize()
        
        # Add custom processor
        from mqtt.message_processor import MessageProcessor, ProcessingResult
        
        class CustomProcessor(MessageProcessor):
            def process(self, message: Message) -> ProcessingResult:
                logger.info(f"Custom processor handling: {message.id}")
                
                # Add custom metadata
                message.metadata["custom_processed"] = True
                message.metadata["custom_timestamp"] = time.time()
                
                return ProcessingResult(
                    success=True,
                    result="Custom processing completed",
                    metadata={"processor": "CustomProcessor"}
                )
        
        # Add custom processor to the system
        system.message_processor.add_processor(CustomProcessor())
        
        # Send a test command
        command = {
            "command": "test",
            "arg": {
                "round_id": "custom_test_001",
                "test_data": "custom processing test"
            }
        }
        
        success = await system.send_command(command)
        logger.info(f"Custom command sent: {'Success' if success else 'Failed'}")
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Show message history
        history = system.message_processor.get_message_history(10)
        logger.info(f"Processed {len(history)} messages")
        
        for message in history:
            if message.metadata.get("custom_processed"):
                logger.info(f"Custom processed message: {message.id}")
        
    except Exception as e:
        logger.error(f"Error in custom processing demo: {e}")
    finally:
        if system:
            await system.cleanup()


async def demo_error_handling():
    """Demonstrate error handling"""
    logger.info("=== Error Handling Demo ===")
    
    system = None
    try:
        # Create system
        system = IntegratedMQTTSystem(GameType.SICBO, Environment.DEVELOPMENT)
        await system.initialize()
        
        # Add error callback
        error_count = 0
        
        def error_callback(message: Message, error: str):
            nonlocal error_count
            error_count += 1
            logger.error(f"Error #{error_count}: {message.id} - {error}")
        
        system.add_error_callback(error_callback)
        
        # Send invalid command to trigger error
        invalid_command = {
            "invalid": "command",  # Missing required fields
            "malformed": True
        }
        
        success = await system.send_command(invalid_command)
        logger.info(f"Invalid command sent: {'Success' if success else 'Failed'}")
        
        # Wait for error processing
        await asyncio.sleep(2)
        
        logger.info(f"Total errors handled: {error_count}")
        
        # Show error stats
        stats = system.message_processor.get_processing_stats()
        logger.info(f"Error handling stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in error handling demo: {e}")
    finally:
        if system:
            await system.cleanup()


async def main():
    """Main demo function"""
    logger.info("Starting Integrated MQTT System Demo")
    
    # Run individual system demos
    await demo_sicbo_system()
    await asyncio.sleep(1)
    
    await demo_baccarat_system()
    await asyncio.sleep(1)
    
    await demo_roulette_system()
    await asyncio.sleep(1)
    
    # Run advanced demos
    await demo_multiple_systems()
    await asyncio.sleep(1)
    
    await demo_custom_message_processing()
    await asyncio.sleep(1)
    
    await demo_error_handling()
    
    logger.info("Integrated MQTT System Demo completed")


if __name__ == "__main__":
    asyncio.run(main())
