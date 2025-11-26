#!/usr/bin/env python3
"""
calc_match.py - Calculate percentage of matching SDP and IDP results
計算 SDP_result 和 IDP_result 相等的百分比
"""

import os
import re
from typing import List, Tuple


def parse_match_log(file_path: str) -> Tuple[List[Tuple[int, int]], List[str]]:
    """
    Parse match.log file and extract SDP_result and IDP_result pairs
    Returns tuple of (results_list, original_lines_list)
    """
    results = []
    original_lines = []
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return results, original_lines
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comment lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse the line format:
                # SDP_line_X | IDP_line_Y | timestamp1 | timestamp2 | sdp_result | idp_result | time_diff
                parts = line.split(' | ')
                if len(parts) != 7:
                    print(f"Warning: Invalid format at line {line_num}: {line}")
                    continue
                
                try:
                    sdp_result = int(parts[4].strip())
                    idp_result = int(parts[5].strip())
                    results.append((sdp_result, idp_result))
                    original_lines.append(line)
                except ValueError as e:
                    print(f"Warning: Could not parse results at line {line_num}: {e}")
                    continue
        
        print(f"Parsed {len(results)} result pairs from match.log")
        return results, original_lines
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return [], []


def calculate_match_statistics(results: List[Tuple[int, int]]) -> dict:
    """
    Calculate statistics for matching results
    """
    if not results:
        return {}
    
    total_pairs = len(results)
    equal_pairs = 0
    unequal_pairs = 0
    
    # Count equal and unequal pairs
    for sdp_result, idp_result in results:
        if sdp_result == idp_result:
            equal_pairs += 1
        else:
            unequal_pairs += 1
    
    # Calculate percentages
    equal_percentage = (equal_pairs / total_pairs) * 100
    unequal_percentage = (unequal_pairs / total_pairs) * 100
    
    return {
        'total_pairs': total_pairs,
        'equal_pairs': equal_pairs,
        'unequal_pairs': unequal_pairs,
        'equal_percentage': equal_percentage,
        'unequal_percentage': unequal_percentage
    }


def print_statistics(stats: dict):
    """
    Print formatted statistics
    """
    if not stats:
        print("No statistics available.")
        return
    
    print("=" * 60)
    print("SDP-IDP Result Match Statistics")
    print("=" * 60)
    
    print(f"\n📊 Overall Statistics:")
    print(f"  Total matched pairs: {stats['total_pairs']}")
    print(f"  Equal results: {stats['equal_pairs']}")
    print(f"  Unequal results: {stats['unequal_pairs']}")
    
    print(f"\n📈 Percentage Analysis:")
    print(f"  ✅ Equal results: {stats['equal_percentage']:.2f}%")
    print(f"  ❌ Unequal results: {stats['unequal_percentage']:.2f}%")
    
    print("=" * 60)


def write_diff_log(results: List[Tuple[int, int]], original_lines: List[str], output_file: str):
    """
    Write lines with different SDP and IDP results to diff.log
    """
    if not results or not original_lines:
        print("No data to write to diff.log")
        return
    
    diff_lines = []
    
    for i, (sdp_result, idp_result) in enumerate(results):
        if sdp_result != idp_result:
            diff_lines.append(original_lines[i])
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# SDP-IDP Different Results\n")
            f.write("# Format: SDP_line | IDP_line | SDP_timestamp | IDP_timestamp | SDP_result | IDP_result | time_diff(seconds)\n")
            f.write("#" + "="*100 + "\n\n")
            
            for line in diff_lines:
                f.write(line + "\n")
        
        print(f"✅ Different results written to {output_file}")
        print(f"   Total different pairs: {len(diff_lines)}")
        
    except Exception as e:
        print(f"Error writing diff.log: {e}")


def main():
    """
    Main function to calculate match statistics
    """
    print("=" * 60)
    print("calc_match.py - Calculate SDP-IDP Result Match Percentage")
    print("=" * 60)
    
    # Define file paths
    match_file = "/home/rnd/studio-sdp-roulette/logs/match.log"
    diff_file = "/home/rnd/studio-sdp-roulette/logs/diff.log"
    
    # Parse match log
    print(f"\n1. Parsing match log: {match_file}")
    results, original_lines = parse_match_log(match_file)
    
    if not results:
        print("Error: Could not parse match log!")
        return
    
    # Calculate statistics
    print(f"\n2. Calculating statistics...")
    stats = calculate_match_statistics(results)
    
    # Print results
    print(f"\n3. Results:")
    print_statistics(stats)
    
    # Write different results to diff.log
    print(f"\n4. Writing different results to diff.log...")
    write_diff_log(results, original_lines, diff_file)
    
    print(f"\n✅ Analysis completed!")


if __name__ == "__main__":
    main()
