#!/usr/bin/env python3
"""
diff_simplifier.py - Simplify diff.log to only keep SDP_result and IDP_result columns
簡化 diff.log 檔案，只保留 SDP_result 和 IDP_result 兩個欄位
"""

import os
from typing import List, Tuple


def parse_diff_log(file_path: str) -> List[Tuple[int, int]]:
    """
    Parse diff.log file and extract SDP_result and IDP_result pairs
    Returns list of (sdp_result, idp_result) tuples
    """
    results = []
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return results
    
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
                except ValueError as e:
                    print(f"Warning: Could not parse results at line {line_num}: {e}")
                    continue
        
        print(f"Parsed {len(results)} result pairs from diff.log")
        return results
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []


def write_simplified_diff(results: List[Tuple[int, int]], output_file: str):
    """
    Write simplified diff results to output file
    Format: SDP_result  IDP_result
    """
    if not results:
        print("No data to write to diff_simple.log")
        return
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# SDP-IDP Different Results (Simplified)\n")
            f.write("# Format: SDP_result  IDP_result\n")
            f.write("#" + "="*40 + "\n\n")
            
            for sdp_result, idp_result in results:
                f.write(f"{sdp_result}  {idp_result}\n")
        
        print(f"✅ Simplified results written to {output_file}")
        print(f"   Total different pairs: {len(results)}")
        
    except Exception as e:
        print(f"Error writing diff_simple.log: {e}")


def main():
    """
    Main function to simplify diff.log
    """
    print("=" * 60)
    print("diff_simplifier.py - Simplify diff.log to SDP_result and IDP_result only")
    print("=" * 60)
    
    # Define file paths
    diff_file = "/home/rnd/studio-sdp-roulette/logs/diff.log"
    output_file = "/home/rnd/studio-sdp-roulette/logs/diff_simple.log"
    
    # Parse diff log
    print(f"\n1. Parsing diff log: {diff_file}")
    results = parse_diff_log(diff_file)
    
    if not results:
        print("Error: Could not parse diff log!")
        return
    
    # Write simplified output
    print(f"\n2. Writing simplified output...")
    write_simplified_diff(results, output_file)
    
    print(f"\n✅ Simplification completed!")
    print(f"Output file: {output_file}")


if __name__ == "__main__":
    main()
