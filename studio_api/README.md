# WebSocket Game Status Update System (ws_update_v2.py)

## Overview

`ws_update_v2.py` is a multi-game type WebSocket status update system that supports Sicbo, Speed/VIP Roulette, and Baccarat games. The system automatically detects game types and sends appropriate status fields and error codes.

## Main Features

### 🎮 Supported Game Types

- **Sicbo Game** (SBO-*)
- **Speed/VIP Roulette Game** (ARO-*)
- **Baccarat Game** (BAC-*)

### 📊 Automatic Status Field Selection

Each game type only sends necessary status fields:

#### Sicbo Game
```python
{
    "maintenance": boolean,
    "zCam": string,
    "broker": string,
    "sdp": string,
    "shaker": string,
    "idp": string,
    "nfcScanner": string
}
```

#### Speed/VIP Roulette Game
```python
{
    "maintenance": boolean,
    "zCam": string,
    "sdp": string,
    "roulette": string,
    "nfcScanner": string
}
```

#### Baccarat Game
```python
{
    "maintenance": boolean,
    "zCam": string,
    "sdp": string,
    "idp": string,
    "barcodeScanner": string,
    "nfcScanner": string
}
```

### ⚠️ Game-Specific Error Codes

#### Sicbo Error Codes (AUTO_SICBO_ERRORS)
- `NO SHAKE` - Most frequently occurred event
- `NO STREAM` - Causes IDP cannot detect result
- `INVALID RESULT after reshake` - Invalid result after reshake
- `BROKER DOWN` - Broker down

#### Roulette Error Codes (AUTO_ROULETTE_ERRORS)
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


### Configuration File
Configure in `conf/ws.json`:
```json
{
    "server_url": "ws://your-server:port",
    "device_name": "your-device-name",
    "token": "your-authentication-token"
}
```

## Usage

### 1. Basic Status Update

#### Automatic Game Type Detection
```python
import asyncio
from ws_update_v2 import update_game_status

# Automatically detect Sicbo game
await update_game_status(table_id="SBO-001")

# Automatically detect Roulette game
await update_game_status(table_id="ARO-001")

# Automatically detect Baccarat game
await update_game_status(table_id="BAC-001")
```

#### Custom Status
```python
from ws_update_v2 import create_sicbo_status, update_game_status

# Create custom Sicbo status
custom_status = create_sicbo_status(
    maintenance=True,
    sdp="down",
    idp="error"
)

# Send custom status
await update_game_status(
    custom_status=custom_status,
    table_id="SBO-001"
)
```

### 2. Exception Event Sending

#### Send Game-Specific Error Codes
```python
from ws_update_v2 import send_exception_event

# Sicbo game error
await send_exception_event("NO SHAKE", "SBO-001")

# Roulette game error
await send_exception_event("SENSOR STUCK", "ARO-001")
```

### 3. Manual Status Object Creation

#### Sicbo Status
```python
from ws_update_v2 import create_sicbo_status

status = create_sicbo_status(
    maintenance=False,
    zCam="up",
    broker="up",
    sdp="up",
    shaker="up",
    idp="up",
    nfcScanner="up"
)
```

#### Roulette Status
```python
from ws_update_v2 import create_roulette_status

status = create_roulette_status(
    maintenance=False,
    zCam="up",
    sdp="up",
    roulette="up",
    nfcScanner="up"
)
```

#### Baccarat Status
```python
from ws_update_v2 import create_baccarat_status

status = create_baccarat_status(
    maintenance=False,
    zCam="up",
    sdp="up",
    idp="up",
    barcodeScanner="up",
    nfcScanner="up"
)
```

## Data Format

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

## Running Tests

### Run Complete Test
```bash
cd studio_api
python ws_update_v2.py
```
