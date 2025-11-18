#!/usr/bin/env python3
"""
Verify Loki logs for ARO-001-2 using Loki Query API
Checks if logs from GC-ARO-001-2 are successfully pushed to Loki
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from env_detect import detect_environment, get_hostname


# Loki server configuration
LOKI_BASE_URL = "http://100.64.0.113:3100"
LOKI_QUERY_RANGE_URL = f"{LOKI_BASE_URL}/loki/api/v1/query_range"
LOKI_QUERY_URL = f"{LOKI_BASE_URL}/loki/api/v1/query"
LOKI_LABELS_URL = f"{LOKI_BASE_URL}/loki/api/v1/labels"


def query_loki_range(
    query: str,
    start_time: datetime,
    end_time: datetime,
    limit: int = 1000
) -> Optional[Dict]:
    """
    Query Loki using query_range API (for time range queries)
    
    Args:
        query: LogQL query string
        start_time: Start time for query
        end_time: End time for query
        limit: Maximum number of results (default: 1000)
    
    Returns:
        Dict with query results or None if error
    """
    try:
        # Convert datetime to nanoseconds (Unix timestamp in nanoseconds)
        start_ns = int(start_time.timestamp() * 1e9)
        end_ns = int(end_time.timestamp() * 1e9)
        
        params = {
            "query": query,
            "start": start_ns,
            "end": end_ns,
            "limit": limit
        }
        
        response = requests.get(LOKI_QUERY_RANGE_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Query failed: HTTP {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: Cannot connect to Loki server at {LOKI_BASE_URL}")
        print(f"   Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error querying Loki: {e}")
        return None


def query_loki_instant(query: str, limit: int = 100) -> Optional[Dict]:
    """
    Query Loki using query API (for instant queries)
    
    Args:
        query: LogQL query string
        limit: Maximum number of results (default: 100)
    
    Returns:
        Dict with query results or None if error
    """
    try:
        params = {
            "query": query,
            "limit": limit
        }
        
        response = requests.get(LOKI_QUERY_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Query failed: HTTP {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: Cannot connect to Loki server at {LOKI_BASE_URL}")
        print(f"   Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error querying Loki: {e}")
        return None


def get_loki_labels() -> Optional[List[str]]:
    """
    Get available labels from Loki
    
    Returns:
        List of label names or None if error
    """
    try:
        response = requests.get(LOKI_LABELS_URL, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        else:
            print(f"❌ Failed to get labels: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting labels: {e}")
        return None


def verify_aro_001_2_logs(hours_back: int = 24) -> bool:
    """
    Verify if logs from GC-ARO-001-2 are successfully pushed to Loki
    
    Args:
        hours_back: Number of hours to look back (default: 24)
    
    Returns:
        bool: True if logs found, False otherwise
    """
    print("=" * 60)
    print("Verifying ARO-001-2 Logs in Loki")
    print("=" * 60)
    print(f"Loki Server: {LOKI_BASE_URL}")
    print()
    
    # Detect environment to get the correct instance name
    detected_table_code, detected_hostname, env_detection_success = detect_environment()
    
    if env_detection_success and detected_hostname:
        instance_name = detected_hostname
        print(f"✅ Environment detected: {detected_table_code}")
        print(f"   Instance name: {instance_name}")
    else:
        # Use expected instance name for ARO-001-2
        instance_name = "GC-ARO-001-2"
        print(f"⚠️  Environment detection failed, using expected instance: {instance_name}")
    
    print()
    
    # Check available labels first
    print("📋 Checking available labels in Loki...")
    labels = get_loki_labels()
    if labels:
        print(f"   Available labels: {', '.join(labels[:10])}{'...' if len(labels) > 10 else ''}")
    else:
        print("   ⚠️  Could not retrieve labels")
    print()
    
    # Build LogQL query
    # Query for speed roulette logs from GC-ARO-001-2
    query = f'{{job="speed_roulette_logs", instance="{instance_name}"}}'
    
    print(f"🔍 Query: {query}")
    print(f"   Time range: Last {hours_back} hours")
    print()
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours_back)
    
    # Query Loki
    print("📤 Querying Loki...")
    result = query_loki_range(query, start_time, end_time, limit=100)
    
    if not result:
        print("❌ Failed to query Loki")
        return False
    
    # Parse results
    status = result.get("status", "unknown")
    data = result.get("data", {})
    result_type = data.get("resultType", "unknown")
    streams = data.get("result", [])
    
    print(f"✅ Query successful (status: {status}, type: {result_type})")
    print()
    
    if not streams:
        print(f"⚠️  No logs found for instance '{instance_name}' in the last {hours_back} hours")
        print()
        print("💡 Suggestions:")
        print("   1. Check if push_speed_log_continuous.py is running")
        print("   2. Verify the instance name matches the hostname")
        print("   3. Check if logs are being generated")
        print("   4. Try querying with a longer time range")
        return False
    
    # Count total log entries
    total_entries = 0
    unique_streams = len(streams)
    
    print(f"📊 Results:")
    print(f"   Found {unique_streams} unique stream(s)")
    
    # Show sample of streams
    for i, stream in enumerate(streams[:5], 1):  # Show first 5 streams
        stream_labels = stream.get("stream", {})
        values = stream.get("values", [])
        total_entries += len(values)
        
        print(f"\n   Stream {i}:")
        print(f"      Labels: {stream_labels}")
        print(f"      Entries: {len(values)}")
        
        # Show first log entry as sample
        if values:
            first_entry = values[0]
            timestamp_ns = first_entry[0]
            log_message = first_entry[1]
            
            # Convert nanoseconds to datetime
            timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1e9)
            print(f"      First entry: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Try to parse JSON log message
            try:
                log_data = json.loads(log_message)
                log_type = log_data.get("type", "unknown")
                direction = log_data.get("direction", "unknown")
                message_preview = log_data.get("message", "")[:100]
                print(f"      Sample: [{log_type}] {direction} {message_preview}...")
            except:
                print(f"      Sample: {log_message[:100]}...")
    
    # Count remaining streams
    if len(streams) > 5:
        remaining_entries = sum(len(s.get("values", [])) for s in streams[5:])
        total_entries += remaining_entries
        print(f"\n   ... and {len(streams) - 5} more stream(s) with {remaining_entries} entries")
    
    print()
    print(f"✅ Total log entries found: {total_entries}")
    print(f"   Time range: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Show recent log entries
    print("📝 Recent log entries (last 10):")
    print("-" * 60)
    
    # Collect all entries and sort by timestamp
    all_entries = []
    for stream in streams:
        for entry in stream.get("values", []):
            timestamp_ns = entry[0]
            log_message = entry[1]
            all_entries.append((int(timestamp_ns), log_message))
    
    # Sort by timestamp (descending) and take last 10
    all_entries.sort(key=lambda x: x[0], reverse=True)
    
    for timestamp_ns, log_message in all_entries[:10]:
        timestamp = datetime.fromtimestamp(timestamp_ns / 1e9)
        
        # Try to parse JSON log message
        try:
            log_data = json.loads(log_message)
            log_type = log_data.get("type", "unknown")
            direction = log_data.get("direction", "unknown")
            message = log_data.get("message", "")
            print(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] [{log_type}] {direction} {message[:80]}")
        except:
            print(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {log_message[:80]}")
    
    print("-" * 60)
    print()
    print("✅ Verification complete: Logs are successfully pushed to Loki!")
    
    return True


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify ARO-001-2 logs in Loki using Query API"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to look back (default: 24)"
    )
    parser.add_argument(
        "--instance",
        type=str,
        help="Override instance name (default: auto-detect from hostname)"
    )
    
    args = parser.parse_args()
    
    success = verify_aro_001_2_logs(hours_back=args.hours)
    
    if not success:
        print("❌ Verification failed")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

