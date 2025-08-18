import serial
import threading
import time
from datetime import datetime
import sys
import random
import json
import asyncio
import websockets

sys.path.append(".")  # Ensure los_api can be imported
from los_api.sr.api_v2_sr import (
    start_post_v2,
    deal_post_v2,
    finish_post_v2,
    broadcast_post_v2,
)
from los_api.sr.api_v2_uat_sr import (
    start_post_v2_uat,
    deal_post_v2_uat,
    finish_post_v2_uat,
    broadcast_post_v2_uat,
)
from los_api.sr.api_v2_prd_sr import (
    start_post_v2_prd,
    deal_post_v2_prd,
    finish_post_v2_prd,
    broadcast_post_v2_prd,
)
from los_api.sr.api_v2_stg_sr import (
    start_post_v2_stg,
    deal_post_v2_stg,
    finish_post_v2_stg,
    broadcast_post_v2_stg,
)
from los_api.sr.api_v2_qat_sr import (
    start_post_v2_qat,
    deal_post_v2_qat,
    finish_post_v2_qat,
    broadcast_post_v2_qat,
)
from concurrent.futures import ThreadPoolExecutor

# import sentry_sdk

# sentry_sdk.init(
#     dsn="https://63a51b0fa2f4c419adaf46fafea61e89@o4509115379679232.ingest.us.sentry.io/4509643182440448",
#     # Add data like request headers and IP for users,
#     # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
#     send_default_pii=True,
# )

# Initialize serial connection only if hardware is available
from utils import create_serial_connection

ser = create_serial_connection(
    port="/dev/ttyUSB0",
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1,
)


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def log_to_file(message, direction):
    with open("self-test-2api.log", "a", encoding="utf-8") as f:
        timestamp = get_timestamp()
        f.write(f"[{timestamp}] {direction} {message}\n")


# Load table configuration
def load_table_config():
    with open("conf/table-config-speed-roulette-v2.json", "r") as f:
        return json.load(f)


# Add LOS API related variables
tables = load_table_config()
x2_count = 0
x5_count = 0
isLaunch = 0
last_x2_time = 0
last_x5_time = 0
start_post_sent = False
deal_post_sent = False
finish_post_time = 0
token = "E5LN4END9Q"
ws_client = None
ws_connected = False


# WebSocket connection function
async def connect_to_recorder(uri="ws://localhost:8765"):
    """Connect to the stream recorder's WebSocket server"""
    global ws_client, ws_connected
    try:
        ws_client = await websockets.connect(uri)
        ws_connected = True
        print(f"[{get_timestamp()}] Connected to stream recorder: {uri}")
        log_to_file(f"Connected to stream recorder: {uri}", "WebSocket >>>")
        return True
    except Exception as e:
        # print(f"[{get_timestamp()}] Failed to connect to stream recorder: {e}")
        # log_to_file(f"Failed to connect to stream recorder: {e}", "WebSocket >>>")
        ws_connected = False
        return False


# Send WebSocket message function
async def send_to_recorder(message):
    """Send message to stream recorder"""
    global ws_connected
    if not ws_connected or not ws_client:
        # print(f"[{get_timestamp()}] Not connected to stream recorder, attempting to reconnect...")
        # log_to_file("Not connected to stream recorder, attempting to reconnect...", "WebSocket >>>")
        await connect_to_recorder()

    if ws_connected:
        try:
            await ws_client.send(message)
            response = await ws_client.recv()
            print(f"[{get_timestamp()}] Recorder response: {response}")
            log_to_file(f"Recorder response: {response}", "WebSocket >>>")
            return True
        except Exception as e:
            print(
                f"[{get_timestamp()}] Failed to send message to recorder: {e}"
            )
            log_to_file(
                f"Failed to send message to recorder: {e}", "WebSocket >>>"
            )
            ws_connected = False
            return False
    return False


# Start WebSocket connection async function
async def init_websocket():
    """Initialize WebSocket connection"""
    await connect_to_recorder()


# Start WebSocket connection in main thread
def start_websocket():
    """Start WebSocket connection in main thread"""
    asyncio.run(init_websocket())


# Start WebSocket connection in a separate thread
websocket_thread = threading.Thread(target=start_websocket)
websocket_thread.daemon = True
websocket_thread.start()


# Function to send start recording message
def send_start_recording(round_id):
    """Send start recording message"""
    asyncio.run(send_to_recorder(f"start_recording:{round_id}"))


# Function to send stop recording message
def send_stop_recording():
    """Send stop recording message"""
    # Use a thread to execute async operation, avoid blocking main thread
    threading.Thread(
        target=lambda: asyncio.run(send_to_recorder("stop_recording"))
    ).start()


def read_from_serial():
    global x2_count, x5_count, last_x2_time, last_x5_time, start_post_sent, deal_post_sent, start_time, deal_post_time, finish_post_time, isLaunch
    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode("utf-8").strip()
            print("Receive >>>", data)
            log_to_file(data, "Receive >>>")

            # Handle *X;2 count
            if "*X;2" in data:
                current_time = time.time()
                if current_time - last_x2_time > 5:
                    x2_count = 1
                else:
                    x2_count += 1
                last_x2_time = current_time

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

                if x2_count >= 1 and not start_post_sent:
                    time.sleep(2)  # for the show result animation time
                    print("\n================Start================")

                    try:
                        start_time = time.time()
                        print(f"start_time: {start_time}")
                        log_to_file(f"start_time: {start_time}", "Receive >>>")

                        if finish_post_time == 0:
                            finish_post_time = start_time
                        finish_to_start_time = start_time - finish_post_time
                        print(f"finish_to_start_time: {finish_to_start_time}")
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

                        start_post_sent = True
                        deal_post_sent = False

                        print("\nSending *u 1 command...")
                        ser.write(("*u 1\r\n").encode())
                        log_to_file("*u 1", "Send <<<")
                        print("*u 1 command sent\n")

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
                                2.0, lambda: send_start_recording(round_id)
                            ).start()
                    except Exception as e:
                        print(f"start_post error: {e}")
                    print("======================================\n")

            elif "*X;3" in data and not isLaunch:
                ball_launch_time = time.time()
                print(f"ball_launch_time: {ball_launch_time}")
                log_to_file(
                    f"ball_launch_time: {ball_launch_time}", "Receive >>>"
                )
                isLaunch = 1

                start_to_launch_time = ball_launch_time - start_time
                print(f"start_to_launch_time: {start_to_launch_time}")
                log_to_file(
                    f"start_to_launch_time: {start_to_launch_time}",
                    "Receive >>>",
                )

                # Removed code that starts recording when ball launches, as it now starts two seconds after *u 1 command

            # Handle *X;5 count
            elif "*X;5" in data and not deal_post_sent:
                current_time = time.time()
                if current_time - last_x5_time > 5:
                    x5_count = 1
                else:
                    x5_count += 1
                last_x5_time = current_time

                if x5_count == 1:
                    try:
                        parts = data.split(";")
                        if len(parts) >= 4:
                            win_num = int(parts[3])
                            print(f"Winning number for this round: {win_num}")

                            print("\n================Deal================")

                            try:
                                deal_post_time = time.time()
                                print(f"deal_post_time: {deal_post_time}")
                                log_to_file(
                                    f"deal_post_time: {deal_post_time}",
                                    "Receive >>>",
                                )

                                launch_to_deal_time = (
                                    deal_post_time - ball_launch_time
                                )
                                print(
                                    f"launch_to_deal_time: {launch_to_deal_time}"
                                )
                                log_to_file(
                                    f"launch_to_deal_time: {launch_to_deal_time}",
                                    "Receive >>>",
                                )

                                # Stop recording - changed to non-blocking execution
                                print(f"[{get_timestamp()}] Stop recording")
                                log_to_file("Stop recording", "WebSocket >>>")
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

                                deal_post_sent = True
                            except Exception as e:
                                print(f"deal_post error: {e}")

                            print("======================================\n")

                            # time.sleep(1)
                            print("\n================Finish================")

                            try:
                                finish_post_time = time.time()
                                print(f"finish_post_time: {finish_post_time}")
                                log_to_file(
                                    f"finish_post_time: {finish_post_time}",
                                    "Receive >>>",
                                )

                                deal_to_finish_time = (
                                    finish_post_time - deal_post_time
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
                                            execute_finish_post, table, token
                                        )
                                        for table in tables
                                    ]
                                    for future in futures:
                                        future.result()  # Wait for all requests to complete

                                # Reset all flags and counters
                                start_post_sent = False
                                x2_count = 0
                                x5_count = 0
                                isLaunch = 0
                            except Exception as e:
                                print(f"finish_post error: {e}")
                            print("======================================\n")
                    except Exception as e:
                        print(f"Error parsing winning number: {e}")


def send_command_and_wait(command, timeout=2):
    """Send a command and wait for the expected response"""
    ser.write((command + "\r\n").encode())
    log_to_file(command, "Send <<<")

    # Get command type (H, S, T, or R)
    cmd_type = command[-1].lower()

    # Wait for response
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        if ser.in_waiting > 0:
            response = ser.readline().decode("utf-8").strip()
            print("Receive >>>", response)
            log_to_file(response, "Receive >>>")

            # Check if this is the response we're waiting for
            if response.startswith(f"*T {cmd_type}"):
                # Parse the value from response
                parts = response.split()
                if len(parts) > 2:  # Make sure we have values after "*T x"
                    return " ".join(parts[2:])  # Return only the values
        time.sleep(0.1)
    return None


def get_config():
    """Get all configuration parameters from terminal"""
    print("\nGetting configuration parameters...")

    # Store results
    config_results = {
        "*T H - GPH": None,
        "*T S - Wheel Speed": None,
        "*T T - Deceleration Distance": None,
        "*T R - In-rim Jet Duration": None,
    }

    # Define commands and their descriptions
    commands = [
        ("*T H", "*T H - GPH"),
        ("*T S", "*T S - Wheel Speed"),
        ("*T T", "*T T - Deceleration Distance"),
        ("*T R", "*T R - In-rim Jet Duration"),
    ]

    # Execute each command and collect responses
    for cmd, desc in commands:
        print(f"\nQuerying {desc}...")
        value = send_command_and_wait(cmd)
        if value:
            config_results[desc] = value  # Store only the value part
            print(f"Stored value: {desc} = {value}")  # For debugging
        time.sleep(0.5)  # Add delay between commands

    # Print all results together
    print("\n=== Configuration Parameters ===")
    print("-" * 50)
    for desc, value in config_results.items():
        if value:
            print(f"{desc}: {value}")
        else:
            print(f"{desc}: No valid response")
    print("-" * 50)


def write_to_serial():
    while True:
        try:
            text = input("Send <<< ")
            if text.lower() in [
                "get_config",
                "gc",
            ]:  # Added "gc" as abbreviation
                get_config()
            else:
                ser.write((text + "\r\n").encode())
                log_to_file(text, "Send <<<")
        except KeyboardInterrupt:
            break


def log_time_intervals(
    finish_to_start, start_to_launch, launch_to_deal, deal_to_finish
):
    """Log time intervals to a separate file"""
    with open("time_intervals-2api.log", "a", encoding="utf-8") as f:
        timestamp = get_timestamp()
        f.write(f"[{timestamp}]\n")
        f.write(f"finish_to_start_time: {finish_to_start}\n")
        f.write(f"start_to_launch_time: {start_to_launch}\n")
        f.write(f"launch_to_deal_time: {launch_to_deal}\n")
        f.write(f"deal_to_finish_time: {deal_to_finish}\n")
        f.write("-" * 50 + "\n")

    # Check if time intervals exceed limits
    try:
        error_message = None
        if finish_to_start > 4:
            error_message = f"Assertion Error: finish_to_start_time ({finish_to_start:.2f}s) > 4s"
        elif start_to_launch > 20:
            error_message = f"Assertion Error: start_to_launch_time ({start_to_launch:.2f}s) > 20s"
        elif launch_to_deal > 20:
            error_message = f"Assertion Error: launch_to_deal_time ({launch_to_deal:.2f}s) > 20s"
        elif deal_to_finish > 2:
            error_message = f"Assertion Error: deal_to_finish_time ({deal_to_finish:.2f}s) > 2s"

        if error_message:
            # Get current round_id
            current_round_id = "unknown"
            if tables and len(tables) > 0 and "round_id" in tables[0]:
                current_round_id = tables[0]["round_id"]

            # Log error to log file, including round_id
            with open("assertion_errors.log", "a", encoding="utf-8") as f:
                timestamp = get_timestamp()
                f.write(
                    f"[{timestamp}] Round ID: {current_round_id} - {error_message}\n"
                )

            # Also log to main log file
            log_to_file(
                f"{error_message} (Round ID: {current_round_id})", "ERROR >>>"
            )

            # Output error message to console, but don't terminate program
            print(
                f"\n[{get_timestamp()}] {error_message} (Round ID: {current_round_id})"
            )
            print("Time interval exceeds limit, but program continues to run")

            # Removed program termination part
            # sys.exit(1)
    except Exception as e:
        log_to_file(f"Error checking time intervals: {e}", "ERROR >>>")
        print(f"Error checking time intervals: {e}")


def execute_finish_post(table, token):
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        if table["name"] == "UAT":
            result = finish_post_v2_uat(post_url, token)
        elif table["name"] == "PRD":
            result = finish_post_v2_prd(post_url, token)
        elif table["name"] == "STG":
            result = finish_post_v2_stg(post_url, token)
        elif table["name"] == "QAT":
            result = finish_post_v2_qat(post_url, token)
        else:
            result = finish_post_v2(post_url, token)
        print(f"Successfully ended this game round for {table['name']}")
        return result
    except Exception as e:
        print(f"Error executing finish_post for {table['name']}: {e}")
        return None


def execute_start_post(table, token):
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        if table["name"] == "UAT":
            round_id, betPeriod = start_post_v2_uat(post_url, token)
        elif table["name"] == "PRD":
            round_id, betPeriod = start_post_v2_prd(post_url, token)
        elif table["name"] == "STG":
            round_id, betPeriod = start_post_v2_stg(post_url, token)
        elif table["name"] == "QAT":
            round_id, betPeriod = start_post_v2_qat(post_url, token)
        else:
            round_id, betPeriod = start_post_v2(post_url, token)

        if round_id != -1:
            table["round_id"] = round_id
            print(
                f"Successfully called start_post for {table['name']}, round_id: {round_id}, betPeriod: {betPeriod}"
            )
            return round_id, betPeriod
        else:
            print(f"Failed to call start_post for {table['name']}")
            return -1, 0
    except Exception as e:
        print(f"Error executing start_post for {table['name']}: {e}")
        return -1, 0


def execute_deal_post(table, token, win_num):
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        if table["name"] == "UAT":
            result = deal_post_v2_uat(
                post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "PRD":
            result = deal_post_v2_prd(
                post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "STG":
            result = deal_post_v2_stg(
                post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "QAT":
            result = deal_post_v2_qat(
                post_url, token, table["round_id"], str(win_num)
            )
        else:
            result = deal_post_v2(
                post_url, token, table["round_id"], str(win_num)
            )
        print(
            f"Successfully sent winning result for {table['name']}: {win_num}"
        )
        return result
    except Exception as e:
        print(f"Error executing deal_post for {table['name']}: {e}")
        return None


def execute_broadcast_post(table, token):
    """Execute broadcast_post to notify relaunch"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        if table["name"] == "UAT":
            result = broadcast_post_v2_uat(
                post_url, token, "roulette.relaunch", "players", 20
            )  # , None)
        elif table["name"] == "PRD":
            result = broadcast_post_v2_prd(
                post_url, token, "roulette.relaunch", "players", 20
            )  # , None)
        elif table["name"] == "STG":
            result = broadcast_post_v2_stg(
                post_url, token, "roulette.relaunch", "players", 20
            )  # , None)
        elif table["name"] == "QAT":
            result = broadcast_post_v2_qat(
                post_url, token, "roulette.relaunch", "players", 20
            )  # , None)
        else:
            result = broadcast_post_v2(
                post_url, token, "roulette.relaunch", "players", 20
            )  # , None)
        print(
            f"Successfully sent broadcast_post (relaunch) for {table['name']}"
        )
        log_to_file(
            f"Successfully sent broadcast_post (relaunch) for {table['name']}",
            "Broadcast >>>",
        )
        return result
    except Exception as e:
        print(f"Error executing broadcast_post for {table['name']}: {e}")
        log_to_file(
            f"Error executing broadcast_post for {table['name']}: {e}",
            "Error >>>",
        )
        return None


def main():
    """Main function for Speed Roulette Controller"""
    # Create and start read thread
    read_thread = threading.Thread(target=read_from_serial)
    read_thread.daemon = True
    read_thread.start()

    # Main thread handles writing
    try:
        write_to_serial()
    except KeyboardInterrupt:
        print("\nProgram ended")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
