#!/usr/bin/env python3
"""
Mock ws_sb module for testing purposes
This module provides the functions needed by ws_sb_update.py
"""

import logging

logger = logging.getLogger(__name__)


def test_sbo_001_device_info():
    """Mock function for testing device info"""
    logger.info("Mock test_sbo_001_device_info function called")
    return {"device_id": "SBO-001", "status": "mock", "version": "1.0.0"}


# Add other functions as needed for testing
def get_device_status():
    """Mock function for getting device status"""
    return {
        "maintenance": False,
        "zCam": "up",
        "broker": "up",
        "sdp": "up",
        "shaker": "up",
        "idp": "up",
    }
