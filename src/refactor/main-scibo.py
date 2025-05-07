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

from controller import GameType, GameConfig
from gameStateController import create_game_state_controller
from deviceController import IDPController, ShakerController
from mqttController import MQTTController
from los_api.api import start_post, deal_post, finish_post, visibility_post, get_roundID, resume_post, get_sdp_config, cancel_post, broadcast_post

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_logging(enable_logging: bool, log_dir: str):
    """Setup logging configuration"""
    if enable_logging:
        # 確保日誌目錄存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 設置檔案處理器
        log_file = os.path.join(log_dir, f'SDP002_{time.strftime("%m%d")}.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # 設置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # 設置根日誌記錄器
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
        # 同時保持控制台輸出
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        root_logger.setLevel(logging.INFO)
        
        logging.info(f"Logging to file: {log_file}")

def load_table_config(config_file='los_api/table-config-scibo.json'):
    """Load table configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading table config: {e}")
        return []

class SDPGame:
    """Main game class for SDP"""
    def __init__(self, config: GameConfig):
        self.config = config
        self.logger = logging.getLogger("SDPGame")
        
        # 初始化控制器
        self.game_controller = create_game_state_controller(config.game_type)
        self.mqtt_controller = MQTTController(
            client_id=f"sdp_controller_{config.room_id}",
            broker=config.broker_host,
            port=config.broker_port
        )
        self.idp_controller = IDPController(config)
        self.shaker_controller = ShakerController(config)
        self.running = False
        
        # 載入所有 table 配置
        self.table_configs = load_table_config()
        self.token = 'E5LN4END9Q'
        self.logger.info(f"Loaded {len(self.table_configs)} table configurations")
        
        self.ffmpeg_process = None
        self.stream_started = False
        
        # WebSocket 客戶端
        self.ws_client = None
        self.ws_connected = False

    async def initialize(self):
        """Initialize all controllers"""
        try:
            await self.mqtt_controller.initialize()
            await self.idp_controller.initialize()
            await self.shaker_controller.initialize()
            
            # 為 SicBo 遊戲設置 MQTT 控制器
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

    async def run_self_test(self):
        """Run self test for all components"""
        self.logger.info("Starting self test...")
        
        # 初始化所有控制器（只做一次）
        try:
            await self.mqtt_controller.initialize()
            await self.shaker_controller.initialize()
            await self.idp_controller.initialize()
            # 連接到錄製器
            await self.connect_to_recorder()
            self.logger.info("All controllers initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize controllers: {e}")
            return False

        while True:  # 無限循環執行回合
            try:
                # 檢查上一局的狀態
                self.logger.info("Checking previous round status...")
                try:
                    # 對所有 table 檢查狀態
                    for table in self.table_configs:
                        get_url = f"{table['get_url']}{table['game_code']}"
                        round_id, status, bet_period = get_roundID(get_url, self.token)
                        self.logger.info(f"Table {table['name']} - round_id: {round_id}, status: {status}, bet_period: {bet_period}")
                        
                        # 如果上一局停在 bet-stopped，需要先完成該局
                        if status == "bet-stopped":
                            self.logger.info(f"Detected incomplete previous round for {table['name']}, cleaning up...")
                            post_url = f"{table['post_url']}{table['game_code']}"
                            resume_post(post_url, self.token)
                            cancel_post(post_url, self.token)
                            self.logger.info(f"Previous round cleanup completed for {table['name']}")
                            await asyncio.sleep(2)  # 等待系統處理
                except Exception as e:
                    self.logger.error(f"Error checking previous round: {e}")
                    await asyncio.sleep(5)
                    continue

                # 開始新的一局
                self.logger.info("Starting new round...")
                round_start_time = time.time()
                
                # 對所有 table 發送 start 請求
                round_ids = []
                for table in self.table_configs:
                    post_url = f"{table['post_url']}{table['game_code']}"
                    round_id, bet_period = start_post(post_url, self.token)
                    if round_id != -1:
                        round_ids.append((table, round_id, bet_period))
                        self.logger.info(f"Started round {round_id} for {table['name']} with bet period {bet_period}")
                
                if not round_ids:
                    self.logger.error("Failed to start round on any table")
                    await asyncio.sleep(5)
                    continue
                
                # # 通知錄製器開始錄製
                # if round_ids:
                #     # 使用第一個 table 的 round_id 作為錄製標識
                #     first_table, first_round_id, _ = round_ids[0]
                #     await self.send_to_recorder(f"start_recording:{first_round_id}")
                
                # 等待下注時間
                betting_duration = 7 # bet_period + 0.5 - 4 - 4 - 2
                self.logger.info(f"Waiting for betting period ({betting_duration:.1f} seconds)...")
                time.sleep(betting_duration)

                # 通知錄製器開始錄製
                if round_ids:
                    # 使用第一個 table 的 round_id 作為錄製標識
                    first_table, first_round_id, _ = round_ids[0]
                    await self.send_to_recorder(f"start_recording:{first_round_id}")

                # 測試搖骰器命令
                SHAKE_TIME = 7
                self.logger.info(f"Testing shake command with round ID: {first_round_id}")
                await self.shaker_controller.shake(first_round_id)
                await asyncio.sleep(SHAKE_TIME+0.5)

                # 測試偵測命令
                max_retries = 3
                retry_count = 0
                
                while retry_count < max_retries:
                    self.logger.info(f"Testing detect command... (attempt {retry_count + 1})")
                    
                    # For testing broadcast, comment out the following line
                    # success, dice_result = self.idp_controller.detect(first_round_id)
                    
                    # is_valid_result = (
                    #     success and 
                    #     dice_result and 
                    #     isinstance(dice_result, list) and 
                    #     all(isinstance(x, int) and x > 0 for x in dice_result)
                    # )

                    # for testing broadcast
                    success = False
                    dice_result = [1,2]
                    is_valid_result = False

                    if is_valid_result:
                        self.logger.info(f"Sending dice result to all tables: {dice_result}")
                        deal_time = time.time()
                        start_to_deal_time = deal_time - round_start_time
                        self.logger.info(f"Start to deal time: {start_to_deal_time:.1f} seconds")

                        # 通知錄製器停止錄製
                        await self.send_to_recorder("stop_recording")

                        # 對所有 table 發送 deal 和 finish 請求
                        for table, round_id, _ in round_ids:
                            post_url = f"{table['post_url']}{table['game_code']}"
                            deal_post(post_url, self.token, round_id, dice_result)

                        time.sleep(3)

                        for table, round_id, _ in round_ids:
                            post_url = f"{table['post_url']}{table['game_code']}"
                            finish_post(post_url, self.token)
                            
                        # # 通知錄製器停止錄製
                        # await self.send_to_recorder("stop_recording")
                            
                        # 計算整個回合實際花費的時間
                        round_duration = time.time() - round_start_time
                        self.logger.info(f"Round completed for {table['name']} in {round_duration:.1f} seconds")
                        
                        # 如果回合完成時間少於預期，則等待剩餘時間
                        TOTAL_ROUND_TIME = 19
                        if round_duration < TOTAL_ROUND_TIME:
                            remaining_time = TOTAL_ROUND_TIME - round_duration
                            self.logger.info(f"Waiting {remaining_time:.1f} seconds to complete round for {table['name']}")
                            await asyncio.sleep(remaining_time)
                        
                        break  # 如果得到有效結果就跳出循環
                    
                    else:
                        self.logger.info("Invalid result received, retrying shake and detect...")
                        # 重新搖骰
                        for table in self.table_configs:
                            post_url = f"{table['post_url']}{table['game_code']}"
                            print("Send broadcast post")
                            broadcast_post(post_url, self.token, "dice.reroll", "players", 4)
                        
                        await self.shaker_controller.shake(first_round_id)
                        await asyncio.sleep(SHAKE_TIME+0.5)
                        retry_count += 1
                        if retry_count >= max_retries:
                            self.logger.error("Max retries reached, cancelling round")
                            for table, round_id, _ in round_ids:
                                post_url = f"{table['post_url']}{table['game_code']}"
                                cancel_post(post_url, self.token)
                            break

            except Exception as e:
                self.logger.error(f"Error in game round: {e}")
                await asyncio.sleep(5)

    async def start(self):
        """Start the game system"""
        self.logger.info(f"Starting SDP game system for {self.config.game_type}")
        self.running = True
        
        try:
            # Initialize all controllers
            await self.initialize()
            
            while self.running:
                # Start new round
                round_id = await self.start_game_round()
                if round_id:
                    await self.run_game_round(round_id)
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.error(f"Error in game system: {e}")
        finally:
            await self.cleanup()

    async def start_game_round(self) -> Optional[str]:
        """Start a new game round using LOS API"""
        round_id, bet_period = start_post(self.post_url, self.token)
        if round_id != -1:
            return round_id
        return None

    async def run_game_round(self, round_id: str):
        """Run a specific game round"""
        try:
            if self.config.game_type == GameType.SICBO:
                # Execute SicBo game round
                await self.game_controller.transition_to(SicBoState.START_GAME)
                await self.game_controller.handle_current_state()
                
                await self.game_controller.transition_to(SicBoState.PLACE_BET)
                await self.game_controller.handle_current_state()
                
                await self.game_controller.transition_to(SicBoState.SHAKE_DICE)
                await self.shaker_controller.shake(round_id)
                await self.game_controller.handle_current_state()
                
                await self.game_controller.transition_to(SicBoState.DETECT_RESULT)
                result = await self.idp_controller.detect(round_id)
                await self.game_controller.handle_current_state()
                
                await self.game_controller.transition_to(SicBoState.WINNING_NUMBER)
                await self.game_controller.handle_current_state()
                
            # Add other game types here as needed
            
        except Exception as e:
            self.logger.error(f"Error in game round {round_id}: {e}")
            if self.config.game_type == GameType.SICBO:
                await self.game_controller.transition_to(SicBoState.ERROR)
            await self.game_controller.handle_current_state()

    async def cleanup(self):
        """Cleanup all resources"""
        self.logger.info("Cleaning up resources")
        
        # 終止 FFmpeg 進程
        if self.ffmpeg_process:
            self.logger.info("Terminating FFmpeg stream...")
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=5)  # 等待進程終止
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()  # 如果無法正常終止，強制結束
            self.logger.info("FFmpeg stream terminated")
        
        # 關閉 WebSocket 連接
        if self.ws_client:
            try:
                await self.ws_client.close()
                self.logger.info("WebSocket connection closed")
            except Exception as e:
                self.logger.error(f"Error closing WebSocket connection: {e}")
        
        # 按照初始化的相反順序進行清理
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
    parser.add_argument('--self-test-only', action='store_true',
                      help='Run self test only and exit')
    # parser.add_argument('--broker', type=str, default='206.53.48.180',
    #                   help='MQTT broker address')
    parser.add_argument('--broker', type=str, default='192.168.88.213',
                      help='MQTT broker address')
    parser.add_argument('--port', type=int, default=1883,
                      help='MQTT broker port')
    parser.add_argument('--game-type', type=str, choices=['roulette', 'sicbo', 'blackjack'],
                      default='sicbo', help='Game type to run')
    parser.add_argument('--enable-logging', action='store_true',
                      help='Enable MQTT logging to file')
    parser.add_argument('--log-dir', type=str, default='../../../logs/sdp',
                      help='Directory for log files')
    
    args = parser.parse_args()

    # 設置日誌
    setup_logging(True, args.log_dir)  # 強制啟用日誌功能，並使用絕對路徑

    # 從 LOS API 獲取 SDP 配置
    try:
        sdp_config = get_sdp_config(url=args.get_url, token=args.token)
        # 使用 SDP 配置覆蓋默認值，但保留命令行參數的優先級
        broker = args.broker or sdp_config.get('broker_host')
        port = args.port or sdp_config.get('broker_port')
        room_id = sdp_config.get('room_id', "SDP-002")
        # 可以添加其他配置參數
    except Exception as e:
        logging.warning(f"Failed to get SDP config: {e}, using default values")
        broker = args.broker
        port = args.port
        room_id = "SDP-002"

    # 創建遊戲配置
    config = GameConfig(
        game_type=GameType(args.game_type),
        room_id=room_id,
        broker_host=broker,
        broker_port=port,
        enable_logging=args.enable_logging,
        log_dir=args.log_dir
    )

    # 創建遊戲實例
    game = SDPGame(config)

    try:
        if args.self_test_only:
            await game.run_self_test()
        else:
            if await game.initialize():
                await game.start()
    except KeyboardInterrupt:
        logging.info("Game interrupted by user")
    except Exception as e:
        logging.error(f"Game error: {e}")
    finally:
        await game.cleanup()

def main():
    """Entry point for the application"""
    asyncio.run(amain())

if __name__ == "__main__":
    main()
