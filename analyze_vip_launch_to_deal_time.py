#!/usr/bin/env python3
"""
Analyze VIP Roulette log files to extract launch_to_deal_time values
Scans all vip_{yyyy}-{mm}-{dd}.log files and extracts launch_to_deal_time values
Outputs statistics to ball_spin_time.csv
"""

import os
import re
import glob
import csv
from typing import List, Tuple
from decimal import Decimal, ROUND_HALF_UP


# Pattern to match launch_to_deal_time lines
# Format: [2025-11-10 02:09:04.061] Receive >>> launch_to_deal_time: 43.50457954406738
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


def find_vip_log_files() -> List[str]:
    """
    Find all vip_{yyyy}-{mm}-{dd}.log files in current directory
    
    Returns:
        List of log file paths, sorted by filename
    """
    pattern = "vip_*.log"
    log_files = glob.glob(pattern)
    # Sort by filename to process in chronological order
    log_files.sort()
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
    print("VIP Roulette Launch-to-Deal Time Analyzer")
    print("=" * 60)
    
    # Find all VIP log files
    log_files = find_vip_log_files()
    
    if not log_files:
        print("❌ No vip_*.log files found in current directory!")
        return
    
    print(f"\n📁 Found {len(log_files)} VIP log file(s):")
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


if __name__ == "__main__":
    main()

