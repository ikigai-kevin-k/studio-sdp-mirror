#!/usr/bin/env python3
"""
stat_e2e.py - End-to-end data analysis script
整合多個資料分析腳本的 end-to-end 資料分析腳本

流程：
1. 從 sdp.log, idp.log 簡化為 sdp_simple_e2e.log, idp_simple_e2e.log
2. 根據簡化後的 log 匹配 SDP 和 IDP，寫入 match_e2e.log
3. 根據 match_e2e.log 計算一致性統計，寫入 consist_stat.log
4. 根據 match_e2e.log 計算延遲統計，寫入 delay.log
"""

import os
import re
import argparse
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from statistics import mean, stdev


class LogEntry:
    """Represents a log entry with timestamp and result"""

    def __init__(self, timestamp_str: str, result: str, line_num: int, source: str):
        self.timestamp_str = timestamp_str
        self.result = int(result)
        self.line_num = line_num
        self.source = source

        # Parse timestamp
        try:
            # Handle both . and , as decimal separators
            normalized_timestamp = timestamp_str.replace(",", ".")
            self.timestamp = datetime.strptime(
                normalized_timestamp, "%Y-%m-%d %H:%M:%S.%f"
            )
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}") from e

    def __repr__(self):
        return (
            f"LogEntry({self.source}:{self.line_num}, "
            f"{self.timestamp_str}, {self.result})"
        )


def parse_start_time(start_time_str: str) -> Optional[datetime]:
    """
    Parse start time from string
    Supports two formats:
    1. Full timestamp: "2025-10-28 09:22:58.197" or "2025-10-28 09:22:58,197"
    2. Date only: "10-28" or "10-28" (mm-dd format, assumes current year)
    
    Returns datetime object or None if parsing fails
    """
    if not start_time_str:
        return None
    
    start_time_str = start_time_str.strip()
    
    # Try full timestamp format (YYYY-MM-DD HH:MM:SS.mmm or YYYY-MM-DD HH:MM:SS,mmm)
    full_patterns = [
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})",  # 2025-10-28 09:22:58.197
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})",  # 2025-10-28 09:22:58,197
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",         # 2025-10-28 09:22:58
    ]
    
    for pattern in full_patterns:
        match = re.match(pattern, start_time_str)
        if match:
            timestamp_str = match.group(1)
            try:
                # Normalize decimal separator
                normalized = timestamp_str.replace(",", ".")
                # Handle with or without milliseconds
                if "." in normalized:
                    return datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S.%f")
                else:
                    return datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
    
    # Try date only format (MM-DD)
    # Only match if it's exactly MM-DD (1-2 digits for month, 1-2 digits for day)
    # and NOT a full date (YYYY-MM-DD)
    date_pattern = r"^(\d{1,2})-(\d{1,2})$"
    match = re.match(date_pattern, start_time_str)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        
        # Validate month and day
        if not (1 <= month <= 12):
            print(f"Warning: Invalid month {month}")
            return None
        if not (1 <= day <= 31):
            print(f"Warning: Invalid day {day}")
            return None
        
        # Get current year
        current_year = datetime.now().year
        
        try:
            # Create datetime with current year, at midnight
            return datetime(current_year, month, day, 0, 0, 0)
        except ValueError as e:
            print(f"Warning: Invalid date {month}-{day}: {e}")
            return None
    
    print(f"Warning: Could not parse start time: {start_time_str}")
    return None


def parse_sdp_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse SDP log line format: [2025-10-28 09:22:58.197] Receive >>> 24
    Returns (timestamp, result) or None if parsing fails
    """
    # Pattern: [timestamp] Receive >>> result
    pattern = (
        r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\] Receive >>> (\d+)"
    )
    match = re.search(pattern, line.strip())

    if match:
        timestamp = match.group(1)
        result = match.group(2)
        return timestamp, result

    return None


def parse_idp_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse IDP log line format: [2025-10-28 09:23:09,271] Round: ... | Result: 24
    Returns (timestamp, result) or None if parsing fails
    """
    # Pattern: [timestamp] Round: ... | Result: result
    pattern = (
        r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\] Round: .*? \| Result: (\d+)"
    )
    match = re.search(pattern, line.strip())

    if match:
        timestamp = match.group(1)
        result = match.group(2)
        return timestamp, result

    return None


def simplify_log_file(
    input_file: str, output_file: str, parse_func, log_type: str, 
    start_time: Optional[datetime] = None
) -> bool:
    """
    Simplify log file to timestamp and result format
    Optionally filter by start_time (only include entries >= start_time)
    """
    print(f"Processing {log_type} log: {input_file}")
    
    if start_time:
        print(f"   Filtering: Only entries from {start_time.strftime('%Y-%m-%d %H:%M:%S')} onwards")

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        return False

    simplified_lines = []
    parsed_count = 0
    filtered_count = 0
    error_count = 0

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines
                if not line:
                    continue

                # Parse the line
                parsed = parse_func(line)

                if parsed:
                    timestamp_str, result = parsed
                    
                    # Filter by start_time if provided
                    if start_time:
                        try:
                            # Normalize timestamp format (handle both . and ,)
                            normalized_timestamp = timestamp_str.replace(",", ".")
                            entry_time = datetime.strptime(
                                normalized_timestamp, "%Y-%m-%d %H:%M:%S.%f"
                            )
                            
                            # Skip entries before start_time
                            if entry_time < start_time:
                                filtered_count += 1
                                continue
                        except ValueError:
                            # If timestamp parsing fails, skip this entry
                            error_count += 1
                            continue
                    
                    simplified_lines.append(f"{timestamp_str}  {result}\n")
                    parsed_count += 1
                else:
                    # Only print warning for first few errors
                    if error_count < 5:
                        print(
                            f"Warning: Could not parse line {line_num}: {line[:50]}..."
                        )
                    error_count += 1

        # Write simplified output
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.writelines(simplified_lines)

        print(f"✅ Successfully processed {log_type} log")
        print(f"   Parsed: {parsed_count} lines")
        if start_time:
            print(f"   Filtered out: {filtered_count} lines (before start time)")
        print(f"   Errors: {error_count} lines")
        print(f"   Output: {output_file}")

        return True

    except Exception as e:
        print(f"Error processing {input_file}: {e}")
        return False


def parse_simple_log(file_path: str, source_name: str) -> List[LogEntry]:
    """
    Parse simplified log file format: timestamp  result
    """
    entries = []

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return entries

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                # Split by two spaces
                parts = line.split("  ")
                if len(parts) != 2:
                    print(f"Warning: Invalid format at line {line_num}: {line}")
                    continue

                timestamp_str, result = parts

                try:
                    entry = LogEntry(timestamp_str, result, line_num, source_name)
                    entries.append(entry)
                except ValueError as e:
                    print(f"Warning: {e} at line {line_num}")
                    continue

        print(f"Parsed {len(entries)} entries from {source_name}")
        return entries

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []


def find_matches(
    sdp_entries: List[LogEntry], idp_entries: List[LogEntry], time_window: int = 15
) -> List[Tuple[LogEntry, LogEntry]]:
    """
    Find matches between SDP and IDP entries within the specified time window (seconds)
    """
    matches = []
    matched_idp_indices = set()  # Track which IDP entries have been matched

    print(f"Searching for matches within {time_window} seconds...")

    for sdp_entry in sdp_entries:
        # Calculate time window: SDP timestamp to SDP timestamp + time_window seconds
        window_start = sdp_entry.timestamp
        window_end = sdp_entry.timestamp + timedelta(seconds=time_window)

        best_match = None
        best_time_diff = float("inf")

        # Find the best match within the time window
        for i, idp_entry in enumerate(idp_entries):
            if i in matched_idp_indices:
                continue  # Skip already matched IDP entries

            # Check if IDP timestamp is within the window
            if window_start <= idp_entry.timestamp <= window_end:
                time_diff = abs(
                    (idp_entry.timestamp - sdp_entry.timestamp).total_seconds()
                )

                # Keep the closest match within the window
                if time_diff < best_time_diff:
                    best_match = idp_entry
                    best_time_diff = time_diff

        if best_match:
            matches.append((sdp_entry, best_match))
            matched_idp_indices.add(idp_entries.index(best_match))

    print(f"Found {len(matches)} matches")
    return matches


def write_match_log(matches: List[Tuple[LogEntry, LogEntry]], output_file: str):
    """
    Write match results to output file
    Format: SDP_line | IDP_line | SDP_timestamp | IDP_timestamp | SDP_result | IDP_result | delay(seconds)
    delay = IDP_timestamp - SDP_timestamp (can be negative)
    """
    try:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# SDP-IDP Match Results\n")
            f.write(
                "# Format: SDP_line | IDP_line | SDP_timestamp | IDP_timestamp | "
                "SDP_result | IDP_result | delay(seconds)\n"
            )
            f.write("# delay = IDP_timestamp - SDP_timestamp (can be negative)\n")
            f.write("#" + "=" * 100 + "\n\n")

            for sdp_entry, idp_entry in matches:
                # Calculate actual delay: IDP timestamp - SDP timestamp
                time_diff = (
                    idp_entry.timestamp - sdp_entry.timestamp
                ).total_seconds()

                f.write(
                    f"SDP_line_{sdp_entry.line_num} | IDP_line_{idp_entry.line_num} | "
                )
                f.write(
                    f"{sdp_entry.timestamp_str} | {idp_entry.timestamp_str} | "
                )
                f.write(
                    f"{sdp_entry.result} | {idp_entry.result} | {time_diff:.3f}\n"
                )

        print(f"✅ Match results written to {output_file}")

    except Exception as e:
        print(f"Error writing match log: {e}")


def parse_match_log(file_path: str) -> List[Tuple[int, int, float]]:
    """
    Parse match.log file and extract SDP_result, IDP_result, and time_diff
    Returns list of (sdp_result, idp_result, time_diff) tuples
    """
    results = []

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return results

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comment lines
                if not line or line.startswith("#"):
                    continue

                # Parse the line format:
                # SDP_line_X | IDP_line_Y | timestamp1 | timestamp2 | sdp_result | idp_result | time_diff
                parts = line.split(" | ")
                if len(parts) != 7:
                    print(f"Warning: Invalid format at line {line_num}: {line}")
                    continue

                try:
                    sdp_result = int(parts[4].strip())
                    idp_result = int(parts[5].strip())
                    time_diff = float(parts[6].strip())
                    results.append((sdp_result, idp_result, time_diff))
                except ValueError as e:
                    print(f"Warning: Could not parse results at line {line_num}: {e}")
                    continue

        print(f"Parsed {len(results)} result pairs from match log")
        return results

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []


def calculate_consistency_stats(
    results: List[Tuple[int, int, float]]
) -> dict:
    """
    Calculate consistency statistics from match results
    """
    if not results:
        return {}

    total_pairs = len(results)
    equal_pairs = 0
    unequal_pairs = 0

    # Count equal and unequal pairs
    for sdp_result, idp_result, _ in results:
        if sdp_result == idp_result:
            equal_pairs += 1
        else:
            unequal_pairs += 1

    # Calculate percentages
    equal_percentage = (equal_pairs / total_pairs) * 100 if total_pairs > 0 else 0.0
    unequal_percentage = (
        (unequal_pairs / total_pairs) * 100 if total_pairs > 0 else 0.0
    )

    return {
        "total_pairs": total_pairs,
        "equal_pairs": equal_pairs,
        "unequal_pairs": unequal_pairs,
        "equal_percentage": equal_percentage,
        "unequal_percentage": unequal_percentage,
    }


def write_consistency_stats(stats: dict, output_file: str):
    """
    Write consistency statistics to output file
    """
    try:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# SDP-IDP Consistency Statistics\n")
            f.write("# Generated by stat_e2e.py\n")
            f.write(f"# Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("#" + "=" * 80 + "\n\n")

            f.write("Overall Statistics:\n")
            f.write(f"  Total matched pairs: {stats['total_pairs']}\n")
            f.write(f"  Equal results: {stats['equal_pairs']}\n")
            f.write(f"  Unequal results: {stats['unequal_pairs']}\n\n")

            f.write("Percentage Analysis:\n")
            f.write(f"  Equal results: {stats['equal_percentage']:.2f}%\n")
            f.write(f"  Unequal results: {stats['unequal_percentage']:.2f}%\n")

        print(f"✅ Consistency statistics written to {output_file}")

    except Exception as e:
        print(f"Error writing consistency stats: {e}")


def calculate_delay_stats(
    results: List[Tuple[int, int, float]]
) -> dict:
    """
    Calculate delay statistics from match results
    Delay = IDP timestamp - SDP timestamp (from time_diff in match log)
    Positive delay means IDP received result later than SDP
    Negative delay means IDP received result earlier than SDP
    """
    if not results:
        return {}

    # Extract time differences (actual delay: IDP - SDP)
    time_diffs = [time_diff for _, _, time_diff in results]

    if not time_diffs:
        return {}

    # Calculate statistics
    min_delay = min(time_diffs)
    max_delay = max(time_diffs)
    avg_delay = mean(time_diffs)
    median_delay = sorted(time_diffs)[len(time_diffs) // 2]

    # Calculate standard deviation if we have more than one value
    std_delay = stdev(time_diffs) if len(time_diffs) > 1 else 0.0

    return {
        "total_matches": len(time_diffs),
        "min_delay": min_delay,
        "max_delay": max_delay,
        "avg_delay": avg_delay,
        "median_delay": median_delay,
        "std_delay": std_delay,
    }


def write_delay_stats(stats: dict, output_file: str):
    """
    Write delay statistics to output file
    """
    try:
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# SDP-IDP Delay Statistics\n")
            f.write("# Delay = IDP timestamp - SDP timestamp (seconds)\n")
            f.write("# Positive delay: IDP received result later than SDP\n")
            f.write("# Negative delay: IDP received result earlier than SDP\n")
            f.write("# Generated by stat_e2e.py\n")
            f.write(f"# Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("#" + "=" * 80 + "\n\n")

            f.write("Delay Statistics:\n")
            f.write(f"  Total matches: {stats['total_matches']}\n")
            f.write(f"  Minimum delay: {stats['min_delay']:.3f} seconds\n")
            f.write(f"  Maximum delay: {stats['max_delay']:.3f} seconds\n")
            f.write(f"  Average delay: {stats['avg_delay']:.3f} seconds\n")
            f.write(f"  Median delay: {stats['median_delay']:.3f} seconds\n")
            f.write(f"  Standard deviation: {stats['std_delay']:.3f} seconds\n")

        print(f"✅ Delay statistics written to {output_file}")

    except Exception as e:
        print(f"Error writing delay stats: {e}")


def main():
    """
    Main function for end-to-end data analysis
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="End-to-end data analysis script for SDP/IDP logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use full timestamp
  python3 stat_e2e.py --start-time "2025-10-28 09:22:58.197"
  
  # Use date only (MM-DD format, assumes current year)
  python3 stat_e2e.py --start-time "10-28"
  
  # No start time filter (process all logs)
  python3 stat_e2e.py
        """
    )
    parser.add_argument(
        "--start-time",
        type=str,
        default=None,
        help="Start time filter. Supports two formats:\n"
             "1. Full timestamp: '2025-10-28 09:22:58.197' or '2025-10-28 09:22:58,197'\n"
             "2. Date only: '10-28' (MM-DD format, assumes current year)\n"
             "Only entries >= start_time will be processed.",
        metavar="TIME"
    )
    
    args = parser.parse_args()
    
    # Parse start time if provided
    start_time = None
    if args.start_time:
        start_time = parse_start_time(args.start_time)
        if not start_time:
            print(f"❌ Error: Could not parse start time: {args.start_time}")
            print("   Please use format: '2025-10-28 09:22:58.197' or '10-28'")
            return
    
    print("=" * 80)
    print("stat_e2e.py - End-to-End Data Analysis Script")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if start_time:
        print(f"Start time filter: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Define file paths
    base_dir = "/home/rnd/studio-sdp-roulette"
    logs_dir = os.path.join(base_dir, "logs")

    # Input files
    sdp_input = os.path.join(logs_dir, "sdp.log")
    idp_input = os.path.join(logs_dir, "idp.log")

    # Output files
    sdp_simple_output = os.path.join(logs_dir, "sdp_simple_e2e.log")
    idp_simple_output = os.path.join(logs_dir, "idp_simple_e2e.log")
    match_output = os.path.join(logs_dir, "match_e2e.log")
    consist_stat_output = os.path.join(logs_dir, "consist_stat.log")
    delay_stat_output = os.path.join(logs_dir, "delay.log")

    success_count = 0

    # Step 1: Simplify log files
    print("=" * 80)
    print("Step 1: Simplifying log files")
    print("=" * 80)

    print(f"\n1.1 Processing SDP log...")
    if simplify_log_file(sdp_input, sdp_simple_output, parse_sdp_line, "SDP", start_time):
        success_count += 1

    print(f"\n1.2 Processing IDP log...")
    if simplify_log_file(idp_input, idp_simple_output, parse_idp_line, "IDP", start_time):
        success_count += 1

    if success_count < 2:
        print("\n❌ Failed to simplify log files. Aborting.")
        return

    # Step 2: Match SDP and IDP entries
    print("\n" + "=" * 80)
    print("Step 2: Matching SDP and IDP entries")
    print("=" * 80)

    print(f"\n2.1 Parsing simplified SDP log: {sdp_simple_output}")
    sdp_entries = parse_simple_log(sdp_simple_output, "SDP")

    print(f"\n2.2 Parsing simplified IDP log: {idp_simple_output}")
    idp_entries = parse_simple_log(idp_simple_output, "IDP")

    if not sdp_entries or not idp_entries:
        print("❌ Could not parse one or both simplified log files!")
        return

    print(f"\n2.3 Finding matches...")
    print(f"   SDP entries: {len(sdp_entries)}")
    print(f"   IDP entries: {len(idp_entries)}")

    matches = find_matches(sdp_entries, idp_entries, time_window=15)

    print(f"\n2.4 Writing match results...")
    write_match_log(matches, match_output)

    if not matches:
        print("\n⚠️  No matches found. Cannot proceed with statistics.")
        return

    # Step 3: Calculate consistency statistics
    print("\n" + "=" * 80)
    print("Step 3: Calculating consistency statistics")
    print("=" * 80)

    print(f"\n3.1 Parsing match log: {match_output}")
    match_results = parse_match_log(match_output)

    if not match_results:
        print("❌ Could not parse match log!")
        return

    print(f"\n3.2 Calculating consistency statistics...")
    consist_stats = calculate_consistency_stats(match_results)

    print(f"\n3.3 Writing consistency statistics...")
    write_consistency_stats(consist_stats, consist_stat_output)

    # Print consistency summary
    print(f"\n📊 Consistency Summary:")
    print(f"   Total matched pairs: {consist_stats['total_pairs']}")
    print(f"   Equal results: {consist_stats['equal_pairs']}")
    print(f"   Unequal results: {consist_stats['unequal_pairs']}")
    print(f"   Consistency: {consist_stats['equal_percentage']:.2f}%")

    # Step 4: Calculate delay statistics
    print("\n" + "=" * 80)
    print("Step 4: Calculating delay statistics")
    print("=" * 80)

    print(f"\n4.1 Calculating delay statistics...")
    delay_stats = calculate_delay_stats(match_results)

    print(f"\n4.2 Writing delay statistics...")
    write_delay_stats(delay_stats, delay_stat_output)

    # Print delay summary
    print(f"\n📈 Delay Summary:")
    print(f"   Total matches: {delay_stats['total_matches']}")
    print(f"   Minimum delay: {delay_stats['min_delay']:.3f} seconds")
    print(f"   Maximum delay: {delay_stats['max_delay']:.3f} seconds")
    print(f"   Average delay: {delay_stats['avg_delay']:.3f} seconds")
    print(f"   Median delay: {delay_stats['median_delay']:.3f} seconds")
    print(f"   Standard deviation: {delay_stats['std_delay']:.3f} seconds")

    # Final summary
    print("\n" + "=" * 80)
    print("✅ End-to-End Analysis Completed Successfully!")
    print("=" * 80)
    print(f"\nOutput files:")
    print(f"  - Simplified SDP log: {sdp_simple_output}")
    print(f"  - Simplified IDP log: {idp_simple_output}")
    print(f"  - Match results: {match_output}")
    print(f"  - Consistency statistics: {consist_stat_output}")
    print(f"  - Delay statistics: {delay_stat_output}")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error running stat_e2e.py: {e}")
        import traceback

        traceback.print_exc()
        exit(1)

