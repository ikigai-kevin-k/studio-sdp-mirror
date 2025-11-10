#!/usr/bin/env python3
"""
Analyze ball_spin_time.csv to calculate mean and standard deviation
within a specified time range
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


def load_csv_data(csv_file: str) -> List[Tuple[datetime, float]]:
    """
    Load data from CSV file
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        List of tuples: (datetime, launch_to_deal_time)
    """
    data = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    dt = parse_datetime(row['date'], row['timestamp'])
                    time_value = float(row['launch_to_deal_time'])
                    data.append((dt, time_value))
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
    data: List[Tuple[datetime, float]],
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> List[float]:
    """
    Filter data by time range
    
    Args:
        data: List of (datetime, value) tuples
        start_time: Start datetime (inclusive), None for no lower bound
        end_time: End datetime (inclusive), None for no upper bound
        
    Returns:
        List of filtered values
    """
    filtered = []
    
    for dt, value in data:
        if start_time is not None and dt < start_time:
            continue
        if end_time is not None and dt > end_time:
            continue
        filtered.append(value)
    
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
        
        # Try to parse as datetime first
        try:
            start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                # Parse as date, set to start of day
                start_time = datetime.strptime(start_str, "%Y-%m-%d")
            except ValueError:
                print(f"❌ Error: Invalid start time format: {start_str}")
                return None, None
        
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
    
    else:
        # Single date, treat as whole day
        try:
            start_time = datetime.strptime(time_range_str, "%Y-%m-%d")
            end_time = start_time.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_time, end_time
        except ValueError:
            print(f"❌ Error: Invalid date format: {time_range_str}")
            return None, None


def main():
    """Main function"""
    print("=" * 60)
    print("Error Rate CSV Analyzer")
    print("=" * 60)
    
    # Load CSV data
    csv_file = "ball_spin_time.csv"
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
            min_time = min(dt for dt, _ in data)
            max_time = max(dt for dt, _ in data)
            print(f"\n📅 Data time range: {min_time.strftime('%Y-%m-%d %H:%M:%S')} to {max_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("\nEnter time range (or press Enter for all data):")
            print("  Format examples:")
            print("    - Single date: 2025-11-10")
            print("    - Date range: 2025-11-01 to 2025-11-10")
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
    filtered_values = filter_by_time_range(data, start_time, end_time)
    
    if not filtered_values:
        print("\n❌ No data found in specified time range!")
        return
    
    print(f"✅ Found {len(filtered_values):,} records in time range")
    
    # Calculate statistics
    print("\n⏳ Calculating statistics...")
    mean, std_dev, stats = calculate_statistics(filtered_values)
    
    # Display results
    print("\n" + "=" * 60)
    print("Statistical Analysis Results")
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
    print(f"Mean (μ):     {mean:.2f} seconds")
    print(f"Std Dev (σ):  {std_dev:.2f} seconds")
    print()
    print(f"Minimum:      {stats['min']:.2f} seconds")
    print(f"Maximum:      {stats['max']:.2f} seconds")
    print(f"Median:       {stats['median']:.2f} seconds")
    
    if 'q1' in stats and 'q3' in stats:
        print(f"Q1 (25%):     {stats['q1']:.2f} seconds")
        print(f"Q3 (75%):     {stats['q3']:.2f} seconds")
        iqr = stats['q3'] - stats['q1']
        print(f"IQR:          {iqr:.2f} seconds")
    
    # Calculate coefficient of variation
    if mean > 0:
        cv = (std_dev / mean) * 100
        print(f"CV (%):       {cv:.2f}%")
    
    # Calculate confidence intervals (95%)
    if len(filtered_values) > 1:
        import math
        se = std_dev / math.sqrt(len(filtered_values))
        t_value = 1.96  # Approximate for large samples (95% confidence)
        margin = t_value * se
        print()
        print(f"95% Confidence Interval:")
        print(f"  Lower: {mean - margin:.2f} seconds")
        print(f"  Upper: {mean + margin:.2f} seconds")
        print(f"  Margin: ±{margin:.2f} seconds")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

