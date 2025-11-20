# Studio API Reference

Complete Studio API integration documentation for device management, table operations, and WebSocket communication.

## Overview

The Studio API provides a comprehensive interface for managing gaming tables, devices, and real-time status updates. It consists of three main components:

1. **HTTP API** - RESTful endpoints for table and device management
2. **WebSocket API** - Real-time status updates and event notifications
3. **Device Registration API** - Device registration and table assignment

## HTTP API

### Base URL

```
http://100.64.0.160:8085
```

### Authentication

All requests require the `x-signature` header:

```python
headers = {
    "accept": "application/json",
    "x-signature": "secret"
}
```

### Healthcheck

Check API service health status.

```python
from studio_api.api import healthcheck_get_v1

healthcheck_get_v1()
```

**Endpoint**: `GET /v1/service/healthcheck`

### Table Operations

#### Get Table Information

Query table status and information.

```python
from studio_api.api import table_get_v1

# Query multiple tables
table_get_v1(["ARO-001", "ARO-002", "ARO-001-1"])
```

**Endpoint**: `GET /v1/service/table?tableId=ARO-001&tableId=ARO-002`

#### Update Table Status (POST)

Update table status to active.

```python
from studio_api.api import table_post_v1

table_post_v1(table_id="ARO-002-1", table_status="active")
```

**Endpoint**: `POST /v1/service/table`

**Request Body**:
```json
{
    "tableId": "ARO-002-1",
    "tableStatus": "active"
}
```

#### Update Table Status (PATCH)

Update table status to inactive.

```python
from studio_api.api import table_patch_v1

table_patch_v1(table_id="ARO-002-1", table_status="inactive")
```

**Endpoint**: `PATCH /v1/service/table`

**Request Body**:
```json
{
    "tableId": "ARO-002-1",
    "tableStatus": "inactive"
}
```

## Device Registration API

### Register Device

Register a new device with the Studio API.

```python
from studio_api.http.register import device_post_v1

device_post_v1(device_id="ARO-001-1-idp")
```

**Endpoint**: `POST /v1/service/device`

**Request Body**:
```json
{
    "deviceId": "ARO-001-1-idp"
}
```

### Update Device Table Assignment

Assign or update device table assignment.

```python
from studio_api.http.register import device_patch_v1

device_patch_v1(device_id="ARO-001-1-idp", table_id="ARO-001")
```

**Endpoint**: `PATCH /v1/service/device`

**Request Body**:
```json
{
    "deviceId": "ARO-001-1-idp",
    "tableId": "ARO-001"
}
```

### Get Device Information

Query device information.

```python
from studio_api.http.register import device_get_v1

# Get specific device
device_get_v1(device_id="ARO-001-1-idp")

# Get all devices
device_get_v1()
```

**Endpoint**: `GET /v1/service/device?deviceId=ARO-001-1-idp`

## WebSocket API

### Overview

The WebSocket API provides real-time status updates for gaming tables and devices. It supports automatic game type detection and game-specific status fields.

### Supported Game Types

- **Sicbo** (SBO-*)
- **Speed/VIP Roulette** (ARO-*)
- **Baccarat** (BAC-*)

### Configuration

Configure WebSocket connection in `conf/ws.json`:

```json
{
    "server_url": "ws://your-server:port",
    "device_name": "your-device-name",
    "token": "your-authentication-token"
}
```

### Update Game Status

Automatically detect game type and send status update.

```python
from studio_api.ws_update_v2 import update_game_status

# Sicbo game
await update_game_status(table_id="SBO-001")

# Roulette game
await update_game_status(table_id="ARO-001")

# Baccarat game
await update_game_status(table_id="BAC-001")
```

### Custom Status Updates

#### Sicbo Status

```python
from studio_api.ws_update_v2 import create_sicbo_status, update_game_status

status = create_sicbo_status(
    maintenance=False,
    zCam="up",
    broker="up",
    sdp="up",
    shaker="up",
    idp="up",
    nfcScanner="up"
)

await update_game_status(custom_status=status, table_id="SBO-001")
```

#### Roulette Status

```python
from studio_api.ws_update_v2 import create_roulette_status, update_game_status

status = create_roulette_status(
    maintenance=False,
    zCam="up",
    sdp="up",
    roulette="up",
    nfcScanner="up"
)

await update_game_status(custom_status=status, table_id="ARO-001")
```

#### Baccarat Status

```python
from studio_api.ws_update_v2 import create_baccarat_status, update_game_status

status = create_baccarat_status(
    maintenance=False,
    zCam="up",
    sdp="up",
    idp="up",
    barcodeScanner="up",
    nfcScanner="up"
)

await update_game_status(custom_status=status, table_id="BAC-001")
```

### Exception Events

Send game-specific error codes.

```python
from studio_api.ws_update_v2 import send_exception_event

# Sicbo errors
await send_exception_event("NO SHAKE", "SBO-001")
await send_exception_event("NO STREAM", "SBO-001")
await send_exception_event("BROKER DOWN", "SBO-001")

# Roulette errors
await send_exception_event("SENSOR STUCK", "ARO-001")
await send_exception_event("NO BALL DETECT", "ARO-001")
await send_exception_event("LAUNCH FAIL", "ARO-001")
```

### Game-Specific Error Codes

#### Sicbo Error Codes

- `NO SHAKE` - Most frequently occurred event
- `NO STREAM` - Causes IDP cannot detect result
- `INVALID RESULT after reshake` - Invalid result after reshake
- `BROKER DOWN` - Broker down

#### Roulette Error Codes

- `NO BALL DETECT` - No ball detected
- `NO WIN NUM` - No winning number
- `SENSOR STUCK` - Sensor stuck (most frequently occurred event)
- `WRONG BALL DIR` - Wrong ball direction
- `LAUNCH FAIL` - Launch failed
- `NOT REACH POS` - Not reaching position
- `HARDWARE FAULT` - Hardware fault
- `ENCODER FAIL` - Encoder failed
- `BALL DROP FAIL` - Ball drop failed
- `WRONG WHEEL DIR` - Wrong wheel direction
- `STUCK NMB` - Stuck number

## Data Formats

### Service Status Event

```json
{
    "event": "service_status",
    "data": {
        "maintenance": false,
        "zCam": "up",
        "sdp": "up",
        "timestamp": "2025-08-25T06:56:13.574584"
    }
}
```

### Exception Event

```json
{
    "event": "exception",
    "data": "NO SHAKE"
}
```

## Related Documentation

- [WebSocket API Guide](../guides/websocket-api.md)
- [Studio API README](../../studio_api/README.md)
- [Error Signals Documentation](../../studio_api/README_error_signals.md)

