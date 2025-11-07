#!/usr/bin/env python3
"""
Script for continuously monitoring time interval metrics from log file and sending to Prometheus Pushgateway
Continuously watches SBO001_{mmdd}.log for new metrics and pushes to GE server side Prometheus Pushgateway service
Reads finish_to_start_time, start_to_launch_time, launch_to_deal_time, deal_to_finish_time
Calculates game_duration_sbo11 as the sum of all four time intervals
Specifically for SBO-001-1 (SBO11) instance
"""

import re
import os
import json
import time
import signal
import sys
from datetime import datetime
from glob import glob
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# GE server side Pushgateway URL
PUSHGATEWAY_URL = "http://100.64.0.113:9091"
JOB_NAME = "time_intervals_metrics"

# Log file pattern for SicBo game (SBO001_{mmdd}.log)
LOG_FILE_PATTERN = "SBO001_*.log"
LOG_DIR = "logs"

# Instance label for SBO-001-1
INSTANCE_LABEL = "sbo11"

# Alternative paths to try for log directory
POSSIBLE_LOG_DIRS = [
    LOG_DIR,
    os.path.join(os.path.dirname(__file__), "..", LOG_DIR),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), LOG_DIR),
    f"/home/rnd/studio-sdp-roulette/{LOG_DIR}"
]

# State file to track last pushed metrics
STATE_FILE = os.path.join(os.path.dirname(__file__), ".last_metrics_sbo11.json")

# State file to track last read position in log file
POSITION_FILE = os.path.join(os.path.dirname(__file__), ".last_position_sbo11.json")

# State file to track last finish time for calculating finish_to_start_time
LAST_FINISH_TIME_FILE = os.path.join(os.path.dirname(__file__), ".last_finish_time_sbo11.json")

# State file to track incomplete round across reads
INCOMPLETE_ROUND_FILE = os.path.join(os.path.dirname(__file__), ".incomplete_round_sbo11.json")

# Monitoring interval in seconds
MONITOR_INTERVAL = 1.0  # Check every 1 second

# Global flag for graceful shutdown
running = True

# Global variable to track last finish time across file reads
last_finish_time = None


def find_latest_log_file():
    """
    Find the latest SBO001_{mmdd}.log file from possible log directories
    
    Returns:
        str: Path to the latest log file, or None if not found
    """
    log_files = []
    
    # Search in all possible log directories
    for log_dir in POSSIBLE_LOG_DIRS:
        if not os.path.isdir(log_dir):
            continue
        
        # Find all SBO001_*.log files
        pattern = os.path.join(log_dir, LOG_FILE_PATTERN)
        found_files = glob(pattern)
        
        # Filter out rotated log files (e.g., SBO001_1106.log.1, SBO001_1106.log.2, etc.)
        for file_path in found_files:
            # Only include files that end with .log (not .log.1, .log.2, etc.)
            if file_path.endswith('.log') and not any(file_path.endswith(f'.log.{i}') for i in range(1, 10)):
                log_files.append(file_path)
    
    if not log_files:
        return None
    
    # Sort by modification time and return the latest
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return log_files[0]


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


def parse_timestamp_from_line(line: str):
    """
    Parse timestamp from log line format: 2025-11-06 12:24:39,796
    
    Args:
        line: Log line containing timestamp
        
    Returns:
        datetime: Parsed datetime object, or None if parsing failed
    """
    # Pattern to match: "YYYY-MM-DD HH:MM:SS,mmm"
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})'
    match = re.search(pattern, line)
    if match:
        try:
            timestamp_str = match.group(1) + '.' + match.group(2)
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            return None
    return None


def find_last_finish_time_from_file(log_file_path: str):
    """
    Find the last finish time from log file by scanning backwards
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        datetime: Last finish time, or None if not found
    """
    try:
        # Read last 100KB of file to find last finish
        chunk_size = 100 * 1024  # 100KB
        file_size = os.path.getsize(log_file_path)
        
        if file_size == 0:
            return None
        
        # Read from end of file
        start_pos = max(0, file_size - chunk_size)
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            f.seek(start_pos)
            content = f.read()
        
        # Split into lines and search backwards for last finish
        lines = content.strip().split('\n')
        
        # Search from end to beginning
        for line in reversed(lines):
            if "Successfully finished round for table" in line:
                timestamp = parse_timestamp_from_line(line)
                if timestamp:
                    return timestamp
        
        return None
    except Exception as e:
        print(f"⚠️  Error finding last finish time: {e}")
        return None


def load_last_finish_time():
    """
    Load last finish time from state file
    
    Returns:
        datetime: Last finish time, or None if file doesn't exist
    """
    global last_finish_time
    
    if not os.path.exists(LAST_FINISH_TIME_FILE):
        return None
    
    try:
        with open(LAST_FINISH_TIME_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            finish_time_str = data.get('finish_time')
            if finish_time_str:
                return datetime.fromisoformat(finish_time_str)
    except Exception:
        return None
    
    return None


def save_last_finish_time(finish_time: datetime):
    """
    Save last finish time to state file
    
    Args:
        finish_time: Datetime object of the finish time
    """
    global last_finish_time
    last_finish_time = finish_time
    
    try:
        with open(LAST_FINISH_TIME_FILE, 'w', encoding='utf-8') as f:
            json.dump({'finish_time': finish_time.isoformat()}, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save last finish time: {e}")


def load_incomplete_round():
    """
    Load incomplete round state from file
    
    Returns:
        tuple: (round_lines, in_round) or (None, False) if no incomplete round
    """
    if not os.path.exists(INCOMPLETE_ROUND_FILE):
        return None, False
    
    try:
        with open(INCOMPLETE_ROUND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            round_lines = data.get('round_lines', [])
            in_round = data.get('in_round', False)
            if round_lines and in_round:
                return round_lines, True
    except Exception:
        pass
    
    return None, False


def save_incomplete_round(round_lines: list, in_round: bool):
    """
    Save incomplete round state to file
    
    Args:
        round_lines: List of log lines for the incomplete round
        in_round: Whether we're currently tracking a round
    """
    try:
        if in_round and round_lines:
            with open(INCOMPLETE_ROUND_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'round_lines': round_lines,
                    'in_round': in_round
                }, f, indent=2)
        else:
            # Remove file if round is complete
            if os.path.exists(INCOMPLETE_ROUND_FILE):
                os.remove(INCOMPLETE_ROUND_FILE)
    except Exception as e:
        print(f"Warning: Failed to save incomplete round: {e}")


def parse_metrics_from_log_lines(lines: list, previous_finish_time: datetime = None):
    """
    Parse metrics from log lines by calculating time intervals between events
    Tracks: previous_finish -> start -> deal -> finish
    
    Args:
        lines: List of log lines to parse
        previous_finish_time: Datetime of previous round's finish (from global state)
        
    Returns:
        dict: Dictionary containing the four metrics plus game_duration_sbo11, or None if parsing failed
    """
    global last_finish_time
    
    # Use provided previous_finish_time or load from global state
    if previous_finish_time is None:
        previous_finish_time = last_finish_time or load_last_finish_time()
    
    # Track timestamps for key events in current round
    start_time = None
    deal_time = None
    finish_time = None
    
    # Parse lines to find key events in sequence
    for line in lines:
        timestamp = parse_timestamp_from_line(line)
        if not timestamp:
            continue
        
        # Find "Starting new round" - this is the start time
        if "Starting new round" in line:
            start_time = timestamp
        
        # Find "Successfully dealt round" - this is the deal time
        elif "Successfully dealt round for table" in line:
            if deal_time is None:  # Use first deal time
                deal_time = timestamp
        
        # Find "Successfully finished round" - this is the current round's finish
        elif "Successfully finished round for table" in line:
            if finish_time is None:  # Use first finish time
                finish_time = timestamp
    
    # Calculate time intervals - need all required timestamps
    if not start_time or not deal_time or not finish_time:
        missing = []
        if not start_time:
            missing.append("start_time")
        if not deal_time:
            missing.append("deal_time")
        if not finish_time:
            missing.append("finish_time")
        print(f"  ⚠️  Missing timestamps: {', '.join(missing)}")
        return None
    
    # If we don't have previous_finish_time, we can't calculate finish_to_start_time
    # This happens on the first round - skip it
    if previous_finish_time is None:
        # Save current finish time for next round
        save_last_finish_time(finish_time)
        print(f"  ⚠️  No previous_finish_time, skipping round (will use this finish for next round)")
        return None
    
    metrics = {}
    
    # finish_to_start_time: from previous finish to new start
    metrics['finish_to_start_time'] = (start_time - previous_finish_time).total_seconds()
    
    # start_to_launch_time: from start to deal (for SicBo, launch is same as deal)
    metrics['start_to_launch_time'] = (deal_time - start_time).total_seconds()
    
    # launch_to_deal_time: for SicBo, this is 0 (launch and deal are the same)
    metrics['launch_to_deal_time'] = 0.0
    
    # deal_to_finish_time: from deal to finish
    metrics['deal_to_finish_time'] = (finish_time - deal_time).total_seconds()
    
    # Calculate total game duration (sum of all four time intervals)
    metrics['game_duration_sbo11'] = (
        metrics['finish_to_start_time'] +
        metrics['start_to_launch_time'] +
        metrics['launch_to_deal_time'] +
        metrics['deal_to_finish_time']
    )
    
    # Save current finish time for next round
    save_last_finish_time(finish_time)
    
    return metrics


def read_new_metrics(log_file_path: str):
    """
    Read new metrics from log file since last read position
    Parses log lines to calculate time intervals between game events
    
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
        
        # Calculate new content size
        new_content_size = len(new_content.encode('utf-8'))
        
        # Update position
        save_last_position(current_size)
        
        # If no new content, return empty list
        if not new_content.strip():
            return []
        
        # Debug: Print new content info
        new_lines_count = len(new_content.strip().split('\n'))
        if new_lines_count > 0:
            print(f"📖 Read {new_content_size} bytes ({new_lines_count} lines) from position {last_position}")
        
        # Split into lines
        new_lines = new_content.strip().split('\n')
        
        # Track game rounds - look for complete round sequences
        # A complete round: previous_finish -> start -> deal -> finish
        metrics_list = []
        
        # Load incomplete round from previous read (if any)
        round_lines, in_round = load_incomplete_round()
        if round_lines is None:
            round_lines = []
            in_round = False
        else:
            print(f"📋 Resuming incomplete round from previous read ({len(round_lines)} lines)")
        
        # Load last finish time at the start
        previous_finish = load_last_finish_time()
        if previous_finish:
            print(f"📅 Previous finish time: {previous_finish.strftime('%Y-%m-%d %H:%M:%S.%f')}")
        else:
            print("📅 No previous finish time (first round will be skipped)")
        
        # Track events found
        events_found = {
            'Starting new round': 0,
            'Successfully dealt round': 0,
            'Successfully finished round': 0
        }
        
        for line in new_lines:
            if not line.strip():
                continue
            
            # Track events
            if "Starting new round" in line:
                events_found['Starting new round'] += 1
            elif "Successfully dealt round for table" in line:
                events_found['Successfully dealt round'] += 1
            elif "Successfully finished round for table" in line:
                events_found['Successfully finished round'] += 1
            
            # Start tracking a new round when we see "Starting new round"
            if "Starting new round" in line:
                if in_round and round_lines:
                    # We were tracking a previous round, try to parse it
                    print(f"🔄 Found new round start, parsing previous round ({len(round_lines)} lines)")
                    metrics = parse_metrics_from_log_lines(round_lines, previous_finish)
                    if metrics:
                        metrics_list.append(metrics)
                        print(f"✅ Parsed previous round metrics")
                        # Update previous_finish for next round
                        previous_finish = load_last_finish_time()
                    else:
                        print(f"⚠️  Failed to parse previous round (missing events)")
                
                # Start tracking new round
                round_lines = [line]
                in_round = True
            
            elif in_round:
                # We're tracking a round, add all lines
                round_lines.append(line)
                
                # Check if we've completed the round (found finish)
                if "Successfully finished round for table" in line:
                    # We have a complete round, parse it
                    print(f"🏁 Found round finish, parsing round ({len(round_lines)} lines)")
                    metrics = parse_metrics_from_log_lines(round_lines, previous_finish)
                    if metrics:
                        metrics_list.append(metrics)
                        print(f"✅ Parsed round metrics")
                        # Update previous_finish for next round
                        previous_finish = load_last_finish_time()
                    else:
                        print(f"⚠️  Failed to parse round (missing events or previous_finish)")
                    # Continue tracking (finish becomes previous_finish for next round)
                    round_lines = []
                    in_round = False
        
        # Handle last round if it's complete
        if in_round and round_lines:
            # Check if we have a finish in the round
            has_finish = any("Successfully finished round for table" in line for line in round_lines)
            if has_finish:
                print(f"🏁 Parsing last round ({len(round_lines)} lines)")
                metrics = parse_metrics_from_log_lines(round_lines, previous_finish)
                if metrics:
                    metrics_list.append(metrics)
                    print(f"✅ Parsed last round metrics")
                    # Round is complete, clear state
                    round_lines = []
                    in_round = False
                else:
                    print(f"⚠️  Failed to parse last round")
        
        # Save incomplete round state for next read
        save_incomplete_round(round_lines, in_round)
        if in_round and round_lines:
            print(f"💾 Saved incomplete round state ({len(round_lines)} lines) for next read")
        
        # Debug: Print events found
        if any(count > 0 for count in events_found.values()):
            print(f"📊 Events found: {events_found}")
        
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
        'game_duration_sbo11'
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
        metrics: Dictionary containing the four metrics plus game_duration_sbo11
        instance_label: Instance label for the metrics (default: sbo11)
        
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
        'game_duration_sbo11',
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
    game_duration.labels(instance=instance_label).set(metrics['game_duration_sbo11'])
    
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
        print(f"  - game_duration_sbo11: {metrics['game_duration_sbo11']:.4f}s")
        
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
    Automatically switches to latest log file if a new one is created
    
    Args:
        log_file_path: Path to the log file to monitor
    """
    global running
    
    current_log_file = log_file_path
    
    print(f"🔄 Starting continuous monitoring mode")
    print(f"   Monitoring: {current_log_file}")
    print(f"   Instance: {INSTANCE_LABEL} (SBO-001-1)")
    print(f"   Check interval: {MONITOR_INTERVAL} seconds")
    print(f"   Press Ctrl+C to stop")
    print("-" * 60)
    
    # Initialize position to end of file if starting fresh
    if load_last_position() == 0:
        try:
            current_size = os.path.getsize(current_log_file)
            
            # Try to find last finish time from existing log file
            if not load_last_finish_time():
                print("ℹ No previous finish time found, scanning log file for last finish...")
                last_finish = find_last_finish_time_from_file(current_log_file)
                if last_finish:
                    save_last_finish_time(last_finish)
                    print(f"✅ Found last finish time: {last_finish.strftime('%Y-%m-%d %H:%M:%S.%f')}")
                else:
                    print("⚠️  No finish time found in log file, first round will be skipped")
            
            save_last_position(current_size)
            print(f"ℹ Initializing position at end of file ({current_size} bytes)")
        except Exception as e:
            print(f"⚠ Could not initialize position: {e}")
    
    metrics_count = 0
    
    try:
        while running:
            # Check if a newer log file exists
            latest_log_file = find_latest_log_file()
            if latest_log_file and latest_log_file != current_log_file:
                print(f"🔄 Newer log file detected: {latest_log_file}")
                print(f"   Switching from: {current_log_file}")
                current_log_file = latest_log_file
                # Reset position when switching files
                save_last_position(0)
            
            # Read new metrics from current log file
            new_metrics_list = read_new_metrics(current_log_file)
            
            # Process each new metrics block
            for metrics in new_metrics_list:
                metrics_count += 1
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] 📊 Found new metrics block #{metrics_count}")
                
                # Send metrics to Prometheus with SBO11 instance label
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
    print("Prometheus Duration Metrics Monitor - SBO-001-1 (SBO11)")
    print("=" * 60)
    print(f"Pushgateway URL: {PUSHGATEWAY_URL}")
    print(f"Job name: {JOB_NAME}")
    print(f"Instance label: {INSTANCE_LABEL}")
    print(f"Log file pattern: {LOG_FILE_PATTERN}")
    print(f"Log directory: {LOG_DIR}")
    print(f"Monitoring interval: {MONITOR_INTERVAL}s")
    print("-" * 60)
    
    # Find the latest log file
    log_file_path = find_latest_log_file()
    if not log_file_path:
        print(f"✗ Log file not found: {LOG_FILE_PATTERN}")
        print(f"  Searched in directories: {POSSIBLE_LOG_DIRS}")
        return
    
    print(f"✓ Found latest log file: {log_file_path}")
    print(f"  File modified: {time.ctime(os.path.getmtime(log_file_path))}")
    
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
    print(f'  game_duration_sbo11{{job="{JOB_NAME}", instance="{INSTANCE_LABEL}"}}')


if __name__ == "__main__":
    main()

