#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serial I/O module for Speed Roulette Controller
Handles serial communication and data processing
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Import log redirector for separated logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from log_redirector import log_mqtt, log_api, log_serial, log_console, get_timestamp


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

                            # Trigger error signal and termination for *X;6 message (not startup condition)
                            print(
                                f"[{get_timestamp()}] *X;6 MESSAGE detected! Sending notifications and terminating program..."
                            )
                            log_to_file(
                                "*X;6 MESSAGE detected! Sending notifications and terminating program...",
                                "Receive >>>",
                            )

                            # Import and call functions directly
                            try:
                                import sys
                                import os

                                # Add parent directory to path to import main_speed
                                sys.path.append(
                                    os.path.dirname(
                                        os.path.dirname(
                                            os.path.abspath(__file__)
                                        )
                                    )
                                )
                                from main_speed import (
                                    send_sensor_error_to_slack,
                                    send_websocket_error_signal,
                                )

                                # Send sensor error notification to Slack
                                send_sensor_error_to_slack()

                                # Send WebSocket error signal
                                send_websocket_error_signal()

                                # Set global flag to terminate the program
                                global_vars["terminate_program"] = True
                                print(
                                    f"[{get_timestamp()}] Program termination flag set due to *X;6 message"
                                )
                                log_to_file(
                                    "Program termination flag set due to *X;6 message",
                                    "Receive >>>",
                                )

                            except ImportError as e:
                                print(
                                    f"[{get_timestamp()}] Error importing functions: {e}"
                                )
                                log_to_file(
                                    f"Error importing functions: {e}",
                                    "Error >>>",
                                )
                                # Still set termination flag even if import fails
                                global_vars["terminate_program"] = True
                            except Exception as e:
                                print(
                                    f"[{get_timestamp()}] Error calling sensor error functions: {e}"
                                )
                                log_to_file(
                                    f"Error calling sensor error functions: {e}",
                                    "Error >>>",
                                )
                                # Still set termination flag even if function call fails
                                global_vars["terminate_program"] = True
                        except Exception as e:
                            print(
                                f"[{get_timestamp()}] Error parsing *X;6 message: {e}"
                            )
                            log_to_file(
                                f"Error parsing *X;6 message: {e}", "Error >>>"
                            )
                            # Still set termination flag even if parsing fails
                            global_vars["terminate_program"] = True

                    # Handle *X;2 count
                    if "*X;2" in data:
                        current_time = time.time()
                        if current_time - global_vars["last_x2_time"] > 5:
                            global_vars["x2_count"] = 1
                        else:
                            global_vars["x2_count"] += 1
                        global_vars["last_x2_time"] = current_time

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

                                    # Import and call error signal functions
                                    try:
                                        import sys
                                        import os

                                        # Add parent directory to path to import main_speed
                                        sys.path.append(
                                            os.path.dirname(
                                                os.path.dirname(
                                                    os.path.abspath(__file__)
                                                )
                                            )
                                        )
                                        from main_speed import (
                                            send_sensor_error_to_slack,
                                            send_websocket_error_signal,
                                        )

                                        # Send sensor error notification to Slack
                                        send_sensor_error_to_slack()

                                        # Send WebSocket error signal
                                        send_websocket_error_signal()

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

                                    # Check if warning_flag requires broadcast (original logic)
                                    if (
                                        int(warning_flag) == 8
                                        or int(warning_flag) == 2
                                        or warning_flag == "A"
                                    ):
                                        # Check if 10 seconds have passed or it's the first broadcast
                                        if (
                                            not hasattr(
                                                execute_broadcast_post,
                                                "last_broadcast_time",
                                            )
                                            or (
                                                current_time
                                                - execute_broadcast_post.last_broadcast_time
                                            )
                                            >= 10
                                        ):

                                            print(
                                                f"\nDetected warning_flag not equal to 0, sending broadcast_post to notify relaunch..."
                                            )
                                            log_to_file(
                                                "Detected warning_flag not equal to 0, sending broadcast_post to notify relaunch",
                                                "Broadcast >>>",
                                            )

                                            # Send broadcast_post to each table
                                            with ThreadPoolExecutor(
                                                max_workers=len(tables)
                                            ) as executor:
                                                futures = [
                                                    executor.submit(
                                                        execute_broadcast_post,
                                                        table,
                                                        token,
                                                    )
                                                    for table in tables
                                                ]
                                                for future in futures:
                                                    future.result()  # Wait for all requests to complete

                                            # Update last send time
                                            execute_broadcast_post.last_broadcast_time = (
                                                current_time
                                            )
                                        else:
                                            print(
                                                f"Already sent broadcast {current_time - execute_broadcast_post.last_broadcast_time:.1f} seconds ago, waiting for time interval..."
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
                                                t, r, b, token, betStop_round_for_table, get_timestamp, log_to_file
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
                                else:
                                    print(
                                        "Warning: Serial connection not available, cannot send *u 1 command"
                                    )

                                # Call Roulette detect immediately after *u 1 command
                                try:
                                    # Import the roulette detect function from independent module
                                    from roulette_mqtt_detect import call_roulette_detect_async
                                    
                                    # Get current round_id for detect call
                                    current_round_id = None
                                    if tables and len(tables) > 0 and "round_id" in tables[0]:
                                        current_round_id = tables[0]["round_id"]
                                    
                                    log_mqtt("Calling Roulette detect after *u 1 command...")
                                    log_to_file("Calling Roulette detect after *u 1 command...", "MQTT >>>")
                                    
                                    # Call detect in a separate thread to avoid blocking
                                    def call_detect_async():
                                        try:
                                            success, result = call_roulette_detect_async(
                                                round_id=current_round_id,
                                                input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
                                            )
                                            if success:
                                                # Only print result if it's not empty/null
                                                if result is not None and result != "" and result != []:
                                                    print(f"[{get_timestamp()}] First Roulette detect completed: {result}")
                                                    log_to_file(f"First Roulette detect completed: {result}", "MQTT >>>")
                                                # Don't print anything for empty results to keep terminal clean
                                            else:
                                                print(f"[{get_timestamp()}] First Roulette detect failed")
                                                log_to_file("First Roulette detect failed", "MQTT >>>")
                                        except Exception as e:
                                            print(f"[{get_timestamp()}] Error in first Roulette detect: {e}")
                                            log_to_file(f"Error in first Roulette detect: {e}", "MQTT >>>")
                                    
                                    # Start detect call in separate thread
                                    threading.Thread(target=call_detect_async, daemon=True).start()
                                    
                                except Exception as e:
                                    print(f"[{get_timestamp()}] Error calling Roulette detect after *u 1: {e}")
                                    log_to_file(f"Error calling Roulette detect after *u 1: {e}", "MQTT >>>")

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

                    # Handle *X;4 - Call second Roulette detect
                    elif "*X;4" in data:
                        try:
                            # Import the roulette detect function from independent module
                            from roulette_mqtt_detect import call_roulette_detect_async
                            
                            # Get current round_id for detect call
                            current_round_id = None
                            if tables and len(tables) > 0 and "round_id" in tables[0]:
                                current_round_id = tables[0]["round_id"]
                            
                            log_mqtt("Detected *X;4 - Calling second Roulette detect...")
                            log_to_file("Detected *X;4 - Calling second Roulette detect...", "MQTT >>>")
                            
                            # Call detect in a separate thread to avoid blocking
                            def call_second_detect_async():
                                try:
                                    success, result = call_roulette_detect_async(
                                        round_id=current_round_id,
                                        input_stream="rtmp://192.168.88.50:1935/live/r10_sr"
                                    )
                                    if success:
                                        # Only print result if it's not empty/null
                                        if result is not None and result != "" and result != []:
                                            print(f"[{get_timestamp()}] Second Roulette detect completed: {result}")
                                            log_to_file(f"Second Roulette detect completed: {result}", "MQTT >>>")
                                        # Don't print anything for empty results to keep terminal clean
                                    else:
                                        print(f"[{get_timestamp()}] Second Roulette detect failed")
                                        log_to_file("Second Roulette detect failed", "MQTT >>>")
                                except Exception as e:
                                    print(f"[{get_timestamp()}] Error in second Roulette detect: {e}")
                                    log_to_file(f"Error in second Roulette detect: {e}", "MQTT >>>")
                            
                            # Start detect call in separate thread
                            threading.Thread(target=call_second_detect_async, daemon=True).start()
                            
                        except Exception as e:
                            print(f"[{get_timestamp()}] Error calling Roulette detect after *X;4: {e}")
                            log_to_file(f"Error calling Roulette detect after *X;4: {e}", "MQTT >>>")

                    # Handle *X;5 count
                    elif "*X;5" in data and not global_vars["deal_post_sent"]:
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

                                    # time.sleep(1)
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

                                        # Reset all flags and counters
                                        global_vars["start_post_sent"] = False
                                        global_vars["x2_count"] = 0
                                        global_vars["x5_count"] = 0
                                        global_vars["isLaunch"] = 0
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


def _bet_stop_countdown(table, round_id, bet_period, token, betStop_round_for_table, get_timestamp, log_to_file):
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
    """
    try:
        # Note: Timer already handles the delay, no need to sleep here
        # Previously: time.sleep(bet_period) - removed to fix double delay issue (14s late bet-stop)

        # Call bet stop for the table
        print(f"[{get_timestamp()}] Calling bet stop for {table['name']} (round {round_id})")
        log_to_file(f"Calling bet stop for {table['name']} (round {round_id})", "Bet Stop >>>")
        
        result = betStop_round_for_table(table, token)

        if result[1]:  # Check if successful
            print(f"[{get_timestamp()}] Successfully stopped betting for {table['name']}")
            log_to_file(f"Successfully stopped betting for {table['name']}", "Bet Stop >>>")
        else:
            print(f"[{get_timestamp()}] Bet stop completed for {table['name']} (may already be stopped)")
            log_to_file(f"Bet stop completed for {table['name']} (may already be stopped)", "Bet Stop >>>")

    except Exception as e:
        print(f"[{get_timestamp()}] Error in bet stop countdown for {table['name']}: {e}")
        log_to_file(f"Error in bet stop countdown for {table['name']}: {e}", "Error >>>")
