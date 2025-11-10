#!/usr/bin/env python3
"""
Analyze vip_game_round.csv to calculate mean and standard deviation
within a specified time range for total game round time
"""

import csv
import sys
import statistics
from datetime import datetime, timedelta
from typing import List, Tuple, Optional


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


def load_csv_data(csv_file: str) -> List[Tuple[datetime, float, float, float, float]]:
    """
    Load data from CSV file
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        List of tuples: (datetime, start_to_launch, launch_to_deal, deal_to_finish, total_time)
    """
    data = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    dt = parse_datetime(row['date'], row['timestamp'])
                    start_to_launch = float(row['start_to_launch_time'])
                    launch_to_deal = float(row['launch_to_deal_time'])
                    deal_to_finish = float(row['deal_to_finish_time'])
                    total_time = float(row['total_game_round_time'])
                    data.append((dt, start_to_launch, launch_to_deal, deal_to_finish, total_time))
                except (ValueError, KeyError) as e:
                    print(f"⚠️  Warning: Skipping invalid row: {e}")
                    continue
    except FileNotFoundError:
        print(f"❌ Error: File '{csv_file}' not found!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        sys.exit(1)
    
    return data


def filter_by_time_range(
    data: List[Tuple[datetime, float, float, float, float]],
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> List[Tuple[float, float, float, float]]:
    """
    Filter data by time range
    
    Args:
        data: List of (datetime, start_to_launch, launch_to_deal, deal_to_finish, total_time) tuples
        start_time: Start datetime (inclusive), None for no lower bound
        end_time: End datetime (inclusive), None for no upper bound
        
    Returns:
        List of filtered (start_to_launch, launch_to_deal, deal_to_finish, total_time) tuples
    """
    filtered = []
    
    for dt, start_to_launch, launch_to_deal, deal_to_finish, total_time in data:
        if start_time is not None and dt < start_time:
            continue
        if end_time is not None and dt > end_time:
            continue
        filtered.append((start_to_launch, launch_to_deal, deal_to_finish, total_time))
    
    return filtered


def calculate_statistics(values: List[float]) -> Tuple[float, float, dict]:
    """
    Calculate mean, standard deviation and other statistics
    
    Args:
        values: List of numeric values
        
    Returns:
        Tuple of (mean, std_dev, additional_stats_dict)
    """
    if not values:
        return 0.0, 0.0, {}
    
    mean = statistics.mean(values)
    
    # Calculate standard deviation
    if len(values) > 1:
        std_dev = statistics.stdev(values)
    else:
        std_dev = 0.0
    
    # Additional statistics
    stats = {
        'count': len(values),
        'min': min(values),
        'max': max(values),
        'median': statistics.median(values),
    }
    
    # Calculate percentiles if we have enough data
    if len(values) >= 4:
        sorted_values = sorted(values)
        stats['q1'] = statistics.median(sorted_values[:len(sorted_values)//2])
        stats['q3'] = statistics.median(sorted_values[len(sorted_values)//2:])
    
    return mean, std_dev, stats


def parse_time_range(time_range_str: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse time range string
    
    Supported formats:
    - "YYYY-MM-DD" (single date, whole day)
    - "YYYY-MM-DD to YYYY-MM-DD" (date range)
    - "YYYY-MM-DD YYYY-MM-DD" (date range, space-separated)
    - "YYYY-MM-DD HH:MM:SS to YYYY-MM-DD HH:MM:SS" (datetime range)
    
    Args:
        time_range_str: Time range string
        
    Returns:
        Tuple of (start_time, end_time)
    """
    time_range_str = time_range_str.strip()
    
    # Check if it's a range (contains "to")
    if " to " in time_range_str:
        parts = time_range_str.split(" to ", 1)
        start_str = parts[0].strip()
        end_str = parts[1].strip()
    else:
        # Try to detect if it's two dates separated by space
        parts = time_range_str.split()
        
        if len(parts) >= 2:
            # Try to parse first part as date
            try:
                datetime.strptime(parts[0], "%Y-%m-%d")
                # If successful, check if second part is also a date
                try:
                    datetime.strptime(parts[1], "%Y-%m-%d")
                    # Both are dates, treat as range
                    start_str = parts[0]
                    end_str = parts[1]
                except ValueError:
                    # Second part is not a date, treat as single date
                    start_str = time_range_str
                    end_str = None
            except ValueError:
                # First part is not a date, treat as single date
                start_str = time_range_str
                end_str = None
        else:
            # Single date
            start_str = time_range_str
            end_str = None
    
    # Parse start time
    try:
        start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            # Parse as date, set to start of day
            start_time = datetime.strptime(start_str, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Error: Invalid start time format: {start_str}")
            return None, None
    
    # Parse end time
    if end_str is None:
        # Single date, treat as whole day
        end_time = start_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_time, end_time
    
    try:
        end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            # Parse as date, set to end of day (23:59:59.999)
            end_time = datetime.strptime(end_str, "%Y-%m-%d")
            end_time = end_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            print(f"❌ Error: Invalid end time format: {end_str}")
            return None, None
    
    return start_time, end_time


def main():
    """Main function"""
    print("=" * 60)
    print("VIP Game Round Time CSV Analyzer")
    print("=" * 60)
    
    # Load CSV data
    csv_file = "vip_game_round.csv"
    print(f"\n📖 Loading data from: {csv_file}")
    data = load_csv_data(csv_file)
    
    if not data:
        print("❌ No data found in CSV file!")
        return
    
    print(f"✅ Loaded {len(data):,} records")
    
    # Get time range from user or command line argument
    if len(sys.argv) > 1:
        time_range_str = " ".join(sys.argv[1:])
    else:
        # Show data range
        if data:
            min_time = min(dt for dt, _, _, _, _ in data)
            max_time = max(dt for dt, _, _, _, _ in data)
            print(f"\n📅 Data time range: {min_time.strftime('%Y-%m-%d %H:%M:%S')} to {max_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("\nEnter time range (or press Enter for all data):")
            print("  Format examples:")
            print("    - Single date: 2025-11-10")
            print("    - Date range: 2025-11-01 to 2025-11-10")
            print("    - Date range (space-separated): 2025-11-01 2025-11-10")
            print("    - DateTime range: 2025-11-10 00:00:00 to 2025-11-10 23:59:59")
            time_range_str = input("Time range: ").strip()
    
    # Parse time range
    start_time = None
    end_time = None
    
    if time_range_str:
        start_time, end_time = parse_time_range(time_range_str)
        if start_time is None or end_time is None:
            print("❌ Invalid time range format!")
            return
        
        print(f"\n📅 Filtering data:")
        print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\n📅 Analyzing all data (no time filter)")
    
    # Filter data
    filtered_data = filter_by_time_range(data, start_time, end_time)
    
    if not filtered_data:
        print("\n❌ No data found in specified time range!")
        return
    
    print(f"✅ Found {len(filtered_data):,} records in time range")
    
    # Extract values for each component
    total_times = [row[3] for row in filtered_data]
    start_to_launch_times = [row[0] for row in filtered_data]
    launch_to_deal_times = [row[1] for row in filtered_data]
    deal_to_finish_times = [row[2] for row in filtered_data]
    
    # Calculate statistics for total time
    print("\n⏳ Calculating statistics...")
    mean, std_dev, stats = calculate_statistics(total_times)
    
    # Display results
    print("\n" + "=" * 60)
    print("Statistical Analysis Results - Total Game Round Time")
    print("=" * 60)
    print(f"Time Range:")
    if start_time and end_time:
        print(f"  From: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  To:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"  All data")
    print()
    print(f"Sample Size: {stats['count']:,}")
    print()
    print(f"Total Game Round Time:")
    print(f"  Mean (μ):     {mean:.2f} seconds")
    print(f"  Std Dev (σ):  {std_dev:.2f} seconds")
    print()
    print(f"  Minimum:      {stats['min']:.2f} seconds")
    print(f"  Maximum:      {stats['max']:.2f} seconds")
    print(f"  Median:       {stats['median']:.2f} seconds")
    
    if 'q1' in stats and 'q3' in stats:
        print(f"  Q1 (25%):     {stats['q1']:.2f} seconds")
        print(f"  Q3 (75%):     {stats['q3']:.2f} seconds")
        iqr = stats['q3'] - stats['q1']
        print(f"  IQR:          {iqr:.2f} seconds")
    
    # Calculate coefficient of variation
    if mean > 0:
        cv = (std_dev / mean) * 100
        print(f"  CV (%):       {cv:.2f}%")
    
    # Calculate games exceeding 60 seconds
    threshold = 60.0
    games_exceeding_threshold = [t for t in total_times if t > threshold]
    total_games = len(total_times)
    games_exceeding_count = len(games_exceeding_threshold)
    
    if total_games > 0:
        percentage_exceeding = (games_exceeding_count / total_games) * 100
        print()
        print(f"Games Exceeding {threshold} seconds:")
        print(f"  Count:        {games_exceeding_count:,} games")
        print(f"  Percentage:   {percentage_exceeding:.2f}%")
        print(f"  Total games:  {total_games:,} games")
    
    # Calculate confidence intervals (95%)
    if len(total_times) > 1:
        import math
        se = std_dev / math.sqrt(len(total_times))
        t_value = 1.96  # Approximate for large samples (95% confidence)
        margin = t_value * se
        print()
        print(f"95% Confidence Interval:")
        print(f"  Lower: {mean - margin:.2f} seconds")
        print(f"  Upper: {mean + margin:.2f} seconds")
        print(f"  Margin: ±{margin:.2f} seconds")
    
    # Component statistics
    print("\n" + "=" * 60)
    print("Component Statistics")
    print("=" * 60)
    
    # start_to_launch_time
    mean_stl, std_dev_stl, stats_stl = calculate_statistics(start_to_launch_times)
    print(f"\nstart_to_launch_time:")
    print(f"  Mean:     {mean_stl:.2f} seconds")
    print(f"  Std Dev:  {std_dev_stl:.2f} seconds")
    print(f"  Min:      {stats_stl['min']:.2f} seconds")
    print(f"  Max:      {stats_stl['max']:.2f} seconds")
    print(f"  Median:   {stats_stl['median']:.2f} seconds")
    
    # launch_to_deal_time
    mean_ltd, std_dev_ltd, stats_ltd = calculate_statistics(launch_to_deal_times)
    print(f"\nlaunch_to_deal_time:")
    print(f"  Mean:     {mean_ltd:.2f} seconds")
    print(f"  Std Dev:  {std_dev_ltd:.2f} seconds")
    print(f"  Min:      {stats_ltd['min']:.2f} seconds")
    print(f"  Max:      {stats_ltd['max']:.2f} seconds")
    print(f"  Median:   {stats_ltd['median']:.2f} seconds")
    
    # deal_to_finish_time
    mean_dtf, std_dev_dtf, stats_dtf = calculate_statistics(deal_to_finish_times)
    print(f"\ndeal_to_finish_time:")
    print(f"  Mean:     {mean_dtf:.2f} seconds")
    print(f"  Std Dev:  {std_dev_dtf:.2f} seconds")
    print(f"  Min:      {stats_dtf['min']:.2f} seconds")
    print(f"  Max:      {stats_dtf['max']:.2f} seconds")
    print(f"  Median:   {stats_dtf['median']:.2f} seconds")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

