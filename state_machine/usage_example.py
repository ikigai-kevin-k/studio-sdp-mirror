"""
Usage Example for Table API State Machine

This file demonstrates how to integrate the state machine module
into main_speed.py, main_vip.py, and main_sicbo.py
"""

import asyncio
import logging
from state_machine import (
    create_state_machine_for_table,
    validate_and_transition,
    handle_broadcast_result,
    GameState,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Example: Integration in game controller initialization
def initialize_state_machines(tables):
    """
    Initialize state machines for all tables

    Args:
        tables: List of table configurations

    Returns:
        Dictionary mapping table names to state machines
    """
    state_machines = {}
    for table in tables:
        table_name = table.get("name", "unknown")
        state_machines[table_name] = create_state_machine_for_table(table_name)
        logger.info(f"Initialized state machine for table: {table_name}")
    return state_machines


# Example: Integration in start_post function
async def example_start_post(state_machine, table, token, start_post_func):
    """
    Example start_post function with state validation

    Args:
        state_machine: State machine instance for the table
        table: Table configuration
        token: API token
        start_post_func: Function to call the actual API

    Returns:
        Tuple of (table, round_id, bet_period) or (None, None) on error
    """
    # Validate state before API call
    success, error = validate_and_transition(
        state_machine,
        "start_post",
        reason="Starting new round"
    )
    if not success:
        logger.error(
            f"[{table['name']}] State validation failed for start_post: {error}"
        )
        return None, None

    # Proceed with API call
    try:
        round_id, bet_period = await start_post_func(
            table['post_url'],
            token
        )
        if round_id == -1:
            # API call failed, transition to broadcast
            validate_and_transition(
                state_machine,
                "broadcast_post",
                reason="Start post returned -1",
                auto_resolved=False
            )
            return None, None
        return table, round_id, bet_period
    except Exception as e:
        logger.error(f"[{table['name']}] API call failed: {e}")
        # Transition to broadcast on error
        validate_and_transition(
            state_machine,
            "broadcast_post",
            reason=f"Start post exception: {e}",
            auto_resolved=False
        )
        return None, None


# Example: Integration in deal_post function
async def example_deal_post(state_machine, table, token, round_id, result, deal_post_func):
    """
    Example deal_post function with state validation

    Args:
        state_machine: State machine instance for the table
        table: Table configuration
        token: API token
        round_id: Round ID
        result: Deal result
        deal_post_func: Function to call the actual API

    Returns:
        Tuple of (table_name, success) or (None, False) on error
    """
    # Validate state before API call
    success, error = validate_and_transition(
        state_machine,
        "deal_post",
        reason="Posting deal result"
    )
    if not success:
        logger.error(
            f"[{table['name']}] State validation failed for deal_post: {error}"
        )
        return None, False

    # Proceed with API call
    try:
        await deal_post_func(table['post_url'], token, round_id, result)
        return table["name"], True
    except Exception as e:
        logger.error(f"[{table['name']}] Deal post failed: {e}")
        # Transition to broadcast on error
        validate_and_transition(
            state_machine,
            "broadcast_post",
            reason=f"Deal post exception: {e}",
            auto_resolved=False
        )
        return None, False


# Example: Integration in finish_post function
async def example_finish_post(state_machine, table, token, round_id, finish_post_func):
    """
    Example finish_post function with state validation

    Args:
        state_machine: State machine instance for the table
        table: Table configuration
        token: API token
        round_id: Round ID
        finish_post_func: Function to call the actual API

    Returns:
        Tuple of (table_name, success) or (None, False) on error
    """
    # Validate state before API call
    success, error = validate_and_transition(
        state_machine,
        "finish_post",
        reason="Finishing round"
    )
    if not success:
        logger.error(
            f"[{table['name']}] State validation failed for finish_post: {error}"
        )
        return None, False

    # Proceed with API call
    try:
        await finish_post_func(table['post_url'], token, round_id)
        return table["name"], True
    except Exception as e:
        logger.error(f"[{table['name']}] Finish post failed: {e}")
        # Transition to broadcast on error
        validate_and_transition(
            state_machine,
            "broadcast_post",
            reason=f"Finish post exception: {e}",
            auto_resolved=False
        )
        return None, False


# Example: Handling broadcast with auto-resolve check
async def example_handle_broadcast(state_machine, table, token, check_auto_resolved_func):
    """
    Example function to handle broadcast state

    Args:
        state_machine: State machine instance for the table
        table: Table configuration
        token: API token
        check_auto_resolved_func: Function to check if issue is auto-resolved

    Returns:
        True if handled successfully, False otherwise
    """
    # Check if broadcast issue is auto-resolved
    auto_resolved = await check_auto_resolved_func(table, token)

    # Handle broadcast result
    success, next_action = handle_broadcast_result(
        state_machine,
        auto_resolved=auto_resolved,
        reason="Broadcast result check"
    )

    if not success:
        logger.error(f"[{table['name']}] Failed to handle broadcast result")
        return False

    if next_action == "continue_normal_flow":
        # Auto-resolved: continue with normal flow
        next_state = state_machine.get_next_state_for_normal_flow()
        if next_state:
            api_name = next_state.value + "_post"
            validate_and_transition(
                state_machine,
                api_name,
                reason="Continuing normal flow after auto-resolved broadcast"
            )
            logger.info(
                f"[{table['name']}] Broadcast auto-resolved, "
                f"continuing to {next_state.value}"
            )
        return True
    elif next_action == "pause":
        # Not auto-resolved: go through exception flow
        logger.info(
            f"[{table['name']}] Broadcast not auto-resolved, "
            f"starting exception flow"
        )
        # Transition to pause
        validate_and_transition(
            state_machine,
            "pause_post",
            reason="Exception flow: pause"
        )
        # Transition to cancel
        validate_and_transition(
            state_machine,
            "cancel_post",
            reason="Exception flow: cancel"
        )
        # Reset to start
        validate_and_transition(
            state_machine,
            "start_post",
            reason="Exception flow: reset to start"
        )
        return True

    return False


# Example: Complete game round flow
async def example_complete_round_flow(state_machine, table, token, api_functions):
    """
    Example complete round flow with state validation

    Args:
        state_machine: State machine instance for the table
        table: Table configuration
        token: API token
        api_functions: Dictionary of API functions

    Returns:
        True if round completed successfully, False otherwise
    """
    try:
        # 1. Start round
        result = await example_start_post(
            state_machine, table, token, api_functions['start_post']
        )
        if result[0] is None:
            return False
        table, round_id, bet_period = result

        # 2. Deal (simulated - replace with actual deal logic)
        # deal_result = get_deal_result()  # Your logic here
        # result = await example_deal_post(
        #     state_machine, table, token, round_id, deal_result,
        #     api_functions['deal_post']
        # )
        # if result[0] is None:
        #     return False

        # 3. Bet stop (simulated)
        # success, error = validate_and_transition(
        #     state_machine, "bet_stop_post", reason="Betting stopped"
        # )
        # if not success:
        #     return False

        # 4. Finish round
        # result = await example_finish_post(
        #     state_machine, table, token, round_id, api_functions['finish_post']
        # )
        # if result[0] is None:
        #     return False

        logger.info(f"[{table['name']}] Round completed successfully")
        return True

    except Exception as e:
        logger.error(f"[{table['name']}] Round flow error: {e}")
        # Transition to broadcast on error
        validate_and_transition(
            state_machine,
            "broadcast_post",
            reason=f"Round flow exception: {e}",
            auto_resolved=False
        )
        return False


if __name__ == "__main__":
    # Example usage
    tables = [
        {"name": "PRD", "post_url": "https://api.example.com", "game_code": "SB"}
    ]
    
    # Initialize state machines
    state_machines = initialize_state_machines(tables)
    
    # Get state machine for a table
    state_machine = state_machines["PRD"]
    
    # Log state info
    info = state_machine.get_state_info()
    logger.info(f"State info: {info}")

