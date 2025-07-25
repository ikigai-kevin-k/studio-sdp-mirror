import asyncio
import logging
import json
import time
from typing import Optional
import requests
import argparse
import os
import logging.handlers
import subprocess
import websockets
import urllib3
from requests.exceptions import ConnectionError

from controller import GameType, GameConfig
from gameStateController import create_game_state_controller
from deviceController import IDPController, ShakerController
from mqttController import MQTTController
from los_api.api_v2_sb import start_post_v2, deal_post_v2, finish_post_v2, pause_post_v2, get_roundID_v2, broadcast_post_v2
from los_api.api_v2_sb_uat import start_post_v2_uat, deal_post_v2_uat, finish_post_v2_uat, pause_post_v2_uat, get_roundID_v2_uat, broadcast_post_v2_uat, get_sdp_config_v2_uat
from los_api.api_v2_sb_prd import start_post_v2_prd, deal_post_v2_prd, finish_post_v2_prd, pause_post_v2_prd, get_roundID_v2_prd, broadcast_post_v2_prd, get_sdp_config_v2_prd
from los_api.api_v2_sb_stg import start_post_v2_stg, deal_post_v2_stg, finish_post_v2_stg, pause_post_v2_stg, get_roundID_v2_stg, broadcast_post_v2_stg, get_sdp_config_v2_stg
from los_api.api_v2_sb_qat import start_post_v2_qat, deal_post_v2_qat, finish_post_v2_qat, pause_post_v2_qat, get_roundID_v2_qat, broadcast_post_v2_qat, get_sdp_config_v2_qat
from networkChecker import networkChecker

import sentry_sdk

sentry_sdk.init(
    dsn="https://63a51b0fa2f4c419adaf46fafea61e89@o4509115379679232.ingest.us.sentry.io/4509643182440448",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_logging(enable_logging: bool, log_dir: str):
    """Setup logging configuration"""
    if enable_logging:
        # ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # set up file handler
        log_file = os.path.join(log_dir, f'SBO001_{time.strftime("%m%d")}.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # set up formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        
        logging.info(f"Logging to file: {log_file}")

def load_table_config(config_file='conf/table-config-scibo-v2.json'):
    """Load table configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading table config: {e}")
        return []

async def retry_with_network_check(func, *args, max_retries=5, retry_delay=5):
# async def retry_with_network_check(func, *args, max_retries=5, retry_delay=5):
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
            return await func(*args) if asyncio.iscoroutinefunction(func) else func(*args)
        except (ConnectionError, urllib3.exceptions.NewConnectionError, urllib3.exceptions.MaxRetryError) as e:
            is_network_error, error_message = networkChecker(e)
            if is_network_error:
                logger.error(f"Network error occurred: {error_message}")
                logger.info(f"Waiting {retry_delay} seconds before retry...")
                await asyncio.sleep(retry_delay)
                retry_count += 1
                continue
            raise
    raise Exception(f"Max retries ({max_retries}) reached while attempting to execute {func.__name__}")

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
            port=config.broker_port
        )
        self.idp_controller = IDPController(config)
        self.shaker_controller = ShakerController(config)
        self.running = False
        
        # load all table configs
        self.table_configs = load_table_config()
        self.token = 'E5LN4END9Q'
        self.logger.info(f"Loaded {len(self.table_configs)} table configurations")
        
        self.stream_started = False
        
        # WebSocket client
        self.ws_client = None
        self.ws_connected = False

    async def initialize(self):
        """Initialize all controllers"""
        try:
            await self.mqtt_controller.initialize()
            await self.idp_controller.initialize()
            await self.shaker_controller.initialize()
            
            # set up MQTT controller for SicBo game
            if self.config.game_type == GameType.SICBO:
                await self.game_controller.set_mqtt_controller(self.mqtt_controller)
                
            self.logger.info("All controllers initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False

    async def connect_to_recorder(self, uri='ws://localhost:8765'):
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
            self.logger.warning("Not connected to stream recorder, attempting to reconnect...")
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

    async def run_sicbo_game(self):
        """Run self test for all components"""
        self.logger.info("Starting self test...")
        
        # initialize all controllers (only once)
        try:
            await self.mqtt_controller.initialize()
            await self.shaker_controller.initialize()
            await self.idp_controller.initialize()
            # connect to recorder
            await self.connect_to_recorder()
            self.logger.info("All controllers initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize controllers: {e}")
            return False

        while True:  # infinite loop for game round
            try:
                # check previous round status
                self.logger.info("Checking previous round status...")
                try:
                    # check status for all tables
                    for table in self.table_configs:
                        get_url = f"{table['get_url']}{table['game_code']}"
                        if table['name'] == 'CIT':
                            round_id, status, bet_period = await retry_with_network_check(
                                get_roundID_v2, get_url, self.token, max_retries=2
                            )
                        elif table['name'] == 'UAT':
                            round_id, status, bet_period = await retry_with_network_check(
                                get_roundID_v2_uat, get_url, self.token, max_retries=2
                            )
                        elif table['name'] == 'PRD':
                            round_id, status, bet_period = await retry_with_network_check(
                                get_roundID_v2_prd, get_url, self.token
                            )
                        elif table['name'] == 'STG':
                            round_id, status, bet_period = await retry_with_network_check(
                                get_roundID_v2_stg, get_url, self.token
                            )
                        elif table['name'] == 'QAT':
                            round_id, status, bet_period = await retry_with_network_check(
                                get_roundID_v2_qat, get_url, self.token, max_retries=2
                            )
                        self.logger.info(f"Table {table['name']} - round_id: {round_id}, status: {status}, bet_period: {bet_period}")
                        
                except Exception as e:
                    self.logger.error(f"Error checking previous round: {e}")
                    await asyncio.sleep(5)
                    continue

                # start new round
                self.logger.info("Starting new round...")
                round_start_time = time.time()
                
                # send start request to all tables
                round_ids = []
                for table in self.table_configs:
                    post_url = f"{table['post_url']}{table['game_code']}"
                    if table['name'] == 'CIT':
                        print("====================")
                        print("[DEBUG] CIT start_post_v2")
                        print("====================")
                        round_id, bet_period = await retry_with_network_check(
                            start_post_v2, post_url, self.token
                        )
                        print("====================")
                        print(round_id, bet_period)
                        print("====================")
                    elif table['name'] == 'UAT':
                        print("====================")
                        print("[DEBUG] UAT start_post_v2")
                        print("====================")
                        round_id, bet_period = await retry_with_network_check(
                            start_post_v2_uat, post_url, self.token
                        )
                        print("====================")
                        print(round_id, bet_period)
                        print("====================")
                    elif table['name'] == 'PRD':
                        print("====================")
                        print("[DEBUG] PRD start_post_v2")
                        print("====================")
                        round_id, bet_period = await retry_with_network_check(
                            start_post_v2_prd, post_url, self.token
                        )
                    elif table['name'] == 'STG':
                        print("====================")
                        print("[DEBUG] STG start_post_v2")
                        print("====================")
                        round_id, bet_period = await retry_with_network_check(
                            start_post_v2_stg, post_url, self.token
                        )

                    elif table['name'] == 'QAT':
                        print("====================")
                        print("[DEBUG] QAT start_post_v2")
                        print("====================")
                        round_id, bet_period = await retry_with_network_check(
                            start_post_v2_qat, post_url, self.token
                        )
                    if round_id != -1:
                        round_ids.append((table, round_id, bet_period))
                        self.logger.info(f"Started round {round_id} for {table['name']} with bet period {bet_period}")
                
                if not round_ids:
                    self.logger.error("Failed to start round on any table")
                    await asyncio.sleep(5)
                    continue
                
                # notify recorder to start recording
                if round_ids:
                    # use first table's round_id as recording identifier
                    first_table, first_round_id, _ = round_ids[0]
                    await self.send_to_recorder(f"start_recording:{first_round_id}")
                
                # wait for betting period
                betting_duration = 3
                self.logger.info(f"Waiting for betting period ({betting_duration:.1f} seconds)...")
                time.sleep(betting_duration)

                # notify recorder to start recording
                if round_ids:
                    # use first table's round_id as recording identifier
                    first_table, first_round_id, _ = round_ids[0]
                    await self.send_to_recorder(f"start_recording:{first_round_id}")            

                # Shake command
                self.logger.info(f"Shake command with round ID: {first_round_id}")
                await self.shaker_controller.shake(first_round_id)

                # Detect command
                # max_retries = 3
                max_retries = 10000
                retry_count = 0
                
                while retry_count < max_retries:
                    self.logger.info(f"Testing detect command... (attempt {retry_count + 1})")
                    time.sleep(2)
                    success, dice_result = self.idp_controller.detect(first_round_id)
                    
                    is_valid_result = (
                        success and 
                        dice_result and 
                        isinstance(dice_result, list) and 
                        all(isinstance(x, int) and x > 0 for x in dice_result)
                    )


                    # for test, temporarily set is_valid_result to False
                    # is_valid_result = False

                    if is_valid_result:
                        self.logger.info(f"Sending dice result to all tables: {dice_result}")
                        deal_time = time.time()
                        start_to_deal_time = deal_time - round_start_time
                        self.logger.info(f"Start to deal time: {start_to_deal_time:.1f} seconds")
                        if start_to_deal_time > 20:
                            sentry_sdk.capture_message("[SBO-001][ERR_SPIN_TIME]: Start to deal time is too long.")

                        # notify recorder to stop recording
                        await self.send_to_recorder("stop_recording")
                        time.sleep(2.5) 

                        for table, round_id, _ in round_ids:
                            post_url = f"{table['post_url']}{table['game_code']}"
                            if table['name'] == 'CIT':
                                await retry_with_network_check(
                                    deal_post_v2, post_url, self.token, round_id, dice_result
                                )
                            elif table['name'] == 'UAT':
                                await retry_with_network_check(
                                    deal_post_v2_uat, post_url, self.token, round_id, dice_result
                                )
                            elif table['name'] == 'PRD':
                                await retry_with_network_check(
                                    deal_post_v2_prd, post_url, self.token, round_id, dice_result
                                )
                            elif table['name'] == 'STG':
                                await retry_with_network_check(
                                    deal_post_v2_stg, post_url, self.token, round_id, dice_result
                                )
                            elif table['name'] == 'QAT':
                                await retry_with_network_check(
                                    deal_post_v2_qat, post_url, self.token, round_id, dice_result
                                )

                        for table, round_id, _ in round_ids:
                            post_url = f"{table['post_url']}{table['game_code']}"
                            if table['name'] == 'CIT':
                                await retry_with_network_check(
                                    finish_post_v2, post_url, self.token
                                )
                            elif table['name'] == 'UAT':
                                await retry_with_network_check(
                                    finish_post_v2_uat, post_url, self.token
                                )
                            elif table['name'] == 'PRD':
                                await retry_with_network_check(
                                    finish_post_v2_prd, post_url, self.token
                                )
                            elif table['name'] == 'STG':
                                await retry_with_network_check(
                                    finish_post_v2_stg, post_url, self.token
                                )
                            elif table['name'] == 'QAT':
                                await retry_with_network_check(
                                    finish_post_v2_qat, post_url, self.token
                                )
                        # notify recorder to stop recording
                        await self.send_to_recorder("stop_recording")
                            
                        # calculate actual round duration
                        round_duration = time.time() - round_start_time
                        self.logger.info(f"Round completed for {table['name']} in {round_duration:.1f} seconds")
                        
                        # if round duration is less than expected, wait for remaining time
                        TOTAL_ROUND_TIME = 16# not 19, 5+7+4 = 16s
                        if round_duration < TOTAL_ROUND_TIME:
                            remaining_time = TOTAL_ROUND_TIME - round_duration
                            self.logger.info(f"Waiting {remaining_time:.1f} seconds to complete round for {table['name']}")
                            await asyncio.sleep(remaining_time)
                        
                        break  # if get valid result, break the loop
                    
                    else:
                        self.logger.info("Invalid result received, retrying shake and detect...")
                        # re-shake
                        for table in self.table_configs:
                            post_url = f"{table['post_url']}{table['game_code']}"
                            if table['name'] == 'CIT':
                                broadcast_post_v2(post_url, self.token, "Issue detected. Reshake ball.", "players", {"afterSeconds": 4})
                                sentry_sdk.capture_message("[SBO-001][CIT][ERR_RESHAKE]: Issue detected. Reshake ball.")
                            elif table['name'] == 'UAT':
                                broadcast_post_v2_uat(post_url, self.token, "Issue detected. Reshake ball.", "players", {"afterSeconds": 4})
                                sentry_sdk.capture_message("[SBO-001][UAT][ERR_RESHAKE]: Issue detected. Reshake ball.")
                            elif table['name'] == 'PRD':
                                broadcast_post_v2_prd(post_url, self.token, "Issue detected. Reshake ball.", "players", {"afterSeconds": 4})
                                sentry_sdk.capture_message("[SBO-001][PRD][ERR_RESHAKE]: Issue detected. Reshake ball.")
                            elif table['name'] == 'STG':
                                broadcast_post_v2_stg(post_url, self.token, "Issue detected. Reshake ball.", "players", {"afterSeconds": 4})
                                sentry_sdk.capture_message("[SBO-001][STG][ERR_RESHAKE]: Issue detected. Reshake ball.")
                            elif table['name'] == 'QAT':
                                broadcast_post_v2_qat(post_url, self.token, "Issue detected. Reshake ball.", "players", {"afterSeconds": 4})
                                sentry_sdk.capture_message("[SBO-001][QAT][ERR_RESHAKE]: Issue detected. Reshake ball.")
                        await self.shaker_controller.shake(first_round_id)
                        retry_count += 1
                        if retry_count >= max_retries:
                            # self.logger.error("Max retries reached, cancelling round")
                            self.logger.info("Max retries reached, pause round")
                            for table, round_id, _ in round_ids:
                                post_url = f"{table['post_url']}{table['game_code']}"
                                
                                # change to: pause_post, then start polling, until status is "finished" or "canceled", then start a new round
                                if table['name'] == 'CIT':
                                    pause_post_v2(post_url, self.token, "IDP cannot detect  the result for 3 times")
                                    print("after pause_post_v2, status_cit:", status_cit)
                                elif table['name'] == 'UAT':
                                    # pause_post(post_url, self.token, "IDP cannot detect  the result for 3 times")
                                    pause_post_v2_uat(post_url, self.token, "IDP cannot detect  the result for 3 times")
                                    print("after pause_post, status_uat:", status_uat)
                                elif table['name'] == 'PRD':
                                    pause_post_v2_prd(post_url, self.token, "IDP cannot detect  the result for 3 times")
                                    print("after pause_post, status_prd:", status_prd)
                                elif table['name'] == 'STG':
                                    pause_post_v2_stg(post_url, self.token, "IDP cannot detect  the result for 3 times")
                                    print("after pause_post, status_stg:", status_stg)
                                elif table['name'] == 'QAT':
                                    pause_post_v2_qat(post_url, self.token, "IDP cannot detect  the result for 3 times")
                                    print("after pause_post, status_qat:", status_qat)
                                # start polling, until status is "finished" or "canceled", then start a new round
                                while True:

                                    print("keep polling")

                                    if table['name'] == 'CIT':
                                        _, status_cit, _ = get_roundID_v2(post_url, self.token)
                                        print("status:", status_cit)
                                    elif table['name'] == 'UAT':
                                        _, status_uat, _ = get_roundID_v2_uat(post_url, self.token)
                                        print("status:", status_uat)
                                    elif table['name'] == 'PRD':
                                        _, status_prd, _ = get_roundID_v2_prd(post_url, self.token)
                                        print("status:", status_prd)
                                    elif table['name'] == 'STG':
                                        _, status_stg, _ = get_roundID_v2_stg(post_url, self.token)
                                        print("status:", status_stg)
                                    elif table['name'] == 'QAT':
                                        _, status_qat, _ = get_roundID_v2_qat(post_url, self.token)
                                        print("status:", status_qat)
                                    if (status_cit == "finished" or status_cit == "canceled") and (status_uat == "finished" or status_uat == "canceled"):
                                        break
                                    
                                    time.sleep(1)
                                # back to the beginning of the infinite loop
                            break

            except Exception as e:
                self.logger.error(f"Error in game round: {e}")
                # For example, "Error in game round: Expecting value: line 1 column 1 (char 0)"
                sentry_sdk.capture_message("[SBO-001][ERR_GAME_ROUND]: Error in game round", exc_info=True)
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
        if hasattr(self.game_controller, 'cleanup'):
            await self.game_controller.cleanup()

    async def stop(self):
        """Stop the game system"""
        self.logger.info("Stopping game system")
        self.running = False
        await self.cleanup()

async def amain():
    """Async main function"""
    # 設置命令列參數
    parser = argparse.ArgumentParser(description='SDP Game System')
    parser.add_argument('--broker', type=str, default='192.168.88.180',
                      help='MQTT broker address (default: 192.168.88.180)')
    parser.add_argument('--port', type=int, default=1883,
                      help='MQTT broker port (default: 1883)')
    parser.add_argument('--game-type', type=str, choices=['roulette', 'sicbo', 'blackjack'],
                      default='sicbo', help='Game type to run (default: sicbo)')
    parser.add_argument('--enable-logging', action='store_true', default=True,
                      help='Enable MQTT logging to file (default: True)')
    parser.add_argument('--log-dir', type=str, default='./logs',
                      help='Directory for log files (default: ./logs)')
    parser.add_argument('--get-url', type=str, default='https://los-api-uat.sdp.com.tw/api/v2/sdp/config',
                      help='Get URL for SDP config (default: https://los-api-uat.sdp.com.tw/api/v2/sdp/config)')
    parser.add_argument('--token', type=str, default='E5LN4END9Q',
                      help='Token for SDP config (default: E5LN4END9Q)')
    args = parser.parse_args()

    # set up logging - directly use default values
    setup_logging(True, args.log_dir)

    # get SDP config from LOS API
    try:
        sdp_config = get_sdp_config_v2_uat(url=args.get_url, token=args.token)
        # use SDP config to override default values, but keep command line parameters priority
        broker = args.broker or sdp_config.get('broker_host')
        port = args.port or sdp_config.get('broker_port')
        room_id = sdp_config.get('room_id')
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
        log_dir=args.log_dir
    )

    # create game instance
    game = SDPGame(config)

    try:
        await game.run_sicbo_game()

    except KeyboardInterrupt:
        logging.info("Game interrupted by user")
        sentry_sdk.capture_message("[SBO-001][WARN_INTERRUPT]: SDP interrupted by developer")
    except Exception as e:
        logging.error(f"Game error: {e}")
    finally:
        await game.cleanup()

def main():
    """Entry point for the application"""
    asyncio.run(amain())

if __name__ == "__main__":
    main()
