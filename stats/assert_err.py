import datetime
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
from statistics import median


def parse_log_file(file_path):
    """Parse log file and extract timestamps and error types"""
    with open(file_path, "r") as f:
        log_lines = f.readlines()

    # Store timestamps and error types
    entries = []

    for line in log_lines:
        # Use regex to extract timestamp and error type
        timestamp_match = re.search(r"\[(.*?)\]", line)
        error_match = re.search(r"Assertion Error: (\w+)", line)

        if timestamp_match and error_match:
            timestamp_str = timestamp_match.group(1)
            error_type = error_match.group(1)

            # Convert timestamp to datetime object
            timestamp = datetime.datetime.strptime(
                timestamp_str, "%Y-%m-%d %H:%M:%S.%f"
            )

            entries.append((timestamp, error_type))

    return entries


def calculate_time_intervals(entries):
    """Calculate time intervals between adjacent errors"""
    if not entries or len(entries) < 2:
        return []

    intervals = []
    for i in range(1, len(entries)):
        current_time, current_error = entries[i]
        prev_time, prev_error = entries[i - 1]

        # Calculate time difference (in seconds)
        time_diff = (current_time - prev_time).total_seconds()

        intervals.append(
            (prev_time, current_time, time_diff, prev_error, current_error)
        )

    return intervals


def analyze_intervals_by_error_type(intervals):
    """Analyze time intervals by error type"""
    # Group by error type
    error_transitions = defaultdict(list)

    for prev_time, current_time, time_diff, prev_error, current_error in intervals:
        transition_key = f"{prev_error} -> {current_error}"
        error_transitions[transition_key].append(time_diff)

    # Calculate statistics for each error type transition
    stats = {}
    for transition, diffs in error_transitions.items():
        stats[transition] = {
            "count": len(diffs),
            "avg_interval": sum(diffs) / len(diffs),
            "median_interval": median(diffs),
            "min_interval": min(diffs),
            "max_interval": max(diffs),
            "intervals": diffs,
        }

    return stats


def plot_interval_distribution(intervals, output_file="interval_distribution.png"):
    """Plot distribution of time intervals"""
    interval_values = [interval[2] for interval in intervals]

    plt.figure(figsize=(12, 6))

    # Draw histogram
    plt.hist(interval_values, bins=30, alpha=0.7, color="skyblue")
    plt.axvline(
        np.mean(interval_values),
        color="red",
        linestyle="dashed",
        linewidth=1,
        label=f"Mean: {np.mean(interval_values):.2f}s",
    )
    plt.axvline(
        np.median(interval_values),
        color="green",
        linestyle="dashed",
        linewidth=1,
        label=f"Median: {np.median(interval_values):.2f}s",
    )

    plt.title("Assertion Error Time Interval Distribution")
    plt.xlabel("Time Interval (seconds)")
    plt.ylabel("Frequency")
    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Distribution chart saved as {output_file}")


def plot_error_type_distribution(entries, output_file="error_type_distribution.png"):
    """Plot distribution of error types"""
    error_counts = defaultdict(int)
    for _, error_type in entries:
        error_counts[error_type] += 1

    # Sort for better display
    sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
    error_types = [item[0] for item in sorted_errors]
    counts = [item[1] for item in sorted_errors]

    plt.figure(figsize=(12, 6))
    bars = plt.bar(error_types, counts, color="skyblue")

    # Display values on each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 0.1,
            f"{height}",
            ha="center",
            va="bottom",
        )

    plt.title("Assertion Error Type Distribution")
    plt.xlabel("Error Type")
    plt.ylabel("Occurrence Count")
    plt.xticks(rotation=45, ha="right")
    plt.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Error type distribution chart saved as {output_file}")


def plot_error_timeline(entries, output_file="error_timeline.png"):
    """Plot timeline of error occurrences"""
    timestamps = [entry[0] for entry in entries]
    error_types = [entry[1] for entry in entries]

    # Assign different colors to different error types
    unique_errors = list(set(error_types))
    color_map = {
        error: plt.cm.tab10(i / len(unique_errors))
        for i, error in enumerate(unique_errors)
    }
    colors = [color_map[error] for error in error_types]

    plt.figure(figsize=(15, 6))

    # Draw timeline
    for i, (timestamp, error) in enumerate(entries):
        plt.scatter(timestamp, 1, color=color_map[error], s=50, alpha=0.7)

    # Add legend
    for error, color in color_map.items():
        plt.scatter([], [], color=color, label=error, s=50)

    plt.title("Assertion Error Timeline")
    plt.xlabel("Time")
    plt.ylabel("Event")
    plt.yticks([])  # Hide y-axis ticks
    plt.grid(True, alpha=0.3, axis="x")
    plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3)

    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Timeline chart saved as {output_file}")


def main(log_file_path):
    """Main function"""
    # Parse log file
    entries = parse_log_file(log_file_path)

    if not entries:
        print("No valid log entries found")
        return

    # Calculate time intervals
    intervals = calculate_time_intervals(entries)

    # Basic statistics
    total_intervals = len(intervals)
    interval_values = [interval[2] for interval in intervals]
    avg_interval = sum(interval_values) / total_intervals
    median_interval = median(interval_values)
    min_interval = min(intervals, key=lambda x: x[2])
    max_interval = max(intervals, key=lambda x: x[2])

    print(f"Analyzed {total_intervals} time intervals")
    print(f"Average time interval: {avg_interval:.2f} seconds")
    print(f"Median time interval: {median_interval:.2f} seconds")
    print(
        f"Shortest time interval: {min_interval[2]:.2f} seconds (between {min_interval[0]} and {min_interval[1]})"
    )
    print(
        f"Longest time interval: {max_interval[2]:.2f} seconds (between {max_interval[0]} and {max_interval[1]})"
    )

    # Analysis by error type
    error_stats = analyze_intervals_by_error_type(intervals)

    print("\nTime interval statistics by error type:")
    for transition, stats in error_stats.items():
        print(f"\n{transition}:")
        print(f"  Occurrence count: {stats['count']}")
        print(f"  Average interval: {stats['avg_interval']:.2f} seconds")
        print(f"  Median interval: {stats['median_interval']:.2f} seconds")
        print(f"  Minimum interval: {stats['min_interval']:.2f} seconds")
        print(f"  Maximum interval: {stats['max_interval']:.2f} seconds")

    # Calculate frequency of each error type
    error_counts = defaultdict(int)
    for _, error_type in entries:
        error_counts[error_type] += 1

    print("\nFrequency of each error type:")
    for error_type, count in sorted(
        error_counts.items(), key=lambda x: x[1], reverse=True
    ):
        percentage = (count / len(entries)) * 100
        print(f"{error_type}: {count} times ({percentage:.2f}%)")

    # Draw charts
    try:
        plot_interval_distribution(intervals)
        plot_error_type_distribution(entries)
        plot_error_timeline(entries)
    except Exception as e:
        print(f"Error occurred while drawing charts: {e}")
        print(
            "If you need chart functionality, please make sure matplotlib is installed (pip install matplotlib)"
        )


if __name__ == "__main__":
    # Assume log file name is assertion_errors.log
    log_file_path = "assertion_errors.log"
    main(log_file_path)
