#!/usr/bin/env python3
"""
dp-log-simplifier.py - Simplify log format to timestamp and result
將 sdp-copy.log 和 idp-copy.log 簡化為 {timestamp} {result} 格式
"""

import os
import re
from typing import List, Tuple, Optional


def parse_sdp_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse SDP log line format: [2025-10-28 09:22:58.197] Receive >>> 24
    Returns (timestamp, result) or None if parsing fails
    """
    # Pattern: [timestamp] Receive >>> result
    pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\] Receive >>> (\d+)'
    match = re.search(pattern, line.strip())
    
    if match:
        timestamp = match.group(1)
        result = match.group(2)
        return timestamp, result
    
    return None


def parse_idp_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse IDP log line format: [2025-10-28 09:23:09,271] Round: ... | Result: 24
    Returns (timestamp, result) or None if parsing fails
    """
    # Pattern: [timestamp] Round: ... | Result: result
    pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\] Round: .*? \| Result: (\d+)'
    match = re.search(pattern, line.strip())
    
    if match:
        timestamp = match.group(1)
        result = match.group(2)
        return timestamp, result
    
    return None


def process_log_file(input_file: str, output_file: str, parse_func, log_type: str) -> bool:
    """
    Process a log file and create simplified version
    """
    print(f"Processing {log_type} log: {input_file}")
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        return False
    
    simplified_lines = []
    parsed_count = 0
    error_count = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Parse the line
                parsed = parse_func(line)
                
                if parsed:
                    timestamp, result = parsed
                    simplified_lines.append(f"{timestamp}  {result}\n")
                    parsed_count += 1
                else:
                    print(f"Warning: Could not parse line {line_num}: {line[:50]}...")
                    error_count += 1
        
        # Write simplified output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(simplified_lines)
        
        print(f"✅ Successfully processed {log_type} log")
        print(f"   Parsed: {parsed_count} lines")
        print(f"   Errors: {error_count} lines")
        print(f"   Output: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"Error processing {input_file}: {e}")
        return False


def main():
    """
    Main function to process both log files
    """
    print("=" * 60)
    print("dp-log-simplifier.py - Simplify log format")
    print("=" * 60)
    
    # Define file paths
    base_dir = "/home/rnd/studio-sdp-roulette/logs"
    sdp_input = os.path.join(base_dir, "sdp-copy.log")
    idp_input = os.path.join(base_dir, "idp-copy.log")
    sdp_output = os.path.join(base_dir, "sdp-simple.log")
    idp_output = os.path.join(base_dir, "idp-simple.log")
    
    success_count = 0
    
    # Process SDP log
    print(f"\n1. Processing SDP log...")
    if process_log_file(sdp_input, sdp_output, parse_sdp_line, "SDP"):
        success_count += 1
    
    # Process IDP log
    print(f"\n2. Processing IDP log...")
    if process_log_file(idp_input, idp_output, parse_idp_line, "IDP"):
        success_count += 1
    
    print(f"\n" + "=" * 60)
    print("Processing completed!")
    print(f"Successfully processed: {success_count}/2 files")
    
    if success_count == 2:
        print(f"\nOutput files:")
        print(f"  SDP: {sdp_output}")
        print(f"  IDP: {idp_output}")
        print(f"\nFormat: {{timestamp}}  {{result}}")
    else:
        print("Some files failed to process. Check error messages above.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
