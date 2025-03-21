import logging
import asyncio
import time
import random
import serial
import threading
import json
from typing import Dict, Optional, Any
from controller import BaseGameStateController, GameType, RouletteState
from utils import log_with_color, RED, GREEN, BLUE, YELLOW, MAGENTA, RESET, check_serial_port, setup_serial_port, check_los_state
from los_api.api import start_post, deal_post, finish_post, cancel_post
from logger import ColorfulLogger
from proto.rs232 import SerialController
from transitions import Machine

class RouletteStateController(BaseGameStateController):
    """Controls Roulette game state transitions"""
    
    # Define state transition waiting times
    P1_MAX_WAITING_TIME = 2
    P0_MAX_WAITING_TIME = 2
    P0_MAX_DELAY = 5
    LOG_FREQUENCY = 0.1
    
    def __init__(self):
        super().__init__(GameType.ROULETTE)
        self.logger = logging.getLogger("RouletteStateController")
        
        # Game state related
        self.current_round_id = None
        self.current_result = None
        self.is_running = False
        self.bet_time = 0
        self.start_time = None
        
        # Serial port related
        self.current_data_protocol_mode = "unknown"
        self.current_power_state = "off"
        self.p0_delay_counter = 0
        self.masterRoulettePort = None
        self.line_number = 1

    def _initialize_state(self):
        """Initialize Roulette state"""
        self.current_state = RouletteState.TABLE_CLOSED
        self.start_time = time.time()

    def _setup_state_handlers(self) -> Dict:
        """Setup Roulette state handlers"""
        return {
            RouletteState.TABLE_CLOSED: self._handle_table_closed,
            RouletteState.START_GAME: self._handle_start_game,
            RouletteState.PLACE_BET: self._handle_place_bet,
            RouletteState.NO_MORE_BET: self._handle_no_more_bet,
            RouletteState.WINNING_NUMBER: self._handle_winning_number,
            RouletteState.ERROR: self._handle_error
        }

    async def _handle_table_closed(self):
        """Handle table closed state"""
        self.logger.info("Table is closed")
        await asyncio.sleep(self.P0_MAX_WAITING_TIME)
        self.transition_to(RouletteState.START_GAME)

    async def _handle_start_game(self):
        """Handle start game state"""
        self.logger.info("Starting new game round")
        self.start_time = time.time()
        self.bet_time = 0
        await asyncio.sleep(self.P1_MAX_WAITING_TIME)
        self.transition_to(RouletteState.PLACE_BET)

    async def _handle_place_bet(self):
        """Handle place bet state"""
        self.logger.info("Place your bets")
        # Calculate betting time
        current_time = time.time()
        self.bet_time = current_time - self.start_time
        
        # Check if exceeded maximum betting time
        if self.bet_time >= self.P0_MAX_DELAY:
            self.transition_to(RouletteState.NO_MORE_BET)
        else:
            await asyncio.sleep(0.1)  # Short wait before checking again

    async def _handle_no_more_bet(self):
        """Handle no more bet state"""
        self.logger.info("No more bets!")
        await asyncio.sleep(self.P1_MAX_WAITING_TIME)
        
        # Simulate roulette spin and ball drop
        self.current_result = self._simulate_roulette_spin()
        self.transition_to(RouletteState.WINNING_NUMBER)

    async def _handle_winning_number(self):
        """Handle winning number state"""
        self.logger.info(f"Winning number is {self.current_result}")
        await asyncio.sleep(self.P1_MAX_WAITING_TIME)
        
        # If game is still running, start new round
        if self.is_running:
            self.transition_to(RouletteState.START_GAME)
        else:
            self.transition_to(RouletteState.TABLE_CLOSED)

    async def _handle_error(self):
        """Handle error state"""
        self.logger.error("Error occurred in roulette game")
        await asyncio.sleep(self.P1_MAX_WAITING_TIME)
        self.transition_to(RouletteState.TABLE_CLOSED)

    def _simulate_roulette_spin(self) -> int:
        """Simulate roulette wheel spin"""
        return random.randint(0, 36)

    def transition_to(self, new_state):
        """Transition to a new Roulette state"""
        if not isinstance(new_state, RouletteState):
            raise ValueError(f"Invalid state {new_state} for Roulette game")
        
        old_state = self.current_state
        self.current_state = new_state
        self.logger.info(f"State transition: {old_state} -> {new_state}")

    async def start(self, round_id: str):
        """Start the roulette game"""
        self.is_running = True
        self.current_round_id = round_id
        self.transition_to(RouletteState.START_GAME)

    async def stop(self):
        """Stop the roulette game"""
        self.is_running = False
        self.transition_to(RouletteState.TABLE_CLOSED)

    async def cleanup(self):
        """Cleanup resources"""
        self.is_running = False
        self.current_round_id = None
        self.current_result = None
        self.logger.info("Roulette game cleaned up")

class RealRouletteController(BaseGameStateController):
    """Controls Roulette game state transitions"""
    
    states = [
        RouletteState.IDLE,
        RouletteState.WAITING_START,
        RouletteState.SPINNING,
        RouletteState.RESULT_READY,
        RouletteState.ERROR
    ]
    
    transitions = [
        {
            'trigger': 'start_game',
            'source': [RouletteState.IDLE, RouletteState.RESULT_READY],
            'dest': RouletteState.WAITING_START,
            'before': 'before_start_game'
        },
        {
            'trigger': 'start_spin',
            'source': RouletteState.WAITING_START,
            'dest': RouletteState.SPINNING,
            'before': 'before_spin'
        },
        {
            'trigger': 'set_result',
            'source': RouletteState.SPINNING,
            'dest': RouletteState.RESULT_READY,
            'conditions': ['is_valid_result'],
            'before': 'before_set_result'
        },
        {
            'trigger': 'handle_error',
            'source': '*',
            'dest': RouletteState.ERROR,
            'before': 'before_error'
        }
    ]

    def __init__(self, logger: ColorfulLogger, config: Dict[str, Any]):
        super().__init__(GameType.ROULETTE)
        self.logger = logger
        self.config = config
        
        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=RouletteState.IDLE,
            auto_transitions=False,
            send_event=True
        )
        
        # Initialize serial controller
        self.serial = SerialController(
            port=config.get('port', '/dev/ttyUSB0'),
            baudrate=config.get('baudrate', 9600)
        )
        
        # Game state variables
        self.round_id: Optional[str] = None
        self.win_num: Optional[int] = None
        self.error_message: Optional[str] = None
        self.x2_count = 0
        self.x5_count = 0
        self.last_x2_time = 0
        self.last_x5_time = 0
        self.start_post_sent = False
        
        # LOS API configuration
        self.post_url = config['los']['post_url_template'].format(game_code=config['room_id'])
        self.get_url = config['los']['get_url_template'].format(game_code=config['room_id'])
        self.token = config['los']['token']

    async def initialize(self):
        """Initialize controller"""
        if not self.serial.initialize():
            raise Exception("Failed to initialize serial port")
            
        self.serial.start_reading(self.handle_serial_data)
        await self._initialize_machine_config()

    async def _initialize_machine_config(self):
        """Initialize machine configuration"""
        machine_config = self.config.get('machine_config', {})
        
        # Set wheel speed
        wheel_speed = machine_config.get('common', {}).get('wheel_speed')
        if wheel_speed:
            self.serial.write(f"*T S {wheel_speed}")
            
        # Set other parameters
        specific = machine_config.get('specific', {})
        if specific.get('gph'):
            self.serial.write(f"*T H {specific['gph']}")
        if specific.get('deceleration_distance'):
            self.serial.write(f"*T T {specific['deceleration_distance']}")
        if specific.get('in_rim_jet_duration'):
            self.serial.write(f"*T R {specific['in_rim_jet_duration']}")

    def handle_serial_data(self, data: str):
        """Handle received serial data"""
        self.logger.log_serial_data(data)
        
        if "*X;2" in data:
            self._handle_x2_signal()
        elif "*X;5" in data:
            self._handle_x5_signal(data)

    def _handle_x2_signal(self):
        """Handle X2 signal (game start)"""
        current_time = time.time()
        if current_time - self.last_x2_time > 5:
            self.x2_count = 1
        else:
            self.x2_count += 1
        self.last_x2_time = current_time
        
        if self.x2_count >= 2 and not self.start_post_sent:
            self.start_game()

    def _handle_x5_signal(self, data: str):
        """Handle X5 signal (game result)"""
        current_time = time.time()
        if current_time - self.last_x5_time > 5:
            self.x5_count = 1
        else:
            self.x5_count += 1
        self.last_x5_time = current_time
        
        if self.x5_count >= 5:
            self._process_game_result(data)

    def before_start_game(self, event):
        """Actions before starting new game"""
        self.round_id = None
        self.win_num = None
        self.error_message = None
        self._start_new_game()

    def before_spin(self, event):
        """Actions before spinning wheel"""
        self.start_post_sent = True

    def before_set_result(self, event):
        """Actions before setting result"""
        self.win_num = event.kwargs.get('win_num')

    def before_error(self, event):
        """Actions before entering error state"""
        self.error_message = event.kwargs.get('error', 'Unknown error')
        self.logger.log_with_color(f"Error occurred: {self.error_message}", RED)

    def is_valid_result(self, event) -> bool:
        """Validate roulette result"""
        win_num = event.kwargs.get('win_num')
        return isinstance(win_num, int) and 0 <= win_num <= 36

    async def _start_new_game(self):
        """Start new game round"""
        try:
            self.round_id, bet_period = start_post(self.post_url, self.token)
            if self.round_id != -1:
                self.start_post_sent = True
                self.logger.log_with_color(f"Started new game round: {self.round_id}", GREEN)
            else:
                self.logger.log_with_color("Failed to start game", RED)
        except Exception as e:
            self.logger.log_with_color(f"Start game error: {e}", RED)

    async def _process_game_result(self, data: str):
        """Process game result"""
        try:
            parts = data.split(';')
            if len(parts) >= 4:
                win_num = int(parts[3])
                self.set_result(win_num=win_num)
                self.logger.log_with_color(f"Winning number: {win_num}", GREEN)
                
                # Reset for next game
                self.start_post_sent = False
                self.x2_count = 0
                self.x5_count = 0
                
        except Exception as e:
            self.handle_error(error=str(e))

    async def start(self):
        """Start the roulette controller"""
        self.logger.info("Starting Roulette controller")
        while True:
            try:
                if self.state == RouletteState.ERROR:
                    await asyncio.sleep(5)
                    self.start_game()
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Game round error: {e}")
                self.handle_error(error=str(e))

    async def cleanup(self):
        """Cleanup resources"""
        if self.serial:
            self.serial.cleanup()
