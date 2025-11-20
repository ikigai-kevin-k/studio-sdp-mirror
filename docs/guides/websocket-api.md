# WebSocket API Guide

This guide explains the WebSocket API for real-time communication.

## Overview

The system uses WebSocket for real-time communication with the Studio API.

## Configuration

Configure in `conf/ws.json`:

```json
{
  "server_url": "ws://your-server:port",
  "device_name": "your-device-name",
  "token": "your-authentication-token"
}
```

## Usage

### Update Game Status

```python
from studio_api.ws_update_v2 import update_game_status

# Automatically detect game type
await update_game_status(table_id="SBO-001")
```

### Send Exception Event

```python
from studio_api.ws_update_v2 import send_exception_event

# Send game-specific error
await send_exception_event("NO SHAKE", "SBO-001")
```

## Related Documentation

- [API Reference](../api-reference/websocket-api.md)
- [Studio API README](../../studio_api/README.md)

