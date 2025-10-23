"""
Unified MQTT Connection Manager

This module provides a unified connection management system for MQTT clients
across different game types (Sicbo, Baccarat, Roulette).

Features:
- Connection pooling and load balancing
- Health monitoring and automatic failover
- Connection statistics and analytics
- Resource management and cleanup
- Connection lifecycle management
- Performance monitoring and optimization
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import weakref
from concurrent.futures import ThreadPoolExecutor
import statistics


class ConnectionState(Enum):
    """Connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class ConnectionType(Enum):
    """Connection types"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    BACKUP = "backup"
    TEST = "test"


@dataclass
class ConnectionMetrics:
    """Connection metrics"""
    connection_time: float = 0.0
    last_activity: float = 0.0
    message_count: int = 0
    error_count: int = 0
    reconnect_count: int = 0
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = float('inf')
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    is_healthy: bool = True
    health_score: float = 1.0


@dataclass
class ConnectionInfo:
    """Connection information"""
    id: str
    client_id: str
    broker: str
    port: int
    connection_type: ConnectionType
    state: ConnectionState = ConnectionState.DISCONNECTED
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    metrics: ConnectionMetrics = field(default_factory=ConnectionMetrics)
    client_ref: Optional[Any] = None
    tags: Set[str] = field(default_factory=set)


class HealthChecker:
    """Connection health checker"""
    
    def __init__(self, check_interval: float = 30.0, timeout: float = 5.0):
        self.check_interval = check_interval
        self.timeout = timeout
        self.logger = logging.getLogger("HealthChecker")
    
    async def check_connection(self, connection_info: ConnectionInfo) -> bool:
        """
        Check connection health
        
        Args:
            connection_info: Connection to check
            
        Returns:
            True if healthy, False otherwise
        """
        try:
            if not connection_info.client_ref:
                return False
            
            # Check if client is connected
            if not hasattr(connection_info.client_ref, 'connection_state'):
                return False
            
            # Simple ping test
            start_time = time.time()
            
            # Try to publish a test message
            test_topic = f"health/check/{connection_info.id}"
            test_payload = f"health_check_{int(time.time())}"
            
            success = connection_info.client_ref.publish(test_topic, test_payload)
            
            if success:
                response_time = time.time() - start_time
                connection_info.metrics.response_times.append(response_time)
                connection_info.metrics.last_activity = time.time()
                connection_info.metrics.is_healthy = True
                connection_info.metrics.health_score = min(1.0, connection_info.metrics.health_score + 0.1)
                return True
            else:
                connection_info.metrics.is_healthy = False
                connection_info.metrics.health_score = max(0.0, connection_info.metrics.health_score - 0.2)
                return False
                
        except Exception as e:
            self.logger.error(f"Health check failed for {connection_info.id}: {e}")
            connection_info.metrics.is_healthy = False
            connection_info.metrics.health_score = max(0.0, connection_info.metrics.health_score - 0.3)
            return False


class LoadBalancer:
    """Connection load balancer"""
    
    def __init__(self, strategy: str = "round_robin"):
        self.strategy = strategy
        self.current_index = 0
        self.logger = logging.getLogger("LoadBalancer")
    
    def select_connection(self, connections: List[ConnectionInfo]) -> Optional[ConnectionInfo]:
        """
        Select connection based on load balancing strategy
        
        Args:
            connections: Available connections
            
        Returns:
            Selected connection or None
        """
        if not connections:
            return None
        
        # Filter healthy connections
        healthy_connections = [conn for conn in connections if conn.metrics.is_healthy]
        
        if not healthy_connections:
            self.logger.warning("No healthy connections available")
            return connections[0] if connections else None
        
        if self.strategy == "round_robin":
            return self._round_robin(healthy_connections)
        elif self.strategy == "least_connections":
            return self._least_connections(healthy_connections)
        elif self.strategy == "health_score":
            return self._health_score(healthy_connections)
        elif self.strategy == "response_time":
            return self._response_time(healthy_connections)
        else:
            return healthy_connections[0]
    
    def _round_robin(self, connections: List[ConnectionInfo]) -> ConnectionInfo:
        """Round robin selection"""
        connection = connections[self.current_index % len(connections)]
        self.current_index += 1
        return connection
    
    def _least_connections(self, connections: List[ConnectionInfo]) -> ConnectionInfo:
        """Select connection with least active connections"""
        return min(connections, key=lambda conn: conn.metrics.message_count)
    
    def _health_score(self, connections: List[ConnectionInfo]) -> ConnectionInfo:
        """Select connection with highest health score"""
        return max(connections, key=lambda conn: conn.metrics.health_score)
    
    def _response_time(self, connections: List[ConnectionInfo]) -> ConnectionInfo:
        """Select connection with lowest average response time"""
        return min(connections, key=lambda conn: conn.metrics.avg_response_time)


class UnifiedConnectionManager:
    """
    Unified MQTT Connection Manager
    
    This class provides comprehensive connection management for MQTT clients
    across different game types and environments.
    """

    def __init__(
        self,
        max_connections: int = 10,
        health_check_interval: float = 30.0,
        load_balance_strategy: str = "round_robin",
        connection_timeout: float = 10.0,
        max_idle_time: float = 300.0
    ):
        """
        Initialize connection manager
        
        Args:
            max_connections: Maximum number of connections
            health_check_interval: Health check interval in seconds
            load_balance_strategy: Load balancing strategy
            connection_timeout: Connection timeout in seconds
            max_idle_time: Maximum idle time before cleanup
        """
        self.max_connections = max_connections
        self.health_check_interval = health_check_interval
        self.connection_timeout = connection_timeout
        self.max_idle_time = max_idle_time
        
        # Connection management
        self.connections: Dict[str, ConnectionInfo] = {}
        self.connection_pools: Dict[str, List[ConnectionInfo]] = defaultdict(list)
        
        # Health monitoring
        self.health_checker = HealthChecker(health_check_interval)
        self.load_balancer = LoadBalancer(load_balance_strategy)
        
        # Monitoring and statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "failed_connections": 0,
            "total_messages": 0,
            "total_errors": 0,
            "avg_response_time": 0.0,
            "uptime": time.time()
        }
        
        # Threading and async support
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.health_check_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Callbacks
        self.connection_callbacks: List[Callable[[ConnectionInfo], None]] = []
        self.error_callbacks: List[Callable[[ConnectionInfo, str], None]] = []
        
        # Logging
        self.logger = logging.getLogger("UnifiedConnectionManager")
        
        # Lock for thread safety
        self.lock = threading.Lock()

    async def start(self):
        """Start connection manager"""
        if self.is_running:
            return
        
        self.is_running = True
        self.logger.info("Starting connection manager")
        
        # Start health checking
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info("Connection manager started")

    async def stop(self):
        """Stop connection manager"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.logger.info("Stopping connection manager")
        
        # Cancel tasks
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Close all connections
        await self._close_all_connections()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        self.logger.info("Connection manager stopped")

    async def create_connection(
        self,
        client_id: str,
        broker: str,
        port: int,
        connection_type: ConnectionType = ConnectionType.PRIMARY,
        tags: Optional[Set[str]] = None,
        client_factory: Optional[Callable] = None
    ) -> Optional[str]:
        """
        Create new connection
        
        Args:
            client_id: Client identifier
            broker: Broker address
            port: Broker port
            connection_type: Type of connection
            tags: Connection tags
            client_factory: Factory function to create client
            
        Returns:
            Connection ID or None if failed
        """
        try:
            # Check connection limit
            if len(self.connections) >= self.max_connections:
                self.logger.warning(f"Connection limit reached ({self.max_connections})")
                return None
            
            # Generate connection ID
            connection_id = f"{client_id}_{broker}_{port}_{int(time.time())}"
            
            # Create connection info
            connection_info = ConnectionInfo(
                id=connection_id,
                client_id=client_id,
                broker=broker,
                port=port,
                connection_type=connection_type,
                tags=tags or set()
            )
            
            # Create client if factory provided
            if client_factory:
                try:
                    client = client_factory(client_id, broker, port)
                    connection_info.client_ref = client
                    connection_info.state = ConnectionState.CONNECTED
                except Exception as e:
                    self.logger.error(f"Failed to create client: {e}")
                    connection_info.state = ConnectionState.FAILED
                    connection_info.metrics.is_healthy = False
            
            # Add to connections
            with self.lock:
                self.connections[connection_id] = connection_info
                self.connection_pools[broker].append(connection_info)
            
            # Update statistics
            self.stats["total_connections"] += 1
            self.stats["active_connections"] += 1
            
            # Notify callbacks
            for callback in self.connection_callbacks:
                try:
                    callback(connection_info)
                except Exception as e:
                    self.logger.error(f"Error in connection callback: {e}")
            
            self.logger.info(f"Created connection {connection_id}")
            return connection_id
            
        except Exception as e:
            self.logger.error(f"Failed to create connection: {e}")
            return None

    async def get_connection(
        self,
        broker: Optional[str] = None,
        connection_type: Optional[ConnectionType] = None,
        tags: Optional[Set[str]] = None
    ) -> Optional[ConnectionInfo]:
        """
        Get connection based on criteria
        
        Args:
            broker: Specific broker
            connection_type: Connection type
            tags: Required tags
            
        Returns:
            Connection info or None
        """
        try:
            with self.lock:
                # Filter connections
                candidates = list(self.connections.values())
                
                if broker:
                    candidates = [conn for conn in candidates if conn.broker == broker]
                
                if connection_type:
                    candidates = [conn for conn in candidates if conn.connection_type == connection_type]
                
                if tags:
                    candidates = [conn for conn in candidates if tags.issubset(conn.tags)]
                
                # Select using load balancer
                selected = self.load_balancer.select_connection(candidates)
                
                if selected:
                    selected.last_used = time.time()
                    selected.metrics.message_count += 1
                    self.stats["total_messages"] += 1
                
                return selected
                
        except Exception as e:
            self.logger.error(f"Error getting connection: {e}")
            return None

    async def remove_connection(self, connection_id: str) -> bool:
        """
        Remove connection
        
        Args:
            connection_id: Connection ID to remove
            
        Returns:
            True if removed successfully
        """
        try:
            with self.lock:
                if connection_id not in self.connections:
                    return False
                
                connection_info = self.connections[connection_id]
                
                # Remove from pools
                if connection_info.broker in self.connection_pools:
                    self.connection_pools[connection_info.broker].remove(connection_info)
                
                # Cleanup client
                if connection_info.client_ref:
                    try:
                        if hasattr(connection_info.client_ref, 'disconnect'):
                            await connection_info.client_ref.disconnect()
                    except Exception as e:
                        self.logger.error(f"Error disconnecting client: {e}")
                
                # Remove from connections
                del self.connections[connection_id]
                
                # Update statistics
                self.stats["active_connections"] -= 1
                
                self.logger.info(f"Removed connection {connection_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error removing connection: {e}")
            return False

    async def _health_check_loop(self):
        """Health check loop"""
        while self.is_running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                # Check all connections
                with self.lock:
                    connections_to_check = list(self.connections.values())
                
                for connection_info in connections_to_check:
                    try:
                        is_healthy = await self.health_checker.check_connection(connection_info)
                        
                        if not is_healthy:
                            self.logger.warning(f"Connection {connection_info.id} is unhealthy")
                            connection_info.state = ConnectionState.FAILED
                            self.stats["failed_connections"] += 1
                            
                            # Notify error callbacks
                            for callback in self.error_callbacks:
                                try:
                                    callback(connection_info, "Health check failed")
                                except Exception as e:
                                    self.logger.error(f"Error in error callback: {e}")
                        
                    except Exception as e:
                        self.logger.error(f"Health check error for {connection_info.id}: {e}")
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")

    async def _cleanup_loop(self):
        """Cleanup loop for idle connections"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = time.time()
                idle_connections = []
                
                with self.lock:
                    for connection_info in self.connections.values():
                        if current_time - connection_info.last_used > self.max_idle_time:
                            idle_connections.append(connection_info.id)
                
                # Remove idle connections
                for connection_id in idle_connections:
                    await self.remove_connection(connection_id)
                    self.logger.info(f"Removed idle connection {connection_id}")
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")

    async def _close_all_connections(self):
        """Close all connections"""
        with self.lock:
            connection_ids = list(self.connections.keys())
        
        for connection_id in connection_ids:
            await self.remove_connection(connection_id)

    def add_connection_callback(self, callback: Callable[[ConnectionInfo], None]):
        """Add connection callback"""
        self.connection_callbacks.append(callback)

    def add_error_callback(self, callback: Callable[[ConnectionInfo, str], None]):
        """Add error callback"""
        self.error_callbacks.append(callback)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        with self.lock:
            healthy_count = sum(1 for conn in self.connections.values() if conn.metrics.is_healthy)
            
            response_times = []
            for conn in self.connections.values():
                response_times.extend(conn.metrics.response_times)
            
            avg_response_time = statistics.mean(response_times) if response_times else 0.0
            
            return {
                "total_connections": len(self.connections),
                "healthy_connections": healthy_count,
                "unhealthy_connections": len(self.connections) - healthy_count,
                "connections_by_broker": {
                    broker: len(connections) 
                    for broker, connections in self.connection_pools.items()
                },
                "connections_by_type": {
                    conn_type.value: sum(1 for conn in self.connections.values() if conn.connection_type == conn_type)
                    for conn_type in ConnectionType
                },
                "avg_response_time": avg_response_time,
                "total_messages": self.stats["total_messages"],
                "total_errors": self.stats["total_errors"],
                "uptime": time.time() - self.stats["uptime"]
            }

    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection information"""
        with self.lock:
            return self.connections.get(connection_id)

    def list_connections(self) -> List[ConnectionInfo]:
        """List all connections"""
        with self.lock:
            return list(self.connections.values())

    def __del__(self):
        """Cleanup on destruction"""
        try:
            if self.is_running:
                asyncio.create_task(self.stop())
        except Exception:
            pass
