#!/usr/bin/env python3
"""
Monitor speed_{yyyy-mm-dd}.log files for ERROR|Error|error lines and push to Loki server
Continuously watches log files and pushes error log entries to remote Loki server

Based on Loki server settings:
- Server: http://100.64.0.113:3100
- Endpoint: /loki/api/v1/push
- Port: 3100
"""

import os
import sys
import re
import json
import time
import signal
import requests
from datetime import datetime, timedelta
from glob import glob
from typing import List, Dict, Optional

# Configuration
LOKI_URL = "http://100.64.0.113:3100/loki/api/v1/push"
STUDIO_SDP_DIR = "/home/rnd/studio-sdp-roulette"
LOG_FILE_PATTERN = "speed_*.log"

# State file to track last read position in log file
POSITION_FILE = os.path.join(STUDIO_SDP_DIR, ".last_position_speed_errors.json")

# Monitoring interval in seconds
MONITOR_INTERVAL = 5.0  # Check every 5 seconds

# Batch size for pushing to Loki (push when we have this many errors)
BATCH_SIZE = 10

# Global flag for graceful shutdown
running = True

# Global buffer for error logs
error_buffer: List[Dict] = []


def find_latest_log_file() -> Optional[str]:
    """
    Find the latest speed_{yyyy-mm-dd}.log file by date (not modification time)
    
    Returns:
        str: Path to the latest log file, or None if not found
    """
    # Find all speed_*.log files matching pattern speed_{yyyy-mm-dd}.log
    pattern = os.path.join(STUDIO_SDP_DIR, LOG_FILE_PATTERN)
    found_files = glob(pattern)
    
    # Filter to only match speed_{yyyy-mm-dd}.log format (e.g., speed_2025-11-11.log)
    log_files = []
    for file_path in found_files:
        filename = os.path.basename(file_path)
        # Match pattern: speed_YYYY-MM-DD.log
        match = re.match(r'^speed_(\d{4}-\d{2}-\d{2})\.log$', filename)
        if match:
            try:
                # Extract date and parse it
                date_str = match.group(1)
                file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                log_files.append((file_path, file_date))
            except ValueError:
                continue
    
    if not log_files:
        return None
    
    # Sort by date (descending) and return the latest
    log_files.sort(key=lambda x: x[1], reverse=True)
    return log_files[0][0]


def parse_timestamp_from_line(line: str) -> Optional[datetime]:
    """
    Parse timestamp from log line format: [2025-11-06 12:11:21.730]
    
    Args:
        line: Log line containing timestamp
        
    Returns:
        datetime: Parsed datetime object, or None if parsing failed
    """
    # Pattern to match: "[YYYY-MM-DD HH:MM:SS.mmm]"
    pattern = r'\[(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\.(\d{3})\]'
    match = re.search(pattern, line)
    if match:
        try:
            timestamp_str = match.group(1) + ' ' + match.group(2) + '.' + match.group(3)
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            return None
    return None


def is_error_line(line: str) -> bool:
    """
    Check if a log line contains ERROR|Error|error
    
    Args:
        line: Log line to check
        
    Returns:
        bool: True if line contains error, False otherwise
    """
    return bool(re.search(r'\b(ERROR|Error|error)\b', line))


def load_last_position() -> int:
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


def save_last_position(position: int, log_file: str):
    """
    Save last read position to state file
    
    Args:
        position: Byte position in the log file
        log_file: Path to the log file
    """
    try:
        with open(POSITION_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'position': position,
                'log_file': log_file,
                'last_update': datetime.now().isoformat()
            }, f, indent=2)
    except Exception as e:
        print(f"⚠️  Warning: Failed to save position file: {e}")


def read_error_lines(log_file_path: str) -> List[Dict]:
    """
    Read new error lines from log file since last read position
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        list: List of error log entries with timestamp and message
    """
    try:
        # Get current file size
        current_size = os.path.getsize(log_file_path)
        last_position = load_last_position()
        
        # Check if we're reading a different file
        saved_data = {}
        if os.path.exists(POSITION_FILE):
            try:
                with open(POSITION_FILE, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
            except:
                pass
        
        # If file changed, reset position
        if saved_data.get('log_file') != log_file_path:
            last_position = 0
        
        # If file was truncated or is smaller, reset position
        if current_size < last_position:
            print("⚠️  Log file appears to have been rotated or truncated, resetting position")
            last_position = 0
        
        # If no new content, return empty list
        if current_size <= last_position:
            return []
        
        # Read new content
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Seek to last position
            f.seek(last_position)
            new_content = f.read()
        
        # Update position
        save_last_position(current_size, log_file_path)
        
        # If no new content, return empty list
        if not new_content.strip():
            return []
        
        # Split into lines and filter error lines
        error_lines = []
        new_lines = new_content.strip().split('\n')
        
        for line in new_lines:
            if not line.strip():
                continue
            
            # Check if line contains error
            if is_error_line(line):
                # Parse timestamp
                timestamp = parse_timestamp_from_line(line)
                if timestamp:
                    error_lines.append({
                        'timestamp': timestamp,
                        'message': line.strip(),
                        'log_file': os.path.basename(log_file_path)
                    })
        
        return error_lines
        
    except Exception as e:
        print(f"✗ Error reading log file: {e}")
        return []


def push_errors_to_loki(error_entries: List[Dict]) -> bool:
    """
    Push error log entries to Loki server
    
    Args:
        error_entries: List of error log entries with timestamp and message
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not error_entries:
        return True
    
    try:
        # Filter out entries that are too old
        # Loki has a dynamic "oldest acceptable timestamp" that changes based on current time
        # To be safe, we'll only keep entries from the last 6 hours
        # This should capture most recent errors while avoiding timestamp issues
        cutoff_time = datetime.now() - timedelta(hours=6)
        # Also filter out entries more than 1 hour in the future
        future_threshold = datetime.now() + timedelta(hours=1)
        
        filtered_entries = []
        skipped_old = 0
        skipped_future = 0
        
        for entry in error_entries:
            timestamp = entry['timestamp']
            if timestamp < cutoff_time:
                skipped_old += 1
                continue
            if timestamp > future_threshold:
                skipped_future += 1
                continue
            filtered_entries.append(entry)
        
        if skipped_old > 0:
            print(f"   ⚠️  Skipped {skipped_old} entries older than 6 hours (Loki timestamp limit)")
        if skipped_future > 0:
            print(f"   ⚠️  Skipped {skipped_future} entries with future timestamps")
        
        if not filtered_entries:
            return True  # No valid entries, but not an error
        
        # Prepare Loki payload
        values = []
        for entry in filtered_entries:
            timestamp = entry['timestamp']
            # Convert to nanoseconds
            timestamp_ns = int(timestamp.timestamp() * 1000000000)
            
            # Create JSON log entry
            log_entry = {
                'log_file': entry['log_file'],
                'date': timestamp.strftime('%Y-%m-%d'),
                'time': timestamp.strftime('%H:%M:%S.%f')[:-3],  # Remove last 3 digits
                'datetime': timestamp.strftime('%Y-%m-%d %H:%M:%S.%f'),
                'message': entry['message']
            }
            
            values.append([str(timestamp_ns), json.dumps(log_entry, ensure_ascii=False)])
        
        # Create stream
        stream = {
            "stream": {
                "job": "speed_roulette_error_logs",
                "instance": "GC-ARO-001-1",
                "game_type": "speed",
                "event_type": "error",
                "source": "speed_log_file"
            },
            "values": values
        }
        
        # Prepare payload
        payload = {"streams": [stream]}
        
        # Push to Loki
        response = requests.post(
            LOKI_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code == 204:
            print(f"✅ Successfully pushed {len(filtered_entries)} error log entries to Loki")
            return True
        else:
            print(f"❌ Failed to push to Loki: HTTP {response.status_code}")
            if response.text:
                print(f"   Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: Cannot connect to Loki server at {LOKI_URL}")
        print(f"   Error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout error: Request to Loki server timed out")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error pushing to Loki: {e}")
        import traceback
        traceback.print_exc()
        return False


def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) for graceful shutdown"""
    global running
    print("\n\n⚠️  Received shutdown signal, stopping monitor...")
    running = False


def monitor_log_file(log_file_path: str):
    """
    Continuously monitor log file for new error lines and push to Loki
    Automatically switches to latest log file if a new one is created
    
    Args:
        log_file_path: Path to the log file to monitor
    """
    global running, error_buffer
    
    current_log_file = log_file_path
    
    print(f"🔄 Starting continuous monitoring mode")
    print(f"   Monitoring: {current_log_file}")
    print(f"   Loki Server: {LOKI_URL}")
    print(f"   Check interval: {MONITOR_INTERVAL}s")
    print(f"   Batch size: {BATCH_SIZE} errors")
    print(f"   Press Ctrl+C to stop")
    print("-" * 60)
    
    # Initialize position to end of file if starting fresh
    if load_last_position() == 0:
        try:
            current_size = os.path.getsize(current_log_file)
            save_last_position(current_size, current_log_file)
            print(f"ℹ️  Initializing position at end of file ({current_size} bytes)")
        except Exception as e:
            print(f"⚠️  Could not initialize position: {e}")
    
    error_count = 0
    push_count = 0
    
    try:
        while running:
            # Check if a newer log file exists
            latest_log_file = find_latest_log_file()
            if latest_log_file and latest_log_file != current_log_file:
                print(f"🔄 Newer log file detected: {latest_log_file}")
                print(f"   Switching from: {current_log_file}")
                current_log_file = latest_log_file
                # Reset position when switching files
                save_last_position(0, current_log_file)
            
            # Read new error lines from current log file
            new_errors = read_error_lines(current_log_file)
            
            if new_errors:
                error_count += len(new_errors)
                print(f"📊 Found {len(new_errors)} new error line(s) in {os.path.basename(current_log_file)}")
                
                # Add to buffer
                error_buffer.extend(new_errors)
                
                # Push to Loki if buffer reaches batch size
                if len(error_buffer) >= BATCH_SIZE:
                    print(f"📤 Pushing batch of {len(error_buffer)} error entries to Loki...")
                    if push_errors_to_loki(error_buffer):
                        push_count += len(error_buffer)
                        error_buffer = []  # Clear buffer after successful push
                    else:
                        print(f"⚠️  Failed to push, keeping {len(error_buffer)} entries in buffer")
            
            # Sleep before next check
            time.sleep(MONITOR_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Keyboard interrupt received")
    except Exception as e:
        print(f"\n✗ Error during monitoring: {e}")
        raise
    finally:
        # Push any remaining errors in buffer
        if error_buffer:
            print(f"\n📤 Pushing remaining {len(error_buffer)} error entries...")
            if push_errors_to_loki(error_buffer):
                push_count += len(error_buffer)
                error_buffer = []
        
        print(f"\n📊 Total errors found: {error_count}")
        print(f"📤 Total errors pushed: {push_count}")
        print("👋 Monitor stopped")


def main():
    """Main function - starts continuous monitoring of log file"""
    global running
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Monitor speed log files for ERROR lines and push to Loki"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (don't monitor continuously)"
    )
    
    args = parser.parse_args()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("Speed Roulette Error Log Monitor - Push to Loki Server")
    print("=" * 60)
    print(f"Loki Server: {LOKI_URL}")
    print(f"Log file pattern: {LOG_FILE_PATTERN}")
    print(f"Monitoring interval: {MONITOR_INTERVAL}s")
    print(f"Batch size: {BATCH_SIZE} errors")
    print("-" * 60)
    
    # Find the latest log file
    log_file_path = find_latest_log_file()
    if not log_file_path:
        print(f"✗ Log file not found: {LOG_FILE_PATTERN}")
        print(f"  Searched in: {STUDIO_SDP_DIR}")
        return
    
    print(f"✓ Found latest log file: {log_file_path}")
    print(f"  File modified: {time.ctime(os.path.getmtime(log_file_path))}")
    
    if args.once:
        # Run once mode: read all new errors and push
        print(f"\n🔄 Running in one-time mode...")
        new_errors = read_error_lines(log_file_path)
        if new_errors:
            print(f"📊 Found {len(new_errors)} new error line(s)")
            if push_errors_to_loki(new_errors):
                print(f"✅ Successfully pushed {len(new_errors)} error log entries to Loki")
            else:
                print(f"❌ Failed to push error log entries to Loki")
        else:
            print(f"ℹ️  No new error lines found")
    else:
        # Start continuous monitoring
        try:
            monitor_log_file(log_file_path)
        except Exception as e:
            print(f"✗ Fatal error: {e}")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Monitor stopped successfully")
    print(f"\nYou can query the error logs in Grafana/Loki using:")
    print(f'  {{job="speed_roulette_error_logs"}}')
    print(f'  {{job="speed_roulette_error_logs", game_type="speed"}}')
    print("=" * 60)


if __name__ == "__main__":
    main()
