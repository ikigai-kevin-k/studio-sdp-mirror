#!/usr/bin/env python3
"""
Generate today's speed log file from logs/sdp_serial.log
This script extracts today's logs and creates speed_{today}.log file
"""

import sys
import os
import re
from datetime import datetime

# Configuration
STUDIO_SDP_DIR = "/home/rnd/studio-sdp-roulette"
CURRENT_LOG_FILE = os.path.join(STUDIO_SDP_DIR, "logs", "sdp_serial.log")

# Log line pattern: [YYYY-MM-DD HH:MM:SS.mmm] <type> >>> <message>
LOG_PATTERN = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\]\s+(\w+)\s+(>>>|<<<)\s+(.*)$'
)


def parse_log_line(line: str):
    """Parse a log line and extract timestamp, type, direction, and message"""
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


def extract_today_logs_from_sdp_serial() -> bool:
    """Extract today's logs from logs/sdp_serial.log and create speed_{today}.log file"""
    today = datetime.now().strftime("%Y-%m-%d")
    today_log_file = os.path.join(STUDIO_SDP_DIR, f"speed_{today}.log")
    
    # Check if sdp_serial.log exists
    if not os.path.exists(CURRENT_LOG_FILE):
        print(f"❌ Log file not found: {CURRENT_LOG_FILE}")
        return False
    
    try:
        today_date = datetime.now().date()
        lines_written = 0
        current_size = os.path.getsize(CURRENT_LOG_FILE)
        
        print(f"   Reading {CURRENT_LOG_FILE} to extract today's logs...")
        print(f"   File size: {current_size:,} bytes ({current_size / (1024*1024):.2f} MB)")
        
        # Read from end backwards (today's logs should be at the end)
        # Read last 200MB first for efficiency
        read_size = min(200 * 1024 * 1024, current_size)
        start_position = max(0, current_size - read_size)
        
        print(f"   Reading from position {start_position:,} bytes (last {read_size / (1024*1024):.0f}MB)...")
        
        # Extract today's logs
        with open(CURRENT_LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f_in:
            f_in.seek(start_position)
            # Skip partial line
            if start_position > 0:
                f_in.readline()
            
            with open(today_log_file, 'w', encoding='utf-8') as f_out:
                line_count = 0
                found_today = False
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
                        
                        if date == today_date:
                            f_out.write(line)
                            lines_written += 1
                            found_today = True
                        elif date > today_date:
                            # Past today, stop reading
                            break
                        elif date < today_date and found_today:
                            # We've passed today's logs, but we already found some
                            # Continue to make sure we get all of today's logs
                            pass
                
                # If not found in last 200MB, search from beginning
                if not found_today:
                    print(f"   Today's logs not found in last 200MB, searching from beginning...")
                    f_in.seek(0)
                    line_count = 0
                    for line in f_in:
                        line_count += 1
                        if line_count % 100000 == 0:
                            print(f"   Searched {line_count:,} lines...")
                        
                        parsed = parse_log_line(line)
                        if parsed:
                            dt, _, _, _ = parsed
                            date = dt.date()
                            
                            if date == today_date:
                                f_out.write(line)
                                lines_written += 1
                                found_today = True
                            elif date > today_date:
                                # Past today, no logs for today
                                break
        
        if lines_written > 0:
            print(f"📝 Created {today_log_file} with {lines_written} log entries")
        else:
            # Create empty file if no logs found for today
            with open(today_log_file, 'w', encoding='utf-8') as f:
                pass
            print(f"📝 Created empty {today_log_file} (no logs found for today)")
        
        return True
    except Exception as e:
        print(f"⚠️  Error extracting today's logs: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Generate today's speed log file"""
    today = datetime.now().strftime("%Y-%m-%d")
    today_log_file = os.path.join(STUDIO_SDP_DIR, f"speed_{today}.log")
    
    print("=" * 60)
    print("Generate Today's Speed Log File")
    print("=" * 60)
    print(f"Today: {today}")
    print(f"Source: {CURRENT_LOG_FILE}")
    print(f"Target: {today_log_file}")
    print()
    
    # Check if file already exists
    if os.path.exists(today_log_file):
        file_size = os.path.getsize(today_log_file)
        print(f"📋 Today's log file already exists: {today_log_file}")
        print(f"   File size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")
        
        if file_size < 100:
            print(f"   File is very small, re-extracting...")
        else:
            response = input("   File exists. Re-extract? (y/N): ")
            if response.lower() != 'y':
                print("   Skipping extraction.")
                return
    
    print()
    print("Extracting today's logs from logs/sdp_serial.log...")
    print()
    
    success = extract_today_logs_from_sdp_serial()
    
    print()
    print("=" * 60)
    if success:
        if os.path.exists(today_log_file):
            file_size = os.path.getsize(today_log_file)
            print(f"✅ Successfully generated: {today_log_file}")
            print(f"   File size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
            
            # Count lines
            try:
                with open(today_log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = sum(1 for _ in f)
                print(f"   Total lines: {line_count:,}")
            except Exception as e:
                print(f"   ⚠️  Could not count lines: {e}")
        else:
            print("⚠️  Function returned success but file not found")
    else:
        print("❌ Failed to generate today's log file")
    print("=" * 60)

if __name__ == "__main__":
    main()
