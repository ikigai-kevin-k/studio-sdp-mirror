#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serial communication module for Speed Roulette Controller
Contains serial I/O and utility functions
"""

from .serialIO import read_from_serial
from .serialUtils import (
    create_serial_connection,
    check_hardware_available,
    load_config,
    get_timestamp,
    log_with_color,
    # Add other commonly used functions as needed
)

__all__ = [
    "read_from_serial",
    "create_serial_connection",
    "check_hardware_available",
    "load_config",
    "get_timestamp",
    "log_with_color",
]
