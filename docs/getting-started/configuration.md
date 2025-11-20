# Configuration Guide

This guide explains how to configure the Studio SDP Roulette System for different environments and use cases.

## Configuration Files

Configuration files are located in the `conf/` directory:

- `roulette_machine_speed.json` - Speed roulette configuration
- `roulette_machine_vip.json` - VIP roulette configuration
- `table-config-sicbo-v2.json` - SicBo game configuration
- `table-config-baccarat-v2.json` - Baccarat game configuration
- `ws.json` - WebSocket configuration

## Environment Variables

Create a `.env` file in the project root for environment-specific settings:

```bash
# MQTT Configuration
MQTT_BROKER=192.168.88.54
MQTT_PORT=1883
MQTT_USERNAME=PFC
MQTT_PASSWORD=wago

# LOS API Configuration
LOS_API_URL=https://los-api-uat.sdp.com.tw/api/v2/sdp/config
LOS_API_TOKEN=YOUR_TOKEN

# WebSocket Configuration
WS_SERVER_URL=ws://your-server:port
WS_DEVICE_NAME=your-device-name
WS_TOKEN=your-authentication-token

# Slack Configuration (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_USER_TOKEN=xoxp-your-user-token

# Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=./logs
```

## Game-Specific Configuration

### Roulette Configuration

#### Speed Roulette (`roulette_machine_speed.json`)

```json
{
  "room_id": "ARO-001",
  "serial_port": "/dev/ttyUSB0",
  "baud_rate": 9600,
  "timeout": 1.0,
  "game_type": "roulette_speed"
}
```

#### VIP Roulette (`roulette_machine_vip.json`)

```json
{
  "room_id": "ARO-002",
  "serial_port": "/dev/ttyUSB0",
  "baud_rate": 9600,
  "timeout": 1.0,
  "game_type": "roulette_vip"
}
```

### SicBo Configuration (`table-config-sicbo-v2.json`)

```json
{
  "room_id": "SBO-001",
  "broker_host": "192.168.88.54",
  "broker_port": 1883,
  "game_type": "sicbo",
  "idp_timeout": 10,
  "retry_count": 3
}
```

### Baccarat Configuration (`table-config-baccarat-v2.json`)

```json
{
  "room_id": "BAC-001",
  "game_type": "baccarat",
  "barcode_scanner": "/dev/hidraw0",
  "idp_enabled": false
}
```

## MQTT Configuration

### Broker Configuration

The system supports multiple MQTT brokers with failover:

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

### Game-Specific Topics

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

## WebSocket Configuration

Configure WebSocket connection in `conf/ws.json`:

```json
{
  "server_url": "ws://your-server:port",
  "device_name": "your-device-name",
  "token": "your-authentication-token"
}
```

## Serial Port Configuration

### Roulette Serial Settings

```python
{
  "port": "/dev/ttyUSB0",
  "baudrate": 9600,
  "bytesize": 8,
  "parity": "N",
  "stopbits": 1,
  "timeout": 1.0,
  "rtscts": true
}
```

## Logging Configuration

### Log Levels

- `DEBUG` - Detailed debug information
- `INFO` - General informational messages
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical error messages

### Log Directory Structure

```
logs/
├── sicbo/
│   ├── sicbo_2025-11-20.log
│   └── sicbo_errors_2025-11-20.log
├── speed/
│   ├── speed_2025-11-20.log
│   └── speed_errors_2025-11-20.log
└── vip/
    ├── vip_2025-11-20.log
    └── vip_errors_2025-11-20.log
```

## Environment-Specific Configuration

### Development Environment

```bash
# .env.development
LOS_API_URL=https://los-api-dev.sdp.com.tw/api/v2/sdp/config
LOG_LEVEL=DEBUG
```

### Staging Environment

```bash
# .env.staging
LOS_API_URL=https://los-api-uat.sdp.com.tw/api/v2/sdp/config
LOG_LEVEL=INFO
```

### Production Environment

```bash
# .env.production
LOS_API_URL=https://los-api-prd.sdp.com.tw/api/v2/sdp/config
LOG_LEVEL=WARNING
```

## Configuration Loading

The system loads configuration in the following order:

1. Environment variables (`.env` file)
2. Command-line arguments
3. Configuration files (`conf/` directory)
4. Default values

### Example: Loading Configuration

```python
from utils import load_config

# Load configuration from file
config = load_config("table-config-sicbo-v2.json")

# Override with environment variables
import os
config["broker_host"] = os.getenv("MQTT_BROKER", config["broker_host"])
```

## Command-Line Configuration Override

You can override configuration via command-line arguments:

```bash
# Override MQTT broker
sdp-sicbo --broker 192.168.88.54 --port 1883

# Override LOS API URL
sdp-sicbo --get-url https://los-api-prd.sdp.com.tw/api/v2/sdp/config --token YOUR_TOKEN

# Override log directory
sdp-sicbo --log-dir /var/log/sdp
```

## Validation

The system validates configuration on startup:

- Required fields are present
- Data types are correct
- Values are within acceptable ranges
- Network endpoints are reachable

### Configuration Validation Example

```python
def validate_config(config):
    required_fields = ["room_id", "game_type"]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    if config["game_type"] not in ["sicbo", "roulette_speed", "roulette_vip", "baccarat"]:
        raise ValueError(f"Invalid game type: {config['game_type']}")
```

## Troubleshooting

### Common Configuration Issues

#### Missing Configuration File

```bash
# Error: FileNotFoundError: conf/table-config-sicbo-v2.json
# Solution: Ensure configuration file exists
ls -la conf/table-config-sicbo-v2.json
```

#### Invalid JSON Format

```bash
# Error: JSONDecodeError
# Solution: Validate JSON syntax
python -m json.tool conf/table-config-sicbo-v2.json
```

#### Environment Variable Not Loaded

```bash
# Error: Configuration value not found
# Solution: Check .env file exists and is loaded
source .env
echo $MQTT_BROKER
```

## Best Practices

1. **Use Environment Variables**: Store sensitive information in `.env` files
2. **Version Control**: Keep configuration templates in version control, but not secrets
3. **Validation**: Always validate configuration on startup
4. **Documentation**: Document all configuration options
5. **Defaults**: Provide sensible defaults for all configuration options

## Related Documentation

- [Installation Guide](installation.md)
- [Quick Start Guide](quick-start.md)
- [Deployment Guide](../deployment/overview.md)

