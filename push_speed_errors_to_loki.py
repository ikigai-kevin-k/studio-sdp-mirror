#!/usr/bin/env python3
"""
Monitor speed_{yyyy-mm-dd}.log files for ERROR|Error|error lines and push to Loki server
Extracts error log entries from last 7 days and pushes to remote Loki server

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
import requests
from datetime import datetime, timedelta
from glob import glob
from typing import List, Dict, Optional

# Import progress bar
try:
    from progress_bar import ProgressBar
    PROGRESS_BAR_AVAILABLE = True
except ImportError:
    PROGRESS_BAR_AVAILABLE = False

# Configuration
LOKI_URL = "http://100.64.0.113:3100/loki/api/v1/push"
STUDIO_SDP_DIR = "/home/rnd/studio-sdp-roulette"
LOG_FILE_PATTERN = "speed_*.log"

# Loki rejects samples older than 7 days (reject_old_samples_max_age: 168h)
# However, Loki also has a dynamic "oldest acceptable timestamp" that changes
# To be safe, we'll process only last 2 days to ensure all entries are accepted
MAX_AGE_DAYS = 2

# Batch size for pushing to Loki (to avoid message size limits)
# Loki has a max message size limit (~4MB), so we'll push in batches
BATCH_SIZE = 1000  # Push 1000 entries at a time


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


def find_speed_log_files() -> List[str]:
    """
    Find speed_{yyyy-mm-dd}.log files from last 7 days
    (We'll filter by timestamp when pushing, not by file date)
    
    Returns:
        list: List of log file paths sorted by date
    """
    # Find all speed_*.log files
    pattern = os.path.join(STUDIO_SDP_DIR, LOG_FILE_PATTERN)
    all_log_files = glob(pattern)
    
    # Filter files from last 7 days
    today = datetime.now().date()
    cutoff_date = today - timedelta(days=7)
    
    log_files = []
    for log_file in all_log_files:
        # Extract date from filename (e.g., speed_2025-11-11.log)
        filename = os.path.basename(log_file)
        try:
            # Extract date part (YYYY-MM-DD)
            date_str = filename.split('_')[1].split('.')[0]
            file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Only include files from last 7 days
            if file_date >= cutoff_date:
                log_files.append(log_file)
        except (IndexError, ValueError) as e:
            # Skip files that don't match expected pattern
            continue
    
    # Sort by date
    log_files.sort()
    return log_files


def extract_error_lines_from_file(log_file_path: str) -> List[Dict]:
    """
    Extract error lines from a log file
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        list: List of error log entries with timestamp and message
    """
    error_lines = []
    
    if not os.path.exists(log_file_path):
        return error_lines
    
    try:
        file_size = os.path.getsize(log_file_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # Estimate total lines
        estimated_lines = max(1, int(file_size / 100))
        
        # Create progress bar if available
        progress = None
        if PROGRESS_BAR_AVAILABLE and file_size_mb > 10:
            progress = ProgressBar(estimated_lines, desc=f"Extracting errors from {os.path.basename(log_file_path)}", width=50)
        
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines_processed = 0
            for line in f:
                lines_processed += 1
                
                # Update progress bar
                if progress:
                    progress.set_current(lines_processed)
                
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
        
        if progress:
            progress.close()
    
    except Exception as e:
        print(f"   ❌ Error reading log file {log_file_path}: {e}")
    
    return error_lines


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
        
        # Push to Loki (don't print here, will be printed by caller)
        
        response = requests.post(
            LOKI_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60
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


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract ERROR lines from speed log files and push to Loki"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (don't monitor continuously)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Speed Roulette Error Log Extractor - Push to Loki Server")
    print("=" * 60)
    print(f"Loki Server: {LOKI_URL}")
    print(f"Log file pattern: {LOG_FILE_PATTERN}")
    print(f"Processing last 7 days of log files")
    print(f"Filtering: Only entries from last 6 hours will be pushed (Loki timestamp limit)")
    print("-" * 60)
    
    # Find speed log files from last 7 days
    log_files = find_speed_log_files()
    
    if not log_files:
        print(f"❌ No speed log files found in the last {MAX_AGE_DAYS} days")
        print(f"   Searched for: {LOG_FILE_PATTERN}")
        return
    
    print(f"📁 Found {len(log_files)} log file(s) from last {MAX_AGE_DAYS} days:")
    for log_file in log_files:
        print(f"   - {os.path.basename(log_file)}")
    
    # Extract error lines from all files
    print(f"\n⏳ Extracting ERROR lines from log files...")
    all_error_entries = []
    
    for i, log_file in enumerate(log_files, 1):
        print(f"\n[{i}/{len(log_files)}] Processing: {os.path.basename(log_file)}...")
        error_lines = extract_error_lines_from_file(log_file)
        all_error_entries.extend(error_lines)
        print(f"   ✅ Found {len(error_lines)} error line(s)")
    
    if not all_error_entries:
        print(f"\n⚠️  No error lines found in any log files")
        return
    
    print(f"\n📊 Total error lines found: {len(all_error_entries)}")
    
    # Push to Loki in batches
    if all_error_entries:
        print(f"\n📤 Pushing error entries to Loki in batches of {BATCH_SIZE}...")
        total_pushed = 0
        total_failed = 0
        
        # Split into batches
        for i in range(0, len(all_error_entries), BATCH_SIZE):
            batch = all_error_entries[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(all_error_entries) + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"\n   Batch {batch_num}/{total_batches}: {len(batch)} entries...")
            if push_errors_to_loki(batch):
                total_pushed += len(batch)
            else:
                total_failed += len(batch)
                print(f"   ⚠️  Batch {batch_num} failed, continuing with next batch...")
        
        print(f"\n📊 Push Summary:")
        print(f"   ✅ Successfully pushed: {total_pushed} entries")
        if total_failed > 0:
            print(f"   ❌ Failed: {total_failed} entries")
        
        if total_pushed > 0:
            print(f"\n✅ Error log entries pushed to Loki successfully")
            print(f"\nYou can query the error logs in Grafana/Loki using:")
            print(f'  {{job="speed_roulette_error_logs"}}')
            print(f'  {{job="speed_roulette_error_logs", game_type="speed"}}')
        else:
            print(f"\n❌ Failed to push any error log entries to Loki")
    else:
        print(f"\n⚠️  No error lines found to push")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

