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

from controller import GameType, GameConfig
from gameStateController import create_game_state_controller
from deviceController import IDPController, ShakerController
from mqttController import MQTTController
from los_api.api import start_post, deal_post, finish_post, visibility_post, get_roundID, resume_post, get_sdp_config, cancel_post

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
        log_file = os.path.join(log_dir, f'sdp_game_{time.strftime("%Y%m%d_%H%M%S")}.log')
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
        
        # LOS API configuration - 修改為與 mqtt_sdp_client.py 一致的設定
        self.game_code = config.room_id
        self.token = 'E5LN4END9Q'
        # 修改 URL 設定，分別設定 get 和 post 的 URL
        self.get_url = f'https://crystal-los.iki-cit.cc/v1/service/table/{self.game_code}'
        self.post_url = f'https://crystal-los.iki-cit.cc/v1/service/sdp/table/{self.game_code}'
        self.ffmpeg_process = None
        self.stream_started = False

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

    async def run_self_test(self):
        """Run self test for all components"""
        self.logger.info("Starting self test...")
        
        # 初始化所有控制器（只做一次）
        try:
            await self.mqtt_controller.initialize()
            await self.shaker_controller.initialize()
            await self.idp_controller.initialize()
            self.logger.info("All controllers initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize controllers: {e}")
            return False

        while True:  # 無限循環執行回合
            try:
                # 檢查上一局的狀態
                self.logger.info("Checking previous round status...")
                try:
                    round_id, status, bet_period = get_roundID(self.get_url, self.token)
                    self.logger.info(f"round_id: {round_id}, status: {status}, bet_period: {bet_period}")
                    
                    # 如果上一局停在 bet-stopped，需要先完成該局
                    if status == "bet-stopped":
                        self.logger.info("Detected incomplete previous round, cleaning up...")
                        resume_post(self.post_url, self.token)
                        # deal_post(self.post_url, self.token, round_id, [""])
                        # finish_post(self.post_url, self.token)
                        cancel_post(self.post_url, self.token)
                        self.logger.info("Previous round cleanup completed")
                        await asyncio.sleep(2)  # 等待系統處理
                except Exception as e:
                    self.logger.error(f"Error checking previous round: {e}")
                    await asyncio.sleep(5)
                    continue

                # 在第一次循環時啟動 FFmpeg 串流
                # if not self.stream_started:
                #     self.logger.info("Starting FFmpeg stream...")
                #     try:
                #         ffmpeg_command = [
                #             "../../FFmpeg/ffmpeg",
                #             "-re",
                #             "-stream_loop", "-1",
                #             "-i", "runbillyrun_020208.mp4",
                #             "-c:v", "libx264",
                #             "-preset", "veryfast",
                #             "-b:v", "3000k",
                #             "-maxrate", "3000k",
                #             "-bufsize", "6000k",
                #             "-pix_fmt", "yuv420p",
                #             "-g", "50",
                #             "-c:a", "aac",
                #             "-b:a", "128k",
                #             "-ar", "44100",
                #             "-f", "flv",
                #             "rtmp://192.168.88.213:1935/live/r1234_dice"
                #         ]
                #         self.ffmpeg_process = subprocess.Popen(
                #             ffmpeg_command,
                #             stdout=subprocess.PIPE,
                #             stderr=subprocess.PIPE
                #         )
                #         self.stream_started = True
                #         self.logger.info("FFmpeg stream started successfully")
                #     except Exception as e:
                #         self.logger.error(f"Failed to start FFmpeg stream: {e}")

                # 開始新的回合
                round_start_time = time.time()  # 記錄回合開始時間

                self.logger.info("Starting new round...")
                round_id, bet_period = start_post(self.post_url, self.token)
                self.logger.info(f"round_id: {round_id}, bet_period: {bet_period}")

                if round_id == -1:
                    self.logger.error("Failed to start new round")
                    await asyncio.sleep(5)
                    continue

                self.logger.info(f"LOS API connection test: OK, round_id: {round_id}")
                
                # 計算已經過的時間
                elapsed_time = time.time() - round_start_time
                
                # 分配剩餘時間
                TOTAL_ROUND_TIME = 19  # 總回合時間為19秒
                LIGHT_TIME = 2
                SHAKE_TIME = 7  # 搖骰子固定需要4秒
                WAIT_STOP_TIME = 2  # 偵測固定需要1秒
                
                # 計算下注時間（總時間減去搖骰和偵測的時間，再預留1秒給其他操作）
                # betting_duration = max(0, TOTAL_ROUND_TIME - SHAKE_TIME - DETECT_TIME - 1 - elapsed_time)
                # betting_duration = bet_period # 12
                betting_duration = bet_period - 4
                self.logger.info(f"Waiting for betting period ({betting_duration:.1f} seconds)...")
                time.sleep(betting_duration)

                # 測試搖骰器命令
                self.logger.info(f"Testing shake command with round ID: {round_id}")
                await self.shaker_controller.shake(round_id)
                await asyncio.sleep(SHAKE_TIME-LIGHT_TIME+WAIT_STOP_TIME+2)  # 固定等待搖骰時間

                # 測試偵測命令
                max_retries = 3  # 最大重試次數
                retry_count = 0
                
                while retry_count < max_retries:

                    self.logger.info(f"Testing detect command... (attempt {retry_count + 1})")
                    success, dice_result = self.idp_controller.detect(round_id)
                    
                    # 檢查 dice_result 是否為有效的結果
                    is_valid_result = (
                        success and 
                        dice_result and 
                        isinstance(dice_result, list) and 
                        all(isinstance(x, int) and x > 0 for x in dice_result)
                    )

                    if is_valid_result:
                        self.logger.info(f"Sending dice result to LOS: {dice_result}")
                        deal_post(self.post_url, self.token, round_id, dice_result)
                        finish_post(self.post_url, self.token)
                        # 計算整個回合實際花費的時間
                        round_duration = time.time() - round_start_time
                        self.logger.info(f"Round completed in {round_duration:.1f} seconds")
                        
                        # 如果回合完成時間少於預期，則等待剩餘時間
                        if round_duration < TOTAL_ROUND_TIME:
                            remaining_time = TOTAL_ROUND_TIME - round_duration
                            self.logger.info(f"Waiting {remaining_time:.1f} seconds to complete round")
                            await asyncio.sleep(remaining_time)
                        break  # 如果得到有效結果就跳出循環
                    
                    else:
                        self.logger.info("Invalid result received, retrying shake and detect...")
                        # 重新搖骰
                        await self.shaker_controller.shake(round_id)
                        await asyncio.sleep(SHAKE_TIME-LIGHT_TIME+WAIT_STOP_TIME+2)
                        retry_count += 1
                        if retry_count >= max_retries:
                            self.logger.error("Max retries reached, cancelling round")
                            cancel_post(self.post_url, self.token)
                            break

                # try:
                #     if is_valid_result:
                #         self.logger.info(f"Sending dice result to LOS: {dice_result}")
                #         deal_post(self.post_url, self.token, round_id, dice_result)
                #         finish_post(self.post_url, self.token)
                #     elif dice_result == [""]:
                #         dice_result = [0,0,0]
                #         self.logger.info(f"Sending dice result to LOS: {dice_result}")
                #         deal_post(self.post_url, self.token, round_id, dice_result)
                #         finish_post(self.post_url, self.token)
                #     else:
                #         self.logger.error(f"Invalid dice result: {dice_result}")
                #         cancel_post(self.post_url, self.token)
                # except Exception as e:
                #     self.logger.error(f"Error posting result to LOS: {e}")
                #     try:
                #         cancel_post(self.post_url, self.token)
                #     except Exception as cancel_error:
                #         self.logger.error(f"Error cancelling round: {cancel_error}")
                
                # # 計算整個回合實際花費的時間
                # round_duration = time.time() - round_start_time
                # self.logger.info(f"Round completed in {round_duration:.1f} seconds")
                
                # # 如果回合完成時間少於預期，則等待剩餘時間
                # if round_duration < TOTAL_ROUND_TIME:
                #     remaining_time = TOTAL_ROUND_TIME - round_duration
                #     self.logger.info(f"Waiting {remaining_time:.1f} seconds to complete round")
                #     await asyncio.sleep(remaining_time)
                
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
    parser.add_argument('--broker', type=str, default='206.53.48.180',
                      help='MQTT broker address')
    parser.add_argument('--port', type=int, default=1883,
                      help='MQTT broker port')
    parser.add_argument('--game-type', type=str, choices=['roulette', 'sicbo', 'blackjack'],
                      default='sicbo', help='Game type to run')
    parser.add_argument('--enable-logging', action='store_true',
                      help='Enable MQTT logging to file')
    parser.add_argument('--log-dir', type=str, default='logs',
                      help='Directory for log files')
    
    args = parser.parse_args()

    # 設置日誌
    setup_logging(args.enable_logging, args.log_dir)

    # 從 LOS API 獲取 SDP 配置
    try:
        sdp_config = get_sdp_config()
        # 使用 SDP 配置覆蓋默認值，但保留命令行參數的優先級
        broker = args.broker or sdp_config.get('broker_host')
        port = args.port or sdp_config.get('broker_port')
        room_id = sdp_config.get('room_id', "SDP-003")
        # 可以添加其他配置參數
    except Exception as e:
        logging.warning(f"Failed to get SDP config: {e}, using default values")
        broker = args.broker
        port = args.port
        room_id = "SDP-003"

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
