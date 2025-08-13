import logging
from typing import Dict, Optional
from enum import Enum, auto
from dataclasses import dataclass


class GameType(Enum):
    """Game types supported by the system"""

    ROULETTE = "roulette"
    SICBO = "sicbo"
    BLACKJACK = "blackjack"
    BACCARAT = "baccarat"


class RouletteState(Enum):
    """Game states for Roulette"""

    TABLE_CLOSED = auto()
    START_GAME = auto()
    PLACE_BET = auto()
    BALL_LAUNCH = auto()
    NO_MORE_BET = auto()
    WINNING_NUMBER = auto()
    ERROR = auto()


class SicBoState(Enum):
    """Game states for SicBo"""

    TABLE_CLOSED = auto()
    START_GAME = auto()
    PLACE_BET = auto()
    SHAKE_DICE = auto()
    DETECT_RESULT = auto()
    WINNING_NUMBER = auto()
    ERROR = auto()


class BlackJackState(Enum):
    """BlackJack game states"""

    TABLE_CLOSED = auto()
    START_GAME = auto()
    DEAL_CARDS = auto()
    PLAYER_TURN = auto()
    DEALER_TURN = auto()
    GAME_RESULT = auto()
    ERROR = auto()


@dataclass
class GameConfig:
    """Configuration for game setup"""

    game_type: GameType
    room_id: str
    broker_host: str
    broker_port: int
    enable_logging: bool = False
    log_dir: str = "logs"
    port: str = "/dev/ttyUSB0"
    baudrate: int = 9600


class Controller:
    """Base controller class"""

    def __init__(self, config: GameConfig):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    async def initialize(self):
        """Initialize controller"""
        raise NotImplementedError

    async def cleanup(self):
        """Cleanup resources"""
        raise NotImplementedError


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

    async def cleanup(self):
        """Cleanup resources"""
        raise NotImplementedError


def create_game_state_controller(game_type: GameType) -> BaseGameStateController:
    """Factory function to create appropriate game state controller"""
    from device.roulette import RouletteStateController
    from device.sicbo import SicBoStateController
    from device.blackjack import BlackJackStateController

    controllers = {
        GameType.ROULETTE: RouletteStateController,
        GameType.SICBO: SicBoStateController,
        GameType.BLACKJACK: BlackJackStateController,
    }

    controller_class = controllers.get(game_type)
    if not controller_class:
        raise ValueError(f"Unsupported game type: {game_type}")

    return controller_class()
