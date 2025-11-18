#!/usr/bin/env python3
"""
Push speed log files to remote Loki server
Reads speed_yyyy-mm-dd.log files and pushes log entries to Loki

Based on Loki server settings from loki.md:
- Server: http://100.64.0.113:3100
- Endpoint: /loki/api/v1/push
- Port: 3100
"""

import os
import sys
import json
import re
import time
import requests
import glob
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

# Import environment detection module
from env_detect import detect_environment, get_hostname

# Import progress bar
try:
    from progress_bar import ProgressBar
    PROGRESS_BAR_AVAILABLE = True
except ImportError:
    PROGRESS_BAR_AVAILABLE = False


# Configuration from loki.md
LOKI_URL = "http://100.64.0.113:3100/loki/api/v1/push"
STUDIO_SDP_DIR = "/home/rnd/studio-sdp-roulette"

# Detect environment and get hostname for Loki instance
detected_table_code, detected_hostname, env_detection_success = detect_environment()
if env_detection_success and detected_hostname:
    LOKI_INSTANCE = detected_hostname
else:
    # Fallback to default if detection fails
    LOKI_INSTANCE = get_hostname() or "GC-ARO-001-1"
    if not env_detection_success:
        print(
            f"⚠️  Environment detection failed, using hostname '{LOKI_INSTANCE}' "
            f"as Loki instance"
        )

# Only push logs from the last week (7 days)
# Loki rejects samples older than 7 days (reject_old_samples_max_age: 168h)
# We'll filter out entries older than 7 days
MAX_AGE_DAYS = 7

# Batch size for pushing to Loki (to avoid exceeding 4MB gRPC message limit)
# Each batch should be small enough to stay under 3MB to be safe
BATCH_SIZE = 1000  # Number of log entries per batch
MAX_BATCH_SIZE_BYTES = 3 * 1024 * 1024  # 3MB max per batch

# Log line pattern: [YYYY-MM-DD HH:MM:SS.mmm] <type> >>> <message>
LOG_PATTERN = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\]\s+(\w+)\s+(>>>|<<<)\s+(.*)$'
)


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


def find_latest_speed_log() -> Optional[str]:
    """
    Find the latest speed_yyyy-mm-dd.log file
    
    Returns:
        Path to latest log file or None if not found
    """
    pattern = os.path.join(STUDIO_SDP_DIR, "speed_*.log")
    log_files = glob.glob(pattern)
    
    if not log_files:
        return None
    
    # Sort by modification time, newest first
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return log_files[0]


def push_batch_to_loki(
    batch_values: List[List[str]],
    game_type: str,
    log_date: str,
    batch_num: int,
    total_batches: int
) -> bool:
    """
    Push a single batch of log entries to Loki server
    
    Args:
        batch_values: List of [timestamp, message] pairs
        game_type: Game type ("speed" or "vip")
        log_date: Date string from log filename
        batch_num: Current batch number (1-indexed)
        total_batches: Total number of batches
        
    Returns:
        True if successful, False otherwise
    """
    if not batch_values:
        return True
    
    try:
        # Extract date from filename for better organization
        stream = {
            "stream": {
                "job": f"{game_type}_roulette_logs",
                "instance": LOKI_INSTANCE,
                "game_type": game_type,
                "log_type": "application_log",
                "source": "speed_log_file",
                "log_date": log_date
            },
            "values": batch_values
        }
        
        # Prepare payload
        payload = {"streams": [stream]}
        
        # Check payload size
        payload_size = len(json.dumps(payload).encode('utf-8'))
        if payload_size > MAX_BATCH_SIZE_BYTES:
            print(
                f"   ⚠️  Warning: Batch {batch_num} size is {payload_size / 1024 / 1024:.2f}MB "
                f"(exceeds {MAX_BATCH_SIZE_BYTES / 1024 / 1024:.2f}MB limit)"
            )
        
        response = requests.post(
            LOKI_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60  # Timeout for each batch
        )
        
        if response.status_code == 204:
            return True
        else:
            print(f"   ❌ Failed to push batch {batch_num}/{total_batches}: HTTP {response.status_code}")
            if response.text:
                print(f"      Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection error in batch {batch_num}: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"   ❌ Timeout error in batch {batch_num}: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error pushing batch {batch_num}: {e}")
        return False


def push_log_to_loki(log_path: str, game_type: str = "speed") -> bool:
    """
    Push log file to Loki server as structured log entries
    Only pushes entries from the last week, and sends in batches to avoid size limits
    
    Args:
        log_path: Path to log file (speed_yyyy-mm-dd.log)
        game_type: Game type ("speed" or "vip")
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(log_path):
        print(f"⚠️  Log file not found: {log_path}")
        return False
    
    try:
        # Read log file
        print(f"📖 Reading log file: {os.path.basename(log_path)}")
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        if not lines:
            print(f"⚠️  Log file is empty: {log_path}")
            return False
        
        print(f"📊 Found {len(lines)} lines in log file")
        
        # Calculate cutoff time (7 days ago - last week)
        cutoff_time = datetime.now() - timedelta(days=MAX_AGE_DAYS)
        cutoff_timestamp = int(cutoff_time.timestamp() * 1000000000)  # nanoseconds
        
        # Prepare Loki payload
        values = []
        skipped_old = 0
        skipped_future = 0
        skipped_invalid = 0
        
        # Create progress bar
        progress = None
        if PROGRESS_BAR_AVAILABLE:
            progress = ProgressBar(len(lines), desc="Parsing log entries", width=50)
        
        # Parse and collect log entries
        for i, line in enumerate(lines):
            if progress:
                progress.set_current(i + 1)
            
            parsed = parse_log_line(line)
            if not parsed:
                skipped_invalid += 1
                continue
            
            dt, log_type, direction, message = parsed
            timestamp = int(dt.timestamp() * 1000000000)  # nanoseconds
            
            # Filter out entries that are too old (older than MAX_AGE_DAYS / 7 days)
            if timestamp < cutoff_timestamp:
                skipped_old += 1
                continue
            
            # Also filter out future entries (more than 1 hour in the future)
            future_threshold = int(
                (datetime.now() + timedelta(hours=1)).timestamp() * 1000000000
            )
            if timestamp > future_threshold:
                skipped_future += 1
                continue
            
            # Create structured log entry as JSON
            log_entry = {
                "timestamp": dt.isoformat(),
                "type": log_type,
                "direction": direction,
                "message": message,
                "raw_line": line.strip()
            }
            log_message = json.dumps(log_entry, ensure_ascii=False)
            
            # Add to values array
            values.append([str(timestamp), log_message])
        
        if progress:
            progress.close()
        
        # Report filtering results
        if skipped_invalid > 0:
            print(f"   ⚠️  Skipped {skipped_invalid} invalid log lines")
        if skipped_old > 0:
            print(
                f"   ⚠️  Skipped {skipped_old} entries older than {MAX_AGE_DAYS} days "
                "(outside last week, Loki rejects old samples)"
            )
        if skipped_future > 0:
            print(f"   ⚠️  Skipped {skipped_future} entries with future timestamps")
        
        if not values:
            print(f"   ⚠️  No valid entries to push (all entries were filtered out)")
            return False
        
        print(
            f"   ✅ {len(values)} entries ready to push "
            f"(filtered from {len(lines)} total lines, last {MAX_AGE_DAYS} days only)"
        )
        
        # Extract date from filename for better organization
        filename = os.path.basename(log_path)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        log_date = date_match.group(1) if date_match else "unknown"
        
        # Split into batches and push
        total_batches = (len(values) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n📤 Pushing {len(values)} log entries to Loki server in {total_batches} batch(es)...")
        print(f"   URL: {LOKI_URL}")
        print(f"   Batch size: {BATCH_SIZE} entries per batch")
        
        success_count = 0
        failed_count = 0
        
        # Create progress bar for batches
        batch_progress = None
        if PROGRESS_BAR_AVAILABLE:
            batch_progress = ProgressBar(total_batches, desc="Pushing batches", width=50)
        
        for batch_idx in range(0, len(values), BATCH_SIZE):
            batch_num = (batch_idx // BATCH_SIZE) + 1
            batch_values = values[batch_idx:batch_idx + BATCH_SIZE]
            
            if batch_progress:
                batch_progress.set_current(batch_num)
            
            if push_batch_to_loki(batch_values, game_type, log_date, batch_num, total_batches):
                success_count += len(batch_values)
            else:
                failed_count += len(batch_values)
                # Continue with next batch even if one fails
        
        if batch_progress:
            batch_progress.close()
        
        # Report results
        if failed_count == 0:
            print(f"\n✅ Successfully pushed {success_count} log entries to Loki")
            return True
        else:
            print(f"\n⚠️  Pushed {success_count} entries, {failed_count} entries failed")
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
        print(f"❌ Error pushing log {os.path.basename(log_path)} to Loki: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Push speed log files to remote Loki server"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Specific log file to push (default: latest speed_*.log)"
    )
    parser.add_argument(
        "--game-type",
        type=str,
        default="speed",
        help="Game type (default: speed)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Push Speed Log Files to Loki Server")
    print("=" * 60)
    print(f"Loki Server: {LOKI_URL}")
    print(f"Loki Instance: {LOKI_INSTANCE}")
    if env_detection_success:
        print(f"Detected Table Code: {detected_table_code}")
    print()
    
    # Determine log file to push
    if args.log_file:
        log_file = args.log_file
        if not os.path.isabs(log_file):
            log_file = os.path.join(STUDIO_SDP_DIR, log_file)
    else:
        # Find latest log file
        log_file = find_latest_speed_log()
        if not log_file:
            print("❌ No speed log files found!")
            print(f"\nExpected files in: {STUDIO_SDP_DIR}")
            print("   Pattern: speed_yyyy-mm-dd.log")
            return
        print(f"📋 Found latest log file: {os.path.basename(log_file)}")
    
    if not os.path.exists(log_file):
        print(f"❌ Log file not found: {log_file}")
        return
    
    print()
    success = push_log_to_loki(log_file, args.game_type)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Log entries pushed to Loki successfully")
    else:
        print("❌ Error occurred while pushing to Loki")
    print("=" * 60)


if __name__ == "__main__":
    main()

