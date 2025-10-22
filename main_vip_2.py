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
# Lazy environment-specific imports are performed inside functions based on table['name']
from concurrent.futures import ThreadPoolExecutor

# Import Studio Alert Manager
sys.path.append("studio-alert-manager")
from studio_alert_manager.alert_manager import AlertManager, AlertLevel

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


# Add Alert Manager instance
alert_manager = None

# Add LOS API related variables
tables = load_table_config()
x2_count = 0
x3_count = 0
x4_count = 0
x5_count = 0
start_post_sent = False
deal_post_sent = False
finish_post_sent = False
terminate_program = False  # Flag to terminate program when *X;6 sensor error is detected
sensor_error_sent_to_slack = False  # Flag to prevent duplicate Slack notifications

# Global variables for tracking game state
current_round_id = None
current_bet_period = 0
ball_launch_time = None
start_time = None
finish_to_start_time = 0.0
start_to_launch_time = 0.0
launch_to_deal_time = 0.0
deal_to_finish_time = 0.0
finish_post_time = None
deal_post_time = None
start_post_time = None

# Global variables for tracking time intervals
time_intervals = {
    "finish_to_start": [],
    "start_to_launch": [],
    "launch_to_deal": [],
    "deal_to_finish": [],
}

# Function to send sensor error notification using Studio Alert Manager
def send_sensor_error_alert():
    """Send sensor error notification using Studio Alert Manager"""
    global sensor_error_sent_to_slack
    
    # Check if we already sent this error to avoid spam
    if sensor_error_sent_to_slack:
        log_to_file(
            f"[{get_timestamp()}] Sensor error already sent to Slack, skipping...",
            "Alert >>>"
        )
        return
    
    try:
        if alert_manager:
            success = alert_manager.send_error(
                error_message="SENSOR ERROR - Detected warning_flag=4 in *X;6 message",
                environment="CIT-2",
                table_name="Studio-Roulette-Test",
                error_code="SENSOR_STUCK"
            )
        else:
            # Fallback to direct Slack notification if alert manager not available
            sys.path.append("slack")
            from slack import send_error_to_slack
            success = send_error_to_slack(
                error_message="SENSOR ERROR - Detected warning_flag=4 in *X;6 message",
                environment="CIT-2",
                table_name="Studio-Roulette-Test",
                error_code="SENSOR_STUCK"
            )
        
        if success:
            sensor_error_sent_to_slack = True
            log_to_file(
                f"[{get_timestamp()}] Sensor error notification sent successfully",
                "Alert >>>"
            )
            print(
                "Sensor error notification sent successfully",
                "Alert >>>",
            )
        else:
            log_to_file(
                f"[{get_timestamp()}] Failed to send sensor error notification",
                "Alert >>>"
            )
            print(
                "Failed to send sensor error notification",
                "Alert >>>",
            )
    except Exception as e:
        log_to_file(
            f"Error sending sensor error notification: {e}", "Alert >>>"
        )
        print(f"Error sending sensor error notification: {e}")


def check_time_intervals():
    """Check if time intervals exceed limits and log warnings"""
    try:
        # Check launch_to_deal_time
        if launch_to_deal_time > 20:
            warning_message = f"launch_to_deal_time ({launch_to_deal_time:.2f}s) > 20s (Round ID: {current_round_id or 'unknown'})"
            print(f"[{get_timestamp()}] Assertion Error: {warning_message}")
            print("Time interval exceeds limit, but program continues to run")
            log_to_file(warning_message, "WARNING >>>")
            
            # Send WebSocket error signal
            try:
                sys.path.append("studio_api")
                from studio_api.ws_err_sig import send_roulette_sensor_stuck_error
                result = asyncio.run(send_roulette_sensor_stuck_error())
            except Exception as ws_error:
                print(f"Failed to send WebSocket error signal: {ws_error}")
                result = False
                
    except Exception as e:
        log_to_file(f"Error checking time intervals: {e}", "ERROR >>>")
        print(f"Error checking time intervals: {e}")


async def retry_with_network_check(func, *args, max_retries=5, retry_delay=5):
    """
    Retry function with network connectivity check
    """
    for attempt in range(max_retries):
        try:
            # Check network connectivity before making the call
            if not networkChecker.check_network():
                print(f"Network check failed on attempt {attempt + 1}, retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                continue
            
            # Make the API call
            result = await func(*args)
            return result
            
        except ConnectionError as e:
            print(f"Connection error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"Max retries reached, giving up")
                raise e
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"Max retries reached, giving up")
                raise e
    
    return None


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

        return result

    except Exception as e:
        print(f"Error executing broadcast_post for {table['name']}: {e}")
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
            )
        elif table["name"] == "STG-2":
            from table_api.vr import stg_vr_2
            result = stg_vr_2.broadcast_post_v2(
                post_url, token, "roulette.relaunch", "players", 20
            )
        elif table["name"] == "QAT-2":
            from table_api.vr import qat_vr_2
            result = qat_vr_2.broadcast_post_v2(
                post_url, token, "roulette.relaunch", "players", 20
            )
        else:  # CIT-2
            from table_api.vr import cit_vr_2
            result = cit_vr_2.broadcast_post_v2(
                post_url, token, "roulette.relaunch", "players", 20
            )

        return result

    except Exception as e:
        print(f"Error executing broadcast_post for {table['name']}: {e}")
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
    global terminate_program

    # Initialize Alert Manager
    try:
        # Load configuration from alert_config.yaml
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
        print(f"[{get_timestamp()}] Alert Manager initialized successfully")
    except Exception as e:
        print(f"[{get_timestamp()}] Failed to initialize Alert Manager: {e}")
        alert_manager = None

    # Start serial read thread
    print(f"[{get_timestamp()}] Serial read thread started, startup time recorded")
    
    # Call read_from_serial with global variables and callback functions
    read_from_serial(
        ser=ser,
        tables=tables,
        token=tables[0]["access_token"] if tables else None,
        global_vars={
            "x2_count": x2_count,
            "x3_count": x3_count,
            "x4_count": x4_count,
            "x5_count": x5_count,
            "start_post_sent": start_post_sent,
            "deal_post_sent": deal_post_sent,
            "finish_post_sent": finish_post_sent,
            "terminate_program": terminate_program,
            "sensor_error_sent_to_slack": sensor_error_sent_to_slack,
            "current_round_id": current_round_id,
            "current_bet_period": current_bet_period,
            "ball_launch_time": ball_launch_time,
            "start_time": start_time,
            "finish_to_start_time": finish_to_start_time,
            "start_to_launch_time": start_to_launch_time,
            "launch_to_deal_time": launch_to_deal_time,
            "deal_to_finish_time": deal_to_finish_time,
            "finish_post_time": finish_post_time,
            "deal_post_time": deal_post_time,
            "start_post_time": start_post_time,
            "time_intervals": time_intervals,
        },
        callback_functions={
            "execute_start_post": execute_start_post,
            "execute_deal_post": execute_deal_post,
            "execute_finish_post": execute_finish_post,
            "execute_broadcast_post": execute_broadcast_post,
            "betStop_round_for_table": betStop_round_for_table,
            "check_time_intervals": check_time_intervals,
            "send_sensor_error_to_slack": send_sensor_error_alert,
        },
        get_timestamp=get_timestamp,
        log_to_file=log_to_file,
    )


if __name__ == "__main__":
    main()