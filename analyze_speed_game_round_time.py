#!/usr/bin/env python3
"""
Analyze Speed Roulette log files to extract game round total time
Scans all serial_{yyyy}-{mm}-{dd}.log files and extracts Summary section
Calculates total game round time = start_to_launch_time + launch_to_deal_time + deal_to_finish_time
Outputs statistics to game_round.csv
"""

import os
import re
import glob
import csv
from typing import List, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP


# Pattern to match Summary section
# Format:
# [2025-11-10 00:00:26.602] Receive >>> Summary:
# [2025-11-10 00:00:26.602] Receive >>> start_to_launch_time: 7.008816480636597
# [2025-11-10 00:00:26.602] Receive >>> launch_to_deal_time: 22.496150732040405
# [2025-11-10 00:00:26.602] Receive >>> deal_to_finish_time: 1.134570837020874

TIMESTAMP_PATTERN = re.compile(
    r'\[(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d{3})\]\s+Receive\s+>>>\s+'
)

SUMMARY_PATTERN = re.compile(r'Summary:')
START_TO_LAUNCH_PATTERN = re.compile(r'start_to_launch_time:\s+([\d.]+)')
LAUNCH_TO_DEAL_PATTERN = re.compile(r'launch_to_deal_time:\s+([\d.]+)')
DEAL_TO_FINISH_PATTERN = re.compile(r'deal_to_finish_time:\s+([\d.]+)')


def round_to_two_decimals(value: float) -> float:
    """
    Round a float value to 2 decimal places
    
    Args:
        value: Float value to round
        
    Returns:
        Float value rounded to 2 decimal places
    """
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def extract_game_round_times(log_file: str) -> List[Tuple[str, str, float, float, float, float]]:
    """
    Extract game round time values from a log file
    
    Args:
        log_file: Path to log file
        
    Returns:
        List of tuples: (date, timestamp, start_to_launch, launch_to_deal, deal_to_finish, total_time)
    """
    results = []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Check if this is a Summary line
                if SUMMARY_PATTERN.search(line):
                    # Extract timestamp from Summary line
                    timestamp_match = TIMESTAMP_PATTERN.search(line)
                    if not timestamp_match:
                        i += 1
                        continue
                    
                    date = timestamp_match.group(1)
                    timestamp = timestamp_match.group(2)
                    
                    # Read next 3 lines for the time values
                    start_to_launch = None
                    launch_to_deal = None
                    deal_to_finish = None
                    
                    # Look for the three time values in the next few lines
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_line = lines[j]
                        
                        # Check if this line has a timestamp (same round)
                        next_timestamp_match = TIMESTAMP_PATTERN.search(next_line)
                        if next_timestamp_match:
                            next_date = next_timestamp_match.group(1)
                            next_timestamp = next_timestamp_match.group(2)
                            
                            # Only process lines with same or very close timestamp (within same second)
                            # This ensures we're reading the same round's summary
                            if next_date == date:
                                # Extract start_to_launch_time
                                if start_to_launch is None:
                                    match = START_TO_LAUNCH_PATTERN.search(next_line)
                                    if match:
                                        start_to_launch = float(match.group(1))
                                
                                # Extract launch_to_deal_time
                                if launch_to_deal is None:
                                    match = LAUNCH_TO_DEAL_PATTERN.search(next_line)
                                    if match:
                                        launch_to_deal = float(match.group(1))
                                
                                # Extract deal_to_finish_time
                                if deal_to_finish is None:
                                    match = DEAL_TO_FINISH_PATTERN.search(next_line)
                                    if match:
                                        deal_to_finish = float(match.group(1))
                    
                    # If we found all three values, calculate total time
                    if start_to_launch is not None and launch_to_deal is not None and deal_to_finish is not None:
                        total_time = start_to_launch + launch_to_deal + deal_to_finish
                        total_time_rounded = round_to_two_decimals(total_time)
                        start_to_launch_rounded = round_to_two_decimals(start_to_launch)
                        launch_to_deal_rounded = round_to_two_decimals(launch_to_deal)
                        deal_to_finish_rounded = round_to_two_decimals(deal_to_finish)
                        
                        results.append((
                            date,
                            timestamp,
                            start_to_launch_rounded,
                            launch_to_deal_rounded,
                            deal_to_finish_rounded,
                            total_time_rounded
                        ))
                
                i += 1
                
    except Exception as e:
        print(f"❌ Error reading file {log_file}: {e}")
    
    return results


def find_serial_log_files() -> List[str]:
    """
    Find all serial_{yyyy}-{mm}-{dd}.log files in current directory
    
    Returns:
        List of log file paths, sorted by filename
    """
    log_files = []
    
    # Check for date-split log files (serial_YYYY-MM-DD.log)
    pattern = "serial_*.log"
    date_split_files = glob.glob(pattern)
    log_files.extend(date_split_files)
    
    # Check for current log file in logs/ directory
    current_log = "logs/sdp_serial.log"
    if os.path.exists(current_log):
        log_files.append(current_log)
    
    # Remove duplicates and sort
    log_files = sorted(list(set(log_files)))
    
    return log_files


def write_to_csv(results: List[Tuple[str, str, str, float, float, float, float]], output_file: str) -> None:
    """
    Write results to CSV file
    
    Args:
        results: List of tuples: (log_file, date, timestamp, start_to_launch, launch_to_deal, deal_to_finish, total_time)
        output_file: Path to output CSV file
    """
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow([
                'log_file',
                'date',
                'timestamp',
                'start_to_launch_time',
                'launch_to_deal_time',
                'deal_to_finish_time',
                'total_game_round_time'
            ])
            
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
    print("Speed Roulette Game Round Time Analyzer")
    print("=" * 60)
    
    # Find all serial log files
    log_files = find_serial_log_files()
    
    if not log_files:
        print("❌ No serial log files found!")
        print("\nExpected files:")
        print("   - serial_*.log (date-split files)")
        print("   - logs/sdp_serial.log (current log)")
        return
    
    print(f"\n📁 Found {len(log_files)} serial log file(s):")
    for log_file in log_files:
        print(f"   - {log_file}")
    
    # Extract data from all log files
    print("\n⏳ Processing log files...")
    all_results = []
    
    for log_file in log_files:
        print(f"   Processing: {log_file}...", end=' ')
        results = extract_game_round_times(log_file)
        
        # Add log file name to each result
        for date, timestamp, start_to_launch, launch_to_deal, deal_to_finish, total_time in results:
            all_results.append((
                log_file,
                date,
                timestamp,
                start_to_launch,
                launch_to_deal,
                deal_to_finish,
                total_time
            ))
        
        print(f"Found {len(results)} game round entries")
    
    if not all_results:
        print("\n❌ No game round entries found in any log files!")
        return
    
    # Write results to CSV
    output_file = "game_round.csv"
    print(f"\n📊 Writing {len(all_results)} entries to {output_file}...")
    write_to_csv(all_results, output_file)
    
    # Print summary statistics
    print("\n" + "=" * 60)
    print("Summary Statistics")
    print("=" * 60)
    print(f"Total log files processed: {len(log_files)}")
    print(f"Total game round entries: {len(all_results)}")
    
    # Calculate statistics
    total_times = [row[6] for row in all_results]
    if total_times:
        print(f"\nTotal Game Round Time Statistics:")
        print(f"   Minimum: {min(total_times):.2f} seconds")
        print(f"   Maximum: {max(total_times):.2f} seconds")
        print(f"   Average: {sum(total_times) / len(total_times):.2f} seconds")
        
        # Component statistics
        start_to_launch_times = [row[3] for row in all_results]
        launch_to_deal_times = [row[4] for row in all_results]
        deal_to_finish_times = [row[5] for row in all_results]
        
        print(f"\nComponent Statistics:")
        print(f"   start_to_launch_time:")
        print(f"      Average: {sum(start_to_launch_times) / len(start_to_launch_times):.2f} seconds")
        print(f"   launch_to_deal_time:")
        print(f"      Average: {sum(launch_to_deal_times) / len(launch_to_deal_times):.2f} seconds")
        print(f"   deal_to_finish_time:")
        print(f"      Average: {sum(deal_to_finish_times) / len(deal_to_finish_times):.2f} seconds")
        
        # Count entries per log file
        print("\nEntries per log file:")
        file_counts = {}
        for log_file, _, _, _, _, _, _ in all_results:
            file_counts[log_file] = file_counts.get(log_file, 0) + 1
        
        for log_file, count in sorted(file_counts.items()):
            print(f"   {log_file}: {count} entries")
    
    print("=" * 60)
    print(f"✅ Analysis completed! Results saved to: {output_file}")
    print(f"\n💡 Next step: Run 'python analyze_game_round_time.py' to analyze the statistics")


if __name__ == "__main__":
    main()

