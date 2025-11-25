"""
State Validator Helper Module

This module provides helper functions to validate and manage state transitions
for table API calls in game controllers.
"""

import logging
from typing import Optional, Callable, Any, Dict, Tuple, List
from state_machine.table_api_state_machine import (
    TableAPIStateMachine,
    GameState,
    StateTransitionError,
    MultiEnvironmentStateManager,
    api_status_to_game_state,
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


def create_multi_environment_manager(
    tables: List[Dict[str, Any]]
) -> MultiEnvironmentStateManager:
    """
    Create multi-environment state manager from table configurations

    Args:
        tables: List of table configurations with 'name' field

    Returns:
        MultiEnvironmentStateManager instance
    """
    manager = MultiEnvironmentStateManager()

    for table in tables:
        table_name = table.get("name", "unknown")
        state_machine = create_state_machine_for_table(table_name)
        manager.add_environment(table_name, state_machine)

    return manager


async def check_environment_state_before_post(
    env_name: str,
    state_machine: TableAPIStateMachine,
    get_roundid_func: Callable,
    post_url: str,
    token: str,
    api_name: str,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check environment state from API before posting

    This function should be called before each tableAPI post to ensure
    the state machine is in sync with the actual API state.

    Args:
        env_name: Environment name
        state_machine: State machine instance for this environment
        get_roundid_func: Function to call get_roundID_v2 API (can be sync or async)
        post_url: API post URL
        token: API token
        api_name: Name of the API post to execute

    Returns:
        Tuple of (should_proceed: bool, api_status: Optional[str], error: Optional[str])
        - should_proceed: True if API post should proceed
        - api_status: Current API status if successfully retrieved
        - error: Error message if check failed
    """
    try:
        # Get current state from API (support both sync and async functions)
        import asyncio
        import inspect

        if inspect.iscoroutinefunction(get_roundid_func):
            round_id, api_status, bet_period = await get_roundid_func(post_url, token)
        else:
            # Synchronous function, run in executor
            loop = asyncio.get_event_loop()
            round_id, api_status, bet_period = await loop.run_in_executor(
                None, get_roundid_func, post_url, token
            )

        if round_id == -1 or api_status is None:
            logger.warning(
                f"[{env_name}] Failed to get API state, proceeding with caution"
            )
            return True, None, None

        # Sync state machine from API
        state_machine.sync_from_api_state(api_status, reason="Pre-post state check")

        logger.debug(
            f"[{env_name}] Current API state: {api_status}, "
            f"State machine state: {state_machine.current_state.value}"
        )

        return True, api_status, None

    except Exception as e:
        error_msg = f"Error checking API state for {env_name}: {e}"
        logger.error(f"[{env_name}] {error_msg}")
        return False, None, error_msg


def check_alignment_before_post(
    manager: MultiEnvironmentStateManager,
    env_name: str,
    cancel_post_func: Optional[Callable] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Check if environment is aligned with PRD before posting

    If not aligned, automatically handle misalignment by sending cancel post.

    Args:
        manager: MultiEnvironmentStateManager instance
        env_name: Environment name to check
        cancel_post_func: Optional function to call cancel_post API

    Returns:
        Tuple of (is_aligned: bool, error_message: Optional[str])
    """
    if env_name == "PRD":
        return True, None  # PRD is always aligned

    is_aligned, error = manager.check_alignment(env_name)

    if not is_aligned:
        logger.warning(
            f"[{env_name}] Not aligned with PRD, handling misalignment"
        )
        # Handle misalignment
        success, error_msg = manager.handle_misalignment(
            env_name, cancel_post_func
        )
        if not success:
            return False, error_msg

        # After cancel, environment should wait for PRD's next round
        logger.info(
            f"[{env_name}] Misalignment handled, will sync with PRD on next round"
        )
        return False, "Environment misaligned, cancel sent, waiting for PRD"

    return True, None


async def initialize_and_sync_environments(
    manager: MultiEnvironmentStateManager,
    tables: List[Dict[str, Any]],
    get_roundid_funcs: Dict[str, Callable],
    token: str,
) -> Tuple[bool, Dict[str, bool], List[str]]:
    """
    Initialize and sync all environments from API states

    This should be called at program startup. It will:
    1. Get current state from API for each environment
    2. Sync state machines with API states
    3. Check alignment between environments
    4. Handle misaligned environments by sending cancel post

    Args:
        manager: MultiEnvironmentStateManager instance
        tables: List of table configurations
        get_roundid_funcs: Dictionary mapping environment names to get_roundID functions
        token: API token

    Returns:
        Tuple of (all_aligned: bool, sync_results: Dict[str, bool], misaligned: List[str])
    """
    api_statuses = {}
    sync_results = {}

    # Step 1: Get API states for all environments
    logger.info("Getting current API states for all environments")
    for table in tables:
        env_name = table.get("name", "unknown")
        if env_name not in get_roundid_funcs:
            logger.warning(f"get_roundID function not found for {env_name}")
            continue

        try:
            post_url = f"{table['post_url']}{table['game_code']}"
            get_roundid_func = get_roundid_funcs[env_name]

            # Support both sync and async get_roundID functions
            import asyncio
            import inspect

            if inspect.iscoroutinefunction(get_roundid_func):
                round_id, api_status, bet_period = await get_roundid_func(post_url, token)
            else:
                # Synchronous function, run in executor
                loop = asyncio.get_event_loop()
                round_id, api_status, bet_period = await loop.run_in_executor(
                    None, get_roundid_func, post_url, token
                )

            if round_id == -1 or api_status is None:
                logger.warning(
                    f"[{env_name}] Failed to get API state, using UNKNOWN"
                )
                api_statuses[env_name] = None
            else:
                api_statuses[env_name] = api_status
                logger.info(
                    f"[{env_name}] Current API state: {api_status}"
                )

        except Exception as e:
            logger.error(f"[{env_name}] Error getting API state: {e}")
            api_statuses[env_name] = None

    # Step 2: Sync state machines from API states
    logger.info("Syncing state machines from API states")
    sync_results = manager.initialize_from_api_states(
        api_statuses, reason="Program startup initialization"
    )

    # Step 3: Check alignment
    logger.info("Checking environment alignment")
    misaligned = manager.get_misaligned_environments()

    if misaligned:
        logger.warning(
            f"Found misaligned environments: {misaligned}. "
            f"These will be handled by sending cancel posts."
        )
    else:
        logger.info("All environments are aligned with PRD")

    # Step 4: Determine next action based on alignment
    all_aligned = len(misaligned) == 0

    if all_aligned:
        # All aligned: can proceed with normal flow
        next_state = manager.get_next_state_for_all_environments()
        if next_state:
            logger.info(
                f"All environments aligned. Next expected state: {next_state.value}"
            )
    else:
        # Some misaligned: need to handle them
        logger.info(
            f"Some environments misaligned. Will handle misalignment for: {misaligned}"
        )

    return all_aligned, sync_results, misaligned

