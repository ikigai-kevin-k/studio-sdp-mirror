#!/usr/bin/env python3
"""
Incremental Sensor Error Monitor
Monitors daily raw log files for new sensor errors and pushes to Loki

First run: Process all historical data
Subsequent runs: Only monitor current day's log file (e.g., speed_2025-11-11.log)
Auto-switch: Automatically switch to new log file when day changes
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict

# Import progress bar
try:
    from progress_bar import ProgressBar
    PROGRESS_BAR_AVAILABLE = True
except ImportError:
    PROGRESS_BAR_AVAILABLE = False

# Import sensor error extraction
from speed_sensor_err_table import extract_x6_messages
from vip_sensor_err_table import extract_x6_messages as extract_x6_messages_vip
from push_sensor_err_to_loki import push_csv_to_loki

# Configuration
STUDIO_SDP_DIR = "/home/rnd/studio-sdp-roulette"
STATE_FILE = os.path.join(STUDIO_SDP_DIR, ".sensor_err_monitor_state.json")


def load_state() -> Dict:
    """Load monitor state from file"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Error loading state file: {e}")
            return {}
    return {
        "speed": {
            "last_processed_file": None,
            "last_processed_date": None,
            "first_run": True
        },
        "vip": {
            "last_processed_file": None,
            "last_processed_date": None,
            "first_run": True
        }
    }


def save_state(state: Dict) -> None:
    """Save monitor state to file"""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving state file: {e}")


def get_current_log_file(game_type: str) -> Optional[str]:
    """
    Get current day's log file path
    
    Args:
        game_type: "speed" or "vip"
        
    Returns:
        Path to current day's log file, or None if not found
    """
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(STUDIO_SDP_DIR, f"{game_type}_{today}.log")
    
    if os.path.exists(log_file):
        return log_file
    return None


def extract_new_events_from_log(
    game_type: str,
    log_file: str,
    existing_timestamps: set
) -> list:
    """
    Extract new sensor error events from log file
    
    Args:
        game_type: "speed" or "vip"
        log_file: Path to log file
        existing_timestamps: Set of (date, time) tuples already processed
        
    Returns:
        List of new event dictionaries
    """
    if not os.path.exists(log_file):
        return []
    
    # Extract messages
    if game_type == "speed":
        messages = extract_x6_messages(log_file, show_progress=False)
    else:
        messages = extract_x6_messages_vip(log_file, show_progress=False)
    
    # Filter new events
    new_events = []
    for dt, date, time_str, message in messages:
        timestamp_key = (date, time_str)
        if timestamp_key not in existing_timestamps:
            new_events.append({
                'log_file': os.path.basename(log_file),
                'date': date,
                'time': time_str,
                'datetime': dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'message': message
            })
    
    return new_events


def process_historical_data(game_type: str, state: Dict) -> bool:
    """
    Process historical data from last 7 days on first run
    
    Args:
        game_type: "speed" or "vip"
        state: State dictionary
        
    Returns:
        True if successful
    """
    print(f"\n📋 First run: Processing last 7 days of historical data for {game_type.upper()}")
    
    # Calculate date range (last 7 days)
    today = datetime.now()
    cutoff_date = today - timedelta(days=7)
    
    # Find all date-based log files
    import glob
    pattern = os.path.join(STUDIO_SDP_DIR, f"{game_type}_*.log")
    all_log_files = sorted(glob.glob(pattern))
    
    if not all_log_files:
        print(f"   ⚠️  No historical log files found for {game_type}")
        return True
    
    # Filter files from last 7 days only
    log_files = []
    for log_file in all_log_files:
        # Extract date from filename (e.g., speed_2025-11-11.log)
        filename = os.path.basename(log_file)
        try:
            # Extract date part (YYYY-MM-DD)
            date_str = filename.split('_')[1].split('.')[0]
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Only include files from last 7 days
            if file_date >= cutoff_date:
                log_files.append(log_file)
        except (IndexError, ValueError) as e:
            # Skip files that don't match expected pattern
            continue
    
    if not log_files:
        print(f"   ⚠️  No log files found in the last 7 days for {game_type}")
        print(f"   📅 Date range: {cutoff_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")
        return True
    
    print(f"   📁 Found {len(log_files)} log file(s) from last 7 days (filtered from {len(all_log_files)} total)")
    print(f"   📅 Date range: {cutoff_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")
    
    # Process each file
    all_events = []
    for log_file in log_files:
        print(f"   📖 Processing: {os.path.basename(log_file)}...")
        
        if game_type == "speed":
            messages = extract_x6_messages(log_file, show_progress=True)
        else:
            messages = extract_x6_messages_vip(log_file, show_progress=True)
        
        # Convert to format
        for dt, date, time_str, message in messages:
            all_events.append({
                'log_file': os.path.basename(log_file),
                'date': date,
                'time': time_str,
                'datetime': dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
                'message': message
            })
        
        print(f"   ✅ Found {len(messages)} events")
    
    if not all_events:
        print(f"   ⚠️  No sensor error events found in historical data")
        return True
    
    # Write to CSV
    import csv
    csv_file = os.path.join(STUDIO_SDP_DIR, f"{game_type}_sensor_err_table.csv")
    
    print(f"\n📊 Writing {len(all_events)} events to {csv_file}...")
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['log_file', 'date', 'time', 'datetime', 'message'])
        writer.writeheader()
        writer.writerows(all_events)
    
    # Push to Loki
    print(f"\n📤 Pushing to Loki...")
    if push_csv_to_loki(csv_file, game_type):
        print(f"   ✅ Historical data pushed successfully")
        
        # Mark first run as complete
        state[game_type]["first_run"] = False
        
        # Set last processed to current day's log file
        current_log = get_current_log_file(game_type)
        if current_log:
            state[game_type]["last_processed_file"] = current_log
            state[game_type]["last_processed_date"] = datetime.now().strftime("%Y-%m-%d")
        
        save_state(state)
        return True
    else:
        print(f"   ❌ Failed to push historical data")
        return False


def monitor_incremental(game_type: str, state: Dict) -> bool:
    """
    Monitor current day's log file for new sensor errors
    
    Args:
        game_type: "speed" or "vip"
        state: State dictionary
        
    Returns:
        True if successful
    """
    game_state = state[game_type]
    
    # Check if first run
    if game_state.get("first_run", True):
        return process_historical_data(game_type, state)
    
    # Get current day's log file
    current_log = get_current_log_file(game_type)
    if not current_log:
        print(f"   ⚠️  Current day's log file not found for {game_type}")
        return True  # Not an error, just no file yet
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    last_date = game_state.get("last_processed_date")
    last_file = game_state.get("last_processed_file")
    
    # Check if day changed - need to switch to new log file
    if last_date != current_date or last_file != current_log:
        print(f"\n📅 Day changed or log file switched")
        print(f"   Previous: {last_file} (date: {last_date})")
        print(f"   Current:  {current_log} (date: {current_date})")
        
        # Update state for new file
        game_state["last_processed_file"] = current_log
        game_state["last_processed_date"] = current_date
    
    # Process incremental data
    print(f"\n📋 Monitoring {game_type.upper()} log: {os.path.basename(current_log)}")
    
    # Read existing CSV to get processed timestamps
    csv_file = os.path.join(STUDIO_SDP_DIR, f"{game_type}_sensor_err_table.csv")
    import csv
    existing_events = []
    if os.path.exists(csv_file):
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_events = list(reader)
    
    existing_timestamps = {(e['date'], e['time']) for e in existing_events}
    
    # Extract new events from current log file
    new_events = extract_new_events_from_log(
        game_type, current_log, existing_timestamps
    )
    
    if new_events:
        print(f"   ✅ Found {len(new_events)} new sensor error event(s)")
        
        # Append to CSV
        all_events = existing_events + new_events
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['log_file', 'date', 'time', 'datetime', 'message'])
            writer.writeheader()
            writer.writerows(all_events)
        
        print(f"   📊 Updated CSV with {len(new_events)} new event(s)")
        
        # Push to Loki
        if push_csv_to_loki(csv_file, game_type):
            print(f"   ✅ New events pushed to Loki")
        else:
            print(f"   ⚠️  Failed to push new events (will retry next run)")
    else:
        print(f"   ℹ️  No new sensor error events")
    
    # Update state
    game_state["last_processed_file"] = current_log
    game_state["last_processed_date"] = current_date
    save_state(state)
    
    return True


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Incremental Sensor Error Monitor for Loki ETL"
    )
    parser.add_argument(
        "--game-type",
        choices=["speed", "vip", "both"],
        default="both",
        help="Game type to monitor (default: both)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Monitoring interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (don't monitor continuously)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Incremental Sensor Error Monitor")
    print("=" * 60)
    print(f"Game Type: {args.game_type}")
    print(f"Mode: {'Run once' if args.once else f'Continuous (interval: {args.interval}s)'}")
    print()
    
    state = load_state()
    
    while True:
        success = True
        
        if args.game_type in ["speed", "both"]:
            if not monitor_incremental("speed", state):
                success = False
        
        if args.game_type in ["vip", "both"]:
            if not monitor_incremental("vip", state):
                success = False
        
        if args.once:
            break
        
        # Wait for next interval
        print(f"\n⏳ Waiting {args.interval} seconds until next check...")
        time.sleep(args.interval)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Monitor completed successfully")
    else:
        print("❌ Monitor completed with errors")
    print("=" * 60)


if __name__ == "__main__":
    main()

