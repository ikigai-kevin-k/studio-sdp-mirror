"""
TableAPI Error Summary Module

This module provides functionality to:
- Record tableAPI errors by environment and API type
- Generate summary reports of errors over time periods
- Send scheduled summary reports to Slack
"""

from .error_tracker import (
    record_table_api_error,
    get_error_summary,
    clear_old_errors,
    ErrorTracker,
)

from .summary_scheduler import (
    start_summary_scheduler,
    stop_summary_scheduler,
    send_summary_report,
)

__all__ = [
    "record_table_api_error",
    "get_error_summary",
    "clear_old_errors",
    "ErrorTracker",
    "start_summary_scheduler",
    "stop_summary_scheduler",
    "send_summary_report",
]

