"""
Roulette MQTT Detect Module

This module provides Roulette MQTT detect functionality
to avoid circular import issues with main_speed.py
"""

import asyncio
import time
from typing import Optional, Tuple, Any
from mqtt.complete_system import CompleteMQTTSystem
from mqtt.config_manager import GameType, Environment, BrokerConfig

# Import MQTT logging function
try:
    from log_redirector import log_mqtt
    MQTT_LOGGING_AVAILABLE = True
except ImportError:
    MQTT_LOGGING_AVAILABLE = False
    def log_mqtt(message):
        # Fallback if log_mqtt is not available
        print(f"[MQTT] {message}")


# Global MQTT system instance
_roulette_mqtt_system: Optional[CompleteMQTTSystem] = None
_detect_count = 0


async def initialize_roulette_mqtt_system():
    """Initialize Roulette MQTT detect system"""
    global _roulette_mqtt_system
    
    try:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Initializing Roulette MQTT detect system...")
        
        # Create broker configuration for ARO-001
        broker_configs = [
            BrokerConfig(
                broker="192.168.88.50",
                port=1883,
                username="PFC",
                password="wago",
                priority=1
            )
        ]
        
        # Create complete MQTT system
        _roulette_mqtt_system = CompleteMQTTSystem(
            game_type=GameType.ROULETTE,
            environment=Environment.DEVELOPMENT,
            enable_connection_pooling=False,
            enable_message_processing=True
        )
        
        # Override configuration
        _roulette_mqtt_system.config.brokers = broker_configs
        _roulette_mqtt_system.config.game_config.command_topic = "ikg/idp/ARO-001/command"
        _roulette_mqtt_system.config.game_config.response_topic = "ikg/idp/ARO-001/response"
        _roulette_mqtt_system.config.game_config.timeout = 30
        _roulette_mqtt_system.config.client_id = "roulette_aro_main_client"
        _roulette_mqtt_system.config.default_username = "PFC"
        _roulette_mqtt_system.config.default_password = "wago"
        
        # Initialize system
        await _roulette_mqtt_system.initialize()
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Roulette MQTT detect system initialized successfully")
        return True
        
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error initializing Roulette MQTT system: {e}")
        _roulette_mqtt_system = None
        return False


async def roulette_detect_result(round_id: Optional[str] = None, input_stream: Optional[str] = None) -> Tuple[bool, Optional[Any]]:
    """Call Roulette detect result function"""
    global _roulette_mqtt_system, _detect_count
    
    if _roulette_mqtt_system is None:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Roulette MQTT system not initialized, skipping detect")
        return False, None
    
    try:
        _detect_count += 1
        
        # Generate round_id if not provided
        if not round_id:
            round_id = f"ARO-001-{int(time.time())}"
        
        # Use default input stream if not provided
        if not input_stream:
            input_stream = "rtmp://192.168.88.50:1935/live/r10_sr"
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Calling Roulette detect (attempt #{_detect_count})")
        log_mqtt(f"Calling Roulette detect (attempt #{_detect_count})")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Round ID: {round_id}")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Input Stream: {input_stream}")
        
        # Call detect function
        success, result = await _roulette_mqtt_system.detect(
            round_id,
            input_stream=input_stream
        )
        
        if success:
            # Detailed result analysis
            if (result is not None and result != "" and result != [] and result != [''] and 
                not isinstance(result, dict) and str(result) != "null"):
                # Valid result received (not empty, not dict, not null)
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Roulette detect successful: {result}")
                log_mqtt(f"🎯 IDP Detection SUCCESS: {result}")
            elif result == [''] or result == []:
                # Empty result - likely ball still moving
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Roulette detect completed but result is empty list")
                log_mqtt("⚠️ IDP Detection: Empty result (ball likely still moving)")
            elif result is None or result == "null":
                # Null result - detection timing or confidence issue
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Roulette detect completed but result is null")
                log_mqtt("⚠️ IDP Detection: Null result (detection timing/confidence issue)")
            else:
                # Unknown result format
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Roulette detect completed with unexpected result: {result}")
                log_mqtt(f"⚠️ IDP Detection: Unexpected result format: {result}")
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Roulette detect failed")
            log_mqtt("❌ IDP Detection FAILED (MQTT communication error)")
        
        return success, result
        
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error in Roulette detect: {e}")
        log_mqtt(f"❌ Error in Roulette detect: {e}")
        return False, None


async def cleanup_roulette_mqtt_system():
    """Cleanup Roulette MQTT system"""
    global _roulette_mqtt_system
    
    if _roulette_mqtt_system:
        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Cleaning up Roulette MQTT system...")
            await _roulette_mqtt_system.cleanup()
            _roulette_mqtt_system = None
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Roulette MQTT system cleanup completed")
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error cleaning up Roulette MQTT system: {e}")


def call_roulette_detect_async(round_id: Optional[str] = None, input_stream: Optional[str] = None):
    """Synchronous wrapper for calling Roulette detect in a separate thread"""
    try:
        success, result = asyncio.run(roulette_detect_result(round_id, input_stream))
        return success, result
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error in async detect call: {e}")
        log_mqtt(f"❌ Error in async detect call: {e}")
        return False, None

