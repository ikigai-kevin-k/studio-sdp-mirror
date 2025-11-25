"""
Table API State Machine Module

This module provides state machine functionality for managing table API state
transitions in main_speed.py, main_vip.py, and main_sicbo.py.

State Flow:
- Normal flow: start -> deal -> bet-stopped -> finished -> start
- Exception flow: start/deal/bet-stopped/finished -> broadcast
  - If auto-resolved: follow normal flow rules for next step
  - If not auto-resolved: pause -> cancel -> start -> normal flow
"""

from state_machine.table_api_state_machine import (
    TableAPIStateMachine,
    GameState,
    StateTransitionError,
    MultiEnvironmentStateManager,
    api_status_to_game_state,
)
from state_machine.state_validator import (
    create_state_machine_for_table,
    validate_and_transition,
    handle_broadcast_result,
    get_state_machine_wrapper,
    log_state_info,
    create_multi_environment_manager,
    check_environment_state_before_post,
    initialize_and_sync_environments,
)

__all__ = [
    "TableAPIStateMachine",
    "GameState",
    "StateTransitionError",
    "MultiEnvironmentStateManager",
    "api_status_to_game_state",
    "create_state_machine_for_table",
    "validate_and_transition",
    "handle_broadcast_result",
    "get_state_machine_wrapper",
    "log_state_info",
    "create_multi_environment_manager",
    "check_environment_state_before_post",
    "initialize_and_sync_environments",
]

