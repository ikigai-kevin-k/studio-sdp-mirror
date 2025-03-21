import logging
import asyncio
from typing import Optional, Dict, List, Tuple
from transitions import Machine
from controller import BaseGameStateController, GameType, GameConfig, SicBoState
from proto.mqtt import MQTTConnector
from device.idp import IDPConnector

class ShakerConnector:
    """Controls dice shaker operations"""
    def __init__(self, config: GameConfig):
        self.config = config
        self.mqtt_client = MQTTConnector(
            client_id=f"shaker_controller_{config.room_id}",
            broker="192.168.88.250",  # Specific broker for shaker
            port=config.broker_port
        )
        self.mqtt_client.client.username_pw_set("PFC", "wago")  # Specific credentials for shaker
        self.logger = logging.getLogger("ShakerConnector")

    async def initialize(self):
        """Initialize shaker controller"""
        if not self.mqtt_client.connect():
            raise Exception("Failed to connect to MQTT broker")
        self.mqtt_client.start_loop()
        self.mqtt_client.subscribe("ikg/shaker/response")

    async def shake(self, round_id: str):
        """Shake the dice using Billy-II settings"""
        cmd = "/cycle/?pattern=0&parameter1=10&parameter2=0&amplitude=0.41&duration=6"
        topic = "ikg/sicbo/Billy-II/listens"
        
        self.mqtt_client.publish(topic, cmd)
        self.mqtt_client.publish(topic, "/state")
        self.logger.info(f"Shake command sent for round {round_id}")

    async def cleanup(self):
        """Cleanup shaker controller resources"""
        self.mqtt_client.stop_loop()
        self.mqtt_client.disconnect()

class DiceShakerController(BaseGameStateController):
    """Controls SicBo game state transitions with integrated shaker control"""
    
    states = [
        SicBoState.IDLE,
        SicBoState.WAITING_START,
        SicBoState.SHAKING,
        SicBoState.DETECTING,
        SicBoState.RESULT_READY,
        SicBoState.ERROR
    ]
    
    transitions = [
        {
            'trigger': 'start_game',
            'source': [SicBoState.IDLE, SicBoState.RESULT_READY],
            'dest': SicBoState.WAITING_START,
            'before': 'before_start_game'
        },
        {
            'trigger': 'start_shake',
            'source': SicBoState.WAITING_START,
            'dest': SicBoState.SHAKING,
            'before': 'before_shake'
        },
        {
            'trigger': 'start_detect',
            'source': SicBoState.SHAKING,
            'dest': SicBoState.DETECTING,
            'before': 'before_detect'
        },
        {
            'trigger': 'set_result',
            'source': SicBoState.DETECTING,
            'dest': SicBoState.RESULT_READY,
            'conditions': ['is_valid_result'],
            'before': 'before_set_result'
        },
        {
            'trigger': 'handle_error',
            'source': '*',
            'dest': SicBoState.ERROR,
            'before': 'before_error'
        }
    ]

    def __init__(self, config: GameConfig):
        super().__init__(GameType.SICBO)
        self.config = config
        self.logger = logging.getLogger("DiceShakerController")
        
        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=SicBoState.IDLE,
            auto_transitions=False,
            send_event=True
        )
        
        # Initialize device controllers
        self.mqtt = MQTTConnector(f"sicbo_controller_{config.room_id}", 
                                config.broker_host, 
                                config.broker_port)
        self.idp = IDPConnector(config)
        self.shaker = ShakerConnector(config)
        
        # Game state variables
        self.current_round_id: Optional[str] = None
        self.dice_result: Optional[List[int]] = None
        self.error_message: Optional[str] = None

    async def initialize(self):
        """Initialize all controllers"""
        try:
            await self.mqtt.initialize()
            await self.idp.initialize()
            await self.shaker.initialize()
            self.logger.info("All controllers initialized successfully")
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise

    def before_start_game(self, event):
        """Actions before starting new game"""
        self.current_round_id = None
        self.dice_result = None
        self.error_message = None

    def before_shake(self, event):
        """Actions before shaking dice"""
        self.current_round_id = event.kwargs.get('round_id')

    async def before_detect(self, event):
        """Actions before detecting dice"""
        await asyncio.sleep(self.config.get('shake_duration', 7))

    def before_set_result(self, event):
        """Actions before setting result"""
        self.dice_result = event.kwargs.get('result')

    def before_error(self, event):
        """Actions before entering error state"""
        self.error_message = event.kwargs.get('error', 'Unknown error')
        self.logger.error(f"Error occurred: {self.error_message}")

    def is_valid_result(self, event) -> bool:
        """Validate dice detection result"""
        result = event.kwargs.get('result')
        return (isinstance(result, list) and 
                len(result) == 3 and 
                all(isinstance(x, int) and 1 <= x <= 6 for x in result))

    async def run_game_round(self) -> bool:
        """Run a complete game round"""
        try:
            # Start new game round
            self.start_game()
            
            # Start shaking
            self.start_shake(round_id=self.current_round_id)
            await self.shaker.shake(self.current_round_id)
            
            # Start detection
            self.start_detect()
            success, result = await self.idp.detect(self.current_round_id)
            
            if success and result:
                self.set_result(result=result)
                return True
            else:
                self.handle_error(error="Detection failed")
                return False
                
        except Exception as e:
            self.handle_error(error=str(e))
            return False

    async def start(self):
        """Start the dice shaker controller"""
        self.logger.info("Starting Dice Shaker controller")
        while True:
            try:
                await self.run_game_round()
                await asyncio.sleep(self.config.get('result_duration', 4))
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Game round error: {e}")
                await asyncio.sleep(1)

    async def cleanup(self):
        """Cleanup all resources"""
        await self.mqtt.cleanup()
        await self.idp.cleanup()
        await self.shaker.cleanup()
