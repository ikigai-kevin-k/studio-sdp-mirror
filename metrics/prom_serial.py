#!/usr/bin/env python3
"""
Script for continuously monitoring serial state transition durations from tmux window
and sending to Prometheus Pushgateway

Monitors tmux window 'dp:log_serial' for state changes (*X;2;, *X;3;, *X;4;, *X;5;)
and calculates transition durations:
- 2to3: Time from *X;2; to *X;3;
- 3to4: Time from *X;3; to *X;4;
- 4to5: Time from *X;4; to *X;5;
- 5to2: Time from *X;5; to *X;2;
"""

import re
import os
import json
import time
import signal
import sys
import subprocess
from datetime import datetime
from typing import Optional, Dict, Tuple, List
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# GE server side Pushgateway URL
PUSHGATEWAY_URL = "http://100.64.0.113:9091"
JOB_NAME = "serial_state_transitions"

# Tmux window to monitor
TMUX_WINDOW = "dp:log_serial"

# State file to track last pushed metrics
STATE_FILE = os.path.join(os.path.dirname(__file__), ".last_serial_metrics.json")

# State file to track last processed lines
PROCESSED_LINES_FILE = os.path.join(
    os.path.dirname(__file__), ".last_serial_processed.json"
)

# State file to track last known transitions
TRANSITIONS_FILE = os.path.join(
    os.path.dirname(__file__), ".last_serial_transitions.json"
)

# Monitoring interval in seconds
MONITOR_INTERVAL = 1.0  # Check every 1 second

# Global flag for graceful shutdown
running = True

# State pattern: *X;2;, *X;3;, *X;4;, *X;5;
STATE_PATTERN = re.compile(r'\*X;([2345]);')

# Timestamp pattern: [YYYY-MM-DD HH:MM:SS.milliseconds]
TIMESTAMP_PATTERN = re.compile(
    r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.(\d+))\]'
)


def get_tmux_output() -> str:
    """
    Get output from tmux window 'dp:log_serial'
    Uses larger history to capture more lines
    
    Returns:
        str: Output from tmux window, or empty string on error
    """
    try:
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', TMUX_WINDOW, '-p', '-S', '-2000'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        print("⚠ Timeout getting tmux output")
        return ""
    except FileNotFoundError:
        print("⚠ tmux command not found")
        return ""
    except Exception as e:
        print(f"⚠ Error getting tmux output: {e}")
        return ""


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse timestamp from log line format [YYYY-MM-DD HH:MM:SS.milliseconds]
    
    Args:
        timestamp_str: Timestamp string
        
    Returns:
        datetime: Parsed datetime object, or None on error
    """
    try:
        # Format: YYYY-MM-DD HH:MM:SS.milliseconds
        # Convert milliseconds to microseconds for datetime
        parts = timestamp_str.split('.')
        if len(parts) == 2:
            base_time = parts[0]
            milliseconds = parts[1]
            # Pad milliseconds to microseconds (6 digits)
            microseconds = milliseconds.ljust(6, '0')[:6]
            dt_str = f"{base_time}.{microseconds}"
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
        else:
            # Fallback to seconds precision
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"⚠ Error parsing timestamp '{timestamp_str}': {e}")
        return None


def parse_state_from_line(line: str) -> Optional[Tuple[datetime, int]]:
    """
    Parse state and timestamp from a log line
    
    Args:
        line: Log line to parse
        
    Returns:
        tuple: (datetime, state_number) if found, or None
        State number is 2, 3, 4, or 5
    """
    # Check if line contains Receive >>> *X;N; pattern
    if 'Receive >>>' not in line:
        return None
    
    # Extract timestamp
    timestamp_match = TIMESTAMP_PATTERN.search(line)
    if not timestamp_match:
        return None
    
    timestamp_str = timestamp_match.group(1)
    timestamp = parse_timestamp(timestamp_str)
    if not timestamp:
        return None
    
    # Extract state
    state_match = STATE_PATTERN.search(line)
    if not state_match:
        return None
    
    state_num = int(state_match.group(1))
    return (timestamp, state_num)


def load_processed_state():
    """
    Load last processed state from file
    
    Returns:
        dict: Dictionary with last_processed_hash and state_history
    """
    if not os.path.exists(PROCESSED_LINES_FILE):
        return {
            'last_processed_hash': None,
            'state_history': []
        }
    
    try:
        with open(PROCESSED_LINES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {
                'last_processed_hash': data.get('last_processed_hash'),
                'state_history': data.get('state_history', [])
            }
    except Exception:
        return {
            'last_processed_hash': None,
            'state_history': []
        }


def load_last_processed_states() -> Dict[int, datetime]:
    """
    Load last processed states from file
    
    Returns:
        dict: Dictionary of {state: timestamp}
    """
    if not os.path.exists(TRANSITIONS_FILE):
        return {}
    
    try:
        with open(TRANSITIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            states = {}
            for state_str, timestamp_str in data.items():
                try:
                    state = int(state_str)
                    timestamp = datetime.fromisoformat(timestamp_str)
                    states[state] = timestamp
                except (ValueError, KeyError):
                    continue
            return states
    except Exception:
        return {}


def save_last_processed_states(states: Dict[int, datetime]):
    """
    Save last processed states to file
    
    Args:
        states: Dictionary of {state: timestamp}
    """
    try:
        data = {
            str(state): ts.isoformat()
            for state, ts in states.items()
        }
        with open(TRANSITIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠ Warning: Failed to save processed states file: {e}")


def save_processed_state(state: dict):
    """
    Save processed state to file
    
    Args:
        state: Dictionary with last_processed_hash and state_history
    """
    try:
        with open(PROCESSED_LINES_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠ Warning: Failed to save processed state: {e}")


def calculate_transition_durations(
    first_occurrences: List[Tuple[datetime, int]],
    last_processed_states: Optional[Dict[int, datetime]] = None
) -> Tuple[Dict[str, float], Dict[int, datetime], bool]:
    """
    Calculate transition durations from first occurrences of states
    Calculates time from state A first occurrence to state B first occurrence
    
    The logic:
    - For each state, record its first occurrence timestamp
    - When a new state appears, calculate duration from previous state's first occurrence
    - Only calculate transitions that follow the expected sequence: 2->3->4->5->2
    
    Args:
        first_occurrences: List of (timestamp, state) tuples in chronological order (only first occurrences)
        last_processed_states: Dict of last processed states {state: timestamp}
        
    Returns:
        tuple: (durations_dict, new_states_dict, has_new_data)
        durations_dict: Dictionary with durations for 2to3, 3to4, 4to5, 5to2
        new_states_dict: Dictionary of newly detected states {state: timestamp}
        has_new_data: True if new transitions were found
    """
    durations = {
        '2to3': None,
        '3to4': None,
        '4to5': None,
        '5to2': None
    }
    
    if last_processed_states is None:
        last_processed_states = {}
    
    if len(first_occurrences) < 2:
        return durations, {}, False
    
    # Find which states are new (not in last_processed_states or with later timestamp)
    new_states = {}
    for timestamp, state in first_occurrences:
        last_timestamp = last_processed_states.get(state)
        if last_timestamp is None or timestamp > last_timestamp:
            new_states[state] = timestamp
    
    has_new_data = len(new_states) > 0
    
    # Process the state sequence to find transitions
    # The sequence contains first occurrences, potentially across multiple cycles
    # Example: [(ts1, 2), (ts2, 3), (ts3, 4), (ts4, 5), (ts5, 2), ...] represents cycles
    
    # Go through the sequence and find transitions
    for i in range(len(first_occurrences) - 1):
        from_timestamp, from_state = first_occurrences[i]
        to_timestamp, to_state = first_occurrences[i + 1]
        
        # Calculate duration from from_state first occurrence to to_state first occurrence
        duration = (to_timestamp - from_timestamp).total_seconds()
        
        # Only record if duration is positive (should always be, but check anyway)
        if duration <= 0:
            continue
        
        # Determine transition type based on expected sequence
        transition_type = None
        if from_state == 2 and to_state == 3:
            transition_type = '2to3'
        elif from_state == 3 and to_state == 4:
            transition_type = '3to4'
        elif from_state == 4 and to_state == 5:
            transition_type = '4to5'
        elif from_state == 5 and to_state == 2:
            transition_type = '5to2'
        
        # Record the transition duration
        # Keep the latest (most recent) duration for each transition type
        if transition_type:
            if durations[transition_type] is None or duration > durations[transition_type]:
                durations[transition_type] = duration
    
    return durations, new_states, has_new_data


def get_first_occurrences() -> Tuple[Optional[int], List[Tuple[datetime, int]]]:
    """
    Get current state and state history with only first occurrence of each state in each cycle
    Tracks the first time each state appears, allowing multiple cycles
    
    Returns:
        tuple: (current_state, first_occurrences)
        current_state: Latest state (2, 3, 4, or 5), or None if not found
        first_occurrences: List of (timestamp, state) tuples, first occurrence of each state
                          Includes multiple cycles (e.g., if state 2 appears twice, both are recorded)
    """
    output = get_tmux_output()
    if not output:
        return None, []
    
    lines = output.split('\n')
    
    # Track first occurrence of each state in sequence
    # We need to track state transitions, so when state 2 appears again after 5, it's a new cycle
    first_occurrences = []
    seen_states_in_current_cycle = set()  # Track which states we've seen in current cycle
    
    for line in lines:
        if not line.strip():
            continue
        
        parsed = parse_state_from_line(line)
        if parsed:
            timestamp, state = parsed
            
            # Check if this is the first time we see this state in the current cycle
            # A cycle starts with state 2, and ends when we see state 2 again
            if state == 2 and 2 in seen_states_in_current_cycle:
                # State 2 appeared again, this starts a new cycle
                seen_states_in_current_cycle = {2}
                first_occurrences.append((timestamp, state))
            elif state not in seen_states_in_current_cycle:
                # First time seeing this state in current cycle
                seen_states_in_current_cycle.add(state)
                first_occurrences.append((timestamp, state))
    
    # Sort by timestamp to ensure chronological order
    first_occurrences.sort(key=lambda x: x[0])
    
    # Get current state (latest state based on last timestamp in first_occurrences)
    # But we should actually check the last line of tmux output for current state
    current_state = None
    if first_occurrences:
        _, current_state = first_occurrences[-1]
    
    return current_state, first_occurrences


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
        print(f"⚠ Warning: Failed to save state file: {e}")


def metrics_are_equal(metrics1: dict, metrics2: dict) -> bool:
    """
    Compare two metrics dictionaries for equality
    
    Args:
        metrics1: First metrics dictionary
        metrics2: Second metrics dictionary
        
    Returns:
        bool: True if all metrics are equal, False otherwise
    """
    required_metrics = ['2to3', '3to4', '4to5', '5to2']
    
    for metric in required_metrics:
        val1 = metrics1.get(metric)
        val2 = metrics2.get(metric)
        
        # None values are considered equal to None
        if val1 is None and val2 is None:
            continue
        
        # If one is None and the other isn't, they're not equal
        if val1 is None or val2 is None:
            return False
        
        # Compare with small tolerance for floating point comparison
        if abs(val1 - val2) > 0.0001:
            return False
    
    return True


def send_metrics_to_prometheus(metrics: dict, instance_label: str = "serial-instance"):
    """
    Send state transition duration metrics to Pushgateway
    Only pushes if metrics have changed since last push
    
    Args:
        metrics: Dictionary containing the four transition durations
        instance_label: Instance label for the metrics
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Create a registry for this push
    registry = CollectorRegistry()
    
    # Create Gauge metrics for each transition duration
    state_2to3 = Gauge(
        'serial_state_2to3_duration',
        'Duration from state 2 to state 3 in seconds',
        ['instance'],
        registry=registry
    )
    
    state_3to4 = Gauge(
        'serial_state_3to4_duration',
        'Duration from state 3 to state 4 in seconds',
        ['instance'],
        registry=registry
    )
    
    state_4to5 = Gauge(
        'serial_state_4to5_duration',
        'Duration from state 4 to state 5 in seconds',
        ['instance'],
        registry=registry
    )
    
    state_5to2 = Gauge(
        'serial_state_5to2_duration',
        'Duration from state 5 to state 2 in seconds',
        ['instance'],
        registry=registry
    )
    
    # Check if metrics are the same as last push
    last_metrics = load_last_metrics()
    if last_metrics and metrics_are_equal(metrics, last_metrics):
        print("ℹ Metrics are identical to last push, skipping...")
        return True
    
    # Set the metric values with instance label
    # Only set if value is not None
    if metrics.get('2to3') is not None:
        state_2to3.labels(instance=instance_label).set(metrics['2to3'])
    
    if metrics.get('3to4') is not None:
        state_3to4.labels(instance=instance_label).set(metrics['3to4'])
    
    if metrics.get('4to5') is not None:
        state_4to5.labels(instance=instance_label).set(metrics['4to5'])
    
    if metrics.get('5to2') is not None:
        state_5to2.labels(instance=instance_label).set(metrics['5to2'])
    
    # Push metrics to Pushgateway
    try:
        push_to_gateway(
            gateway=PUSHGATEWAY_URL,
            job=JOB_NAME,
            registry=registry
        )
        print(f"✓ Successfully pushed metrics (instance={instance_label}):")
        for metric_name, value in metrics.items():
            if value is not None:
                print(f"  - {metric_name}: {value:.4f}s")
            else:
                print(f"  - {metric_name}: (no data)")
        
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


def monitor_serial_states():
    """
    Continuously monitor tmux window for state changes and push metrics to Prometheus
    """
    global running
    
    print(f"🔄 Starting continuous monitoring mode")
    print(f"   Monitoring tmux window: {TMUX_WINDOW}")
    print(f"   Check interval: {MONITOR_INTERVAL} seconds")
    print(f"   Press Ctrl+C to stop")
    print("-" * 60)
    
    # Load last processed states
    last_processed_states = load_last_processed_states()
    
    # Keep track of all durations (most recent for each transition type)
    all_durations = {
        '2to3': None,
        '3to4': None,
        '4to5': None,
        '5to2': None
    }
    
    metrics_count = 0
    
    try:
        while running:
            # Get current state and first occurrences from tmux
            current_state, first_occurrences = get_first_occurrences()
            
            if not first_occurrences:
                # No states found, wait and retry
                time.sleep(MONITOR_INTERVAL)
                continue
            
            # Calculate transition durations from first occurrences
            durations, new_states, has_new_data = calculate_transition_durations(
                first_occurrences, last_processed_states
            )
            
            # Update all_durations with new values (keep most recent for each type)
            for trans_type, duration in durations.items():
                if duration is not None:
                    all_durations[trans_type] = duration
            
            # Check if we have new states/transitions to process
            if has_new_data:
                metrics_count += 1
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] 📊 Found new state transitions #{metrics_count}")
                print(f"   Current state: {current_state}")
                
                # Print new states detected
                if new_states:
                    print(f"   New states detected: {list(new_states.keys())}")
                
                # Print durations found
                for trans_type, duration in durations.items():
                    if duration is not None:
                        print(f"   - {trans_type}: {duration:.4f}s")
                
                # Send metrics to Prometheus (send all durations we have so far)
                success = send_metrics_to_prometheus(all_durations)
                
                if success:
                    print(f"   ✓ Metrics processed and sent")
                else:
                    print(f"   ✗ Failed to send metrics")
                
                # Update last processed states with new ones
                last_processed_states.update(new_states)
                save_last_processed_states(last_processed_states)
            
            # Sleep before next check
            time.sleep(MONITOR_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n⚠ Keyboard interrupt received")
    except Exception as e:
        print(f"\n✗ Error during monitoring: {e}")
        raise
    finally:
        print(f"\n📊 Total metrics updates processed: {metrics_count}")
        print("👋 Monitor stopped")


def main():
    """Main function - starts continuous monitoring of serial states"""
    global running
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("Prometheus Serial State Transition Monitor")
    print("=" * 60)
    print(f"Pushgateway URL: {PUSHGATEWAY_URL}")
    print(f"Job name: {JOB_NAME}")
    print(f"Tmux window: {TMUX_WINDOW}")
    print(f"Monitoring interval: {MONITOR_INTERVAL}s")
    print("-" * 60)
    
    # Verify tmux window exists
    try:
        result = subprocess.run(
            ['tmux', 'list-windows', '-t', 'dp'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if 'log_serial' not in result.stdout:
            print(f"⚠ Warning: tmux window '{TMUX_WINDOW}' may not exist")
            print("  Available windows:")
            print(result.stdout)
    except Exception as e:
        print(f"⚠ Warning: Could not verify tmux window: {e}")
    
    # Test getting output
    test_output = get_tmux_output()
    if not test_output:
        print(f"✗ Could not get output from tmux window '{TMUX_WINDOW}'")
        print("  Make sure the tmux session 'dp' exists and has a 'log_serial' window")
        return
    
    print(f"✓ Successfully connected to tmux window")
    
    # Start monitoring
    try:
        monitor_serial_states()
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Monitor stopped successfully")
    print(f"\nYou can verify the metrics at:")
    print(f"  - Pushgateway: {PUSHGATEWAY_URL}")
    print(f"  - Prometheus: http://100.64.0.113:9090")
    print(f"\nQuery examples in Prometheus:")
    print(f'  serial_state_2to3_duration{{job="{JOB_NAME}"}}')
    print(f'  serial_state_3to4_duration{{job="{JOB_NAME}"}}')
    print(f'  serial_state_4to5_duration{{job="{JOB_NAME}"}}')
    print(f'  serial_state_5to2_duration{{job="{JOB_NAME}"}}')


if __name__ == "__main__":
    main()

