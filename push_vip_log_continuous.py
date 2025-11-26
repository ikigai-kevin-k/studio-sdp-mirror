#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Continuously monitor vip_{yyyy-mm-dd}.log files and push ALL log entries to Loki server
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

# Import environment detection module
from env_detect import detect_environment, get_hostname

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
LOG_FILE_PATTERN = "vip_*.log"

# Detect environment and get hostname for Loki instance
detected_table_code, detected_hostname, env_detection_success = detect_environment()
if env_detection_success and detected_hostname:
    LOKI_INSTANCE = detected_hostname
else:
    # Fallback to default if detection fails
    LOKI_INSTANCE = get_hostname() or "GC-ARO-002-1"
    if not env_detection_success:
        print(
            f"⚠️  Environment detection failed, using hostname '{LOKI_INSTANCE}' "
            f"as Loki instance"
        )

# State file to track last read position in log file
POSITION_FILE = os.path.join(STUDIO_SDP_DIR, ".last_position_vip_logs.json")

# State file to track last read position in self-test-2api.log for syncing
SELF_TEST_POSITION_FILE = os.path.join(STUDIO_SDP_DIR, ".last_position_self_test_sync.json")

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


def sync_today_logs_from_self_test(today_log_file: str) -> int:
    """
    Sync today's logs from self-test-2api.log to vip_{today}.log file
    Only appends new logs that haven't been synced yet
    
    Args:
        today_log_file: Path to today's log file (vip_{today}.log)
        
    Returns:
        int: Number of new log lines synced
    """
    current_log_file = os.path.join(STUDIO_SDP_DIR, "self-test-2api.log")
    
    # Check if self-test-2api.log exists
    if not os.path.exists(current_log_file):
        return 0
    
    try:
        today_date = datetime.now().date()
        lines_synced = 0
        
        # Load last sync position
        last_sync_position = 0
        if os.path.exists(SELF_TEST_POSITION_FILE):
            try:
                with open(SELF_TEST_POSITION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    last_sync_position = data.get('position', 0)
            except:
                pass
        
        # Get current file size
        current_size = os.path.getsize(current_log_file)
        
        # If file was truncated or is smaller, reset position
        if current_size < last_sync_position:
            print("⚠️  self-test-2api.log appears to have been rotated or truncated, resetting sync position")
            last_sync_position = 0
        
        # If no new content, return
        if current_size <= last_sync_position:
            return 0
        
        # Read new content from self-test-2api.log
        with open(current_log_file, 'r', encoding='utf-8', errors='ignore') as f_in:
            f_in.seek(last_sync_position)
            new_content = f_in.read()
        
        # Append today's logs to vip_{today}.log
        if new_content.strip():
            with open(today_log_file, 'a', encoding='utf-8') as f_out:
                for line in new_content.split('\n'):
                    if not line.strip():
                        continue
                    
                    # Parse log line to check date
                    parsed = parse_log_line(line)
                    if parsed:
                        dt, _, _, _ = parsed
                        if dt.date() == today_date:
                            f_out.write(line + '\n')
                            lines_synced += 1
        
        # Save new sync position
        try:
            with open(SELF_TEST_POSITION_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'position': current_size,
                    'last_sync': datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
        
        return lines_synced
    except Exception as e:
        print(f"⚠️  Error syncing today's logs: {e}")
        return 0


def find_today_start_position(log_file_path: str, today_date: datetime.date) -> int:
    """
    Find the file position where today's logs start
    Optimized: reads from end backwards to find today's first log
    
    Args:
        log_file_path: Path to the log file
        today_date: Today's date
        
    Returns:
        int: File position where today's logs start, or file size if not found
    """
    try:
        file_size = os.path.getsize(log_file_path)
        
        # If file is small, just return 0 (read from beginning)
        if file_size < 10000:  # Less than 10KB
            return 0
        
        # Try multiple search strategies:
        # 1. Read last 200MB (most common case - today's logs at end)
        # 2. If not found, read last 500MB
        # 3. If still not found, read last 1GB
        # 4. If still not found, read entire file (fallback)
        
        search_sizes = [
            200 * 1024 * 1024,  # 200MB
            500 * 1024 * 1024,  # 500MB
            1024 * 1024 * 1024,  # 1GB
            file_size  # Entire file as last resort
        ]
        
        earliest_today_position = file_size
        found_today = False
        
        for search_size in search_sizes:
            if search_size > file_size:
                search_size = file_size
            
            start_position = max(0, file_size - search_size)
            
            print(f"   Searching in last {search_size / (1024*1024):.0f}MB (position {start_position:,} to {file_size:,})...")
            
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(start_position)
                # Skip partial line
                if start_position > 0:
                    f.readline()
                
                lines_checked = 0
                # Read lines and find today's first log
                for _ in range(200000):  # Read up to 200k lines per search
                    line_pos = f.tell()
                    line = f.readline()
                    if not line:
                        break
                    
                    lines_checked += 1
                    parsed = parse_log_line(line)
                    if parsed:
                        dt, _, _, _ = parsed
                        if dt.date() == today_date:
                            found_today = True
                            earliest_today_position = min(earliest_today_position, line_pos)
                            # Continue to find the earliest one
                        elif dt.date() < today_date and found_today:
                            # We found today's logs and now we're past them
                            # Found the earliest position
                            print(f"   Found today's logs starting at position {earliest_today_position:,} (checked {lines_checked:,} lines)")
                            return earliest_today_position
                        elif dt.date() > today_date:
                            # Future date, skip
                            continue
                
                if found_today:
                    print(f"   Found today's logs starting at position {earliest_today_position:,} (checked {lines_checked:,} lines)")
                    # Try to find the very first today log by searching backwards
                    if earliest_today_position > start_position:
                        # Search backwards from earliest position
                        search_back = min(50 * 1024 * 1024, earliest_today_position)  # Search back 50MB
                        search_start = max(0, earliest_today_position - search_back)
                        
                        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f2:
                            f2.seek(search_start)
                            if search_start > 0:
                                f2.readline()  # Skip partial line
                            
                            # Read forward to find the first today log
                            for _ in range(50000):  # Read up to 50k lines
                                line_pos = f2.tell()
                                if line_pos >= earliest_today_position:
                                    break
                                
                                line = f2.readline()
                                if not line:
                                    break
                                
                                parsed = parse_log_line(line)
                                if parsed:
                                    dt, _, _, _ = parsed
                                    if dt.date() == today_date:
                                        earliest_today_position = min(earliest_today_position, line_pos)
                                    elif dt.date() > today_date:
                                        # Past today, stop
                                        break
                    
                    return earliest_today_position
                else:
                    # Not found in this chunk, try larger search
                    if search_size >= file_size:
                        # Already searched entire file, give up
                        break
                    continue
        
        # If we get here, we didn't find today's logs
        print(f"   ⚠️  No logs found for today ({today_date}) in searched areas")
        return file_size
    except Exception as e:
        print(f"⚠️  Error finding today's start position: {e}, using fallback")
        import traceback
        traceback.print_exc()
        # Fallback: read from last 200MB
        file_size = os.path.getsize(log_file_path)
        return max(0, file_size - 200 * 1024 * 1024)  # Last 200MB


def extract_today_logs_from_self_test() -> bool:
    """
    Extract today's logs from self-test-2api.log and create vip_{today}.log file
    Optimized to only read from today's start position instead of entire file
    
    Returns:
        bool: True if successful, False otherwise
    """
    today = datetime.now().strftime("%Y-%m-%d")
    today_log_file = os.path.join(STUDIO_SDP_DIR, f"vip_{today}.log")
    current_log_file = os.path.join(STUDIO_SDP_DIR, "self-test-2api.log")
    
    # Check if self-test-2api.log exists
    if not os.path.exists(current_log_file):
        return False
    
    try:
        today_date = datetime.now().date()
        lines_written = 0
        current_size = os.path.getsize(current_log_file)
        
        # Find the position where today's logs start (much faster than reading entire file)
        print(f"   Finding today's log start position in {current_log_file}...")
        start_position = find_today_start_position(current_log_file, today_date)
        
        if start_position >= current_size:
            # No logs found for today in search, but try reading last 200MB anyway
            # to make sure we don't miss anything
            print(f"   ⚠️  Today's start position not found, reading last 200MB as fallback...")
            start_position = max(0, current_size - 200 * 1024 * 1024)
        
        print(f"   Reading from position {start_position:,} bytes (today's logs start here)")
        
        # Read only from today's start position to end of file
        first_date_found = None
        last_date_found = None
        with open(current_log_file, 'r', encoding='utf-8', errors='ignore') as f_in:
            f_in.seek(start_position)
            with open(today_log_file, 'w', encoding='utf-8') as f_out:
                line_count = 0
                for line in f_in:
                    line_count += 1
                    # Show progress every 50k lines
                    if line_count % 50000 == 0:
                        print(f"   Processed {line_count:,} lines, found {lines_written:,} today logs...")
                    
                    # Parse log line to check date
                    parsed = parse_log_line(line)
                    if parsed:
                        dt, _, _, _ = parsed
                        date = dt.date()
                        
                        # Track date range for debugging
                        if first_date_found is None:
                            first_date_found = date
                        last_date_found = date
                        
                        if date == today_date:
                            f_out.write(line)
                            lines_written += 1
                        elif date > today_date:
                            # Past today, stop reading
                            break
                
                # Show date range found for debugging
                if first_date_found:
                    print(f"   Date range in read section: {first_date_found} to {last_date_found}")
                    if first_date_found > today_date:
                        print(f"   ⚠️  Warning: First date found ({first_date_found}) is after today ({today_date})")
                    elif last_date_found < today_date:
                        print(f"   ⚠️  Warning: Last date found ({last_date_found}) is before today ({today_date})")
        
        # Save sync position
        try:
            with open(SELF_TEST_POSITION_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'position': current_size,
                    'last_sync': datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
        
        if lines_written > 0:
            print(f"📝 Created {today_log_file} with {lines_written} log entries from self-test-2api.log")
        else:
            # Create empty file if no logs found for today
            with open(today_log_file, 'w', encoding='utf-8') as f:
                pass
            print(f"📝 Created empty {today_log_file} (no logs found for today in self-test-2api.log)")
        
        return True
    except Exception as e:
        print(f"⚠️  Error extracting today's logs: {e}")
        return False


def find_latest_log_file() -> Optional[str]:
    """
    Find the latest log file to monitor
    Priority: 1) vip_{today}.log (current day), 2) create it from self-test-2api.log if needed, 3) self-test-2api.log (current), 4) latest vip_{yyyy-mm-dd}.log (legacy)
    
    Returns:
        str: Path to the latest log file, or None if not found
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # First, check if today's log file exists (vip_{today}.log)
    today_log_file = os.path.join(STUDIO_SDP_DIR, f"vip_{today}.log")
    if os.path.exists(today_log_file):
        # Check if file is empty or very small (less than 100 bytes)
        # Only re-extract if file is truly empty or very small
        file_size = os.path.getsize(today_log_file)
        if file_size < 100:
            print(f"📋 Today's log file ({os.path.basename(today_log_file)}) exists but is empty or very small")
            print(f"   Note: Will monitor existing file. Use generate_today_vip_log.py to regenerate from logs/sdp_serial.log")
        # Return the existing file even if small - don't overwrite it
        return today_log_file
    
    # Second, if today's file doesn't exist, try to create it from self-test-2api.log
    current_log_file = os.path.join(STUDIO_SDP_DIR, "self-test-2api.log")
    if os.path.exists(current_log_file):
        print(f"📋 Today's log file ({os.path.basename(today_log_file)}) not found")
        print(f"   Extracting today's logs from self-test-2api.log...")
        if extract_today_logs_from_self_test():
            # File created, return it
            return today_log_file
        else:
            # Failed to extract, fall back to monitoring self-test-2api.log
            return current_log_file
    
    # Fallback to date-split log files (legacy)
    # Find all vip_*.log files matching pattern vip_{yyyy-mm-dd}.log
    pattern = os.path.join(STUDIO_SDP_DIR, LOG_FILE_PATTERN)
    found_files = glob(pattern)
    
    # Filter to only match vip_{yyyy-mm-dd}.log format (e.g., vip_2025-11-11.log)
    log_files = []
    for file_path in found_files:
        filename = os.path.basename(file_path)
        # Match pattern: vip_YYYY-MM-DD.log
        match = re.match(r'^vip_(\d{4}-\d{2}-\d{2})\.log$', filename)
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
                            cutoff_time = datetime.now() - timedelta(hours=2)
                            if dt < cutoff_time:
                                # Saved position is too old, find recent position
                                print(f"⚠️  Saved position is too old (timestamp: {dt}), finding recent position...")
                                last_position = find_recent_log_position(log_file_path, hours_back=2)
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
        
        # If monitoring self-test-2api.log, only include today's logs
        today = datetime.now().date()
        is_self_test_log = os.path.basename(log_file_path) == "self-test-2api.log"
        
        for line in new_lines:
            if not line.strip():
                continue
            
            # Parse log line
            parsed = parse_log_line(line)
            if parsed:
                dt, log_type, direction, message = parsed
                
                # If monitoring self-test-2api.log, filter to only today's logs
                if is_self_test_log and dt.date() != today:
                    continue
                
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
            print(f"   ⚠️  Skipped {skipped_old} entries older than 2 hours (Loki rejects old samples)")
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
                "job": "vip_roulette_logs",
                "instance": LOKI_INSTANCE,
                "game_type": "vip",
                "log_type": "application_log",
                "source": "vip_log_file",
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
        # Directly push without size check to avoid recursion
        if not _push_logs_to_loki_direct(batch, log_date):
            all_success = False
    
    return all_success


def _push_logs_to_loki_direct(log_entries: List[Dict], log_date: str) -> bool:
    """
    Directly push log entries to Loki without size checking
    (Internal function used by push_logs_to_loki_in_batches)
    
    Args:
        log_entries: List of log entries with timestamp and message
        log_date: Date string from log filename
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not log_entries:
        return True
    
    try:
        # Prepare Loki payload
        values = []
        for entry in log_entries:
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
                "job": "vip_roulette_logs",
                "instance": LOKI_INSTANCE,
                "game_type": "vip",
                "log_type": "application_log",
                "source": "vip_log_file",
                "log_date": log_date
            },
            "values": values
        }
        
        # Prepare payload
        payload = {"streams": [stream]}
        
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
                print(f"   ❌ Failed to push batch to Loki: HTTP {response.status_code}")
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
            print(f"   ❌ Error pushing batch to Loki: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Error preparing batch for Loki: {e}")
        return False


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
    print(f"   Loki Instance: {LOKI_INSTANCE}")
    print(f"   Check interval: {MONITOR_INTERVAL}s")
    print(f"   Batch size: {BATCH_SIZE} log entries")
    print(f"   Press Ctrl+C to stop")
    print("-" * 60)
    
    # Initialize position
    saved_data = {}
    if os.path.exists(POSITION_FILE):
        try:
            with open(POSITION_FILE, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
        except:
            pass
    
    # Check if we're monitoring a different file or starting fresh
    saved_log_file = saved_data.get('log_file')
    if saved_log_file != current_log_file or load_last_position() == 0:
        try:
            current_size = os.path.getsize(current_log_file)
            
            # If monitoring today's log file and it's a different file, 
            # find position for today's logs
            today = datetime.now().strftime("%Y-%m-%d")
            today_log_file = os.path.join(STUDIO_SDP_DIR, f"vip_{today}.log")
            if current_log_file == today_log_file:
                # Find position for today's logs (last 2 hours)
                initial_position = find_recent_log_position(current_log_file, hours_back=2)
                save_last_position(initial_position, current_log_file)
                print(f"ℹ️  Initializing position for today's logs ({initial_position} bytes)")
            else:
                # For date-split files, start from end
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
                
                # Initialize position when switching files
                try:
                    current_size = os.path.getsize(current_log_file)
                    # If switching to today's log file, find position for today's logs
                    today = datetime.now().strftime("%Y-%m-%d")
                    today_log_file = os.path.join(STUDIO_SDP_DIR, f"vip_{today}.log")
                    if current_log_file == today_log_file:
                        initial_position = find_recent_log_position(current_log_file, hours_back=2)
                        save_last_position(initial_position, current_log_file)
                        print(f"   Initialized position for today's logs ({initial_position} bytes)")
                    else:
                        # For other files, start from end
                        save_last_position(current_size, current_log_file)
                        print(f"   Initialized position at end of file ({current_size} bytes)")
                except Exception as e:
                    print(f"   ⚠️  Could not initialize position: {e}, starting from beginning")
                    save_last_position(0, current_log_file)
            
            # If monitoring today's log file, sync new logs from self-test-2api.log
            today = datetime.now().strftime("%Y-%m-%d")
            today_log_file = os.path.join(STUDIO_SDP_DIR, f"vip_{today}.log")
            if current_log_file == today_log_file:
                synced_lines = sync_today_logs_from_self_test(today_log_file)
                if synced_lines > 0:
                    print(f"🔄 Synced {synced_lines} new log line(s) from self-test-2api.log to {os.path.basename(today_log_file)}")
            
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
    print("VIP Roulette Log Monitor - Push to Loki Server")
    print("=" * 60)
    print(f"Loki Server: {LOKI_URL}")
    print(f"Loki Instance: {LOKI_INSTANCE}")
    if env_detection_success:
        print(f"Detected Table Code: {detected_table_code}")
    print()
    
    # Find latest log file
    log_file = find_latest_log_file()
    if not log_file:
        print("❌ No VIP log files found!")
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

