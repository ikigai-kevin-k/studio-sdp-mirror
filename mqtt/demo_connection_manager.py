"""
Demo for Unified MQTT Connection Manager

This module demonstrates how to use the UnifiedConnectionManager for
connection pooling, load balancing, and health monitoring.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Set
from mqtt.connection_manager import (
    UnifiedConnectionManager, ConnectionType, ConnectionState,
    ConnectionInfo, ConnectionMetrics
)
from mqtt.base_client import UnifiedMQTTClient
from mqtt.config_manager import BrokerConfig


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mock_client(client_id: str, broker: str, port: int) -> UnifiedMQTTClient:
    """Create mock MQTT client for testing"""
    broker_configs = [
        BrokerConfig(broker=broker, port=port, priority=1)
    ]
    
    client = UnifiedMQTTClient(
        client_id=client_id,
        broker_configs=broker_configs
    )
    
    # Mock connection state
    client.connection_state = ConnectionState.CONNECTED
    
    return client


async def demo_basic_connection_management():
    """Demonstrate basic connection management"""
    logger.info("=== Basic Connection Management Demo ===")
    
    manager = UnifiedConnectionManager(max_connections=5)
    
    try:
        # Start manager
        await manager.start()
        
        # Create connections
        connections = []
        
        # Create primary connections
        for i in range(3):
            conn_id = await manager.create_connection(
                client_id=f"primary_client_{i}",
                broker="192.168.20.9",
                port=1883,
                connection_type=ConnectionType.PRIMARY,
                tags={"game": "sicbo", "priority": "high"},
                client_factory=create_mock_client
            )
            if conn_id:
                connections.append(conn_id)
                logger.info(f"Created primary connection: {conn_id}")
        
        # Create secondary connections
        for i in range(2):
            conn_id = await manager.create_connection(
                client_id=f"secondary_client_{i}",
                broker="192.168.20.10",
                port=1883,
                connection_type=ConnectionType.SECONDARY,
                tags={"game": "baccarat", "priority": "medium"},
                client_factory=create_mock_client
            )
            if conn_id:
                connections.append(conn_id)
                logger.info(f"Created secondary connection: {conn_id}")
        
        # Show connection stats
        stats = manager.get_connection_stats()
        logger.info(f"Connection stats: {json.dumps(stats, indent=2)}")
        
        # List all connections
        all_connections = manager.list_connections()
        logger.info(f"Total connections: {len(all_connections)}")
        
        for conn in all_connections:
            logger.info(f"Connection {conn.id}: {conn.broker}:{conn.port} ({conn.connection_type.value})")
        
        # Wait for health checks
        await asyncio.sleep(5)
        
        # Show updated stats
        stats = manager.get_connection_stats()
        logger.info(f"Updated stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in basic demo: {e}")
    finally:
        await manager.stop()


async def demo_load_balancing():
    """Demonstrate load balancing"""
    logger.info("\n=== Load Balancing Demo ===")
    
    manager = UnifiedConnectionManager(
        max_connections=5,
        load_balance_strategy="round_robin"
    )
    
    try:
        await manager.start()
        
        # Create multiple connections
        brokers = ["192.168.20.9", "192.168.20.10", "192.168.20.11"]
        
        for broker in brokers:
            conn_id = await manager.create_connection(
                client_id=f"client_{broker.split('.')[-1]}",
                broker=broker,
                port=1883,
                connection_type=ConnectionType.PRIMARY,
                client_factory=create_mock_client
            )
            if conn_id:
                logger.info(f"Created connection to {broker}")
        
        # Test load balancing
        logger.info("Testing load balancing...")
        
        for i in range(10):
            connection = await manager.get_connection()
            if connection:
                logger.info(f"Request {i+1}: Selected {connection.broker} ({connection.id})")
            else:
                logger.warning(f"Request {i+1}: No connection available")
            
            await asyncio.sleep(0.1)
        
        # Test different strategies
        strategies = ["round_robin", "least_connections", "health_score", "response_time"]
        
        for strategy in strategies:
            logger.info(f"\nTesting {strategy} strategy:")
            manager.load_balancer.strategy = strategy
            
            for i in range(5):
                connection = await manager.get_connection()
                if connection:
                    logger.info(f"  Request {i+1}: {connection.broker}")
                await asyncio.sleep(0.1)
        
    except Exception as e:
        logger.error(f"Error in load balancing demo: {e}")
    finally:
        await manager.stop()


async def demo_health_monitoring():
    """Demonstrate health monitoring"""
    logger.info("\n=== Health Monitoring Demo ===")
    
    manager = UnifiedConnectionManager(
        max_connections=3,
        health_check_interval=5.0
    )
    
    try:
        await manager.start()
        
        # Add callbacks
        def connection_callback(conn_info: ConnectionInfo):
            logger.info(f"Connection callback: {conn_info.id} - {conn_info.state.value}")
        
        def error_callback(conn_info: ConnectionInfo, error: str):
            logger.error(f"Error callback: {conn_info.id} - {error}")
        
        manager.add_connection_callback(connection_callback)
        manager.add_error_callback(error_callback)
        
        # Create connections
        connections = []
        for i in range(3):
            conn_id = await manager.create_connection(
                client_id=f"health_client_{i}",
                broker=f"192.168.20.{9+i}",
                port=1883,
                connection_type=ConnectionType.PRIMARY,
                client_factory=create_mock_client
            )
            if conn_id:
                connections.append(conn_id)
        
        logger.info(f"Created {len(connections)} connections for health monitoring")
        
        # Monitor health for a while
        for i in range(6):  # Monitor for 30 seconds
            await asyncio.sleep(5)
            
            stats = manager.get_connection_stats()
            logger.info(f"Health check {i+1}: {stats['healthy_connections']}/{stats['total_connections']} healthy")
            
            # Show individual connection health
            for conn_id in connections:
                conn_info = manager.get_connection_info(conn_id)
                if conn_info:
                    health_score = conn_info.metrics.health_score
                    is_healthy = conn_info.metrics.is_healthy
                    logger.info(f"  {conn_id}: health_score={health_score:.2f}, healthy={is_healthy}")
        
    except Exception as e:
        logger.error(f"Error in health monitoring demo: {e}")
    finally:
        await manager.stop()


async def demo_connection_filtering():
    """Demonstrate connection filtering"""
    logger.info("\n=== Connection Filtering Demo ===")
    
    manager = UnifiedConnectionManager(max_connections=10)
    
    try:
        await manager.start()
        
        # Create connections with different tags
        game_types = ["sicbo", "baccarat", "roulette"]
        priorities = ["high", "medium", "low"]
        
        for game in game_types:
            for priority in priorities:
                conn_id = await manager.create_connection(
                    client_id=f"{game}_{priority}_client",
                    broker=f"192.168.20.{9 + hash(game) % 3}",
                    port=1883,
                    connection_type=ConnectionType.PRIMARY,
                    tags={game, priority},
                    client_factory=create_mock_client
                )
                if conn_id:
                    logger.info(f"Created {game} {priority} connection: {conn_id}")
        
        # Test filtering by game type
        logger.info("\nFiltering by game type:")
        for game in game_types:
            connection = await manager.get_connection(tags={game})
            if connection:
                logger.info(f"  {game}: {connection.id} (tags: {connection.tags})")
        
        # Test filtering by priority
        logger.info("\nFiltering by priority:")
        for priority in priorities:
            connection = await manager.get_connection(tags={priority})
            if connection:
                logger.info(f"  {priority}: {connection.id} (tags: {connection.tags})")
        
        # Test filtering by multiple tags
        logger.info("\nFiltering by multiple tags:")
        connection = await manager.get_connection(tags={"sicbo", "high"})
        if connection:
            logger.info(f"  sicbo+high: {connection.id} (tags: {connection.tags})")
        
        # Test filtering by broker
        logger.info("\nFiltering by broker:")
        connection = await manager.get_connection(broker="192.168.20.9")
        if connection:
            logger.info(f"  192.168.20.9: {connection.id}")
        
        # Test filtering by connection type
        logger.info("\nFiltering by connection type:")
        connection = await manager.get_connection(connection_type=ConnectionType.PRIMARY)
        if connection:
            logger.info(f"  PRIMARY: {connection.id}")
        
    except Exception as e:
        logger.error(f"Error in filtering demo: {e}")
    finally:
        await manager.stop()


async def demo_connection_cleanup():
    """Demonstrate connection cleanup"""
    logger.info("\n=== Connection Cleanup Demo ===")
    
    manager = UnifiedConnectionManager(
        max_connections=5,
        max_idle_time=10.0  # Short idle time for demo
    )
    
    try:
        await manager.start()
        
        # Create connections
        connections = []
        for i in range(3):
            conn_id = await manager.create_connection(
                client_id=f"cleanup_client_{i}",
                broker=f"192.168.20.{9+i}",
                port=1883,
                connection_type=ConnectionType.PRIMARY,
                client_factory=create_mock_client
            )
            if conn_id:
                connections.append(conn_id)
        
        logger.info(f"Created {len(connections)} connections")
        
        # Use some connections
        for i in range(3):
            connection = await manager.get_connection()
            if connection:
                logger.info(f"Using connection: {connection.id}")
            await asyncio.sleep(1)
        
        # Wait for idle timeout
        logger.info("Waiting for idle timeout...")
        await asyncio.sleep(15)
        
        # Check remaining connections
        stats = manager.get_connection_stats()
        logger.info(f"Remaining connections: {stats['total_connections']}")
        
        # Manually remove a connection
        if connections:
            conn_id = connections[0]
            success = await manager.remove_connection(conn_id)
            logger.info(f"Manually removed {conn_id}: {'Success' if success else 'Failed'}")
        
        # Final stats
        stats = manager.get_connection_stats()
        logger.info(f"Final stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in cleanup demo: {e}")
    finally:
        await manager.stop()


async def demo_performance_monitoring():
    """Demonstrate performance monitoring"""
    logger.info("\n=== Performance Monitoring Demo ===")
    
    manager = UnifiedConnectionManager(max_connections=3)
    
    try:
        await manager.start()
        
        # Create connections
        connections = []
        for i in range(3):
            conn_id = await manager.create_connection(
                client_id=f"perf_client_{i}",
                broker=f"192.168.20.{9+i}",
                port=1883,
                connection_type=ConnectionType.PRIMARY,
                client_factory=create_mock_client
            )
            if conn_id:
                connections.append(conn_id)
        
        # Simulate message processing
        logger.info("Simulating message processing...")
        
        for i in range(20):
            connection = await manager.get_connection()
            if connection:
                # Simulate response time
                response_time = 0.1 + (i % 3) * 0.05  # Vary response times
                connection.metrics.response_times.append(response_time)
                connection.metrics.message_count += 1
                
                if i % 5 == 0:
                    logger.info(f"Processed {i+1} messages, current connection: {connection.broker}")
        
        # Show performance metrics
        logger.info("\nPerformance metrics:")
        stats = manager.get_connection_stats()
        logger.info(f"Total messages: {stats['total_messages']}")
        logger.info(f"Average response time: {stats['avg_response_time']:.3f}s")
        
        # Show individual connection metrics
        for conn_id in connections:
            conn_info = manager.get_connection_info(conn_id)
            if conn_info:
                metrics = conn_info.metrics
                logger.info(f"Connection {conn_id}:")
                logger.info(f"  Messages: {metrics.message_count}")
                logger.info(f"  Response times: {len(metrics.response_times)} samples")
                logger.info(f"  Health score: {metrics.health_score:.2f}")
                logger.info(f"  Is healthy: {metrics.is_healthy}")
        
    except Exception as e:
        logger.error(f"Error in performance demo: {e}")
    finally:
        await manager.stop()


async def demo_integration_with_systems():
    """Demonstrate integration with other MQTT systems"""
    logger.info("\n=== Integration Demo ===")
    
    manager = UnifiedConnectionManager(max_connections=3)
    
    try:
        await manager.start()
        
        # Create connections for different game types
        game_configs = [
            ("sicbo", "192.168.20.9", {"game": "sicbo", "priority": "high"}),
            ("baccarat", "192.168.20.10", {"game": "baccarat", "priority": "medium"}),
            ("roulette", "192.168.20.11", {"game": "roulette", "priority": "low"})
        ]
        
        connections = []
        for game, broker, tags in game_configs:
            conn_id = await manager.create_connection(
                client_id=f"{game}_integration_client",
                broker=broker,
                port=1883,
                connection_type=ConnectionType.PRIMARY,
                tags=tags,
                client_factory=create_mock_client
            )
            if conn_id:
                connections.append(conn_id)
                logger.info(f"Created {game} integration connection: {conn_id}")
        
        # Simulate game-specific operations
        logger.info("\nSimulating game operations:")
        
        for game in ["sicbo", "baccarat", "roulette"]:
            connection = await manager.get_connection(tags={game})
            if connection:
                logger.info(f"  {game}: Using connection {connection.broker}")
                
                # Simulate some operations
                for i in range(3):
                    connection.metrics.message_count += 1
                    connection.metrics.response_times.append(0.1 + i * 0.02)
                    await asyncio.sleep(0.1)
        
        # Show final integration stats
        stats = manager.get_connection_stats()
        logger.info(f"\nIntegration stats: {json.dumps(stats, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error in integration demo: {e}")
    finally:
        await manager.stop()


async def main():
    """Main demo function"""
    logger.info("Starting Unified MQTT Connection Manager Demo")
    
    # Run demos
    await demo_basic_connection_management()
    await asyncio.sleep(1)
    
    await demo_load_balancing()
    await asyncio.sleep(1)
    
    await demo_health_monitoring()
    await asyncio.sleep(1)
    
    await demo_connection_filtering()
    await asyncio.sleep(1)
    
    await demo_connection_cleanup()
    await asyncio.sleep(1)
    
    await demo_performance_monitoring()
    await asyncio.sleep(1)
    
    await demo_integration_with_systems()
    
    logger.info("Connection Manager Demo completed")


if __name__ == "__main__":
    asyncio.run(main())
