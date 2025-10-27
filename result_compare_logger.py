#!/usr/bin/env python3
"""
Result comparison logger for Speed Roulette SDP system
Compares serial port results with IDP detection results for the same round
"""

import os
import json
import time
import threading
from typing import Dict, Optional, Any
from datetime import datetime

class ResultCompareLogger:
    """Logger to compare serial port and IDP detection results for the same round"""
    
    def __init__(self, log_file: str = "logs/serial_idp_result_compare.log"):
        self.log_file = log_file
        self.results_cache = {}  # Store results by round_id
        self.lock = threading.Lock()
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Initialize log file with header if it doesn't exist
        if not os.path.exists(log_file):
            self._write_log_header()
    
    def _write_log_header(self):
        """Write header to log file"""
        header = """# Serial Port vs IDP Detection Result Comparison Log
# Format: [TIMESTAMP] ROUND_ID | SERIAL_RESULT | IDP_RESULT | MATCH_STATUS | NOTES
# ================================================================================
"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(header)
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    def _write_to_log(self, message: str):
        """Thread-safe write to log file"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{message}\n")
            f.flush()
    
    def log_serial_result(self, round_id: str, serial_result: Any, source: str = "SERIAL"):
        """
        Log serial port result for a round
        
        Args:
            round_id: Round identifier 
            serial_result: Result from serial port (*X;5 command)
            source: Source identifier (default: "SERIAL")
        """
        with self.lock:
            timestamp = self._get_timestamp()
            
            # Initialize round data if not exists
            if round_id not in self.results_cache:
                self.results_cache[round_id] = {
                    'serial_result': '__NOT_RECEIVED__',
                    'serial_timestamp': None,
                    'idp_result': '__NOT_RECEIVED__',
                    'idp_timestamp': None,
                    'comparison_logged': False
                }
            
            # Store serial result
            self.results_cache[round_id]['serial_result'] = serial_result
            self.results_cache[round_id]['serial_timestamp'] = timestamp
            
            print(f"[ResultCompare] Serial result logged: Round={round_id}, Result={serial_result}")
            
            # Check if we can compare now
            self._try_compare_results(round_id)
    
    def log_idp_result(self, round_id: str, idp_result: Any, source: str = "IDP"):
        """
        Log IDP detection result for a round
        
        Args:
            round_id: Round identifier
            idp_result: Result from IDP detection
            source: Source identifier (default: "IDP")
        """
        with self.lock:
            timestamp = self._get_timestamp()
            
            # Initialize round data if not exists  
            if round_id not in self.results_cache:
                self.results_cache[round_id] = {
                    'serial_result': '__NOT_RECEIVED__',
                    'serial_timestamp': None,
                    'idp_result': '__NOT_RECEIVED__',
                    'idp_timestamp': None,
                    'comparison_logged': False
                }
            
            # Store IDP result
            self.results_cache[round_id]['idp_result'] = idp_result
            self.results_cache[round_id]['idp_timestamp'] = timestamp
            
            print(f"[ResultCompare] IDP result logged: Round={round_id}, Result={idp_result}")
            
            # Check if we can compare now
            self._try_compare_results(round_id)
    
    def _try_compare_results(self, round_id: str):
        """
        Try to compare results if both serial and IDP results are available
        
        Args:
            round_id: Round identifier
        """
        if round_id not in self.results_cache:
            return
        
        round_data = self.results_cache[round_id]
        
        # Check if both results are available and not yet compared
        if not round_data['comparison_logged']:
            
            # Only compare if we have received both results (including None/empty values)
            if (round_data['serial_result'] != '__NOT_RECEIVED__' and 
                round_data['idp_result'] != '__NOT_RECEIVED__'):
                self._compare_and_log(round_id, round_data)
                round_data['comparison_logged'] = True
    
    def _compare_and_log(self, round_id: str, round_data: Dict):
        """
        Compare serial and IDP results and log the comparison
        
        Args:
            round_id: Round identifier
            round_data: Dictionary containing both results and timestamps
        """
        serial_result = round_data['serial_result']
        idp_result = round_data['idp_result']
        serial_time = round_data['serial_timestamp']
        idp_time = round_data['idp_timestamp']
        
        # Normalize results for comparison
        normalized_serial = self._normalize_result(serial_result)
        normalized_idp = self._normalize_result(idp_result)
        
        # Determine match status
        match_status = "MATCH" if normalized_serial == normalized_idp else "MISMATCH"
        
        # Generate notes
        notes = self._generate_comparison_notes(serial_result, idp_result, normalized_serial, normalized_idp)
        
        # Create log entry
        log_entry = (
            f"[{max(serial_time, idp_time)}] {round_id} | "
            f"SERIAL: {serial_result} | IDP: {idp_result} | "
            f"{match_status} | {notes}"
        )
        
        # Write to log file
        self._write_to_log(log_entry)
        
        # Print to console
        status_emoji = "✅" if match_status == "MATCH" else "❌"
        print(f"[ResultCompare] {status_emoji} {match_status}: Round {round_id}")
        print(f"  Serial: {serial_result} (at {serial_time})")
        print(f"  IDP:    {idp_result} (at {idp_time})")
        print(f"  Notes:  {notes}")
    
    def _normalize_result(self, result: Any) -> Optional[int]:
        """
        Normalize result to integer for comparison
        
        Args:
            result: Raw result value
            
        Returns:
            Normalized integer result or None if invalid
        """
        if result is None:
            return None
        
        # Handle different result formats
        if isinstance(result, int):
            return result if 0 <= result <= 36 else None
        
        if isinstance(result, str):
            if result.strip() == "" or result.lower() == "null":
                return None
            try:
                num = int(result.strip())
                return num if 0 <= num <= 36 else None
            except ValueError:
                return None
        
        if isinstance(result, list):
            if len(result) == 0 or result == ['']:
                return None
            try:
                # Take first element if it's a list
                first_element = result[0]
                if isinstance(first_element, (int, str)):
                    return self._normalize_result(first_element)
            except (IndexError, ValueError):
                return None
        
        return None
    
    def _generate_comparison_notes(self, serial_raw: Any, idp_raw: Any, 
                                 serial_norm: Optional[int], idp_norm: Optional[int]) -> str:
        """
        Generate notes for the comparison
        
        Args:
            serial_raw: Raw serial result
            idp_raw: Raw IDP result  
            serial_norm: Normalized serial result
            idp_norm: Normalized IDP result
            
        Returns:
            Notes string describing the comparison
        """
        notes = []
        
        # Check for null/empty results
        if serial_norm is None and idp_norm is None:
            notes.append("Both results null/empty")
        elif serial_norm is None:
            notes.append("Serial result null/empty")
        elif idp_norm is None:
            notes.append("IDP result null/empty")
        
        # Check for format differences
        if type(serial_raw) != type(idp_raw):
            notes.append(f"Format difference: Serial={type(serial_raw).__name__}, IDP={type(idp_raw).__name__}")
        
        # Check for valid roulette numbers
        if serial_norm is not None and not (0 <= serial_norm <= 36):
            notes.append(f"Invalid serial number: {serial_norm}")
        if idp_norm is not None and not (0 <= idp_norm <= 36):
            notes.append(f"Invalid IDP number: {idp_norm}")
        
        # Default note if no specific issues
        if not notes:
            if serial_norm == idp_norm:
                notes.append("Perfect match")
            else:
                notes.append("Value mismatch")
        
        return "; ".join(notes)
    
    def force_compare_round(self, round_id: str):
        """
        Force comparison for a round even if one result is missing
        
        Args:
            round_id: Round identifier
        """
        with self.lock:
            if round_id in self.results_cache and not self.results_cache[round_id]['comparison_logged']:
                round_data = self.results_cache[round_id]
                
                # Fill missing results with "NOT_RECEIVED"
                if round_data['serial_result'] == '__NOT_RECEIVED__':
                    round_data['serial_result'] = "NOT_RECEIVED"
                    round_data['serial_timestamp'] = self._get_timestamp()
                
                if round_data['idp_result'] == '__NOT_RECEIVED__':
                    round_data['idp_result'] = "NOT_RECEIVED"
                    round_data['idp_timestamp'] = self._get_timestamp()
                
                self._compare_and_log(round_id, round_data)
                round_data['comparison_logged'] = True
    
    def cleanup_old_rounds(self, max_rounds: int = 100):
        """
        Clean up old round data to prevent memory growth
        
        Args:
            max_rounds: Maximum number of rounds to keep in cache
        """
        with self.lock:
            if len(self.results_cache) > max_rounds:
                # Keep only the most recent rounds (by creation order)
                round_ids = list(self.results_cache.keys())
                for old_round_id in round_ids[:-max_rounds]:
                    del self.results_cache[old_round_id]
                
                print(f"[ResultCompare] Cleaned up {len(round_ids) - max_rounds} old rounds from cache")

# Global instance
_result_compare_logger = None

def get_result_compare_logger() -> ResultCompareLogger:
    """Get or create the global result compare logger instance"""
    global _result_compare_logger
    if _result_compare_logger is None:
        _result_compare_logger = ResultCompareLogger()
    return _result_compare_logger

def log_serial_result(round_id: str, result: Any):
    """Convenience function to log serial result"""
    logger = get_result_compare_logger()
    logger.log_serial_result(round_id, result)

def log_idp_result(round_id: str, result: Any):
    """Convenience function to log IDP result"""
    logger = get_result_compare_logger()
    logger.log_idp_result(round_id, result)
