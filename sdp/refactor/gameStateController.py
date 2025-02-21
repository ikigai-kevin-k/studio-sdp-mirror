import logging
import asyncio
from typing import Dict, Optional
from enum import Enum, auto
import time
import os
import requests

from controller import GameType, RouletteState, SicBoState
from utils import log_with_color, RED, GREEN, BLUE, YELLOW, MAGENTA, RESET

class BaseGameStateController:
    """Base class for game state controllers"""
    def __init__(self, game_type: GameType):
        self.game_type = game_type
        self.current_state = None
        self.state_handlers = self._setup_state_handlers()
        self._initialize_state()

    def _initialize_state(self):
        """Initialize state based on game type"""
        raise NotImplementedError

    def _setup_state_handlers(self) -> Dict:
        """Setup state transition handlers"""
        raise NotImplementedError

    async def handle_current_state(self):
        """Handle current state"""
        if self.current_state in self.state_handlers:
            await self.state_handlers[self.current_state]()
        else:
            raise ValueError(f"No handler for state {self.current_state}")

    def transition_to(self, new_state):
        """Transition to a new state"""
        raise NotImplementedError

class RouletteStateController(BaseGameStateController):
    """Controls Roulette game state transitions"""
    
    # 定義狀態轉換等待時間
    P1_MAX_WAITING_TIME = 2
    P0_MAX_WAITING_TIME = 2
    P0_MAX_DELAY = 5
    LOG_FREQUENCY = 0.1
    
    def __init__(self):
        super().__init__(GameType.ROULETTE)
        self.logger = logging.getLogger("RouletteStateController")
        
        # 遊戲狀態相關
        self.current_round_id = None
        self.current_result = None
        self.is_running = False
        self.bet_time = 0
        self.start_time = None
        
        # Serial port 相關
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

    def state_discriminator(self, data: str):
        """Discriminate state from serial port data"""
        if "*X" in data:
            """
            Game state
            """
            if "*X;0" in data:
                self.current_state = RouletteState.TABLE_CLOSED
                self.current_data_protocol_mode = "game_state_mode"
                return
            elif "*X;1" in data:
                self.current_state = RouletteState.START_GAME
                self.current_data_protocol_mode = "game_state_mode"
                return
            elif "*X;2" in data:
                self.current_state = RouletteState.PLACE_BET
                self.current_data_protocol_mode = "game_state_mode"
                return
            elif "*X;3" in data:
                self.current_state = RouletteState.NO_MORE_BET
                self.current_data_protocol_mode = "game_state_mode"
                return
            elif "*X;4" in data:
                self.current_state = RouletteState.WINNING_NUMBER
                self.current_data_protocol_mode = "game_state_mode"
                return
            else:
                log_with_color(f"unknown game state: {data}")
                raise Exception("unknown game state, close the program.")
            
        elif "*o" in data:
            self.current_data_protocol_mode = "operation_mode"
            pass
        elif "*F" in data:
            self.current_data_protocol_mode = "self_test_mode"
            pass
        elif "*P" in data:
            """Power setting mode"""
            if "*P 1" in data and self.current_power_state == "off":
                self.current_power_state = "on"
                self.current_data_protocol_mode = "power_setting_mode"
                return
            
            elif "*P 0" in data and self.current_power_state == "on":
                self.current_power_state = "off"
                self.current_state = RouletteState.TABLE_CLOSED
                self.current_data_protocol_mode = "power_setting_mode"

                if "*X:6" not in data and self.p0_delay_counter < self.P0_MAX_DELAY:
                    self.p0_delay_counter += 1
                else:
                    raise Exception(f"{RED}P0 delay time too long, there may be something wrong.{RESET}")
                return
            
            elif "*P OK" in data:
                return
            else:
                log_with_color(data)
                raise Exception("unknown power state.")

        elif "*C" in data:
            self.current_data_protocol_mode = "calibration_mode"
            pass
        elif "*W" in data:
            self.current_data_protocol_mode = "warning_flag_mode"
            self.current_state = RouletteState.START_GAME
            pass
        elif "*M" in data:
            self.current_data_protocol_mode = "statistics_mode"
            pass
        elif data.strip().isdigit():
            """The number of the winning number"""
            self.current_result = int(data.strip())
            pass
        else:
            log_with_color(data)
            raise Exception("unknown protocol log type.")

    async def update_sdp_state(self):
        """Update SDP state based on current state"""
        await self.handle_current_state()

    def roulette_state_display(self):
        """Display current roulette state"""
        log_with_color(f"{RESET}Current{GREEN} {YELLOW}game state:{RESET} {self.current_state}{RESET}")
        log_with_color(f"{RESET}Current{GREEN} {BLUE}data protocol mode:{RESET} {self.current_data_protocol_mode}{RESET}")
        if self.current_power_state == "on":
            log_with_color(f"{RESET}Current{GREEN} {MAGENTA}power state:{RESET} {GREEN}{self.current_power_state}{RESET}")
        elif self.current_power_state == "off":
            log_with_color(f"{RESET}Current{RED} {MAGENTA}power state:{RESET} {RED}{self.current_power_state}{RESET}")

    def roulette_write_data_to_sdp(self, data):
        """Write data to SDP"""
        os.write(self.masterRoulettePort, data.encode())
        log_with_color(f"Roulette simulator sent to SDP: {data.encode().strip()}")

    def roulette_read_data_from_sdp(self):
        """Read data from SDP"""
        read_data = os.read(self.masterRoulettePort, 1024)
        if read_data:
            log_with_color(f"Roulette supposed to be received from SDP: {read_data.decode().strip()}")

    async def read_ss2_protocol_log(self, file_name):
        """Read SS2 protocol log file"""
        try:
            with open(file_name, "r") as file:
                lines = file.readlines()
                if self.line_number <= len(lines):
                    line = lines[self.line_number - 1]
                    log_with_color(f"讀取到數據: {line.strip()}")
                    return line.strip()
                else:
                    log_with_color("到達文件末尾")
                    return None
        except Exception as e:
            log_with_color(f"讀取文件錯誤: {e}")
            return None

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
        # 計算下注時間
        current_time = time.time()
        self.bet_time = current_time - self.start_time
        
        # 檢查是否超過最大下注時間
        if self.bet_time >= self.P0_MAX_DELAY:
            self.transition_to(RouletteState.NO_MORE_BET)
        else:
            await asyncio.sleep(0.1)  # 短暫等待後再次檢查

    async def _handle_no_more_bet(self):
        """Handle no more bet state"""
        self.logger.info("No more bets!")
        await asyncio.sleep(self.P1_MAX_WAITING_TIME)
        
        # 模擬輪盤旋轉和球落下
        self.current_result = self._simulate_roulette_spin()
        self.transition_to(RouletteState.WINNING_NUMBER)

    async def _handle_winning_number(self):
        """Handle winning number state"""
        self.logger.info(f"Winning number is {self.current_result}")
        await asyncio.sleep(self.P1_MAX_WAITING_TIME)
        
        # 如果遊戲還在運行，開始新的回合
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
        import random
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

class SicBoStateController(BaseGameStateController):
    """Controls SicBo game state transitions"""
    
    def __init__(self):
        super().__init__(GameType.SICBO)
        self.logger = logging.getLogger("SicBoStateController")
        self.current_round_id = None
        self.current_result = None
        self.is_running = False
        
        # LOS API configuration
        self.los_url = 'https://crystal-los.iki-cit.cc/v1/service/sdp/table/'
        self.token = 'E5LN4END9Q'
        
        # 遊戲時間設定
        self.betting_duration = 8  # 下注時間
        self.shake_duration = 7    # 搖骰子時間
        self.result_duration = 4   # 結果顯示時間

        # MQTT 相關設定
        self.response_received = False
        self.last_response = None
        self.mqtt_controller = None  # 將在外部注入 MQTTController

    def _initialize_state(self):
        """Initialize SicBo state"""
        self.current_state = SicBoState.TABLE_CLOSED

    def _setup_state_handlers(self) -> Dict:
        """Setup SicBo state handlers"""
        return {
            SicBoState.TABLE_CLOSED: self._handle_table_closed,
            SicBoState.START_GAME: self._handle_start_game,
            SicBoState.PLACE_BET: self._handle_place_bet,
            SicBoState.SHAKE_DICE: self._handle_shake_dice,
            SicBoState.DETECT_RESULT: self._handle_detect_result,
            SicBoState.WINNING_NUMBER: self._handle_winning_number,
        }

    async def _handle_table_closed(self):
        """Handle table closed state"""
        self.logger.info("Table is closed")
        if self.is_running:
            self.transition_to(SicBoState.START_GAME)

    async def _handle_start_game(self):
        """Handle start game state"""
        self.logger.info("Starting new game round")
        
        # 呼叫 LOS API start
        headers = self._get_los_headers()
        response = requests.post(f'{self.los_url}/start', headers=headers, json={})
        
        if response.status_code != 200:
            self.logger.error(f"Failed to start game: {response.status_code} - {response.text}")
            self.transition_to(SicBoState.ERROR)
            return
            
        response_data = response.json()
        self.current_round_id = response_data.get('data', {}).get('table', {}).get('tableRound', {}).get('roundId')
        
        if not self.current_round_id:
            self.logger.error("Failed to get round ID")
            self.transition_to(SicBoState.ERROR)
            return
            
        self.logger.info(f"New round started with ID: {self.current_round_id}")
        self.transition_to(SicBoState.PLACE_BET)

    async def _handle_place_bet(self):
        """Handle place bet state"""
        self.logger.info("Betting time...")
        await asyncio.sleep(self.betting_duration)
        self.transition_to(SicBoState.SHAKE_DICE)

    async def _handle_shake_dice(self):
        """Handle shake dice state"""
        self.logger.info("Shaking dice...")
        
        # 發送搖骰子命令
        shake_command = {
            "command": "shake",
            "arg": {
                "round_id": self.current_round_id
            }
        }
        
        # 等待搖骰子完成
        await asyncio.sleep(self.shake_duration)
        self.transition_to(SicBoState.DETECT_RESULT)

    async def _handle_detect_result(self):
        """Handle detect result state"""
        self.logger.info("Detecting dice result...")
        
        if not self.mqtt_controller:
            self.logger.error("MQTT controller not initialized")
            self.transition_to(SicBoState.ERROR)
            return

        # 發送偵測命令
        detect_command = {
            "command": "detect",
            "arg": {
                "round_id": self.current_round_id,
                "input_stream": "https://192.168.88.213:8088/live/r1234_dice.flv",
                "output_stream": ""
            }
        }
        
        # 發送命令並等待回應
        success, dice_result = await self.mqtt_controller.send_detect_command(
            self.current_round_id,
            input_stream="https://192.168.88.213:8088/live/r1234_dice.flv",
            output_stream=""
        )
        
        if not success or dice_result is None:
            self.logger.error("Failed to get dice result")
            self.transition_to(SicBoState.ERROR)
            return
            
        self.current_result = dice_result
        self.logger.info(f"Received dice result: {self.current_result}")
        self.transition_to(SicBoState.WINNING_NUMBER)

    async def _handle_winning_number(self):
        """Handle winning number state"""
        self.logger.info(f"Winning numbers: {self.current_result}")
        
        # 發送結果到 LOS API
        headers = self._get_los_headers()
        deal_data = {
            "roundId": self.current_round_id,
            "sicBo": self.current_result
        }
        
        deal_response = requests.post(f'{self.los_url}/deal', 
                                    headers=headers, 
                                    json=deal_data)
        
        if deal_response.status_code != 200:
            self.logger.error(f"Failed to send deal result: {deal_response.status_code}")
            self.transition_to(SicBoState.ERROR)
            return
            
        # 等待結果顯示時間
        await asyncio.sleep(self.result_duration)
        
        # 結束回合
        finish_response = requests.post(f'{self.los_url}/finish', 
                                      headers=headers, 
                                      json={})
        
        if finish_response.status_code != 200:
            self.logger.error(f"Failed to finish round: {finish_response.status_code}")
            self.transition_to(SicBoState.ERROR)
            return
            
        # 開始新的回合
        if self.is_running:
            self.transition_to(SicBoState.START_GAME)
        else:
            self.transition_to(SicBoState.TABLE_CLOSED)

    def _get_los_headers(self):
        """Get LOS API headers"""
        return {
            'accept': 'application/json',
            'Bearer': f'Bearer {self.token}',
            'x-signature': 'los-local-signature',
            'Content-Type': 'application/json'
        }

    async def start(self, round_id: Optional[str] = None):
        """Start the SicBo game"""
        self.is_running = True
        if round_id:
            self.current_round_id = round_id
        self.transition_to(SicBoState.START_GAME)

    async def stop(self):
        """Stop the SicBo game"""
        self.is_running = False
        self.transition_to(SicBoState.TABLE_CLOSED)

    async def cleanup(self):
        """Cleanup resources"""
        self.is_running = False
        self.current_round_id = None
        self.current_result = None

    async def set_mqtt_controller(self, mqtt_controller):
        """Set MQTT controller"""
        self.mqtt_controller = mqtt_controller
        await self.mqtt_controller.initialize()

class BlackJackStateController(BaseGameStateController):
    """Controls BlackJack game state transitions (TBD)"""
    
    def __init__(self):
        super().__init__(GameType.BLACKJACK)

    def _initialize_state(self):
        """Initialize BlackJack state"""
        pass  # To be implemented

    def _setup_state_handlers(self) -> Dict:
        """Setup BlackJack state handlers"""
        return {}  # To be implemented

    def transition_to(self, new_state):
        """Transition to a new BlackJack state"""
        pass  # To be implemented

def create_game_state_controller(game_type: GameType) -> BaseGameStateController:
    """Factory function to create appropriate game state controller"""
    controllers = {
        GameType.ROULETTE: RouletteStateController,
        GameType.SICBO: SicBoStateController,
        GameType.BLACKJACK: BlackJackStateController
    }
    
    controller_class = controllers.get(game_type)
    if not controller_class:
        raise ValueError(f"Unsupported game type: {game_type}")
    
    return controller_class() 