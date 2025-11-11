import asyncio
import logging
import json
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys


import argparse
import os
import logging.handlers

import websockets
import urllib3
from requests.exceptions import ConnectionError

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

from controller import GameType, GameConfig
from gameStateController import create_game_state_controller
from mqtt.deviceController import IDPController, ShakerController
from mqttController import MQTTController
from table_api.sb.api_v2_sb import (
    start_post_v2,
    deal_post_v2,
    finish_post_v2,
    pause_post_v2,
    get_roundID_v2,
    broadcast_post_v2,
    bet_stop_post,
)
from table_api.sb.api_v2_uat_sb import (
    start_post_v2_uat,
    deal_post_v2_uat,
    finish_post_v2_uat,
    pause_post_v2_uat,
    get_roundID_v2_uat,
    broadcast_post_v2_uat,
    bet_stop_post_uat,
    get_sdp_config_v2_uat,
)
from table_api.sb.api_v2_prd_sb import (
    start_post_v2_prd,
    deal_post_v2_prd,
    finish_post_v2_prd,
    pause_post_v2_prd,
    get_roundID_v2_prd,
    broadcast_post_v2_prd,
    bet_stop_post_prd,
)
from table_api.sb.api_v2_stg_sb import (
    start_post_v2_stg,
    deal_post_v2_stg,
    finish_post_v2_stg,
    pause_post_v2_stg,
    get_roundID_v2_stg,
    broadcast_post_v2_stg,
    bet_stop_post_stg,
)
from table_api.sb.api_v2_qat_sb import (
    start_post_v2_qat,
    deal_post_v2_qat,
    finish_post_v2_qat,
    pause_post_v2_qat,
    get_roundID_v2_qat,
    broadcast_post_v2_qat,
    bet_stop_post_qat,
)
from table_api.sb.api_v2_glc_sb import (
    start_post_v2_glc,
    deal_post_v2_glc,
    finish_post_v2_glc,
    pause_post_v2_glc,
    get_roundID_v2_glc,
    broadcast_post_v2_glc,
    bet_stop_post_glc,
)
from networkChecker import networkChecker
from datetime import datetime
from slack import send_error_to_slack

# Global error notification state tracker to prevent duplicate Slack messages
# Key: environment_name, Value: last_error_time
error_notification_state = {}


def should_send_error_notification(
    environment_name: str, cooldown_minutes: int = 30
) -> bool:
    """
    Check if error notification should be sent for the given environment.
    Prevents duplicate notifications within the cooldown period.

    Args:
        environment_name: Name of the environment (PRD/STG)
        cooldown_minutes: Minutes to wait before allowing another notification

    Returns:
        bool: True if notification should be sent, False otherwise
    """
    current_time = time.time()

    if environment_name not in error_notification_state:
        # First time error for this environment, allow notification
        error_notification_state[environment_name] = current_time
        return True

    last_error_time = error_notification_state[environment_name]
    time_since_last_error = current_time - last_error_time

    # Allow notification if cooldown period has passed
    if time_since_last_error >= (cooldown_minutes * 60):
        error_notification_state[environment_name] = current_time
        return True

    return False


def reset_error_notification_state(environment_name: str):
    """
    Reset error notification state for the given environment.
    Call this when the environment recovers successfully.

    Args:
        environment_name: Name of the environment to reset
    """
    if environment_name in error_notification_state:
        del error_notification_state[environment_name]
        logger.info(f"Reset error notification state for {environment_name}")


# Import the update function from ws_sb_update.py
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "studio_api"))
from ws_sb_update import update_sicbo_game_status
from table_api_error_signal import (
    send_table_api_error_signal,
    reset_error_signal_count,
    reset_all_error_signal_counts,
)

# import sentry_sdk

# sentry_sdk.init(
#     dsn="https://63a51b0fa2f4c419adaf46fafea61e89@o4509115379679232.ingest.us.sentry.io/4509643182440448",
#     # Add data like request headers and IP for users,
#     # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
#     send_default_pii=True,
# )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DailyFileHandler(logging.FileHandler):
    """
    Custom file handler that creates a new log file each day.
    File format: sbo_{yyyy-mm-dd}.log
    """
    
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        # Initialize current_date before calling super().__init__()
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        log_file = self._get_log_file_path()
        super().__init__(log_file, encoding="utf-8")
    
    def _get_log_file_path(self):
        """Get log file path for current date"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, f'sbo_{current_date}.log')
        return log_file
    
    def _should_rotate(self):
        """Check if we should rotate to a new file (new day)"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        return current_date != self.current_date
    
    def emit(self, record):
        """Emit a record, rotating file if needed"""
        if self._should_rotate():
            # Close current file
            if self.stream:
                self.stream.close()
                self.stream = None
            
            # Open new file for new day
            self.baseFilename = self._get_log_file_path()
            self.current_date = datetime.now().strftime("%Y-%m-%d")
            self.stream = self._open()
        
        super().emit(record)


def setup_logging(enable_logging: bool, log_dir: str):
    """Setup logging configuration"""
    if enable_logging:
        # ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        # set up file handler with daily rotation
        # File format: sbo_{yyyy-mm-dd}.log
        file_handler = DailyFileHandler(log_dir)

        # set up formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        # set up root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        # keep console output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        root_logger.setLevel(logging.INFO)

        logging.info(f"Logging to file: {file_handler.baseFilename}")


def load_table_config(config_file="conf/table-config-sicbo-v2.json"):
    """Load table configuration from JSON file
    
    This function supports loading from:
    1. Current working directory (development mode)
    2. Packaged resources in .pyz file (production mode)
    """
    # Try to load from current working directory first
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                logger.info(f"Loaded table config from: {config_file}")
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading table config from {config_file}: {e}")
    
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
                        logger.info(f"Loaded table config from packaged resources: {config_filename}")
                        return json.load(f)
            except Exception as e:
                logger.debug(f"Failed to load from importlib.resources: {e}")
        
        elif HAVE_IMPORTLIB_RESOURCES is False:
            # Use pkg_resources (fallback)
            try:
                config_data = pkg_resources.resource_string('conf', config_filename)
                logger.info(f"Loaded table config from pkg_resources: {config_filename}")
                return json.loads(config_data.decode('utf-8'))
            except Exception as e:
                logger.debug(f"Failed to load from pkg_resources: {e}")
        
        # Last resort: try to find conf directory in site-packages
        for path in sys.path:
            potential_config = os.path.join(path, config_file)
            if os.path.exists(potential_config):
                with open(potential_config, 'r') as f:
                    logger.info(f"Loaded table config from sys.path: {potential_config}")
                    return json.load(f)
        
        logger.error(f"Could not find config file: {config_file} in any location")
        return []
        
    except Exception as e:
        logger.error(f"Error loading table config from packaged resources: {e}")
        return []


async def start_round_for_table(table, token):
    """Start round for a single table - helper function for thread pool execution"""
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
            try:
                round_id, bet_period = await retry_with_network_check(
                    start_post_v2_prd,
                    post_url,
                    token,
                    max_retries=5,
                    error_type="NO_START",
                    table_name="PRD",
                )
                if round_id == -1:
                    # Send error signal for PRD start post failure (returned -1)
                    # This is the first failure, send warn signal
                    try:
                        await send_table_api_error_signal(
                            error_type="NO_START",
                            retry_count=0,
                            max_retries=5,
                            table_id="SBO-001",
                            device_id="ASB-001-1",
                        )
                    except Exception as signal_error:
                        logger.error(
                            f"Failed to send NO_START error signal: {signal_error}"
                        )
                    
                    # Send Slack error notification for PRD start post failure
                    # Only send if we haven't sent one recently
                    if should_send_error_notification("PRD"):
                        send_error_to_slack(
                            error_message="PRD Start Post Failed",
                            environment="Sicbo - TableAPI Error",
                            table_name=table["name"],
                            error_code="START_POST_FAILED",
                        )
                        logger.warning(
                            "PRD Start Post Failed - Slack notification sent"
                        )
                    else:
                        logger.info(
                            "PRD Start Post Failed - Skipping duplicate "
                            "Slack notification"
                        )
            except Exception as e:
                logger.error(f"PRD start_post_v2_prd failed: {e}")
                # Error signal already sent in retry_with_network_check if max retries reached
                # Send Slack error notification for PRD start post failure
                # Only send if we haven't sent one recently
                if should_send_error_notification("PRD"):
                    send_error_to_slack(
                        error_message="PRD Start Post Failed",
                        environment="Sicbo - TableAPI Error",
                        table_name=table["name"],
                        error_code="START_POST_FAILED",
                    )
                    logger.warning(
                        "PRD Start Post Failed - Slack notification sent"
                    )
                else:
                    logger.info(
                        "PRD Start Post Failed - Skipping duplicate Slack notification"
                    )
                round_id, bet_period = -1, None
        elif table["name"] == "STG":
            try:
                round_id, bet_period = await retry_with_network_check(
                    start_post_v2_stg, post_url, token
                )
                if round_id == -1:
                    # Send Slack error notification for STG start post failure
                    # Only send if we haven't sent one recently
                    if should_send_error_notification("STG"):
                        send_error_to_slack(
                            error_message="STG Start Post Failed",
                            environment="Sicbo - TableAPI Error",
                            table_name=table["name"],
                            error_code="START_POST_FAILED",
                        )
                        logger.warning(
                            "STG Start Post Failed - Slack notification sent"
                        )
                    else:
                        logger.info(
                            "STG Start Post Failed - Skipping duplicate Slack notification"
                        )
            except Exception as e:
                logger.error(f"STG start_post_v2_stg failed: {e}")
                # Send Slack error notification for STG start post failure
                # Only send if we haven't sent one recently
                if should_send_error_notification("STG"):
                    send_error_to_slack(
                        error_message="STG Start Post Failed",
                        environment="Sicbo - TableAPI Error",
                        table_name=table["name"],
                        error_code="START_POST_FAILED",
                    )
                    logger.warning(
                        "STG Start Post Failed - Slack notification sent"
                    )
                else:
                    logger.info(
                        "STG Start Post Failed - Skipping duplicate Slack notification"
                    )
                round_id, bet_period = -1, None
        elif table["name"] == "QAT":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_qat, post_url, token
            )
        elif table["name"] == "GLC":
            round_id, bet_period = await retry_with_network_check(
                start_post_v2_glc, post_url, token
            )
        else:
            return None, None

        if round_id != -1:
            return table, round_id, bet_period
        else:
            return None, None

    except Exception as e:
        logger.error(f"Error starting round for table {table['name']}: {e}")
        return None, None


async def deal_round_for_table(table, token, round_id, dice_result):
    """Deal round for a single table - helper function for thread pool execution"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"

        if table["name"] == "CIT":
            await retry_with_network_check(
                deal_post_v2, post_url, token, round_id, dice_result
            )
        elif table["name"] == "UAT":
            await retry_with_network_check(
                deal_post_v2_uat, post_url, token, round_id, dice_result
            )
        elif table["name"] == "PRD":
            try:
                await retry_with_network_check(
                    deal_post_v2_prd,
                    post_url,
                    token,
                    round_id,
                    dice_result,
                    max_retries=5,
                    error_type="NO_DEAL",
                    table_name="PRD",
                )
            except Exception as e:
                logger.error(
                    f"PRD deal_post_v2_prd failed after retries: {e}"
                )
                # Error signal already sent in retry_with_network_check
                raise
        elif table["name"] == "STG":
            await retry_with_network_check(
                deal_post_v2_stg, post_url, token, round_id, dice_result
            )
        elif table["name"] == "QAT":
            await retry_with_network_check(
                deal_post_v2_qat, post_url, token, round_id, dice_result
            )
        elif table["name"] == "GLC":
            await retry_with_network_check(
                deal_post_v2_glc, post_url, token, round_id, dice_result
            )

        return table["name"], True

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Error dealing round for table {table['name']}: {error_msg}"
        )

        # Check if this is a JSON parsing error for PRD or STG
        if "Expecting value: line 1 column 1 (char 0)" in error_msg and table[
            "name"
        ] in ["PRD", "STG"]:
            # Log detailed information for debugging
            logger.error(f"JSON parsing error detected for {table['name']}")
            logger.error(f"Table: {table['name']}")
            logger.error(f"Round ID: {round_id}")
            logger.error(f"Dice Result: {dice_result}")
            logger.error(f"Post URL: {post_url}")
            logger.error(f"Token: ***")
            logger.error(f"Timestamp: {int(time.time())}")

            # Log the expected curl command
            timecode = str(int(time.time() * 1000))
            curl_command = (
                f"curl -X POST '{post_url}/deal' "
                f"-H 'accept: application/json' "
                f"-H 'Bearer: ***' "
                f"-H 'x-signature: los-local-signature' "
                f"-H 'Content-Type: application/json' "
                f"-H 'timecode: {timecode}' "
                f"-H 'Cookie: accessToken=***' "
                f"-H 'Connection: close' "
                f'-d \'{{"roundId": "{round_id}", "sicBo": {dice_result}}}\''
            )
            logger.error(f"Expected CURL command: {curl_command}")

        return table["name"], False


async def finish_round_for_table(table, token):
    """Finish round for a single table - helper function for thread pool execution"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"

        if table["name"] == "CIT":
            await retry_with_network_check(finish_post_v2, post_url, token)
        elif table["name"] == "UAT":
            await retry_with_network_check(finish_post_v2_uat, post_url, token)
        elif table["name"] == "PRD":
            try:
                await retry_with_network_check(
                    finish_post_v2_prd,
                    post_url,
                    token,
                    max_retries=5,
                    error_type="NO_FINISH",
                    table_name="PRD",
                )
            except Exception as e:
                logger.error(
                    f"PRD finish_post_v2_prd failed after retries: {e}"
                )
                # Error signal already sent in retry_with_network_check
                raise
        elif table["name"] == "STG":
            await retry_with_network_check(finish_post_v2_stg, post_url, token)
        elif table["name"] == "QAT":
            await retry_with_network_check(finish_post_v2_qat, post_url, token)
        elif table["name"] == "GLC":
            await retry_with_network_check(finish_post_v2_glc, post_url, token)

        return table["name"], True

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Error finishing round for table {table['name']}: {error_msg}"
        )

        # Check if this is a JSON parsing error for PRD or STG
        if "Expecting value: line 1 column 1 (char 0)" in error_msg and table[
            "name"
        ] in ["PRD", "STG"]:
            # Log detailed information for debugging
            logger.error(
                f"JSON parsing error detected for {table['name']} finish"
            )
            logger.error(f"Table: {table['name']}")
            logger.error(f"Post URL: {post_url}")
            logger.error(f"Token: ***")
            logger.error(f"Timestamp: {int(time.time())}")

            # Log the expected curl command
            curl_command = (
                f"curl -X POST '{post_url}/finish' "
                f"-H 'accept: application/json' "
                f"-H 'Bearer: ***' "
                f"-H 'x-signature: los-local-signature' "
                f"-H 'Content-Type: application/json' "
                f"-H 'Cookie: accessToken=***' "
                f"-H 'Connection: close'"
            )
            logger.error(f"Expected CURL command: {curl_command}")

        return table["name"], False


async def betStop_round_for_table(table, token):
    """Stop betting for a single table - helper function for thread pool execution"""
    try:
        post_url = f"{table['post_url']}{table['game_code']}"

        if table["name"] == "CIT":
            await retry_with_network_check(bet_stop_post, post_url, token)
        elif table["name"] == "UAT":
            await retry_with_network_check(bet_stop_post_uat, post_url, token)
        elif table["name"] == "PRD":
            try:
                await retry_with_network_check(
                    bet_stop_post_prd,
                    post_url,
                    token,
                    max_retries=5,
                    error_type="NO_BETSTOP",
                    table_name="PRD",
                )
            except Exception as e:
                logger.error(
                    f"PRD bet_stop_post_prd failed after retries: {e}"
                )
                # Error signal already sent in retry_with_network_check
                raise
        elif table["name"] == "STG":
            await retry_with_network_check(bet_stop_post_stg, post_url, token)
        elif table["name"] == "QAT":
            await retry_with_network_check(bet_stop_post_qat, post_url, token)
        elif table["name"] == "GLC":
            await retry_with_network_check(bet_stop_post_glc, post_url, token)

        return table["name"], True

    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Error stopping betting for table {table['name']}: {error_msg}"
        )
        return table["name"], False


async def retry_with_network_check(
    func,
    *args,
    max_retries=5,
    retry_delay=5,
    error_type=None,
    table_name=None,
    environment=None,
):
    """
    Retry a function with network error checking and optional error signal sending.

    Args:
        func: The function to retry
        *args: Arguments to pass to the function
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        error_type: Error type for error signal ("NO_START", "NO_BETSTOP", "NO_DEAL", "NO_FINISH")
        table_name: Table name (e.g., "PRD", "STG") - only send error signal for PRD
        environment: Environment name (optional, for compatibility)

    Returns:
        The result of the function if successful
    """
    retry_count = 0
    last_exception = None
    
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
                logger.error(f"Network error occurred: {error_message}")
                logger.info(f"Waiting {retry_delay} seconds before retry...")
                
                # Send error signal for PRD environment if error_type is provided
                # Send warn signal during retry (retry_count < max_retries)
                if error_type is not None and table_name == "PRD":
                    try:
                        await send_table_api_error_signal(
                            error_type=error_type,
                            retry_count=retry_count,
                            max_retries=max_retries,
                            table_id="SBO-001",
                            device_id="ASB-001-1",
                        )
                    except Exception as signal_error:
                        logger.error(
                            f"Failed to send error signal: {signal_error}"
                        )
                
                await asyncio.sleep(retry_delay)
                retry_count += 1
                last_exception = e
                continue
            # Not a network error, re-raise
            last_exception = e
            raise
        except Exception as e:
            # Handle non-network errors (e.g., API errors, validation errors)
            # For PRD environment, send error signal if error_type is provided
            # Send warn signal during retry (retry_count < max_retries)
            if error_type is not None and table_name == "PRD":
                try:
                    await send_table_api_error_signal(
                        error_type=error_type,
                        retry_count=retry_count,
                        max_retries=max_retries,
                        table_id="SBO-001",
                        device_id="ASB-001-1",
                    )
                except Exception as signal_error:
                    logger.error(f"Failed to send error signal: {signal_error}")
            
            # If we've exhausted retries, send final error signal and raise
            if retry_count >= max_retries - 1:
                if error_type is not None and table_name == "PRD":
                    try:
                        # Send error signal when max_retries exceeded
                        await send_table_api_error_signal(
                            error_type=error_type,
                            retry_count=max_retries,
                            max_retries=max_retries,
                            table_id="SBO-001",
                            device_id="ASB-001-1",
                        )
                    except Exception as signal_error:
                        logger.error(f"Failed to send final error signal: {signal_error}")
                raise Exception(
                    f"Max retries ({max_retries}) reached while attempting to execute {func.__name__}: {e}"
                )
            
            retry_count += 1
            last_exception = e
            await asyncio.sleep(retry_delay)
            continue
    
    # All retries exhausted - send error signal if applicable
    if error_type is not None and table_name == "PRD":
        try:
            await send_table_api_error_signal(
                error_type=error_type,
                retry_count=max_retries,
                max_retries=max_retries,
                table_id="SBO-001",
                device_id="ASB-001-1",
            )
        except Exception as signal_error:
            logger.error(f"Failed to send final error signal: {signal_error}")
    
    raise Exception(
        f"Max retries ({max_retries}) reached while attempting to execute {func.__name__}"
    ) from last_exception


class SDPGame:
    """Main game class for SDP"""

    def __init__(self, config: GameConfig): 
        self.config = config
        self.logger = logging.getLogger("SDPGame")

        # initialize controllers
        self.game_controller = create_game_state_controller(config.game_type)
        self.mqtt_controller = MQTTController(
            client_id=f"sdp_controller_{config.room_id}",
            broker=config.broker_host,
            port=config.broker_port,
        )
        self.idp_controller = IDPController(config)
        self.shaker_controller = ShakerController(config)
        self.running = False

        # load all table configs
        self.table_configs = load_table_config()
        self.token = "E5LN4END9Q"
        self.logger.info(
            f"Loaded {len(self.table_configs)} table configurations"
        )
        
        # Set table_configs and token for IDP controller to enable broadcast_post
        self.idp_controller.table_configs = self.table_configs
        self.idp_controller.token = self.token

        self.stream_started = False

        # WebSocket client
        self.ws_client = None
        self.ws_connected = False

    async def initialize(self):
        """Initialize all controllers"""
        try:
            self.logger.info("Initializing MQTT controller...")
            await self.mqtt_controller.initialize()

            self.logger.info("Initializing IDP controller...")
            await self.idp_controller.initialize()

            self.logger.info("Initializing shaker controller...")
            await self.shaker_controller.initialize()

            # set up MQTT controller for SicBo game
            if self.config.game_type == GameType.SICBO:
                await self.game_controller.set_mqtt_controller(
                    self.mqtt_controller
                )

            self.logger.info("All controllers initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            # Try to cleanup any partially initialized controllers
            try:
                await self.cleanup()
            except Exception as cleanup_error:
                self.logger.error(f"Cleanup error: {cleanup_error}")
            return False

    async def connect_to_recorder(self, uri="ws://localhost:8765"):
        """Connect to the stream recorder via WebSocket"""
        try:
            self.ws_client = await websockets.connect(uri)
            self.ws_connected = True
            self.logger.info(f"Connected to stream recorder at {uri}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to stream recorder: {e}")
            self.ws_connected = False
            return False

    async def send_to_recorder(self, message):
        """Send message to stream recorder"""
        if not self.ws_connected or not self.ws_client:
            self.logger.warning(
                "Not connected to stream recorder, attempting to reconnect..."
            )
            await self.connect_to_recorder()

        if self.ws_connected:
            try:
                await self.ws_client.send(message)
                response = await self.ws_client.recv()
                self.logger.info(f"Recorder response: {response}")
                return True
            except Exception as e:
                self.logger.error(f"Error sending message to recorder: {e}")
                self.ws_connected = False
                return False
        return False

    async def check_mqtt_connections(self):
        """Check MQTT connection status for all controllers"""
        try:
            # Check shaker controller MQTT connection
            if hasattr(self.shaker_controller, "mqtt_client"):
                if hasattr(self.shaker_controller.mqtt_client, "connected"):
                    if not self.shaker_controller.mqtt_client.connected:
                        self.logger.warning("Shaker MQTT disconnected")
                    else:
                        self.logger.info("Shaker MQTT connection is healthy")

            # Check IDP controller MQTT connection
            if hasattr(self.idp_controller, "mqtt_client"):
                if hasattr(self.idp_controller.mqtt_client, "connected"):
                    if not self.idp_controller.mqtt_client.connected:
                        self.logger.warning("IDP MQTT disconnected")
                    else:
                        self.logger.info("IDP MQTT connection is healthy")

            # Check main MQTT controller connection
            if hasattr(self.mqtt_controller, "mqtt_logger"):
                if hasattr(self.mqtt_controller.mqtt_logger, "connected"):
                    if not self.mqtt_controller.mqtt_logger.connected:
                        self.logger.warning("Main MQTT disconnected")
                    else:
                        self.logger.info("Main MQTT connection is healthy")

        except Exception as e:
            self.logger.error(f"Error checking MQTT connections: {e}")

    async def ensure_mqtt_connections(self):
        """Ensure all MQTT connections are active, reconnect if necessary"""
        try:
            # Check and reconnect shaker controller if needed
            if (
                hasattr(self.shaker_controller, "mqtt_client")
                and hasattr(self.shaker_controller.mqtt_client, "connected")
                and not self.shaker_controller.mqtt_client.connected
            ):
                self.logger.info("Reconnecting shaker MQTT...")
                await self.shaker_controller.initialize()

            # Check and reconnect IDP controller if needed
            if (
                hasattr(self.idp_controller, "mqtt_client")
                and hasattr(self.idp_controller.mqtt_client, "connected")
                and not self.idp_controller.mqtt_client.connected
            ):
                self.logger.info("Reconnecting IDP MQTT...")
                await self.idp_controller.initialize()

            # Check and reconnect main MQTT controller if needed
            if (
                hasattr(self.mqtt_controller, "mqtt_logger")
                and hasattr(self.mqtt_controller.mqtt_logger, "connected")
                and not self.mqtt_controller.mqtt_logger.connected
            ):
                self.logger.info("Reconnecting main MQTT...")
                await self.mqtt_controller.initialize()

        except Exception as e:
            self.logger.error(f"Error ensuring MQTT connections: {e}")

    async def _bet_stop_countdown(self, table, round_id, bet_period):
        """Countdown and call bet stop for a table (non-blocking)"""
        try:
            # Wait for the bet period duration
            await asyncio.sleep(bet_period)

            # Call bet stop for the table
            self.logger.info(
                f"Calling bet stop for {table['name']} (round {round_id})"
            )
            result = await betStop_round_for_table(table, self.token)

            if result[1]:  # Check if successful
                self.logger.info(
                    f"Successfully stopped betting for {table['name']}"
                )
            else:
                self.logger.error(
                    f"Failed to stop betting for {table['name']}"
                )

        except Exception as e:
            self.logger.error(
                f"Error in bet stop countdown for {table['name']}: {e}"
            )

    async def run_sicbo_game(self):
        """Run self test for all components"""
        self.logger.info("Starting self test...")

        # initialize all controllers (only once)
        try:
            # Use the unified initialize method
            if not await self.initialize():
                self.logger.error("Failed to initialize controllers")
                return False

            # connect to recorder
            await self.connect_to_recorder()
            self.logger.info("All controllers initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize controllers: {e}")
            return False

        while True:  # infinite loop for game round
            try:
                # Check MQTT connections periodically
                await self.check_mqtt_connections()

                # check previous round status
                self.logger.info("Checking previous round status...")
                try:
                    # check status for all tables
                    for table in self.table_configs:
                        get_url = f"{table['get_url']}{table['game_code']}"
                        if table["name"] == "CIT":
                            round_id, status, bet_period = (
                                await retry_with_network_check(
                                    get_roundID_v2,
                                    get_url,
                                    self.token,
                                    max_retries=2,
                                )
                            )
                        elif table["name"] == "UAT":
                            round_id, status, bet_period = (
                                await retry_with_network_check(
                                    get_roundID_v2_uat,
                                    get_url,
                                    self.token,
                                    max_retries=2,
                                )
                            )
                        elif table["name"] == "PRD":
                            round_id, status, bet_period = (
                                await retry_with_network_check(
                                    get_roundID_v2_prd, get_url, self.token
                                )
                            )
                        elif table["name"] == "STG":
                            round_id, status, bet_period = (
                                await retry_with_network_check(
                                    get_roundID_v2_stg, get_url, self.token
                                )
                            )
                        elif table["name"] == "QAT":
                            round_id, status, bet_period = (
                                await retry_with_network_check(
                                    get_roundID_v2_qat,
                                    get_url,
                                    self.token,
                                    max_retries=2,
                                )
                            )
                        elif table["name"] == "GLC":
                            round_id, status, bet_period = (
                                await retry_with_network_check(
                                    get_roundID_v2_glc,
                                    get_url,
                                    self.token,
                                    max_retries=2,
                                )
                            )
                        self.logger.info(
                            f"Table {table['name']} - round_id: {round_id}, status: {status}, bet_period: {bet_period}"
                        )
                except Exception as e:
                    self.logger.error(f"Error checking previous round: {e}")
                    await asyncio.sleep(5)
                    continue

                # start new round
                self.logger.info("Starting new round...")
                round_start_time = time.time()
                
                # Reset all table API error signal counts for new round
                reset_all_error_signal_counts(table_id="SBO-001", device_id="ASB-001-1")

                # Update Sicbo game status before starting rounds (using fast mode)
                self.logger.info("Updating Sicbo game device status...")
                try:
                    await update_sicbo_game_status(fast_mode=True)
                    self.logger.info(
                        "✅ Sicbo game device status updated successfully"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"⚠️  Failed to update Sicbo game device status: {e}"
                    )
                    self.logger.info("Continuing with round start...")

                # send start request to all tables using thread pool for parallel execution
                round_ids = []
                self.logger.info(
                    "Starting rounds for all tables in parallel..."
                )

                # Create tasks for all tables
                tasks = []
                for table in self.table_configs:
                    task = start_round_for_table(table, self.token)
                    tasks.append(task)

                # Execute all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(
                            f"Error starting round for table {self.table_configs[i]['name']}: {result}"
                        )
                    elif (
                        result and result[0] and result[1]
                    ):  # Check if we got valid table and round_id
                        table, round_id, bet_period = result
                        round_ids.append((table, round_id, bet_period))
                        self.logger.info(
                            f"Started round {round_id} for {table['name']} with bet period {bet_period}"
                        )
                    else:
                        self.logger.warning(
                            f"Failed to start round for table {self.table_configs[i]['name']}"
                        )

                if not round_ids:
                    self.logger.error("Failed to start round on any table")
                    await asyncio.sleep(5)
                    continue

                # Start bet stop countdown for each table (non-blocking)
                bet_stop_tasks = []
                for table, round_id, bet_period in round_ids:
                    if bet_period and bet_period > 0:
                        # Create async task for bet stop countdown
                        task = asyncio.create_task(
                            self._bet_stop_countdown(
                                table, round_id, bet_period
                            )
                        )
                        bet_stop_tasks.append(task)
                        self.logger.info(
                            f"Started bet stop countdown for {table['name']} "
                            f"(round {round_id}, {bet_period}s)"
                        )

                # notify recorder to start recording
                if round_ids:
                    # use first table's round_id as recording identifier
                    first_table, first_round_id, _ = round_ids[0]
                    await self.send_to_recorder(
                        f"start_recording:{first_round_id}"
                    )

                ## wait for betting period
                pre_shaking_duration = 2
                self.logger.info(
                    f"Waiting for pre-shaking period ({pre_shaking_duration:.1f} seconds)..."
                )
                await asyncio.sleep(pre_shaking_duration)

                # notify recorder to start recording
                if round_ids:
                    # use first table's round_id as recording identifier
                    first_table, first_round_id, _ = round_ids[0]
                    await self.send_to_recorder(
                        f"start_recording:{first_round_id}"
                    )

                # Reset error signal flag for new shake cycle
                self.idp_controller.reset_error_signal_flag()

                # Shake command
                self.logger.info(
                    f"Shake command with round ID: {first_round_id}"
                )
                await self.shaker_controller.shake(first_round_id)

                # Wait for shaker to reach S0 state before sending detect command
                self.logger.info("Waiting for shaker to reach S0 state...")
                s0_reached = await self.shaker_controller.wait_for_s0_state()

                if not s0_reached:
                    self.logger.warning(
                        "Shaker did not reach S0 state, but continuing with detect command..."
                    )
                else:
                    self.logger.info(
                        "Shaker successfully reached S0 state, proceeding with detect command..."
                    )

                # Detect command
                # max_retries = 3
                max_retries = 10000
                retry_count = 0

                while retry_count < max_retries:
                    self.logger.info(
                        f"Testing detect command... (attempt {retry_count + 1})"
                    )

                    # Log timing information
                    self.logger.info("====================")
                    self.logger.info("[DEBUG] detect command, time:")
                    self.logger.info(
                        str(int(time.time() * 1000)),
                        "HH:MM:SS.msmsms",
                        str(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")),
                    )
                    self.logger.info("====================")

                    detect_time = int(time.time() * 1000)
                    success, dice_result = await self.idp_controller.detect(
                        first_round_id
                    )

                    is_valid_result = (
                        success
                        and dice_result
                        and isinstance(dice_result, list)
                        and all(
                            isinstance(x, int) and x > 0 for x in dice_result
                        )
                    )

                    # for test, temporarily set is_valid_result to False
                    # is_valid_result = False

                    if is_valid_result:
                        self.logger.info(
                            f"Sending dice result to all tables: {dice_result}"
                        )
                        deal_time = time.time()
                        start_to_deal_time = deal_time - round_start_time
                        self.logger.info(
                            f"Start to deal time: {start_to_deal_time:.1f} seconds"
                        )
                        # if start_to_deal_time > 20:
                        # sentry_sdk.capture_message("[SBO-001][ERR_SPIN_TIME]: Start to deal time is too long.")

                        # notify recorder to stop recording
                        await self.send_to_recorder("stop_recording")
                        await asyncio.sleep(2.5)
                        self.logger.info("====================")
                        self.logger.info("[DEBUG] send dice result, time:")
                        self.logger.info(
                            str(int(time.time() * 1000)),
                            "HH:MM:SS.msmsms",
                            str(
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                            ),
                        )
                        self.logger.info("====================")
                        # Deal round for all tables using thread pool for parallel execution
                        self.logger.info(
                            "Dealing rounds for all tables in parallel..."
                        )

                        # Create tasks for all tables
                        deal_tasks = []
                        for table, round_id, _ in round_ids:
                            task = deal_round_for_table(
                                table, self.token, round_id, dice_result
                            )
                            deal_tasks.append(task)

                        # Execute all deal tasks concurrently
                        deal_results = await asyncio.gather(
                            *deal_tasks, return_exceptions=True
                        )

                        # Process deal results and record timing for CIT table
                        deal_time = int(time.time() * 1000)
                        self.logger.info(f"deal_time: {deal_time}")
                        detect_to_deal_time = deal_time - detect_time
                        self.logger.info(
                            f"[DEBUG]Detect to deal time: {detect_to_deal_time:.1f} ms"
                        )

                        # Log deal results
                        for i, result in enumerate(deal_results):
                            if isinstance(result, Exception):
                                table_name = round_ids[i][0]["name"]
                                error_msg = str(result)

                                self.logger.error(
                                    f"Error dealing round for table {table_name}: {error_msg}"
                                )

                                # Check if this is a JSON parsing error for PRD or STG
                                if (
                                    "Expecting value: line 1 column 1 (char 0)"
                                    in error_msg
                                    and table_name in ["PRD", "STG"]
                                ):
                                    # Log detailed information for debugging
                                    table = round_ids[i][0]
                                    post_url = f"{table['post_url']}{table['game_code']}"
                                    timecode = str(int(time.time() * 1000))

                                    self.logger.error(
                                        f"JSON parsing error detected for {table_name}"
                                    )
                                    self.logger.error(f"Table: {table_name}")
                                    self.logger.error(f"Round ID: {round_id}")
                                    self.logger.error(
                                        f"Dice Result: {dice_result}"
                                    )
                                    self.logger.error(f"Post URL: {post_url}")
                                    self.logger.error(f"Token: ***")
                                    self.logger.error(
                                        f"Timestamp: {int(time.time())}"
                                    )

                                    # Log the expected curl command
                                    curl_command = (
                                        f"curl -X POST '{post_url}/deal' "
                                        f"-H 'accept: application/json' "
                                        f"-H 'Bearer: ***' "
                                        f"-H 'x-signature: los-local-signature' "
                                        f"-H 'Content-Type: application/json' "
                                        f"-H 'timecode: {timecode}' "
                                        f"-H 'Cookie: accessToken=***' "
                                        f"-H 'Connection: close' "
                                        f'-d \'{{"roundId": "{round_id}", "sicBo": {dice_result}}}\''
                                    )
                                    self.logger.error(
                                        f"Expected CURL command: {curl_command}"
                                    )

                                    # Send Slack notification only if cooldown period has passed
                                    if should_send_error_notification(
                                        table_name, cooldown_minutes=15
                                    ):
                                        slack_message = (
                                            f"Description: JSON parsing error in deal_post\n"
                                            f"Details: {error_msg}\n"
                                        )

                                        try:
                                            send_error_to_slack(
                                                error_message=slack_message,
                                                environment=table_name,
                                                table_name="SBO-001",
                                                error_code="JSON_PARSE_ERROR",
                                            )
                                            self.logger.info(
                                                f"Slack notification sent for {table_name} JSON parsing error"
                                            )
                                        except Exception as slack_error:
                                            self.logger.error(
                                                f"Failed to send Slack notification: {slack_error}"
                                            )

                            elif (
                                result and result[1]
                            ):  # Check if deal was successful
                                self.logger.info(
                                    f"Successfully dealt round for table {result[0]}"
                                )
                            else:
                                self.logger.warning(
                                    f"Failed to deal round for table {round_ids[i][0]['name']}"
                                )

                        # Finish round for all tables using thread pool for parallel execution
                        self.logger.info(
                            "Finishing rounds for all tables in parallel..."
                        )

                        # Create tasks for all tables
                        finish_tasks = []
                        for table, round_id, _ in round_ids:
                            task = finish_round_for_table(table, self.token)
                            finish_tasks.append(task)

                        # Execute all finish tasks concurrently
                        finish_results = await asyncio.gather(
                            *finish_tasks, return_exceptions=True
                        )

                        # Log finish results
                        for i, result in enumerate(finish_results):
                            if isinstance(result, Exception):
                                table_name = round_ids[i][0]["name"]
                                error_msg = str(result)

                                self.logger.error(
                                    f"Error finishing round for table {table_name}: {error_msg}"
                                )

                                # Check if this is a JSON parsing error for PRD or STG
                                if (
                                    "Expecting value: line 1 column 1 (char 0)"
                                    in error_msg
                                    and table_name in ["PRD", "STG"]
                                ):

                                    # Send Slack notification only if cooldown period has passed
                                    if should_send_error_notification(
                                        table_name, cooldown_minutes=15
                                    ):
                                        slack_message = (
                                            f"🚨 *SDP Error Alert*\n"
                                            f"*Environment:* {table_name}\n"
                                            f"*Error:* JSON parsing error in finish_round\n"
                                            f"*Details:* {error_msg}\n"
                                            f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                            f"*Table:* {table_name}"
                                        )

                                        try:
                                            send_error_to_slack(
                                                error_message=slack_message,
                                                environment=table_name,
                                                table_name=table_name,
                                                error_code="JSON_PARSE_ERROR",
                                            )
                                            self.logger.info(
                                                f"Slack notification sent for {table_name} finish round JSON parsing error"
                                            )
                                        except Exception as slack_error:
                                            self.logger.error(
                                                f"Failed to send Slack notification: {slack_error}"
                                            )

                            elif (
                                result and result[1]
                            ):  # Check if finish was successful
                                self.logger.info(
                                    f"Successfully finished round for table {result[0]}"
                                )
                            else:
                                self.logger.warning(
                                    f"Failed to finish round for table {round_ids[i][0]['name']}"
                                )
                        # notify recorder to stop recording
                        await self.send_to_recorder("stop_recording")

                        # calculate actual round duration
                        round_duration = time.time() - round_start_time
                        self.logger.info(
                            f"Round completed for {table['name']} in {round_duration:.1f} seconds"
                        )

                        # if round duration is less than expected, wait for remaining time
                        TOTAL_ROUND_TIME = 16  # not 19, 5+7+4 = 16s
                        if round_duration < TOTAL_ROUND_TIME:
                            remaining_time = TOTAL_ROUND_TIME - round_duration
                            self.logger.info(
                                f"Waiting {remaining_time:.1f} seconds to complete round for {table['name']}"
                            )
                            await asyncio.sleep(remaining_time)

                        break  # if get valid result, break the loop

                    else:
                        self.logger.info(
                            "Invalid result received, retrying shake and detect..."
                        )
                        # re-shake
                        for table in self.table_configs:
                            post_url = (
                                f"{table['post_url']}{table['game_code']}"
                            )
                            if table["name"] == "CIT":
                                broadcast_post_v2(
                                    post_url,
                                    self.token,
                                    "dice.reshake",
                                    "players",
                                    4,
                                )
                                # sentry_sdk.capture_message("[SBO-001][CIT][ERR_RESHAKE]: Issue detected. Reshake ball.")
                            elif table["name"] == "UAT":
                                broadcast_post_v2_uat(
                                    post_url,
                                    self.token,
                                    "dice.reshake",
                                    "players",
                                    4,
                                )
                                # sentry_sdk.capture_message("[SBO-001][UAT][ERR_RESHAKE]: Issue detected. Reshake ball.")
                            elif table["name"] == "PRD":
                                broadcast_post_v2_prd(
                                    post_url,
                                    self.token,
                                    "dice.reshake",
                                    "players",
                                    4,
                                )
                                # sentry_sdk.capture_message("[SBO-001][PRD][ERR_RESHAKE]: Issue detected. Reshake ball.")
                            elif table["name"] == "STG":
                                broadcast_post_v2_stg(
                                    post_url,
                                    self.token,
                                    "dice.reshake",
                                    "players",
                                    4,
                                )
                                # sentry_sdk.capture_message("[SBO-001][STG][ERR_RESHAKE]: Issue detected. Reshake ball.")
                            elif table["name"] == "QAT":
                                broadcast_post_v2_qat(
                                    post_url,
                                    self.token,
                                    "dice.reshake",
                                    "players",
                                    4,
                                )
                                # sentry_sdk.capture_message("[SBO-001][QAT][ERR_RESHAKE]: Issue detected. Reshake ball.")
                            elif table["name"] == "GLC":
                                broadcast_post_v2_glc(
                                    post_url,
                                    self.token,
                                    "dice.reshake",
                                    "players",
                                    4,
                                )
                                # sentry_sdk.capture_message("[SBO-001][GLC][ERR_RESHAKE]: Issue detected. Reshake ball.")
                        # Reset error signal flag for reshake cycle
                        self.idp_controller.reset_error_signal_flag()
                        await self.shaker_controller.shake(first_round_id)
                        retry_count += 1
                        if retry_count >= max_retries:
                            # self.logger.error("Max retries reached, cancelling round")
                            self.logger.info(
                                "Max retries reached, pause round"
                            )
                            for table, round_id, _ in round_ids:
                                post_url = (
                                    f"{table['post_url']}{table['game_code']}"
                                )

                                # Initialize status variables
                                status_cit = None
                                status_uat = None
                                status_prd = None
                                status_stg = None
                                status_qat = None
                                status_glc = None

                                # change to: pause_post, then start polling, until status is "finished" or "canceled", then start a new round
                                if table["name"] == "CIT":
                                    pause_post_v2(
                                        post_url,
                                        self.token,
                                        "IDP cannot detect  the result for 3 times",
                                    )
                                    print(
                                        "after pause_post_v2, status_cit:",
                                        status_cit,
                                    )
                                elif table["name"] == "UAT":
                                    # pause_post(post_url, self.token, "IDP cannot detect  the result for 3 times")
                                    pause_post_v2_uat(
                                        post_url,
                                        self.token,
                                        "IDP cannot detect  the result for 3 times",
                                    )
                                    print(
                                        "after pause_post, status_uat:",
                                        status_uat,
                                    )
                                elif table["name"] == "PRD":
                                    pause_post_v2_prd(
                                        post_url,
                                        self.token,
                                        "IDP cannot detect  the result for 3 times",
                                    )
                                    print(
                                        "after pause_post, status_prd:",
                                        status_prd,
                                    )
                                elif table["name"] == "STG":
                                    pause_post_v2_stg(
                                        post_url,
                                        self.token,
                                        "IDP cannot detect  the result for 3 times",
                                    )
                                    print(
                                        "after pause_post, status_stg:",
                                        status_stg,
                                    )
                                elif table["name"] == "QAT":
                                    pause_post_v2_qat(
                                        post_url,
                                        self.token,
                                        "IDP cannot detect  the result for 3 times",
                                    )
                                    print(
                                        "after pause_post, status_qat:",
                                        status_qat,
                                    )
                                elif table["name"] == "GLC":
                                    pause_post_v2_glc(
                                        post_url,
                                        self.token,
                                        "IDP cannot detect  the result for 3 times",
                                    )
                                    print(
                                        "after pause_post, status_glc:",
                                        status_glc,
                                    )
                                # start polling, until status is "finished" or "canceled", then start a new round
                                while True:

                                    print("keep polling")

                                    if table["name"] == "CIT":
                                        _, status_cit, _ = get_roundID_v2(
                                            post_url, self.token
                                        )
                                        print("status:", status_cit)
                                    elif table["name"] == "UAT":
                                        _, status_uat, _ = get_roundID_v2_uat(
                                            post_url, self.token
                                        )
                                        print("status:", status_uat)
                                    elif table["name"] == "PRD":
                                        _, status_prd, _ = get_roundID_v2_prd(
                                            post_url, self.token
                                        )
                                        print("status:", status_prd)
                                    elif table["name"] == "STG":
                                        _, status_stg, _ = get_roundID_v2_stg(
                                            post_url, self.token
                                        )
                                        print("status:", status_stg)
                                    elif table["name"] == "QAT":
                                        _, status_qat, _ = get_roundID_v2_qat(
                                            post_url, self.token
                                        )
                                        print("status:", status_qat)
                                    elif table["name"] == "GLC":
                                        _, status_glc, _ = get_roundID_v2_glc(
                                            post_url, self.token
                                        )
                                        print("status:", status_glc)
                                    if (
                                        status_cit == "finished"
                                        or status_cit == "canceled"
                                    ) and (
                                        status_uat == "finished"
                                        or status_uat == "canceled"
                                    ):
                                        break

                                    await asyncio.sleep(1)
                                # back to the beginning of the infinite loop
                            break

            except Exception as e:
                self.logger.error(f"Error in game round: {e}")
                # For example, "Error in game round: Expecting value: line 1 column 1 (char 0)"
                # sentry_sdk.capture_message("[SBO-001][ERR_GAME_ROUND]: Error in game round", exc_info=True)
                await asyncio.sleep(5)

    async def cleanup(self):
        """Cleanup all resources"""
        self.logger.info("Cleaning up resources")

        # close WebSocket connection
        if self.ws_client:
            try:
                await self.ws_client.close()
                self.logger.info("WebSocket connection closed")
            except Exception as e:
                self.logger.error(f"Error closing WebSocket connection: {e}")

        # clean up in reverse order of initialization
        await self.shaker_controller.cleanup()
        await self.idp_controller.cleanup()
        await self.mqtt_controller.cleanup()
        if hasattr(self.game_controller, "cleanup"):
            await self.game_controller.cleanup()

    async def stop(self):
        """Stop the game system"""
        self.logger.info("Stopping game system")
        self.running = False
        await self.cleanup()


async def amain():
    """Async main function"""
    # 設置命令列參數
    parser = argparse.ArgumentParser(description="SDP Game System")
    parser.add_argument(
        "--broker",
        type=str,
        default="192.168.88.54",
        help="MQTT broker address (default: 192.168.88.54)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)",
    )
    parser.add_argument(
        "--game-type",
        type=str,
        choices=["roulette", "sicbo", "blackjack"],
        default="sicbo",
        help="Game type to run (default: sicbo)",
    )
    parser.add_argument(
        "--enable-logging",
        action="store_true",
        default=True,
        help="Enable MQTT logging to file (default: True)",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="./logs",
        help="Directory for log files (default: ./logs)",
    )
    parser.add_argument(
        "--get-url",
        type=str,
        default="https://los-api-uat.sdp.com.tw/api/v2/sdp/config",
        help="Get URL for SDP config (default: https://los-api-uat.sdp.com.tw/api/v2/sdp/config)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default="E5LN4END9Q",
        help="Token for SDP config (default: E5LN4END9Q)",
    )
    parser.add_argument(
        "-r",
        "--relaunch",
        action="store_true",
        default=True,
        help="Execute api_v2_all_sb.py before running main program (default: True)",
    )
    args = parser.parse_args()

    # Execute api_v2_all_sb.py if relaunch is enabled
    if args.relaunch:
        try:
            logger.info("Executing api_v2_all_sb.py before main program...")

            # construct the full path of api_v2_all_sb.py
            current_dir = Path(__file__).parent
            api_v2_all_sb_path = (
                current_dir / "los_api" / "sb" / "api_v2_all_sb.py"
            )

            if api_v2_all_sb_path.exists():
                # execute api_v2_all_sb.py
                import subprocess
                import sys

                logger.info(f"Running {api_v2_all_sb_path}")
                result = subprocess.run(
                    [
                        sys.executable,
                        str(api_v2_all_sb_path),
                        "--mode",
                        "parallel",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minutes timeout
                    cwd=api_v2_all_sb_path.parent,
                )

                if result.returncode == 0:
                    logger.info("api_v2_all_sb.py executed successfully")
                    logger.info("Output preview:")
                    # 顯示前幾行輸出
                    output_lines = result.stdout.strip().split("\n")[:10]
                    for line in output_lines:
                        logger.info(f"  {line}")
                    if len(result.stdout.strip().split("\n")) > 10:
                        logger.info("  ... (output truncated)")
                else:
                    logger.warning(
                        f"api_v2_all_sb.py failed with return code {result.returncode}"
                    )
                    logger.warning(f"Error output: {result.stderr}")

            else:
                logger.warning(
                    f"api_v2_all_sb.py not found at {api_v2_all_sb_path}"
                )

        except subprocess.TimeoutExpired:
            logger.error(
                "api_v2_all_sb.py execution timed out after 2 minutes"
            )
        except Exception as e:
            logger.error(f"Error executing api_v2_all_sb.py: {e}")
            logger.info("Continuing with main program execution...")

    # set up logging - directly use default values
    setup_logging(True, args.log_dir)

    # get SDP config from LOS API
    try:
        sdp_config = get_sdp_config_v2_uat(url=args.get_url, token=args.token)
        # use SDP config to override default values, but keep command line parameters priority
        broker = args.broker or sdp_config.get("broker_host")
        port = args.port or sdp_config.get("broker_port")
        room_id = sdp_config.get("room_id")
        # can add other config parameters
    except Exception as e:
        logging.warning(f"Failed to get SDP config: {e}, using default values")
        broker = args.broker
        port = args.port
        room_id = "SBO-001"

    # create game config
    config = GameConfig(
        game_type=GameType(args.game_type),
        room_id=room_id,
        broker_host=broker,
        broker_port=port,
        enable_logging=args.enable_logging,
        log_dir=args.log_dir,
    )

    # create game instance
    game = SDPGame(config)

    try:
        await game.run_sicbo_game()

    except KeyboardInterrupt:
        logging.info("Game interrupted by user")
        # sentry_sdk.capture_message("[SBO-001][WARN_INTERRUPT]: SDP interrupted by developer")
    except Exception as e:
        logging.error(f"Game error: {e}")
    finally:
        await game.cleanup()


def main():
    """Entry point for the application"""
    asyncio.run(amain())


if __name__ == "__main__":
    main()
