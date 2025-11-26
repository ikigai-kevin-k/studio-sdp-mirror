#!/usr/bin/env python3
"""
Generic table API error signal handler module.
Supports tracking error signal send count and signalType (warn/error).
Compatible with main_sicbo.py, main_speed.py, and main_vip.py.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Optional, Callable
from enum import Enum

# Add the current directory to Python path to import error signal modules
sys.path.append(os.path.dirname(__file__))

from ws_err_sig_sbe import ErrorMsgId, ErrorSignalClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class TableAPIErrorType(Enum):
    """Table API error types"""
    NO_START = "NO_START"
    NO_BETSTOP = "NO_BETSTOP"
    NO_DEAL = "NO_DEAL"
    NO_FINISH = "NO_FINISH"


class TableAPIErrorSignalManager:
    """Manager for tracking and sending table API error signals"""
    
    def __init__(self, table_id: str = "SBO-001", device_id: str = "ASB-001-1"):
        """
        Initialize error signal manager
        
        Args:
            table_id: Table ID (default: SBO-001 for Sicbo)
            device_id: Device ID (default: ASB-001-1 for Sicbo)
        """
        self.table_id = table_id
        self.device_id = device_id
        
        # Track error signal send count for each error type
        # Key: error_type, Value: send_count (0 = not sent, 1 = first (warn), 2 = second (error))
        self._error_signal_counts: Dict[TableAPIErrorType, int] = {
            TableAPIErrorType.NO_START: 0,
            TableAPIErrorType.NO_BETSTOP: 0,
            TableAPIErrorType.NO_DEAL: 0,
            TableAPIErrorType.NO_FINISH: 0,
        }
        
        # Error metadata mapping
        self._error_metadata = {
            TableAPIErrorType.NO_START: {
                "title": "NO START",
                "description": "Table API start_post failed",
                "code": "ASE.2",
                "suggestion": "Check table API connection and status",
            },
            TableAPIErrorType.NO_BETSTOP: {
                "title": "NO BETSTOP",
                "description": "Table API bet_stop_post failed",
                "code": "ASE.3",
                "suggestion": "Check table API connection and status",
            },
            TableAPIErrorType.NO_DEAL: {
                "title": "NO DEAL",
                "description": "Table API deal_post failed",
                "code": "ASE.4",
                "suggestion": "Check table API connection and status",
            },
            TableAPIErrorType.NO_FINISH: {
                "title": "NO FINISH",
                "description": "Table API finish_post failed",
                "code": "ASE.5",
                "suggestion": "Check table API connection and status",
            },
        }
    
    def reset_error_signal_count(self, error_type: TableAPIErrorType):
        """Reset error signal count for a specific error type"""
        self._error_signal_counts[error_type] = 0
        logger.debug(f"Reset error signal count for {error_type.value}")
    
    def reset_all_error_signal_counts(self):
        """Reset all error signal counts"""
        for error_type in TableAPIErrorType:
            self._error_signal_counts[error_type] = 0
        logger.debug("Reset all error signal counts")
    
    def _get_signal_type(self, error_type: TableAPIErrorType, retry_count: int, max_retries: int) -> str:
        """
        Determine signal type based on retry count
        
        Args:
            error_type: Type of error
            retry_count: Current retry count (0-based, so retry_count=0 means first attempt)
            max_retries: Maximum retry count
            
        Returns:
            'warn' if within max_retries, 'error' if exceeded max_retries
        """
        # If retry_count < max_retries, still within retry limit, send 'warn'
        # If retry_count >= max_retries, exceeded retry limit, send 'error'
        if retry_count < max_retries:
            return "warn"
        else:
            return "error"
    
    async def send_table_api_error_signal(
        self,
        error_type: TableAPIErrorType,
        retry_count: int,
        max_retries: int,
        server_url: Optional[str] = None,
        token: Optional[str] = None,
    ) -> bool:
        """
        Send table API error signal with appropriate signalType
        
        Args:
            error_type: Type of error (NO_START, NO_BETSTOP, NO_DEAL, NO_FINISH)
            retry_count: Current retry count
            max_retries: Maximum retry count
            server_url: WebSocket server URL (optional, uses default if not provided)
            token: Authentication token (optional, uses default if not provided)
            
        Returns:
            True if error signal sent successfully, False otherwise
        """
        # Determine signal type based on retry count
        signal_type = self._get_signal_type(error_type, retry_count, max_retries)
        
        # Update error signal count based on signal type
        # For warn signals: only send once (first time)
        # For error signals: only send once (when max_retries exceeded)
        current_count = self._error_signal_counts[error_type]
        should_send = False
        
        if signal_type == "warn":
            # Only send warn signal once (first time)
            if current_count == 0:
                self._error_signal_counts[error_type] = 1
                should_send = True
            else:
                logger.info(
                    f"Warn signal for {error_type.value} already sent, skipping"
                )
                return False
        elif signal_type == "error":
            # Only send error signal once (when max_retries exceeded)
            if current_count < 2:
                self._error_signal_counts[error_type] = 2
                should_send = True
            else:
                logger.info(
                    f"Error signal for {error_type.value} already sent, skipping"
                )
                return False
        
        if not should_send:
            return False
        
        # Use default CIT configuration if not provided
        if server_url is None:
            server_url = "wss://studio-api.iki-cit.cc/v1/ws"
        if token is None:
            token = "0000"
        
        # Create error signal client
        client = ErrorSignalClient(server_url, self.table_id, self.device_id, token)
        
        try:
            # Connect to the table
            logger.info(f"Connecting to {self.table_id} for error signal...")
            if not await client.connect():
                logger.error(f"Failed to connect to {self.table_id}")
                return False
            
            logger.info(f"Successfully connected to {self.table_id}")
            
            # Get error metadata
            metadata = self._error_metadata[error_type].copy()
            metadata["signalType"] = signal_type
            
            # Create error signal according to spec
            signal_data = {
                "msgId": ErrorMsgId[error_type.value].value,
                "content": metadata["description"],
                "metadata": metadata,
            }
            
            # Send the error signal
            logger.info(
                f"Sending {error_type.value} error signal with signalType={signal_type} "
                f"(retry {retry_count}/{max_retries})..."
            )
            logger.info(f"   - Signal: {signal_data}")
            
            success = await client.send_error_signal(signal_data)
            
            if success:
                logger.info(
                    f"✅ {error_type.value} error signal sent successfully "
                    f"with signalType={signal_type}"
                )
            else:
                logger.error(f"❌ Failed to send {error_type.value} error signal")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error during {error_type.value} error signal sending: {e}")
            return False
            
        finally:
            # Disconnect from server
            try:
                await client.disconnect()
                logger.info(f"✅ Disconnected from {self.table_id}")
            except Exception as e:
                logger.error(f"❌ Error disconnecting from {self.table_id}: {e}")


# Global instances for different table IDs
_global_error_signal_managers: Dict[str, TableAPIErrorSignalManager] = {}


def get_error_signal_manager(
    table_id: str = "SBO-001", device_id: str = "ASB-001-1"
) -> TableAPIErrorSignalManager:
    """
    Get or create error signal manager instance for a specific table ID
    
    Args:
        table_id: Table ID
        device_id: Device ID
        
    Returns:
        TableAPIErrorSignalManager instance
    """
    global _global_error_signal_managers
    # Use table_id as key to ensure each table has its own manager instance
    if table_id not in _global_error_signal_managers:
        _global_error_signal_managers[table_id] = TableAPIErrorSignalManager(
            table_id, device_id
        )
    return _global_error_signal_managers[table_id]


async def send_table_api_error_signal(
    error_type: str,
    retry_count: int,
    max_retries: int,
    table_id: str = "SBO-001",
    device_id: str = "ASB-001-1",
    server_url: Optional[str] = None,
    token: Optional[str] = None,
) -> bool:
    """
    Convenience function to send table API error signal
    
    Args:
        error_type: Error type string ("NO_START", "NO_BETSTOP", "NO_DEAL", "NO_FINISH")
        retry_count: Current retry count
        max_retries: Maximum retry count
        table_id: Table ID
        device_id: Device ID
        server_url: WebSocket server URL (optional)
        token: Authentication token (optional)
        
    Returns:
        True if error signal sent successfully, False otherwise
    """
    manager = get_error_signal_manager(table_id, device_id)
    try:
        error_type_enum = TableAPIErrorType[error_type]
        return await manager.send_table_api_error_signal(
            error_type_enum, retry_count, max_retries, server_url, token
        )
    except KeyError:
        logger.error(f"Invalid error type: {error_type}")
        return False


def reset_error_signal_count(
    error_type: str, table_id: str = "SBO-001", device_id: str = "ASB-001-1"
):
    """
    Reset error signal count for a specific error type
    
    Args:
        error_type: Error type string ("NO_START", "NO_BETSTOP", "NO_DEAL", "NO_FINISH")
        table_id: Table ID
        device_id: Device ID
    """
    manager = get_error_signal_manager(table_id, device_id)
    try:
        error_type_enum = TableAPIErrorType[error_type]
        manager.reset_error_signal_count(error_type_enum)
    except KeyError:
        logger.error(f"Invalid error type: {error_type}")


def reset_all_error_signal_counts(
    table_id: str = "SBO-001", device_id: str = "ASB-001-1"
):
    """
    Reset all error signal counts
    
    Args:
        table_id: Table ID
        device_id: Device ID
    """
    manager = get_error_signal_manager(table_id, device_id)
    manager.reset_all_error_signal_counts()

