#!/usr/bin/env python3
"""
wf2.py - Insert blank lines for intervals over 70 seconds
在 sdp_span.log 中超過70秒的行前插入空白行，同時在 sdp-copy.log 的對應行前也插入空白行
"""

import os
import re
from typing import List, Tuple


def read_file_lines(file_path: str) -> List[str]:
    """
    Read all lines from a file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except FileNotFoundError:
        print(f"Error: File {file_path} not found!")
        return []
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []


def write_file_lines(file_path: str, lines: List[str]) -> bool:
    """
    Write lines to a file
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return False


def parse_interval_from_span_line(line: str) -> float:
    """
    Parse interval value from sdp_span.log line
    Format: Line X-Y Z.ZZZ
    """
    # Extract the interval value (last number in the line)
    parts = line.strip().split()
    if len(parts) >= 3:
        try:
            return float(parts[-1])
        except ValueError:
            return 0.0
    return 0.0


def find_lines_over_70_seconds(span_lines: List[str]) -> List[int]:
    """
    Find line numbers where interval is over 70 seconds
    Returns list of 1-based line numbers
    """
    over_70_lines = []
    
    for i, line in enumerate(span_lines):
        if not line.strip():  # Skip empty lines
            continue
            
        interval = parse_interval_from_span_line(line)
        if interval > 70.0:
            over_70_lines.append(i + 1)  # Convert to 1-based line number
            print(f"Found interval {interval:.3f} seconds at line {i + 1}")
    
    return over_70_lines


def insert_blank_lines(lines: List[str], target_line_numbers: List[int]) -> List[str]:
    """
    Insert blank lines before specified line numbers
    Note: line_numbers are 1-based, but we need to account for already inserted lines
    """
    result_lines = []
    inserted_count = 0
    
    for i, line in enumerate(lines):
        current_line_number = i + 1 + inserted_count
        
        # Check if we need to insert a blank line before this line
        if current_line_number in target_line_numbers:
            result_lines.append('\n')  # Insert blank line
            inserted_count += 1
            print(f"Inserted blank line before line {current_line_number}")
        
        result_lines.append(line)
    
    return result_lines


def main():
    """
    Main function to process both files
    """
    print("=" * 60)
    print("wf2.py - Insert blank lines for intervals over 70 seconds")
    print("=" * 60)
    
    # Define file paths
    base_dir = "/home/rnd/studio-sdp-roulette/logs"
    sdp_copy_file = os.path.join(base_dir, "sdp-copy.log")
    sdp_span_file = os.path.join(base_dir, "sdp_span.log")
    
    # Read both files
    print(f"\n1. Reading {sdp_copy_file}...")
    sdp_copy_lines = read_file_lines(sdp_copy_file)
    if not sdp_copy_lines:
        return
    
    print(f"2. Reading {sdp_span_file}...")
    sdp_span_lines = read_file_lines(sdp_span_file)
    if not sdp_span_lines:
        return
    
    print(f"SDP Copy: {len(sdp_copy_lines)} lines")
    print(f"SDP Span: {len(sdp_span_lines)} lines")
    
    # Find lines with intervals over 70 seconds
    print(f"\n3. Finding lines with intervals over 70 seconds...")
    over_70_lines = find_lines_over_70_seconds(sdp_span_lines)
    
    if not over_70_lines:
        print("No lines found with intervals over 70 seconds.")
        return
    
    print(f"Found {len(over_70_lines)} lines with intervals over 70 seconds:")
    for line_num in over_70_lines:
        print(f"  Line {line_num}")
    
    # Insert blank lines in both files
    print(f"\n4. Inserting blank lines...")
    
    # Process sdp_span.log first
    print("Processing sdp_span.log...")
    new_span_lines = insert_blank_lines(sdp_span_lines, over_70_lines)
    
    # Process sdp-copy.log
    print("Processing sdp-copy.log...")
    new_copy_lines = insert_blank_lines(sdp_copy_lines, over_70_lines)
    
    # Write the modified files
    print(f"\n5. Writing modified files...")
    
    # Create backup files first
    backup_span = sdp_span_file + ".backup"
    backup_copy = sdp_copy_file + ".backup"
    
    print(f"Creating backup: {backup_span}")
    write_file_lines(backup_span, sdp_span_lines)
    
    print(f"Creating backup: {backup_copy}")
    write_file_lines(backup_copy, sdp_copy_lines)
    
    # Write modified files
    print(f"Writing modified sdp_span.log...")
    if write_file_lines(sdp_span_file, new_span_lines):
        print(f"✅ Successfully updated {sdp_span_file}")
    
    print(f"Writing modified sdp-copy.log...")
    if write_file_lines(sdp_copy_file, new_copy_lines):
        print(f"✅ Successfully updated {sdp_copy_file}")
    
    print(f"\n" + "=" * 60)
    print("Processing completed!")
    print(f"Original files backed up as:")
    print(f"  {backup_span}")
    print(f"  {backup_copy}")
    print(f"Modified files:")
    print(f"  {sdp_span_file}")
    print(f"  {sdp_copy_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
