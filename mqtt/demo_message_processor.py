"""
Demo for Unified MQTT Message Processor

This module demonstrates how to use the UnifiedMessageProcessor for different
game types and message processing scenarios.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any
from mqtt.message_processor import (
    UnifiedMessageProcessor, Message, MessageType, MessagePriority,
    ProcessingStatus, JSONMessageValidator, GameMessageValidator,
    MessageLogger, MessageRouter, GameResultProcessor
)
from mqtt.config_manager import GameType, get_config


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CustomMessageTransformer:
    """Custom message transformer example"""
    
    def transform(self, message: Message) -> Message:
        """Transform message by adding metadata"""
        message.metadata["transformed"] = True
        message.metadata["transform_time"] = time.time()
        return message


class CustomMessageProcessor:
    """Custom message processor example"""
    
    def __init__(self, processor_name: str):
        self.processor_name = processor_name
    
    def process(self, message: Message) -> ProcessingResult:
        """Process message with custom logic"""
        logger.info(f"[{self.processor_name}] Processing message {message.id}")
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Add processing result to metadata
        message.metadata[f"{self.processor_name}_processed"] = True
        
        return ProcessingResult(
            success=True,
            result=f"Processed by {self.processor_name}",
            metadata={"processor": self.processor_name}
        )


def demo_basic_message_processing():
    """Demonstrate basic message processing"""
    logger.info("=== Basic Message Processing Demo ===")
    
    # Create message processor
    processor = UnifiedMessageProcessor(max_queue_size=100, max_workers=2)
    
    # Add validators
    processor.add_validator(JSONMessageValidator())
    processor.add_validator(GameMessageValidator("sicbo"))
    
    # Add transformers
    processor.add_transformer(CustomMessageTransformer())
    
    # Add processors
    processor.add_processor(MessageLogger(logger))
    processor.add_processor(CustomMessageProcessor("CustomProcessor1"))
    processor.add_processor(CustomMessageProcessor("CustomProcessor2"))
    
    # Add callbacks
    def message_callback(message: Message):
        logger.info(f"Message callback: {message.id} - {message.message_type.value}")
    
    def error_callback(message: Message, error: str):
        logger.error(f"Error callback: {message.id} - {error}")
    
    processor.add_message_callback(message_callback)
    processor.add_error_callback(error_callback)
    
    # Create test messages
    messages = [
        processor.create_message(
            topic="ikg/idp/SBO-001/command",
            payload=json.dumps({
                "command": "detect",
                "arg": {
                    "round_id": "test_001",
                    "input_stream": "rtmp://test.com/stream"
                }
            }),
            message_type=MessageType.COMMAND,
            priority=MessagePriority.HIGH
        ),
        processor.create_message(
            topic="ikg/idp/SBO-001/response",
            payload=json.dumps({
                "response": "result",
                "arg": {
                    "res": [1, 2, 3]
                }
            }),
            message_type=MessageType.RESPONSE,
            priority=MessagePriority.NORMAL
        ),
        processor.create_message(
            topic="ikg/idp/SBO-001/status",
            payload=json.dumps({
                "status": "ready",
                "timestamp": time.time()
            }),
            message_type=MessageType.STATUS,
            priority=MessagePriority.LOW
        )
    ]
    
    # Enqueue messages
    for message in messages:
        processor.enqueue_message(message)
        logger.info(f"Enqueued message: {message.id}")
    
    # Show queue status
    status = processor.get_queue_status()
    logger.info(f"Queue status: {status}")
    
    return processor


def demo_game_specific_processing():
    """Demonstrate game-specific message processing"""
    logger.info("\n=== Game-Specific Processing Demo ===")
    
    # Create processors for different games
    sicbo_processor = UnifiedMessageProcessor()
    baccarat_processor = UnifiedMessageProcessor()
    roulette_processor = UnifiedMessageProcessor()
    
    # Setup Sicbo processor
    sicbo_processor.add_validator(JSONMessageValidator())
    sicbo_processor.add_validator(GameMessageValidator("sicbo"))
    sicbo_processor.add_processor(MessageLogger(logger))
    sicbo_processor.add_processor(GameResultProcessor("sicbo"))
    
    # Setup Baccarat processor
    baccarat_processor.add_validator(JSONMessageValidator())
    baccarat_processor.add_validator(GameMessageValidator("baccarat"))
    baccarat_processor.add_processor(MessageLogger(logger))
    baccarat_processor.add_processor(GameResultProcessor("baccarat"))
    
    # Setup Roulette processor
    roulette_processor.add_validator(JSONMessageValidator())
    roulette_processor.add_validator(GameMessageValidator("roulette"))
    roulette_processor.add_processor(MessageLogger(logger))
    roulette_processor.add_processor(GameResultProcessor("roulette"))
    
    # Create game-specific messages
    sicbo_message = sicbo_processor.create_message(
        topic="ikg/idp/SBO-001/response",
        payload=json.dumps({
            "response": "result",
            "arg": {
                "res": [4, 5, 6]
            }
        }),
        message_type=MessageType.RESPONSE
    )
    
    baccarat_message = baccarat_processor.create_message(
        topic="ikg/idp/BAC-001/response",
        payload=json.dumps({
            "response": "result",
            "arg": {
                "res": ["A", "K", "Q", "J", "10", "9"]
            }
        }),
        message_type=MessageType.RESPONSE
    )
    
    roulette_message = roulette_processor.create_message(
        topic="ikg/idp/ROU-001/response",
        payload=json.dumps({
            "response": "result",
            "arg": {
                "res": "RED_17"
            }
        }),
        message_type=MessageType.RESPONSE
    )
    
    # Process messages
    processors = [
        (sicbo_processor, sicbo_message, "Sicbo"),
        (baccarat_processor, baccarat_message, "Baccarat"),
        (roulette_processor, roulette_message, "Roulette")
    ]
    
    for proc, msg, game_name in processors:
        proc.enqueue_message(msg)
        logger.info(f"Enqueued {game_name} message: {msg.id}")
    
    return processors


def demo_message_routing():
    """Demonstrate message routing"""
    logger.info("\n=== Message Routing Demo ===")
    
    processor = UnifiedMessageProcessor()
    
    # Add router
    processor.add_processor(MessageRouter())
    
    # Setup routing rules
    processor.add_route("ikg/idp/SBO-001/command", "ikg/idp/SBO-001/response")
    processor.add_route("ikg/idp/BAC-001/command", "ikg/idp/BAC-001/response")
    processor.add_route("ikg/idp/ROU-001/command", "ikg/idp/ROU-001/response")
    
    # Create messages with routing
    messages = [
        processor.create_message(
            topic="ikg/idp/SBO-001/command",
            payload=json.dumps({"command": "detect", "arg": {"round_id": "001"}}),
            message_type=MessageType.COMMAND
        ),
        processor.create_message(
            topic="ikg/idp/BAC-001/command",
            payload=json.dumps({"command": "detect", "arg": {"round_id": "002"}}),
            message_type=MessageType.COMMAND
        )
    ]
    
    # Enqueue messages
    for message in messages:
        processor.enqueue_message(message)
        logger.info(f"Enqueued message for routing: {message.topic}")
    
    return processor


def demo_error_handling():
    """Demonstrate error handling and retry mechanisms"""
    logger.info("\n=== Error Handling Demo ===")
    
    processor = UnifiedMessageProcessor()
    
    # Add validators
    processor.add_validator(JSONMessageValidator())
    
    # Add error callback
    def error_callback(message: Message, error: str):
        logger.error(f"Error in message {message.id}: {error}")
    
    processor.add_error_callback(error_callback)
    
    # Create invalid messages to trigger errors
    invalid_messages = [
        processor.create_message(
            topic="test/invalid",
            payload="invalid json",  # Invalid JSON
            message_type=MessageType.COMMAND,
            max_retries=2
        ),
        processor.create_message(
            topic="test/missing_field",
            payload=json.dumps({"invalid": "structure"}),  # Missing required fields
            message_type=MessageType.COMMAND,
            max_retries=1
        )
    ]
    
    # Enqueue invalid messages
    for message in invalid_messages:
        processor.enqueue_message(message)
        logger.info(f"Enqueued invalid message: {message.id}")
    
    return processor


def demo_priority_processing():
    """Demonstrate priority-based message processing"""
    logger.info("\n=== Priority Processing Demo ===")
    
    processor = UnifiedMessageProcessor()
    
    # Add simple processor
    processor.add_processor(MessageLogger(logger))
    
    # Create messages with different priorities
    messages = [
        processor.create_message(
            topic="test/low",
            payload="low priority message",
            message_type=MessageType.NOTIFICATION,
            priority=MessagePriority.LOW
        ),
        processor.create_message(
            topic="test/normal",
            payload="normal priority message",
            message_type=MessageType.NOTIFICATION,
            priority=MessagePriority.NORMAL
        ),
        processor.create_message(
            topic="test/high",
            payload="high priority message",
            message_type=MessageType.NOTIFICATION,
            priority=MessagePriority.HIGH
        ),
        processor.create_message(
            topic="test/critical",
            payload="critical priority message",
            message_type=MessageType.NOTIFICATION,
            priority=MessagePriority.CRITICAL
        )
    ]
    
    # Enqueue messages in reverse priority order
    for message in reversed(messages):
        processor.enqueue_message(message)
        logger.info(f"Enqueued {message.priority.name} priority message: {message.id}")
    
    # Show queue status
    status = processor.get_queue_status()
    logger.info(f"Queue status: {status}")
    
    return processor


async def demo_async_processing():
    """Demonstrate async message processing"""
    logger.info("\n=== Async Processing Demo ===")
    
    processor = UnifiedMessageProcessor()
    
    # Add processors
    processor.add_validator(JSONMessageValidator())
    processor.add_processor(MessageLogger(logger))
    processor.add_processor(CustomMessageProcessor("AsyncProcessor"))
    
    # Create messages
    messages = []
    for i in range(5):
        message = processor.create_message(
            topic=f"test/async/{i}",
            payload=json.dumps({"message_id": i, "data": f"test_data_{i}"}),
            message_type=MessageType.NOTIFICATION,
            priority=MessagePriority.NORMAL
        )
        messages.append(message)
        processor.enqueue_message(message)
    
    logger.info(f"Enqueued {len(messages)} messages for async processing")
    
    # Start processing
    processing_task = asyncio.create_task(processor.process_messages())
    
    # Let it process for a short time
    await asyncio.sleep(2)
    
    # Stop processing
    processor.stop_processing()
    processing_task.cancel()
    
    # Show results
    stats = processor.get_processing_stats()
    logger.info(f"Processing stats: {stats}")
    
    history = processor.get_message_history(10)
    logger.info(f"Processed {len(history)} messages")
    
    return processor


async def demo_integration_with_config():
    """Demonstrate integration with configuration manager"""
    logger.info("\n=== Integration with Config Manager Demo ===")
    
    # Load configuration
    config = get_config(GameType.SICBO)
    
    # Create processor with game-specific setup
    processor = UnifiedMessageProcessor()
    
    # Add game-specific validators and processors
    processor.add_validator(JSONMessageValidator())
    processor.add_validator(GameMessageValidator("sicbo"))
    processor.add_processor(MessageLogger(logger))
    processor.add_processor(GameResultProcessor("sicbo"))
    
    # Create message using configuration
    message = processor.create_message(
        topic=config.game_config.response_topic,
        payload=json.dumps({
            "response": "result",
            "arg": {
                "res": [1, 2, 3]
            }
        }),
        message_type=MessageType.RESPONSE,
        priority=MessagePriority.HIGH,
        metadata={"game_config": config.game_config.game_code}
    )
    
    # Process message
    processor.enqueue_message(message)
    logger.info(f"Enqueued message using config: {message.topic}")
    
    # Start processing
    processing_task = asyncio.create_task(processor.process_messages())
    
    # Let it process
    await asyncio.sleep(1)
    
    # Stop processing
    processor.stop_processing()
    processing_task.cancel()
    
    return processor


async def main():
    """Main demo function"""
    logger.info("Starting Unified MQTT Message Processor Demo")
    
    # Run demos
    demo_basic_message_processing()
    demo_game_specific_processing()
    demo_message_routing()
    demo_error_handling()
    demo_priority_processing()
    
    # Async demos
    await demo_async_processing()
    await demo_integration_with_config()
    
    logger.info("Message Processor Demo completed")


if __name__ == "__main__":
    asyncio.run(main())
