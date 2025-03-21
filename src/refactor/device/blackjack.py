import logging
import asyncio
from typing import Dict, List, Optional
from transitions import Machine
from controller import BaseGameStateController, GameType, GameConfig, BlackJackState
from proto.hid import HIDController
from los_api.api import start_post, deal_post, finish_post

class Card:
    """Represents a playing card"""
    def __init__(self, suit: str, value: str):
        self.suit = suit
        self.value = value

    def __str__(self):
        return f"{self.value} of {self.suit}"

class BlackJackStateController(BaseGameStateController):
    """Controls BlackJack game state transitions"""
    
    states = [
        BlackJackState.TABLE_CLOSED,
        BlackJackState.START_GAME,
        BlackJackState.DEAL_CARDS,
        BlackJackState.PLAYER_TURN,
        BlackJackState.DEALER_TURN,
        BlackJackState.GAME_RESULT,
        BlackJackState.ERROR
    ]
    
    transitions = [
        {
            'trigger': 'open_table',
            'source': BlackJackState.TABLE_CLOSED,
            'dest': BlackJackState.START_GAME,
            'before': 'before_open_table'
        },
        {
            'trigger': 'start_dealing',
            'source': BlackJackState.START_GAME,
            'dest': BlackJackState.DEAL_CARDS,
            'before': 'before_dealing'
        },
        {
            'trigger': 'start_player_turn',
            'source': BlackJackState.DEAL_CARDS,
            'dest': BlackJackState.PLAYER_TURN,
            'conditions': ['is_initial_deal_complete']
        },
        {
            'trigger': 'start_dealer_turn',
            'source': BlackJackState.PLAYER_TURN,
            'dest': BlackJackState.DEALER_TURN,
            'conditions': ['is_player_turn_complete']
        },
        {
            'trigger': 'end_game',
            'source': [BlackJackState.PLAYER_TURN, BlackJackState.DEALER_TURN],
            'dest': BlackJackState.GAME_RESULT,
            'before': 'before_end_game'
        },
        {
            'trigger': 'handle_error',
            'source': '*',
            'dest': BlackJackState.ERROR,
            'before': 'before_error'
        },
        {
            'trigger': 'close_table',
            'source': '*',
            'dest': BlackJackState.TABLE_CLOSED,
            'before': 'before_close_table'
        }
    ]

    def __init__(self, config: GameConfig):
        super().__init__(GameType.BLACKJACK)
        self.config = config
        self.logger = logging.getLogger("BlackJackController")
        
        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=BlackJackState.TABLE_CLOSED,
            auto_transitions=False,
            send_event=True
        )
        
        # Initialize HID controller
        self.hid_controller = HIDController("Barcode Scanner")
        
        # Game state variables
        self.dealer_cards: List[Card] = []
        self.player_cards: List[Card] = []
        self.current_round_id: Optional[str] = None
        self.error_message: Optional[str] = None
        self.is_running = False

    async def initialize(self):
        """Initialize controller"""
        if not self.hid_controller.initialize():
            raise Exception("Failed to initialize barcode scanner")
            
        self.hid_controller.start_reading(self._handle_card_scan)

    def before_open_table(self, event):
        """Actions before opening table"""
        self.dealer_cards = []
        self.player_cards = []
        self.current_round_id = None
        self.error_message = None

    def before_dealing(self, event):
        """Actions before dealing cards"""
        self.current_round_id = event.kwargs.get('round_id')

    def before_end_game(self, event):
        """Actions before ending game"""
        self._calculate_game_result()

    def before_error(self, event):
        """Actions before entering error state"""
        self.error_message = event.kwargs.get('error', 'Unknown error')
        self.logger.error(f"Error occurred: {self.error_message}")

    def before_close_table(self, event):
        """Actions before closing table"""
        self.is_running = False

    def is_initial_deal_complete(self, event) -> bool:
        """Check if initial deal is complete"""
        return len(self.player_cards) == 2 and len(self.dealer_cards) == 2

    def is_player_turn_complete(self, event) -> bool:
        """Check if player's turn is complete"""
        return (self._calculate_hand_value(self.player_cards) >= 21 or 
                event.kwargs.get('player_stands', False))

    def _handle_card_scan(self, code: str):
        """Handle scanned card code"""
        if not self.hid_controller.is_valid_card_code(code):
            self.logger.warning(f"Invalid card code scanned: {code}")
            return
            
        suit, value = self.hid_controller.parse_card_code(code)
        if suit and value:
            card = Card(suit, value)
            self._process_scanned_card(card)

    def _process_scanned_card(self, card: Card):
        """Process a scanned card based on current game state"""
        if self.state == BlackJackState.DEAL_CARDS:
            if len(self.player_cards) < 2:
                self.player_cards.append(card)
                self.logger.info(f"Dealt to player: {card}")
            elif len(self.dealer_cards) < 2:
                self.dealer_cards.append(card)
                self.logger.info(f"Dealt to dealer: {card}")
                if self.is_initial_deal_complete(None):
                    self.start_player_turn()
                    
        elif self.state == BlackJackState.PLAYER_TURN:
            self.player_cards.append(card)
            self.logger.info(f"Player hits: {card}")
            if self._calculate_hand_value(self.player_cards) >= 21:
                self.end_game()
                
        elif self.state == BlackJackState.DEALER_TURN:
            self.dealer_cards.append(card)
            self.logger.info(f"Dealer hits: {card}")
            if self._calculate_hand_value(self.dealer_cards) >= 17:
                self.end_game()

    def _calculate_hand_value(self, cards: List[Card]) -> int:
        """Calculate the value of a hand"""
        value = 0
        aces = 0
        
        for card in cards:
            if card.value in ['K', 'Q', 'J']:
                value += 10
            elif card.value == 'A':
                aces += 1
            else:
                value += int(card.value)
        
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
        
        return value

    def _calculate_game_result(self):
        """Calculate and log game result"""
        player_value = self._calculate_hand_value(self.player_cards)
        dealer_value = self._calculate_hand_value(self.dealer_cards)
        
        self.logger.info(f"Player's final hand ({player_value}): {', '.join(str(card) for card in self.player_cards)}")
        self.logger.info(f"Dealer's final hand ({dealer_value}): {', '.join(str(card) for card in self.dealer_cards)}")
        
        if player_value > 21:
            self.logger.info("Player busts! Dealer wins!")
        elif dealer_value > 21:
            self.logger.info("Dealer busts! Player wins!")
        elif player_value > dealer_value:
            self.logger.info("Player wins!")
        elif dealer_value > player_value:
            self.logger.info("Dealer wins!")
        else:
            self.logger.info("Push!")

    async def start(self):
        """Start the blackjack controller"""
        self.is_running = True
        self.open_table()
        
        while self.is_running:
            try:
                if self.state == BlackJackState.ERROR:
                    await asyncio.sleep(5)
                    self.open_table()
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Game round error: {e}")
                self.handle_error(error=str(e))

    async def cleanup(self):
        """Cleanup resources"""
        if self.hid_controller:
            self.hid_controller.cleanup()
