"""
Table API State Machine Implementation

This module implements a state machine to ensure table API state transitions
follow the defined rules for all game types (Speed, VIP, SicBo).
"""

import logging
from enum import Enum
from typing import Optional, Dict, Set, Callable, Any, List, Tuple
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


def api_status_to_game_state(api_status: Optional[str]) -> GameState:
    """
    Convert API status string to GameState enum

    Args:
        api_status: Status string from get_roundID_v2 API

    Returns:
        Corresponding GameState
    """
    if api_status is None:
        return GameState.UNKNOWN

    # Normalize status string (lowercase, strip whitespace)
    status = api_status.lower().strip()

    # Map API status to GameState
    status_map = {
        "start": GameState.START,
        "deal": GameState.DEAL,
        "bet-stopped": GameState.BET_STOPPED,
        "betstopped": GameState.BET_STOPPED,
        "finished": GameState.FINISHED,
        "broadcast": GameState.BROADCAST,
        "pause": GameState.PAUSE,
        "cancel": GameState.CANCEL,
        "cancelled": GameState.CANCEL,
    }

    return status_map.get(status, GameState.UNKNOWN)


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

    def sync_from_api_state(
        self, api_status: Optional[str], reason: Optional[str] = None
    ) -> bool:
        """
        Sync state machine from API status

        Args:
            api_status: Status string from get_roundID_v2 API
            reason: Optional reason for sync

        Returns:
            True if sync was successful, False otherwise
        """
        api_state = api_status_to_game_state(api_status)

        if api_state == GameState.UNKNOWN:
            logger.warning(
                f"[{self.table_name}] Cannot sync from unknown API status: "
                f"{api_status}"
            )
            return False

        # If current state is UNKNOWN, directly set to API state
        if self.current_state == GameState.UNKNOWN:
            self.current_state = api_state
            self.previous_state = None
            logger.info(
                f"[{self.table_name}] Initialized state from API: "
                f"{api_state.value}"
            )
            return True

        # If states match, no need to sync
        if self.current_state == api_state:
            logger.debug(
                f"[{self.table_name}] State already matches API state: "
                f"{api_state.value}"
            )
            return True

        # If states don't match, log warning but don't force transition
        # This could happen if the state machine is out of sync
        logger.warning(
            f"[{self.table_name}] State mismatch: state machine has "
            f"{self.current_state.value}, but API reports {api_state.value}"
        )
        # Optionally, we could force sync here, but it's safer to let
        # the caller handle this case
        return False


class MultiEnvironmentStateManager:
    """
    Manager for multiple environment state machines

    Manages state synchronization between PRD (primary) and other environments
    (CIT, QAT, UAT, STG). Ensures all environments stay aligned with PRD.
    """

    def __init__(self):
        """Initialize multi-environment state manager"""
        self.state_machines: Dict[str, TableAPIStateMachine] = {}
        self.prd_state_machine: Optional[TableAPIStateMachine] = None
        self.environments_to_align = ["CIT", "QAT", "UAT", "STG"]

    def add_environment(
        self, env_name: str, state_machine: TableAPIStateMachine
    ) -> bool:
        """
        Add an environment state machine

        Args:
            env_name: Environment name (PRD, CIT, QAT, UAT, STG)
            state_machine: State machine instance for this environment

        Returns:
            True if added successfully
        """
        self.state_machines[env_name] = state_machine

        if env_name == "PRD":
            self.prd_state_machine = state_machine
            logger.info(f"Set PRD as primary state machine")

        logger.info(f"Added state machine for environment: {env_name}")
        return True

    def get_environment_state(self, env_name: str) -> Optional[GameState]:
        """
        Get current state for an environment

        Args:
            env_name: Environment name

        Returns:
            Current GameState or None if environment not found
        """
        if env_name not in self.state_machines:
            return None
        return self.state_machines[env_name].current_state

    def get_prd_state(self) -> Optional[GameState]:
        """
        Get PRD current state

        Returns:
            PRD GameState or None if PRD not set
        """
        if self.prd_state_machine is None:
            return None
        return self.prd_state_machine.current_state

    def check_alignment(
        self, env_name: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if an environment is aligned with PRD

        Args:
            env_name: Environment name to check

        Returns:
            Tuple of (is_aligned: bool, error_message: Optional[str])
        """
        if self.prd_state_machine is None:
            return False, "PRD state machine not initialized"

        if env_name == "PRD":
            return True, None  # PRD is always aligned with itself

        if env_name not in self.state_machines:
            return False, f"Environment {env_name} not found"

        prd_state = self.prd_state_machine.current_state
        env_state = self.state_machines[env_name].current_state

        is_aligned = prd_state == env_state

        if not is_aligned:
            logger.warning(
                f"Environment {env_name} not aligned with PRD: "
                f"{env_name}={env_state.value}, PRD={prd_state.value}"
            )

        return is_aligned, None

    def check_all_alignment(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        Check alignment status for all environments

        Returns:
            Dictionary mapping environment names to (is_aligned, error_message)
        """
        alignment_status = {}

        for env_name in self.state_machines.keys():
            is_aligned, error = self.check_alignment(env_name)
            alignment_status[env_name] = (is_aligned, error)

        return alignment_status

    def get_misaligned_environments(self) -> List[str]:
        """
        Get list of environments that are not aligned with PRD

        Returns:
            List of environment names that are misaligned
        """
        misaligned = []

        for env_name in self.environments_to_align:
            if env_name in self.state_machines:
                is_aligned, _ = self.check_alignment(env_name)
                if not is_aligned:
                    misaligned.append(env_name)

        return misaligned

    def sync_environment_from_api(
        self,
        env_name: str,
        api_status: Optional[str],
        reason: Optional[str] = None,
    ) -> bool:
        """
        Sync environment state from API status

        Args:
            env_name: Environment name
            api_status: Status string from get_roundID_v2 API
            reason: Optional reason for sync

        Returns:
            True if sync was successful
        """
        if env_name not in self.state_machines:
            logger.error(f"Environment {env_name} not found")
            return False

        state_machine = self.state_machines[env_name]
        return state_machine.sync_from_api_state(api_status, reason)

    def sync_all_environments_from_api(
        self,
        api_statuses: Dict[str, Optional[str]],
        reason: Optional[str] = None,
    ) -> Dict[str, bool]:
        """
        Sync all environments from API statuses

        Args:
            api_statuses: Dictionary mapping environment names to API statuses
            reason: Optional reason for sync

        Returns:
            Dictionary mapping environment names to sync success status
        """
        sync_results = {}

        for env_name, api_status in api_statuses.items():
            success = self.sync_environment_from_api(env_name, api_status, reason)
            sync_results[env_name] = success

        return sync_results

    def initialize_from_api_states(
        self,
        api_statuses: Dict[str, Optional[str]],
        reason: Optional[str] = None,
    ) -> Dict[str, bool]:
        """
        Initialize all state machines from API states

        This should be called at program startup to sync state machines
        with actual API states.

        Args:
            api_statuses: Dictionary mapping environment names to API statuses
            reason: Optional reason for initialization

        Returns:
            Dictionary mapping environment names to initialization success status
        """
        logger.info("Initializing state machines from API states")
        return self.sync_all_environments_from_api(api_statuses, reason)

    def handle_misalignment(
        self, env_name: str, cancel_post_func: Optional[Callable] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Handle misaligned environment by sending cancel post

        Args:
            env_name: Environment name that is misaligned
            cancel_post_func: Optional function to call cancel_post API

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if env_name not in self.state_machines:
            return False, f"Environment {env_name} not found"

        if env_name == "PRD":
            return False, "Cannot cancel PRD environment"

        state_machine = self.state_machines[env_name]

        # Transition to CANCEL state
        try:
            state_machine.transition_to(
                GameState.CANCEL,
                reason=f"Misaligned with PRD, canceling to reset"
            )
        except StateTransitionError as e:
            return False, str(e)

        # Call cancel_post API if provided
        if cancel_post_func:
            try:
                cancel_post_func()
            except Exception as e:
                logger.error(
                    f"Error calling cancel_post for {env_name}: {e}"
                )
                return False, f"Cancel post failed: {e}"

        logger.info(
            f"Handled misalignment for {env_name}: sent cancel post"
        )
        return True, None

    def get_next_state_for_all_environments(self) -> Optional[GameState]:
        """
        Get next expected state in normal flow based on PRD state

        Returns:
            Next expected state, or None if PRD not set
        """
        if self.prd_state_machine is None:
            return None

        return self.prd_state_machine.get_next_state_for_normal_flow()

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get summary of all environment states

        Returns:
            Dictionary containing state summary
        """
        summary = {
            "prd_state": (
                self.prd_state_machine.current_state.value
                if self.prd_state_machine
                else None
            ),
            "environments": {},
            "misaligned": self.get_misaligned_environments(),
        }

        for env_name, state_machine in self.state_machines.items():
            summary["environments"][env_name] = {
                "current_state": state_machine.current_state.value,
                "is_aligned": (
                    self.check_alignment(env_name)[0]
                    if env_name != "PRD"
                    else True
                ),
            }

        return summary

