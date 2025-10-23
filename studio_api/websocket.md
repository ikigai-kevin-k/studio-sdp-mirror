# WebSocket Implementation for Studio SDP Roulette System

This document describes the usage of the WebSocket implementation for the Studio SDP system, including the server, client, and test files.

## Overview

The WebSocket system consists of three main components:
- `studio_api/ws.py` - WebSocket server for receiving table/device status updates
- `ws_client.py` - WebSocket client for sending status updates
- `tests/test_ws.py` - Unit tests for the WebSocket functionality

## Files Description

### 1. `studio_api/ws.py` - WebSocket Server

**Purpose**: Receives and processes table/device status updates from clients

**Key Features**:
- Client authentication via user ID and token
- Status management for multiple tables
- Support for service and device status updates
- Automatic status initialization for new tables

**Supported Status Types**:
- **Service Status**: SDP, IDP (up, down, standby, calibration, exception)
- **Device Status**: Roulette, Shaker, Broker, ZCam, Barcode Scanner, NFC Scanner (up, down)

### 2. `ws_client.py` - WebSocket Client

**Purpose**: Sends status updates to the WebSocket server

**Key Features**:
- Automatic connection and authentication
- Support for individual and batch status updates
- Interactive mode for manual testing
- Demo mode for automated testing

**Modes**:
- **Demo Mode**: Automatically sends various status updates
- **Interactive Mode**: Manual command input for status updates

### 3. `tests/test_ws.py` - Unit Tests

**Purpose**: Validates the WebSocket server functionality

**Test Coverage**:
- Enumeration value validation
- Status class creation and conversion
- Server initialization and configuration
- Query parameter parsing
- Connection handling and authentication
- Status update processing
- Error handling

## Usage

### Starting the WebSocket Server

#### Method 1: Direct execution
```bash
python studio_api/ws.py
```

#### Method 2: Custom port (to avoid conflicts)
```bash
python -c "
from studio_api.ws import StudioWebSocketServer
import asyncio
server = StudioWebSocketServer(port=8081)
asyncio.run(server.start())
"
```

**Default Configuration**:
- Host: localhost
- Port: 8080
- Authentication: Required (user ID + token)

### Running the WebSocket Client

#### Demo Mode (Automated)
```bash
python ws_client.py
```

**Demo Actions**:
1. Service status updates (SDP, IDP)
2. Device status updates (Roulette, Shaker, Broker)
3. Multiple simultaneous updates
4. Maintenance mode toggle
5. Calibration status

#### Interactive Mode (Manual)
```bash
python ws_client.py --interactive
```

**Status Values**:
- **Service Status**: `up`, `down`, `standby`, `calibration`, `exception`
- **Device Status**: `up`, `down`

### Running Tests

#### All Tests
```bash
pytest tests/test_ws.py -v
```

#### Specific Test Classes
```bash
# Test server functionality
pytest tests/test_ws.py::TestStudioWebSocketServer -v

# Test integration
pytest tests/test_ws.py::TestWebSocketIntegration -v
```

#### Specific Test Methods
```bash
# Test server initialization
pytest tests/test_ws.py::TestStudioWebSocketServer::test_server_initialization -v

# Test status updates
pytest tests/test_ws.py::TestStudioWebSocketServer::test_handle_status_update_service_status -v
```

## Message Format

### Client to Server

#### Service Status Update
```json
{
  "sdp": "up"
}
```

#### Device Status Update
```json
{
  "roulette": "up"
}
```

#### Multiple Updates
```json
{
  "sdp": "up",
  "roulette": "down",
  "shaker": "up"
}
```

#### Custom Updates
```json
{
  "maintenance": true,
  "custom_field": "custom_value"
}
```

### Server to Client

#### Initial Status
```json
{
  "TABLE_ID": "ARO-001",
  "UPTIME": 0,
  "TIMESTAMP": "2024-01-01T12:00:00",
  "MAINTENANCE": false,
  "SDP": "standby",
  "IDP": "standby",
  "BROKER": "down",
  "ZCam": "down",
  "ROULETTE": "down",
  "SHAKER": "down",
  "BARCODE_SCANNER": "down",
  "NFC_SCANNER": "down"
}
```

#### Confirmation Response
```json
{
  "status": "updated",
  "table_id": "ARO-001"
}
```

#### Error Response
```json
{
  "error": "Invalid JSON format"
}
```

## Configuration

### Server Configuration
```python
# Default configuration
server = StudioWebSocketServer()

# Custom configuration
server = StudioWebSocketServer(
    host='0.0.0.0',  # Listen on all interfaces
    port=8081        # Custom port
)
```

### Client Configuration
```python
# Default configuration
client = StudioWebSocketClient(
    server_url="ws://localhost:8080",
    table_id="ARO-001",
    device_name="dealerPC",
    token="MY_TOKEN"
)
```
