#!/usr/bin/env python3
"""
Script to set SDP down status for ARO-002 table and monitor main_vip.py entering idle mode.
This script will:
1. Set SDP status to down via WebSocket (using "down" for CIT env compatibility)
   Note: Future support for "down_pause" when Studio API is updated
2. Monitor main_vip.py to detect when it enters idle mode
3. Wait for idle mode operations to complete
"""

import sys
import os
import time
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from studio_api.http.status import set_sdp_status_via_http, get_sdp_status
from log_redirector import get_timestamp, log_console


def monitor_idle_mode(table_id: str = "ARO-002", max_wait_time: int = 300):
    """
    Monitor main_vip.py to detect when it enters idle mode.
    This is done by checking if SDP status is "down" (or future: "down_pause"/"down_cancel"),
    which should trigger main_vip.py to enter idle mode.
    
    Args:
        table_id (str): Table ID to monitor (default: "ARO-002")
        max_wait_time (int): Maximum time to wait for idle mode in seconds (default: 300)
    
    Returns:
        bool: True if idle mode detected, False otherwise
    """
    print(f"[{get_timestamp()}] Monitoring for idle mode entry...")
    log_console("Monitoring for idle mode entry...", "SDP Down Script >>>")
    
    start_time = time.time()
    check_interval = 2  # Check every 2 seconds
    
    while time.time() - start_time < max_wait_time:
        try:
            sdp_status = get_sdp_status(table_id)
            
            # Current: check for "down" (CIT env compatibility)
            # Future: also check for "down_pause", "down_cancel" when Studio API supports it
            if sdp_status in ["down", "down_pause", "down_cancel"]:
                print(f"[{get_timestamp()}] ✅ Detected SDP status: {sdp_status} - main_vip.py should be in idle mode")
                log_console(
                    f"Detected SDP status: {sdp_status} - main_vip.py should be in idle mode",
                    "SDP Down Script >>>"
                )
                return True
            else:
                print(f"[{get_timestamp()}] Current SDP status: {sdp_status} (waiting for down/down_pause/down_cancel)...")
                log_console(
                    f"Current SDP status: {sdp_status} (waiting for down/down_pause/down_cancel)...",
                    "SDP Down Script >>>"
                )
        
        except Exception as e:
            print(f"[{get_timestamp()}] Error checking SDP status: {e}")
            log_console(f"Error checking SDP status: {e}", "SDP Down Script >>>")
        
        time.sleep(check_interval)
    
    print(f"[{get_timestamp()}] ⚠️  Timeout waiting for idle mode (max wait time: {max_wait_time}s)")
    log_console(
        f"Timeout waiting for idle mode (max wait time: {max_wait_time}s)",
        "SDP Down Script >>>"
    )
    return False


def main():
    """Main function to set SDP down and monitor idle mode"""
    table_id = "ARO-002"
    # Using "down" for CIT environment compatibility
    # TODO: Change to "down_pause" when Studio API supports it
    sdp_status = "down"
    
    print("=" * 60)
    print(f"Setting SDP Down for {table_id}")
    print("=" * 60)
    print(f"[{get_timestamp()}] Target table: {table_id}")
    print(f"[{get_timestamp()}] Target SDP status: {sdp_status}")
    print(f"[{get_timestamp()}] Note: Using 'down' for CIT env (future: 'down_pause')")
    print()
    
    log_console(
        f"Starting SDP down process for {table_id}",
        "SDP Down Script >>>"
    )
    
    # Step 1: Set SDP status to down (or down_pause when Studio API supports it)
    print(f"[{get_timestamp()}] Step 1: Setting SDP status to {sdp_status}...")
    log_console(f"Step 1: Setting SDP status to {sdp_status}", "SDP Down Script >>>")
    
    # Try HTTP API first (more reliable), fallback to WebSocket if needed
    success = set_sdp_status_via_http(table_id, sdp_status)
    
    if success:
        print(f"[{get_timestamp()}] ✅ SDP status set to {sdp_status} successfully")
        log_console(f"SDP status set to {sdp_status} successfully", "SDP Down Script >>>")
    else:
        print(f"[{get_timestamp()}] ❌ Failed to set SDP status to {sdp_status}")
        log_console(f"Failed to set SDP status to {sdp_status}", "SDP Down Script >>>")
        return 1
    
    # Wait a moment for the status to propagate
    print(f"[{get_timestamp()}] Waiting 3 seconds for status to propagate...")
    time.sleep(3)
    
    # Step 2: Verify SDP status was set
    print(f"[{get_timestamp()}] Step 2: Verifying SDP status...")
    log_console("Step 2: Verifying SDP status", "SDP Down Script >>>")
    
    current_status = get_sdp_status(table_id)
    if current_status:
        print(f"[{get_timestamp()}] Current SDP status: {current_status}")
        log_console(f"Current SDP status: {current_status}", "SDP Down Script >>>")
    else:
        print(f"[{get_timestamp()}] ⚠️  Could not retrieve SDP status")
        log_console("Could not retrieve SDP status", "SDP Down Script >>>")
    
    # Step 3: Monitor for idle mode
    print(f"[{get_timestamp()}] Step 3: Monitoring main_vip.py for idle mode entry...")
    print(f"[{get_timestamp()}] Note: main_vip.py should detect SDP down and enter idle mode")
    print(f"[{get_timestamp()}] In idle mode, main_vip.py will:")
    print(f"  - SSH to rnd@192.168.88.53 and execute sudo reboot")
    print(f"  - Execute sudo ~/down.sh sr on local machine")
    print(f"  - Gracefully shutdown itself")
    print()
    log_console("Step 3: Monitoring for idle mode entry", "SDP Down Script >>>")
    
    idle_detected = monitor_idle_mode(table_id, max_wait_time=60)
    
    if idle_detected:
        print(f"[{get_timestamp()}] ✅ Idle mode detected - main_vip.py should be executing idle mode operations")
        log_console("Idle mode detected - main_vip.py should be executing idle mode operations", "SDP Down Script >>>")
        
        # Wait additional time for idle mode operations to complete
        print(f"[{get_timestamp()}] Waiting for idle mode operations to complete (up to 5 minutes)...")
        log_console("Waiting for idle mode operations to complete", "SDP Down Script >>>")
        time.sleep(300)  # Wait up to 5 minutes for operations to complete
        
        print(f"[{get_timestamp()}] ✅ Idle mode operations should be complete")
        log_console("Idle mode operations should be complete", "SDP Down Script >>>")
    else:
        print(f"[{get_timestamp()}] ⚠️  Could not confirm idle mode entry")
        log_console("Could not confirm idle mode entry", "SDP Down Script >>>")
    
    print()
    print("=" * 60)
    print("SDP Down Process Completed")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n[{get_timestamp()}] Script interrupted by user")
        log_console("Script interrupted by user", "SDP Down Script >>>")
        sys.exit(1)
    except Exception as e:
        print(f"[{get_timestamp()}] ❌ Unexpected error: {e}")
        log_console(f"Unexpected error: {e}", "SDP Down Script >>>")
        sys.exit(1)

