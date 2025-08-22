"""
Slack notification package

This package provides complete Slack notification functionality, including:
- Basic message sending
- Error and success notifications
- Rich message formatting
- Multiple authentication methods

Main components:
- slack_notifier: Main Slack notification class
- Utility functions: Quickly send notifications of common types
- Test scripts: Verify functionality is working properly
"""

from .slack_notifier import (
    SlackNotifier,
    send_error_to_slack,
    send_success_to_slack
)

__version__ = "1.4.0"
__author__ = "SDP Roulette Team"

# Provide convenient import methods
__all__ = [
    "SlackNotifier",
    "send_error_to_slack", 
    "send_success_to_slack"
]

# Version information
VERSION = __version__

# Package description
DESCRIPTION = "Complete Slack notification system for SDP Roulette"
