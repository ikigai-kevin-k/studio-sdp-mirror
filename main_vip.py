import serial
import threading
import time
from datetime import datetime
import sys
import json
import asyncio
import websockets
import os
from concurrent.futures import ThreadPoolExecutor
from utils import create_serial_connection

# Import for reading packaged resources
try:
    from importlib.resources import files, as_file
    HAVE_IMPORTLIB_RESOURCES = True
except ImportError:
    try:
        import pkg_resources
        HAVE_IMPORTLIB_RESOURCES = False
    except ImportError:
        HAVE_IMPORTLIB_RESOURCES = None

from table_api.vr.api_v2_vr import (
    start_post_v2,
    deal_post_v2,
    finish_post_v2,
    broadcast_post_v2,
    bet_stop_post,
)
from table_api.vr.api_v2_uat_vr import (
    start_post_v2_uat,
    deal_post_v2_uat,
    finish_post_v2_uat,
    broadcast_post_v2_uat,
    bet_stop_post_uat,
)
from table_api.vr.api_v2_prd_vr import (
    start_post_v2_prd,
    deal_post_v2_prd,
    finish_post_v2_prd,
    broadcast_post_v2_prd,
    bet_stop_post_prd,
)
from table_api.vr.api_v2_prd_vr_3 import (
    start_post_v2_prd as start_post_v2_prd3,
    deal_post_v2_prd as deal_post_v2_prd3,
    finish_post_v2_prd as finish_post_v2_prd3,
    broadcast_post_v2_prd as broadcast_post_v2_prd3,
    bet_stop_post_prd as bet_stop_post_prd3,
)
from table_api.vr.api_v2_prd_vr_4 import (
    start_post_v2_prd as start_post_v2_prd4,
    deal_post_v2_prd as deal_post_v2_prd4,
    finish_post_v2_prd as finish_post_v2_prd4,
    broadcast_post_v2_prd as broadcast_post_v2_prd4,
    bet_stop_post_prd as bet_stop_post_prd4,
)
from table_api.vr.api_v2_stg_vr import (
    start_post_v2_stg,
    deal_post_v2_stg,
    finish_post_v2_stg,
    broadcast_post_v2_stg,
    bet_stop_post_stg,
)
from table_api.vr.api_v2_qat_vr import (
    start_post_v2_qat,
    deal_post_v2_qat,
    finish_post_v2_qat,
    broadcast_post_v2_qat,
    bet_stop_post_qat,
)
from table_api.vr.api_v2_glc_vr import (
    start_post_v2_glc,
    deal_post_v2_glc,
    finish_post_v2_glc,
    broadcast_post_v2_glc,
    bet_stop_post_glc,
)

# Import Slack notification module
from slack import send_error_to_slack

# Import WebSocket error signal module
from studio_api.ws_err_sig import send_roulette_sensor_stuck_error

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not installed, using system environment variables")
    print("Install with: pip install python-dotenv")

# Serial connection will be initialized in main()
ser = None


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def log_to_file(message, direction):
    with open("self-test-2api.log", "a", encoding="utf-8") as f:
        timestamp = get_timestamp()
        f.write(f"[{timestamp}] {direction} {message}\n")


# Load table configuration
def load_table_config(config_file="conf/table-config-vip-roulette-v2.json"):
    """Load table configuration from JSON file
    
    This function supports loading from:
    1. Current working directory (development mode)
    2. Packaged resources in .pyz file (production mode)
    """
    # Try to load from current working directory first
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                print(f"Loaded table config from: {config_file}")
                return json.load(f)
        except Exception as e:
            print(f"Error loading table config from {config_file}: {e}")
    
    # If not found, try to load from packaged resources
    try:
        # Extract filename from path
        config_filename = os.path.basename(config_file)
        
        if HAVE_IMPORTLIB_RESOURCES:
            # Use importlib.resources (Python 3.9+)
            try:
                conf_files = files('conf')
                config_resource = conf_files / config_filename
                with as_file(config_resource) as config_path:
                    with open(config_path, 'r') as f:
                        print(f"Loaded table config from packaged resources: {config_filename}")
                        return json.load(f)
            except Exception as e:
                print(f"Failed to load from importlib.resources: {e}")
        
        elif HAVE_IMPORTLIB_RESOURCES is False:
            # Use pkg_resources (fallback)
            try:
                config_data = pkg_resources.resource_string('conf', config_filename)
                print(f"Loaded table config from pkg_resources: {config_filename}")
                return json.loads(config_data.decode('utf-8'))
            except Exception as e:
                print(f"Failed to load from pkg_resources: {e}")
        
        # Last resort: try to find conf directory in site-packages
        try:
            import site
            for site_dir in site.getsitepackages():
                conf_path = os.path.join(site_dir, 'conf', config_filename)
                if os.path.exists(conf_path):
                    with open(conf_path, 'r') as f:
                        print(f"Loaded table config from site-packages: {conf_path}")
                        return json.load(f)
        except Exception as e:
            print(f"Failed to load from site-packages: {e}")
    
    except Exception as e:
        print(f"Error loading table configuration: {e}")
    
    # If all methods fail, raise error
    raise FileNotFoundError(f"Could not load table configuration file: {config_file}")


# Add LOS API related variables
tables = None  # Will be loaded in main()
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

# Add variables for *P 1 monitoring
p1_sent = False  # Flag to track if *P 1 has been sent
x1_received = False  # Flag to track if *X;1 has been received after *P 1
x1_to_x6_timer = None  # Timer to track 15-second window
x1_received_time = 0  # Time when *X;1 was first received


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
        print(f"[{get_timestamp()}] Failed to connect to stream recorder: {e}")
        log_to_file(
            f"Failed to connect to stream recorder: {e}", "WebSocket >>>"
        )
        ws_connected = False
        return False


# Send WebSocket message function
async def send_to_recorder(message):
    """Send message to stream recorder"""
    global ws_connected
    if not ws_connected or not ws_client:
        print(
            f"[{get_timestamp()}] Not connected to stream recorder, attempting to reconnect..."
        )
        log_to_file(
            "Not connected to stream recorder, attempting to reconnect...",
            "WebSocket >>>",
        )
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
    """Send sensor error notification to Slack for VIP Roulette table"""
    global sensor_error_sent

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
            table_name="ARO-002-1 (vip - main)",
            error_code="SENSOR_STUCK",
            mention_user="Mark Bochkov",  # Mention Mark Bochkov for sensor errors
            channel="#studio-rnd",  # Send sensor errors to studio-rnd channel
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


# Function to send WebSocket error signal
def send_websocket_error_signal():
    """Send WebSocket error signal for VIP Roulette table"""
    global ws_connected, ws_client
    try:
        print(f"[{get_timestamp()}] Sending WebSocket error signal...")
        log_to_file("Sending WebSocket error signal...", "WebSocket >>>")

        # Run the async function and wait for completion
        def send_ws_error():
            try:
                # Send error signal specifically for ARO-002 VIP Roulette table
                # Use ARO-002-1 for primary device
                result = asyncio.run(send_roulette_sensor_stuck_error(
                    table_id="ARO-002", 
                    device_id="ARO-002-1"
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


def read_from_serial():
    global x2_count, x5_count, last_x2_time, last_x5_time, start_post_sent, deal_post_sent, start_time, deal_post_time, finish_post_time, isLaunch
    global p1_sent, x1_received, x1_to_x6_timer, x1_received_time
    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode("utf-8").strip()
            print("Receive >>>", data)
            log_to_file(data, "Receive >>>")

            # Handle *P 0 command - reset monitoring state
            if "*P 0" in data:
                if p1_sent and x1_received:
                    print(f"[{get_timestamp()}] Received *P 0, resetting P1 monitoring state")
                    log_to_file("Received *P 0, resetting P1 monitoring state", "Receive >>>")
                p1_sent = False
                x1_received = False
                x1_to_x6_timer = None
                x1_received_time = 0

            # Handle *X;1 messages after *P 1
            if "*X;1" in data and p1_sent and not x1_received:
                x1_received = True
                x1_received_time = time.time()
                print(f"[{get_timestamp()}] Received *X;1 after *P 1, starting 15-second monitoring...")
                log_to_file("Received *X;1 after *P 1, starting 15-second monitoring", "Receive >>>")
                
                # Start 15-second timer to monitor for *X;6
                def check_x6_timeout():
                    time.sleep(15)
                    if x1_received and p1_sent:  # Check if still in monitoring state
                        print(f"[{get_timestamp()}] 15-second timeout reached, *X;6 not received - monitoring continues")
                        log_to_file("15-second timeout reached, *X;6 not received - monitoring continues", "Receive >>>")
                
                x1_to_x6_timer = threading.Thread(target=check_x6_timeout)
                x1_to_x6_timer.daemon = True
                x1_to_x6_timer.start()

            # Handle *X;6 sensor error messages
            if "*X;6" in data:
                try:
                    parts = data.split(";")
                    if (
                        len(parts) >= 5
                    ):  # Ensure there are enough parts to get warning_flag
                        warning_flag = parts[4]
                        print(
                            f"[{get_timestamp()}] Detected *X;6 message with warning_flag: {warning_flag}"
                        )
                        log_to_file(
                            f"Detected *X;6 message with warning_flag: {warning_flag}",
                            "Receive >>>",
                        )

                        # Check if this is *X;6 after *X;1 within 15 seconds (P1 monitoring case) - PRIORITY CHECK
                        current_time = time.time()
                        if (p1_sent and x1_received and 
                            current_time - x1_received_time <= 15):
                            print(
                                f"[{get_timestamp()}] *X;6 detected within 15 seconds after *X;1 (P1 monitoring) - sending WebSocket error signal"
                            )
                            log_to_file(
                                "*X;6 detected within 15 seconds after *X;1 (P1 monitoring) - sending WebSocket error signal",
                                "Receive >>>",
                            )
                            
                            # Send WebSocket error signal
                            send_websocket_error_signal()
                            
                            # Reset monitoring flags
                            x1_received = False
                            x1_to_x6_timer = None
                            
                            continue  # Skip normal *X;6 error handling

                        # Check if this is a startup condition (warning_flag=0 and recently started)
                        startup_threshold = 30  # 30 seconds after startup
                        
                        # Initialize startup time if not exists
                        if not hasattr(read_from_serial, "startup_time"):
                            read_from_serial.startup_time = current_time
                        
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

                        # Send sensor error notification to Slack
                        send_sensor_error_to_slack()
                        
                        # Send WebSocket error signal
                        print(f"[{get_timestamp()}] Sending WebSocket error signal...")
                        log_to_file("Sending WebSocket error signal...", "WebSocket >>>")
                        send_websocket_error_signal()
                        
                        # Set termination flag to stop the program
                        global terminate_program
                        terminate_program = True
                        print(f"[{get_timestamp()}] Program will terminate due to sensor error")
                        log_to_file("Program will terminate due to sensor error", "Terminate >>>")
                except Exception as e:
                    print(
                        f"[{get_timestamp()}] Error parsing *X;6 message: {e}"
                    )
                    log_to_file(
                        f"Error parsing *X;6 message: {e}", "Error >>>"
                    )

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

                                time.sleep(0.5)
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

                        start_post_sent = True
                        deal_post_sent = False

                        # Start bet stop countdown for each table (non-blocking)
                        for table, round_id, bet_period in round_ids:
                            if bet_period and bet_period > 0:
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
        elif table["name"] == "PRD-3":
            result = finish_post_v2_prd3(post_url, token)
        elif table["name"] == "PRD-4":
            result = finish_post_v2_prd4(post_url, token)
        elif table["name"] == "STG":
            result = finish_post_v2_stg(post_url, token)
        elif table["name"] == "QAT":
            result = finish_post_v2_qat(post_url, token)
        elif table["name"] == "GLC":
            result = finish_post_v2_glc(post_url, token)
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
        elif table["name"] == "PRD-3":
            round_id, betPeriod = start_post_v2_prd3(post_url, token)
        elif table["name"] == "PRD-4":
            round_id, betPeriod = start_post_v2_prd4(post_url, token)
        elif table["name"] == "STG":
            round_id, betPeriod = start_post_v2_stg(post_url, token)
        elif table["name"] == "QAT":
            round_id, betPeriod = start_post_v2_qat(post_url, token)
        elif table["name"] == "GLC":
            round_id, betPeriod = start_post_v2_glc(post_url, token)
        else:
            round_id, betPeriod = start_post_v2(post_url, token)

        if round_id != -1:
            table["round_id"] = round_id
            print(
                f"Successfully called start_post for {table['name']}, round_id: {round_id}, betPeriod: {betPeriod}"
            )
            return table, round_id, betPeriod
        else:
            print(f"Failed to call start_post for {table['name']}")
            return None, -1, 0
    except Exception as e:
        print(f"Error executing start_post for {table['name']}: {e}")
        return None, -1, 0


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
        elif table["name"] == "PRD-3":
            result = deal_post_v2_prd3(
                post_url, token, table["round_id"], str(win_num)
            )
        elif table["name"] == "PRD-4":
            result = deal_post_v2_prd4(
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
        elif table["name"] == "GLC":
            result = deal_post_v2_glc(
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


def betStop_round_for_table(table, token):
    """Stop betting for a single table - helper function for thread pool execution"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"

        if table["name"] == "CIT":
            result = bet_stop_post(post_url, token)
        elif table["name"] == "UAT":
            result = bet_stop_post_uat(post_url, token)
        elif table["name"] == "PRD":
            result = bet_stop_post_prd(post_url, token)
        elif table["name"] == "PRD-3":
            result = bet_stop_post_prd3(post_url, token)
        elif table["name"] == "PRD-4":
            result = bet_stop_post_prd4(post_url, token)
        elif table["name"] == "STG":
            result = bet_stop_post_stg(post_url, token)
        elif table["name"] == "QAT":
            result = bet_stop_post_qat(post_url, token)
        elif table["name"] == "GLC":
            result = bet_stop_post_glc(post_url, token)
        else:
            result = False

        return table["name"], result

    except Exception as e:
        error_msg = str(e)
        print(f"Error stopping betting for table {table['name']}: {error_msg}")
        return table["name"], False


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
        elif table["name"] == "PRD-3":
            result = broadcast_post_v2_prd3(
                post_url, token, "roulette.relaunch", "players", 20
            )  # , None)
        elif table["name"] == "PRD-4":
            result = broadcast_post_v2_prd4(
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
        elif table["name"] == "GLC":
            result = broadcast_post_v2_glc(
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
        # Wait for the bet period duration
        time.sleep(bet_period)

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


def main():
    """Main function for VIP Roulette Controller"""
    global terminate_program, ws_connected, ws_client, p1_sent, tables, ser
    
    # Load table configuration at startup
    try:
        tables = load_table_config()
        print(f"[{get_timestamp()}] Table configuration loaded successfully")
    except Exception as e:
        print(f"[{get_timestamp()}] Error loading table configuration: {e}")
        print("Program cannot continue without table configuration")
        sys.exit(1)
    
    # Initialize serial connection
    try:
        ser = create_serial_connection(
            port="/dev/ttyUSB0",
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1,
        )
        if ser is None:
            print(f"[{get_timestamp()}] Warning: Serial connection not available")
        else:
            print(f"[{get_timestamp()}] Serial connection established successfully")
    except Exception as e:
        print(f"[{get_timestamp()}] Error creating serial connection: {e}")
        print("Program cannot continue without serial connection")
        sys.exit(1)

    # Send *P 1 command at program startup
    if ser is not None:
        print(f"[{get_timestamp()}] Sending *P 1 command at startup...")
        log_to_file("*P 1", "Send <<<")
        ser.write(("*P 1\r\n").encode())
        print(f"[{get_timestamp()}] *P 1 command sent successfully")
    else:
        print(f"[{get_timestamp()}] Cannot send *P 1 command: Serial connection not available")
    
    # Set flag to indicate *P 1 has been sent
    p1_sent = True

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

    # Create a wrapper function for read_from_serial with all required parameters
    def read_from_serial_wrapper():
        read_from_serial()

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
