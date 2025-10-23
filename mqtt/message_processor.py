"""
Unified MQTT Message Processor

This module provides a unified message processing framework for MQTT clients
across different game types (Sicbo, Baccarat, Roulette).

Features:
- Unified message processing framework
- Message routing and forwarding
- Message queue and buffering
- Message validation and transformation
- Error handling and retry mechanisms
- Message history and analytics
- Plugin-based message processors
"""

import json
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor


class MessageType(Enum):
    """Message types"""
    COMMAND = "command"
    RESPONSE = "response"
    STATUS = "status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    NOTIFICATION = "notification"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ProcessingStatus(Enum):
    """Message processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Message:
    """Message data structure"""
    id: str
    topic: str
    payload: str
    message_type: MessageType
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    source: Optional[str] = None
    destination: Optional[str] = None
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed_at: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class ProcessingResult:
    """Message processing result"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    transformed_message: Optional[Message] = None
    should_forward: bool = False
    forward_topic: Optional[str] = None


class MessageValidator:
    """Message validation interface"""
    
    def validate(self, message: Message) -> Tuple[bool, Optional[str]]:
        """
        Validate message
        
        Args:
            message: Message to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        raise NotImplementedError


class MessageTransformer:
    """Message transformation interface"""
    
    def transform(self, message: Message) -> Message:
        """
        Transform message
        
        Args:
            message: Message to transform
            
        Returns:
            Transformed message
        """
        raise NotImplementedError


class MessageProcessor:
    """Message processing interface"""
    
    def process(self, message: Message) -> ProcessingResult:
        """
        Process message
        
        Args:
            message: Message to process
            
        Returns:
            Processing result
        """
        raise NotImplementedError


class JSONMessageValidator(MessageValidator):
    """JSON message validator"""
    
    def validate(self, message: Message) -> Tuple[bool, Optional[str]]:
        """Validate JSON message format"""
        try:
            json.loads(message.payload)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {e}"


class GameMessageValidator(MessageValidator):
    """Game-specific message validator"""
    
    def __init__(self, game_type: str):
        self.game_type = game_type
    
    def validate(self, message: Message) -> Tuple[bool, Optional[str]]:
        """Validate game-specific message format"""
        try:
            data = json.loads(message.payload)
            
            # Check required fields
            if "command" not in data and "response" not in data:
                return False, "Missing command or response field"
            
            # Game-specific validation
            if self.game_type == "sicbo":
                return self._validate_sicbo_message(data)
            elif self.game_type == "baccarat":
                return self._validate_baccarat_message(data)
            elif self.game_type == "roulette":
                return self._validate_roulette_message(data)
            
            return True, None
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {e}"
    
    def _validate_sicbo_message(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate Sicbo message"""
        if "command" in data and data["command"] == "detect":
            if "arg" not in data:
                return False, "Missing arg field in detect command"
            if "round_id" not in data["arg"]:
                return False, "Missing round_id in detect command"
        
        return True, None
    
    def _validate_baccarat_message(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate Baccarat message"""
        if "command" in data and data["command"] == "detect":
            if "arg" not in data:
                return False, "Missing arg field in detect command"
            if "round_id" not in data["arg"]:
                return False, "Missing round_id in detect command"
        
        return True, None
    
    def _validate_roulette_message(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate Roulette message"""
        if "command" in data and data["command"] == "detect":
            if "arg" not in data:
                return False, "Missing arg field in detect command"
            if "round_id" not in data["arg"]:
                return False, "Missing round_id in detect command"
        
        return True, None


class MessageLogger(MessageProcessor):
    """Message logging processor"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def process(self, message: Message) -> ProcessingResult:
        """Log message"""
        self.logger.info(
            f"Message {message.id}: {message.message_type.value} on {message.topic}"
        )
        return ProcessingResult(success=True, result="logged")


class MessageRouter(MessageProcessor):
    """Message routing processor"""
    
    def __init__(self):
        self.routes: Dict[str, List[str]] = defaultdict(list)
    
    def add_route(self, source_pattern: str, destination_topic: str):
        """Add routing rule"""
        self.routes[source_pattern].append(destination_topic)
    
    def process(self, message: Message) -> ProcessingResult:
        """Route message based on topic patterns"""
        destinations = []
        
        for pattern, topics in self.routes.items():
            if self._topic_matches(message.topic, pattern):
                destinations.extend(topics)
        
        if destinations:
            return ProcessingResult(
                success=True,
                should_forward=True,
                forward_topic=destinations[0]  # Forward to first destination
            )
        
        return ProcessingResult(success=True)
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern"""
        if pattern == topic:
            return True
        
        if "#" in pattern:
            prefix = pattern.replace("#", "")
            return topic.startswith(prefix)
        
        if "+" in pattern:
            pattern_parts = pattern.split("/")
            topic_parts = topic.split("/")
            
            if len(pattern_parts) != len(topic_parts):
                return False
            
            for p, t in zip(pattern_parts, topic_parts):
                if p != "+" and p != t:
                    return False
            return True
        
        return False


class GameResultProcessor(MessageProcessor):
    """Game result processing"""
    
    def __init__(self, game_type: str):
        self.game_type = game_type
    
    def process(self, message: Message) -> ProcessingResult:
        """Process game result message"""
        try:
            data = json.loads(message.payload)
            
            if "response" in data and data["response"] == "result":
                if "arg" in data and "res" in data["arg"]:
                    result = data["arg"]["res"]
                    
                    # Validate result based on game type
                    if self._validate_result(result):
                        return ProcessingResult(
                            success=True,
                            result=result,
                            metadata={"game_type": self.game_type, "validated": True}
                        )
                    else:
                        return ProcessingResult(
                            success=False,
                            error=f"Invalid {self.game_type} result format"
                        )
            
            return ProcessingResult(success=True)
            
        except Exception as e:
            return ProcessingResult(success=False, error=str(e))
    
    def _validate_result(self, result: Any) -> bool:
        """Validate game result"""
        if self.game_type == "sicbo":
            return isinstance(result, list) and len(result) == 3
        elif self.game_type == "baccarat":
            return isinstance(result, list) and len(result) == 6
        elif self.game_type == "roulette":
            return isinstance(result, (str, int, list))
        
        return True


class UnifiedMessageProcessor:
    """
    Unified MQTT Message Processor
    
    This class provides a comprehensive message processing framework
    for MQTT clients across different game types.
    """

    def __init__(self, max_queue_size: int = 1000, max_workers: int = 4):
        """
        Initialize unified message processor
        
        Args:
            max_queue_size: Maximum message queue size
            max_workers: Maximum number of worker threads
        """
        self.max_queue_size = max_queue_size
        self.max_workers = max_workers
        
        # Message queues (priority-based)
        self.message_queues: Dict[MessagePriority, deque] = {
            priority: deque(maxlen=max_queue_size) 
            for priority in MessagePriority
        }
        
        # Processing pipeline
        self.validators: List[MessageValidator] = []
        self.transformers: List[MessageTransformer] = []
        self.processors: List[MessageProcessor] = []
        
        # Message routing
        self.router = MessageRouter()
        
        # Message history and analytics
        self.message_history: deque = deque(maxlen=max_queue_size)
        self.processing_stats: Dict[str, int] = defaultdict(int)
        
        # Threading and async support
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing_lock = threading.Lock()
        self.is_processing = False
        
        # Logging
        self.logger = logging.getLogger("UnifiedMessageProcessor")
        
        # Callbacks
        self.message_callbacks: List[Callable[[Message], None]] = []
        self.error_callbacks: List[Callable[[Message, str], None]] = []

    def add_validator(self, validator: MessageValidator):
        """Add message validator"""
        self.validators.append(validator)
        self.logger.info(f"Added validator: {validator.__class__.__name__}")

    def add_transformer(self, transformer: MessageTransformer):
        """Add message transformer"""
        self.transformers.append(transformer)
        self.logger.info(f"Added transformer: {transformer.__class__.__name__}")

    def add_processor(self, processor: MessageProcessor):
        """Add message processor"""
        self.processors.append(processor)
        self.logger.info(f"Added processor: {processor.__class__.__name__}")

    def add_message_callback(self, callback: Callable[[Message], None]):
        """Add message callback"""
        self.message_callbacks.append(callback)
        self.logger.info("Added message callback")

    def add_error_callback(self, callback: Callable[[Message, str], None]):
        """Add error callback"""
        self.error_callbacks.append(callback)
        self.logger.info("Added error callback")

    def enqueue_message(self, message: Message) -> bool:
        """
        Enqueue message for processing
        
        Args:
            message: Message to enqueue
            
        Returns:
            True if enqueued successfully, False otherwise
        """
        try:
            with self.processing_lock:
                queue = self.message_queues[message.priority]
                
                if len(queue) >= self.max_queue_size:
                    self.logger.warning(f"Message queue full, dropping message {message.id}")
                    return False
                
                queue.append(message)
                self.logger.debug(f"Enqueued message {message.id} with priority {message.priority.name}")
                
                # Notify callbacks
                for callback in self.message_callbacks:
                    try:
                        callback(message)
                    except Exception as e:
                        self.logger.error(f"Error in message callback: {e}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error enqueueing message: {e}")
            return False

    def create_message(
        self,
        topic: str,
        payload: str,
        message_type: MessageType,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Message:
        """
        Create message with unique ID
        
        Args:
            topic: MQTT topic
            payload: Message payload
            message_type: Message type
            priority: Message priority
            correlation_id: Correlation ID for message tracking
            **kwargs: Additional message attributes
            
        Returns:
            Message object
        """
        message_id = f"{int(time.time() * 1000)}_{hash(payload) % 10000}"
        
        return Message(
            id=message_id,
            topic=topic,
            payload=payload,
            message_type=message_type,
            priority=priority,
            correlation_id=correlation_id,
            **kwargs
        )

    async def process_messages(self):
        """Process messages from queues"""
        self.is_processing = True
        self.logger.info("Starting message processing")
        
        try:
            while self.is_processing:
                # Process messages by priority (highest first)
                for priority in reversed(list(MessagePriority)):
                    queue = self.message_queues[priority]
                    
                    if queue:
                        message = queue.popleft()
                        await self._process_single_message(message)
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
        except Exception as e:
            self.logger.error(f"Error in message processing loop: {e}")
        finally:
            self.logger.info("Message processing stopped")

    async def _process_single_message(self, message: Message):
        """Process a single message"""
        try:
            message.processing_status = ProcessingStatus.PROCESSING
            
            # Validation phase
            for validator in self.validators:
                is_valid, error = validator.validate(message)
                if not is_valid:
                    message.processing_status = ProcessingStatus.FAILED
                    message.error_message = error
                    self.logger.error(f"Message validation failed: {error}")
                    
                    # Notify error callbacks
                    for callback in self.error_callbacks:
                        try:
                            callback(message, error)
                        except Exception as e:
                            self.logger.error(f"Error in error callback: {e}")
                    return
            
            # Transformation phase
            for transformer in self.transformers:
                message = transformer.transform(message)
            
            # Processing phase
            for processor in self.processors:
                result = processor.process(message)
                
                if not result.success:
                    message.processing_status = ProcessingStatus.FAILED
                    message.error_message = result.error
                    self.logger.error(f"Message processing failed: {result.error}")
                    
                    # Retry logic
                    if message.retry_count < message.max_retries:
                        message.retry_count += 1
                        message.processing_status = ProcessingStatus.RETRYING
                        self.logger.info(f"Retrying message {message.id} (attempt {message.retry_count})")
                        
                        # Re-enqueue with higher priority
                        retry_priority = MessagePriority(min(message.priority.value + 1, MessagePriority.CRITICAL.value))
                        message.priority = retry_priority
                        self.enqueue_message(message)
                        return
                    
                    # Notify error callbacks
                    for callback in self.error_callbacks:
                        try:
                            callback(message, result.error)
                        except Exception as e:
                            self.logger.error(f"Error in error callback: {e}")
                    return
                
                # Handle forwarding
                if result.should_forward and result.forward_topic:
                    forward_message = self.create_message(
                        topic=result.forward_topic,
                        payload=message.payload,
                        message_type=message.message_type,
                        priority=message.priority,
                        correlation_id=message.correlation_id
                    )
                    self.enqueue_message(forward_message)
            
            # Mark as completed
            message.processing_status = ProcessingStatus.COMPLETED
            message.processed_at = time.time()
            
            # Update statistics
            self.processing_stats[f"{message.message_type.value}_completed"] += 1
            
            # Add to history
            self.message_history.append(message)
            
            self.logger.debug(f"Message {message.id} processed successfully")
            
        except Exception as e:
            message.processing_status = ProcessingStatus.FAILED
            message.error_message = str(e)
            self.logger.error(f"Error processing message {message.id}: {e}")
            
            # Notify error callbacks
            for callback in self.error_callbacks:
                try:
                    callback(message, str(e))
                except Exception as e:
                    self.logger.error(f"Error in error callback: {e}")

    def stop_processing(self):
        """Stop message processing"""
        self.is_processing = False
        self.logger.info("Stopping message processing")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get message queue status"""
        with self.processing_lock:
            return {
                priority.name: len(queue) 
                for priority, queue in self.message_queues.items()
            }

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            "total_messages": len(self.message_history),
            "queue_status": self.get_queue_status(),
            "processing_stats": dict(self.processing_stats),
            "is_processing": self.is_processing
        }

    def get_message_history(self, limit: int = 100) -> List[Message]:
        """Get recent message history"""
        return list(self.message_history)[-limit:]

    def clear_history(self):
        """Clear message history"""
        self.message_history.clear()
        self.processing_stats.clear()
        self.logger.info("Message history cleared")

    def add_route(self, source_pattern: str, destination_topic: str):
        """Add message routing rule"""
        self.router.add_route(source_pattern, destination_topic)
        self.logger.info(f"Added route: {source_pattern} -> {destination_topic}")

    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.stop_processing()
            self.executor.shutdown(wait=False)
        except Exception:
            pass
