#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual Hot Reload Manager for main_speed.py
Triggers module reload when 'reload' command is received
"""

import os
import sys
import time
import threading
import importlib
import signal
from pathlib import Path
from log_redirector import log_console, get_timestamp

class ManualHotReloadManager:
    """Manages manual hot reloading of Python modules"""
    
    def __init__(self):
        self.reload_requested = False
        self.reload_lock = threading.Lock()
        self.running = False
        
        # Modules to reload (in dependency order)
        self.reload_modules = [
            'log_redirector',
            'serial_comm.serialUtils',
            'serial_comm.serialIO',
            'table_api.sr.api_v2_sr',
            'table_api.sr.api_v2_uat_sr',
            'table_api.sr.api_v2_prd_sr',
            'table_api.sr.api_v2_stg_sr',
            'table_api.sr.api_v2_qat_sr',
            'table_api.sr.api_v2_sr_5',
            'table_api.sr.api_v2_sr_6',
            'table_api.sr.api_v2_sr_7',
            'table_api.sr.api_v2_prd_sr_5',
            'table_api.sr.api_v2_prd_sr_6',
            'table_api.sr.api_v2_prd_sr_7',
            'main_speed'
        ]
        
        # Create reload trigger file in user home directory
        home_dir = os.path.expanduser("~")
        self.reload_trigger_file = os.path.join(home_dir, "sdp_hotreload_trigger")
        
    def start(self):
        """Start the manual hot reload manager"""
        if self.running:
            return
            
        self.running = True
        
        # Create trigger file
        with open(self.reload_trigger_file, 'w') as f:
            f.write("0")  # 0 = no reload requested
        
        # Start reload processing thread
        reload_thread = threading.Thread(target=self._monitor_reload_requests, daemon=True)
        reload_thread.start()
        
        log_console("Manual hot reload manager started", "HOTRELOAD >>>")
        log_console(f"Trigger file: {self.reload_trigger_file}", "HOTRELOAD >>>")
        log_console("Use './reload' to trigger reload", "HOTRELOAD >>>")
        
    def stop(self):
        """Stop the manual hot reload manager"""
        if not self.running:
            return
            
        self.running = False
        
        # Clean up trigger file
        try:
            if os.path.exists(self.reload_trigger_file):
                os.remove(self.reload_trigger_file)
        except Exception as e:
            log_console(f"Error removing trigger file: {e}", "HOTRELOAD >>>")
            
        log_console("Manual hot reload manager stopped", "HOTRELOAD >>>")
        
    def _monitor_reload_requests(self):
        """Monitor for reload requests in background thread"""
        while self.running:
            try:
                if os.path.exists(self.reload_trigger_file):
                    with open(self.reload_trigger_file, 'r') as f:
                        content = f.read().strip()
                        
                    if content == "reload":
                        log_console("Reload request detected, processing...", "HOTRELOAD >>>")
                        self._reload_all_modules()
                        
                        # Reset trigger file
                        with open(self.reload_trigger_file, 'w') as f:
                            f.write("0")
                            
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                log_console(f"Error in reload monitoring: {e}", "HOTRELOAD >>>")
                time.sleep(1)
                
    def _reload_all_modules(self):
        """Reload all modules in dependency order"""
        log_console("Starting module reload process...", "HOTRELOAD >>>")
        
        reloaded_count = 0
        failed_count = 0
        
        for module_name in self.reload_modules:
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                    log_console(f"✅ Reloaded: {module_name}", "HOTRELOAD >>>")
                    reloaded_count += 1
                else:
                    log_console(f"⚠️  Module not loaded: {module_name}", "HOTRELOAD >>>")
                    
            except Exception as e:
                log_console(f"❌ Failed to reload {module_name}: {e}", "HOTRELOAD >>>")
                failed_count += 1
                
        log_console(f"Reload complete: {reloaded_count} successful, {failed_count} failed", "HOTRELOAD >>>")
        
    def trigger_reload(self):
        """Manually trigger a reload"""
        try:
            with open(self.reload_trigger_file, 'w') as f:
                f.write("reload")
            log_console("Reload trigger sent", "HOTRELOAD >>>")
        except Exception as e:
            log_console(f"Failed to trigger reload: {e}", "HOTRELOAD >>>")

# Global manual hot reload manager instance
manual_hot_reload_manager = ManualHotReloadManager()

def start_manual_hot_reload():
    """Start manual hot reload manager"""
    manual_hot_reload_manager.start()

def stop_manual_hot_reload():
    """Stop manual hot reload manager"""
    manual_hot_reload_manager.stop()

def trigger_manual_reload():
    """Manually trigger a reload"""
    manual_hot_reload_manager.trigger_reload()

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        log_console(f"Received signal {signum}, shutting down hot reload manager", "HOTRELOAD >>>")
        stop_manual_hot_reload()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    # Test the manual hot reload manager
    setup_signal_handlers()
    start_manual_hot_reload()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_manual_hot_reload()
