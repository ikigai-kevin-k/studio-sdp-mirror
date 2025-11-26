#!/usr/bin/env python3
"""
Extract *X;6 sensor error messages from VIP Roulette log files
Scans all vip_{yyyy}-{mm}-{dd}.log files and extracts *X;6 messages
Only keeps non-consecutive log lines (first occurrence in a sequence)
Outputs results to vip_sensor_err.csv
"""

import os
import re
import glob
import csv
from typing import List, Tuple, Optional
from datetime import datetime


# Pattern to match *X messages
# Format: [2025-11-10 04:07:13.725] Receive >>> *X;6;117;13;0;002;0
# Only match actual *X messages, not lines that contain "*X" in other contexts
X_PATTERN = re.compile(
    r'\[(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d{3})\]\s+Receive\s+>>>\s+(\*X;[2346][^\n]+)'
)
X6_PATTERN = re.compile(
    r'\[(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d{3})\]\s+Receive\s+>>>\s+(\*X;6;[^\n]+)'
)


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """
    Parse date and time strings into datetime object
    
    Args:
        date_str: Date string in format YYYY-MM-DD
        time_str: Time string in format HH:MM:SS.mmm
        
    Returns:
        datetime object
    """
    datetime_str = f"{date_str} {time_str}"
    return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f")


def extract_x6_messages(log_file: str, show_progress: bool = False) -> List[Tuple[datetime, str, str, str]]:
    """
    Extract *X;6 messages from a log file
    Only keep *X;6 messages that transition from *X;2, *X;3, or *X;4 states
    Do not keep *X;6 messages that come after another *X;6 message
    
    Args:
        log_file: Path to log file
        show_progress: Whether to show progress indicator for large files
        
    Returns:
        List of tuples: (datetime, date, time, message) - only *X;6 messages from valid transitions
    """
    results = []
    prev_state = None  # Track previous state: 'X2', 'X3', 'X4', 'X6', or None
    prev_x6_datetime = None
    time_threshold_seconds = 10.1  # Consider *X;6 messages within 10 seconds as consecutive (allow small margin for timestamp precision)
    
    try:
        # Check file size to determine if we should show progress
        file_size = os.path.getsize(log_file)
        file_size_mb = file_size / (1024 * 1024)
        should_show_progress = show_progress or file_size_mb > 50  # Show progress for files > 50MB
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines_processed = 0
            for line in f:
                lines_processed += 1
                
                # Show progress every 100k lines for large files
                if should_show_progress and lines_processed % 100000 == 0:
                    print(f"      Processed {lines_processed:,} lines...", end='\r', flush=True)
                match = X_PATTERN.search(line)
                if match:
                    date = match.group(1)
                    time = match.group(2)
                    message = match.group(3).strip()
                    
                    # Parse datetime
                    dt = parse_datetime(date, time)
                    
                    # Determine current state
                    if message.startswith('*X;2'):
                        current_state = 'X2'
                    elif message.startswith('*X;3'):
                        current_state = 'X3'
                    elif message.startswith('*X;4'):
                        current_state = 'X4'
                    elif message.startswith('*X;6'):
                        current_state = 'X6'
                    else:
                        current_state = None
                    
                    # Only keep *X;6 messages that transition from *X;2, *X;3, or *X;4
                    if current_state == 'X6':
                        # Check if previous state was X2, X3, or X4
                        if prev_state in ['X2', 'X3', 'X4']:
                            # Also check if this is not consecutive to previous *X;6 (within 10 seconds)
                            is_consecutive = False
                            if prev_x6_datetime is not None:
                                time_diff = (dt - prev_x6_datetime).total_seconds()
                                if 0 < time_diff <= time_threshold_seconds:
                                    is_consecutive = True
                            
                            # Only keep if NOT consecutive to previous *X;6
                            if not is_consecutive:
                                results.append((dt, date, time, message))
                                prev_x6_datetime = dt
                        # If previous state was X6 or None, don't keep this *X;6 message
                    
                    # Update previous state
                    prev_state = current_state
            
            # Clear progress line if we showed progress
            if should_show_progress and lines_processed > 0:
                print(" " * 50, end='\r')  # Clear the progress line
    except Exception as e:
        print(f"❌ Error reading file {log_file}: {e}")
    
    return results


def find_vip_log_files() -> Tuple[List[str], Optional[str]]:
    """
    Find all vip_{yyyy}-{mm}-{dd}.log files and self-test-2api.log
    
    Returns:
        Tuple of (vip_log_files, self_test_log_file)
        vip_log_files: List of vip_*.log file paths, sorted by filename
        self_test_log_file: Path to self-test-2api.log if exists, None otherwise
    """
    vip_log_files = []
    
    # Check for date-split log files (vip_YYYY-MM-DD.log)
    pattern = "vip_*.log"
    date_split_files = glob.glob(pattern)
    vip_log_files.extend(date_split_files)
    vip_log_files = sorted(list(set(vip_log_files)))
    
    # Check for current log file (self-test-2api.log)
    current_log = "self-test-2api.log"
    self_test_log = current_log if os.path.exists(current_log) else None
    
    return vip_log_files, self_test_log


def write_to_csv(results: List[Tuple[str, datetime, str, str, str]], output_file: str) -> None:
    """
    Write results to CSV file
    
    Args:
        results: List of tuples: (log_file, datetime, date, time, message)
        output_file: Path to output CSV file
    """
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow([
                'log_file',
                'date',
                'time',
                'datetime',
                'message'
            ])
            
            # Write data rows
            for log_file, dt, date, time, message in results:
                writer.writerow([
                    log_file,
                    date,
                    time,
                    dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                    message
                ])
        
        print(f"✅ Results written to: {output_file}")
    except Exception as e:
        print(f"❌ Error writing CSV file: {e}")
        raise


def main():
    """Main function"""
    print("=" * 60)
    print("VIP Sensor Error (*X;6) Message Extractor")
    print("=" * 60)
    
    # Find all VIP log files
    vip_log_files, self_test_log = find_vip_log_files()
    
    if not vip_log_files and not self_test_log:
        print("❌ No VIP log files found!")
        print("\nExpected files:")
        print("   - vip_*.log (date-split files)")
        print("   - self-test-2api.log (current log)")
        return
    
    print(f"\n📁 Found log files:")
    if vip_log_files:
        print(f"   VIP log files: {len(vip_log_files)} file(s)")
    if self_test_log:
        print(f"   self-test-2api.log: 1 file")
    
    # Extract data from VIP log files first (priority)
    print("\n⏳ Processing log files...")
    all_messages = []
    processed_timestamps = set()  # Track processed (date, time) tuples to avoid duplicates
    
    # Process VIP log files first
    for log_file in vip_log_files:
        print(f"   Processing: {log_file}...", end=' ')
        # extract_x6_messages already filters out consecutive messages
        messages = extract_x6_messages(log_file)
        
        # Add log file name to each result and track timestamps
        for dt, date, time, message in messages:
            timestamp_key = (date, time)  # Use (date, time) as unique identifier
            all_messages.append((log_file, dt, date, time, message))
            processed_timestamps.add(timestamp_key)
        
        print(f"Found {len(messages)} non-consecutive *X;6 messages")
    
    # Process self-test-2api.log only for messages not already in VIP log files
    if self_test_log:
        print(f"   Processing: {self_test_log}...", end=' ')
        messages = extract_x6_messages(self_test_log)
        
        # Only add messages that are not already in VIP log files
        new_messages = 0
        for dt, date, time, message in messages:
            timestamp_key = (date, time)
            if timestamp_key not in processed_timestamps:
                all_messages.append((self_test_log, dt, date, time, message))
                processed_timestamps.add(timestamp_key)
                new_messages += 1
        
        print(f"Found {len(messages)} non-consecutive *X;6 messages, {new_messages} new (not in VIP logs)")
    
    if not all_messages:
        print("\n❌ No *X;6 messages found in any log files!")
        return
    
    # Sort all messages by datetime
    all_messages.sort(key=lambda x: x[1])
    
    # Filter out consecutive messages across all files (final pass)
    print("\n⏳ Filtering consecutive messages across all files...")
    filtered_messages = []
    prev_x6_datetime = None
    time_threshold_seconds = 10.1  # Consider *X;6 messages within 10 seconds as consecutive (allow small margin for timestamp precision)
    
    for log_file, dt, date, time, message in all_messages:
        is_consecutive = False
        if prev_x6_datetime is not None:
            time_diff = (dt - prev_x6_datetime).total_seconds()
            # If within threshold, consider it consecutive
            if 0 < time_diff <= time_threshold_seconds:
                is_consecutive = True
        
        # Only keep if NOT consecutive
        if not is_consecutive:
            filtered_messages.append((log_file, dt, date, time, message))
        
        # Update previous *X;6 datetime
        prev_x6_datetime = dt
    
    print(f"   Filtered from {len(all_messages)} to {len(filtered_messages)} messages")
    
    # Write results to CSV
    output_file = "vip_sensor_err.csv"
    print(f"\n📊 Writing {len(filtered_messages)} non-consecutive *X;6 messages to {output_file}...")
    write_to_csv(filtered_messages, output_file)
    
    # Print summary statistics
    print("\n" + "=" * 60)
    print("Summary Statistics")
    print("=" * 60)
    total_files = len(vip_log_files) + (1 if self_test_log else 0)
    print(f"Total log files processed: {total_files}")
    print(f"   - VIP log files: {len(vip_log_files)}")
    if self_test_log:
        print(f"   - self-test-2api.log: 1")
    print(f"Total non-consecutive *X;6 messages: {len(filtered_messages)}")
    
    # Count messages per log file
    print("\nMessages per log file:")
    file_counts = {}
    for log_file, _, _, _, _ in filtered_messages:
        file_counts[log_file] = file_counts.get(log_file, 0) + 1
    
    for log_file, count in sorted(file_counts.items()):
        print(f"   {log_file}: {count} messages")
    
    # Show time range
    if filtered_messages:
        min_time = min(dt for _, dt, _, _, _ in filtered_messages)
        max_time = max(dt for _, dt, _, _, _ in filtered_messages)
        print(f"\nTime range:")
        print(f"   From: {min_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   To:   {max_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("=" * 60)
    print(f"✅ Analysis completed! Results saved to: {output_file}")


if __name__ == "__main__":
    main()

