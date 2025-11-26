#!/usr/bin/env python3
"""
Time Interval Calculator for Log Files
計算 sdp.log 和 idp.log 每行之間的時間間隔
"""

import re
import os
from datetime import datetime
from typing import List, Tuple, Optional


def parse_timestamp_sdp(line: str) -> Optional[datetime]:
    """
    Parse timestamp from sdp.log format: [2025-10-28 09:22:58.197]
    """
    pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]'
    match = re.search(pattern, line)
    if match:
        timestamp_str = match.group(1)
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
    return None


def parse_timestamp_idp(line: str) -> Optional[datetime]:
    """
    Parse timestamp from idp.log format: [2025-10-28 09:23:09,271]
    """
    pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\]'
    match = re.search(pattern, line)
    if match:
        timestamp_str = match.group(1)
        # Replace comma with dot for datetime parsing
        timestamp_str = timestamp_str.replace(',', '.')
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
    return None


def calculate_intervals(log_file: str, parse_func, output_file: str) -> None:
    """
    Calculate time intervals between consecutive log entries
    """
    print(f"Processing {log_file}...")
    
    if not os.path.exists(log_file):
        print(f"Error: {log_file} not found!")
        return
    
    timestamps = []
    lines = []
    
    # Read and parse all timestamps
    with open(log_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            timestamp = parse_func(line)
            if timestamp:
                timestamps.append(timestamp)
                lines.append((line_num, line))
            else:
                print(f"Warning: Could not parse timestamp in line {line_num}: {line[:50]}...")
    
    print(f"Found {len(timestamps)} valid timestamps")
    
    if len(timestamps) < 2:
        print("Not enough timestamps to calculate intervals")
        return
    
    # Calculate intervals and write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for i in range(1, len(timestamps)):
            prev_time = timestamps[i-1]
            curr_time = timestamps[i]
            interval = (curr_time - prev_time).total_seconds()
            
            prev_line_num, prev_line = lines[i-1]
            curr_line_num, curr_line = lines[i]
            
            # Format the output line in simplified format
            f.write(f"Line {prev_line_num}-{curr_line_num} {interval:.3f}\n")
    
    print(f"Results saved to {output_file}")
    
    # Print summary statistics
    intervals = [(timestamps[i] - timestamps[i-1]).total_seconds() 
                for i in range(1, len(timestamps))]
    
    if intervals:
        avg_interval = sum(intervals) / len(intervals)
        min_interval = min(intervals)
        max_interval = max(intervals)
        
        print(f"\nSummary for {log_file}:")
        print(f"  Total entries: {len(timestamps)}")
        print(f"  Total intervals: {len(intervals)}")
        print(f"  Average interval: {avg_interval:.3f} seconds")
        print(f"  Minimum interval: {min_interval:.3f} seconds")
        print(f"  Maximum interval: {max_interval:.3f} seconds")


def main():
    """
    Main function to process both log files
    """
    print("=" * 60)
    print("Time Interval Calculator for Log Files")
    print("=" * 60)
    
    # Define file paths
    base_dir = "/home/rnd/studio-sdp-roulette"
    sdp_log = os.path.join(base_dir, "logs", "sdp.log")
    idp_log = os.path.join(base_dir, "logs", "idp.log")
    sdp_output = os.path.join(base_dir, "logs", "sdp_span.log")
    idp_output = os.path.join(base_dir, "logs", "idp_span.log")
    
    # Process SDP log
    print("\n1. Processing SDP log...")
    calculate_intervals(sdp_log, parse_timestamp_sdp, sdp_output)
    
    # Process IDP log
    print("\n2. Processing IDP log...")
    calculate_intervals(idp_log, parse_timestamp_idp, idp_output)
    
    print("\n" + "=" * 60)
    print("Analysis completed!")
    print(f"SDP intervals saved to: {sdp_output}")
    print(f"IDP intervals saved to: {idp_output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
