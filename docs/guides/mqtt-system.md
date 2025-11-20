# MQTT System Guide

This guide explains the unified MQTT system used in the Studio SDP Roulette System.

## Overview

The system uses a unified MQTT client (`CompleteMQTTSystem`) that provides:

- **Unified Interface**: All game types use the same MQTT client interface
- **Failover Support**: Automatic failover between multiple brokers
- **Connection Pooling**: Efficient connection management
- **Message Processing**: Unified message processing framework
- **Health Monitoring**: Automatic health checks and recovery

## Architecture

### CompleteMQTTSystem

The `CompleteMQTTSystem` integrates all MQTT components:

```python
from mqtt.complete_system import CompleteMQTTSystem, GameType, Environment

# Create system
system = CompleteMQTTSystem(
    game_type=GameType.SICBO,
    environment=Environment.DEVELOPMENT
)

# Initialize
await system.initialize()

# Use system
success, result = await system.detect("round_001")

# Cleanup
await system.cleanup()
```

## Configuration

### Broker Configuration

Configure multiple brokers with priorities:

```json
{
  "brokers": [
    {
      "broker": "192.168.20.9",
      "port": 1883,
      "username": "PFC",
      "password": "wago",
      "priority": 1
    },
    {
      "broker": "192.168.20.10",
      "port": 1883,
      "username": "PFC",
      "password": "wago",
      "priority": 2
    }
  ]
}
```

### Game Configuration

```json
{
  "game_config": {
    "game_type": "sicbo",
    "game_code": "SBO-001",
    "command_topic": "ikg/idp/SBO-001/command",
    "response_topic": "ikg/idp/SBO-001/response",
    "shaker_topic": "ikg/sicbo/Billy-III/listens",
    "timeout": 10,
    "retry_count": 3
  }
}
```

## Usage Examples

### SicBo Game

```python
from mqtt.complete_system import CompleteMQTTSystem, GameType, Environment

# Create SicBo system
system = CompleteMQTTSystem(
    game_type=GameType.SICBO,
    environment=Environment.DEVELOPMENT
)

# Initialize
await system.initialize()

# Send detect command
success, result = await system.detect(
    round_id="round_001",
    input_stream="input_stream",
    output_stream="output_stream"
)

# Cleanup
await system.cleanup()
```

### Baccarat Game

```python
# Create Baccarat system
system = CompleteMQTTSystem(
    game_type=GameType.BACCARAT,
    environment=Environment.PRODUCTION
)

await system.initialize()
success, result = await system.detect("round_001")
await system.cleanup()
```

### Roulette Game

```python
# Create Roulette system
system = CompleteMQTTSystem(
    game_type=GameType.ROULETTE,
    environment=Environment.STAGING
)

await system.initialize()
success, result = await system.detect("round_001")
await system.cleanup()
```

## Features

### 1. Failover Mechanism

The system automatically switches to backup brokers:

```python
# Primary broker fails
# System automatically connects to backup broker
# No manual intervention required
```

### 2. Connection Pooling

Efficient connection management:

```python
# Connections are pooled and reused
# Automatic connection health checks
# Automatic reconnection on failure
```

### 3. Message Processing

Unified message processing:

```python
# Automatic message validation
# Message transformation
# Error handling and retry
```

### 4. Health Monitoring

Automatic health checks:

```python
# Periodic health checks
# Automatic recovery
# Health statistics
```

## Migration from Old System

### Old Implementation

```python
from mqttController import MQTTController

controller = MQTTController("client_id", "broker", 1883)
await controller.initialize()
await controller.send_detect_command(round_id, input_stream, output_stream)
await controller.cleanup()
```

### New Implementation

```python
from mqtt.complete_system import CompleteMQTTSystem, GameType, Environment

system = CompleteMQTTSystem(
    game_type=GameType.SICBO,
    environment=Environment.DEVELOPMENT
)
await system.initialize()
success, result = await system.detect(round_id, input_stream, output_stream)
await system.cleanup()
```

## Advanced Usage

### Custom Message Handlers

```python
def custom_handler(topic, payload, data):
    # Process message
    print(f"Received message on {topic}: {payload}")

system.add_message_handler("custom/topic", custom_handler)
```

### Connection Statistics

```python
# Get connection statistics
stats = system.get_connection_stats()
print(f"Total connections: {stats['total_connections']}")
print(f"Active connections: {stats['active_connections']}")
print(f"Failed connections: {stats['failed_connections']}")
```

### Health Check

```python
# Check system health
health = await system.check_health()
if health["status"] == "healthy":
    print("System is healthy")
else:
    print(f"System issues: {health['issues']}")
```

## Troubleshooting

### Connection Issues

```python
# Check broker connectivity
from mqtt.base_client import test_broker_connection

success = await test_broker_connection("192.168.20.9", 1883)
if not success:
    print("Broker is not reachable")
```

### Message Delivery Issues

```python
# Enable debug logging
import logging
logging.getLogger("mqtt").setLevel(logging.DEBUG)
```

## Best Practices

1. **Use Environment Variables**: Store broker credentials in environment variables
2. **Configure Failover**: Always configure multiple brokers for redundancy
3. **Monitor Health**: Regularly check system health
4. **Handle Errors**: Implement proper error handling
5. **Cleanup Resources**: Always call `cleanup()` when done

## Related Documentation

- [MQTT Migration Guide](../../MQTT_MIGRATION_GUIDE.md)
- [API Reference](../api-reference/mqtt-api.md)
- [Deployment Guide](../deployment/overview.md)

