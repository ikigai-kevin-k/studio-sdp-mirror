import asyncio
import logging
import json
import argparse
from controller import GameType, GameConfig
from device.dice_shaker import DiceShakerController
from device.roulette import RealRouletteController
from device.blackjack import BlackJackStateController
from logger import setup_logging, get_logger, ColorfulLogger
from utils import load_config

# 定義遊戲類型與配置文件的對應關係
GAME_CONFIG_MAPPING = {
    'sicbo': 'conf/sicbo_auto.json',
    'roulette_speed': 'conf/roulette_auto_speed.json',
    'roulette_vip': 'conf/roulette_auto_vip.json',
    'blackjack': 'conf/blackjack.json'
}

class GameRunner:
    """Game runner class to manage different game types"""
    def __init__(self, game_type: str, config_path: str):
        self.game_type = game_type
        self.config = load_config(config_path)
        self.logger = ColorfulLogger('GameRunner')  # 使用 ColorfulLogger
        self.controller = None

    async def initialize(self):
        """Initialize game controller based on game type"""
        try:
            # 設置日誌
            setup_logging(
                self.config.get('enable_logging', True),
                self.config.get('log_dir', 'logs')
            )

            # 創建遊戲配置
            game_config = GameConfig(
                game_type=self._get_game_type(),
                room_id=self.config.get('room', {}).get('id') or self.config.get('room_id'),
                broker_host=self.config.get('broker', {}).get('host') or self.config.get('broker_host'),
                broker_port=self.config.get('broker', {}).get('port') or self.config.get('broker_port'),
                enable_logging=self.config.get('enable_logging', True),
                log_dir=self.config.get('log_dir', 'logs'),
                port=self.config.get('port', '/dev/ttyUSB0'),
                baudrate=self.config.get('baudrate', 9600)
            )

            # 創建對應的遊戲控制器
            self.controller = self._create_controller(game_config)
            if not self.controller:
                raise Exception(f"Failed to create controller for game type: {self.game_type}")

            # 初始化控制器
            await self.controller.initialize()
            return True

        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            return False

    def _get_game_type(self) -> GameType:
        """Get GameType enum based on game type string"""
        game_type_mapping = {
            'sicbo': GameType.SICBO,
            'roulette_speed': GameType.ROULETTE,
            'roulette_vip': GameType.ROULETTE,
            'blackjack': GameType.BLACKJACK
        }
        return game_type_mapping[self.game_type]

    def _create_controller(self, game_config: GameConfig):
        """Create appropriate game controller"""
        try:
            if self.game_type.startswith('roulette'):
                return RealRouletteController(self.logger, game_config)
            elif self.game_type == 'sicbo':
                return DiceShakerController(game_config)  # 更新為新的控制器名稱
            elif self.game_type == 'blackjack':
                return BlackJackStateController(game_config)
            return None
        except Exception as e:
            self.logger.error(f"Failed to create controller: {e}")
            raise

    async def run(self):
        """Run the game"""
        try:
            if not self.controller:
                raise Exception("Controller not initialized")

            self.logger.info(f"Starting {self.game_type} game...")
            await self.controller.start()

        except KeyboardInterrupt:
            self.logger.info("Game interrupted by user")
        except Exception as e:
            self.logger.error(f"Game error: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        if self.controller:
            self.logger.info("Cleaning up resources...")
            await self.controller.cleanup()

async def amain():
    """Async main function"""
    parser = argparse.ArgumentParser(description='SDP Game System')
    parser.add_argument('--game-type', type=str, 
                       choices=['sicbo', 'roulette_speed', 'roulette_vip', 'blackjack'],
                       required=True, help='Game type to run')
    parser.add_argument('--config', type=str, help='Optional custom config file path')
    
    args = parser.parse_args()
    
    # 決定使用哪個配置文件
    config_file = args.config if args.config else GAME_CONFIG_MAPPING[args.game_type]
    
    # 創建並運行遊戲
    runner = GameRunner(args.game_type, config_file)
    if await runner.initialize():
        await runner.run()
    else:
        logging.error("Failed to initialize game runner")
        return 1
    return 0

def main():
    """Entry point for the application"""
    try:
        exit_code = asyncio.run(amain())
        exit(exit_code)
    except KeyboardInterrupt:
        logging.info("Application terminated by user")
        exit(0)
    except Exception as e:
        logging.error(f"Application error: {e}")
        exit(1)

if __name__ == "__main__":
    main()
