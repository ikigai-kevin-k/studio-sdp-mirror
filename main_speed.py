import serial
import threading
import time
import os
from datetime import datetime
import sys
import json
import asyncio
import websockets
import urllib3
from requests.exceptions import ConnectionError
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

# Import manual hot reload manager
try:
    from manual_hot_reload_manager import start_manual_hot_reload, stop_manual_hot_reload, setup_signal_handlers
    MANUAL_HOT_RELOAD_AVAILABLE = True
except ImportError:
    MANUAL_HOT_RELOAD_AVAILABLE = False
    print("Warning: Manual hot reload not available.")

# Import log redirector for separated logging
from log_redirector import log_mqtt, log_api, log_serial, log_console, get_timestamp

sys.path.append(".")  # Ensure los_api can be imported
from table_api.sr.api_v2_sr import (
    start_post_v2,
    deal_post_v2,
    finish_post_v2,
    broadcast_post_v2,
    bet_stop_post,
)
from table_api.sr.api_v2_uat_sr import (
    start_post_v2_uat,
    deal_post_v2_uat,
    finish_post_v2_uat,
    broadcast_post_v2_uat,
    bet_stop_post_uat,
)
from table_api.sr.api_v2_prd_sr import (
    start_post_v2_prd,
    deal_post_v2_prd,
    finish_post_v2_prd,
    broadcast_post_v2_prd,
    bet_stop_post_prd,
)
from table_api.sr.api_v2_stg_sr import (
    start_post_v2_stg,
    deal_post_v2_stg,
    finish_post_v2_stg,
    broadcast_post_v2_stg,
    bet_stop_post_stg,
)
from table_api.sr.api_v2_qat_sr import (
    start_post_v2_qat,
    deal_post_v2_qat,
    finish_post_v2_qat,
    broadcast_post_v2_qat,
    bet_stop_post_qat,
)
from table_api.sr.api_v2_sr_5 import (
    start_post_v2 as start_post_v2_cit5,
    deal_post_v2 as deal_post_v2_cit5,
    finish_post_v2 as finish_post_v2_cit5,
    broadcast_post_v2 as broadcast_post_v2_cit5,
    bet_stop_post as bet_stop_post_cit5,
)
from table_api.sr.api_v2_sr_6 import (
    start_post_v2 as start_post_v2_cit6,
    deal_post_v2 as deal_post_v2_cit6,
    finish_post_v2 as finish_post_v2_cit6,
    broadcast_post_v2 as broadcast_post_v2_cit6,
    bet_stop_post as bet_stop_post_cit6,
)
from table_api.sr.api_v2_sr_7 import (
    start_post_v2 as start_post_v2_cit7,
    deal_post_v2 as deal_post_v2_cit7,
    finish_post_v2 as finish_post_v2_cit7,
    broadcast_post_v2 as broadcast_post_v2_cit7,
    bet_stop_post as bet_stop_post_cit7,
)
from table_api.sr.api_v2_prd_sr_5 import (
    start_post_v2_prd as start_post_v2_prd5,
    deal_post_v2_prd as deal_post_v2_prd5,
    finish_post_v2_prd as finish_post_v2_prd5,
    broadcast_post_v2_prd as broadcast_post_v2_prd5,
    bet_stop_post_prd as bet_stop_post_prd5,
)
from table_api.sr.api_v2_prd_sr_6 import (
    start_post_v2_prd as start_post_v2_prd6,
    deal_post_v2_prd as deal_post_v2_prd6,
    finish_post_v2_prd as finish_post_v2_prd6,
    broadcast_post_v2_prd as broadcast_post_v2_prd6,
    bet_stop_post_prd as bet_stop_post_prd6,
)
from table_api.sr.api_v2_prd_sr_7 import (
    start_post_v2_prd as start_post_v2_prd7,
    deal_post_v2_prd as deal_post_v2_prd7,
    finish_post_v2_prd as finish_post_v2_prd7,
    broadcast_post_v2_prd as broadcast_post_v2_prd7,
    bet_stop_post_prd as bet_stop_post_prd7,
)
from table_api.sr.api_v2_glc_sr import (
    start_post_v2_glc,
    deal_post_v2_glc,
    finish_post_v2_glc,
    broadcast_post_v2_glc,
    bet_stop_post_glc,
)
from concurrent.futures import ThreadPoolExecutor

# Import Slack notification module
sys.path.append("slack")  # ensure slack module can be imported
from slack import send_error_to_slack

# Import TableAPI error summary module
from slack.summary import record_table_api_error, start_summary_scheduler

# Import WebSocket error signal module
sys.path.append("studio_api")  # ensure studio_api module can be imported
from studio_api.ws_err_sig import (
    send_roulette_sensor_stuck_error,
    send_roulette_wrong_ball_dir_error,
)

# Import HTTP service status module
sys.path.append("studio_api/http")  # ensure studio_api/http module can be imported
from studio_api.http.status import get_sdp_status, set_sdp_status_via_http

# Import network checker
from networkChecker import networkChecker

# Import environment detection module
from env_detect import (
    detect_environment,
    get_table_id_from_table_code,
    get_device_id_from_table_code,
    get_device_alias,
)

# Import Roulette MQTT detect functionality
from roulette_mqtt_detect import (
    initialize_roulette_mqtt_system,
    roulette_detect_result,
    cleanup_roulette_mqtt_system,
    call_roulette_detect_async
)

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
    import os
    # Try multiple possible paths for configuration file
    possible_paths = [
        "conf/sr_dev.json",  # Original relative path
        os.path.join(os.path.dirname(__file__), "conf", "sr_dev.json"),  # Relative to script location
        "/home/rnd/studio-sdp-roulette/conf/sr_dev.json",  # Absolute path to source
        os.path.join(os.getcwd(), "conf", "sr_dev.json"),  # Relative to current working directory
    ]
    
    for config_path in possible_paths:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
    
    # If no config found, raise an error with helpful message
    raise FileNotFoundError(
        f"Configuration file 'sr_dev.json' not found. Tried paths: {possible_paths}\n"
        f"Current working directory: {os.getcwd()}\n"
        f"Script location: {os.path.dirname(__file__)}"
    )

device_config = load_device_config()

# Get IDP enable/disable setting (default to True for backward compatibility)
ENABLE_IDP = device_config.get("enable_idp", True)

# Detect environment from hostname
detected_table_code, detected_hostname, env_detection_success = detect_environment()

# Set detected table code and table ID as global variables
if env_detection_success:
    DETECTED_TABLE_CODE = detected_table_code
    DETECTED_TABLE_ID = get_table_id_from_table_code(detected_table_code)
    DETECTED_DEVICE_ID = get_device_id_from_table_code(detected_table_code)
    DETECTED_DEVICE_ALIAS = get_device_alias(DETECTED_DEVICE_ID)
    log_console(
        f"Environment detection successful: Table Code={DETECTED_TABLE_CODE}, "
        f"Table ID={DETECTED_TABLE_ID}, Device ID={DETECTED_DEVICE_ID}, "
        f"Device Alias={DETECTED_DEVICE_ALIAS}",
        "ENV_DETECT >>>"
    )
else:
    # Fallback to default values if detection fails
    DETECTED_TABLE_CODE = "ARO-001-1"
    DETECTED_TABLE_ID = "ARO-001"
    DETECTED_DEVICE_ID = "ARO-001-1"
    DETECTED_DEVICE_ALIAS = "main"
    log_console(
        f"Environment detection failed, using default values: "
        f"Table Code={DETECTED_TABLE_CODE}, Table ID={DETECTED_TABLE_ID}, "
        f"Device ID={DETECTED_DEVICE_ID}, Device Alias={DETECTED_DEVICE_ALIAS}",
        "ENV_DETECT >>>"
    )

# Parse parity setting
parity_map = {
    "NONE": serial.PARITY_NONE,
    "ODD": serial.PARITY_ODD,
    "EVEN": serial.PARITY_EVEN
}

ser = create_serial_connection(
    port=device_config["dev_port"],
    baudrate=device_config["baudrate"],
    parity=parity_map.get(device_config["parity"], serial.PARITY_NONE),
    stopbits=device_config["stopbits"],
    bytesize=device_config["bytesize"],
    timeout=device_config["timeout"],
)


# Use log redirector functions instead of local implementations
# get_timestamp is imported from log_redirector

def log_to_file(message, direction):
    """
    Legacy log_to_file function - now redirects to appropriate log type
    Determines log type based on direction and message content
    """
    # Determine log type based on direction and message content
    if "MQTT" in direction or "mqtt" in message.lower():
        log_mqtt(message, direction)
    elif "API" in direction or "api" in message.lower() or "post" in message.lower():
        log_api(message, direction)
    elif "Serial" in direction or "serial" in message.lower() or "Receive" in direction or "Send" in direction:
        log_serial(message, direction)
    else:
        # Default to console for important messages
        log_console(message, direction)


# Load table configuration
def load_table_config():
    import os
    # Try multiple possible paths for table configuration file
    possible_paths = [
        "conf/sr-1.json",  # Original relative path
        os.path.join(os.path.dirname(__file__), "conf", "sr-1.json"),  # Relative to script location
        "/home/rnd/studio-sdp-roulette/conf/sr-1.json",  # Absolute path to source
        os.path.join(os.getcwd(), "conf", "sr-1.json"),  # Relative to current working directory
    ]
    
    for config_path in possible_paths:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
    
    # If no config found, raise an error with helpful message
    raise FileNotFoundError(
        f"Table configuration file 'sr-1.json' not found. Tried paths: {possible_paths}\n"
        f"Current working directory: {os.getcwd()}\n"
        f"Script location: {os.path.dirname(__file__)}"
    )


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
# Game state tracking for auto-recovery
u1_sent = False  # Track if *u 1 command has been sent
betStop_sent = False  # Track if betStop has been sent
finish_post_sent = False  # Track if finish_post has been sent
token = "E5LN4END9Q"
ws_client = None
ws_connected = False

# Add Slack notification variables
sensor_error_sent = False  # Flag to ensure sensor error is only sent once
relaunch_failed_sent = False  # Flag to ensure relaunch failed error is only sent once
wrong_ball_dir_error_sent = False  # Flag to ensure wrong ball direction error is only sent once
launch_fail_error_sent = False  # Flag to ensure launch fail error is only sent once

# Add program termination flag
terminate_program = False  # Flag to terminate program when *X;6 sensor error is detected

# Add mode management
# Mode: "running" (normal operation) or "idle" (maintenance mode)
current_mode = "running"  # Start in running mode
mode_lock = threading.Lock()  # Lock for thread-safe mode access

async def retry_with_network_check(func, *args, max_retries=5, retry_delay=5):
    """
    Retry a function with network error checking.

    Args:
        func: The function to retry
        *args: Arguments to pass to the function
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds

    Returns:
        The result of the function if successful
    """
    retry_count = 0
    while retry_count < max_retries:
        try:
            return (
                await func(*args)
                if asyncio.iscoroutinefunction(func)
                else func(*args)
            )
        except (
            ConnectionError,
            urllib3.exceptions.NewConnectionError,
            urllib3.exceptions.MaxRetryError,
        ) as e:
            is_network_error, error_message = networkChecker(e)
            if is_network_error:
                print(f"[{get_timestamp()}] Network error occurred: {error_message}")
                print(f"[{get_timestamp()}] Waiting {retry_delay} seconds before retry...")
                await asyncio.sleep(retry_delay)
                retry_count += 1
                continue
            raise
    raise Exception(
        f"Max retries ({max_retries}) reached while attempting to execute {func.__name__}"
    )


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

# StudioAPI WebSocket client for receiving "down" signals
studio_api_ws_client = None
studio_api_ws_connected = False


async def init_studio_api_websocket():
    """
    Initialize WebSocket connection to StudioAPI to listen for "down" signals
    """
    global studio_api_ws_client, studio_api_ws_connected
    
    import os
    import json
    
    # Load configuration from ws.json
    config_path = os.path.join(
        os.path.dirname(__file__), "conf", "ws.json"
    )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        SERVER_URL = config.get("server_url", "wss://studio-api.iki-cit.cc/v1/ws")
        TOKEN = config.get("token", "0000")
        # Use detected device ID, fallback to default if detection failed
        DEVICE_ID = DETECTED_DEVICE_ID
    except Exception as e:
        print(f"[{get_timestamp()}] Warning: Could not load ws.json config: {e}")
        SERVER_URL = "wss://studio-api.iki-cit.cc/v1/ws"
        TOKEN = "0000"
        # Use detected device ID, fallback to default if detection failed
        DEVICE_ID = DETECTED_DEVICE_ID
    
    try:
        from studio_api.ws_client import SmartStudioWebSocketClient
        
        # Create WebSocket client
        studio_api_ws_client = SmartStudioWebSocketClient(
            server_url=SERVER_URL,
            table_id=DETECTED_TABLE_ID,
            device_name=DEVICE_ID,
            token=TOKEN,
            fast_connect=True
        )
        
        # Connect to StudioAPI
        if await studio_api_ws_client.connect():
            studio_api_ws_connected = True
            print(f"[{get_timestamp()}] Connected to StudioAPI WebSocket")
            log_to_file("Connected to StudioAPI WebSocket", "StudioAPI >>>")
            
            # Start listening for messages
            await listen_for_studio_api_messages()
        else:
            print(f"[{get_timestamp()}] Failed to connect to StudioAPI WebSocket")
            log_to_file("Failed to connect to StudioAPI WebSocket", "StudioAPI >>>")
            studio_api_ws_connected = False
    except Exception as e:
        print(f"[{get_timestamp()}] Error initializing StudioAPI WebSocket: {e}")
        log_to_file(f"Error initializing StudioAPI WebSocket: {e}", "StudioAPI >>>")
        studio_api_ws_connected = False


async def listen_for_studio_api_messages():
    """
    Listen for messages from StudioAPI WebSocket, specifically "down" signals
    """
    global current_mode, studio_api_ws_client, studio_api_ws_connected
    
    if not studio_api_ws_client or not studio_api_ws_client.websocket:
        return
    
    try:
        while studio_api_ws_connected:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(
                    studio_api_ws_client.websocket.recv(), timeout=1.0
                )
                
                if message:
                    try:
                        # Parse JSON message
                        data = json.loads(message)
                        print(f"[{get_timestamp()}] StudioAPI received message: {data}")
                        log_to_file(f"StudioAPI received message: {data}", "StudioAPI >>>")
                        
                        # Check for "down" signal
                        # Signal format can be: {"signal": {...}, "cmd": {...}} or {"sdp": "down", ...}
                        if isinstance(data, dict):
                            # Check for direct "down" status
                            if data.get("sdp") == "down" or data.get("status") == "down":
                                print(f"[{get_timestamp()}] Received 'down' signal from StudioAPI, switching to idle mode")
                                log_to_file("Received 'down' signal from StudioAPI, switching to idle mode", "StudioAPI >>>")
                                
                                # Switch to idle mode
                                with mode_lock:
                                    if current_mode == "running":
                                        current_mode = "idle"
                                        print(f"[{get_timestamp()}] Mode switched to: {current_mode}")
                                        log_to_file(f"Mode switched to: {current_mode}", "Mode >>>")
                                        
                                        # Trigger idle mode actions
                                        threading.Thread(target=handle_idle_mode).start()
                            
                            # Check for signal in nested structure
                            elif "signal" in data:
                                signal = data.get("signal", {})
                                if isinstance(signal, dict):
                                    msg_id = signal.get("msgId", "")
                                    if "DOWN" in msg_id.upper() or signal.get("content", "").upper() == "DOWN":
                                        print(f"[{get_timestamp()}] Received 'down' signal from StudioAPI, switching to idle mode")
                                        log_to_file("Received 'down' signal from StudioAPI, switching to idle mode", "StudioAPI >>>")
                                        
                                        # Switch to idle mode
                                        with mode_lock:
                                            if current_mode == "running":
                                                current_mode = "idle"
                                                print(f"[{get_timestamp()}] Mode switched to: {current_mode}")
                                                log_to_file(f"Mode switched to: {current_mode}", "Mode >>>")
                                                
                                                # Trigger idle mode actions
                                                threading.Thread(target=handle_idle_mode).start()
                    
                    except json.JSONDecodeError:
                        # Non-JSON message, check if it contains "down"
                        if isinstance(message, str) and "down" in message.lower():
                            print(f"[{get_timestamp()}] Received 'down' message from StudioAPI, switching to idle mode")
                            log_to_file("Received 'down' message from StudioAPI, switching to idle mode", "StudioAPI >>>")
                            
                            # Switch to idle mode
                            with mode_lock:
                                if current_mode == "running":
                                    current_mode = "idle"
                                    print(f"[{get_timestamp()}] Mode switched to: {current_mode}")
                                    log_to_file(f"Mode switched to: {current_mode}", "Mode >>>")
                                    
                                    # Trigger idle mode actions
                                    threading.Thread(target=handle_idle_mode).start()
            
            except asyncio.TimeoutError:
                # Timeout is expected, continue listening
                continue
            except Exception as e:
                print(f"[{get_timestamp()}] Error receiving StudioAPI message: {e}")
                log_to_file(f"Error receiving StudioAPI message: {e}", "StudioAPI >>>")
                await asyncio.sleep(1)
    
    except Exception as e:
        print(f"[{get_timestamp()}] Error in StudioAPI message listener: {e}")
        log_to_file(f"Error in StudioAPI message listener: {e}", "StudioAPI >>>")
        studio_api_ws_connected = False


def start_studio_api_websocket():
    """Start StudioAPI WebSocket connection in a separate thread"""
    asyncio.run(init_studio_api_websocket())


def handle_idle_mode():
    """
    Handle idle mode operations:
    1. Disable error scenario processing (already handled by mode check)
    2. Disable tableAPI calls (already handled by mode check)
    3. Execute ~/startup_sr.sh
    4. Gracefully shutdown main_speed.py
    """
    global terminate_program, current_mode
    
    print(f"[{get_timestamp()}] Entering idle mode operations...")
    log_to_file("Entering idle mode operations...", "Idle Mode >>>")
    
    # Execute ~/startup_sr.sh
    startup_script = os.path.expanduser("~/startup_sr.sh")
    print(f"[{get_timestamp()}] Executing {startup_script}...")
    log_to_file(f"Executing {startup_script}...", "Idle Mode >>>")
    
    try:
        import subprocess
        result = subprocess.run(
            ["bash", startup_script],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print(f"[{get_timestamp()}] {startup_script} executed successfully")
            log_to_file(f"{startup_script} executed successfully", "Idle Mode >>>")
            if result.stdout:
                print(f"[{get_timestamp()}] Script output: {result.stdout}")
                log_to_file(f"Script output: {result.stdout}", "Idle Mode >>>")
        else:
            print(f"[{get_timestamp()}] {startup_script} exited with code {result.returncode}")
            log_to_file(f"{startup_script} exited with code {result.returncode}", "Idle Mode >>>")
            if result.stderr:
                print(f"[{get_timestamp()}] Script error: {result.stderr}")
                log_to_file(f"Script error: {result.stderr}", "Idle Mode >>>")
    
    except subprocess.TimeoutExpired:
        print(f"[{get_timestamp()}] {startup_script} execution timed out")
        log_to_file(f"{startup_script} execution timed out", "Idle Mode >>>")
    except Exception as e:
        print(f"[{get_timestamp()}] Error executing {startup_script}: {e}")
        log_to_file(f"Error executing {startup_script}: {e}", "Idle Mode >>>")
    
    # Gracefully shutdown main_speed.py
    print(f"[{get_timestamp()}] Initiating graceful shutdown...")
    log_to_file("Initiating graceful shutdown...", "Idle Mode >>>")
    
    terminate_program = True


def get_system_boot_time():
    """
    Get system boot time (last reboot time).
    
    Returns:
        datetime: System boot time, or None if error
    """
    try:
        # Get system uptime and calculate boot time
        uptime_sec = float(Path("/proc/uptime").read_text().split()[0])
        boot_time = datetime.now().timestamp() - uptime_sec
        return datetime.fromtimestamp(boot_time)
    except Exception as e:
        print(f"[{get_timestamp()}] Error getting system boot time: {e}")
        log_to_file(f"Error getting system boot time: {e}", "Boot Check >>>")
        return None


def check_recent_reboot_and_send_up():
    """
    Check if system was rebooted within the last 5 minutes.
    If so, automatically send sdp: up request.
    
    This handles the scenario where another host's main_speed.py
    received sdp: down, SSH'd to this host, and executed reboot.
    """
    boot_time = get_system_boot_time()
    if boot_time is None:
        print(f"[{get_timestamp()}] Could not determine boot time, skipping reboot check")
        log_to_file("Could not determine boot time, skipping reboot check", "Boot Check >>>")
        return
    
    current_time = datetime.now()
    time_since_boot = (current_time - boot_time).total_seconds()
    minutes_since_boot = time_since_boot / 60.0
    
    print(f"[{get_timestamp()}] System boot time: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[{get_timestamp()}] Time since boot: {minutes_since_boot:.2f} minutes")
    log_to_file(f"System boot time: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}", "Boot Check >>>")
    log_to_file(f"Time since boot: {minutes_since_boot:.2f} minutes", "Boot Check >>>")
    
    # Check if reboot was within last 5 minutes
    if minutes_since_boot <= 5.0:
        print(f"[{get_timestamp()}] System rebooted within last 5 minutes, sending sdp: up request")
        log_to_file("System rebooted within last 5 minutes, sending sdp: up request", "Boot Check >>>")
        
        # Send sdp: up request using detected table ID
        table_id = DETECTED_TABLE_ID
        success = set_sdp_status_via_http(table_id, "up")
        
        if success:
            print(f"[{get_timestamp()}] Successfully sent sdp: up request after reboot detection")
            log_to_file("Successfully sent sdp: up request after reboot detection", "Boot Check >>>")
        else:
            print(f"[{get_timestamp()}] Failed to send sdp: up request after reboot detection")
            log_to_file("Failed to send sdp: up request after reboot detection", "Boot Check >>>")
    else:
        print(f"[{get_timestamp()}] System boot time is more than 5 minutes ago, no action needed")
        log_to_file(f"System boot time is more than 5 minutes ago ({minutes_since_boot:.2f} minutes), no action needed", "Boot Check >>>")


def check_service_status_and_switch_mode():
    """
    Check service status from HTTP API and switch mode based on SDP status.
    This function runs in a separate thread to periodically check the service status.
    
    Mode switching logic:
    - "down_pause" or "down_cancel" -> switch to idle mode
    - "up_cancel" or "up_resume" -> switch to running mode
    """
    global current_mode
    
    try:
        # Get SDP status from service status API
        sdp_status = get_sdp_status(DETECTED_TABLE_ID)
        
        if sdp_status is None:
            # API call failed, log but don't change mode
            log_to_file(
                f"Failed to get SDP status from service status API for table {DETECTED_TABLE_ID}",
                "HTTP API >>>"
            )
            return
        
        log_to_file(
            f"Service status check: SDP status = {sdp_status} (current mode = {current_mode})",
            "HTTP API >>>"
        )
        
        # Check if we need to switch to idle mode
        if sdp_status in ["down_pause", "down_cancel"]:
            with mode_lock:
                if current_mode == "running":
                    current_mode = "idle"
                    print(f"[{get_timestamp()}] Mode switched to idle (SDP status: {sdp_status})")
                    log_to_file(
                        f"Mode switched to idle mode due to SDP status: {sdp_status}",
                        "Mode >>>"
                    )
        
        # Check if we need to switch to running mode
        elif sdp_status in ["up_cancel", "up_resume"]:
            with mode_lock:
                if current_mode == "idle":
                    current_mode = "running"
                    print(f"[{get_timestamp()}] Mode switched to running (SDP status: {sdp_status})")
                    log_to_file(
                        f"Mode switched to running mode due to SDP status: {sdp_status}",
                        "Mode >>>"
                    )
        
    except Exception as e:
        log_to_file(
            f"Error checking service status and switching mode: {e}",
            "HTTP API >>>"
        )
        print(f"[{get_timestamp()}] Error checking service status: {e}")


def service_status_monitor():
    """
    Monitor service status periodically in a separate thread.
    Checks service status every 5 seconds.
    """
    while not terminate_program:
        try:
            check_service_status_and_switch_mode()
            # Wait 5 seconds before next check
            time.sleep(5)
        except Exception as e:
            log_to_file(
                f"Error in service status monitor: {e}",
                "HTTP API >>>"
            )
            # Wait 5 seconds before retry even on error
            time.sleep(5)


# HTTP server for receiving PATCH requests
class StatusRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for receiving service status PATCH requests"""
    
    def do_PATCH(self):
        """Handle PATCH requests for service status updates"""
        global current_mode, mode_lock
        
        # Only handle /v1/service/status endpoint
        if self.path != "/v1/service/status":
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = json.dumps({"error": {"code": 404, "message": "Not found"}})
            self.wfile.write(response.encode())
            return
        
        # Check headers
        content_length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")
        x_signature = self.headers.get("x-signature", "")
        
        # Verify signature (optional, but recommended)
        if x_signature != "rgs-local-signature":
            print(f"[{get_timestamp()}] Invalid signature in PATCH request: {x_signature}")
            log_to_file(f"Invalid signature in PATCH request: {x_signature}", "HTTP Server >>>")
            # Continue anyway for now, but log it
        
        # Read request body
        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            
            print(f"[{get_timestamp()}] Received PATCH request: {data}")
            log_to_file(f"Received PATCH request: {data}", "HTTP Server >>>")
            
            # Check if this is for detected table ID and sdp is "up"
            table_id = data.get("tableId", "")
            sdp_status = data.get("sdp", "")
            
            if table_id == DETECTED_TABLE_ID and sdp_status == "up":
                print(f"[{get_timestamp()}] Received sdp: up request for {DETECTED_TABLE_ID}, switching to running mode")
                log_to_file(f"Received sdp: up request for {DETECTED_TABLE_ID}, switching to running mode", "HTTP Server >>>")
                
                # Switch to running mode
                with mode_lock:
                    if current_mode == "idle":
                        current_mode = "running"
                        print(f"[{get_timestamp()}] Mode switched to: {current_mode}")
                        log_to_file(f"Mode switched to: {current_mode}", "Mode >>>")
                    else:
                        print(f"[{get_timestamp()}] Already in {current_mode} mode, no change needed")
                        log_to_file(f"Already in {current_mode} mode, no change needed", "Mode >>>")
                
                # Send success response
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response_data = {
                    "error": None,
                    "data": {
                        "tableId": table_id,
                        "sdp": sdp_status
                    }
                }
                response = json.dumps(response_data)
                self.wfile.write(response.encode())
                return
            else:
                # Not the request we're looking for, but respond anyway
                print(f"[{get_timestamp()}] Received PATCH request for {table_id} with sdp: {sdp_status} (not {DETECTED_TABLE_ID} up)")
                log_to_file(f"Received PATCH request for {table_id} with sdp: {sdp_status} (not {DETECTED_TABLE_ID} up)", "HTTP Server >>>")
                
                # Send success response anyway
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                response_data = {
                    "error": None,
                    "data": {
                        "tableId": table_id,
                        "sdp": sdp_status
                    }
                }
                response = json.dumps(response_data)
                self.wfile.write(response.encode())
                return
                
        except json.JSONDecodeError as e:
            print(f"[{get_timestamp()}] Error parsing JSON in PATCH request: {e}")
            log_to_file(f"Error parsing JSON in PATCH request: {e}", "HTTP Server >>>")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = json.dumps({"error": {"code": 400, "message": "Invalid JSON"}})
            self.wfile.write(response.encode())
            return
        except Exception as e:
            print(f"[{get_timestamp()}] Error handling PATCH request: {e}")
            log_to_file(f"Error handling PATCH request: {e}", "HTTP Server >>>")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = json.dumps({"error": {"code": 500, "message": str(e)}})
            self.wfile.write(response.encode())
            return
    
    def log_message(self, format, *args):
        """Override to use our logging function"""
        message = format % args
        log_to_file(message, "HTTP Server >>>")


def start_http_server(port=8085):
    """
    Start HTTP server to receive PATCH requests for service status updates.
    
    Args:
        port (int): Port number to listen on (default: 8085, to avoid conflict with Studio API on 8084)
    """
    global terminate_program
    try:
        server = HTTPServer(("0.0.0.0", port), StatusRequestHandler)
        print(f"[{get_timestamp()}] HTTP server started on port {port}")
        log_to_file(f"HTTP server started on port {port}", "HTTP Server >>>")
        
        # Serve with timeout to allow checking terminate_program flag
        while not terminate_program:
            server.timeout = 1.0
            server.handle_request()
        
        # Close server when terminating
        server.server_close()
        print(f"[{get_timestamp()}] HTTP server stopped")
        log_to_file("HTTP server stopped", "HTTP Server >>>")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"[{get_timestamp()}] Port {port} already in use, trying alternative port {port + 1}")
            log_to_file(f"Port {port} already in use, trying alternative port {port + 1}", "HTTP Server >>>")
            try:
                server = HTTPServer(("0.0.0.0", port + 1), StatusRequestHandler)
                print(f"[{get_timestamp()}] HTTP server started on alternative port {port + 1}")
                log_to_file(f"HTTP server started on alternative port {port + 1}", "HTTP Server >>>")
                
                # Serve with timeout to allow checking terminate_program flag
                while not terminate_program:
                    server.timeout = 1.0
                    server.handle_request()
                
                # Close server when terminating
                server.server_close()
                print(f"[{get_timestamp()}] HTTP server stopped")
                log_to_file("HTTP server stopped", "HTTP Server >>>")
            except Exception as e2:
                print(f"[{get_timestamp()}] Error starting HTTP server on alternative port: {e2}")
                log_to_file(f"Error starting HTTP server on alternative port: {e2}", "HTTP Server >>>")
        else:
            print(f"[{get_timestamp()}] Error starting HTTP server: {e}")
            log_to_file(f"Error starting HTTP server: {e}", "HTTP Server >>>")
    except Exception as e:
        print(f"[{get_timestamp()}] Error starting HTTP server: {e}")
        log_to_file(f"Error starting HTTP server: {e}", "HTTP Server >>>")


# Function to send sensor error notification to Slack
def send_sensor_error_to_slack():
    """Send sensor error notification to Slack for Speed Roulette table"""
    global sensor_error_sent, current_mode
    
    # Skip error handling in idle mode
    with mode_lock:
        if current_mode == "idle":
            return False

    if sensor_error_sent:
        print(
            f"[{get_timestamp()}] Sensor error already sent to Slack, skipping..."
        )
        return False

    try:
        # Import the specialized roulette sensor error function
        from slack.slack_notifier import send_roulette_sensor_error_to_slack

        # Send roulette sensor error notification with specialized format
        success = send_roulette_sensor_error_to_slack(
            action_message="relaunch the wheel controller with *P 1",
            table_name=f"{DETECTED_DEVICE_ID} (speed - {DETECTED_DEVICE_ALIAS})",
            error_code="SENSOR_STUCK",
            mention_user="Kevin Kuo",  # Mention Kevin Kuo for sensor errors
            channel="#alert-ge-studio",  # Send sensor errors to alert-ge-studio channel
        )

        if success:
            sensor_error_sent = True
            print(
                f"[{get_timestamp()}] Sensor error notification sent to Slack successfully (with mention)"
            )
            log_to_file(
                "Sensor error notification sent to Slack successfully (with mention)",
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


# Function to send wrong ball direction error notification to Slack
def send_wrong_ball_dir_error_to_slack():
    """Send wrong ball direction error notification to Slack for Speed Roulette table"""
    global wrong_ball_dir_error_sent, current_mode
    
    # Skip error handling in idle mode
    with mode_lock:
        if current_mode == "idle":
            return False

    if wrong_ball_dir_error_sent:
        print(
            f"[{get_timestamp()}] Wrong ball direction error already sent to Slack, skipping..."
        )
        return False

    try:
        # Import the specialized roulette sensor error function
        from slack.slack_notifier import send_roulette_sensor_error_to_slack

        # Send wrong ball direction error notification with specialized format
        # This error can be auto-recovered, so send to alert-tw-studio with Kevin Kuo
        success = send_roulette_sensor_error_to_slack(
            action_message="None (can be auto-recovered)",
            table_name=f"{DETECTED_DEVICE_ID} (speed - {DETECTED_DEVICE_ALIAS})",
            error_code="ROUELTTE_WRONG_BALL_DIR",  # Note: Using ErrorMsgId enum value (has typo in enum)
            mention_user="Kevin Kuo",  # Mention Kevin Kuo for auto-recoverable errors
            channel="#alert-tw-studio",  # Send auto-recoverable errors to alert-tw-studio channel
        )

        if success:
            wrong_ball_dir_error_sent = True
            print(
                f"[{get_timestamp()}] Wrong ball direction error notification sent to Slack successfully (with mention)"
            )
            log_to_file(
                "Wrong ball direction error notification sent to Slack successfully (with mention)",
                "Slack >>>",
            )
            return True
        else:
            print(
                f"[{get_timestamp()}] Failed to send wrong ball direction error notification to Slack"
            )
            log_to_file(
                "Failed to send wrong ball direction error notification to Slack",
                "Slack >>>",
            )
            return False

    except Exception as e:
        print(
            f"[{get_timestamp()}] Error sending wrong ball direction error notification: {e}"
        )
        log_to_file(
            f"Error sending wrong ball direction error notification: {e}", "Slack >>>"
        )
        return False


# Function to send launch fail error notification to Slack
def send_launch_fail_error_to_slack():
    """Send launch fail error notification to Slack for Speed Roulette table"""
    global launch_fail_error_sent, current_mode
    
    # Skip error handling in idle mode
    with mode_lock:
        if current_mode == "idle":
            return False

    if launch_fail_error_sent:
        print(
            f"[{get_timestamp()}] Launch fail error already sent to Slack, skipping..."
        )
        return False

    try:
        # Import the specialized roulette sensor error function
        from slack.slack_notifier import send_roulette_sensor_error_to_slack

        # Send launch fail error notification with specialized format
        # This error can be auto-recovered, so send to alert-tw-studio with Kevin Kuo
        success = send_roulette_sensor_error_to_slack(
            action_message="None (can be auto-recovered)",
            table_name=f"{DETECTED_DEVICE_ID} (speed - {DETECTED_DEVICE_ALIAS})",
            error_code="ROULETTE_LAUNCH_FAIL",
            mention_user="Kevin Kuo",  # Mention Kevin Kuo for auto-recoverable errors
            channel="#alert-tw-studio",  # Send auto-recoverable errors to alert-tw-studio channel
        )

        if success:
            launch_fail_error_sent = True
            print(
                f"[{get_timestamp()}] Launch fail error notification sent to Slack successfully (with mention)"
            )
            log_to_file(
                "Launch fail error notification sent to Slack successfully (with mention)",
                "Slack >>>",
            )
            return True
        else:
            print(
                f"[{get_timestamp()}] Failed to send launch fail error notification to Slack"
            )
            log_to_file(
                "Failed to send launch fail error notification to Slack",
                "Slack >>>",
            )
            return False

    except Exception as e:
        print(
            f"[{get_timestamp()}] Error sending launch fail error notification: {e}"
        )
        log_to_file(
            f"Error sending launch fail error notification: {e}", "Slack >>>"
        )
        return False


# Function to send relaunch failed notification to Slack
def send_relaunch_failed_to_slack():
    """Send relaunch failed notification to Slack with specialized format"""
    global relaunch_failed_sent

    if relaunch_failed_sent:
        print(
            f"[{get_timestamp()}] Relaunch failed error already sent to Slack, skipping..."
        )
        return False

    try:
        # Import the specialized roulette sensor error function
        from slack.slack_notifier import send_roulette_sensor_error_to_slack

        # Send roulette relaunch failed notification with specialized format
        # Action is None (can be auto-recovered)
        # Auto-recoverable errors go to alert-tw-studio with Kevin Kuo
        success = send_roulette_sensor_error_to_slack(
            action_message="None (can be auto-recovered)",
            table_name=f"{DETECTED_DEVICE_ID} (speed - {DETECTED_DEVICE_ALIAS})",
            error_code="ROULETTE_RELAUNCH_FAILED",
            mention_user="Kevin Kuo",  # Mention Kevin Kuo for auto-recoverable errors
            channel="#alert-tw-studio",  # Send auto-recoverable errors to alert-tw-studio channel
        )

        if success:
            relaunch_failed_sent = True
            print(
                f"[{get_timestamp()}] Relaunch failed notification sent to Slack successfully (with mention)"
            )
            log_to_file(
                "Relaunch failed notification sent to Slack successfully (with mention)",
                "Slack >>>",
            )
            return True
        else:
            print(
                f"[{get_timestamp()}] Failed to send relaunch failed notification to Slack"
            )
            log_to_file(
                "Failed to send relaunch failed notification to Slack",
                "Slack >>>",
            )
            return False

    except Exception as e:
        print(
            f"[{get_timestamp()}] Error sending relaunch failed notification: {e}"
        )
        log_to_file(
            f"Error sending relaunch failed notification: {e}", "Slack >>>"
        )
        return False


# Function to send WebSocket wrong ball direction error signal
def send_websocket_wrong_ball_dir_error_signal():
    """Send WebSocket wrong ball direction error signal for Speed Roulette table"""
    global current_mode
    
    # Skip error handling in idle mode
    with mode_lock:
        if current_mode == "idle":
            return False
    
    try:
        print(f"[{get_timestamp()}] Sending WebSocket error signal (wrong ball direction)...")
        log_to_file("Sending WebSocket error signal (wrong ball direction)...", "WebSocket >>>")

        # Run the async function and wait for completion
        def send_ws_error():
            try:
                # Send wrong ball direction error signal for Speed Roulette table
                result = asyncio.run(send_roulette_wrong_ball_dir_error(
                    table_id=DETECTED_TABLE_ID,
                    device_id=DETECTED_DEVICE_ID
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
    """Send WebSocket error signal for Speed Roulette table"""
    global ws_connected, ws_client, current_mode
    
    # Skip error handling in idle mode
    with mode_lock:
        if current_mode == "idle":
            return False
    
    try:
        print(f"[{get_timestamp()}] Sending WebSocket error signal...")
        log_to_file("Sending WebSocket error signal...", "WebSocket >>>")

        # Run the async function and wait for completion
        def send_ws_error():
            try:
                # Send error signal specifically for Speed Roulette table
                result = asyncio.run(send_roulette_sensor_stuck_error(
                    table_id=DETECTED_TABLE_ID, 
                    device_id=DETECTED_DEVICE_ID
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
        
        # Ensure WebSocket connection is properly closed after sending error signal
        try:
            if ws_connected and ws_client:
                print(f"[{get_timestamp()}] Disconnecting WebSocket after error signal...")
                log_to_file("Disconnecting WebSocket after error signal...", "WebSocket >>>")
                asyncio.run(ws_client.close())
                ws_connected = False
                print(f"[{get_timestamp()}] WebSocket disconnected successfully")
                log_to_file("WebSocket disconnected successfully", "WebSocket >>>")
        except Exception as e:
            print(f"[{get_timestamp()}] Error disconnecting WebSocket: {e}")
            log_to_file(f"Error disconnecting WebSocket: {e}", "WebSocket >>>")

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
        log_serial("Warning: Serial connection not available, cannot send command")
        return None

    ser.write((command + "\r\n").encode())
    log_serial(command, "Send <<<")

    # Get command type (H, S, T, or R)
    cmd_type = command[-1].lower()

    # Wait for response
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        if ser is not None and ser.in_waiting > 0:
            response = ser.readline().decode("utf-8").strip()
            log_serial(f"Receive >>> {response}")
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
    """Finish round for a single table - async implementation"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        if table["name"] == "CIT":
            await retry_with_network_check(finish_post_v2, post_url, token)
        elif table["name"] == "UAT":
            await retry_with_network_check(finish_post_v2_uat, post_url, token)
        elif table["name"] == "PRD":
            await retry_with_network_check(finish_post_v2_prd, post_url, token)
        elif table["name"] == "STG":
            await retry_with_network_check(finish_post_v2_stg, post_url, token)
        elif table["name"] == "QAT":
            await retry_with_network_check(finish_post_v2_qat, post_url, token)
        elif table["name"] == "CIT-5":
            await retry_with_network_check(finish_post_v2_cit5, post_url, token)
        elif table["name"] == "CIT-6":
            await retry_with_network_check(finish_post_v2_cit6, post_url, token)
        elif table["name"] == "CIT-7":
            await retry_with_network_check(finish_post_v2_cit7, post_url, token)
        elif table["name"] == "PRD-5":
            await retry_with_network_check(finish_post_v2_prd5, post_url, token)
        elif table["name"] == "PRD-6":
            await retry_with_network_check(finish_post_v2_prd6, post_url, token)
        elif table["name"] == "PRD-7":
            await retry_with_network_check(finish_post_v2_prd7, post_url, token)
        elif table["name"] == "GLC":
            await retry_with_network_check(finish_post_v2_glc, post_url, token)
        else:
            return None

        log_api(f"Successfully ended this game round for {table['name']}", "API >>>")
        return table["name"], True

    except Exception as e:
        error_msg = str(e)
        log_api(f"Error executing finish_post for {table['name']}: {error_msg}", "API >>>")
        # Record error to summary instead of sending Slack notification immediately
        try:
            record_table_api_error(
                environment=table["name"],
                api_type="finish",
                table_name=table.get("game_code", "Unknown"),
                error_message=error_msg,
            )
        except Exception as summary_error:
            log_api(f"Error recording to summary: {summary_error}", "API >>>")
        return table["name"], False


def execute_finish_post(table, token):
    """Finish round for a single table - synchronous wrapper"""
    global current_mode
    
    # Skip tableAPI calls in idle mode
    with mode_lock:
        if current_mode == "idle":
            print(f"[{get_timestamp()}] Skipping finish_post in idle mode")
            log_to_file("Skipping finish_post in idle mode", "Idle Mode >>>")
            return None, False
    
    return asyncio.run(_execute_finish_post_async(table, token))


async def _execute_start_post_async(table, token):
    """Start round for a single table - async implementation"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        if table["name"] == "CIT":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2, post_url, token
            )
        elif table["name"] == "UAT":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_uat, post_url, token
            )
        elif table["name"] == "PRD":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_prd, post_url, token
            )
        elif table["name"] == "STG":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_stg, post_url, token
            )
        elif table["name"] == "QAT":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_qat, post_url, token
            )
        elif table["name"] == "CIT-5":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_cit5, post_url, token
            )
        elif table["name"] == "CIT-6":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_cit6, post_url, token
            )
        elif table["name"] == "CIT-7":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_cit7, post_url, token
            )
        elif table["name"] == "PRD-5":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_prd5, post_url, token
            )
        elif table["name"] == "PRD-6":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_prd6, post_url, token
            )
        elif table["name"] == "PRD-7":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_prd7, post_url, token
            )
        elif table["name"] == "GLC":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_glc, post_url, token
            )
        else:
            return None, None

        if round_id != -1:
            table["round_id"] = round_id
            log_api(
                f"Successfully called start_post for {table['name']}, round_id: {round_id}, bet_period: {bet_period}",
                "API >>>"
            )
            return table, round_id, bet_period
        else:
            log_api(f"Failed to call start_post for {table['name']}", "API >>>")
            # Record error to summary instead of sending Slack notification immediately
            try:
                record_table_api_error(
                    environment=table["name"],
                    api_type="start",
                    table_name=table.get("game_code", "Unknown"),
                    error_message="Failed to call start_post (round_id == -1)",
                )
            except Exception as summary_error:
                log_api(f"Error recording to summary: {summary_error}", "API >>>")
            return None, None
    except Exception as e:
        error_msg = str(e)
        log_api(f"Error executing start_post for {table['name']}: {error_msg}", "API >>>")
        # Record error to summary instead of sending Slack notification immediately
        try:
            record_table_api_error(
                environment=table["name"],
                api_type="start",
                table_name=table.get("game_code", "Unknown"),
                error_message=error_msg,
            )
        except Exception as summary_error:
            log_api(f"Error recording to summary: {summary_error}", "API >>>")
        return None, None


def execute_start_post(table, token):
    """Start round for a single table - synchronous wrapper"""
    global current_mode
    
    # Skip tableAPI calls in idle mode
    with mode_lock:
        if current_mode == "idle":
            print(f"[{get_timestamp()}] Skipping start_post in idle mode")
            log_to_file("Skipping start_post in idle mode", "Idle Mode >>>")
            return None, None
    
    return asyncio.run(_execute_start_post_async(table, token))


async def _execute_deal_post_async(table, token, win_num):
    """Deal round for a single table - async implementation"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        if table["name"] == "CIT":
            await retry_with_network_check(
                deal_post_v2, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "UAT":
            await retry_with_network_check(
                deal_post_v2_uat, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "PRD":
            await retry_with_network_check(
                deal_post_v2_prd, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "STG":
            await retry_with_network_check(
                deal_post_v2_stg, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "QAT":
            await retry_with_network_check(
                deal_post_v2_qat, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "CIT-5":
            await retry_with_network_check(
                deal_post_v2_cit5, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "CIT-6":
            await retry_with_network_check(
                deal_post_v2_cit6, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "CIT-7":
            await retry_with_network_check(
                deal_post_v2_cit7, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "PRD-5":
            await retry_with_network_check(
                deal_post_v2_prd5, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "PRD-6":
            await retry_with_network_check(
                deal_post_v2_prd6, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "PRD-7":
            await retry_with_network_check(
                deal_post_v2_prd7, post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "GLC":
            await retry_with_network_check(
                deal_post_v2_glc, post_url, token, table["round_id"], str(win_num)
            )
        else:
            return None

        log_api(
            f"Successfully sent winning result for {table['name']}: {win_num}",
            "API >>>"
        )
        return table["name"], True

    except Exception as e:
        error_msg = str(e)
        log_api(f"Error executing deal_post for {table['name']}: {error_msg}", "API >>>")
        # Record error to summary instead of sending Slack notification immediately
        try:
            record_table_api_error(
                environment=table["name"],
                api_type="deal",
                table_name=table.get("game_code", "Unknown"),
                error_message=error_msg,
            )
        except Exception as summary_error:
            log_api(f"Error recording to summary: {summary_error}", "API >>>")
        return table["name"], False


def execute_deal_post(table, token, win_num):
    """Deal round for a single table - synchronous wrapper"""
    global current_mode
    
    # Skip tableAPI calls in idle mode
    with mode_lock:
        if current_mode == "idle":
            print(f"[{get_timestamp()}] Skipping deal_post in idle mode")
            log_to_file("Skipping deal_post in idle mode", "Idle Mode >>>")
            return None, False
    
    return asyncio.run(_execute_deal_post_async(table, token, win_num))


async def _betStop_round_for_table_async(table, token):
    """Stop betting for a single table - async implementation"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        if table["name"] == "CIT":
            await retry_with_network_check(bet_stop_post, post_url, token)
        elif table["name"] == "UAT":
            await retry_with_network_check(bet_stop_post_uat, post_url, token)
        elif table["name"] == "PRD":
            await retry_with_network_check(bet_stop_post_prd, post_url, token)
        elif table["name"] == "STG":
            await retry_with_network_check(bet_stop_post_stg, post_url, token)
        elif table["name"] == "QAT":
            await retry_with_network_check(bet_stop_post_qat, post_url, token)
        elif table["name"] == "CIT-5":
            await retry_with_network_check(bet_stop_post_cit5, post_url, token)
        elif table["name"] == "CIT-6":
            await retry_with_network_check(bet_stop_post_cit6, post_url, token)
        elif table["name"] == "CIT-7":
            await retry_with_network_check(bet_stop_post_cit7, post_url, token)
        elif table["name"] == "PRD-5":
            await retry_with_network_check(bet_stop_post_prd5, post_url, token)
        elif table["name"] == "PRD-6":
            await retry_with_network_check(bet_stop_post_prd6, post_url, token)
        elif table["name"] == "PRD-7":
            await retry_with_network_check(bet_stop_post_prd7, post_url, token)
        elif table["name"] == "GLC":
            await retry_with_network_check(bet_stop_post_glc, post_url, token)
        else:
            return table["name"], False

        return table["name"], True

    except Exception as e:
        error_msg = str(e)
        print(f"Error stopping betting for table {table['name']}: {error_msg}")
        log_api(f"Error executing bet_stop_post for {table['name']}: {error_msg}", "API >>>")
        # Record error to summary instead of sending Slack notification immediately
        try:
            record_table_api_error(
                environment=table["name"],
                api_type="betStop",
                table_name=table.get("game_code", "Unknown"),
                error_message=error_msg,
            )
        except Exception as summary_error:
            log_api(f"Error recording to summary: {summary_error}", "API >>>")
        return table["name"], False


def betStop_round_for_table(table, token):
    """Stop betting for a single table - synchronous wrapper"""
    return asyncio.run(_betStop_round_for_table_async(table, token))


async def _execute_broadcast_post_async(table, token, broadcast_type="roulette.relaunch"):
    """Execute broadcast_post to notify relaunch - async implementation"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"
        if table["name"] == "CIT":
            result = await retry_with_network_check(
                broadcast_post_v2, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "UAT":
            result = await retry_with_network_check(
                broadcast_post_v2_uat, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "PRD":
            result = await retry_with_network_check(
                broadcast_post_v2_prd, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "STG":
            result = await retry_with_network_check(
                broadcast_post_v2_stg, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "QAT":
            result = await retry_with_network_check(
                broadcast_post_v2_qat, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "CIT-5":
            result = await retry_with_network_check(
                broadcast_post_v2_cit5, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "CIT-6":
            result = await retry_with_network_check(
                broadcast_post_v2_cit6, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "CIT-7":
            result = await retry_with_network_check(
                broadcast_post_v2_cit7, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "PRD-5":
            result = await retry_with_network_check(
                broadcast_post_v2_prd5, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "PRD-6":
            result = await retry_with_network_check(
                broadcast_post_v2_prd6, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "PRD-7":
            result = await retry_with_network_check(
                broadcast_post_v2_prd7, post_url, token, broadcast_type, "players", 20
            )
        elif table["name"] == "GLC":
            result = await retry_with_network_check(
                broadcast_post_v2_glc, post_url, token, broadcast_type, "players", 20
            )
        else:
            return None

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

            # Send Slack notification for failed relaunch (only once, regardless of how many tables fail)
            # This will be called for each failed table, but the function itself handles deduplication
            try:
                send_relaunch_failed_to_slack()
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


def execute_broadcast_post(table, token, broadcast_type="roulette.relaunch"):
    """Execute broadcast_post to notify relaunch - synchronous wrapper"""
    global current_mode
    
    # Skip tableAPI calls in idle mode
    with mode_lock:
        if current_mode == "idle":
            print(f"[{get_timestamp()}] Skipping broadcast_post in idle mode")
            log_to_file("Skipping broadcast_post in idle mode", "Idle Mode >>>")
            return False
    
    return asyncio.run(_execute_broadcast_post_async(table, token, broadcast_type))


def main():
    """Main function for Speed Roulette Controller"""
    global terminate_program, ws_connected, ws_client

    # Check if system was recently rebooted and send sdp: up if needed
    print(f"[{get_timestamp()}] Checking system boot time...")
    log_to_file("Checking system boot time...", "MAIN >>>")
    check_recent_reboot_and_send_up()

    # Setup manual hot reload if available
    if MANUAL_HOT_RELOAD_AVAILABLE:
        setup_signal_handlers()
        start_manual_hot_reload()
        log_console("Manual hot reload enabled - use './reload' to reload", "MAIN >>>")
    else:
        log_console("Manual hot reload disabled", "MAIN >>>")

    # Initialize Roulette MQTT system (only if IDP is enabled)
    if ENABLE_IDP:
        log_mqtt("Starting Roulette MQTT system initialization...")
        asyncio.run(initialize_roulette_mqtt_system())
    else:
        log_mqtt("IDP functionality is DISABLED - skipping Roulette MQTT system initialization")
        log_console("IDP functionality is DISABLED", "MAIN >>>")
    
    # Start HTTP server to receive PATCH requests for service status updates
    # Use port 8085 to avoid conflict with Studio API on 8084
    http_server_thread = threading.Thread(target=start_http_server, args=(8085,))
    http_server_thread.daemon = True
    http_server_thread.start()
    print(f"[{get_timestamp()}] HTTP server thread started on port 8085")
    log_to_file("HTTP server thread started on port 8085", "MAIN >>>")
    
    # Start StudioAPI WebSocket connection to listen for "down" signals
    studio_api_ws_thread = threading.Thread(target=start_studio_api_websocket)
    studio_api_ws_thread.daemon = True
    studio_api_ws_thread.start()
    log_console("StudioAPI WebSocket listener started", "MAIN >>>")
    
    # Start TableAPI error summary scheduler (sends summary at 6 AM and 6 PM)
    try:
        start_summary_scheduler()
        log_console("TableAPI error summary scheduler started", "MAIN >>>")
    except Exception as e:
        log_console(f"Failed to start summary scheduler: {e}", "MAIN >>>")
    
    # Start service status monitor to check HTTP API and switch mode
    service_status_thread = threading.Thread(target=service_status_monitor)
    service_status_thread.daemon = True
    service_status_thread.start()
    log_console("Service status monitor started", "MAIN >>>")

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
        "relaunch_failed_sent": relaunch_failed_sent,
        "terminate_program": terminate_program,
        # Game state tracking for auto-recovery
        "u1_sent": u1_sent,
        "betStop_sent": betStop_sent,
        "finish_post_sent": finish_post_sent,
        "current_mode": current_mode,  # Include mode in global_vars for access in read_from_serial
        "enable_idp": ENABLE_IDP,  # Include IDP enable flag for access in read_from_serial
    }

    # Create a wrapper function for read_from_serial with all required parameters
    def read_from_serial_wrapper():

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
            send_wrong_ball_dir_error_to_slack=send_wrong_ball_dir_error_to_slack,  # Pass wrong ball direction Slack notification callback
            send_launch_fail_error_to_slack=send_launch_fail_error_to_slack,  # Pass launch fail Slack notification callback
        )

    # Create and start read thread
    read_thread = threading.Thread(target=read_from_serial_wrapper)
    read_thread.daemon = True
    read_thread.start()

    # Main thread handles writing and monitors termination flag
    try:
        while not global_vars.get("terminate_program", False):
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
        if global_vars.get("terminate_program", False):
            print(f"\n[{get_timestamp()}] Program terminating due to *X;6 message detection")
            log_to_file("Program terminating due to *X;6 message detection", "Terminate >>>")
            
            # Gracefully close WebSocket connection
            if ws_connected and ws_client:
                try:
                    print(f"[{get_timestamp()}] Closing WebSocket connection...")
                    log_to_file("Closing WebSocket connection...", "WebSocket >>>")
                    asyncio.run(ws_client.close())
                    ws_connected = False
                    print(f"[{get_timestamp()}] WebSocket connection closed successfully")
                    log_to_file("WebSocket connection closed successfully", "WebSocket >>>")
                except Exception as e:
                    print(f"[{get_timestamp()}] Error closing WebSocket connection: {e}")
                    log_to_file(f"Error closing WebSocket connection: {e}", "WebSocket >>>")
            
            # Gracefully close serial connection
            if ser is not None:
                try:
                    print(f"[{get_timestamp()}] Closing serial connection...")
                    log_to_file("Closing serial connection...", "Serial >>>")
                    ser.close()
                    print(f"[{get_timestamp()}] Serial connection closed successfully")
                    log_to_file("Serial connection closed successfully", "Serial >>>")
                except Exception as e:
                    print(f"[{get_timestamp()}] Error closing serial connection: {e}")
                    log_to_file(f"Error closing serial connection: {e}", "Serial >>>")
            
            print(f"[{get_timestamp()}] Program terminated gracefully")
            log_to_file("Program terminated gracefully", "Terminate >>>")
            
    except KeyboardInterrupt:
        print(f"\n[{get_timestamp()}] Program ended by user")
        log_to_file("Program ended by user", "Terminate >>>")
    finally:
        # Stop manual hot reload manager
        if MANUAL_HOT_RELOAD_AVAILABLE:
            stop_manual_hot_reload()
            
        # Cleanup Roulette MQTT system (only if IDP is enabled)
        if ENABLE_IDP:
            try:
                print(f"[{get_timestamp()}] Cleaning up Roulette MQTT system...")
                asyncio.run(cleanup_roulette_mqtt_system())
            except Exception as e:
                print(f"[{get_timestamp()}] Error cleaning up Roulette MQTT system: {e}")
        
        # Ensure connections are closed even if not terminated gracefully
        if ser is not None:
            try:
                ser.close()
                print(f"[{get_timestamp()}] Serial connection closed in finally block")
            except:
                pass
        
        if ws_connected and ws_client:
            try:
                asyncio.run(ws_client.close())
                print(f"[{get_timestamp()}] WebSocket connection closed in finally block")
            except:
                pass
        
        print(f"[{get_timestamp()}] Program terminated")


if __name__ == "__main__":
    main()
