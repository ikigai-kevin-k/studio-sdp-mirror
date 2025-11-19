"""
State Validator Helper Module

This module provides helper functions to validate and manage state transitions
for table API calls in game controllers.
"""

import logging
from typing import Optional, Callable, Any
from state_machine.table_api_state_machine import (
    TableAPIStateMachine,
    GameState,
    StateTransitionError,
)

logger = logging.getLogger(__name__)


def create_state_machine_for_table(table_name: str) -> TableAPIStateMachine:
    """
    Create a state machine instance for a table

    Args:
        table_name: Name of the table

    Returns:
        TableAPIStateMachine instance
    """
    return TableAPIStateMachine(table_name=table_name)


def validate_and_transition(
    state_machine: TableAPIStateMachine,
    api_name: str,
    reason: Optional[str] = None,
    auto_resolved: Optional[bool] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate API call and perform state transition

    Args:
        state_machine: State machine instance
        api_name: Name of the API call
        reason: Optional reason for the transition
        auto_resolved: Optional flag for broadcast auto-resolved

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
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
        error_msg = f"Unknown API name: {api_name}"
        logger.error(f"[{state_machine.table_name}] {error_msg}")
        return False, error_msg

    try:
        # Check if transition is valid
        if not state_machine.can_transition_to(target_state):
            error_msg = (
                f"Invalid state transition for {api_name}: "
                f"{state_machine.current_state.value} -> {target_state.value}"
            )
            logger.error(f"[{state_machine.table_name}] {error_msg}")
            return False, error_msg

        # Perform transition
        state_machine.transition_to(
            target_state, reason=reason, auto_resolved=auto_resolved
        )
        return True, None

    except StateTransitionError as e:
        error_msg = str(e)
        logger.error(f"[{state_machine.table_name}] {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error during state transition: {e}"
        logger.error(f"[{state_machine.table_name}] {error_msg}")
        return False, error_msg


def handle_broadcast_result(
    state_machine: TableAPIStateMachine,
    auto_resolved: bool,
    reason: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Handle broadcast result and determine next action

    Args:
        state_machine: State machine instance
        auto_resolved: Whether broadcast issue was auto-resolved
        reason: Optional reason

    Returns:
        Tuple of (success: bool, next_action: Optional[str])
        next_action can be: "continue_normal_flow", "pause", or None
    """
    if state_machine.current_state != GameState.BROADCAST:
        error_msg = (
            f"handle_broadcast_result called but current state is "
            f"{state_machine.current_state.value}, not BROADCAST"
        )
        logger.error(f"[{state_machine.table_name}] {error_msg}")
        return False, None

    # Update broadcast auto-resolved flag
    state_machine.broadcast_auto_resolved = auto_resolved

    if auto_resolved:
        # Continue with normal flow based on previous state
        next_state = state_machine.get_next_state_for_normal_flow()
        if next_state:
            logger.info(
                f"[{state_machine.table_name}] Broadcast auto-resolved, "
                f"continuing normal flow to {next_state.value}"
            )
            return True, "continue_normal_flow"
        else:
            logger.warning(
                f"[{state_machine.table_name}] Broadcast auto-resolved but "
                f"cannot determine next state"
            )
            return True, None
    else:
        # Not auto-resolved, need to go through exception flow
        logger.info(
            f"[{state_machine.table_name}] Broadcast not auto-resolved, "
            f"starting exception flow (pause -> cancel -> start)"
        )
        return True, "pause"


def get_state_machine_wrapper(
    state_machine: TableAPIStateMachine,
) -> Callable[[str, Optional[str], Optional[bool]], tuple[bool, Optional[str]]]:
    """
    Get a wrapper function for API calls that validates state transitions

    Args:
        state_machine: State machine instance

    Returns:
        Wrapper function that can be used to wrap API calls
    """
    def api_wrapper(
        api_name: str,
        reason: Optional[str] = None,
        auto_resolved: Optional[bool] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Wrapper function for API calls with state validation

        Args:
            api_name: Name of the API call
            reason: Optional reason for the transition
            auto_resolved: Optional flag for broadcast auto-resolved

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        return validate_and_transition(
            state_machine, api_name, reason, auto_resolved
        )

    return api_wrapper


def log_state_info(state_machine: TableAPIStateMachine):
    """
    Log current state information

    Args:
        state_machine: State machine instance
    """
    info = state_machine.get_state_info()
    logger.info(
        f"[{state_machine.table_name}] State Info: "
        f"current={info['current_state']}, "
        f"previous={info['previous_state']}, "
        f"transitions={info['transition_count']}, "
        f"valid_next={info['valid_next_states']}"
    )

