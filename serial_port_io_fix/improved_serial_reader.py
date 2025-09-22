#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Improved Serial Port Reader/Writer with better buffer management
and error handling to prevent data blocking issues.
"""

import serial
import serial.tools.list_ports
import threading
import time
import queue
import logging
from typing import Optional, Callable
from dataclasses import dataclass
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s.%(msecs)03d] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@dataclass
class SerialConfig:
    """Serial port configuration parameters"""
    port: str
    baudrate: int = 115200
    timeout: float = 0.1  # Short timeout for non-blocking reads
    write_timeout: float = 1.0
    bytesize: int = serial.EIGHTBITS
    parity: str = serial.PARITY_NONE
    stopbits: int = serial.STOPBITS_ONE
    xonxoff: bool = False  # Software flow control
    rtscts: bool = True    # Hardware flow control
    dsrdtr: bool = False
    inter_byte_timeout: float = 0.01  # Timeout between bytes

class ImprovedSerialReader:
    """
    Improved serial port reader with better buffer management
    and error handling to prevent blocking issues.
    """
    
    def __init__(self, config: SerialConfig, data_callback: Optional[Callable] = None):
        self.config = config
        self.data_callback = data_callback
        self.serial_conn: Optional[serial.Serial] = None
        self.is_running = False
        self.read_thread: Optional[threading.Thread] = None
        self.write_queue = queue.Queue(maxsize=100)  # Limit write queue size
        self.write_thread: Optional[threading.Thread] = None
        
        # Buffer management
        self.read_buffer = deque(maxlen=1000)  # Circular buffer
        self.buffer_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'bytes_received': 0,
            'bytes_sent': 0,
            'errors': 0,
            'buffer_overflows': 0,
            'last_activity': time.time()
        }
        
    def connect(self) -> bool:
        """Connect to serial port with error handling"""
        try:
            # Close existing connection if any
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
                
            # Create new connection with improved settings
            self.serial_conn = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                timeout=self.config.timeout,
                write_timeout=self.config.write_timeout,
                bytesize=self.config.bytesize,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                xonxoff=self.config.xonxoff,
                rtscts=self.config.rtscts,
                dsrdtr=self.config.dsrdtr,
                inter_byte_timeout=self.config.inter_byte_timeout
            )
            
            # Clear buffers
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            
            logger.info(f"Connected to {self.config.port} at {self.config.baudrate} baud")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Failed to connect to {self.config.port}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from serial port"""
        self.is_running = False
        
        # Wait for threads to finish
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2.0)
        if self.write_thread and self.write_thread.is_alive():
            self.write_thread.join(timeout=2.0)
            
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Disconnected from serial port")
    
    def start(self):
        """Start reading and writing threads"""
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.connect():
                return False
                
        self.is_running = True
        
        # Start read thread
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        
        # Start write thread
        self.write_thread = threading.Thread(target=self._write_loop, daemon=True)
        self.write_thread.start()
        
        logger.info("Serial reader/writer started")
        return True
    
    def stop(self):
        """Stop reading and writing"""
        self.is_running = False
        self.disconnect()
        logger.info("Serial reader/writer stopped")
    
    def write_data(self, data: bytes) -> bool:
        """Queue data for writing (non-blocking)"""
        try:
            self.write_queue.put_nowait(data)
            return True
        except queue.Full:
            logger.warning("Write queue is full, dropping data")
            return False
    
    def _read_loop(self):
        """Main reading loop with improved error handling"""
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                # Check if data is available
                if self.serial_conn.in_waiting > 0:
                    # Read available data
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    if data:
                        self._process_received_data(data)
                        consecutive_errors = 0  # Reset error counter
                else:
                    # No data available, sleep briefly
                    time.sleep(0.001)  # 1ms sleep to prevent busy waiting
                    
            except serial.SerialTimeoutException:
                # Timeout is normal, continue
                continue
            except serial.SerialException as e:
                consecutive_errors += 1
                self.stats['errors'] += 1
                logger.error(f"Serial read error ({consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors, attempting reconnection")
                    self._attempt_reconnection()
                    consecutive_errors = 0
                    
            except Exception as e:
                consecutive_errors += 1
                self.stats['errors'] += 1
                logger.error(f"Unexpected read error: {e}")
                
        logger.info("Read loop ended")
    
    def _write_loop(self):
        """Main writing loop"""
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                # Get data from queue with timeout
                data = self.write_queue.get(timeout=1.0)
                
                if self.serial_conn and self.serial_conn.is_open:
                    bytes_written = self.serial_conn.write(data)
                    self.serial_conn.flush()  # Ensure data is sent
                    self.stats['bytes_sent'] += bytes_written
                    logger.debug(f"Sent {bytes_written} bytes")
                    
            except queue.Empty:
                # No data to write, continue
                continue
            except serial.SerialException as e:
                self.stats['errors'] += 1
                logger.error(f"Serial write error: {e}")
                self._attempt_reconnection()
            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"Unexpected write error: {e}")
                
        logger.info("Write loop ended")
    
    def _process_received_data(self, data: bytes):
        """Process received data with buffer management"""
        self.stats['bytes_received'] += len(data)
        self.stats['last_activity'] = time.time()
        
        # Add to circular buffer
        with self.buffer_lock:
            if len(self.read_buffer) >= self.read_buffer.maxlen:
                self.stats['buffer_overflows'] += 1
                logger.warning("Read buffer overflow, dropping oldest data")
            
            # Split data by newlines and add each line
            lines = data.decode('utf-8', errors='ignore').split('\n')
            for line in lines:
                if line.strip():  # Only add non-empty lines
                    self.read_buffer.append({
                        'timestamp': time.time(),
                        'data': line.strip()
                    })
        
        # Call user callback if provided
        if self.data_callback:
            try:
                self.data_callback(data)
            except Exception as e:
                logger.error(f"Error in data callback: {e}")
    
    def _attempt_reconnection(self):
        """Attempt to reconnect to serial port"""
        logger.info("Attempting to reconnect...")
        time.sleep(1.0)  # Wait before reconnecting
        
        if self.connect():
            logger.info("Reconnection successful")
        else:
            logger.error("Reconnection failed")
    
    def get_latest_data(self, count: int = 10) -> list:
        """Get latest received data"""
        with self.buffer_lock:
            return list(self.read_buffer)[-count:]
    
    def get_stats(self) -> dict:
        """Get communication statistics"""
        return self.stats.copy()
    
    def clear_buffers(self):
        """Clear all buffers"""
        with self.buffer_lock:
            self.read_buffer.clear()
        
        # Clear write queue
        while not self.write_queue.empty():
            try:
                self.write_queue.get_nowait()
            except queue.Empty:
                break
                
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()

def list_available_ports():
    """List all available serial ports"""
    ports = serial.tools.list_ports.comports()
    available_ports = []
    
    for port in ports:
        available_ports.append({
            'device': port.device,
            'description': port.description,
            'hwid': port.hwid
        })
    
    return available_ports

# Example usage
if __name__ == "__main__":
    # List available ports
    ports = list_available_ports()
    print("Available serial ports:")
    for port in ports:
        print(f"  {port['device']}: {port['description']}")
    
    if not ports:
        print("No serial ports found!")
        exit(1)
    
    # Use first available port
    port_name = ports[0]['device']
    
    # Create configuration
    config = SerialConfig(
        port=port_name,
        baudrate=115200,
        timeout=0.1,
        rtscts=True,  # Enable hardware flow control
        inter_byte_timeout=0.01
    )
    
    # Data callback function
    def on_data_received(data: bytes):
        """Handle received data"""
        try:
            message = data.decode('utf-8', errors='ignore').strip()
            if message:
                print(f"Received: {message}")
        except Exception as e:
            logger.error(f"Error processing received data: {e}")
    
    # Create and start reader
    reader = ImprovedSerialReader(config, on_data_received)
    
    try:
        if reader.start():
            print(f"Started reading from {port_name}")
            print("Press Ctrl+C to stop...")
            
            # Main loop
            while True:
                time.sleep(1)
                
                # Print statistics every 10 seconds
                stats = reader.get_stats()
                if int(time.time()) % 10 == 0:
                    print(f"Stats: {stats['bytes_received']} bytes received, "
                          f"{stats['bytes_sent']} bytes sent, "
                          f"{stats['errors']} errors")
                    
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        reader.stop()
