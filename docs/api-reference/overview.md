# API Reference Overview

This section provides complete API documentation for the Studio SDP System.

## API Categories

- **[MQTT API](mqtt-api.md)** - MQTT communication API
- **[Serial API](serial-api.md)** - RS232 serial communication API
- **[WebSocket API](websocket-api.md)** - WebSocket real-time communication API
- **[Table API](table-api.md)** - LOS API integration

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

### Table API

```python
from table_api import start_post, deal_post

await start_post(round_id, config)
await deal_post(round_id, result, config)
```

## Related Documentation

- [Guides](../guides/architecture.md)
- [Getting Started](../getting-started/installation.md)

