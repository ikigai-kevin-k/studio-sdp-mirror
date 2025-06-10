import asyncio
import logging
import json
import argparse
from transitions import Machine
from controller import GameType, GameConfig
from device.dice_shaker import DiceShakerController
from device.roulette import RealRouletteController
from device.blackjack import BlackJackStateController
from logger import setup_logging, get_logger, ColorfulLogger
from utils import load_config

# 定義遊戲類型與配置文件的對應關係
GAME_CONFIG_MAPPING = {
    'sicbo': 'conf/sicbo_auto.json',
    'roulette_speed': 'conf/roulette_machine_speed.json',
    'roulette_vip': 'conf/roulette_machine_vip.json',
    'blackjack': 'conf/blackjack_machine.json'
}

class MainState:
    """Main program states"""
    INITIALIZING = 'initializing'
    RUNNING = 'running'
    ERROR = 'error'
    STOPPING = 'stopping'
    STOPPED = 'stopped'

class GameRunner:
    """Game runner class with state machine"""
    
    states = [
        MainState.INITIALIZING,
        MainState.RUNNING,
        MainState.ERROR,
        MainState.STOPPING,
        MainState.STOPPED
    ]
    
    transitions = [
        {
            'trigger': 'start_init',
            'source': '*',
            'dest': MainState.INITIALIZING,
            'before': 'before_init'
        },
        {
            'trigger': 'start_running',
            'source': MainState.INITIALIZING,
            'dest': MainState.RUNNING,
            'conditions': ['is_initialized'],
            'before': 'before_running'
        },
        {
            'trigger': 'handle_error',
            'source': '*',
            'dest': MainState.ERROR,
            'before': 'before_error'
        },
        {
            'trigger': 'start_stopping',
            'source': [MainState.RUNNING, MainState.ERROR],
            'dest': MainState.STOPPING,
            'before': 'before_stopping'
        },
        {
            'trigger': 'complete_stop',
            'source': MainState.STOPPING,
            'dest': MainState.STOPPED,
            'before': 'before_complete_stop'
        }
    ]

    def __init__(self, game_type: str, config_path: str):
        self.game_type = game_type
        self.config_path = config_path
        self.config = None
        self.logger = ColorfulLogger('GameRunner')
        self.controller = None
        self.error_message = None
        self.initialized = False
        
        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=MainState.INITIALIZING,
            auto_transitions=False,
            send_event=True
        )

    def before_init(self, event):
        """Actions before initialization"""
        self.logger.info(f"Initializing {self.game_type} game system...")
        self.initialized = False
        self.error_message = None

    def before_running(self, event):
        """Actions before running"""
        self.logger.info(f"Starting {self.game_type} game...")

    def before_error(self, event):
        """Actions before error state"""
        self.error_message = event.kwargs.get('error', 'Unknown error')
        self.logger.error(f"Error occurred: {self.error_message}")

    def before_stopping(self, event):
        """Actions before stopping"""
        self.logger.info("Stopping game system...")

    def before_complete_stop(self, event):
        """Actions before complete stop"""
        self.logger.info("Game system stopped")

    def is_initialized(self, event) -> bool:
        """Check if system is properly initialized"""
        return self.initialized and self.controller is not None

    async def initialize(self) -> bool:
        """Initialize game system"""
        try:
            # Load configuration
            self.config = load_config(self.config_path)
            
            # Setup logging
            setup_logging(
                self.config.get('enable_logging', True),
                self.config.get('log_dir', 'logs')
            )

            # Create game configuration
            game_config = GameConfig(
                game_type=self._get_game_type(),
                room_id=self.config.get('room', {}).get('id') or self.config.get('room_id'),
                broker_host=self.config.get('broker', {}).get('host') or self.config.get('broker_host'),
                broker_port=self.config.get('broker', {}).get('port') or self.config.get('broker_port'),
                enable_logging=self.config.get('enable_logging', True),
                log_dir=self.config.get('log_dir', 'logs/sdp'),
                port=self.config.get('port', '/dev/ttyUSB0'),
                baudrate=self.config.get('baudrate', 9600)
            )

            # Create and initialize game controller
            self.controller = self._create_controller(game_config)
            if not self.controller:
                raise Exception(f"Failed to create controller for game type: {self.game_type}")

            await self.controller.initialize()
            self.initialized = True
            self.start_running()
            return True

        except Exception as e:
            self.handle_error(error=str(e))
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
                return DiceShakerController(game_config)
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

            await self.controller.start()

        except KeyboardInterrupt:
            self.logger.info("Game interrupted by user")
            await self.stop()
        except Exception as e:
            self.handle_error(error=str(e))
        finally:
            await self.cleanup()

    async def stop(self):
        """Stop the game system"""
        self.start_stopping()
        await self.cleanup()
        self.complete_stop()

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
