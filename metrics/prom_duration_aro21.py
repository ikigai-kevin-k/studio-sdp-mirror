#!/usr/bin/env python3
"""
Script for continuously monitoring time interval metrics from log file and sending to Prometheus Pushgateway
Continuously watches time_intervals-2api.log for new metrics and pushes to GE server side Prometheus Pushgateway service
Reads finish_to_start_time, start_to_launch_time, launch_to_deal_time, deal_to_finish_time
Calculates game_duration_aro21 as the sum of all four time intervals
Specifically for ARO-002-1 (ARO21) instance
"""

import re
import os
import json
import time
import signal
import sys
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# GE server side Pushgateway URL
PUSHGATEWAY_URL = "http://100.64.0.113:9091"
JOB_NAME = "time_intervals_metrics"

# Log file path (same as main_vip.py uses)
LOG_FILE = "time_intervals-2api.log"

# Instance label for ARO-002-1
INSTANCE_LABEL = "aro21"

# Alternative paths to try
POSSIBLE_LOG_PATHS = [
    LOG_FILE,
    os.path.join(os.path.dirname(__file__), "..", LOG_FILE),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), LOG_FILE),
    f"/home/rnd/studio-sdp-roulette/{LOG_FILE}"
]

# State file to track last pushed metrics
STATE_FILE = os.path.join(os.path.dirname(__file__), ".last_metrics_aro21.json")

# State file to track last read position in log file
POSITION_FILE = os.path.join(os.path.dirname(__file__), ".last_position_aro21.json")

# Monitoring interval in seconds
MONITOR_INTERVAL = 1.0  # Check every 1 second

# Global flag for graceful shutdown
running = True


def find_log_file():
    """
    Find the log file from possible paths
    
    Returns:
        str: Path to the log file, or None if not found
    """
    for path in POSSIBLE_LOG_PATHS:
        if os.path.exists(path):
            return path
    return None


def load_last_position():
    """
    Load last read position from state file
    
    Returns:
        int: Last read position (byte offset), or 0 if file doesn't exist
    """
    if not os.path.exists(POSITION_FILE):
        return 0
    
    try:
        with open(POSITION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('position', 0)
    except Exception:
        return 0


def save_last_position(position: int):
    """
    Save last read position to state file
    
    Args:
        position: Byte position in the log file
    """
    try:
        with open(POSITION_FILE, 'w', encoding='utf-8') as f:
            json.dump({'position': position}, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save position file: {e}")


def parse_metrics_from_block(block: str):
    """
    Parse metrics from a single block
    
    Args:
        block: Text block containing metrics
        
    Returns:
        dict: Dictionary containing the four metrics plus game_duration_aro21, or None if parsing failed
    """
    metrics = {}
    
    # Pattern to match: "metric_name: value"
    pattern = r'(finish_to_start_time|start_to_launch_time|launch_to_deal_time|deal_to_finish_time):\s*([\d.]+)'
    matches = re.findall(pattern, block)
    
    # Build metrics dictionary
    for metric_name, value_str in matches:
        try:
            metrics[metric_name] = float(value_str)
        except ValueError:
            continue
    
    # Check if we have all four metrics
    required_metrics = [
        'finish_to_start_time',
        'start_to_launch_time',
        'launch_to_deal_time',
        'deal_to_finish_time'
    ]
    
    if all(metric in metrics for metric in required_metrics):
        # Calculate total game duration (sum of all four time intervals)
        metrics['game_duration_aro21'] = (
            metrics['finish_to_start_time'] +
            metrics['start_to_launch_time'] +
            metrics['launch_to_deal_time'] +
            metrics['deal_to_finish_time']
        )
        return metrics
    
    return None


def read_new_metrics(log_file_path: str):
    """
    Read new metrics from log file since last read position
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        list: List of metrics dictionaries found in new content, or empty list
    """
    try:
        # Get current file size
        current_size = os.path.getsize(log_file_path)
        last_position = load_last_position()
        
        # If file was truncated or is smaller, reset position
        if current_size < last_position:
            print("⚠ Log file appears to have been rotated or truncated, resetting position")
            last_position = 0
        
        # If no new content, return empty list
        if current_size <= last_position:
            return []
        
        # Read new content
        with open(log_file_path, 'r', encoding='utf-8') as f:
            # Seek to last position
            f.seek(last_position)
            new_content = f.read()
            
        # Update position
        save_last_position(current_size)
        
        # If no new content, return empty list
        if not new_content.strip():
            return []
        
        # Parse blocks from new content
        blocks = new_content.split('--------------------------------------------------')
        
        metrics_list = []
        for block in blocks:
            if not block.strip():
                continue
            
            metrics = parse_metrics_from_block(block)
            if metrics:
                metrics_list.append(metrics)
        
        return metrics_list
        
    except Exception as e:
        print(f"✗ Error reading log file: {e}")
        return []


def load_last_metrics():
    """
    Load last pushed metrics from state file
    
    Returns:
        dict: Last pushed metrics, or None if file doesn't exist
    """
    if not os.path.exists(STATE_FILE):
        return None
    
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def save_last_metrics(metrics: dict):
    """
    Save last pushed metrics to state file
    
    Args:
        metrics: Dictionary containing the metrics to save
    """
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save state file: {e}")


def metrics_are_equal(metrics1: dict, metrics2: dict):
    """
    Compare two metrics dictionaries for equality
    
    Args:
        metrics1: First metrics dictionary
        metrics2: Second metrics dictionary
        
    Returns:
        bool: True if all metrics are equal, False otherwise
    """
    required_metrics = [
        'finish_to_start_time',
        'start_to_launch_time',
        'launch_to_deal_time',
        'deal_to_finish_time',
        'game_duration_aro21'
    ]
    
    for metric in required_metrics:
        if metric not in metrics1 or metric not in metrics2:
            return False
        # Compare with small tolerance for floating point comparison
        if abs(metrics1[metric] - metrics2[metric]) > 0.0001:
            return False
    
    return True


def send_metrics_to_prometheus(metrics: dict, instance_label: str = INSTANCE_LABEL):
    """
    Send time interval metrics to Pushgateway
    Only pushes if metrics have changed since last push
    
    Args:
        metrics: Dictionary containing the four metrics plus game_duration_aro21
        instance_label: Instance label for the metrics (default: aro21)
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Create a registry for this push
    registry = CollectorRegistry()
    
    # Create Gauge metrics for each time interval
    # Gauge is appropriate for values that can go up or down
    finish_to_start = Gauge(
        'finish_to_start_time',
        'Time from finish to start in seconds',
        ['instance'],
        registry=registry
    )
    
    start_to_launch = Gauge(
        'start_to_launch_time',
        'Time from start to launch in seconds',
        ['instance'],
        registry=registry
    )
    
    launch_to_deal = Gauge(
        'launch_to_deal_time',
        'Time from launch to deal in seconds',
        ['instance'],
        registry=registry
    )
    
    deal_to_finish = Gauge(
        'deal_to_finish_time',
        'Time from deal to finish in seconds',
        ['instance'],
        registry=registry
    )
    
    # Create Gauge metric for total game duration
    game_duration = Gauge(
        'game_duration_aro21',
        'Total game duration (sum of all four time intervals) in seconds',
        ['instance'],
        registry=registry
    )
    
    # Check if metrics are the same as last push
    last_metrics = load_last_metrics()
    if last_metrics and metrics_are_equal(metrics, last_metrics):
        print("ℹ Metrics are identical to last push, skipping...")
        print("  No need to push the same metrics again")
        return True
    
    # Set the metric values with instance label
    finish_to_start.labels(instance=instance_label).set(metrics['finish_to_start_time'])
    start_to_launch.labels(instance=instance_label).set(metrics['start_to_launch_time'])
    launch_to_deal.labels(instance=instance_label).set(metrics['launch_to_deal_time'])
    deal_to_finish.labels(instance=instance_label).set(metrics['deal_to_finish_time'])
    game_duration.labels(instance=instance_label).set(metrics['game_duration_aro21'])
    
    # Push metrics to Pushgateway
    try:
        push_to_gateway(
            gateway=PUSHGATEWAY_URL,
            job=JOB_NAME,
            registry=registry
        )
        print(f"✓ Successfully pushed metrics (instance={instance_label}):")
        print(f"  - finish_to_start_time: {metrics['finish_to_start_time']:.4f}s")
        print(f"  - start_to_launch_time: {metrics['start_to_launch_time']:.4f}s")
        print(f"  - launch_to_deal_time: {metrics['launch_to_deal_time']:.4f}s")
        print(f"  - deal_to_finish_time: {metrics['deal_to_finish_time']:.4f}s")
        print(f"  - game_duration_aro21: {metrics['game_duration_aro21']:.4f}s")
        
        # Save current metrics as last pushed metrics
        save_last_metrics(metrics)
        return True
    except Exception as e:
        print(f"✗ Failed to push metrics: {e}")
        return False


def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown"""
    global running
    print("\n\n⚠ Received shutdown signal, stopping monitor...")
    running = False


def monitor_log_file(log_file_path: str):
    """
    Continuously monitor log file for new metrics and push to Prometheus
    
    Args:
        log_file_path: Path to the log file to monitor
    """
    global running
    
    print(f"🔄 Starting continuous monitoring mode")
    print(f"   Monitoring: {log_file_path}")
    print(f"   Instance: {INSTANCE_LABEL} (ARO-002-1)")
    print(f"   Check interval: {MONITOR_INTERVAL} seconds")
    print(f"   Press Ctrl+C to stop")
    print("-" * 60)
    
    # Initialize position to end of file if starting fresh
    if load_last_position() == 0:
        try:
            current_size = os.path.getsize(log_file_path)
            save_last_position(current_size)
            print(f"ℹ Initializing position at end of file ({current_size} bytes)")
        except Exception as e:
            print(f"⚠ Could not initialize position: {e}")
    
    metrics_count = 0
    
    try:
        while running:
            # Read new metrics from log file
            new_metrics_list = read_new_metrics(log_file_path)
            
            # Process each new metrics block
            for metrics in new_metrics_list:
                metrics_count += 1
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] 📊 Found new metrics block #{metrics_count}")
                
                # Send metrics to Prometheus with ARO21 instance label
                success = send_metrics_to_prometheus(metrics, INSTANCE_LABEL)
                
                if success:
                    print(f"   ✓ Metrics processed and sent")
                else:
                    print(f"   ✗ Failed to send metrics")
            
            # Sleep before next check
            time.sleep(MONITOR_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n⚠ Keyboard interrupt received")
    except Exception as e:
        print(f"\n✗ Error during monitoring: {e}")
        raise
    finally:
        print(f"\n📊 Total metrics blocks processed: {metrics_count}")
        print("👋 Monitor stopped")


def main():
    """Main function - starts continuous monitoring of log file"""
    global running
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("Prometheus Duration Metrics Monitor - ARO-002-1 (ARO21)")
    print("=" * 60)
    print(f"Pushgateway URL: {PUSHGATEWAY_URL}")
    print(f"Job name: {JOB_NAME}")
    print(f"Instance label: {INSTANCE_LABEL}")
    print(f"Log file: {LOG_FILE}")
    print(f"Monitoring interval: {MONITOR_INTERVAL}s")
    print("-" * 60)
    
    # Find the log file
    log_file_path = find_log_file()
    if not log_file_path:
        print(f"✗ Log file not found: {LOG_FILE}")
        print(f"  Tried paths: {POSSIBLE_LOG_PATHS}")
        return
    
    print(f"✓ Found log file: {log_file_path}")
    
    # Start monitoring
    try:
        monitor_log_file(log_file_path)
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Monitor stopped successfully")
    print(f"\nYou can verify the metrics at:")
    print(f"  - Pushgateway: {PUSHGATEWAY_URL}")
    print(f"  - Prometheus: http://100.64.0.113:9090")
    print(f"\nQuery examples in Prometheus:")
    print(f'  finish_to_start_time{{job="{JOB_NAME}", instance="{INSTANCE_LABEL}"}}')
    print(f'  start_to_launch_time{{job="{JOB_NAME}", instance="{INSTANCE_LABEL}"}}')
    print(f'  launch_to_deal_time{{job="{JOB_NAME}", instance="{INSTANCE_LABEL}"}}')
    print(f'  deal_to_finish_time{{job="{JOB_NAME}", instance="{INSTANCE_LABEL}"}}')
    print(f'  game_duration_aro21{{job="{JOB_NAME}", instance="{INSTANCE_LABEL}"}}')


if __name__ == "__main__":
    main()

