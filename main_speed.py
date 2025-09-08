import serial
import threading
import time
from datetime import datetime
import sys
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

# Import Slack notification module
sys.path.append("slack")  # ensure slack module can be imported
from slack import send_error_to_slack

# Import WebSocket error signal module
sys.path.append("studio_api")  # ensure studio_api module can be imported
from studio_api.ws_err_sig import send_roulette_sensor_stuck_error

# import sentry_sdk

# sentry_sdk.init(
#     dsn="https://63a51b0fa2f4c419adaf46fafea61e89@o4509115379679232.ingest.us.sentry.io/4509643182440448",
#     # Add data like request headers and IP for users,
#     # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
#     send_default_pii=True,
# )

# Initialize serial connection only if hardware is available
from serial_comm.serialUtils import create_serial_connection
from serial_comm.serialIO import read_from_serial

ser = create_serial_connection(
    port="/dev/ttyUSB1",
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
start_time = 0
deal_post_time = 0
finish_post_time = 0
token = "E5LN4END9Q"
ws_client = None
ws_connected = False

# Add Slack notification variables
sensor_error_sent = False  # Flag to ensure sensor error is only sent once

# Add program termination flag
terminate_program = False  # Flag to terminate program when *X;6 sensor error is detected


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


# Function to send sensor error notification to Slack
def send_sensor_error_to_slack():
    """Send sensor error notification to Slack for Speed Roulette table"""
    global sensor_error_sent

    if sensor_error_sent:
        print(
            f"[{get_timestamp()}] Sensor error already sent to Slack, skipping..."
        )
        return False

    try:
        # Send error notification using the convenience function
        # This function will create its own SlackNotifier instance
        success = send_error_to_slack(
            error_message="SENSOR ERROR - Detected warning_flag=4 in *X;6 message",
            error_code="SENSOR_STUCK",
            table_name="Speed Roulette",
            environment="SPEED_ROULETTE",
        )

        if success:
            sensor_error_sent = True
            print(
                f"[{get_timestamp()}] Sensor error notification sent to Slack successfully"
            )
            log_to_file(
                "Sensor error notification sent to Slack successfully",
                "Slack >>>",
            )
            return True
        else:
            print(
                f"[{get_timestamp()}] Failed to send sensor error notification to Slack"
            )
            log_to_file(
                "Failed to send sensor error notification to Slack",
                "Slack >>>",
            )
            return False

    except Exception as e:
        print(
            f"[{get_timestamp()}] Error sending sensor error notification: {e}"
        )
        log_to_file(
            f"Error sending sensor error notification: {e}", "Slack >>>"
        )
        return False


# Function to send WebSocket error signal
def send_websocket_error_signal():
    """Send WebSocket error signal for Speed Roulette table"""
    try:
        print(f"[{get_timestamp()}] Sending WebSocket error signal...")
        log_to_file("Sending WebSocket error signal...", "WebSocket >>>")

        # Run the async function and wait for completion
        def send_ws_error():
            try:
                result = asyncio.run(send_roulette_sensor_stuck_error())
                if result:
                    print(
                        f"[{get_timestamp()}] WebSocket error signal sent successfully"
                    )
                    log_to_file(
                        "WebSocket error signal sent successfully", "WebSocket >>>"
                    )
                else:
                    print(
                        f"[{get_timestamp()}] WebSocket error signal failed"
                    )
                    log_to_file(
                        "WebSocket error signal failed", "WebSocket >>>"
                    )
                return result
            except Exception as e:
                print(
                    f"[{get_timestamp()}] Failed to send WebSocket error signal: {e}"
                )
                log_to_file(
                    f"Failed to send WebSocket error signal: {e}",
                    "WebSocket >>>",
                )
                return False

        # Start WebSocket error signal in a separate thread and wait for completion
        ws_thread = threading.Thread(target=send_ws_error)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for the WebSocket signal to complete (with timeout)
        ws_thread.join(timeout=10)  # Wait up to 10 seconds
        
        if ws_thread.is_alive():
            print(f"[{get_timestamp()}] WebSocket error signal timeout, proceeding with termination")
            log_to_file("WebSocket error signal timeout, proceeding with termination", "WebSocket >>>")

        return True

    except Exception as e:
        print(f"[{get_timestamp()}] Error sending WebSocket error signal: {e}")
        log_to_file(
            f"Error sending WebSocket error signal: {e}", "WebSocket >>>"
        )
        return False


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


def send_command_and_wait(command, timeout=2):
    """Send a command and wait for the expected response"""
    # Check if serial connection is available
    if ser is None:
        print("Warning: Serial connection not available, cannot send command")
        return None

    ser.write((command + "\r\n").encode())
    log_to_file(command, "Send <<<")

    # Get command type (H, S, T, or R)
    cmd_type = command[-1].lower()

    # Wait for response
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        if ser is not None and ser.in_waiting > 0:
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
    """Legacy function - functionality moved to main() for better termination control"""
    while True:
        try:
            text = input("Send <<< ")
            if text.lower() in [
                "get_config",
                "gc",
            ]:  # Added "gc" as abbreviation
                get_config()
            else:
                # Check if serial connection is available
                if ser is None:
                    print(
                        "Warning: Serial connection not available, cannot send command"
                    )
                    continue
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

        if result:
            print(
                f"Successfully sent broadcast_post (relaunch) for {table['name']}"
            )
            log_to_file(
                f"Successfully sent broadcast_post (relaunch) for {table['name']}",
                "Broadcast >>>",
            )

            # Send Slack notification for successful relaunch
            try:
                send_error_to_slack(
                    error_message="Roulette relaunch notification sent successfully",
                    environment=table["name"],
                    table_name=table.get("game_code", "Unknown"),
                    error_code="ROULETTE_RELAUNCH",
                )
                print(f"Slack notification sent for {table['name']} relaunch")
            except Exception as slack_error:
                print(f"Failed to send Slack notification: {slack_error}")
                log_to_file(
                    f"Failed to send Slack notification: {slack_error}",
                    "Slack >>>",
                )
        else:
            print(
                f"Failed to send broadcast_post (relaunch) for {table['name']}"
            )
            log_to_file(
                f"Failed to send broadcast_post (relaunch) for {table['name']}",
                "Broadcast >>>",
            )

            # Send Slack notification for failed relaunch
            try:
                send_error_to_slack(
                    error_message="Failed to send roulette relaunch notification",
                    environment=table["name"],
                    table_name=table.get("game_code", "Unknown"),
                    error_code="ROULETTE_RELAUNCH_FAILED",
                )
                print(
                    f"Slack error notification sent for {table['name']} relaunch failure"
                )
            except Exception as slack_error:
                print(
                    f"Failed to send Slack error notification: {slack_error}"
                )
                log_to_file(
                    f"Failed to send Slack error notification: {slack_error}",
                    "Slack >>>",
                )

        return result
    except Exception as e:
        print(f"Error executing broadcast_post for {table['name']}: {e}")
        log_to_file(
            f"Error executing broadcast_post for {table['name']}: {e}",
            "Error >>>",
        )

        # Send Slack notification for exception
        try:
            send_error_to_slack(
                error_message=f"Exception during broadcast_post: {str(e)}",
                environment=table["name"],
                table_name=table.get("game_code", "Unknown"),
                error_code="BROADCAST_POST_EXCEPTION",
            )
            print(f"Slack exception notification sent for {table['name']}")
        except Exception as slack_error:
            print(
                f"Failed to send Slack exception notification: {slack_error}"
            )
            log_to_file(
                f"Failed to send Slack exception notification: {slack_error}",
                "Slack >>>",
            )

        return None


def main():
    """Main function for Speed Roulette Controller"""
    global terminate_program

    # Create a wrapper function for read_from_serial with all required parameters
    def read_from_serial_wrapper():
        # Create a dictionary containing all global state variables
        global_vars = {
            "x2_count": x2_count,
            "x5_count": x5_count,
            "last_x2_time": last_x2_time,
            "last_x5_time": last_x5_time,
            "start_post_sent": start_post_sent,
            "deal_post_sent": deal_post_sent,
            "start_time": start_time,
            "deal_post_time": deal_post_time,
            "finish_post_time": finish_post_time,
            "isLaunch": isLaunch,
            "sensor_error_sent": sensor_error_sent,
            "terminate_program": terminate_program,
        }

        read_from_serial(
            ser=ser,
            tables=tables,
            token=token,
            global_vars=global_vars,
            # Callback functions
            get_timestamp=get_timestamp,
            log_to_file=log_to_file,
            send_sensor_error_to_slack=send_sensor_error_to_slack,
            execute_broadcast_post=execute_broadcast_post,
            execute_start_post=execute_start_post,
            execute_deal_post=execute_deal_post,
            execute_finish_post=execute_finish_post,
            send_start_recording=send_start_recording,
            send_stop_recording=send_stop_recording,
            log_time_intervals=log_time_intervals,
        )

    # Create and start read thread
    read_thread = threading.Thread(target=read_from_serial_wrapper)
    read_thread.daemon = True
    read_thread.start()

    # Main thread handles writing and monitors termination flag
    try:
        while not terminate_program:
            try:
                # Check for user input with timeout to allow checking termination flag
                import select
                import sys
                
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    text = input("Send <<< ")
                    if text.lower() in ["get_config", "gc"]:
                        get_config()
                    else:
                        # Check if serial connection is available
                        if ser is None:
                            print("Warning: Serial connection not available, cannot send command")
                            continue
                        ser.write((text + "\r\n").encode())
                        log_to_file(text, "Send <<<")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(0.1)
        
        # Check if program should terminate due to *X;6 sensor error
        if terminate_program:
            print(f"\n[{get_timestamp()}] Program terminating due to *X;6 message detection")
            log_to_file("Program terminating due to *X;6 message detection", "Terminate >>>")
            
    except KeyboardInterrupt:
        print("\nProgram ended by user")
    finally:
        if ser is not None:
            ser.close()
        print(f"[{get_timestamp()}] Program terminated")


if __name__ == "__main__":
    main()
