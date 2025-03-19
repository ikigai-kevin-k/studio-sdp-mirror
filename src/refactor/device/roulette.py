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
    def __init__(self, logger: ColorfulLogger, port='/dev/ttyUSB0', baudrate=9600):
        super().__init__(GameType.ROULETTE)
        self.logger = logger
        self.serial_port = None
        self.port = port
        self.baudrate = baudrate
        self.running = True
        
        # Game state variables
        self.win_num = None
        self.round_id = None
        self.current_state = RouletteState.TABLE_CLOSED
        self.power_state = "off"
        self.protocol_mode = "unknown"
        self.last_command = None
        
        # API configuration
        self.post_url = 'https://crystal-los.iki-cit.cc/v1/service/sdp/table/SDP-001'
        self.get_url = 'https://crystal-los.iki-cit.cc/v1/service/table/SDP-001'
        self.token = 'E5LN4END9Q'
        
        # State tracking flags
        self.u1_sent_success = False
        self.start_post_success = False
        self.x1_sequence_started = False
        self.is_processing_command = False
        
        # Command response tracking
        self.command_responses: Dict[str, Any] = {}
        self.expected_responses = {
            'U1': ['u1'],
            'X1': ['x1'],
            'P0': ['p0'],
            'P1': ['p1'],
            'G0': ['g0'],
            'S0': ['s0']
        }
        
        # Initialize serial port
        self.initialize_serial_port()

    def initialize_serial_port(self):
        """Initialize serial port connection"""
        if not check_serial_port(self.port):
            raise Exception(f"Serial port {self.port} is in use")
            
        self.serial_port = setup_serial_port(self.port, self.baudrate)
        self.logger.log_with_color(f"Successfully opened serial port {self.port}", GREEN)

    async def initialize_power_state(self):
        """Initialize power state of the roulette wheel"""
        await self.send_command('U1')
        await asyncio.sleep(1)
        if self.power_state == "off":
            await self.send_command('P1')
            await asyncio.sleep(2)

    def read_from_serial(self):
        """Read data from serial port"""
        while self.running:
            try:
                if self.serial_port and self.serial_port.in_waiting:
                    data = self.serial_port.readline().decode().strip()
                    if data:
                        self.logger.log_serial_data(data)
                        self.process_serial_data(data)
            except Exception as e:
                self.logger.log_with_color(f"Serial read error: {e}", RED)
            time.sleep(0.1)

    def process_serial_data(self, data: str):
        """Process incoming serial data"""
        try:
            # Log the received data
            self.logger.log_with_color(f"Received: {data}", BLUE)
            
            # Process different response types
            if data.startswith('u1'):
                self.u1_sent_success = True
                self.protocol_mode = "normal"
            elif data.startswith('p'):
                self.power_state = "on" if data == "p1" else "off"
            elif data.startswith('x1'):
                self.x1_sequence_started = True
            elif data.startswith('w'):
                # Process winning number
                self.win_num = int(data[1:])
                asyncio.create_task(self.handle_winning_number())
            
            # Update command response tracking
            if self.last_command and data in self.expected_responses.get(self.last_command, []):
                self.command_responses[self.last_command] = data
                self.is_processing_command = False
                
        except Exception as e:
            self.logger.log_with_color(f"Data processing error: {e}", RED)

    async def send_command(self, command: str):
        """Send command to serial port"""
        try:
            while self.is_processing_command:
                await asyncio.sleep(0.1)
            
            self.is_processing_command = True
            self.last_command = command
            
            self.logger.log_with_color(f"Sending command: {command}", YELLOW)
            self.serial_port.write(f"{command}\r\n".encode())
            
            # Wait for response
            timeout = 5
            start_time = time.time()
            while time.time() - start_time < timeout:
                if command in self.command_responses:
                    response = self.command_responses.pop(command)
                    self.is_processing_command = False
                    return response
                await asyncio.sleep(0.1)
            
            self.is_processing_command = False
            raise TimeoutError(f"Command {command} timed out")
            
        except Exception as e:
            self.is_processing_command = False
            self.logger.log_with_color(f"Send command error: {e}", RED)
            raise

    async def handle_winning_number(self):
        """Handle winning number result"""
        try:
            if self.win_num is not None and self.round_id:
                self.logger.log_with_color(f"Winning number: {self.win_num}", GREEN)
                await finish_post(self.post_url, self.token, self.round_id, self.win_num)
                self.win_num = None
                self.round_id = None
        except Exception as e:
            self.logger.log_with_color(f"Handle winning number error: {e}", RED)

    async def start_new_game(self):
        """Start a new game round"""
        try:
            status, round_id, message = await check_los_state(self.get_url, self.token)
            if status == 200:
                self.round_id = round_id
                await start_post(self.post_url, self.token, round_id)
                await self.send_command('X1')
                self.logger.log_with_color(f"Started new game round: {round_id}", GREEN)
            else:
                self.logger.log_with_color(f"Failed to start game: {message}", RED)
        except Exception as e:
            self.logger.log_with_color(f"Start game error: {e}", RED)

    def handle_user_input(self):
        """Handle user input commands"""
        while self.running:
            try:
                command = input().strip().upper()
                if command == 'Q':
                    self.running = False
                elif command in ['U1', 'P0', 'P1', 'X1', 'G0', 'S0']:
                    asyncio.create_task(self.send_command(command))
                elif command == 'START':
                    asyncio.create_task(self.start_new_game())
            except Exception as e:
                self.logger.log_with_color(f"Input handling error: {e}", RED)

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.serial_port:
                if self.power_state == "on":
                    await self.send_command('P0')
                self.serial_port.close()
            self.running = False
            self.logger.log_with_color("Cleanup completed", GREEN)
        except Exception as e:
            self.logger.log_with_color(f"Cleanup error: {e}", RED)

    async def start(self):
        """Start the roulette controller"""
        try:
            # Start serial read thread
            read_thread = threading.Thread(target=self.read_from_serial)
            read_thread.daemon = True
            read_thread.start()
            
            # Start input handling thread
            input_thread = threading.Thread(target=self.handle_user_input)
            input_thread.daemon = True
            input_thread.start()
            
            # Initialize power state
            await self.initialize_power_state()
            
            # Keep main process running
            while self.running:
                await asyncio.sleep(0.1)
                
        except Exception as e:
            self.logger.log_with_color(f"Start error: {e}", RED)
            raise
        finally:
            await self.cleanup()
