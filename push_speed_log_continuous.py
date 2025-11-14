#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Continuously monitor speed_{yyyy-mm-dd}.log files and push ALL log entries to Loki server
Continuously watches log files and pushes all log entries (not just errors) to remote Loki server

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
from typing import List, Dict, Optional, Tuple

# Force unbuffered output for real-time logging
if sys.stdout.isatty():
    # If running in terminal, use line buffering
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
else:
    # If running with nohup, flush after each print
    import functools
    original_print = print
    def print(*args, **kwargs):
        original_print(*args, **kwargs)
        sys.stdout.flush()
        sys.stderr.flush()

# Configuration
LOKI_URL = "http://100.64.0.113:3100/loki/api/v1/push"
STUDIO_SDP_DIR = "/home/rnd/studio-sdp-roulette"
LOG_FILE_PATTERN = "speed_*.log"
# Current log file (main_speed.py writes to this)
CURRENT_LOG_FILE = os.path.join(STUDIO_SDP_DIR, "logs", "sdp_serial.log")

# State file to track last read position in log file
POSITION_FILE = os.path.join(STUDIO_SDP_DIR, ".last_position_speed_logs.json")

# Monitoring interval in seconds
MONITOR_INTERVAL = 5.0  # Check every 5 seconds

# Batch size for pushing to Loki (push when we have this many log entries)
BATCH_SIZE = 10  # Push 10 log entries at a time (reduced for faster updates)

# Maximum batch size in bytes (to avoid exceeding 4MB gRPC message limit)
MAX_BATCH_SIZE_BYTES = 3 * 1024 * 1024  # 3MB max per batch

# Log line pattern: [YYYY-MM-DD HH:MM:SS.mmm] <type> >>> <message>
LOG_PATTERN = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\]\s+(\w+)\s+(>>>|<<<)\s+(.*)$'
)

# Global flag for graceful shutdown
running = True

# Global buffer for log entries
log_buffer: List[Dict] = []


def signal_handler(sig, frame):
    """Handle SIGINT and SIGTERM signals for graceful shutdown"""
    global running
    print("\n\n⚠️  Shutdown signal received, stopping monitor...")
    running = False


def find_latest_log_file() -> Optional[str]:
    """
    Find the latest log file to monitor
    Priority: 1) logs/sdp_serial.log (current), 2) speed_{yyyy-mm-dd}.log files (legacy)
    
    Returns:
        str: Path to the latest log file, or None if not found
    """
    # First, check if current log file exists (main_speed.py writes here)
    if os.path.exists(CURRENT_LOG_FILE):
        return CURRENT_LOG_FILE
    
    # Fallback to date-split log files (legacy)
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


def parse_log_line(line: str) -> Optional[Tuple[datetime, str, str, str]]:
    """
    Parse a log line and extract timestamp, type, direction, and message
    
    Args:
        line: Log line to parse
        
    Returns:
        Tuple of (datetime, log_type, direction, message) or None if parsing fails
    """
    line = line.strip()
    if not line:
        return None
    
    match = LOG_PATTERN.match(line)
    if not match:
        return None
    
    timestamp_str, log_type, direction, message = match.groups()
    
    try:
        # Parse timestamp: YYYY-MM-DD HH:MM:SS.mmm
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        return (dt, log_type, direction, message)
    except ValueError:
        return None


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


def find_recent_log_position(log_file_path: str, hours_back: int = 6) -> int:
    """
    Find the file position corresponding to logs from the last N hours
    Uses binary search to find the position efficiently
    
    Args:
        log_file_path: Path to the log file
        hours_back: Number of hours to look back (default: 6)
        
    Returns:
        int: File position, or file size if no recent logs found
    """
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        file_size = os.path.getsize(log_file_path)
        
        # If file is small, just return file size (start from end)
        if file_size < 10000:  # Less than 10KB
            return file_size
        
        # Binary search for the position
        # Start from end and work backwards
        chunk_size = min(1024 * 1024, file_size // 10)  # 1MB chunks or 10% of file
        position = max(0, file_size - chunk_size)
        
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Try to find a line with timestamp >= cutoff_time
            for _ in range(10):  # Limit to 10 iterations
                f.seek(position)
                # Skip partial line
                if position > 0:
                    f.readline()
                
                # Read a few lines to find timestamp
                for _ in range(100):  # Read up to 100 lines
                    line = f.readline()
                    if not line:
                        break
                    
                    parsed = parse_log_line(line)
                    if parsed:
                        dt, _, _, _ = parsed
                        if dt >= cutoff_time:
                            # Found recent log, return this position
                            return position
                
                # Move backwards
                position = max(0, position - chunk_size)
                if position == 0:
                    break
        
        # If we can't find recent logs, start from end
        return file_size
    except Exception as e:
        print(f"⚠️  Error finding recent log position: {e}, starting from end of file")
        return os.path.getsize(log_file_path)


def read_new_log_lines(log_file_path: str) -> List[Dict]:
    """
    Read new log lines from log file since last read position
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        list: List of log entries with timestamp and message
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
        
        # Check if saved position is too old (more than 6 hours)
        # If so, find a recent position instead
        if last_position > 0 and last_position < current_size:
            try:
                with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(max(0, last_position - 1000))  # Read a bit before saved position
                    # Skip partial line
                    if last_position > 1000:
                        f.readline()
                    
                    # Read a few lines to check timestamp
                    for _ in range(10):
                        line = f.readline()
                        if not line:
                            break
                        parsed = parse_log_line(line)
                        if parsed:
                            dt, _, _, _ = parsed
                            cutoff_time = datetime.now() - timedelta(hours=6)
                            if dt < cutoff_time:
                                # Saved position is too old, find recent position
                                print(f"⚠️  Saved position is too old (timestamp: {dt}), finding recent position...")
                                last_position = find_recent_log_position(log_file_path, hours_back=6)
                                break
            except Exception as e:
                print(f"⚠️  Error checking saved position: {e}, using saved position")
        
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
        
        # Split into lines and parse
        log_entries = []
        new_lines = new_content.strip().split('\n')
        
        for line in new_lines:
            if not line.strip():
                continue
            
            # Parse log line
            parsed = parse_log_line(line)
            if parsed:
                dt, log_type, direction, message = parsed
                log_entries.append({
                    'timestamp': dt,
                    'type': log_type,
                    'direction': direction,
                    'message': message,
                    'raw_line': line.strip(),
                    'log_file': os.path.basename(log_file_path)
                })
        
        return log_entries
        
    except Exception as e:
        print(f"✗ Error reading log file: {e}")
        return []


def push_logs_to_loki(log_entries: List[Dict]) -> bool:
    """
    Push log entries to Loki server
    
    Args:
        log_entries: List of log entries with timestamp and message
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not log_entries:
        return True
    
    try:
        # Filter out entries that are too old
        # Loki has a dynamic "oldest acceptable timestamp" that changes based on current time
        # From error messages, Loki typically only accepts entries from the last 6 hours
        # To be safe, we'll only keep entries from the last 6 hours
        cutoff_time = datetime.now() - timedelta(hours=6)
        # Also filter out entries more than 1 hour in the future
        future_threshold = datetime.now() + timedelta(hours=1)
        
        filtered_entries = []
        skipped_old = 0
        skipped_future = 0
        
        for entry in log_entries:
            timestamp = entry['timestamp']
            if timestamp < cutoff_time:
                skipped_old += 1
                continue
            if timestamp > future_threshold:
                skipped_future += 1
                continue
            filtered_entries.append(entry)
        
        if skipped_old > 0:
            print(f"   ⚠️  Skipped {skipped_old} entries older than 6 hours (Loki rejects old samples)")
        if skipped_future > 0:
            print(f"   ⚠️  Skipped {skipped_future} entries with future timestamps")
        
        if not filtered_entries:
            return True
        
        # Extract date from log file for better organization
        log_file = filtered_entries[0].get('log_file', 'unknown')
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', log_file)
        log_date = date_match.group(1) if date_match else "unknown"
        
        # Prepare Loki payload
        values = []
        for entry in filtered_entries:
            timestamp = entry['timestamp']
            timestamp_ns = int(timestamp.timestamp() * 1000000000)  # nanoseconds
            
            # Create structured log entry as JSON
            log_entry = {
                "timestamp": timestamp.isoformat(),
                "type": entry['type'],
                "direction": entry['direction'],
                "message": entry['message'],
                "raw_line": entry['raw_line']
            }
            log_message = json.dumps(log_entry, ensure_ascii=False)
            
            values.append([str(timestamp_ns), log_message])
        
        # Prepare stream
        stream = {
            "stream": {
                "job": "speed_roulette_logs",
                "instance": "GC-ARO-001-1",
                "game_type": "speed",
                "log_type": "application_log",
                "source": "speed_log_file",
                "log_date": log_date
            },
            "values": values
        }
        
        # Check payload size
        payload = {"streams": [stream]}
        payload_size = len(json.dumps(payload).encode('utf-8'))
        if payload_size > MAX_BATCH_SIZE_BYTES:
            print(
                f"   ⚠️  Warning: Batch size is {payload_size / 1024 / 1024:.2f}MB "
                f"(exceeds {MAX_BATCH_SIZE_BYTES / 1024 / 1024:.2f}MB limit)"
            )
            # Split into smaller batches if needed
            return push_logs_to_loki_in_batches(filtered_entries, log_date)
        
        # Push to Loki
        try:
            response = requests.post(
                LOKI_URL,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60
            )
            
            if response.status_code == 204:
                return True
            else:
                print(f"   ❌ Failed to push to Loki: HTTP {response.status_code}")
                if response.text:
                    print(f"      Response: {response.text[:500]}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            print(f"   ❌ Connection error: Cannot connect to Loki server at {LOKI_URL}")
            print(f"      Error: {e}")
            return False
        except requests.exceptions.Timeout as e:
            print(f"   ❌ Timeout error: Request to Loki server timed out")
            print(f"      Error: {e}")
            return False
        except Exception as e:
            print(f"   ❌ Error pushing to Loki: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Error preparing logs for Loki: {e}")
        import traceback
        traceback.print_exc()
        return False


def push_logs_to_loki_in_batches(log_entries: List[Dict], log_date: str) -> bool:
    """
    Push log entries to Loki in smaller batches to avoid size limits
    
    Args:
        log_entries: List of log entries
        log_date: Date string from log filename
        
    Returns:
        bool: True if all batches successful, False otherwise
    """
    # Split into smaller batches
    batch_size = 50  # Smaller batch size
    all_success = True
    
    for i in range(0, len(log_entries), batch_size):
        batch = log_entries[i:i + batch_size]
        if not push_logs_to_loki(batch):
            all_success = False
    
    return all_success


def monitor_log_file(log_file_path: str):
    """
    Continuously monitor log file for new log lines and push to Loki
    Automatically switches to latest log file if a new one is created
    
    Args:
        log_file_path: Path to the log file to monitor
    """
    global running, log_buffer
    
    current_log_file = log_file_path
    
    print(f"🔄 Starting continuous monitoring mode")
    print(f"   Monitoring: {current_log_file}")
    print(f"   Loki Server: {LOKI_URL}")
    print(f"   Check interval: {MONITOR_INTERVAL}s")
    print(f"   Batch size: {BATCH_SIZE} log entries")
    print(f"   Press Ctrl+C to stop")
    print("-" * 60)
    
    # Initialize position to end of file if starting fresh
    if load_last_position() == 0:
        try:
            current_size = os.path.getsize(current_log_file)
            save_last_position(current_size, current_log_file)
            print(f"ℹ️  Initializing position at end of file ({current_size} bytes)")
            print(f"   (Only new log entries will be pushed)")
        except Exception as e:
            print(f"⚠️  Could not initialize position: {e}")
    
    log_count = 0
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
            
            # Read new log lines from current log file
            new_logs = read_new_log_lines(current_log_file)
            
            if new_logs:
                log_count += len(new_logs)
                print(f"📊 Found {len(new_logs)} new log line(s) in {os.path.basename(current_log_file)}")
                
                # Add to buffer
                log_buffer.extend(new_logs)
                
                # Push to Loki if buffer reaches batch size
                if len(log_buffer) >= BATCH_SIZE:
                    print(f"📤 Pushing batch of {len(log_buffer)} log entries to Loki...")
                    if push_logs_to_loki(log_buffer):
                        push_count += len(log_buffer)
                        log_buffer = []  # Clear buffer after successful push
                        print(f"   ✅ Successfully pushed batch")
                    else:
                        print(f"   ⚠️  Failed to push, keeping {len(log_buffer)} entries in buffer")
            
            # Sleep before next check
            time.sleep(MONITOR_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Keyboard interrupt received")
    except Exception as e:
        print(f"\n✗ Error during monitoring: {e}")
        raise
    finally:
        # Push any remaining logs in buffer
        if log_buffer:
            print(f"\n📤 Pushing remaining {len(log_buffer)} log entries...")
            if push_logs_to_loki(log_buffer):
                push_count += len(log_buffer)
                log_buffer = []
                print(f"   ✅ Successfully pushed remaining entries")
        
        print(f"\n📊 Summary:")
        print(f"   Total log entries read: {log_count}")
        print(f"   Total log entries pushed: {push_count}")
        print("👋 Monitor stopped")


def main():
    """Main function - starts continuous monitoring of log file"""
    global running
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("Speed Roulette Log Monitor - Push to Loki Server")
    print("=" * 60)
    print(f"Loki Server: {LOKI_URL}")
    print()
    
    # Find latest log file
    log_file = find_latest_log_file()
    if not log_file:
        print("❌ No speed log files found!")
        print(f"\nExpected files in: {STUDIO_SDP_DIR}")
        print(f"   Pattern: {LOG_FILE_PATTERN}")
        return
    
    print(f"📋 Found latest log file: {os.path.basename(log_file)}")
    print()
    
    # Start monitoring
    try:
        monitor_log_file(log_file)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()



