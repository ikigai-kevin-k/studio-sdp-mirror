# API Reference Overview

This section provides complete API documentation for the Studio SDP System.

## API Categories

- **[MQTT API](mqtt-api.md)** - MQTT communication API
- **[Serial API](serial-api.md)** - RS232 serial communication API
- **[WebSocket API](websocket-api.md)** - WebSocket real-time communication API
- **[Studio API](studio-api.md)** - Studio API for device and table management
- **[Table API](table-api.md)** - Live Backend Service API integration

## Quick Reference

### MQTT API

```python
from mqtt.complete_system import CompleteMQTTSystem

system = CompleteMQTTSystem(game_type=GameType.SICBO)
await system.initialize()
```

### Serial API

```python
import serial

ser = serial.Serial(port="/dev/ttyUSB0", baudrate=9600)
```

### WebSocket API

```python
from studio_api.ws_update_v2 import update_game_status

await update_game_status(table_id="SBO-001")
```

### Studio API

```python
from studio_api.api import table_get_v1, table_post_v1
from studio_api.ws_update_v2 import update_game_status

# Get table information
table_get_v1(["ARO-001", "ARO-002"])

# Update table status
table_post_v1("ARO-001", "active")

# Send WebSocket status update
await update_game_status(table_id="SBO-001")
```

### Table API

```python
from table_api.sb.api_v2_sb import start_post_v2, deal_post_v2

# Start new round
round_id, bet_period = await start_post_v2(url, token)

# Submit game result
await deal_post_v2(url, token, round_id, result)
```

## Related Documentation

- [Guides](../guides/architecture.md)
- [Getting Started](../getting-started/installation.md)

