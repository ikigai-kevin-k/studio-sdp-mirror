#!/usr/bin/env python3
"""
Push sensor error CSV files to remote Loki server
Reads {speed|vip}_sensor_err_table.csv and pushes sensor error events to Loki

Based on Loki server settings from loki.md:
- Server: http://100.64.0.113:3100
- Endpoint: /loki/api/v1/push
- Port: 3100
"""

import os
import sys
import json
import csv
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

# Import progress bar
try:
    from progress_bar import ProgressBar
    PROGRESS_BAR_AVAILABLE = True
except ImportError:
    PROGRESS_BAR_AVAILABLE = False


# Configuration from loki.md
LOKI_URL = "http://100.64.0.113:3100/loki/api/v1/push"
STUDIO_SDP_DIR = "/home/rnd/studio-sdp-roulette"

# Loki rejects samples older than 7 days (reject_old_samples_max_age: 168h)
# We'll filter out entries older than 6 days to be safe (with 1 day buffer)
MAX_AGE_DAYS = 6


def push_csv_to_loki(csv_path: str, game_type: str) -> bool:
    """
    Push CSV file to Loki server as structured sensor error events
    
    Args:
        csv_path: Path to CSV file ({speed|vip}_sensor_err_table.csv)
        game_type: Game type ("speed" or "vip")
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(csv_path):
        print(f"⚠️  CSV file not found: {csv_path}")
        return False
    
    try:
        # Read CSV content
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            print(f"⚠️  CSV file is empty: {csv_path}")
            return False
        
        print(f"📊 Found {len(rows)} sensor error events in {os.path.basename(csv_path)}")
        
        # Calculate cutoff time (6 days ago)
        cutoff_time = datetime.now() - timedelta(days=MAX_AGE_DAYS)
        cutoff_timestamp = int(cutoff_time.timestamp() * 1000000000)  # nanoseconds
        
        # Prepare Loki payload - use single stream for all events
        current_time = int(time.time() * 1000000000)  # nanoseconds
        values = []
        skipped_old = 0
        skipped_future = 0
        
        # Create progress bar
        progress = None
        if PROGRESS_BAR_AVAILABLE:
            progress = ProgressBar(len(rows), desc="Preparing data for Loki", width=50)
        
        # Collect all log entries with timestamps
        for i, row in enumerate(rows):
            if progress:
                progress.set_current(i + 1)
            # Try to parse timestamp from CSV if available
            timestamp = current_time + (i * 1000000000)
            timestamp_parsed = False
            
            if 'datetime' in row and row['datetime']:
                try:
                    dt = datetime.strptime(row['datetime'], "%Y-%m-%d %H:%M:%S.%f")
                    timestamp = int(dt.timestamp() * 1000000000)
                    timestamp_parsed = True
                except ValueError:
                    # Try without microseconds
                    try:
                        dt = datetime.strptime(row['datetime'], "%Y-%m-%d %H:%M:%S")
                        timestamp = int(dt.timestamp() * 1000000000)
                        timestamp_parsed = True
                    except:
                        pass
            elif 'date' in row and 'time' in row and row['date'] and row['time']:
                try:
                    dt = datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M:%S.%f")
                    timestamp = int(dt.timestamp() * 1000000000)
                    timestamp_parsed = True
                except ValueError:
                    # Try without microseconds
                    try:
                        dt = datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M:%S")
                        timestamp = int(dt.timestamp() * 1000000000)
                        timestamp_parsed = True
                    except:
                        pass
            
            # Filter out entries that are too old (older than MAX_AGE_DAYS)
            if timestamp_parsed:
                if timestamp < cutoff_timestamp:
                    skipped_old += 1
                    continue
                # Also filter out future entries (more than 1 hour in the future)
                future_threshold = int((datetime.now() + timedelta(hours=1)).timestamp() * 1000000000)
                if timestamp > future_threshold:
                    skipped_future += 1
                    continue
            
            # Format row as JSON log entry
            log_message = json.dumps(row, ensure_ascii=False)
            
            # Add to values array
            values.append([str(timestamp), log_message])
        
        if progress:
            progress.close()
        
        # Report filtering results
        if skipped_old > 0:
            print(f"   ⚠️  Skipped {skipped_old} entries older than {MAX_AGE_DAYS} days (Loki rejects old samples)")
        if skipped_future > 0:
            print(f"   ⚠️  Skipped {skipped_future} entries with future timestamps")
        
        if not values:
            print(f"   ⚠️  No valid entries to push (all entries were filtered out)")
            return False
        
        print(f"   ✅ {len(values)} entries ready to push (filtered from {len(rows)} total)")
        
        # Create single stream with all values
        stream = {
            "stream": {
                "job": f"{game_type}_roulette_sensor_errors",
                "instance": "GC-ARO-001-1",
                "game_type": game_type,
                "event_type": "sensor_error",
                "source": "sensor_err_table"
            },
            "values": values
        }
        
        # Prepare payload
        payload = {"streams": [stream]}
        
        # Push to Loki
        print(f"\n📤 Pushing {len(values)} sensor error events to Loki server...")
        print(f"   URL: {LOKI_URL}")
        
        if PROGRESS_BAR_AVAILABLE:
            print("   ⏳ Uploading... (this may take a while for large files)")
        
        response = requests.post(
            LOKI_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60  # Longer timeout for large files
        )
        
        if response.status_code == 204:
            print(f"✅ Successfully pushed {len(rows)} sensor error events to Loki")
            return True
        else:
            print(f"❌ Failed to push to Loki: HTTP {response.status_code}")
            if response.text:
                print(f"   Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: Cannot connect to Loki server at {LOKI_URL}")
        print(f"   Error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout error: Request to Loki server timed out")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error pushing CSV {os.path.basename(csv_path)} to Loki: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Push sensor error CSV files to remote Loki server"
    )
    parser.add_argument(
        "--game-type",
        choices=["speed", "vip", "both"],
        default="both",
        help="Game type to process (default: both)"
    )
    parser.add_argument(
        "--csv-file",
        type=str,
        help="Specific CSV file to push (overrides --game-type)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Push Sensor Error Events to Loki Server")
    print("=" * 60)
    print(f"Loki Server: {LOKI_URL}")
    print()
    
    success = True
    
    if args.csv_file:
        # Push specific file
        if not os.path.exists(args.csv_file):
            print(f"❌ File not found: {args.csv_file}")
            return
        
        # Determine game type from filename
        filename = os.path.basename(args.csv_file)
        if "speed" in filename.lower():
            game_type = "speed"
        elif "vip" in filename.lower():
            game_type = "vip"
        else:
            print("⚠️  Cannot determine game type from filename, using 'speed'")
            game_type = "speed"
        
        if not push_csv_to_loki(args.csv_file, game_type):
            success = False
    else:
        # Push based on game type
        csv_files = []
        
        if args.game_type in ["speed", "both"]:
            speed_csv = os.path.join(STUDIO_SDP_DIR, "speed_sensor_err_table.csv")
            if os.path.exists(speed_csv):
                csv_files.append((speed_csv, "speed"))
        
        if args.game_type in ["vip", "both"]:
            vip_csv = os.path.join(STUDIO_SDP_DIR, "vip_sensor_err_table.csv")
            if os.path.exists(vip_csv):
                csv_files.append((vip_csv, "vip"))
        
        if not csv_files:
            print("❌ No sensor error CSV files found!")
            print("\nExpected files:")
            if args.game_type in ["speed", "both"]:
                print("   - speed_sensor_err_table.csv")
            if args.game_type in ["vip", "both"]:
                print("   - vip_sensor_err_table.csv")
            return
        
        for csv_file, game_type in csv_files:
            print(f"\n📋 Processing {game_type.upper()} sensor errors...")
            if not push_csv_to_loki(csv_file, game_type):
                success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All sensor error events pushed to Loki successfully")
    else:
        print("❌ Some errors occurred while pushing to Loki")
    print("=" * 60)


if __name__ == "__main__":
    main()

