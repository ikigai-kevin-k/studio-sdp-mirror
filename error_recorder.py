#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Error Recorder Module for SDP Roulette System
Monitors sbo_{yyyy-mm-dd}.log files for IDP error responses with err: -3
and captures frames from RTMP stream using ffmpeg
"""

import os
import sys
import re
import json
import time
import signal
import subprocess
from datetime import datetime
from pathlib import Path
from glob import glob
from typing import Optional

# Configuration
LOG_DIR = "logs"
LOG_FILE_PATTERN = "sbo_*.log"

# Alternative paths to try for log directory
POSSIBLE_LOG_DIRS = [
    LOG_DIR,
    os.path.join(os.path.dirname(__file__), LOG_DIR),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), LOG_DIR),
    f"/home/rnd/studio-sdp-roulette/{LOG_DIR}"
]

# RTMP stream URL
RTMP_STREAM_URL = "rtmp://192.168.88.54:1935/live/r14_sb"

# Output directory for captured images
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "error_captures")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

# State file to track last read position in log file
POSITION_FILE = os.path.join(
    os.path.dirname(__file__), ".last_position_error_recorder.json"
)

# Monitoring interval in seconds
MONITOR_INTERVAL = 1.0  # Check every 1 second

# Global flag for graceful shutdown
running = True

# Global flag to track if ffmpeg is currently running
ffmpeg_process: Optional[subprocess.Popen] = None

# Temporary file for continuous frame capture
TEMP_FRAME_FILE = os.path.join(OUTPUT_DIR, ".temp_frame.png")


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global running, ffmpeg_process
    print("\n🛑 Shutting down error recorder...")
    running = False
    
    # Terminate ffmpeg if running
    if ffmpeg_process is not None:
        try:
            print("🛑 Stopping ffmpeg stream...")
            ffmpeg_process.terminate()
            ffmpeg_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ffmpeg_process.kill()
        except Exception as e:
            print(f"⚠️  Error terminating ffmpeg: {e}")
        finally:
            ffmpeg_process = None
    
    # Clean up temp file
    if os.path.exists(TEMP_FRAME_FILE):
        try:
            os.remove(TEMP_FRAME_FILE)
        except Exception:
            pass
    
    sys.exit(0)


def find_latest_log_file() -> Optional[str]:
    """
    Find the latest sbo_{yyyy-mm-dd}.log file from possible log directories
    
    Returns:
        str: Path to the latest log file, or None if not found
    """
    log_files = []
    
    # Search in all possible log directories
    for log_dir in POSSIBLE_LOG_DIRS:
        if not os.path.isdir(log_dir):
            continue
        
        # Find all sbo_*.log files matching pattern sbo_{yyyy-mm-dd}.log
        pattern = os.path.join(log_dir, LOG_FILE_PATTERN)
        found_files = glob(pattern)
        
        # Filter to only match sbo_{yyyy-mm-dd}.log format (e.g., sbo_2024-10-06.log)
        for file_path in found_files:
            filename = os.path.basename(file_path)
            # Match pattern: sbo_YYYY-MM-DD.log
            if re.match(r'^sbo_\d{4}-\d{2}-\d{2}\.log$', filename):
                log_files.append(file_path)
    
    if not log_files:
        return None
    
    # Sort by modification time and return the latest
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return log_files[0]


def get_current_date_log_file() -> Optional[str]:
    """
    Get log file for current date (sbo_yyyy-mm-dd.log)
    
    Returns:
        str: Path to current date log file, or None if not found
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"sbo_{current_date}.log"
    
    # Search in all possible log directories
    for log_dir in POSSIBLE_LOG_DIRS:
        if not os.path.isdir(log_dir):
            continue
        
        log_file = os.path.join(log_dir, log_filename)
        if os.path.exists(log_file):
            return log_file
    
    return None


def parse_timestamp_from_line(line: str) -> Optional[datetime]:
    """
    Parse timestamp from log line format: 2025-11-12 11:24:10,923
    
    Args:
        line: Log line containing timestamp
        
    Returns:
        datetime: Parsed datetime object, or None if parsing failed
    """
    # Pattern to match: "YYYY-MM-DD HH:MM:SS,mmm"
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})'
    match = re.search(pattern, line)
    if match:
        try:
            timestamp_str = match.group(1) + '.' + match.group(2)
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            return None
    return None


def is_error_minus_3_line(line: str) -> bool:
    """
    Check if a log line contains IDP error response with err: -3
    
    Args:
        line: Log line to check
        
    Returns:
        bool: True if line contains err: -3, False otherwise
    """
    # Check if line contains IDP response message
    if "ikg/idp/SBO-001/response" not in line:
        return False
    
    # Try to extract JSON from the line
    # Look for JSON pattern in the message
    json_pattern = r'\{[^{}]*"err"\s*:\s*-3[^{}]*\}'
    if re.search(json_pattern, line):
        return True
    
    # More comprehensive check: try to parse JSON
    try:
        # Extract JSON part from log line
        json_match = re.search(r'\{.*\}', line)
        if json_match:
            json_str = json_match.group(0)
            data = json.loads(json_str)
            
            # Check nested structure: response -> arg -> err
            if isinstance(data, dict):
                if data.get("response") == "result":
                    arg = data.get("arg", {})
                    if isinstance(arg, dict) and arg.get("err") == -3:
                        return True
    except (json.JSONDecodeError, AttributeError, KeyError):
        pass
    
    return False


def load_last_position() -> int:
    """
    Load last read position from state file
    
    Returns:
        int: Last read position (byte offset), or 0 if file doesn't exist
    """
    if not os.path.exists(POSITION_FILE):
        return 0
    
    try:
        with open(POSITION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('position', 0)
    except Exception:
        return 0


def save_last_position(position: int, log_file: str):
    """
    Save last read position to state file
    
    Args:
        position: Byte position in the log file
        log_file: Path to the log file
    """
    try:
        with open(POSITION_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'position': position,
                'log_file': log_file,
                'last_update': datetime.now().isoformat()
            }, f, indent=2)
    except Exception as e:
        print(f"⚠️  Error saving position file: {e}")


def start_ffmpeg_stream(rtmp_url: str, temp_file: str) -> bool:
    """
    Start ffmpeg process to continuously capture frames from RTMP stream
    Updates temp_file periodically (every second)
    
    Args:
        rtmp_url: RTMP stream URL
        temp_file: Path to temporary file for continuous frame updates
        
    Returns:
        bool: True if successful, False otherwise
    """
    global ffmpeg_process
    
    # Check if ffmpeg is already running
    if ffmpeg_process is not None:
        try:
            # Check if process is still running
            if ffmpeg_process.poll() is None:
                return True  # Already running
            else:
                # Process has finished, clean up
                ffmpeg_process = None
        except Exception as e:
            print(f"⚠️  Error checking ffmpeg process: {e}")
            ffmpeg_process = None
    
    try:
        # Build ffmpeg command to continuously capture frames
        # -i: input stream
        # -vf fps=1: capture 1 frame per second
        # -f image2: output format as image sequence
        # -y: overwrite output file if exists
        # -loglevel error: only show errors
        # Note: ffmpeg will continuously update the PNG file with latest frame
        cmd = [
            'ffmpeg',
            '-loglevel', 'error',  # Only show errors
            '-i', rtmp_url,
            '-vf', 'fps=1',  # Capture 1 frame per second
            '-f', 'image2',  # Output format as image
            '-y',
            temp_file
        ]
        
        print(f"📹 Starting ffmpeg stream capture from {rtmp_url}")
        print(f"💾 Continuously updating: {temp_file}")
        
        # Start ffmpeg process (don't wait, let it run continuously)
        ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment to check if process started successfully
        time.sleep(1)
        
        if ffmpeg_process.poll() is None:
            print("✅ ffmpeg stream started successfully")
            return True
        else:
            # Process exited immediately, something went wrong
            stdout, stderr = ffmpeg_process.communicate()
            print(f"❌ ffmpeg failed to start (return code: {ffmpeg_process.returncode})")
            if stderr:
                print(f"Error output: {stderr[:500]}")
            ffmpeg_process = None
            return False
            
    except FileNotFoundError:
        print("❌ ffmpeg not found. Please install ffmpeg.")
        return False
    except Exception as e:
        print(f"❌ Error starting ffmpeg stream: {e}")
        if ffmpeg_process is not None:
            try:
                ffmpeg_process.terminate()
                ffmpeg_process.wait(timeout=5)
            except Exception:
                pass
            ffmpeg_process = None
        return False


def save_current_frame(output_path: str) -> bool:
    """
    Save current frame from temp file to output path
    This is called when err: -3 is detected
    
    Args:
        output_path: Path to save the captured frame
        
    Returns:
        bool: True if successful, False otherwise
    """
    global ffmpeg_process
    
    # Check if ffmpeg is running and temp file exists
    if ffmpeg_process is None or ffmpeg_process.poll() is not None:
        print("⚠️  ffmpeg stream is not running")
        return False
    
    if not os.path.exists(TEMP_FRAME_FILE):
        print("⚠️  Temporary frame file does not exist yet")
        return False
    
    try:
        # Copy temp file to output path
        import shutil
        shutil.copy2(TEMP_FRAME_FILE, output_path)
        print(f"✅ Frame saved: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving frame: {e}")
        return False


def monitor_log_file():
    """
    Monitor log file for error responses and capture frames
    Only monitors new log entries after startup, no backward scanning
    """
    global running
    
    # Start from current file end, don't load old position
    last_position = None  # Will be set to file end when file is first opened
    current_log_file = None
    last_date = None
    
    print("🔍 Starting error recorder monitor...")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"📡 RTMP stream: {RTMP_STREAM_URL}")
    print("ℹ️  Only monitoring new log entries (no backward scanning)")
    
    # Start ffmpeg stream capture (keep it running)
    print("\n🎬 Starting continuous ffmpeg stream capture...")
    if not start_ffmpeg_stream(RTMP_STREAM_URL, TEMP_FRAME_FILE):
        print("❌ Failed to start ffmpeg stream, exiting...")
        return
    
    # Wait a bit for ffmpeg to start capturing
    print("⏳ Waiting for ffmpeg to establish stream connection...")
    time.sleep(3)
    
    while running:
        try:
            # Get current date
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Check if date changed (cross-day detection)
            if last_date is not None and current_date != last_date:
                print(f"📅 Date changed from {last_date} to {current_date}, switching log file...")
                last_position = None  # Reset position for new day
                current_log_file = None
            
            # Get current date log file
            log_file = get_current_date_log_file()
            
            if log_file is None:
                # Log file doesn't exist yet, wait and retry
                time.sleep(MONITOR_INTERVAL)
                continue
            
            # If log file changed, reset position to file end
            if current_log_file != log_file:
                print(f"📝 Monitoring log file: {log_file}")
                current_log_file = log_file
                # Set position to current file end (only monitor new entries)
                if os.path.exists(log_file):
                    last_position = os.path.getsize(log_file)
                    print(f"📍 Starting from end of file (position: {last_position})")
                else:
                    last_position = None
            
            # Check if file exists and is readable
            if not os.path.exists(log_file):
                time.sleep(MONITOR_INTERVAL)
                continue
            
            # Get current file size
            current_size = os.path.getsize(log_file)
            
            # Initialize position to file end if not set
            if last_position is None:
                last_position = current_size
                print(f"📍 Starting from end of file (position: {last_position})")
            
            # If file was truncated or position is beyond file size, reset to file end
            if last_position > current_size:
                print("⚠️  Log file was truncated, resetting position to file end")
                last_position = current_size
            
            # Read new content
            if current_size > last_position:
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        # Seek to last position
                        f.seek(last_position)
                        
                        # Read new lines
                        new_lines = f.readlines()
                        
                        # Process each new line
                        for line in new_lines:
                            if not running:
                                break
                            
                            # Check if line contains err: -3
                            if is_error_minus_3_line(line):
                                print(f"\n🚨 Detected err: -3 in log line:")
                                print(f"   {line.strip()[:200]}")
                                
                                # Generate output filename with timestamp
                                timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                                output_filename = f"{timestamp}.png"
                                output_path = os.path.join(OUTPUT_DIR, output_filename)
                                
                                # Save current frame from continuously running ffmpeg stream
                                success = save_current_frame(output_path)
                                
                                if success:
                                    print(f"✅ Frame saved successfully: {output_filename}")
                                else:
                                    print(f"❌ Failed to save frame")
                                
                                # Check if ffmpeg is still running, restart if needed
                                if ffmpeg_process is None or ffmpeg_process.poll() is not None:
                                    print("⚠️  ffmpeg stream stopped, restarting...")
                                    start_ffmpeg_stream(RTMP_STREAM_URL, TEMP_FRAME_FILE)
                                    time.sleep(2)  # Wait for stream to establish
                        
                        # Update position
                        last_position = f.tell()
                        # Don't save position to avoid backward scanning on restart
                        
                except Exception as e:
                    print(f"❌ Error reading log file: {e}")
            
            # Update last date
            last_date = current_date
            
            # Check if ffmpeg is still running, restart if needed
            if ffmpeg_process is None or ffmpeg_process.poll() is not None:
                print("⚠️  ffmpeg stream stopped, restarting...")
                start_ffmpeg_stream(RTMP_STREAM_URL, TEMP_FRAME_FILE)
                time.sleep(2)  # Wait for stream to establish
            
            # Sleep before next check
            time.sleep(MONITOR_INTERVAL)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error in monitor loop: {e}")
            time.sleep(MONITOR_INTERVAL)


def main():
    """Main function"""
    global running
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("Error Recorder - IDP Error Response Monitor")
    print("=" * 60)
    print(f"Monitoring: sbo_yyyy-mm-dd.log files")
    print(f"Trigger: IDP error response with err: -3")
    print(f"Action: Capture frame from RTMP stream")
    print("=" * 60)
    print()
    
    try:
        monitor_log_file()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        global ffmpeg_process
        if ffmpeg_process is not None:
            try:
                print("🛑 Stopping ffmpeg stream...")
                ffmpeg_process.terminate()
                ffmpeg_process.wait(timeout=5)
            except Exception:
                pass
            ffmpeg_process = None
        
        # Clean up temp file
        if os.path.exists(TEMP_FRAME_FILE):
            try:
                os.remove(TEMP_FRAME_FILE)
            except Exception:
                pass
        
        print("👋 Error recorder stopped")


if __name__ == "__main__":
    main()

