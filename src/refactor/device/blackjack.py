import logging
import asyncio
import random
from typing import Dict, List
from controller import BaseGameStateController, GameType, BlackJackState

class Card:
    """Represents a playing card"""
    def __init__(self, suit: str, value: str):
        self.suit = suit
        self.value = value

    def __str__(self):
        return f"{self.value} of {self.suit}"

class BlackJackStateController(BaseGameStateController):
    """Controls BlackJack game state transitions"""
    
    def __init__(self):
        super().__init__(GameType.BLACKJACK)
        self.logger = logging.getLogger("BlackJackStateController")
        self.current_round_id = None
        self.is_running = False
        
        # Game state
        self.dealer_cards: List[Card] = []
        self.player_cards: List[Card] = []
        self.deck: List[Card] = []
        
        # Game settings
        self.WAIT_TIME = 2.0  # seconds between state transitions

    def _initialize_state(self):
        """Initialize BlackJack state"""
        self.current_state = BlackJackState.TABLE_CLOSED
        self._initialize_deck()

    def _initialize_deck(self):
        """Initialize a new deck of cards"""
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [Card(suit, value) for suit in suits for value in values]
        random.shuffle(self.deck)

    def _setup_state_handlers(self) -> Dict:
        """Setup BlackJack state handlers"""
        return {
            BlackJackState.TABLE_CLOSED: self._handle_table_closed,
            BlackJackState.START_GAME: self._handle_start_game,
            BlackJackState.DEAL_CARDS: self._handle_deal_cards,
            BlackJackState.PLAYER_TURN: self._handle_player_turn,
            BlackJackState.DEALER_TURN: self._handle_dealer_turn,
            BlackJackState.GAME_RESULT: self._handle_game_result,
            BlackJackState.ERROR: self._handle_error
        }

    async def _handle_table_closed(self):
        """Handle table closed state"""
        self.logger.info("Table is closed")
        await asyncio.sleep(self.WAIT_TIME)
        if self.is_running:
            self.transition_to(BlackJackState.START_GAME)

    async def _handle_start_game(self):
        """Handle start game state"""
        self.logger.info("Starting new game round")
        self._initialize_deck()
        self.dealer_cards = []
        self.player_cards = []
        await asyncio.sleep(self.WAIT_TIME)
        self.transition_to(BlackJackState.DEAL_CARDS)

    async def _handle_deal_cards(self):
        """Handle dealing initial cards"""
        self.logger.info("Dealing initial cards")
        # Deal two cards each to player and dealer
        self.player_cards.extend([self.deck.pop() for _ in range(2)])
        self.dealer_cards.extend([self.deck.pop() for _ in range(2)])
        
        self.logger.info(f"Player cards: {', '.join(str(card) for card in self.player_cards)}")
        self.logger.info(f"Dealer shows: {self.dealer_cards[0]}")
        
        await asyncio.sleep(self.WAIT_TIME)
        self.transition_to(BlackJackState.PLAYER_TURN)

    async def _handle_player_turn(self):
        """Handle player's turn"""
        self.logger.info("Player's turn")
        # Simulate player decision (hit or stand)
        if self._calculate_hand_value(self.player_cards) < 17:
            self.player_cards.append(self.deck.pop())
            self.logger.info(f"Player hits: {self.player_cards[-1]}")
            if self._calculate_hand_value(self.player_cards) > 21:
                self.transition_to(BlackJackState.GAME_RESULT)
            else:
                await asyncio.sleep(self.WAIT_TIME)
        else:
            self.logger.info("Player stands")
            self.transition_to(BlackJackState.DEALER_TURN)

    async def _handle_dealer_turn(self):
        """Handle dealer's turn"""
        self.logger.info("Dealer's turn")
        self.logger.info(f"Dealer's hole card: {self.dealer_cards[1]}")
        
        while self._calculate_hand_value(self.dealer_cards) < 17:
            self.dealer_cards.append(self.deck.pop())
            self.logger.info(f"Dealer hits: {self.dealer_cards[-1]}")
            await asyncio.sleep(self.WAIT_TIME)
        
        self.logger.info("Dealer stands")
        self.transition_to(BlackJackState.GAME_RESULT)

    async def _handle_game_result(self):
        """Handle game result"""
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
        
        await asyncio.sleep(self.WAIT_TIME)
        if self.is_running:
            self.transition_to(BlackJackState.START_GAME)
        else:
            self.transition_to(BlackJackState.TABLE_CLOSED)

    async def _handle_error(self):
        """Handle error state"""
        self.logger.error("Error occurred in blackjack game")
        await asyncio.sleep(self.WAIT_TIME)
        self.transition_to(BlackJackState.TABLE_CLOSED)

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
        
        # Add aces
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
        
        return value

    def transition_to(self, new_state):
        """Transition to a new BlackJack state"""
        if not isinstance(new_state, BlackJackState):
            raise ValueError(f"Invalid state transition: {new_state}")
        old_state = self.current_state
        self.current_state = new_state
        self.logger.info(f"State transition: {old_state} -> {new_state}")

    async def start(self, round_id: str):
        """Start the blackjack game"""
        self.is_running = True
        self.current_round_id = round_id
        self.transition_to(BlackJackState.START_GAME)

    async def stop(self):
        """Stop the blackjack game"""
        self.is_running = False
        self.transition_to(BlackJackState.TABLE_CLOSED)

    async def cleanup(self):
        """Cleanup resources"""
        self.is_running = False
        self.current_round_id = None
        self.dealer_cards = []
        self.player_cards = []
        self.deck = []
        self.logger.info("Blackjack game cleaned up")
