#!/usr/bin/env python3
"""
Compare Log Script - Extract IDP and Serial Results from TMUX Windows

This script monitors tmux windows to extract:
1. IDP MQTT results from 'dp:idp' window
2. Serial port results from 'dp:log_serial' window

Writes results to:
- logs/idp.log (IDP MQTT responses)
- logs/sdp.log (Serial port results)
"""

import re
import json
import subprocess
import time
from datetime import datetime
from collections import defaultdict
from typing import Dict, Tuple, Optional


class ResultDeduplicator:
    """Helper class to track and deduplicate results"""
    
    def __init__(self, time_threshold: float = 1.0):
        self.time_threshold = time_threshold
        self.last_times: Dict[str, float] = {}
        self.seen_uuids: Dict[str, float] = {}
    
    def should_record(self, identifier: str, timestamp: float) -> bool:
        """
        Check if we should record this result based on deduplication rules
        
        Args:
            identifier: Unique identifier for this result (e.g., MQTT UUID or serial result)
            timestamp: Timestamp of the result
            
        Returns:
            True if we should record, False if it's a duplicate
        """
        # Check if we've seen this result recently
        if identifier in self.last_times:
            time_diff = timestamp - self.last_times[identifier]
            if time_diff < self.time_threshold:
                return False
        
        # Record this result
        self.last_times[identifier] = timestamp
        return True


class IDPResultExtractor:
    """Extract IDP results from tmux window"""
    
    def __init__(self):
        self.log_file = "logs/idp.log"
        self.deduplicator = ResultDeduplicator(time_threshold=10.0)  # 10 seconds for MQTT
        self.mqtt_uuid_pattern = re.compile(r'MqttClient_IDP_ARO-001-([a-f0-9-]{36})')
        self.json_pattern = re.compile(r'\{[^}]+\}')
    
    def ensure_log_file(self):
        """Ensure the log file exists with header"""
        import os
        os.makedirs("logs", exist_ok=True)
        
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write("# IDP MQTT Results Log\n")
                f.write("# Format: [TIMESTAMP] ROUND_ID | RESULT | ERROR_CODE\n")
                f.write("# " + "=" * 60 + "\n")
    
    def parse_idp_simple(self, lines: list, start_idx: int) -> Optional[Dict]:
        """Parse IDP MQTT result from multi-line output"""
        try:
            # Get the start line with timestamp
            if start_idx >= len(lines):
                return None
            
            line = lines[start_idx]
            
            # Extract timestamp
            timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
            if not timestamp_match:
                return None
            
            # Extract UUID from log line
            uuid_match = self.mqtt_uuid_pattern.search(line)
            if not uuid_match:
                return None
            
            uuid = uuid_match.group(1)
            
            # Collect lines until we have complete JSON
            # Build the full text from start_idx to end of JSON
            full_text_parts = []
            for i in range(start_idx, min(start_idx + 5, len(lines))):  # Search up to 5 lines ahead
                full_text_parts.append(lines[i])
            
            full_text = ' '.join(full_text_parts)
            
            # Find JSON start and end - try multiple patterns
            json_start = full_text.find('{"response":')
            if json_start == -1:
                json_start = full_text.find('"response": "result"')
                if json_start > 0:
                    json_start = full_text.rfind('{', 0, json_start)
                else:
                    return None
            
            # Find matching closing brace
            brace_count = 0
            json_end = json_start
            for i in range(json_start, len(full_text)):
                char = full_text[i]
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            if brace_count != 0:
                return None
            
            json_str = full_text[json_start:json_end]
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Validate structure
            if not (data.get("response") == "result" and 
                    "arg" in data and 
                    "res" in data["arg"] and 
                    "err" in data["arg"]):
                return None
            
            result = data["arg"]["res"]
            error_code = data["arg"]["err"]
            round_id = data["arg"].get("round_id", "UNKNOWN")
            
            # Validate: err must be 0 and result must be 0-36
            if error_code != 0:
                return None
            
            # Handle null results - skip them
            if result is None:
                return None
            
            if not isinstance(result, int) or not (0 <= result <= 36):
                return None
            
            # Check deduplication based on UUID
            current_time = time.time()
            identifier = f"mqtt_{uuid}"
            if not self.deduplicator.should_record(identifier, current_time):
                return None
            
            return {
                "timestamp": timestamp_match.group(1),
                "uuid": uuid,
                "round_id": round_id,
                "result": result,
                "error_code": error_code,
                "raw_line": json_str
            }
            
        except (json.JSONDecodeError, ValueError, AttributeError) as e:
            return None
    
    def get_tmux_output(self) -> str:
        """Get output from tmux window 'dp:idp' - use larger history"""
        try:
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'dp:idp', '-p', '-S', '-2000'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout
        except Exception as e:
            print(f"Error getting tmux output from dp:idp: {e}")
            return ""
    
    def extract_and_log(self):
        """Extract IDP results and write to log file"""
        self.ensure_log_file()
        
        output = self.get_tmux_output()
        if not output:
            print("⚠️  No output from tmux window 'dp:idp'")
            return
        
        # Simple regex extraction: find all valid IDP results
        import re
        # Pattern to match: "res": <0-36 number>, "err": 0
        valid_result_pattern = re.compile(r'"res":\s*(\d{1,2}),\s*"err":\s*0')
        
        # Search for valid results with round_id
        found_results = []
        for match in valid_result_pattern.finditer(output):
            # Find the surrounding context to get round_id and timestamp
            start_idx = match.start()
            end_idx = match.end()
            
            # Look backwards for round_id
            context_start = max(0, start_idx - 500)
            context_end = min(len(output), end_idx + 100)
            context = output[context_start:context_end]
            
            # Extract round_id - try multiple patterns
            round_id_match = re.search(r'"round_id":\s*"([A-Z]{3}-\d{3}-[a-f0-9-]{36})"', context)
            if not round_id_match:
                round_id_match = re.search(r'"round_id":\s*"[^"]*([a-f0-9-]{8}-[a-f0-9-]{4}-[a-f0-9-]{4}-[a-f0-9-]{4}-[a-f0-9-]{12})"', context)
            if not round_id_match:
                round_id_match = re.search(r'ARO-001-[a-f0-9-]{36}', context)
            round_id = round_id_match.group(1) if round_id_match and round_id_match.lastindex else (round_id_match.group(0) if round_id_match else "UNKNOWN")
            
            result_value = int(match.group(1))
            
            # Extract timestamp if present
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', context)
            timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().strftime('%Y-%m-%d %H:%M:%S,000')
            
            # Check deduplication
            current_time = time.time()
            identifier = f"idp_{result_value}_{round_id}"
            if self.deduplicator.should_record(identifier, current_time) and round_id != "UNKNOWN":
                found_results.append({
                    "round_id": round_id,
                    "result": result_value,
                    "timestamp": timestamp
                })
        
        print(f"Found {len(found_results)} valid IDP results")
        
        recent_results = found_results
        
        # Log new results (only if UUID not found in last 10 logged entries)
        if recent_results:
            # Read existing logs to check last 10 entries for UUIDs
            try:
                with open(self.log_file, 'r') as f:
                    existing_lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
                    # Get last 10 entries
                    last_10_lines = existing_lines[-10:] if len(existing_lines) > 0 else []
                    
                    # Extract all UUIDs from last 10 lines
                    logged_uuids = set()
                    for line in last_10_lines:
                        # Extract round_id/UUID from log entry
                        if 'Round:' in line:
                            # Format: [timestamp] Round: UUID | Result: X
                            parts = line.split('Round: ')
                            if len(parts) > 1:
                                uuid_part = parts[1].split(' | ')[0].strip()
                                logged_uuids.add(uuid_part)
                    
                    print(f"Found {len(logged_uuids)} unique UUIDs in last 10 entries: {list(logged_uuids)[:3]}")
            except (FileNotFoundError, IndexError):
                logged_uuids = set()
            
            new_to_log = []
            for result in recent_results:
                round_id = result['round_id']
                
                # Check if this UUID was already logged in last 10 entries
                if round_id not in logged_uuids:
                    log_entry = (
                        f"[{result['timestamp']}] "
                        f"Round: {result['round_id']} | "
                        f"Result: {result['result']}"
                    )
                    new_to_log.append((log_entry, result))
                    logged_uuids.add(round_id)  # Add to set to avoid duplicates in same run
                else:
                    print(f"⚠️  Skipping duplicate UUID: {round_id} (already in last 10 entries)")
            
            if new_to_log:
                with open(self.log_file, 'a') as f:
                    for log_entry, result in new_to_log:
                        f.write(log_entry + '\n')
                        print(f"✅ IDP logged: Round={result['round_id']}, Result={result['result']}")
            else:
                print("⚠️  No new results to log (all UUIDs already in last 10 entries)")
        else:
            print("⚠️  No valid IDP results found to log")


class SerialResultExtractor:
    """Extract Serial port results from tmux window"""
    
    def __init__(self):
        self.log_file = "logs/sdp.log"
        self.deduplicator = ResultDeduplicator(time_threshold=1.0)  # 1 second for serial
        self.serial_pattern = re.compile(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\] Receive >>> (\d{1,2})')
    
    def ensure_log_file(self):
        """Ensure the log file exists with header"""
        import os
        os.makedirs("logs", exist_ok=True)
        
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write("# Serial Port Results Log\n")
                f.write("# Format: [TIMESTAMP] RESULT\n")
                f.write("# " + "=" * 60 + "\n")
    
    def parse_serial_line(self, line: str) -> Optional[Dict]:
        """Parse Serial log line to extract result information"""
        match = self.serial_pattern.search(line)
        if not match:
            return None
        
        timestamp_str = match.group(1)
        result_str = match.group(2)
        
        try:
            result = int(result_str)
            
            # Validate: result must be 0-36
            if not (0 <= result <= 36):
                return None
            
            # Parse timestamp to get unix time
            try:
                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                timestamp = dt.timestamp()
            except ValueError:
                timestamp = time.time()
            
            # Check deduplication: same result within 1 second
            identifier = f"serial_{result}"
            if not self.deduplicator.should_record(identifier, timestamp):
                return None
            
            return {
                "timestamp": timestamp_str,
                "result": result,
                "raw_line": line.strip()
            }
            
        except ValueError:
            return None
    
    def get_tmux_output(self) -> str:
        """Get output from tmux window 'dp:log_serial'"""
        try:
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', 'dp:log_serial', '-p'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout
        except Exception as e:
            print(f"Error getting tmux output from dp:log_serial: {e}")
            return ""
    
    def extract_and_log(self):
        """Extract Serial results and write to log file"""
        self.ensure_log_file()
        
        output = self.get_tmux_output()
        if not output:
            return
        
        lines = output.split('\n')
        recent_results = []
        
        for line in lines:
            if 'Receive >>>' in line:
                parsed = self.parse_serial_line(line)
                if parsed:
                    recent_results.append(parsed)
        
        # Log new results (only if different from last 10 logged entries)
        if recent_results:
            # Read existing logs to check last 10 entries
            try:
                with open(self.log_file, 'r') as f:
                    existing_lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
                    # Get last 10 entries
                    last_10_lines = existing_lines[-10:] if len(existing_lines) > 0 else []
                    
                    # Extract all results from last 10 lines
                    logged_results = set()
                    for line in last_10_lines:
                        # Extract result number from log entry
                        if 'Receive >>>' in line:
                            # Format: [timestamp] Receive >>> X
                            parts = line.split('Receive >>> ')
                            if len(parts) > 1:
                                result_num = parts[1].strip()
                                logged_results.add(result_num)
                    
                    print(f"Found {len(logged_results)} unique results in last 10 entries: {list(logged_results)}")
            except (FileNotFoundError, IndexError):
                logged_results = set()
            
            new_to_log = []
            for result in recent_results:
                result_str = str(result['result'])
                
                # Check if this result was already logged in last 10 entries
                if result_str not in logged_results:
                    log_entry = f"[{result['timestamp']}] Receive >>> {result['result']}"
                    new_to_log.append((log_entry, result))
                    logged_results.add(result_str)  # Add to set to avoid duplicates in same run
                else:
                    print(f"⚠️  Skipping duplicate serial result: {result_str} (already in last 10 entries)")
            
            if new_to_log:
                with open(self.log_file, 'a') as f:
                    for log_entry, result in new_to_log:
                        f.write(log_entry + '\n')
                        print(f"✅ Serial logged: Result={result['result']}")
            else:
                print("⚠️  No new serial results to log (all results already in last 10 entries)")
        else:
            print("⚠️  No serial results found to log")


def main():
    """Main execution - extract and log results from both tmux windows"""
    print("=" * 60)
    print("Compare Log Script - Extracting IDP and Serial Results")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Extract IDP results
    print("\n📥 Processing IDP results from tmux window 'dp:idp'...")
    idp_extractor = IDPResultExtractor()
    idp_extractor.extract_and_log()
    
    # Extract Serial results
    print("\n📥 Processing Serial results from tmux window 'dp:log_serial'...")
    serial_extractor = SerialResultExtractor()
    serial_extractor.extract_and_log()
    
    print("\n✅ Processing complete!")
    print("\n📝 Log files:")
    print(f"   - IDP results: logs/idp.log")
    print(f"   - Serial results: logs/sdp.log")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error running compare_log.py: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
