# MQTT Failover Mechanism Documentation

## Overview

This project has implemented an MQTT broker failover mechanism. When the primary broker loses connection, the system automatically attempts to connect to a backup broker. This mechanism is based on the `connect_with_failover` method from `studio-idp-gitactions`.

## New Features

### 1. Broker Configuration Files

- `conf/baccarat-broker.json` - Broker configuration for Baccarat game
- `conf/sicbo-broker.json` - Broker configuration for Sicbo game

Each configuration file contains:
- `brokers`: List of brokers, sorted by priority
- `game_config`: Game-related configuration (topics, etc.)

### 2. Modified Files

#### `mqtt_wrapper.py`
- Added `broker_list` parameter to support multiple brokers
- Added `connect_with_failover()` method
- Added `reconnect_with_failover()` method
- Added `set_broker_list()` and `get_current_broker()` helper methods

#### `proto/mqtt.py`
- Added `load_broker_config()` function to load configuration files
- Modified `MQTTLogger` class to support failover
- Modified `MQTTConnector` class to support failover
- Uses `connect_with_failover()` in the `initialize()` method

## Usage

### Basic Usage

```python
from mqtt_wrapper import MQTTLogger
from proto.mqtt import load_broker_config

# Load broker configuration
config = load_broker_config("conf/baccarat-broker.json")
broker_list = config.get("brokers", [])

# Create MQTT client
mqtt_client = MQTTLogger(
    client_id="my_client",
    broker=broker_list[0]["broker"],
    port=broker_list[0]["port"],
    broker_list=broker_list
)

# Connect with failover
if mqtt_client.connect_with_failover():
    print("Successfully connected to broker")
    # Perform MQTT operations...
else:
    print("Failed to connect to any broker")
```

### Using MQTTConnector

```python
from proto.mqtt import MQTTConnector, load_broker_config

# Load configuration
config = load_broker_config("conf/sicbo-broker.json")
broker_list = config.get("brokers", [])

# Create connector
connector = MQTTConnector(
    client_id="my_connector",
    broker=broker_list[0]["broker"],
    port=broker_list[0]["port"],
    broker_list=broker_list
)

# Initialize (automatically uses failover)
await connector.initialize()
```

## Configuration File Format

```json
{
    "brokers": [
        {
            "broker": "192.168.20.10",
            "port": 1883,
            "username": "PFC",
            "password": "wago",
            "priority": 1
        },
        {
            "broker": "192.168.20.9",
            "port": 1883,
            "username": "PFC",
            "password": "wago",
            "priority": 2
        }
    ],
    "game_config": {
        "game_type": "baccarat",
        "game_code": "BAC-001",
        "command_topic": "ikg/idp/BAC-001/command",
        "response_topic": "ikg/idp/BAC-001/response"
    }
}
```

## Failover Mechanism

1. **Connection Order**: Attempts to connect in the order specified in the `brokers` array
2. **Automatic Reconnection**: When connection is lost, automatically attempts to reconnect to the next available broker
3. **Error Handling**: Logs the reason for each broker connection failure
4. **State Tracking**: Tracks the index of the currently connected broker

## Backward Compatibility

- The original `connect()` method is still available
- If `broker_list` parameter is not provided, single broker mode is used
- All existing functionality remains unchanged

## Example Program

Run `mqtt_failover_example.py` to see a complete usage example:

```bash
# Test baccarat broker failover (default)
python mqtt_failover_example.py

# Test specific game type
python mqtt_failover_example.py baccarat
python mqtt_failover_example.py sicbo
```

## Important Notes

1. Ensure all broker authentication information is correct
2. Good network connectivity
3. Proper error handling and logging
4. Verify failover mechanism in test environment

## Log Output

The failover process generates detailed logs:

```
[FAILOVER] Trying broker 1/2: 192.168.20.10:1883
[FAILOVER] Successfully connected to 192.168.20.10:1883
```

Or

```
[FAILOVER] Trying broker 1/2: 192.168.20.10:1883
[FAILOVER] Failed to connect to 192.168.20.10:1883 - Connection refused
[FAILOVER] Trying broker 2/2: 192.168.20.9:1883
[FAILOVER] Successfully connected to 192.168.20.9:1883
```
