#!/usr/bin/env python3
"""
Monitor vip_{yyyy-mm-dd}.log files for ERROR|Error|error lines and push to Loki server
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
LOG_FILE_PATTERN = "vip_*.log"

# State file to track last read position in log file
POSITION_FILE = os.path.join(STUDIO_SDP_DIR, ".last_position_vip_errors.json")

# Monitoring interval in seconds
MONITOR_INTERVAL = 5.0  # Check every 5 seconds

# Batch size for pushing to Loki (push when we have this many errors)
BATCH_SIZE = 10

# Global flag for graceful shutdown
running = True

# Global buffer for error logs
error_buffer: List[Dict] = []


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


def find_latest_log_file() -> Optional[str]:
    """
    Find the latest vip_{yyyy-mm-dd}.log file
    
    Returns:
        str: Path to the latest log file, or None if not found
    """
    # Find all vip_*.log files matching pattern vip_{yyyy-mm-dd}.log
    pattern = os.path.join(STUDIO_SDP_DIR, LOG_FILE_PATTERN)
    all_log_files = glob(pattern)
    
    # Filter to only match vip_{yyyy-mm-dd}.log format (e.g., vip_2025-11-11.log)
    log_files = []
    for file_path in all_log_files:
        filename = os.path.basename(file_path)
        # Match pattern: vip_YYYY-MM-DD.log
        if re.match(r'^vip_\d{4}-\d{2}-\d{2}\.log$', filename):
            log_files.append(file_path)
    
    if not log_files:
        return None
    
    # Sort by modification time and return the latest
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return log_files[0]


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
        # Prepare Loki payload
        values = []
        for entry in error_entries:
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
                "job": "vip_roulette_error_logs",
                "instance": "GC-ARO-002-1",
                "game_type": "vip",
                "event_type": "error",
                "source": "vip_log_file"
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
            print(f"✅ Successfully pushed {len(error_entries)} error log entries to Loki")
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
    print(f"   Check interval: {MONITOR_INTERVAL} seconds")
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
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("VIP Roulette Error Log Monitor - Push to Loki Server")
    print("=" * 60)
    print(f"Loki Server: {LOKI_URL}")
    print(f"Log file pattern: {LOG_FILE_PATTERN}")
    print(f"Log directory: {STUDIO_SDP_DIR}")
    print(f"Monitoring interval: {MONITOR_INTERVAL}s")
    print(f"Batch size: {BATCH_SIZE} errors")
    print("-" * 60)
    
    # Find the latest log file
    log_file_path = find_latest_log_file()
    if not log_file_path:
        print(f"✗ Log file not found: {LOG_FILE_PATTERN}")
        print(f"  Searched in directory: {STUDIO_SDP_DIR}")
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
    print(f"\nYou can query the error logs in Grafana/Loki using:")
    print(f'  {{job="vip_roulette_error_logs"}}')
    print(f'  {{job="vip_roulette_error_logs", game_type="vip"}}')
    print("=" * 60)


if __name__ == "__main__":
    main()

