#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for log separation functionality
"""

import time
from log_redirector import log_mqtt, log_api, log_serial, log_console

def test_log_separation():
    """Test the log separation functionality"""
    print("Testing log separation functionality...")
    print("Check tmux windows to see separated logs:")
    print("  - log_mqtt: MQTT related logs")
    print("  - log_api: API related logs")
    print("  - log_serial: Serial related logs")
    print("")
    
    # Test MQTT logs
    log_mqtt("Testing MQTT log separation", "MQTT >>>")
    log_mqtt("MQTT connection established", "MQTT >>>")
    log_mqtt("MQTT message received: test_message", "MQTT >>>")
    
    # Test API logs
    log_api("Testing API log separation", "API >>>")
    log_api("API call: start_post_v2", "API >>>")
    log_api("API response: success", "API >>>")
    
    # Test Serial logs
    log_serial("Testing Serial log separation", "Serial >>>")
    log_serial("Serial command sent: *u 1", "Send <<<")
    log_serial("Serial response: *T u 1", "Receive >>>")
    
    # Test Console logs
    log_console("Testing Console log separation", "Console >>>")
    log_console("Important system message", "Console >>>")
    
    print("Log separation test completed!")
    print("Check the tmux windows to see the separated logs.")

if __name__ == "__main__":
    test_log_separation()
