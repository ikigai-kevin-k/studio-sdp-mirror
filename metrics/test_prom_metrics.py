#!/usr/bin/env python3
"""
Test script for sending metrics to Prometheus Pushgateway
Sends test metric "round_duration" to GE server side Prometheus Pushgateway service
"""

import time
import random
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# GE server side Pushgateway URL
PUSHGATEWAY_URL = "http://100.64.0.113:9091"
JOB_NAME = "test_metrics"

def send_round_duration_metric(duration_value: float, instance_label: str = "test-instance"):
    """
    Send round_duration metric to Pushgateway
    
    Args:
        duration_value: The duration value in seconds
        instance_label: Instance label for the metric
    """
    # Create a registry for this push
    registry = CollectorRegistry()
    
    # Create the round_duration metric as a Gauge
    # Gauge is appropriate for values that can go up or down
    round_duration = Gauge(
        'round_duration',
        'Round duration in seconds',
        ['instance'],
        registry=registry
    )
    
    # Set the metric value with instance label
    round_duration.labels(instance=instance_label).set(duration_value)
    
    # Push metrics to Pushgateway
    try:
        push_to_gateway(
            gateway=PUSHGATEWAY_URL,
            job=JOB_NAME,
            registry=registry
        )
        print(f"✓ Successfully pushed round_duration={duration_value}s (instance={instance_label})")
        return True
    except Exception as e:
        print(f"✗ Failed to push metric: {e}")
        return False

def main():
    """Main function - sends test metrics periodically"""
    print(f"Starting Prometheus metrics test")
    print(f"Pushgateway URL: {PUSHGATEWAY_URL}")
    print(f"Job name: {JOB_NAME}")
    print(f"Metric: round_duration")
    print("-" * 60)
    
    # Send a few test metrics
    test_values = [
        (1.5, "test-instance-1"),
        (2.3, "test-instance-2"),
        (0.8, "test-instance-1"),
        (3.1, "test-instance-2"),
    ]
    
    print("\nSending test metrics...")
    for value, instance in test_values:
        send_round_duration_metric(value, instance)
        time.sleep(1)  # Small delay between pushes
    
    print("\n" + "-" * 60)
    print("Test metrics sent successfully!")
    print(f"\nYou can verify the metrics at:")
    print(f"  - Pushgateway: {PUSHGATEWAY_URL}")
    print(f"  - Prometheus: http://100.64.0.113:9090")
    print(f"\nQuery example in Prometheus:")
    print(f'  round_duration{{job="{JOB_NAME}"}}')

if __name__ == "__main__":
    main()
