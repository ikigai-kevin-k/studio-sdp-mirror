#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serial Port Diagnostics Tool
Helps identify and diagnose serial communication issues.
"""

import serial
import serial.tools.list_ports
import time
import threading
import statistics
from collections import deque
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SerialDiagnostics:
    """Diagnostic tool for serial port communication issues"""
    
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_running = False
        
        # Diagnostic data
        self.timing_data = deque(maxlen=1000)
        self.data_sizes = deque(maxlen=1000)
        self.error_count = 0
        self.start_time = None
        
    def connect(self) -> bool:
        """Connect to serial port"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                write_timeout=1.0,
                rtscts=True,  # Enable hardware flow control
                inter_byte_timeout=0.01
            )
            
            # Clear buffers
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            
            logger.info(f"Connected to {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def run_diagnostics(self, duration: int = 60) -> Dict:
        """
        Run comprehensive diagnostics for specified duration
        
        Args:
            duration: Duration in seconds to run diagnostics
            
        Returns:
            Dictionary containing diagnostic results
        """
        if not self.connect():
            return {"error": "Failed to connect"}
        
        self.is_running = True
        self.start_time = time.time()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        
        logger.info(f"Running diagnostics for {duration} seconds...")
        
        # Run for specified duration
        time.sleep(duration)
        
        self.is_running = False
        self.serial_conn.close()
        
        # Analyze results
        results = self._analyze_results()
        return results
    
    def _monitor_loop(self):
        """Monitor serial communication in background"""
        last_data_time = time.time()
        last_data_size = 0
        
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                current_time = time.time()
                
                # Check for available data
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    
                    if data:
                        # Record timing information
                        time_diff = current_time - last_data_time
                        self.timing_data.append(time_diff)
                        self.data_sizes.append(len(data))
                        
                        last_data_time = current_time
                        last_data_size = len(data)
                        
                        # Log data bursts
                        if len(data) > 100:  # Large data burst
                            logger.warning(f"Large data burst: {len(data)} bytes")
                            
                else:
                    # Check for silence periods
                    silence_duration = current_time - last_data_time
                    if silence_duration > 5.0:  # More than 5 seconds of silence
                        logger.warning(f"Long silence period: {silence_duration:.2f} seconds")
                        
                time.sleep(0.001)  # 1ms sleep
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Monitoring error: {e}")
                time.sleep(0.1)
    
    def _analyze_results(self) -> Dict:
        """Analyze collected diagnostic data"""
        if not self.timing_data:
            return {"error": "No data received during diagnostics"}
        
        # Calculate timing statistics
        timing_stats = {
            "min_interval": min(self.timing_data),
            "max_interval": max(self.timing_data),
            "avg_interval": statistics.mean(self.timing_data),
            "median_interval": statistics.median(self.timing_data),
            "std_interval": statistics.stdev(self.timing_data) if len(self.timing_data) > 1 else 0
        }
        
        # Calculate data size statistics
        size_stats = {
            "min_size": min(self.data_sizes),
            "max_size": max(self.data_sizes),
            "avg_size": statistics.mean(self.data_sizes),
            "median_size": statistics.median(self.data_sizes),
            "std_size": statistics.stdev(self.data_sizes) if len(self.data_sizes) > 1 else 0
        }
        
        # Detect patterns
        patterns = self._detect_patterns()
        
        # Calculate throughput
        total_duration = time.time() - self.start_time
        total_bytes = sum(self.data_sizes)
        throughput = total_bytes / total_duration if total_duration > 0 else 0
        
        return {
            "duration": total_duration,
            "total_data_points": len(self.timing_data),
            "total_bytes": total_bytes,
            "throughput_bps": throughput,
            "error_count": self.error_count,
            "timing_stats": timing_stats,
            "size_stats": size_stats,
            "patterns": patterns,
            "recommendations": self._generate_recommendations(timing_stats, size_stats, patterns)
        }
    
    def _detect_patterns(self) -> Dict:
        """Detect communication patterns and issues"""
        patterns = {
            "data_bursts": 0,
            "silence_periods": 0,
            "irregular_timing": False,
            "buffer_overflows": 0
        }
        
        if not self.timing_data:
            return patterns
        
        # Detect data bursts (very short intervals)
        burst_threshold = 0.001  # 1ms
        for interval in self.timing_data:
            if interval < burst_threshold:
                patterns["data_bursts"] += 1
        
        # Detect silence periods (very long intervals)
        silence_threshold = 1.0  # 1 second
        for interval in self.timing_data:
            if interval > silence_threshold:
                patterns["silence_periods"] += 1
        
        # Detect irregular timing (high standard deviation)
        if len(self.timing_data) > 1:
            avg_interval = statistics.mean(self.timing_data)
            std_interval = statistics.stdev(self.timing_data)
            if std_interval > avg_interval * 0.5:  # High variation
                patterns["irregular_timing"] = True
        
        return patterns
    
    def _generate_recommendations(self, timing_stats: Dict, size_stats: Dict, patterns: Dict) -> List[str]:
        """Generate recommendations based on diagnostic results"""
        recommendations = []
        
        # Timing recommendations
        if patterns["data_bursts"] > 10:
            recommendations.append("High number of data bursts detected. Consider enabling hardware flow control (RTS/CTS).")
        
        if patterns["silence_periods"] > 5:
            recommendations.append("Multiple silence periods detected. Check device power supply and connection stability.")
        
        if patterns["irregular_timing"]:
            recommendations.append("Irregular timing detected. Consider adjusting timeout settings and buffer sizes.")
        
        # Size recommendations
        if size_stats["max_size"] > 1000:
            recommendations.append("Large data packets detected. Consider implementing packet fragmentation.")
        
        if size_stats["std_size"] > size_stats["avg_size"] * 0.5:
            recommendations.append("Highly variable packet sizes. Consider implementing adaptive buffering.")
        
        # Error recommendations
        if self.error_count > 0:
            recommendations.append(f"{self.error_count} errors detected. Check cable quality and device compatibility.")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Communication appears stable. Consider monitoring for longer periods.")
        
        return recommendations

def print_diagnostic_results(results: Dict):
    """Print diagnostic results in a formatted way"""
    if "error" in results:
        print(f"Diagnostic Error: {results['error']}")
        return
    
    print("\n" + "="*60)
    print("SERIAL PORT DIAGNOSTIC RESULTS")
    print("="*60)
    
    print(f"\nTest Duration: {results['duration']:.2f} seconds")
    print(f"Total Data Points: {results['total_data_points']}")
    print(f"Total Bytes: {results['total_bytes']}")
    print(f"Throughput: {results['throughput_bps']:.2f} bytes/second")
    print(f"Errors: {results['error_count']}")
    
    print(f"\nTiming Statistics:")
    timing = results['timing_stats']
    print(f"  Min Interval: {timing['min_interval']:.6f} seconds")
    print(f"  Max Interval: {timing['max_interval']:.6f} seconds")
    print(f"  Average Interval: {timing['avg_interval']:.6f} seconds")
    print(f"  Median Interval: {timing['median_interval']:.6f} seconds")
    print(f"  Std Deviation: {timing['std_interval']:.6f} seconds")
    
    print(f"\nData Size Statistics:")
    size = results['size_stats']
    print(f"  Min Size: {size['min_size']} bytes")
    print(f"  Max Size: {size['max_size']} bytes")
    print(f"  Average Size: {size['avg_size']:.2f} bytes")
    print(f"  Median Size: {size['median_size']} bytes")
    print(f"  Std Deviation: {size['std_size']:.2f} bytes")
    
    print(f"\nDetected Patterns:")
    patterns = results['patterns']
    print(f"  Data Bursts: {patterns['data_bursts']}")
    print(f"  Silence Periods: {patterns['silence_periods']}")
    print(f"  Irregular Timing: {patterns['irregular_timing']}")
    print(f"  Buffer Overflows: {patterns['buffer_overflows']}")
    
    print(f"\nRecommendations:")
    for i, rec in enumerate(results['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    print("\n" + "="*60)

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python serial_diagnostics.py <port> [baudrate] [duration]")
        print("\nAvailable ports:")
        ports = serial.tools.list_ports.comports()
        for port in ports:
            print(f"  {port.device}: {port.description}")
        sys.exit(1)
    
    port = sys.argv[1]
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    
    print(f"Starting diagnostics on {port} at {baudrate} baud for {duration} seconds...")
    
    diagnostics = SerialDiagnostics(port, baudrate)
    results = diagnostics.run_diagnostics(duration)
    
    print_diagnostic_results(results)
