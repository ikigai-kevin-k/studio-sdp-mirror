#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serial I/O module for Speed Roulette Controller
Handles serial communication and data processing
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor


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

    while True:
        # Check if program should terminate
        if global_vars.get("terminate_program", False):
            print(f"[{get_timestamp()}] Serial read thread terminating due to program termination flag")
            break
            
        # Check if serial connection is available
        if ser is None:
            print(
                "Warning: Serial connection not available, skipping serial read"
            )
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
                    print("Receive >>>", line)
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

                            # Trigger error signal and termination for ANY *X;6 message
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

                        # Check if warning_flag is 8, if so send broadcast_post
                        try:
                            parts = data.split(";")
                            if (
                                len(parts) >= 5
                            ):  # Ensure there are enough parts to get warning_flag
                                warning_flag = parts[4]
                                current_time = time.time()

                                # Check if warning_flag requires broadcast
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
                                f"Error parsing warning_flag or sending broadcast_post: {e}"
                            )
                            log_to_file(
                                f"Error parsing warning_flag or sending broadcast_post: {e}",
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
                                with ThreadPoolExecutor(
                                    max_workers=len(tables)
                                ) as executor:
                                    futures = [
                                        executor.submit(
                                            execute_start_post, table, token
                                        )
                                        for table in tables
                                    ]
                                    for future in futures:
                                        future.result()  # Wait for all requests to complete

                                global_vars["start_post_sent"] = True
                                global_vars["deal_post_sent"] = False

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
