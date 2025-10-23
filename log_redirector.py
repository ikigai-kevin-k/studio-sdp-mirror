#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log Redirection Module for SDP Roulette System
Separates different types of logs into different tmux windows
"""

import os
import threading
from datetime import datetime
from typing import Optional


class LogRedirector:
    """Redirect logs to different tmux windows based on log type"""
    
    def __init__(self):
        # Use project directory instead of /tmp to avoid permission issues
        project_dir = os.path.dirname(os.path.abspath(__file__))
        self.log_files = {
            'mqtt': os.path.join(project_dir, 'logs', 'sdp_mqtt.log'),
            'api': os.path.join(project_dir, 'logs', 'sdp_api.log'), 
            'serial': os.path.join(project_dir, 'logs', 'sdp_serial.log')
        }
        
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(project_dir, 'logs')
        if not os.path.exists(logs_dir):
            try:
                os.makedirs(logs_dir, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create logs directory: {e}")
                # Fallback to /tmp with different names
                import tempfile
                temp_dir = tempfile.gettempdir()
                self.log_files = {
                    'mqtt': os.path.join(temp_dir, f'sdp_mqtt_{os.getpid()}.log'),
                    'api': os.path.join(temp_dir, f'sdp_api_{os.getpid()}.log'), 
                    'serial': os.path.join(temp_dir, f'sdp_serial_{os.getpid()}.log')
                }
        
        # Create log files if they don't exist
        for log_file in self.log_files.values():
            try:
                if not os.path.exists(log_file):
                    with open(log_file, 'w') as f:
                        f.write(f"# {log_file} - Created at {datetime.now()}\n")
            except Exception as e:
                print(f"Warning: Could not create log file {log_file}: {e}")
        
        # Thread lock for thread-safe writing
        self.lock = threading.Lock()
    
    def get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def write_log(self, log_type: str, message: str, direction: str = "") -> None:
        """
        Write log message to appropriate log file
        
        Args:
            log_type: Type of log ('mqtt', 'api', 'serial')
            message: Log message
            direction: Direction indicator (e.g., "Send <<<", "Receive >>>")
        """
        if log_type not in self.log_files:
            print(f"Warning: Unknown log type '{log_type}', using console output")
            print(f"[{self.get_timestamp()}] {direction} {message}")
            return
        
        log_file = self.log_files[log_type]
        timestamp = self.get_timestamp()
        
        with self.lock:
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    if direction:
                        f.write(f"[{timestamp}] {direction} {message}\n")
                    else:
                        f.write(f"[{timestamp}] {message}\n")
            except PermissionError as e:
                print(f"Permission denied writing to {log_file}: {e}")
                # Fallback to console output
                if direction:
                    print(f"[{timestamp}] {direction} {message}")
                else:
                    print(f"[{timestamp}] {message}")
            except Exception as e:
                print(f"Error writing to {log_file}: {e}")
                # Fallback to console output
                if direction:
                    print(f"[{timestamp}] {direction} {message}")
                else:
                    print(f"[{timestamp}] {message}")
    
    def log_mqtt(self, message: str, direction: str = "") -> None:
        """Log MQTT related messages"""
        self.write_log('mqtt', message, direction)
    
    def log_api(self, message: str, direction: str = "") -> None:
        """Log API related messages"""
        self.write_log('api', message, direction)
    
    def log_serial(self, message: str, direction: str = "") -> None:
        """Log Serial related messages"""
        self.write_log('serial', message, direction)
    
    def log_console(self, message: str, direction: str = "") -> None:
        """Log to console (for important messages that should always be visible)"""
        timestamp = self.get_timestamp()
        if direction:
            print(f"[{timestamp}] {direction} {message}")
        else:
            print(f"[{timestamp}] {message}")


# Global log redirector instance
log_redirector = LogRedirector()


# Convenience functions for easy import
def log_mqtt(message: str, direction: str = "") -> None:
    """Log MQTT related messages"""
    log_redirector.log_mqtt(message, direction)


def log_api(message: str, direction: str = "") -> None:
    """Log API related messages"""
    log_redirector.log_api(message, direction)


def log_serial(message: str, direction: str = "") -> None:
    """Log Serial related messages"""
    log_redirector.log_serial(message, direction)


def log_console(message: str, direction: str = "") -> None:
    """Log to console (for important messages)"""
    log_redirector.log_console(message, direction)


def get_timestamp() -> str:
    """Get current timestamp"""
    return log_redirector.get_timestamp()


# Test function
def test_log_redirector():
    """Test the log redirector functionality"""
    print("Testing log redirector...")
    
    log_mqtt("Test MQTT message", "MQTT >>>")
    log_api("Test API message", "API >>>")
    log_serial("Test Serial message", "Serial >>>")
    log_console("Test Console message", "Console >>>")
    
    print("Log redirector test completed. Check tmux windows for output.")


if __name__ == "__main__":
    test_log_redirector()
