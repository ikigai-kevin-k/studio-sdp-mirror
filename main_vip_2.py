import serial
import threading
import time
from datetime import datetime
import sys
import json
import asyncio
import websockets
import urllib3
from requests.exceptions import ConnectionError

sys.path.append(".")  # Ensure los_api can be imported
from table_api.vr.cit_vr_2 import (
    start_post_v2,
    deal_post_v2,
    finish_post_v2,
    broadcast_post_v2,
    bet_stop_post,
)
from table_api.vr.uat_vr_2 import (
    start_post_v2 as start_post_v2_uat,
    deal_post_v2 as deal_post_v2_uat,
    finish_post_v2 as finish_post_v2_uat,
    broadcast_post_v2 as broadcast_post_v2_uat,
    bet_stop_post as bet_stop_post_uat,
)
from table_api.vr.stg_vr_2 import (
    start_post_v2 as start_post_v2_stg,
    deal_post_v2 as deal_post_v2_stg,
    finish_post_v2 as finish_post_v2_stg,
    broadcast_post_v2 as broadcast_post_v2_stg,
    bet_stop_post as bet_stop_post_stg,
)
from table_api.vr.qat_vr_2 import (
    start_post_v2 as start_post_v2_qat,
    deal_post_v2 as deal_post_v2_qat,
    finish_post_v2 as finish_post_v2_qat,
    broadcast_post_v2 as broadcast_post_v2_qat,
    bet_stop_post as bet_stop_post_qat,
)
from concurrent.futures import ThreadPoolExecutor

# Import Studio Alert Manager (with fallback)
try:
    sys.path.append("studio-alert-manager")
    from studio_alert_manager.alert_manager import AlertManager, AlertLevel
    ALERT_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Alert Manager not available: {e}")
    AlertManager = None
    AlertLevel = None
    ALERT_MANAGER_AVAILABLE = False

# Import Slack notification module (fallback)
sys.path.append("slack")  # ensure slack module can be imported
from slack import send_error_to_slack

# Import WebSocket error signal module
sys.path.append("studio_api")  # ensure studio_api module can be imported
from studio_api.ws_err_sig import (
    send_roulette_sensor_stuck_error,
    send_roulette_wrong_ball_dir_error,
)

# Import network checker
from networkChecker import networkChecker

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

# Load device configuration
def load_device_config():
    with open("conf/vr-dev.json", "r") as f:
        return json.load(f)

device_config = load_device_config()

# Parse parity setting
parity_map = {
    "NONE": serial.PARITY_NONE,
    "ODD": serial.PARITY_ODD,
    "EVEN": serial.PARITY_EVEN
}

ser = create_serial_connection(
    port=device_config["dev_port2"],
    baudrate=device_config["baudrate"],
    parity=parity_map.get(device_config["parity"], serial.PARITY_NONE),
    stopbits=device_config["stopbits"],
    bytesize=device_config["bytesize"],
    timeout=device_config["timeout"],
)


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def log_to_file(message, direction):
    with open("self-test-2api.log", "a", encoding="utf-8") as f:
        timestamp = get_timestamp()
        f.write(f"[{timestamp}] {direction} {message}\n")


# Load table configuration
def load_table_config():
    with open("conf/vr-2.json", "r") as f:
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

# Add Alert Manager instance
alert_manager = None

# Add Slack notification variables
sensor_error_sent = False  # Flag to ensure sensor error is only sent once

# Add program termination flag
terminate_program = False  # Flag to terminate program when *X;6 sensor error is detected

# Add retry tracking for alert levels
retry_counts = {}  # Track retry counts for each error type


def send_alert_with_retry_level(error_type, message, environment, table_name=None, error_code=None, is_recoverable=True):
    """
    Send alert with appropriate level based on retry count and recoverability
    
    Args:
        error_type: Unique identifier for this error type
        message: Alert message
        environment: Environment name
        table_name: Table name (optional)
        error_code: Error code (optional)
        is_recoverable: Whether this error is recoverable (default: True)
    """
    global retry_counts
    
    # Initialize retry count for this error type
    if error_type not in retry_counts:
        retry_counts[error_type] = 0
    
    retry_counts[error_type] += 1
    
    # Determine alert level based on recoverability and retry count
    if not is_recoverable:
        # Non-recoverable errors are always ERROR level
        alert_level = "ERROR"
        level_name = "ERROR"
    elif retry_counts[error_type] == 1:
        # First occurrence of recoverable error is WARNING
        alert_level = "WARNING"
        level_name = "WARNING"
    else:
        # Subsequent occurrences of recoverable error are ERROR
        alert_level = "ERROR"
        level_name = "ERROR"
    
    try:
        if alert_manager and ALERT_MANAGER_AVAILABLE:
            # Convert string alert level to AlertLevel enum if available
            if AlertLevel:
                if alert_level == "WARNING":
                    level_enum = AlertLevel.WARNING
                elif alert_level == "ERROR":
                    level_enum = AlertLevel.ERROR
                else:
                    level_enum = AlertLevel.INFO
            else:
                level_enum = None
            
            success = alert_manager.send_alert(
                message=f"{message} (Attempt {retry_counts[error_type]})",
                environment=environment,
                alert_level=level_enum,
                table_name=table_name,
                error_code=error_code
            )
        else:
            # Fallback to direct Slack notification
            success = send_error_to_slack(
                error_message=f"{message} (Attempt {retry_counts[error_type]})",
                environment=environment,
                table_name=table_name,
                error_code=error_code
            )
        
        if success:
            print(f"[{get_timestamp()}] {level_name} alert sent: {message}")
            log_to_file(f"{level_name} alert sent: {message}", "Alert >>>")
        else:
            print(f"[{get_timestamp()}] Failed to send {level_name} alert: {message}")
            log_to_file(f"Failed to send {level_name} alert: {message}", "Alert >>>")
        
        return success
        
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending {level_name} alert: {e}")
        log_to_file(f"Error sending {level_name} alert: {e}", "Alert >>>")
        return False


async def retry_with_network_check(func, *args, max_retries=5, retry_delay=5):
    """
    Retry a function with network error checking.

    Args:
        func: The function to retry
        *args: Arguments to pass to the function
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds

    Returns:
        The result of the function call, or None if all retries failed
    """
    for attempt in range(max_retries + 1):
        try:
            # Check network connectivity before attempting
            if not networkChecker():
                print(f"[{get_timestamp()}] Network check failed, attempt {attempt + 1}/{max_retries + 1}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    print(f"[{get_timestamp()}] Network check failed after {max_retries + 1} attempts")
                    return None

            # Execute the function
            result = func(*args)
            return result

        except ConnectionError as e:
            print(f"[{get_timestamp()}] Connection error on attempt {attempt + 1}/{max_retries + 1}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
                continue
            else:
                print(f"[{get_timestamp()}] Connection error after {max_retries + 1} attempts")
                return None

        except Exception as e:
            print(f"[{get_timestamp()}] Unexpected error on attempt {attempt + 1}/{max_retries + 1}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
                continue
            else:
                print(f"[{get_timestamp()}] Unexpected error after {max_retries + 1} attempts")
                return None

    return None


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


# Function to send sensor error notification using Alert Manager
def send_sensor_error_to_slack():
    """Send sensor error notification using Alert Manager for VIP Roulette table"""
    global sensor_error_sent

    if sensor_error_sent:
        print(
            f"[{get_timestamp()}] Sensor error already sent, skipping..."
        )
        return False

    try:
        if alert_manager:
            # Use Alert Manager for critical sensor error (non-recoverable)
            success = alert_manager.send_critical(
                critical_message="SENSOR ERROR - Detected warning_flag=4 in *X;6 message",
                environment="CIT-2",
                table_name="Studio-Roulette-Test",
                error_code="SENSOR_STUCK"
            )
        else:
            # Fallback to direct Slack notification
            success = send_error_to_slack(
                error_message="SENSOR ERROR - Detected warning_flag=4 in *X;6 message",
                error_code="SENSOR_STUCK",
                table_name="VIP Roulette",
                environment="VIP_ROULETTE",
            )

        if success:
            sensor_error_sent = True
            print(
                f"[{get_timestamp()}] Sensor error notification sent successfully"
            )
            log_to_file(
                "Sensor error notification sent successfully",
                "Alert >>>",
            )
            return True
        else:
            print(
                f"[{get_timestamp()}] Failed to send sensor error notification"
            )
            log_to_file(
                "Failed to send sensor error notification",
                "Alert >>>",
            )
            return False

    except Exception as e:
        print(
            f"[{get_timestamp()}] Error sending sensor error notification: {e}"
        )
        log_to_file(
            f"Error sending sensor error notification: {e}", "Alert >>>"
        )
        return False


# Function to send WebSocket wrong ball direction error signal
def send_websocket_wrong_ball_dir_error_signal():
    """Send WebSocket wrong ball direction error signal for VIP Roulette table"""
    try:
        print(f"[{get_timestamp()}] Sending WebSocket error signal (wrong ball direction)...")
        log_to_file("Sending WebSocket error signal (wrong ball direction)...", "WebSocket >>>")

        # Run the async function and wait for completion
        def send_ws_error():
            try:
                # Send wrong ball direction error signal for VIP Roulette table (ARO-002-2 for backup device)
                result = asyncio.run(send_roulette_wrong_ball_dir_error(
                    table_id="ARO-002",
                    device_id="ARO-002-2"
                ))
                if result:
                    print(
                        f"[{get_timestamp()}] WebSocket wrong ball direction error signal sent successfully"
                    )
                    log_to_file(
                        "WebSocket wrong ball direction error signal sent successfully", "WebSocket >>>"
                    )
                else:
                    print(
                        f"[{get_timestamp()}] WebSocket wrong ball direction error signal failed"
                    )
                    log_to_file(
                        "WebSocket wrong ball direction error signal failed", "WebSocket >>>"
                    )
                return result
            except Exception as e:
                print(
                    f"[{get_timestamp()}] Failed to send WebSocket wrong ball direction error signal: {e}"
                )
                log_to_file(
                    f"Failed to send WebSocket wrong ball direction error signal: {e}",
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
            print(f"[{get_timestamp()}] WebSocket wrong ball direction error signal timeout, proceeding with termination")
            log_to_file("WebSocket wrong ball direction error signal timeout, proceeding with termination", "WebSocket >>>")

        return True

    except Exception as e:
        print(f"[{get_timestamp()}] Error sending WebSocket wrong ball direction error signal: {e}")
        log_to_file(
            f"Error sending WebSocket wrong ball direction error signal: {e}", "WebSocket >>>"
        )
        return False


# Function to send WebSocket error signal (sensor stuck)
def send_websocket_error_signal():
    """Send WebSocket error signal for VIP Roulette table (sensor stuck)"""
    try:
        print(f"[{get_timestamp()}] Sending WebSocket error signal (sensor stuck)...")
        log_to_file("Sending WebSocket error signal (sensor stuck)...", "WebSocket >>>")

        # Run the async function and wait for completion
        def send_ws_error():
            try:
                # Send error signal for VIP Roulette table (ARO-002-2 for backup device)
                result = asyncio.run(send_roulette_sensor_stuck_error(
                    table_id="ARO-002",
                    device_id="ARO-002-2"
                ))
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


async def _execute_finish_post_async(table, token):
    """Async version of execute_finish_post with network retry"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        
        # Check if round_id exists, if not try to get it from table status
        if "round_id" not in table or table["round_id"] is None:
            print(f"No round_id found for {table['name']}, attempting to get current round_id from table status...")
            try:
                # Try to get current round_id from table status
                if table["name"] == "UAT-2":
                    from table_api.vr import uat_vr_2
                    current_round_id = uat_vr_2.get_roundID(post_url, token)
                elif table["name"] == "STG-2":
                    from table_api.vr import stg_vr_2
                    current_round_id = stg_vr_2.get_roundID(post_url, token)
                elif table["name"] == "QAT-2":
                    from table_api.vr import qat_vr_2
                    current_round_id = qat_vr_2.get_roundID(post_url, token)
                else:  # CIT-2
                    from table_api.vr import cit_vr_2
                    current_round_id = cit_vr_2.get_roundID(post_url, token)
                
                if current_round_id:
                    table["round_id"] = current_round_id
                    print(f"Retrieved current round_id: {current_round_id}")
                else:
                    print(f"Error: No round_id found for {table['name']}")
                    return None
            except Exception as e:
                print(f"Error retrieving round_id for {table['name']}: {e}")
                return None
        
        # Import the specific module for this environment
        if table["name"] == "UAT-2":
            from table_api.vr import uat_vr_2
            result = await retry_with_network_check(uat_vr_2.finish_post_v2, post_url, token)
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            result = await retry_with_network_check(stg_vr_2.finish_post_v2, post_url, token)
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            result = await retry_with_network_check(qat_vr_2.finish_post_v2, post_url, token)
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            result = await retry_with_network_check(cit_vr_2.finish_post_v2, post_url, token)
            
        print(f"Successfully ended this game round for {table['name']}")
        return result
    except Exception as e:
        print(f"Error executing finish_post for {table['name']}: {e}")
        return None


def execute_finish_post(table, token):
    """Sync wrapper for async finish_post function"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        access_token = table.get('access_token', '')
        
        # Check if round_id exists, if not try to get it from table status
        if "round_id" not in table or table["round_id"] is None:
            print(f"No round_id found for {table['name']}, attempting to get current round_id from table status...")
            try:
                # Try to get current round_id from table status
                if table["name"] == "UAT-2":
                    from table_api.vr import uat_vr_2
                    current_round_id = uat_vr_2.get_roundID(post_url, token)
                elif table["name"] == "STG-2":
                    from table_api.vr import stg_vr_2
                    current_round_id = stg_vr_2.get_roundID(post_url, token)
                elif table["name"] == "QAT-2":
                    from table_api.vr import qat_vr_2
                    current_round_id = qat_vr_2.get_roundID(post_url, token)
                else:  # CIT-2
                    from table_api.vr import cit_vr_2
                    current_round_id = cit_vr_2.get_roundID(post_url, token)
                
                if current_round_id:
                    table["round_id"] = current_round_id
                    print(f"Retrieved current round_id: {current_round_id}")
                else:
                    print(f"Error: No round_id found for {table['name']}")
                    return None
            except Exception as e:
                print(f"Error retrieving round_id for {table['name']}: {e}")
                return None
        
        # Import the specific module for this environment
        if table["name"] == "UAT-2":
            from table_api.vr import uat_vr_2
            result = uat_vr_2.finish_post_v2(post_url, token)
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            result = stg_vr_2.finish_post_v2(post_url, token)
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            result = qat_vr_2.finish_post_v2(post_url, token)
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            result = cit_vr_2.finish_post_v2(post_url, token)
            
        print(f"Successfully ended this game round for {table['name']}")
        return result
    except Exception as e:
        print(f"Error executing finish_post for {table['name']}: {e}")
        return None


async def _execute_start_post_async(table, token):
    """Async version of execute_start_post with network retry"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        
        # Import the specific module for this environment
        if table["name"] == "UAT-2":
            from table_api.vr import uat_vr_2
            round_id, bet_period = await retry_with_network_check(uat_vr_2.start_post_v2, post_url, token)
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            round_id, bet_period = await retry_with_network_check(stg_vr_2.start_post_v2, post_url, token)
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            round_id, bet_period = await retry_with_network_check(qat_vr_2.start_post_v2, post_url, token)
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            round_id, bet_period = await retry_with_network_check(cit_vr_2.start_post_v2, post_url, token)

        if round_id and round_id != -1:
            table["round_id"] = round_id
            print(
                f"Successfully called start_post for {table['name']}, round_id: {round_id}, betPeriod: {bet_period}"
            )
            return table, round_id, bet_period
        else:
            print(f"Failed to call start_post for {table['name']}")
            print(f"Attempting to finish current round on {table['name']} before retrying...")
            
            # Try to finish the current round
            try:
                # First try to stop betting if the round is still in "opened" state
                print(f"Attempting to stop betting on {table['name']} before finishing...")
                if table["name"] == "UAT-2":
                    from table_api.vr import uat_vr_2
                    await retry_with_network_check(uat_vr_2.bet_stop_post, post_url, token)
                    await retry_with_network_check(uat_vr_2.finish_post_v2, post_url, token)
                elif table["name"] == "STG-2":
                    from table_api.vr import stg_vr_2
                    await retry_with_network_check(stg_vr_2.bet_stop_post, post_url, token)
                    await retry_with_network_check(stg_vr_2.finish_post_v2, post_url, token)
                elif table["name"] == "QAT-2":
                    from table_api.vr import qat_vr_2
                    await retry_with_network_check(qat_vr_2.bet_stop_post, post_url, token)
                    await retry_with_network_check(qat_vr_2.finish_post_v2, post_url, token)
                else:  # CIT-2
                    from table_api.vr import cit_vr_2
                    await retry_with_network_check(cit_vr_2.bet_stop_post, post_url, token)
                    await retry_with_network_check(cit_vr_2.finish_post_v2, post_url, token)
                
                print(f"Successfully finished current round on {table['name']}, retrying start_post...")
                
                # Retry start_post after finishing
                if table["name"] == "UAT-2":
                    from table_api.vr import uat_vr_2
                    round_id, bet_period = await retry_with_network_check(uat_vr_2.start_post_v2, post_url, token)
                elif table["name"] == "STG-2":
                    from table_api.vr import stg_vr_2
                    round_id, bet_period = await retry_with_network_check(stg_vr_2.start_post_v2, post_url, token)
                elif table["name"] == "QAT-2":
                    from table_api.vr import qat_vr_2
                    round_id, bet_period = await retry_with_network_check(qat_vr_2.start_post_v2, post_url, token)
                else:  # CIT-2
                    from table_api.vr import cit_vr_2
                    round_id, bet_period = await retry_with_network_check(cit_vr_2.start_post_v2, post_url, token)
                
                if round_id and round_id != -1:
                    table["round_id"] = round_id
                    print(
                        f"Successfully called start_post after retry for {table['name']}, round_id: {round_id}, betPeriod: {bet_period}"
                    )
                    return table, round_id, bet_period
                else:
                    print(f"Failed to call start_post after retry for {table['name']}")
                    return table, -1, 0
            except Exception as retry_error:
                print(f"Error during finish/retry sequence for {table['name']}: {retry_error}")
                return table, -1, 0
    except Exception as e:
        print(f"Error executing start_post for {table['name']}: {e}")
        return table, -1, 0


def execute_start_post(table, token):
    """Sync wrapper for async start_post function"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        
        # Import the specific module for this environment
        if table["name"] == "UAT-2":
            from table_api.vr import uat_vr_2
            round_id, betPeriod = uat_vr_2.start_post_v2(post_url, token)
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            round_id, betPeriod = stg_vr_2.start_post_v2(post_url, token)
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            round_id, betPeriod = qat_vr_2.start_post_v2(post_url, token)
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            round_id, betPeriod = cit_vr_2.start_post_v2(post_url, token)

        if round_id and round_id != -1:
            table["round_id"] = round_id
            print(
                f"Successfully called start_post for {table['name']}, round_id: {round_id}, betPeriod: {betPeriod}"
            )
            return table, round_id, betPeriod
        else:
            print(f"Failed to call start_post for {table['name']}")
            print(f"Attempting to finish current round on {table['name']} before retrying...")
            
            # Try to finish the current round
            try:
                # First try to stop betting if the round is still in "opened" state
                print(f"Attempting to stop betting on {table['name']} before finishing...")
                if table["name"] == "UAT-2":
                    from table_api.vr import uat_vr_2
                    uat_vr_2.bet_stop_post(post_url, token)
                    uat_vr_2.finish_post_v2(post_url, token)
                elif table["name"] == "STG-2":
                    from table_api.vr import stg_vr_2
                    stg_vr_2.bet_stop_post(post_url, token)
                    stg_vr_2.finish_post_v2(post_url, token)
                elif table["name"] == "QAT-2":
                    from table_api.vr import qat_vr_2
                    qat_vr_2.bet_stop_post(post_url, token)
                    qat_vr_2.finish_post_v2(post_url, token)
                else:  # CIT-2
                    from table_api.vr import cit_vr_2
                    cit_vr_2.bet_stop_post(post_url, token)
                    cit_vr_2.finish_post_v2(post_url, token)
                
                print(f"Successfully finished current round on {table['name']}, retrying start_post...")
                
                # Retry start_post after finishing
                if table["name"] == "UAT-2":
                    from table_api.vr import uat_vr_2
                    round_id, betPeriod = uat_vr_2.start_post_v2(post_url, token)
                elif table["name"] == "STG-2":
                    from table_api.vr import stg_vr_2
                    round_id, betPeriod = stg_vr_2.start_post_v2(post_url, token)
                elif table["name"] == "QAT-2":
                    from table_api.vr import qat_vr_2
                    round_id, betPeriod = qat_vr_2.start_post_v2(post_url, token)
                else:  # CIT-2
                    from table_api.vr import cit_vr_2
                    round_id, betPeriod = cit_vr_2.start_post_v2(post_url, token)
                
                if round_id and round_id != -1:
                    table["round_id"] = round_id
                    print(
                        f"Successfully called start_post after retry for {table['name']}, round_id: {round_id}, betPeriod: {betPeriod}"
                    )
                    return table, round_id, betPeriod
                else:
                    print(f"Failed to call start_post after retry for {table['name']}")
                    return table, -1, 0
            except Exception as retry_error:
                print(f"Error during finish/retry sequence for {table['name']}: {retry_error}")
                return table, -1, 0
    except Exception as e:
        print(f"Error executing start_post for {table['name']}: {e}")
        return table, -1, 0


async def _execute_deal_post_async(table, token, win_num):
    """Async version of execute_deal_post with network retry"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        
        # Check if round_id exists, if not try to get it from table status
        if "round_id" not in table or table["round_id"] is None:
            print(f"No round_id found for {table['name']}, attempting to get current round_id from table status...")
            try:
                # Try to get current round_id from table status
                if table["name"] == "UAT-2":
                    from table_api.vr import uat_vr_2
                    current_round_id = uat_vr_2.get_roundID(post_url, token)
                elif table["name"] == "STG-2":
                    from table_api.vr import stg_vr_2
                    current_round_id = stg_vr_2.get_roundID(post_url, token)
                elif table["name"] == "QAT-2":
                    from table_api.vr import qat_vr_2
                    current_round_id = qat_vr_2.get_roundID(post_url, token)
                else:  # CIT-2
                    from table_api.vr import cit_vr_2
                    current_round_id = cit_vr_2.get_roundID(post_url, token)
                
                if current_round_id:
                    table["round_id"] = current_round_id
                    print(f"Retrieved current round_id: {current_round_id}")
                else:
                    print(f"Error: No round_id found for {table['name']}")
                    return None
            except Exception as e:
                print(f"Error retrieving round_id for {table['name']}: {e}")
                return None
        
        # Import the specific module for this environment
        if table["name"] == "UAT-2":
            from table_api.vr import uat_vr_2
            result = await retry_with_network_check(
                uat_vr_2.deal_post_v2, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            result = await retry_with_network_check(
                stg_vr_2.deal_post_v2, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            result = await retry_with_network_check(
                qat_vr_2.deal_post_v2, post_url, token, table["round_id"], str(win_num)
            )
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            result = await retry_with_network_check(
                cit_vr_2.deal_post_v2, post_url, token, table["round_id"], str(win_num)
            )
        print(
            f"Successfully sent winning result for {table['name']}: {win_num}"
        )
        return result
    except Exception as e:
        print(f"Error executing deal_post for {table['name']}: {e}")
        return None


def execute_deal_post(table, token, win_num):
    """Sync wrapper for async deal_post function"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        
        # Check if round_id exists, if not try to get it from table status
        if "round_id" not in table or table["round_id"] is None:
            print(f"No round_id found for {table['name']}, attempting to get current round_id from table status...")
            try:
                # Try to get current round_id from table status
                if table["name"] == "UAT-2":
                    from table_api.vr import uat_vr_2
                    current_round_id = uat_vr_2.get_roundID(post_url, token)
                elif table["name"] == "STG-2":
                    from table_api.vr import stg_vr_2
                    current_round_id = stg_vr_2.get_roundID(post_url, token)
                elif table["name"] == "QAT-2":
                    from table_api.vr import qat_vr_2
                    current_round_id = qat_vr_2.get_roundID(post_url, token)
                else:  # CIT-2
                    from table_api.vr import cit_vr_2
                    current_round_id = cit_vr_2.get_roundID(post_url, token)
                
                if current_round_id:
                    table["round_id"] = current_round_id
                    print(f"Retrieved current round_id: {current_round_id}")
                else:
                    print(f"Error: No round_id found for {table['name']}")
                    return None
            except Exception as e:
                print(f"Error retrieving round_id for {table['name']}: {e}")
                return None
        
        # Import the specific module for this environment
        if table["name"] == "UAT-2":
            from table_api.vr import uat_vr_2
            result = uat_vr_2.deal_post_v2(
                post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            result = stg_vr_2.deal_post_v2(
                post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            result = qat_vr_2.deal_post_v2(
                post_url, token, table["round_id"], str(win_num)
            )
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            result = cit_vr_2.deal_post_v2(
                post_url, token, table["round_id"], str(win_num)
            )
        print(
            f"Successfully sent winning result for {table['name']}: {win_num}"
        )
        return result
    except Exception as e:
        print(f"Error executing deal_post for {table['name']}: {e}")
        return None


async def _execute_broadcast_post_async(table, token):
    """Async version of execute_broadcast_post with network retry"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        
        # Import the specific module for this environment
        if table["name"] == "UAT-2":
            from table_api.vr import uat_vr_2
            result = await retry_with_network_check(
                uat_vr_2.broadcast_post_v2, post_url, token, "roulette.relaunch", "players", 20
            )
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            result = await retry_with_network_check(
                stg_vr_2.broadcast_post_v2, post_url, token, "roulette.relaunch", "players", 20
            )
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            result = await retry_with_network_check(
                qat_vr_2.broadcast_post_v2, post_url, token, "roulette.relaunch", "players", 20
            )
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            result = await retry_with_network_check(
                cit_vr_2.broadcast_post_v2, post_url, token, "roulette.relaunch", "players", 20
            )

        if result:
            print(
                f"Successfully sent broadcast_post (relaunch) for {table['name']}"
            )
            log_to_file(
                f"Successfully sent broadcast_post (relaunch) for {table['name']}",
                "Broadcast >>>",
            )

            # Send success notification for successful relaunch
            try:
                if alert_manager:
                    alert_manager.send_info(
                        info_message="Roulette relaunch notification sent successfully",
                        environment=table["name"],
                        table_name=table.get("game_code", "Unknown")
                    )
                else:
                    send_error_to_slack(
                        error_message="Roulette relaunch notification sent successfully",
                        environment=table["name"],
                        table_name=table.get("game_code", "Unknown"),
                        error_code="ROULETTE_RELAUNCH",
                    )
                print(f"Success notification sent for {table['name']} relaunch")
            except Exception as alert_error:
                print(f"Failed to send success notification: {alert_error}")
                log_to_file(
                    f"Failed to send success notification: {alert_error}",
                    "Alert >>>",
                )
        else:
            print(
                f"Failed to send broadcast_post (relaunch) for {table['name']}"
            )
            log_to_file(
                f"Failed to send broadcast_post (relaunch) for {table['name']}",
                "Broadcast >>>",
            )

            # Send error notification for failed relaunch
            try:
                send_alert_with_retry_level(
                    error_type=f"broadcast_post_failed_{table['name']}",
                    message="Failed to send roulette relaunch notification",
                    environment=table["name"],
                    table_name=table.get("game_code", "Unknown"),
                    error_code="ROULETTE_RELAUNCH_FAILED",
                    is_recoverable=True
                )
                print(
                    f"Error notification sent for {table['name']} relaunch failure"
                )
            except Exception as alert_error:
                print(
                    f"Failed to send error notification: {alert_error}"
                )
                log_to_file(
                    f"Failed to send error notification: {alert_error}",
                    "Alert >>>",
                )

        return result
    except Exception as e:
        print(f"Error executing broadcast_post for {table['name']}: {e}")
        log_to_file(
            f"Error executing broadcast_post for {table['name']}: {e}",
            "Error >>>",
        )

        # Send exception notification
        try:
            send_alert_with_retry_level(
                error_type=f"broadcast_post_exception_{table['name']}",
                message=f"Exception during broadcast_post: {str(e)}",
                environment=table["name"],
                table_name=table.get("game_code", "Unknown"),
                error_code="BROADCAST_POST_EXCEPTION",
                is_recoverable=False
            )
            print(f"Exception notification sent for {table['name']}")
        except Exception as alert_error:
            print(
                f"Failed to send exception notification: {alert_error}"
            )
            log_to_file(
                f"Failed to send exception notification: {alert_error}",
                "Alert >>>",
            )

        return None


def execute_broadcast_post(table, token):
    """Sync wrapper for async broadcast_post function"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        
        # Import the specific module for this environment
        if table["name"] == "UAT-2":
            from table_api.vr import uat_vr_2
            result = uat_vr_2.broadcast_post_v2(
                post_url, token, "roulette.relaunch", "players", 20
            )  # , None)
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            result = stg_vr_2.broadcast_post_v2(
                post_url, token, "roulette.relaunch", "players", 20
            )  # , None)
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            result = qat_vr_2.broadcast_post_v2(
                post_url, token, "roulette.relaunch", "players", 20
            )  # , None)
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            result = cit_vr_2.broadcast_post_v2(
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

            # Send success notification for successful relaunch
            try:
                if alert_manager:
                    alert_manager.send_info(
                        info_message="Roulette relaunch notification sent successfully",
                        environment=table["name"],
                        table_name=table.get("game_code", "Unknown")
                    )
                else:
                    send_error_to_slack(
                        error_message="Roulette relaunch notification sent successfully",
                        environment=table["name"],
                        table_name=table.get("game_code", "Unknown"),
                        error_code="ROULETTE_RELAUNCH",
                    )
                print(f"Success notification sent for {table['name']} relaunch")
            except Exception as alert_error:
                print(f"Failed to send success notification: {alert_error}")
                log_to_file(
                    f"Failed to send success notification: {alert_error}",
                    "Alert >>>",
                )
        else:
            print(
                f"Failed to send broadcast_post (relaunch) for {table['name']}"
            )
            log_to_file(
                f"Failed to send broadcast_post (relaunch) for {table['name']}",
                "Broadcast >>>",
            )

            # Send error notification for failed relaunch
            try:
                send_alert_with_retry_level(
                    error_type=f"broadcast_post_failed_{table['name']}",
                    message="Failed to send roulette relaunch notification",
                    environment=table["name"],
                    table_name=table.get("game_code", "Unknown"),
                    error_code="ROULETTE_RELAUNCH_FAILED",
                    is_recoverable=True
                )
                print(
                    f"Error notification sent for {table['name']} relaunch failure"
                )
            except Exception as alert_error:
                print(
                    f"Failed to send error notification: {alert_error}"
                )
                log_to_file(
                    f"Failed to send error notification: {alert_error}",
                    "Alert >>>",
                )

        return result
    except Exception as e:
        print(f"Error executing broadcast_post for {table['name']}: {e}")
        log_to_file(
            f"Error executing broadcast_post for {table['name']}: {e}",
            "Error >>>",
        )

        # Send exception notification
        try:
            send_alert_with_retry_level(
                error_type=f"broadcast_post_exception_{table['name']}",
                message=f"Exception during broadcast_post: {str(e)}",
                environment=table["name"],
                table_name=table.get("game_code", "Unknown"),
                error_code="BROADCAST_POST_EXCEPTION",
                is_recoverable=False
            )
            print(f"Exception notification sent for {table['name']}")
        except Exception as alert_error:
            print(
                f"Failed to send exception notification: {alert_error}"
            )
            log_to_file(
                f"Failed to send exception notification: {alert_error}",
                "Alert >>>",
            )

        return None


async def _betStop_round_for_table_async(table, token):
    """Async version of betStop_round_for_table with network retry"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        
        # Import the specific module for this environment
        if table["name"] == "UAT-2":
            from table_api.vr import uat_vr_2
            result = await retry_with_network_check(uat_vr_2.bet_stop_post, post_url, token)
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            result = await retry_with_network_check(stg_vr_2.bet_stop_post, post_url, token)
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            result = await retry_with_network_check(qat_vr_2.bet_stop_post, post_url, token)
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            result = await retry_with_network_check(cit_vr_2.bet_stop_post, post_url, token)

        return table["name"], result

    except Exception as e:
        print(f"Error in betStop_round_for_table for {table['name']}: {e}")
        return table["name"], False


def betStop_round_for_table(table, token):
    """Sync wrapper for async betStop_round_for_table function"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        
        # Import the specific module for this environment
        if table["name"] == "UAT-2":
            from table_api.vr import uat_vr_2
            result = uat_vr_2.bet_stop_post(post_url, token)
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            result = stg_vr_2.bet_stop_post(post_url, token)
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            result = qat_vr_2.bet_stop_post(post_url, token)
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            result = cit_vr_2.bet_stop_post(post_url, token)

        return table["name"], result

    except Exception as e:
        print(f"Error in betStop_round_for_table for {table['name']}: {e}")
        return table["name"], False


def main():
    """Main function for VIP Roulette Controller"""
    global terminate_program, alert_manager

    # Initialize Alert Manager
    if ALERT_MANAGER_AVAILABLE:
        try:
            # Try to load configuration from alert_config.yaml
            try:
                import yaml
                config_path = "studio-alert-manager/config/alert_config.yaml"
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Replace environment variables in config
                import os
                if 'slack' in config:
                    if 'webhook_url' in config['slack']:
                        config['slack']['webhook_url'] = os.path.expandvars(config['slack']['webhook_url'])
                    if 'bot_token' in config['slack']:
                        config['slack']['bot_token'] = os.path.expandvars(config['slack']['bot_token'])
                
                alert_manager = AlertManager(config=config)
                print(f"[{get_timestamp()}] Alert Manager initialized successfully with config file")
            except ImportError:
                # Fallback: Initialize AlertManager without config file
                import os
                alert_manager = AlertManager(
                    webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
                    bot_token=os.getenv("SLACK_BOT_TOKEN"),
                    default_channel="#sdp-alerts"
                )
                print(f"[{get_timestamp()}] Alert Manager initialized successfully with environment variables")
        except Exception as e:
            print(f"[{get_timestamp()}] Failed to initialize Alert Manager: {e}")
            alert_manager = None
    else:
        print(f"[{get_timestamp()}] Alert Manager not available, using direct Slack notifications")
        alert_manager = None

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
            send_websocket_error_signal=send_websocket_error_signal,  # Pass WebSocket error signal callback (sensor stuck)
            send_websocket_wrong_ball_dir_error_signal=send_websocket_wrong_ball_dir_error_signal,  # Pass WebSocket wrong ball direction error signal callback
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
