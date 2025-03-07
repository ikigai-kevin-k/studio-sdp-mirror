import logging
import asyncio
import time
import random
from typing import Dict
from controller import BaseGameStateController, GameType, RouletteState
from utils import log_with_color, RED, GREEN, BLUE, YELLOW, MAGENTA, RESET

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
