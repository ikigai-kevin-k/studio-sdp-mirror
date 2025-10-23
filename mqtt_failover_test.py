#!/usr/bin/env python3
"""
MQTT Failover Test
This test demonstrates how to use the MQTT failover mechanism
with broker configuration files.
"""

import json
import logging
import sys
import time
import threading
from mqtt.mqtt_wrapper import MQTTLogger
from proto.mqtt import MQTTConnector, load_broker_config


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_with_mqtt_wrapper(game_type_param="baccarat"):
    """Test using MQTTLogger with failover"""
    print(f"=== MQTT Wrapper Failover Test - {game_type_param.upper()} ===")

    # Load broker configuration based on game type
    config_file = f"conf/{game_type_param}-broker.json"
    config = load_broker_config(config_file)
    if not config:
        print("Failed to load broker configuration")
        return

    broker_list = config.get("brokers", [])
    if not broker_list:
        print("No brokers found in configuration")
        return

    # Create MQTT client with failover
    client_id = "test_client_001"
    mqtt_client = MQTTLogger(
        client_id=client_id,
        broker=broker_list[0]["broker"],
        port=broker_list[0]["port"],
        broker_list=broker_list
    )

    # Connect with failover
    if mqtt_client.connect_with_failover():
        print(
            f"Successfully connected to broker: "
            f"{mqtt_client.broker}:{mqtt_client.port}"
        )

        # Subscribe to topics
        game_config = config.get("game_config", {})
        command_topic = game_config.get("command_topic", "test/command")
        response_topic = game_config.get("response_topic", "test/response")

        mqtt_client.subscribe(command_topic)
        mqtt_client.subscribe(response_topic)

        print(f"Subscribed to topics: {command_topic}, {response_topic}")

        # Test publishing
        test_message = {
            "test": "message",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        mqtt_client.publish(response_topic, json.dumps(test_message))
        print(f"Published test message to {response_topic}")

        # Cleanup
        mqtt_client.stop_loop()
        mqtt_client.disconnect()
        print("Disconnected from MQTT broker")
    else:
        print("Failed to connect to any broker")


def test_connection_monitoring(game_type_param="baccarat"):
    """Test demonstrating connection monitoring and failover"""
    title = (f"=== Connection Monitoring & Failover Test - "
             f"{game_type_param.upper()} ===")
    print(title)

    # Load broker configuration based on game type
    config_file = f"conf/{game_type_param}-broker.json"
    config = load_broker_config(config_file)
    if not config:
        print("Failed to load broker configuration")
        return

    broker_list = config.get("brokers", [])
    if not broker_list:
        print("No brokers found in configuration")
        return

    # Create MQTT client with failover
    client_id = "monitor_client_001"
    mqtt_client = MQTTLogger(
        client_id=client_id,
        broker=broker_list[0]["broker"],
        port=broker_list[0]["port"],
        broker_list=broker_list
    )

    # Connect to first broker
    if mqtt_client.connect_with_failover():
        broker_info = f"{mqtt_client.broker}:{mqtt_client.port}"
        print(f"✓ Connected to primary broker: {broker_info}")

        # Subscribe to topics
        game_config = config.get("game_config", {})
        command_topic = game_config.get("command_topic", "test/command")
        response_topic = game_config.get("response_topic", "test/response")

        mqtt_client.subscribe(command_topic)
        mqtt_client.subscribe(response_topic)
        print(f"✓ Subscribed to topics: {command_topic}, {response_topic}")

        # Start monitoring connection status
        def monitor_connection():
            """Monitor connection and handle failover"""
            last_connected = True
            while True:
                time.sleep(2)  # Check every 2 seconds

                if not mqtt_client.connected and last_connected:
                    print("⚠️  Connection lost! Attempting failover...")
                    mqtt_client.logger.info(
                        "[FAILOVER] Connection lost, attempting reconnection"
                    )

                    # Try to reconnect with failover
                    if mqtt_client.reconnect_with_failover():
                        broker_host = mqtt_client.broker
                        broker_port = mqtt_client.port
                        print(f"✓ Reconnected to broker: "
                              f"{broker_host}:{broker_port}")
                        # Re-subscribe to topics
                        mqtt_client.subscribe(command_topic)
                        mqtt_client.subscribe(response_topic)
                        print(f"✓ Re-subscribed to topics: "
                              f"{command_topic}, {response_topic}")
                    else:
                        print("✗ Failed to reconnect to any broker")
                        break

                elif mqtt_client.connected and not last_connected:
                    broker_info = f"{mqtt_client.broker}:{mqtt_client.port}"
                    print(f"✓ Connection restored to: {broker_info}")

                last_connected = mqtt_client.connected

        # Start monitoring in background thread
        monitor_thread = threading.Thread(
            target=monitor_connection, daemon=True
        )
        monitor_thread.start()

        # Connection monitoring is now active
        print("\n--- Connection monitoring & failover test ---")
        print("Connection monitoring is active. The system will automatically")
        print("detect disconnections and attempt failover to backup brokers.")
        print("You can manually disconnect the broker to test failover.")

        # Test publishing after potential failover
        print("\n--- Testing after failover ---")
        print("Testing message publishing to verify connection status...")
        # Send a test message to verify connection
        test_message = {
            "test": "failover_verification",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "broker": f"{mqtt_client.broker}:{mqtt_client.port}",
            "status": "post_failover_test"
        }
        mqtt_client.publish(response_topic, json.dumps(test_message))
        print(f"📤 Published failover verification message to {response_topic}")
        print(f"Current broker: {mqtt_client.broker}:{mqtt_client.port}")

        # Cleanup
        print("\n--- Cleanup ---")
        mqtt_client.stop_loop()
        mqtt_client.disconnect()
        print("✓ Disconnected from MQTT broker")

    else:
        print("✗ Failed to connect to any broker")


def test_with_mqtt_connector():
    """Test using MQTTConnector with failover"""
    print("\n=== MQTT Connector Failover Test ===")

    # Load broker configuration
    config = load_broker_config("conf/sicbo-broker.json")
    if not config:
        print("Failed to load broker configuration")
        return

    broker_list = config.get("brokers", [])
    if not broker_list:
        print("No brokers found in configuration")
        return

    # Create MQTT connector with failover
    client_id = "test_connector_001"
    MQTTConnector(
        client_id=client_id,
        broker=broker_list[0]["broker"],
        port=broker_list[0]["port"],
        broker_list=broker_list
    )

    print("Created MQTT connector with failover support")
    print(f"Available brokers: {[b['broker'] for b in broker_list]}")


if __name__ == "__main__":
    print("MQTT Failover Mechanism Demo")
    print("=" * 50)

    # Get game type from command line argument or use default
    game_type = sys.argv[1] if len(sys.argv) > 1 else "baccarat"

    # Check for monitoring mode argument
    monitor_mode = len(sys.argv) > 2 and sys.argv[2] == "monitor"

    # Only test the specified game type
    if game_type in ["baccarat", "sicbo"]:
        print(f"Testing {game_type} broker failover mechanism...")

        if monitor_mode:
            print("Running in connection monitoring mode...")
            test_connection_monitoring(game_type)
        else:
            print("Running basic failover test...")
            test_with_mqtt_wrapper(game_type)
    else:
        print(f"Invalid game type: {game_type}")
        print("Valid options: baccarat, sicbo")
        print("Usage: python mqtt_failover_test.py [game_type] [monitor]")
        print("Test: python mqtt_failover_test.py baccarat monitor")
        sys.exit(1)

    print("\nDemo completed!")
