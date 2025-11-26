#!/usr/bin/env python3
"""
Split log file by date based on timestamp in each line
Reads log files and splits them into multiple files by date (e.g., 2025-10-23.log)
Preserves the original log files

Supports:
- self-test-2api.log (legacy)
- logs/sdp_api.log (current)
- logs/sdp_mqtt.log (current)
- logs/sdp_serial.log (current)
"""

import os
import re
import sys
from collections import defaultdict
from typing import Dict, TextIO, Optional, List

# Pre-compile regex patterns for better performance
TIMESTAMP_PATTERN = re.compile(r'\[(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}:\d{2}\.\d{3}\]')
SIMPLE_DATE_PATTERN = re.compile(r'\[(\d{4}-\d{2}-\d{2})')


def extract_date_from_timestamp(line: str) -> Optional[str]:
    """
    Extract date from timestamp in log line
    Format: [2025-10-23 11:28:29.960]
    Returns: 2025-10-23 or None if not found
    """
    # Try full timestamp pattern first
    match = TIMESTAMP_PATTERN.search(line)
    if match:
        return match.group(1)
    
    # Fallback to simple date pattern
    match = SIMPLE_DATE_PATTERN.search(line)
    if match:
        return match.group(1)
    
    return None


def split_log_by_date(input_file: str, output_prefix: str = "") -> None:
    """
    Split log file by date based on timestamp in each line
    
    Args:
        input_file: Path to input log file (e.g., self-test-2api.log)
        output_prefix: Optional prefix for output files (e.g., "api_" for logs/sdp_api.log)
    """
    if not os.path.exists(input_file):
        print(f"❌ Error: File '{input_file}' not found!")
        return
    
    print(f"📖 Reading log file: {input_file}")
    print("⏳ Processing... (this may take a while for large files)")
    
    # Dictionary to store file handles for each date
    date_files: Dict[str, TextIO] = {}
    lines_processed = 0
    lines_without_timestamp = 0
    dates_found = set()
    
    try:
        # Open input file and process line by line
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                lines_processed += 1
                
                # Extract date from timestamp
                date = extract_date_from_timestamp(line)
                
                if date:
                    dates_found.add(date)
                    
                    # Open file for this date if not already open
                    if date not in date_files:
                        if output_prefix:
                            output_file = f"{output_prefix}{date}.log"
                        else:
                            output_file = f"{date}.log"
                        date_files[date] = open(output_file, 'a', encoding='utf-8')
                        print(f"📝 Created/opened file: {output_file}")
                    
                    # Write line to appropriate date file
                    date_files[date].write(line)
                else:
                    lines_without_timestamp += 1
                    # Optionally write lines without timestamp to a special file
                    # For now, we'll just count them
                
                # Progress indicator every 100k lines
                if lines_processed % 100000 == 0:
                    print(f"   Processed {lines_processed:,} lines...")
        
        # Close all date files
        for date, file_handle in date_files.items():
            file_handle.close()
        
        print("\n" + "=" * 60)
        print(f"✅ Log splitting completed for: {input_file}")
        print("=" * 60)
        print(f"📊 Statistics:")
        print(f"   Total lines processed: {lines_processed:,}")
        print(f"   Lines with valid timestamp: {lines_processed - lines_without_timestamp:,}")
        print(f"   Lines without timestamp: {lines_without_timestamp:,}")
        print(f"   Unique dates found: {len(dates_found)}")
        print(f"   Output files created:")
        for date in sorted(dates_found):
            if output_prefix:
                output_file = f"{output_prefix}{date}.log"
            else:
                output_file = f"{date}.log"
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                file_size_mb = file_size / (1024 * 1024)
                print(f"      - {output_file} ({file_size_mb:.2f} MB)")
        print(f"\n📁 Original file preserved: {input_file}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        # Close any open files in case of error
        for file_handle in date_files.values():
            try:
                file_handle.close()
            except:
                pass
        raise


def split_multiple_logs(input_files: List[str], output_prefixes: List[str] = None) -> None:
    """
    Split multiple log files by date
    
    Args:
        input_files: List of input log file paths
        output_prefixes: Optional list of prefixes for output files (one per input file)
    """
    if output_prefixes is None:
        output_prefixes = [""] * len(input_files)
    
    if len(output_prefixes) != len(input_files):
        print("⚠️  Warning: Number of prefixes doesn't match number of files. Using empty prefixes.")
        output_prefixes = [""] * len(input_files)
    
    print("=" * 60)
    print("Multi-File Log Splitter by Date")
    print("=" * 60)
    print(f"Processing {len(input_files)} file(s):")
    for i, input_file in enumerate(input_files):
        prefix = output_prefixes[i] if output_prefixes[i] else "(no prefix)"
        print(f"   {i+1}. {input_file} -> {prefix}YYYY-MM-DD.log")
    print()
    
    for i, input_file in enumerate(input_files):
        prefix = output_prefixes[i] if i < len(output_prefixes) else ""
        print(f"\n{'='*60}")
        print(f"Processing file {i+1}/{len(input_files)}: {input_file}")
        print(f"{'='*60}\n")
        split_log_by_date(input_file, prefix)


def main():
    """Main function"""
    # Check if specific files are provided as command line arguments
    if len(sys.argv) > 1:
        input_files = sys.argv[1:]
        # Determine prefixes based on file names
        output_prefixes = []
        for input_file in input_files:
            if "sdp_api" in input_file:
                output_prefixes.append("api_")
            elif "sdp_mqtt" in input_file:
                output_prefixes.append("mqtt_")
            elif "sdp_serial" in input_file:
                output_prefixes.append("serial_")
            else:
                output_prefixes.append("")
        
        split_multiple_logs(input_files, output_prefixes)
    else:
        # Default: process all known log files
        log_files = []
        prefixes = []
        
        # Legacy file
        if os.path.exists("self-test-2api.log"):
            log_files.append("self-test-2api.log")
            prefixes.append("")
        
        # Current log files in logs/ directory
        current_logs = [
            ("logs/sdp_api.log", "api_"),
            ("logs/sdp_mqtt.log", "mqtt_"),
            ("logs/sdp_serial.log", "serial_"),
        ]
        
        for log_file, prefix in current_logs:
            if os.path.exists(log_file):
                log_files.append(log_file)
                prefixes.append(prefix)
        
        if not log_files:
            print("❌ Error: No log files found!")
            print("\nAvailable options:")
            print("  1. Run with specific files: python split_log_by_date.py <file1> [file2] ...")
            print("  2. Ensure log files exist in current directory or logs/ directory")
            return
        
        print("=" * 60)
        print("Log File Splitter by Date")
        print("=" * 60)
        print("Auto-detected log files:")
        for log_file in log_files:
            print(f"  - {log_file}")
        print()
        
        split_multiple_logs(log_files, prefixes)


if __name__ == "__main__":
    main()

