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

from controller import GameType, GameConfig, create_game_state_controller
from device.idp import IDPConnector
from device.dice_shaker import ShakerConnector
from proto.mqtt import MQTTConnector
from los.api import start_post, deal_post, finish_post, visibility_post, get_roundID, resume_post, get_sdp_config, cancel_post
from logger import setup_logging, get_logger
from utils import load_config
from device.roulette import RealRouletteController

########################################################
# [v] move configure log to utils
########################################################
# Configure logging
logger = get_logger(__name__)

class SDP:
    """Main game class for SDP"""
    def __init__(self, config: GameConfig):
        self.config = config
        self.logger = logging.getLogger("SDP")
        
        # Initialize controllers
        self.game_controller = create_game_state_controller(config.game_type)
        self.mqtt_controller = MQTTConnector(
            client_id=f"sdp_controller_{config.room_id}",
            broker=config.broker_host,
            port=config.broker_port
        )
        self.idp_controller = IDPConnector(config)
        self.shaker_controller = ShakerConnector(config)
        self.running = False
        
        # Load LOS API configuration from sicbo_auto.json
        with open('conf/sicbo_auto.json', 'r') as f:
            self.game_config = json.load(f)
        
        # LOS API configuration
        self.game_code = config.room_id
        self.token = self.game_config['los']['token']
        self.get_url = self.game_config['los']['get_url_template'].format(game_code=self.game_code)
        self.post_url = self.game_config['los']['post_url_template'].format(game_code=self.game_code)

    ########################################################
    # TODO: wrap initialize to start()
    ########################################################
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
    ########################################################
    # TODO: wrap run_self_test to start() and rename as run_game_round() in start()
    ########################################################
    async def run_game_round(self):
        """Run self test for all components"""
        self.logger.info("Starting self test...")
        
        # 初始化所有控制器（只做一次）
        ########################################################
        # TODO: move self.mqtt_controller.initialize() to initialize() in start()
        # TODO: move self.shaker_controller.initialize() to initialize() in start()
        # TODO: move self.idp_controller.initialize() to initialize() in start()
        ########################################################

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
                ########################################################
                # TODO: wrap check previous round to check_previous_round() in start()
                ########################################################
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

                ########################################################
                # TODO: wrap start new round to start_game_round() in start()
                ########################################################
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
                
            except Exception as e:
                self.logger.error(f"Error in game round: {e}")
                await asyncio.sleep(5)

    async def start_game_round(self) -> Optional[str]:
        """Start a new game round using LOS API"""
        round_id, bet_period = start_post(self.post_url, self.token)
        if round_id != -1:
            return round_id
        return None

    async def cleanup(self):
        """Cleanup all resources"""
        self.logger.info("Cleaning up resources")
        

        
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
    parser = argparse.ArgumentParser(description='SDP Game System')
    parser.add_argument('--config', type=str, default='conf/roulette_auto_speed.json',
                      help='Path to configuration file')
    parser.add_argument('--game-type', type=str, choices=['roulette', 'sicbo', 'blackjack'],
                      default='roulette', help='Game type to run')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_data = load_config(args.config)
        
        # Setup logging
        setup_logging(config_data.get('enable_logging', True), 
                     config_data.get('log_dir', 'logs'))
        
        logger = get_logger('main')
        
        # Create game configuration
        game_config = GameConfig(
            game_type=GameType(args.game_type),
            room_id=config_data['room_id'],
            broker_host=config_data['broker_host'],
            broker_port=config_data['broker_port'],
            enable_logging=config_data['enable_logging'],
            log_dir=config_data['log_dir'],
            port=config_data['port'],
            baudrate=config_data['baudrate']
        )
        
        # Create and start game controller
        if game_config.game_type == GameType.ROULETTE:
            controller = RealRouletteController(logger, game_config.port, game_config.baudrate)
            await controller.start()
        else:
            logger.error(f"Unsupported game type: {game_config.game_type}")
            
    except KeyboardInterrupt:
        logger.info("Game interrupted by user")
    except Exception as e:
        logger.error(f"Game error: {e}")
    finally:
        if 'controller' in locals():
            await controller.cleanup()

def main():
    """Entry point for the application"""
    asyncio.run(amain())

if __name__ == "__main__":
    main()
