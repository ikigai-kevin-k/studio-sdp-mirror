"""
Table API State Machine Implementation

This module implements a state machine to ensure table API state transitions
follow the defined rules for all game types (Speed, VIP, SicBo).
"""

import logging
from enum import Enum
from typing import Optional, Dict, Set, Callable, Any
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)


class GameState(Enum):
    """Game state enumeration"""

    START = "start"
    DEAL = "deal"
    BET_STOPPED = "bet-stopped"
    FINISHED = "finished"
    BROADCAST = "broadcast"
    PAUSE = "pause"
    CANCEL = "cancel"
    UNKNOWN = "unknown"  # Initial state or error state


class StateTransitionError(Exception):
    """Exception raised when an invalid state transition is attempted"""

    def __init__(
        self,
        current_state: GameState,
        attempted_state: GameState,
        message: str = None,
    ):
        self.current_state = current_state
        self.attempted_state = attempted_state
        self.message = message or (
            f"Invalid state transition from {current_state.value} "
            f"to {attempted_state.value}"
        )
        super().__init__(self.message)


class TableAPIStateMachine:
    """
    State machine for managing table API state transitions

    Normal flow: start -> deal -> bet-stopped -> finished -> start
    Exception flow: start/deal/bet-stopped/finished -> broadcast
      - If auto-resolved: follow normal flow rules for next step
      - If not auto-resolved: pause -> cancel -> start -> normal flow
    """

    def __init__(self, table_name: str = "unknown"):
        """
        Initialize the state machine

        Args:
            table_name: Name of the table for logging purposes
        """
        self.table_name = table_name
        self.current_state = GameState.UNKNOWN
        self.previous_state: Optional[GameState] = None
        self.broadcast_auto_resolved = False
        self.state_history: list[tuple[datetime, GameState, Optional[str]]] = []
        self.transition_count = 0

        # Define valid transitions
        self._normal_transitions: Dict[GameState, Set[GameState]] = {
            GameState.START: {GameState.DEAL, GameState.BROADCAST},
            GameState.DEAL: {GameState.BET_STOPPED, GameState.BROADCAST},
            GameState.BET_STOPPED: {GameState.FINISHED, GameState.BROADCAST},
            GameState.FINISHED: {GameState.START, GameState.BROADCAST},
            GameState.UNKNOWN: {GameState.START},  # Initial state
        }

        # Exception flow transitions
        self._exception_transitions: Dict[GameState, Set[GameState]] = {
            GameState.BROADCAST: {GameState.PAUSE, GameState.DEAL, GameState.BET_STOPPED, GameState.FINISHED, GameState.START},
            GameState.PAUSE: {GameState.CANCEL},
            GameState.CANCEL: {GameState.START},
        }

        # Callbacks for state transitions
        self._transition_callbacks: Dict[
            tuple[GameState, GameState], list[Callable]
        ] = {}

    def _get_all_valid_transitions(self, state: GameState) -> Set[GameState]:
        """
        Get all valid transitions for a given state

        Args:
            state: Current state

        Returns:
            Set of valid next states
        """
        valid_states = set()

        # Add normal transitions
        if state in self._normal_transitions:
            valid_states.update(self._normal_transitions[state])

        # Add exception transitions
        if state in self._exception_transitions:
            valid_states.update(self._exception_transitions[state])

        return valid_states

    def can_transition_to(self, target_state: GameState) -> bool:
        """
        Check if transition to target state is valid

        Args:
            target_state: Target state to check

        Returns:
            True if transition is valid, False otherwise
        """
        valid_transitions = self._get_all_valid_transitions(self.current_state)
        return target_state in valid_transitions

    def transition_to(
        self,
        new_state: GameState,
        reason: Optional[str] = None,
        auto_resolved: Optional[bool] = None,
    ) -> bool:
        """
        Transition to a new state

        Args:
            new_state: Target state
            reason: Optional reason for the transition
            auto_resolved: Optional flag indicating if broadcast was auto-resolved

        Returns:
            True if transition was successful, False otherwise

        Raises:
            StateTransitionError: If transition is invalid
        """
        # Handle broadcast auto-resolved flag
        if new_state == GameState.BROADCAST:
            if auto_resolved is not None:
                self.broadcast_auto_resolved = auto_resolved
            else:
                # Default to False if not specified
                self.broadcast_auto_resolved = False

        # Special handling for broadcast -> normal flow (auto-resolved)
        if (
            self.current_state == GameState.BROADCAST
            and self.broadcast_auto_resolved
            and new_state in [GameState.DEAL, GameState.BET_STOPPED, GameState.FINISHED, GameState.START]
        ):
            # Auto-resolved: can transition to normal flow states
            # based on what state we were in before broadcast
            if self.previous_state:
                # Check if the transition makes sense based on previous state
                if self.previous_state == GameState.START and new_state == GameState.DEAL:
                    pass  # Valid
                elif self.previous_state == GameState.DEAL and new_state == GameState.BET_STOPPED:
                    pass  # Valid
                elif self.previous_state == GameState.BET_STOPPED and new_state == GameState.FINISHED:
                    pass  # Valid
                elif self.previous_state == GameState.FINISHED and new_state == GameState.START:
                    pass  # Valid
                else:
                    # Transition doesn't match previous state, but allow it
                    # as auto-resolved might have changed the game state
                    logger.warning(
                        f"[{self.table_name}] Auto-resolved transition from "
                        f"{self.current_state.value} to {new_state.value} "
                        f"(previous: {self.previous_state.value})"
                    )
        elif not self.can_transition_to(new_state):
            error_msg = (
                f"[{self.table_name}] Invalid state transition: "
                f"{self.current_state.value} -> {new_state.value}"
            )
            logger.error(error_msg)
            raise StateTransitionError(
                self.current_state, new_state, error_msg
            )

        # Perform transition
        self.previous_state = self.current_state
        self.current_state = new_state
        self.transition_count += 1

        # Record transition in history
        self.state_history.append(
            (datetime.now(), new_state, reason or "No reason provided")
        )

        # Log transition
        log_msg = (
            f"[{self.table_name}] State transition: "
            f"{self.previous_state.value} -> {new_state.value}"
        )
        if reason:
            log_msg += f" (Reason: {reason})"
        if new_state == GameState.BROADCAST and auto_resolved is not None:
            log_msg += f" (Auto-resolved: {auto_resolved})"
        logger.info(log_msg)

        # Execute callbacks
        callback_key = (self.previous_state, new_state)
        if callback_key in self._transition_callbacks:
            for callback in self._transition_callbacks[callback_key]:
                try:
                    callback(self.previous_state, new_state, reason)
                except Exception as e:
                    logger.error(
                        f"[{self.table_name}] Error executing transition "
                        f"callback: {e}"
                    )

        return True

    def get_next_state_for_normal_flow(self) -> Optional[GameState]:
        """
        Get the next expected state in normal flow based on current state

        If current state is BROADCAST, use previous_state to determine next state.

        Returns:
            Next expected state in normal flow, or None if not applicable
        """
        normal_flow_map = {
            GameState.START: GameState.DEAL,
            GameState.DEAL: GameState.BET_STOPPED,
            GameState.BET_STOPPED: GameState.FINISHED,
            GameState.FINISHED: GameState.START,
        }

        # If in BROADCAST state, use previous_state to determine next state
        if self.current_state == GameState.BROADCAST:
            if self.previous_state:
                return normal_flow_map.get(self.previous_state)
            else:
                # No previous state, cannot determine next state
                return None

        return normal_flow_map.get(self.current_state)

    def handle_broadcast(
        self, auto_resolved: bool = False, reason: Optional[str] = None
    ) -> bool:
        """
        Handle broadcast state transition

        Args:
            auto_resolved: Whether the broadcast issue was auto-resolved
            reason: Optional reason for broadcast

        Returns:
            True if transition was successful
        """
        return self.transition_to(
            GameState.BROADCAST, reason=reason, auto_resolved=auto_resolved
        )

    def handle_exception_flow(
        self, reason: Optional[str] = None
    ) -> bool:
        """
        Handle exception flow: pause -> cancel -> start

        This should be called when broadcast is not auto-resolved.

        Args:
            reason: Optional reason for the exception flow

        Returns:
            True if all transitions were successful

        Note:
            This method only transitions to PAUSE. The caller should
            handle subsequent transitions (cancel -> start) separately.
        """
        if self.current_state != GameState.BROADCAST:
            logger.warning(
                f"[{self.table_name}] handle_exception_flow called "
                f"but current state is {self.current_state.value}, not BROADCAST"
            )
            return False

        # Transition to pause
        return self.transition_to(GameState.PAUSE, reason=reason)

    def reset_to_start(self, reason: Optional[str] = None) -> bool:
        """
        Reset state machine to START state

        Args:
            reason: Optional reason for reset

        Returns:
            True if reset was successful
        """
        return self.transition_to(GameState.START, reason=reason)

    def register_transition_callback(
        self,
        from_state: GameState,
        to_state: GameState,
        callback: Callable[[GameState, GameState, Optional[str]], None],
    ):
        """
        Register a callback to be executed on specific state transition

        Args:
            from_state: Source state
            to_state: Target state
            callback: Callback function that receives (from_state, to_state, reason)
        """
        callback_key = (from_state, to_state)
        if callback_key not in self._transition_callbacks:
            self._transition_callbacks[callback_key] = []
        self._transition_callbacks[callback_key].append(callback)

    def get_state_info(self) -> Dict[str, Any]:
        """
        Get current state information

        Returns:
            Dictionary containing state information
        """
        return {
            "table_name": self.table_name,
            "current_state": self.current_state.value,
            "previous_state": (
                self.previous_state.value if self.previous_state else None
            ),
            "broadcast_auto_resolved": self.broadcast_auto_resolved,
            "transition_count": self.transition_count,
            "history_length": len(self.state_history),
            "valid_next_states": [
                state.value
                for state in self._get_all_valid_transitions(self.current_state)
            ],
        }

    def validate_api_call(self, api_name: str) -> bool:
        """
        Validate if an API call is allowed in current state

        Args:
            api_name: Name of the API call (e.g., "start_post", "deal_post")

        Returns:
            True if API call is allowed, False otherwise
        """
        api_to_state_map = {
            "start_post": GameState.START,
            "deal_post": GameState.DEAL,
            "bet_stop_post": GameState.BET_STOPPED,
            "finish_post": GameState.FINISHED,
            "broadcast_post": GameState.BROADCAST,
            "pause_post": GameState.PAUSE,
            "cancel_post": GameState.CANCEL,
        }

        target_state = api_to_state_map.get(api_name)
        if target_state is None:
            logger.warning(
                f"[{self.table_name}] Unknown API name: {api_name}"
            )
            return False

        return self.can_transition_to(target_state)

