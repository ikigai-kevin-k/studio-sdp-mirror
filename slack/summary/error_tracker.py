"""
TableAPI Error Tracker

Tracks tableAPI errors by environment and API type.
Errors are stored in memory and can be queried for summary reports.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from enum import Enum

# Thread-safe error storage
_error_storage_lock = threading.Lock()
_error_storage: Dict[str, List[Dict]] = defaultdict(list)

# Supported environments
ENVIRONMENTS = ["CIT", "QAT", "UAT", "STG", "PRD"]

# Supported API types
API_TYPES = ["start", "betStop", "deal", "finish"]


class ErrorTracker:
    """Thread-safe error tracker for tableAPI errors"""

    def __init__(self):
        """Initialize error tracker"""
        self.lock = threading.Lock()
        self.errors: List[Dict] = []

    def record_error(
        self,
        environment: str,
        api_type: str,
        table_name: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """
        Record a tableAPI error

        Args:
            environment: Environment name (CIT, QAT, UAT, STG, PRD)
            api_type: API type (start, betStop, deal, finish)
            table_name: Optional table name
            error_message: Optional error message
        """
        if environment not in ENVIRONMENTS:
            # Normalize environment names
            if "CIT" in environment.upper():
                environment = "CIT"
            elif "QAT" in environment.upper():
                environment = "QAT"
            elif "UAT" in environment.upper():
                environment = "UAT"
            elif "STG" in environment.upper():
                environment = "STG"
            elif "PRD" in environment.upper():
                environment = "PRD"
            else:
                # Default to CIT if unknown
                environment = "CIT"

        if api_type not in API_TYPES:
            # Normalize API type names
            api_lower = api_type.lower()
            if "start" in api_lower:
                api_type = "start"
            elif "bet" in api_lower and "stop" in api_lower:
                api_type = "betStop"
            elif "deal" in api_lower:
                api_type = "deal"
            elif "finish" in api_lower:
                api_type = "finish"
            else:
                # Default to start if unknown
                api_type = "start"

        error_record = {
            "timestamp": datetime.now(),
            "environment": environment,
            "api_type": api_type,
            "table_name": table_name,
            "error_message": error_message,
        }

        with self.lock:
            self.errors.append(error_record)

    def get_summary(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, Dict[str, int]]:
        """
        Get error summary for a time period

        Args:
            start_time: Start of time period
            end_time: End of time period

        Returns:
            Dictionary with structure:
            {
                "CIT": {"start": 5, "betStop": 2, "deal": 1, "finish": 0},
                "QAT": {"start": 3, "betStop": 1, "deal": 0, "finish": 0},
                ...
            }
        """
        summary: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )

        with self.lock:
            for error in self.errors:
                error_time = error["timestamp"]
                if start_time <= error_time <= end_time:
                    env = error["environment"]
                    api = error["api_type"]
                    summary[env][api] += 1

        # Ensure all environments and API types are included
        result = {}
        for env in ENVIRONMENTS:
            result[env] = {}
            for api in API_TYPES:
                result[env][api] = summary[env][api]

        return result

    def clear_old_errors(self, before_time: datetime):
        """
        Clear errors older than specified time

        Args:
            before_time: Clear errors before this time
        """
        with self.lock:
            self.errors = [
                error
                for error in self.errors
                if error["timestamp"] >= before_time
            ]

    def get_error_count(self) -> int:
        """Get total number of errors in storage"""
        with self.lock:
            return len(self.errors)


# Global error tracker instance
_global_error_tracker = ErrorTracker()


def record_table_api_error(
    environment: str,
    api_type: str,
    table_name: Optional[str] = None,
    error_message: Optional[str] = None,
):
    """
    Record a tableAPI error (global function)

    Args:
        environment: Environment name (CIT, QAT, UAT, STG, PRD)
        api_type: API type (start, betStop, deal, finish)
        table_name: Optional table name
        error_message: Optional error message
    """
    _global_error_tracker.record_error(
        environment, api_type, table_name, error_message
    )


def get_error_summary(
    start_time: datetime, end_time: datetime
) -> Dict[str, Dict[str, int]]:
    """
    Get error summary for a time period (global function)

    Args:
        start_time: Start of time period
        end_time: End of time period

    Returns:
        Dictionary with error counts by environment and API type
    """
    return _global_error_tracker.get_summary(start_time, end_time)


def clear_old_errors(before_time: datetime):
    """
    Clear errors older than specified time (global function)

    Args:
        before_time: Clear errors before this time
    """
    _global_error_tracker.clear_old_errors(before_time)


def get_error_tracker() -> ErrorTracker:
    """Get the global error tracker instance"""
    return _global_error_tracker

