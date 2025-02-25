import logging
from typing import Dict, Optional
from enum import Enum, auto
from dataclasses import dataclass

class GameType(Enum):
    """Game types supported by the system"""
    ROULETTE = "roulette"
    SICBO = "sicbo"
    BLACKJACK = "blackjack"

class RouletteState(Enum):
    """Game states for Roulette"""
    TABLE_CLOSED = auto()
    START_GAME = auto()
    PLACE_BET = auto()
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
    log_dir: str = 'logs'

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
