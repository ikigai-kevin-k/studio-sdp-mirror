#!/usr/bin/env python3
"""
Compare Accuracy Script - Calculate consistency rate between sdp.log and idp.log

This script reads results from both logs and calculates:
- Total compared entries
- Number of matching results
- Accuracy percentage
- Handles different log lengths by aligning line numbers
"""

import re
from datetime import datetime
from typing import List, Tuple, Optional


def extract_result_from_line(line: str) -> Optional[int]:
    """Extract result number from a log line"""
    # For sdp.log: [timestamp] Receive >>> X
    # For idp.log: [timestamp] Round: UUID | Result: X
    sdp_match = re.search(r'Receive >>> (\d{1,2})', line)
    if sdp_match:
        return int(sdp_match.group(1))
    
    idp_match = re.search(r'Result: (\d{1,2})', line)
    if idp_match:
        return int(idp_match.group(1))
    
    return None


def read_log_file(filepath: str) -> List[Tuple[str, int]]:
    """Read log file and return list of (timestamp, result) tuples"""
    results = []
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip header lines and empty lines
                if not line or line.startswith('#') or line.startswith('='):
                    continue
                
                # Extract result
                result = extract_result_from_line(line)
                if result is not None:
                    # Extract timestamp
                    timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[\.,]\d{3})\]', line)
                    timestamp = timestamp_match.group(1) if timestamp_match else "UNKNOWN"
                    results.append((timestamp, result))
    
    except FileNotFoundError:
        print(f"⚠️  File not found: {filepath}")
        return []
    except Exception as e:
        print(f"❌ Error reading {filepath}: {e}")
        return []
    
    return results


def align_logs(sdp_results: List[Tuple[str, int]], idp_results: List[Tuple[str, int]]) -> Tuple[List[int], List[int]]:
    """
    Align logs by line number to compare.
    Use the number of lines from the log with fewer entries.
    Returns: (sdp_results_aligned, idp_results_aligned)
    """
    sdp_values = [r[1] for r in sdp_results]
    idp_values = [r[1] for r in idp_results]
    
    sdp_len = len(sdp_values)
    idp_len = len(idp_values)
    
    # Use the minimum length to align both logs
    min_len = min(sdp_len, idp_len)
    
    if sdp_len > idp_len:
        print(f"⚠️  sdp.log has {sdp_len} lines, idp.log has {idp_len} lines")
        print(f"   Truncating sdp.log: ignoring last {sdp_len - idp_len} entry(ies)")
        sdp_values = sdp_values[:min_len]
    elif idp_len > sdp_len:
        print(f"⚠️  idp.log has {idp_len} lines, sdp.log has {sdp_len} lines")
        print(f"   Truncating idp.log: ignoring last {idp_len - sdp_len} entry(ies)")
        idp_values = idp_values[:min_len]
    
    return sdp_values, idp_values


def calculate_accuracy(sdp_results: List[int], idp_results: List[int]) -> Tuple[int, int, float]:
    """
    Calculate accuracy between two result lists.
    Returns: (total_compared, matches, accuracy_percentage)
    """
    if len(sdp_results) != len(idp_results):
        print(f"⚠️  Warning: sdp_results ({len(sdp_results)}) and idp_results ({len(idp_results)}) have different lengths")
        min_len = min(len(sdp_results), len(idp_results))
        sdp_results = sdp_results[:min_len]
        idp_results = idp_results[:min_len]
    
    total = len(sdp_results)
    matches = 0
    
    for sdp_val, idp_val in zip(sdp_results, idp_results):
        if sdp_val == idp_val:
            matches += 1
    
    accuracy = (matches / total * 100) if total > 0 else 0.0
    
    return total, matches, accuracy


def print_detailed_comparison(sdp_results: List[Tuple[str, int]], idp_results: List[Tuple[str, int]], 
                              sdp_aligned: List[int], idp_aligned: List[int]):
    """Print detailed comparison of matched and mismatched results"""
    print("\n" + "=" * 80)
    print("DETAILED COMPARISON")
    print("=" * 80)
    
    matches = []
    mismatches = []
    
    for i, (sdp_val, idp_val) in enumerate(zip(sdp_aligned, idp_aligned)):
        if i < len(sdp_results) and i < len(idp_results):
            sdp_timestamp = sdp_results[i][0]
            idp_timestamp = idp_results[i][0]
            
            if sdp_val == idp_val:
                matches.append((i + 1, sdp_timestamp, sdp_val, idp_timestamp, idp_val))
            else:
                mismatches.append((i + 1, sdp_timestamp, sdp_val, idp_timestamp, idp_val))
    
    if matches:
        print(f"\n✅ MATCHED RESULTS ({len(matches)}):")
        print("-" * 80)
        for idx, sdp_ts, sdp_val, idp_ts, idp_val in matches:
            print(f"Line {idx:3d}: SDP [{sdp_ts}] → {sdp_val:2d} : IDP [{idp_ts}] → {idp_val:2d} ✅")
    
    if mismatches:
        print(f"\n❌ MISMATCHED RESULTS ({len(mismatches)}):")
        print("-" * 80)
        for idx, sdp_ts, sdp_val, idp_ts, idp_val in mismatches:
            print(f"Line {idx:3d}: SDP [{sdp_ts}] → {sdp_val:2d} : IDP [{idp_ts}] → {idp_val:2d} ❌")
    
    print("=" * 80)


def main():
    """Main execution"""
    print("=" * 80)
    print("Compare Accuracy Script - Serial vs IDP Result Consistency")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Read both log files
    print("\n📥 Reading logs...")
    sdp_results = read_log_file("logs/sdp.log")
    idp_results = read_log_file("logs/idp.log")
    
    print(f"   sdp.log: {len(sdp_results)} entries")
    print(f"   idp.log: {len(idp_results)} entries")
    
    if not sdp_results or not idp_results:
        print("\n❌ Cannot compare: one or both log files are empty")
        return
    
    # Align logs (handle different lengths)
    print("\n🔍 Aligning logs for comparison...")
    sdp_aligned, idp_aligned = align_logs(sdp_results, idp_results)
    
    # Calculate accuracy
    total, matches, accuracy = calculate_accuracy(sdp_aligned, idp_aligned)
    
    # Print summary
    print("\n" + "=" * 80)
    print("ACCURACY SUMMARY")
    print("=" * 80)
    print(f"Total Compared:      {total} entries")
    print(f"Matched Results:     {matches} entries")
    print(f"Mismatched Results:  {total - matches} entries")
    print(f"Accuracy:            {accuracy:.2f}%")
    print("=" * 80)
    
    # Print detailed comparison if requested
    if matches > 0 or total - matches > 0:
        print_detailed_comparison(sdp_results, idp_results, sdp_aligned, idp_aligned)
    
    # Print recommendation
    print("\n" + "=" * 80)
    if accuracy >= 90:
        print("🎉 Excellent consistency between Serial and IDP results!")
    elif accuracy >= 70:
        print("✅ Good consistency, but some mismatches detected.")
    else:
        print("⚠️  Low consistency detected. Review system integration.")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error running compare_acc.py: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
