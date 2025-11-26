#!/usr/bin/env python3
"""
Analyze Speed Roulette log files to extract launch_to_deal_time values
Scans all speed log files (logs/sdp_serial.log or serial_*.log) and extracts launch_to_deal_time values
Outputs statistics to ball_spin_time.csv
"""

import os
import re
import glob
import csv
from typing import List, Tuple
from decimal import Decimal, ROUND_HALF_UP


# Pattern to match launch_to_deal_time lines
# Format: [2025-10-23 11:51:15.531] Receive >>> launch_to_deal_time: 22.00007128715515
LAUNCH_TO_DEAL_PATTERN = re.compile(
    r'\[(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d{3})\]\s+Receive\s+>>>\s+launch_to_deal_time:\s+([\d.]+)'
)


def round_to_two_decimals(value: float) -> float:
    """
    Round a float value to 2 decimal places
    
    Args:
        value: Float value to round
        
    Returns:
        Float value rounded to 2 decimal places
    """
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def extract_launch_to_deal_times(log_file: str) -> List[Tuple[str, str, float]]:
    """
    Extract launch_to_deal_time values from a log file
    
    Args:
        log_file: Path to log file
        
    Returns:
        List of tuples: (date, timestamp, launch_to_deal_time_value)
    """
    results = []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                match = LAUNCH_TO_DEAL_PATTERN.search(line)
                if match:
                    date = match.group(1)
                    timestamp = match.group(2)
                    time_value = float(match.group(3))
                    # Round to 2 decimal places
                    time_value_rounded = round_to_two_decimals(time_value)
                    results.append((date, timestamp, time_value_rounded))
    except Exception as e:
        print(f"❌ Error reading file {log_file}: {e}")
    
    return results


def find_speed_log_files() -> List[str]:
    """
    Find all speed log files in current directory and logs/ directory
    
    Priority:
    1. Date-split log files: serial_*.log (from split_log_by_date.py)
    2. Current log file: logs/sdp_serial.log
    3. Legacy log files: self-test-2api.log (if exists)
    
    Returns:
        List of log file paths, sorted by filename
    """
    log_files = []
    
    # 1. Check for date-split log files (serial_YYYY-MM-DD.log)
    pattern = "serial_*.log"
    date_split_files = glob.glob(pattern)
    log_files.extend(date_split_files)
    
    # 2. Check for current log file in logs/ directory
    current_log = "logs/sdp_serial.log"
    if os.path.exists(current_log):
        log_files.append(current_log)
    
    # 3. Check for legacy log file (self-test-2api.log)
    legacy_log = "self-test-2api.log"
    if os.path.exists(legacy_log):
        log_files.append(legacy_log)
    
    # Remove duplicates and sort
    log_files = sorted(list(set(log_files)))
    
    return log_files


def write_to_csv(results: List[Tuple[str, str, str, float]], output_file: str) -> None:
    """
    Write results to CSV file
    
    Args:
        results: List of tuples: (log_file, date, timestamp, launch_to_deal_time)
        output_file: Path to output CSV file
    """
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow(['log_file', 'date', 'timestamp', 'launch_to_deal_time'])
            
            # Write data rows
            for row in results:
                writer.writerow(row)
        
        print(f"✅ Results written to: {output_file}")
    except Exception as e:
        print(f"❌ Error writing CSV file: {e}")
        raise


def main():
    """Main function"""
    print("=" * 60)
    print("Speed Roulette Launch-to-Deal Time Analyzer")
    print("=" * 60)
    
    # Find all speed log files
    log_files = find_speed_log_files()
    
    if not log_files:
        print("❌ No speed log files found!")
        print("\nExpected files:")
        print("   - serial_*.log (date-split files)")
        print("   - logs/sdp_serial.log (current log)")
        print("   - self-test-2api.log (legacy log)")
        return
    
    print(f"\n📁 Found {len(log_files)} speed log file(s):")
    for log_file in log_files:
        print(f"   - {log_file}")
    
    # Extract data from all log files
    print("\n⏳ Processing log files...")
    all_results = []
    
    for log_file in log_files:
        print(f"   Processing: {log_file}...", end=' ')
        results = extract_launch_to_deal_times(log_file)
        
        # Add log file name to each result
        for date, timestamp, time_value in results:
            all_results.append((log_file, date, timestamp, time_value))
        
        print(f"Found {len(results)} launch_to_deal_time entries")
    
    if not all_results:
        print("\n❌ No launch_to_deal_time entries found in any log files!")
        return
    
    # Write results to CSV
    output_file = "ball_spin_time.csv"
    print(f"\n📊 Writing {len(all_results)} entries to {output_file}...")
    write_to_csv(all_results, output_file)
    
    # Print summary statistics
    print("\n" + "=" * 60)
    print("Summary Statistics")
    print("=" * 60)
    print(f"Total log files processed: {len(log_files)}")
    print(f"Total launch_to_deal_time entries: {len(all_results)}")
    
    # Calculate statistics
    time_values = [row[3] for row in all_results]
    if time_values:
        print(f"Minimum launch_to_deal_time: {min(time_values):.2f} seconds")
        print(f"Maximum launch_to_deal_time: {max(time_values):.2f} seconds")
        print(f"Average launch_to_deal_time: {sum(time_values) / len(time_values):.2f} seconds")
        
        # Count entries per log file
        print("\nEntries per log file:")
        file_counts = {}
        for log_file, _, _, _ in all_results:
            file_counts[log_file] = file_counts.get(log_file, 0) + 1
        
        for log_file, count in sorted(file_counts.items()):
            print(f"   {log_file}: {count} entries")
    
    print("=" * 60)
    print(f"✅ Analysis completed! Results saved to: {output_file}")
    print(f"\n💡 Next step: Run 'python analyze_ballspin_time.py' to analyze the statistics")


if __name__ == "__main__":
    main()

