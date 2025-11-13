#!/usr/bin/env python3
"""
Split self-test-2api.log by date for VIP Roulette
Reads self-test-2api.log and splits it into vip_{yyyy}-{mm}-{dd}.log files
Only processes dates from last processed date to today
"""

import os
import re
import sys
from datetime import datetime, timedelta
from typing import Dict, TextIO, Optional

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


def find_last_vip_log_date() -> Optional[datetime]:
    """Find the date of the last existing vip_*.log file"""
    import glob
    pattern = "vip_*.log"
    log_files = glob.glob(pattern)
    
    if not log_files:
        return None
    
    dates = []
    for log_file in log_files:
        filename = os.path.basename(log_file)
        match = re.search(r'vip_(\d{4}-\d{2}-\d{2})\.log', filename)
        if match:
            try:
                date = datetime.strptime(match.group(1), '%Y-%m-%d')
                dates.append(date)
            except:
                continue
    
    if dates:
        return max(dates)
    return None


def split_log_by_date(input_file: str = "self-test-2api.log", output_prefix: str = "vip_") -> None:
    """
    Split log file by date based on timestamp in each line
    Only processes dates from last existing log file to today
    
    Args:
        input_file: Path to input log file (default: self-test-2api.log)
        output_prefix: Prefix for output files (default: "vip_")
    """
    if not os.path.exists(input_file):
        print(f"❌ Error: File '{input_file}' not found!")
        return
    
    # Find last processed date
    last_date = find_last_vip_log_date()
    today = datetime.now().date()
    
    if last_date:
        last_date = last_date.date()
        print(f"📅 Last processed date: {last_date}")
        print(f"📅 Today: {today}")
        if last_date >= today:
            print(f"✅ All dates up to today are already processed!")
            return
        print(f"📅 Processing dates from {last_date + timedelta(days=1)} to {today}")
    else:
        print(f"📅 No existing VIP log files found, processing all dates up to {today}")
        last_date = None
    
    print(f"📖 Reading log file: {input_file}")
    
    # Get file size for progress estimation
    file_size = os.path.getsize(input_file)
    file_size_mb = file_size / (1024 * 1024)
    
    # Estimate total lines (rough estimate: ~100 bytes per line)
    estimated_lines = max(1, int(file_size / 100))
    
    # Dictionary to store file handles for each date
    date_files: Dict[str, TextIO] = {}
    lines_processed = 0
    lines_without_timestamp = 0
    dates_found = set()
    dates_processed = set()
    
    # Import progress bar if available
    try:
        from progress_bar import ProgressBar
        progress = ProgressBar(estimated_lines, desc="Splitting log file", width=50)
        PROGRESS_BAR_AVAILABLE = True
    except ImportError:
        progress = None
        PROGRESS_BAR_AVAILABLE = False
        print("⏳ Processing... (this may take a while for large files)")
    
    try:
        # Open input file and process line by line
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                lines_processed += 1
                
                # Update progress bar
                if progress:
                    progress.set_current(lines_processed)
                
                # Extract date from timestamp
                date_str = extract_date_from_timestamp(line)
                
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        # Only process dates after last_date (if exists) and up to today
                        if last_date and date_obj <= last_date:
                            continue  # Skip already processed dates
                        
                        if date_obj > today:
                            continue  # Skip future dates
                        
                        dates_found.add(date_str)
                        dates_processed.add(date_str)
                        
                        # Open file for this date if not already open
                        if date_str not in date_files:
                            output_file = f"{output_prefix}{date_str}.log"
                            date_files[date_str] = open(output_file, 'a', encoding='utf-8')
                            if not PROGRESS_BAR_AVAILABLE:  # Only print if no progress bar
                                print(f"📝 Created/opened file: {output_file}")
                        
                        # Write line to appropriate date file
                        date_files[date_str].write(line)
                    except ValueError:
                        lines_without_timestamp += 1
                else:
                    lines_without_timestamp += 1
        
        # Close progress bar
        if progress:
            progress.close()
        
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
        print(f"   Dates processed: {len(dates_processed)}")
        print(f"   Output files created:")
        for date in sorted(dates_processed):
            output_file = f"{output_prefix}{date}.log"
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


def main():
    """Main function"""
    print("=" * 60)
    print("VIP Roulette Log Splitter by Date (Incremental)")
    print("=" * 60)
    
    input_file = "self-test-2api.log"
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"❌ Error: File '{input_file}' not found!")
        print("\nUsage:")
        print("   python split_log_by_date_vip.py [input_file]")
        print("\nDefault input file: self-test-2api.log")
        return
    
    split_log_by_date(input_file, "vip_")


if __name__ == "__main__":
    main()

