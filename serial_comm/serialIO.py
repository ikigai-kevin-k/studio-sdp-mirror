#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serial I/O module for Speed Roulette Controller
Handles serial communication and data processing
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Global lock for detection scheduling to prevent race conditions
_detection_scheduling_lock = threading.Lock()

# Import log redirector for separated logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from log_redirector import log_mqtt, log_api, log_serial, log_console, get_timestamp

# Global variables for auto-recovery from *X;6
_auto_recovery_state = {
    "active": False,  # Whether auto-recovery is currently active
    "p_ok_received": False,  # Whether *P OK has been received
    "x2_restored": False,  # Whether *X;2 has been restored
    "recovery_start_time": None,  # When recovery started
    "p1_send_count": 0,  # Number of *P 1 commands sent
}


def _send_p1_repeatedly(ser, get_timestamp, log_to_file, duration=10, interval=1):
    """
    Send *P 1 command repeatedly for specified duration
    
    Args:
        ser: Serial connection object
        get_timestamp: Function to get timestamp
        log_to_file: Function to log messages
        duration: Total duration in seconds (default 10)
        interval: Interval between sends in seconds (default 1)
    """
    global _auto_recovery_state
    
    if ser is None:
        log_serial("Warning: Serial connection not available, cannot send *P 1")
        return
    
    start_time = time.time()
    send_count = 0
    
    while (time.time() - start_time) < duration and _auto_recovery_state["active"]:
        try:
            ser.write(("*P 1\r\n").encode())
            send_count += 1
            _auto_recovery_state["p1_send_count"] = send_count
            log_serial(f"*P 1 (attempt {send_count})", "Send <<<")
            log_to_file("*P 1", "Send <<<")
            print(f"[{get_timestamp()}] Sent *P 1 command (attempt {send_count})")
        except Exception as e:
            print(f"[{get_timestamp()}] Error sending *P 1: {e}")
            log_to_file(f"Error sending *P 1: {e}", "Error >>>")
        
        # Wait for interval, but check if recovery succeeded
        elapsed = time.time() - start_time
        remaining = duration - elapsed
        if remaining > 0:
            time.sleep(min(interval, remaining))
    
    print(f"[{get_timestamp()}] Finished sending *P 1 commands (total: {send_count})")
    log_to_file(f"Finished sending *P 1 commands (total: {send_count})", "Auto-Recovery >>>")


def _continue_game_from_state(
    global_vars,
    ser,
    tables,
    token,
    get_timestamp,
    log_to_file,
    execute_start_post,
    execute_deal_post,
    execute_finish_post,
    send_start_recording,
    betStop_round_for_table,
):
    """
    Continue game execution based on current game state
    
    Args:
        global_vars: Dictionary containing game state variables
        ser: Serial connection object
        tables: Table configuration list
        token: Authentication token
        get_timestamp: Function to get timestamp
        log_to_file: Function to log messages
        execute_start_post: Function to execute start post
        execute_deal_post: Function to execute deal post
        execute_finish_post: Function to execute finish post
        send_start_recording: Function to send start recording
        betStop_round_for_table: Function to call bet stop
    """
    print(f"[{get_timestamp()}] Continuing game from saved state...")
    log_to_file("Continuing game from saved state...", "Auto-Recovery >>>")
    
    # Determine current game state and continue from where we left off
    if global_vars.get("start_post_sent", False):
        if not global_vars.get("u1_sent", False):
            # Continue with *u 1, betStop, deal, finish
            print(f"[{get_timestamp()}] Resuming from start: sending *u 1 (betStop, deal, finish will follow)")
            log_to_file("Resuming from start: sending *u 1 (betStop, deal, finish will follow)", "Auto-Recovery >>>")
            
            # Send *u 1
            if ser is not None:
                ser.write(("*u 1\r\n").encode())
                log_to_file("*u 1", "Send <<<")
                print(f"[{get_timestamp()}] Sent *u 1 command")
                global_vars["u1_sent"] = True
            else:
                print(f"[{get_timestamp()}] Warning: Serial connection not available, cannot send *u 1")
            
            # Note: betStop, deal, and finish will be handled by normal game flow
            # when *X;3 triggers betStop and *X;5 triggers deal and finish
            
        elif not global_vars.get("betStop_sent", False):
            # Continue with betStop, deal, finish
            print(f"[{get_timestamp()}] Resuming from *u 1: betStop, deal, finish will follow")
            log_to_file("Resuming from *u 1: betStop, deal, finish will follow", "Auto-Recovery >>>")
            
            # Note: betStop, deal, and finish will be handled by normal game flow
            # when *X;3 triggers betStop and *X;5 triggers deal and finish
            
        elif not global_vars.get("deal_post_sent", False):
            # Continue with deal, finish
            print(f"[{get_timestamp()}] Resuming from betStop: deal, finish will follow")
            log_to_file("Resuming from betStop: deal, finish will follow", "Auto-Recovery >>>")
            
            # Note: deal and finish will be handled by normal game flow
            # when *X;5 triggers deal and finish
            
        elif not global_vars.get("finish_post_sent", False):
            # Continue with finish
            print(f"[{get_timestamp()}] Resuming from deal: finish will follow")
            log_to_file("Resuming from deal: finish will follow", "Auto-Recovery >>>")
            
            # Note: finish will be handled by normal game flow
            # when *X;5 triggers finish
            
        else:
            # All steps completed, start next round
            print(f"[{get_timestamp()}] All steps completed, will start next round on *X;2")
            log_to_file("All steps completed, will start next round on *X;2", "Auto-Recovery >>>")
    else:
        # No start sent yet, will start on next *X;2
        print(f"[{get_timestamp()}] No start sent yet, will start on next *X;2")
        log_to_file("No start sent yet, will start on next *X;2", "Auto-Recovery >>>")


def read_from_serial(
    ser,
    tables,
    token,
    # Global state variables (passed by reference)
    global_vars,
    # Callback functions
    get_timestamp,
    log_to_file,
    send_sensor_error_to_slack,
    execute_broadcast_post,
    execute_start_post,
    execute_deal_post,
    execute_finish_post,
    send_start_recording,
    send_stop_recording,
    log_time_intervals,
    send_websocket_error_signal=None,  # Optional callback for WebSocket error signal (sensor stuck)
    send_websocket_wrong_ball_dir_error_signal=None,  # Optional callback for WebSocket wrong ball direction error signal
):
    """
    Read and process serial data with non-blocking approach

    Args:
        ser: Serial connection object
        tables: Table configuration list
        token: Authentication token
        global_vars: Dictionary containing all global state variables
        # Callback functions for various operations
    """

    # Set startup time for startup condition detection
    read_from_serial.startup_time = time.time()
    log_serial("Serial read thread started, startup time recorded")

    while True:
        # Check if program should terminate
        if global_vars.get("terminate_program", False):
            log_serial("Serial read thread terminating due to program termination flag")
            break
            
        # Check if serial connection is available
        if ser is None:
            log_serial("Warning: Serial connection not available, skipping serial read")
            time.sleep(5)  # Wait 5 seconds before checking again
            continue

        if ser.in_waiting > 0:
            # Non-blocking read approach
            raw_data = ser.read(ser.in_waiting)
            data_str = raw_data.decode("utf-8", errors="ignore")

            # Add to buffer and process complete lines
            if not hasattr(read_from_serial, "buffer"):
                read_from_serial.buffer = ""
            read_from_serial.buffer += data_str

            # Process complete lines from buffer
            while "\n" in read_from_serial.buffer:
                line, read_from_serial.buffer = read_from_serial.buffer.split(
                    "\n", 1
                )
                line = line.strip()
                if line:
                    log_serial(f"Receive >>> {line}")
                    log_to_file(line, "Receive >>>")
                    data = line  # Use the current line for processing

                    # Handle *X;6 sensor error messages - trigger on ANY *X;6 message
                    if "*X;6" in data:
                        try:
                            parts = data.split(";")
                            warning_flag = parts[4] if len(parts) >= 5 else "unknown"
                            print(
                                f"[{get_timestamp()}] Detected *X;6 message with warning_flag: {warning_flag}"
                            )
                            log_to_file(
                                f"Detected *X;6 message with warning_flag: {warning_flag}",
                                "Receive >>>",
                            )

                            # Check if this is a startup condition (warning_flag=0 and recently started)
                            current_time = time.time()
                            startup_threshold = 30  # 30 seconds after startup
                            
                            # Check if we're in startup phase and warning_flag is 0
                            if (warning_flag == "0" and 
                                hasattr(read_from_serial, "startup_time") and 
                                current_time - read_from_serial.startup_time < startup_threshold):
                                print(
                                    f"[{get_timestamp()}] *X;6 with warning_flag=0 detected during startup phase, ignoring (normal behavior)"
                                )
                                log_to_file(
                                    "*X;6 with warning_flag=0 detected during startup phase, ignoring (normal behavior)",
                                    "Receive >>>",
                                )
                                continue  # Skip error handling for startup condition

                            # Start auto-recovery process for *X;6 message (not startup condition)
                            global _auto_recovery_state
                            
                            # Check if auto-recovery is already active
                            if _auto_recovery_state["active"]:
                                print(
                                    f"[{get_timestamp()}] Auto-recovery already active, ignoring duplicate *X;6"
                                )
                                log_to_file(
                                    "Auto-recovery already active, ignoring duplicate *X;6",
                                    "Receive >>>",
                                )
                                continue
                            
                            print(
                                f"[{get_timestamp()}] *X;6 MESSAGE detected! Starting auto-recovery process..."
                            )
                            log_to_file(
                                "*X;6 MESSAGE detected! Starting auto-recovery process...",
                                "Receive >>>",
                            )
                            
                            # Initialize auto-recovery state
                            _auto_recovery_state["active"] = True
                            _auto_recovery_state["p_ok_received"] = False
                            _auto_recovery_state["x2_restored"] = False
                            _auto_recovery_state["recovery_start_time"] = current_time
                            _auto_recovery_state["p1_send_count"] = 0
                            
                            # Start sending *P 1 commands in a separate thread
                            def auto_recovery_thread():
                                global _auto_recovery_state
                                
                                # Send *P 1 commands for 10 seconds, every 1 second
                                _send_p1_repeatedly(ser, get_timestamp, log_to_file, duration=10, interval=1)
                                
                                # Wait up to 20 seconds total for recovery (10s for P1 + 10s for recovery)
                                recovery_timeout = 20
                                elapsed = time.time() - _auto_recovery_state["recovery_start_time"]
                                
                                while elapsed < recovery_timeout and _auto_recovery_state["active"]:
                                    time.sleep(0.5)  # Check every 0.5 seconds
                                    elapsed = time.time() - _auto_recovery_state["recovery_start_time"]
                                    
                                    # Check if recovery succeeded
                                    if _auto_recovery_state["p_ok_received"] and _auto_recovery_state["x2_restored"]:
                                        print(
                                            f"[{get_timestamp()}] Auto-recovery SUCCESS! *P OK received and *X;2 restored"
                                        )
                                        log_to_file(
                                            "Auto-recovery SUCCESS! *P OK received and *X;2 restored",
                                            "Auto-Recovery >>>",
                                        )
                                        
                                        # Continue game from saved state
                                        try:
                                            # Import betStop function
                                            import sys
                                            import os
                                            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                            
                                            betStop_round_for_table = None
                                            if 'main_speed' in sys.modules:
                                                from main_speed import betStop_round_for_table
                                            else:
                                                main_script = sys.argv[0] if sys.argv else ''
                                                if 'main_speed' in main_script:
                                                    from main_speed import betStop_round_for_table
                                            
                                            _continue_game_from_state(
                                                global_vars,
                                                ser,
                                                tables,
                                                token,
                                                get_timestamp,
                                                log_to_file,
                                                execute_start_post,
                                                execute_deal_post,
                                                execute_finish_post,
                                                send_start_recording,
                                                betStop_round_for_table,
                                            )
                                        except Exception as e:
                                            print(f"[{get_timestamp()}] Error continuing game: {e}")
                                            log_to_file(f"Error continuing game: {e}", "Error >>>")
                                        
                                        # Reset auto-recovery state
                                        _auto_recovery_state["active"] = False
                                        return
                                
                                # Recovery failed or timeout
                                if _auto_recovery_state["active"]:
                                    print(
                                        f"[{get_timestamp()}] Auto-recovery FAILED or TIMEOUT! Sending sensor error notification..."
                                    )
                                    log_to_file(
                                        "Auto-recovery FAILED or TIMEOUT! Sending sensor error notification...",
                                        "Auto-Recovery >>>",
                                    )
                                    
                                    # Send sensor error notification to Slack
                                    try:
                                        send_sensor_error_to_slack()
                                        
                                        # Send WebSocket error signal
                                        if send_websocket_error_signal is not None:
                                            send_websocket_error_signal()
                                        
                                        # Send broadcast_post for sensor stuck error
                                        current_time_broadcast = time.time()
                                        broadcast_type_sensor_stuck = "roulette.sensor_stuck"
                                        last_broadcast_key_sensor_stuck = f"last_broadcast_time_{broadcast_type_sensor_stuck}"
                                        
                                        if (
                                            not hasattr(execute_broadcast_post, last_broadcast_key_sensor_stuck)
                                            or (current_time_broadcast - getattr(execute_broadcast_post, last_broadcast_key_sensor_stuck, 0)) >= 10
                                        ):
                                            print(f"[{get_timestamp()}] Sending broadcast_post ({broadcast_type_sensor_stuck})...")
                                            log_to_file(f"Sending broadcast_post ({broadcast_type_sensor_stuck})...", "Broadcast >>>")
                                            
                                            with ThreadPoolExecutor(max_workers=len(tables)) as executor:
                                                futures = [
                                                    executor.submit(execute_broadcast_post, table, token, broadcast_type_sensor_stuck)
                                                    for table in tables
                                                ]
                                                for future in futures:
                                                    future.result()
                                            
                                            setattr(execute_broadcast_post, last_broadcast_key_sensor_stuck, current_time_broadcast)
                                        
                                        # Set termination flag
                                        global_vars["terminate_program"] = True
                                        
                                    except Exception as e:
                                        print(f"[{get_timestamp()}] Error sending sensor error notification: {e}")
                                        log_to_file(f"Error sending sensor error notification: {e}", "Error >>>")
                                        global_vars["terminate_program"] = True
                                    
                                    # Reset auto-recovery state
                                    _auto_recovery_state["active"] = False
                            
                            # Start auto-recovery thread
                            recovery_thread = threading.Thread(target=auto_recovery_thread, daemon=True)
                            recovery_thread.start()
                            
                        except Exception as e:
                            print(
                                f"[{get_timestamp()}] Error parsing *X;6 message: {e}"
                            )
                            log_to_file(
                                f"Error parsing *X;6 message: {e}", "Error >>>"
                            )
                            # Reset auto-recovery state on error
                            _auto_recovery_state["active"] = False

                    # Handle *P OK response
                    if "*P OK" in data:
                        global _auto_recovery_state
                        if _auto_recovery_state["active"]:
                            _auto_recovery_state["p_ok_received"] = True
                            print(
                                f"[{get_timestamp()}] Received *P OK during auto-recovery"
                            )
                            log_to_file(
                                "Received *P OK during auto-recovery",
                                "Auto-Recovery >>>",
                            )

                    # Handle *X;2 count
                    if "*X;2" in data:
                        current_time = time.time()
                        if current_time - global_vars["last_x2_time"] > 5:
                            global_vars["x2_count"] = 1
                        else:
                            global_vars["x2_count"] += 1
                        global_vars["last_x2_time"] = current_time
                        
                        # Check if this is recovery from *X;6
                        global _auto_recovery_state
                        if _auto_recovery_state["active"]:
                            _auto_recovery_state["x2_restored"] = True
                            print(
                                f"[{get_timestamp()}] Received *X;2 during auto-recovery - state restored!"
                            )
                            log_to_file(
                                "Received *X;2 during auto-recovery - state restored!",
                                "Auto-Recovery >>>",
                            )

                        # Check if warning_flag is not 0, if so send broadcast_post and error signal
                        try:
                            parts = data.split(";")
                            if (
                                len(parts) >= 5
                            ):  # Ensure there are enough parts to get warning_flag
                                warning_flag = parts[4]
                                current_time = time.time()

                                # Check if warning_flag is not 0 (any warning condition)
                                if warning_flag != "0":
                                    print(
                                        f"[{get_timestamp()}] Detected *X;2 message with warning_flag: {warning_flag}"
                                    )
                                    log_to_file(
                                        f"Detected *X;2 message with warning_flag: {warning_flag}",
                                        "Receive >>>",
                                    )

                                    # Send error signal for warning conditions
                                    print(
                                        f"[{get_timestamp()}] *X;2 WARNING detected! Sending error signal..."
                                    )
                                    log_to_file(
                                        "*X;2 WARNING detected! Sending error signal...",
                                        "Receive >>>",
                                    )

                                    # Use callback functions if provided, otherwise try to import
                                    # Choose error signal based on warning_flag
                                    try:
                                        # Send sensor error notification to Slack (already passed as callback)
                                        send_sensor_error_to_slack()

                                        # Send WebSocket error signal based on warning_flag
                                        # warning_flag == 2: Wrong ball direction error
                                        # warning_flag == 4: Sensor stuck error
                                        # Other: Use sensor stuck error (default)
                                        if warning_flag == "2":
                                            # Send wrong ball direction error signal
                                            if send_websocket_wrong_ball_dir_error_signal is not None:
                                                send_websocket_wrong_ball_dir_error_signal()
                                            elif send_websocket_error_signal is not None:
                                                # Fallback to sensor stuck if wrong ball dir not available
                                                send_websocket_error_signal()
                                            else:
                                                # Fallback: try to import from main_speed (for backward compatibility)
                                                import sys
                                                import os
                                                sys.path.append(
                                                    os.path.dirname(
                                                        os.path.dirname(
                                                            os.path.abspath(__file__)
                                                        )
                                                    )
                                                )
                                                from main_speed import send_websocket_error_signal as fallback_send_ws_error
                                                fallback_send_ws_error()
                                        else:
                                            # Send sensor stuck error signal (default for warning_flag 4 and others)
                                            if send_websocket_error_signal is not None:
                                                send_websocket_error_signal()
                                            else:
                                                # Fallback: try to import from main_speed (for backward compatibility)
                                                import sys
                                                import os
                                                sys.path.append(
                                                    os.path.dirname(
                                                        os.path.dirname(
                                                            os.path.abspath(__file__)
                                                        )
                                                    )
                                                )
                                                from main_speed import send_websocket_error_signal as fallback_send_ws_error
                                                fallback_send_ws_error()

                                        print(
                                            f"[{get_timestamp()}] Error signal sent for *X;2 warning_flag: {warning_flag}"
                                        )
                                        log_to_file(
                                            f"Error signal sent for *X;2 warning_flag: {warning_flag}",
                                            "Receive >>>",
                                        )

                                    except ImportError as e:
                                        print(
                                            f"[{get_timestamp()}] Error importing functions for *X;2: {e}"
                                        )
                                        log_to_file(
                                            f"Error importing functions for *X;2: {e}",
                                            "Error >>>",
                                        )
                                    except Exception as e:
                                        print(
                                            f"[{get_timestamp()}] Error calling error signal functions for *X;2: {e}"
                                        )
                                        log_to_file(
                                            f"Error calling error signal functions for *X;2: {e}",
                                            "Error >>>",
                                        )

                                    # Check if warning_flag requires broadcast and determine broadcast_type
                                    broadcast_type = None
                                    if int(warning_flag) == 8:
                                        broadcast_type = "roulette.launch_fail"
                                    elif int(warning_flag) == 2:
                                        broadcast_type = "roulette.wrong_ball_dir"
                                    elif warning_flag == "A":
                                        broadcast_type = "roulette.relaunch"  # Default for flag A
                                    
                                    if broadcast_type:
                                        # Check if 10 seconds have passed or it's the first broadcast
                                        # Use different last_broadcast_time for each broadcast_type
                                        last_broadcast_key = f"last_broadcast_time_{broadcast_type}"
                                        if (
                                            not hasattr(
                                                execute_broadcast_post,
                                                last_broadcast_key,
                                            )
                                            or (
                                                current_time
                                                - getattr(execute_broadcast_post, last_broadcast_key, 0)
                                            )
                                            >= 10
                                        ):

                                            print(
                                                f"\nDetected warning_flag={warning_flag}, sending broadcast_post ({broadcast_type})..."
                                            )
                                            log_to_file(
                                                f"Detected warning_flag={warning_flag}, sending broadcast_post ({broadcast_type})",
                                                "Broadcast >>>",
                                            )

                                            # Send broadcast_post to each table with specific broadcast_type
                                            with ThreadPoolExecutor(
                                                max_workers=len(tables)
                                            ) as executor:
                                                futures = [
                                                    executor.submit(
                                                        execute_broadcast_post,
                                                        table,
                                                        token,
                                                        broadcast_type,
                                                    )
                                                    for table in tables
                                                ]
                                                for future in futures:
                                                    future.result()  # Wait for all requests to complete

                                            # Update last send time for this broadcast_type
                                            setattr(execute_broadcast_post, last_broadcast_key, current_time)
                                        else:
                                            elapsed = current_time - getattr(execute_broadcast_post, last_broadcast_key, 0)
                                            print(
                                                f"Already sent broadcast ({broadcast_type}) {elapsed:.1f} seconds ago, waiting for time interval..."
                                            )
                        except Exception as e:
                            print(
                                f"Error parsing warning_flag or sending error signal: {e}"
                            )
                            log_to_file(
                                f"Error parsing warning_flag or sending error signal: {e}",
                                "Error >>>",
                            )

                        if (
                            global_vars["x2_count"] >= 1
                            and not global_vars["start_post_sent"]
                        ):
                            time.sleep(2)  # for the show result animation time
                            print("\n================Start================")

                            try:
                                global_vars["start_time"] = time.time()
                                print(
                                    f"start_time: {global_vars['start_time']}"
                                )
                                log_to_file(
                                    f"start_time: {global_vars['start_time']}",
                                    "Receive >>>",
                                )

                                if global_vars["finish_post_time"] == 0:
                                    global_vars["finish_post_time"] = (
                                        global_vars["start_time"]
                                    )
                                finish_to_start_time = (
                                    global_vars["start_time"]
                                    - global_vars["finish_post_time"]
                                )
                                print(
                                    f"finish_to_start_time: {finish_to_start_time}"
                                )
                                log_to_file(
                                    f"finish_to_start_time: {finish_to_start_time}",
                                    "Receive >>>",
                                )

                                # Asynchronously process start_post for all tables
                                round_ids = []
                                with ThreadPoolExecutor(
                                    max_workers=len(tables)
                                ) as executor:
                                    futures = [
                                        executor.submit(
                                            execute_start_post, table, token
                                        )
                                        for table in tables
                                    ]
                                    for i, future in enumerate(futures):
                                        result = future.result()  # Wait for all requests to complete
                                        if result and result[0] and result[1]:  # Check if we got valid table and round_id
                                            table, round_id, bet_period = result
                                            round_ids.append((table, round_id, bet_period))

                                global_vars["start_post_sent"] = True
                                global_vars["deal_post_sent"] = False
                                # Reset game state tracking for new round
                                global_vars["u1_sent"] = False
                                global_vars["betStop_sent"] = False
                                global_vars["finish_post_sent"] = False

                                # Start bet stop countdown for each table (non-blocking)
                                for table, round_id, bet_period in round_ids:
                                    if bet_period and bet_period > 0:
                                        # Import betStop_round_for_table function dynamically
                                        import sys
                                        import os
                                        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                        
                                        # Determine which main module is being used based on the main process
                                        main_module = None
                                        if 'main_speed_2' in sys.modules:
                                            main_module = 'main_speed_2'
                                        elif 'main_speed' in sys.modules:
                                            main_module = 'main_speed'
                                        elif 'main_vip_2' in sys.modules:
                                            main_module = 'main_vip_2'
                                        else:
                                            # Check the main script name
                                            main_script = sys.argv[0] if sys.argv else ''
                                            if 'main_speed_2' in main_script:
                                                main_module = 'main_speed_2'
                                            elif 'main_speed' in main_script:
                                                main_module = 'main_speed'
                                            elif 'main_vip_2' in main_script or 'main_vip' in main_script:
                                                main_module = 'main_vip_2'
                                        
                                        # Import the appropriate betStop_round_for_table function
                                        betStop_round_for_table = None
                                        if main_module == 'main_speed_2':
                                            try:
                                                from main_speed_2 import betStop_round_for_table
                                                print(f"[{get_timestamp()}] Using betStop_round_for_table from main_speed_2")
                                            except ImportError as e:
                                                print(f"[{get_timestamp()}] Error importing from main_speed_2: {e}")
                                                betStop_round_for_table = None
                                        elif main_module == 'main_speed':
                                            try:
                                                from main_speed import betStop_round_for_table
                                                print(f"[{get_timestamp()}] Using betStop_round_for_table from main_speed")
                                            except ImportError as e:
                                                print(f"[{get_timestamp()}] Error importing from main_speed: {e}")
                                                betStop_round_for_table = None
                                        elif main_module == 'main_vip_2':
                                            try:
                                                from main_vip_2 import betStop_round_for_table
                                                print(f"[{get_timestamp()}] Using betStop_round_for_table from main_vip_2")
                                            except ImportError as e:
                                                print(f"[{get_timestamp()}] Error importing from main_vip_2: {e}")
                                                betStop_round_for_table = None
                                        else:
                                            # Fallback: try all modules
                                            try:
                                                from main_vip_2 import betStop_round_for_table
                                                print(f"[{get_timestamp()}] Fallback: Using betStop_round_for_table from main_vip_2")
                                            except ImportError:
                                                try:
                                                    from main_speed_2 import betStop_round_for_table
                                                    print(f"[{get_timestamp()}] Fallback: Using betStop_round_for_table from main_speed_2")
                                                except ImportError:
                                                    try:
                                                        from main_speed import betStop_round_for_table
                                                        print(f"[{get_timestamp()}] Fallback: Using betStop_round_for_table from main_speed")
                                                    except ImportError:
                                                        print(f"[{get_timestamp()}] Error: Could not import betStop_round_for_table from any module")
                                                        continue
                                        
                                        if betStop_round_for_table is None:
                                            print(f"[{get_timestamp()}] Error: betStop_round_for_table function not available")
                                            continue
                                        
                                        # Create thread for bet stop countdown
                                        threading.Timer(
                                            bet_period,
                                            lambda t=table, r=round_id, b=bet_period: _bet_stop_countdown(
                                                t, r, b, token, betStop_round_for_table, get_timestamp, log_to_file, global_vars
                                            )
                                        ).start()
                                        print(f"[{get_timestamp()}] Started bet stop countdown for {table['name']} (round {round_id}, {bet_period}s)")
                                        log_to_file(f"Started bet stop countdown for {table['name']} (round {round_id}, {bet_period}s)", "Bet Stop >>>")

                                print("\nSending *u 1 command...")
                                # Check if serial connection is available
                                if ser is not None:
                                    ser.write(("*u 1\r\n").encode())
                                    log_to_file("*u 1", "Send <<<")
                                    print("*u 1 command sent\n")
                                    # Update game state tracking
                                    global_vars["u1_sent"] = True
                                else:
                                    print(
                                        "Warning: Serial connection not available, cannot send *u 1 command"
                                    )

                                # First Roulette detect disabled - IDP integration not ready
                                log_mqtt("First Roulette detect disabled (IDP integration not complete)")
                                log_to_file("First Roulette detect disabled (IDP integration not complete)", "MQTT >>>")

                                # Start recording two seconds after sending *u 1 command
                                if (
                                    tables
                                    and len(tables) > 0
                                    and "round_id" in tables[0]
                                ):
                                    round_id = tables[0]["round_id"]
                                    print(
                                        f"[{get_timestamp()}] Preparing to start recording round_id: {round_id}, will start in two seconds"
                                    )
                                    log_to_file(
                                        f"Preparing to start recording round_id: {round_id}, will start in two seconds",
                                        "WebSocket >>>",
                                    )
                                    # Use thread to delay recording execution, avoid blocking main process
                                    threading.Timer(
                                        2.0,
                                        lambda: send_start_recording(round_id),
                                    ).start()
                            except Exception as e:
                                print(f"start_post error: {e}")
                            print("======================================\n")

                    elif "*X;3" in data and not global_vars["isLaunch"]:
                        ball_launch_time = time.time()
                        print(f"ball_launch_time: {ball_launch_time}")
                        log_to_file(
                            f"ball_launch_time: {ball_launch_time}",
                            "Receive >>>",
                        )
                        global_vars["isLaunch"] = 1

                        start_to_launch_time = (
                            ball_launch_time - global_vars["start_time"]
                        )
                        print(f"start_to_launch_time: {start_to_launch_time}")
                        log_to_file(
                            f"start_to_launch_time: {start_to_launch_time}",
                            "Receive >>>",
                        )

                        # Removed code that starts recording when ball launches, as it now starts two seconds after *u 1 command

                    # Handle *X;4 - Schedule delayed second Roulette detect (ONCE per round)
                    elif "*X;4" in data:
                        # Check if we already started roulette detection for this round
                        current_round_id = None
                        if tables and len(tables) > 0 and "round_id" in tables[0]:
                            current_round_id = tables[0]["round_id"]
                        
                        # Use deal_post_sent as detection_sent flag (reset on new round)
                        detection_key = f"roulette_detection_{current_round_id}"
                        
                        # Thread-safe check for detection scheduling
                        with _detection_scheduling_lock:
                            detection_status = global_vars.get('roulette_detection_sent', None)
                            
                            print(f"[{get_timestamp()}] Checking detection status for round {current_round_id}: current_status={detection_status}")
                            log_mqtt(f"Checking detection status for round {current_round_id}: current_status={detection_status}")
                            
                            if detection_status != current_round_id:
                                # Mark detection as scheduled immediately to prevent duplicates
                                global_vars['roulette_detection_sent'] = current_round_id
                                should_schedule = True
                                print(f"[{get_timestamp()}] SCHEDULING detection for round {current_round_id}")
                                log_mqtt(f"SCHEDULING detection for round {current_round_id}")
                            else:
                                should_schedule = False
                                print(f"[{get_timestamp()}] SKIPPING duplicate detection for round {current_round_id}")
                                log_mqtt(f"⚠️ SKIPPING duplicate detection for round {current_round_id} (already scheduled)")
                        
                        if should_schedule:
                            try:
                                # Import the roulette detect function from independent module
                                from roulette_mqtt_detect import call_roulette_detect_async
                                
                                log_mqtt(f"Detected *X;4 - Scheduling SINGLE Roulette detect for round {current_round_id} after 15 seconds...")
                                log_to_file(f"Detected *X;4 - Scheduling SINGLE Roulette detect for round {current_round_id} after 15 seconds...", "MQTT >>>")
                                
                                # Call detect with 15-second delay in a separate thread
                                def call_delayed_second_detect():
                                    try:
                                        # Wait 15 seconds before calling detect (increased from 10s)
                                        print(f"[{get_timestamp()}] Waiting 15 seconds before second Roulette detect...")
                                        log_mqtt("Waiting 15 seconds before second Roulette detect...")
                                        log_to_file("Waiting 15 seconds before second Roulette detect...", "MQTT >>>")
                                        
                                        # Check every second if *X;5 has started (deal post phase)
                                        for i in range(15):
                                            time.sleep(1)
                                            # If *X;5 has started, cancel the detect command
                                            if global_vars.get('x5_started', False):
                                                print(f"[{get_timestamp()}] *X;5 detected - Cancelling delayed Roulette detect")
                                                log_mqtt("🛑 *X;5 detected - Cancelling delayed Roulette detect (round ended)")
                                                log_to_file("*X;5 detected - Cancelling delayed Roulette detect", "MQTT >>>")
                                                return
                                        
                                        # Double check before executing detect
                                        if global_vars.get('x5_started', False):
                                            print(f"[{get_timestamp()}] *X;5 already started - Skipping delayed Roulette detect")
                                            log_mqtt("🛑 *X;5 already started - Skipping delayed Roulette detect")
                                            log_to_file("*X;5 already started - Skipping delayed Roulette detect", "MQTT >>>")
                                            return
                                        
                                        print(f"[{get_timestamp()}] Starting SINGLE second Roulette detect...")
                                        log_mqtt("Starting SINGLE second Roulette detect...")
                                        log_to_file("Starting SINGLE second Roulette detect...", "MQTT >>>")
                                        
                                        success, result = call_roulette_detect_async(
                                            round_id=current_round_id,
                                            input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
                                        )
                                        if success:
                                            # Check different types of results
                                            if (result is not None and result != "" and result != [] and result != [''] and 
                                                not isinstance(result, dict) and str(result) != "null"):
                                                # Valid result received (not empty, not dict, not null)
                                                print(f"[{get_timestamp()}] Second Roulette detect completed: {result}")
                                                log_mqtt(f"🎯 Second Roulette detect SUCCESS: {result}")
                                                log_to_file(f"Second Roulette detect completed: {result}", "MQTT >>>")
                                            elif result == [''] or result == []:
                                                # IDP returned empty result (ball still moving or detection issues)
                                                print(f"[{get_timestamp()}] Second Roulette detect completed but IDP returned empty result")
                                                log_mqtt("⚠️ Second Roulette detect: IDP returned empty result (ball may still be moving)")
                                                log_to_file("Second Roulette detect completed but IDP returned empty result", "MQTT >>>")
                                            elif result is None or result == "null":
                                                # IDP returned null (detection error or timing issue)
                                                print(f"[{get_timestamp()}] Second Roulette detect completed but IDP returned null result")
                                                log_mqtt("⚠️ Second Roulette detect: IDP returned null result (timing or detection issue)")
                                                log_to_file("Second Roulette detect completed but IDP returned null result", "MQTT >>>")
                                            else:
                                                # Unknown result format
                                                print(f"[{get_timestamp()}] Second Roulette detect completed with unknown result format: {result}")
                                                log_mqtt(f"⚠️ Second Roulette detect: Unknown result format: {result}")
                                                log_to_file(f"Second Roulette detect completed with unknown result format: {result}", "MQTT >>>")
                                        else:
                                            print(f"[{get_timestamp()}] Second Roulette detect failed")
                                            log_mqtt("❌ Second Roulette detect FAILED")
                                            log_to_file("Second Roulette detect failed", "MQTT >>>")
                                    except Exception as e:
                                        print(f"[{get_timestamp()}] Error in delayed second Roulette detect: {e}")
                                        log_mqtt(f"Error in delayed second Roulette detect: {e}")
                                        log_to_file(f"Error in delayed second Roulette detect: {e}", "MQTT >>>")
                                
                                # Start delayed detect call in separate thread
                                threading.Thread(target=call_delayed_second_detect, daemon=True).start()
                                
                            except Exception as e:
                                print(f"[{get_timestamp()}] Error scheduling delayed Roulette detect after *X;4: {e}")
                                log_to_file(f"Error scheduling delayed Roulette detect after *X;4: {e}", "MQTT >>>")
                        else:
                            # Detection already scheduled for this round - skip duplicate
                            # Note: This message is already logged in the lock section above
                            pass

                    # Handle *X;5 count
                    elif "*X;5" in data and not global_vars["deal_post_sent"]:
                        # Set flag to indicate *X;5 has started - this will cancel any pending detect commands
                        global_vars['x5_started'] = True
                        log_mqtt("🔥 *X;5 detected - Setting flag to cancel any pending detect commands")
                        log_to_file("*X;5 detected - Setting flag to cancel pending detects", "MQTT >>>")
                        
                        current_time = time.time()
                        if current_time - global_vars["last_x5_time"] > 5:
                            global_vars["x5_count"] = 1
                        else:
                            global_vars["x5_count"] += 1
                        global_vars["last_x5_time"] = current_time

                        if global_vars["x5_count"] == 1:
                            try:
                                parts = data.split(";")
                                if len(parts) >= 4:
                                    win_num = int(parts[3])
                                    print(
                                        f"Winning number for this round: {win_num}"
                                    )
                                    
                                    # Log serial result for comparison with IDP result
                                    try:
                                        from result_compare_logger import log_serial_result
                                        
                                        # Get current round_id from tables
                                        current_round_id = None
                                        if tables and len(tables) > 0 and "round_id" in tables[0]:
                                            current_round_id = tables[0]["round_id"]
                                        else:
                                            # Fallback: create a round_id based on timestamp
                                            current_round_id = f"ARO-001-serial-{int(time.time())}"
                                        
                                        # Log the serial port result
                                        log_serial_result(current_round_id, win_num)
                                        log_to_file(f"Serial result logged for comparison: Round={current_round_id}, Result={win_num}", "COMPARE >>>")
                                        
                                    except Exception as e:
                                        print(f"[{get_timestamp()}] Error logging serial result for comparison: {e}")
                                        log_to_file(f"Error logging serial result for comparison: {e}", "ERROR >>>")

                                    print(
                                        "\n================Deal================"
                                    )

                                    try:
                                        global_vars["deal_post_time"] = (
                                            time.time()
                                        )
                                        print(
                                            f"deal_post_time: {global_vars['deal_post_time']}"
                                        )
                                        log_to_file(
                                            f"deal_post_time: {global_vars['deal_post_time']}",
                                            "Receive >>>",
                                        )

                                        launch_to_deal_time = (
                                            global_vars["deal_post_time"]
                                            - ball_launch_time
                                        )
                                        print(
                                            f"launch_to_deal_time: {launch_to_deal_time}"
                                        )
                                        log_to_file(
                                            f"launch_to_deal_time: {launch_to_deal_time}",
                                            "Receive >>>",
                                        )

                                        # Stop recording - changed to non-blocking execution
                                        print(
                                            f"[{get_timestamp()}] Stop recording"
                                        )
                                        log_to_file(
                                            "Stop recording", "WebSocket >>>"
                                        )
                                        send_stop_recording()  # This function now doesn't block the main thread

                                        # Asynchronously process deal_post for all tables
                                        time.sleep(0.5)
                                        with ThreadPoolExecutor(
                                            max_workers=len(tables)
                                        ) as executor:
                                            futures = [
                                                executor.submit(
                                                    execute_deal_post,
                                                    table,
                                                    token,
                                                    win_num,
                                                )
                                                for table in tables
                                            ]
                                            for future in futures:
                                                future.result()  # Wait for all requests to complete

                                        global_vars["deal_post_sent"] = True
                                    except Exception as e:
                                        print(f"deal_post error: {e}")

                                    print(
                                        "======================================\n"
                                    )

                                    # No longer wait for detection results in *X;5 - proceed immediately to finish post
                                    print(f"[{get_timestamp()}] *X;5 received - Proceeding to finish post without waiting for detection")
                                    log_mqtt("⚡ *X;5 - Proceeding to finish post immediately (no detection wait)")
                                    log_to_file("*X;5 - Proceeding to finish post immediately", "MQTT >>>")

                                    print(
                                        "\n================Finish================"
                                    )

                                    try:
                                        global_vars["finish_post_time"] = (
                                            time.time()
                                        )
                                        print(
                                            f"finish_post_time: {global_vars['finish_post_time']}"
                                        )
                                        log_to_file(
                                            f"finish_post_time: {global_vars['finish_post_time']}",
                                            "Receive >>>",
                                        )

                                        deal_to_finish_time = (
                                            global_vars["finish_post_time"]
                                            - global_vars["deal_post_time"]
                                        )
                                        print(
                                            f"deal_to_finish_time: {deal_to_finish_time}"
                                        )
                                        log_to_file(
                                            f"deal_to_finish_time: {deal_to_finish_time}",
                                            "Receive >>>",
                                        )

                                        log_to_file("Summary:", "Receive >>>")
                                        log_to_file(
                                            f"start_to_launch_time: {start_to_launch_time}",
                                            "Receive >>>",
                                        )
                                        log_to_file(
                                            f"launch_to_deal_time: {launch_to_deal_time}",
                                            "Receive >>>",
                                        )
                                        log_to_file(
                                            f"deal_to_finish_time: {deal_to_finish_time}",
                                            "Receive >>>",
                                        )
                                        log_to_file(
                                            f"finish_to_start_time: {finish_to_start_time}",
                                            "Receive >>>",
                                        )

                                        log_time_intervals(
                                            finish_to_start_time,
                                            start_to_launch_time,
                                            launch_to_deal_time,
                                            deal_to_finish_time,
                                        )

                                        # Asynchronously process finish_post for all tables
                                        with ThreadPoolExecutor(
                                            max_workers=len(tables)
                                        ) as executor:
                                            futures = [
                                                executor.submit(
                                                    execute_finish_post,
                                                    table,
                                                    token,
                                                )
                                                for table in tables
                                            ]
                                            for future in futures:
                                                future.result()  # Wait for all requests to complete

                                        # Update game state tracking - finish_post has been sent
                                        global_vars["finish_post_sent"] = True

                                        # Reset all flags and counters (including roulette detection)
                                        global_vars["start_post_sent"] = False
                                        global_vars["x2_count"] = 0
                                        global_vars["x5_count"] = 0
                                        global_vars["isLaunch"] = 0
                                        # Reset game state tracking for next round
                                        global_vars["u1_sent"] = False
                                        global_vars["betStop_sent"] = False
                                        global_vars["finish_post_sent"] = False
                                        
                                        # Reset roulette detection flags for next round
                                        if 'roulette_detection_sent' in global_vars:
                                            global_vars['roulette_detection_sent'] = None
                                            log_mqtt("Reset roulette detection flag for new round")
                                            log_to_file("Reset roulette detection flag for new round", "MQTT >>>")
                                        
                                        # Reset *X;5 flag for next round
                                        global_vars['x5_started'] = False
                                        log_mqtt("Reset *X;5 flag for new round")
                                        log_to_file("Reset *X;5 flag for new round", "MQTT >>>")
                                        
                                    except Exception as e:
                                        print(f"finish_post error: {e}")
                                    print(
                                        "======================================\n"
                                    )
                            except Exception as e:
                                print(f"Error parsing winning number: {e}")
        else:
            # No data available, sleep briefly to prevent busy waiting
            time.sleep(0.001)  # 1ms sleep


def _bet_stop_countdown(table, round_id, bet_period, token, betStop_round_for_table, get_timestamp, log_to_file, global_vars=None):
    """
    Countdown and call bet stop for a table (non-blocking)
    
    Args:
        table: Table configuration dictionary
        round_id: Current round ID
        bet_period: Betting period duration in seconds
        token: Authentication token
        betStop_round_for_table: Function to call bet stop
        get_timestamp: Function to get current timestamp
        log_to_file: Function to log messages to file
        global_vars: Dictionary containing game state variables (optional)
    """
    try:
        # Note: Timer already handles the delay, no need to sleep here
        # Previously: time.sleep(bet_period) - removed to fix double delay issue (14s late bet-stop)

        # Call bet stop for the table
        print(f"[{get_timestamp()}] Calling bet stop for {table['name']} (round {round_id})")
        log_to_file(f"Calling bet stop for {table['name']} (round {round_id})", "Bet Stop >>>")
        
        result = betStop_round_for_table(table, token)
        
        # Update game state tracking - betStop has been sent
        if global_vars is not None:
            global_vars["betStop_sent"] = True

        if result[1]:  # Check if successful
            print(f"[{get_timestamp()}] Successfully stopped betting for {table['name']}")
            log_to_file(f"Successfully stopped betting for {table['name']}", "Bet Stop >>>")
        else:
            print(f"[{get_timestamp()}] Bet stop completed for {table['name']} (may already be stopped)")
            log_to_file(f"Bet stop completed for {table['name']} (may already be stopped)", "Bet Stop >>>")

    except Exception as e:
        print(f"[{get_timestamp()}] Error in bet stop countdown for {table['name']}: {e}")
        log_to_file(f"Error in bet stop countdown for {table['name']}: {e}", "Error >>>")
