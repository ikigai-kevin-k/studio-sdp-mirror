#!/usr/bin/env python3
"""
match.py - Match SDP and IDP log entries within 15 seconds
匹配 sdp-simple.log 和 idp-simple.log 中15秒範圍內的結果
"""

import os
from datetime import datetime, timedelta
from typing import List, Tuple, Optional


class LogEntry:
    """Represents a log entry with timestamp and result"""
    
    def __init__(self, timestamp_str: str, result: str, line_num: int, source: str):
        self.timestamp_str = timestamp_str
        self.result = int(result)
        self.line_num = line_num
        self.source = source
        
        # Parse timestamp
        try:
            # Handle both . and , as decimal separators
            normalized_timestamp = timestamp_str.replace(',', '.')
            self.timestamp = datetime.strptime(normalized_timestamp, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}") from e
    
    def __repr__(self):
        return f"LogEntry({self.source}:{self.line_num}, {self.timestamp_str}, {self.result})"


def parse_simple_log(file_path: str, source_name: str) -> List[LogEntry]:
    """
    Parse simplified log file format: timestamp  result
    """
    entries = []
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return entries
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Split by two spaces
                parts = line.split('  ')
                if len(parts) != 2:
                    print(f"Warning: Invalid format at line {line_num}: {line}")
                    continue
                
                timestamp_str, result = parts
                
                try:
                    entry = LogEntry(timestamp_str, result, line_num, source_name)
                    entries.append(entry)
                except ValueError as e:
                    print(f"Warning: {e} at line {line_num}")
                    continue
        
        print(f"Parsed {len(entries)} entries from {source_name}")
        return entries
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []


def find_matches(sdp_entries: List[LogEntry], idp_entries: List[LogEntry], 
                time_window: int = 15) -> List[Tuple[LogEntry, LogEntry]]:
    """
    Find matches between SDP and IDP entries within the specified time window (seconds)
    """
    matches = []
    matched_idp_indices = set()  # Track which IDP entries have been matched
    
    print(f"Searching for matches within {time_window} seconds...")
    
    for sdp_entry in sdp_entries:
        # Calculate time window: SDP timestamp to SDP timestamp + time_window seconds
        window_start = sdp_entry.timestamp
        window_end = sdp_entry.timestamp + timedelta(seconds=time_window)
        
        best_match = None
        best_time_diff = float('inf')
        
        # Find the best match within the time window
        for i, idp_entry in enumerate(idp_entries):
            if i in matched_idp_indices:
                continue  # Skip already matched IDP entries
            
            # Check if IDP timestamp is within the window
            if window_start <= idp_entry.timestamp <= window_end:
                time_diff = abs((idp_entry.timestamp - sdp_entry.timestamp).total_seconds())
                
                # Keep the closest match within the window
                if time_diff < best_time_diff:
                    best_match = idp_entry
                    best_time_diff = time_diff
        
        if best_match:
            matches.append((sdp_entry, best_match))
            matched_idp_indices.add(idp_entries.index(best_match))
            print(f"Match: SDP line {sdp_entry.line_num} ({sdp_entry.timestamp_str}) -> "
                  f"IDP line {best_match.line_num} ({best_match.timestamp_str}) "
                  f"[{best_time_diff:.3f}s, result: {sdp_entry.result}]")
    
    return matches


def write_match_log(matches: List[Tuple[LogEntry, LogEntry]], output_file: str):
    """
    Write match results to output file
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# SDP-IDP Match Results\n")
            f.write("# Format: SDP_line | IDP_line | SDP_timestamp | IDP_timestamp | SDP_result | IDP_result | time_diff(seconds)\n")
            f.write("#" + "="*100 + "\n\n")
            
            for sdp_entry, idp_entry in matches:
                time_diff = abs((idp_entry.timestamp - sdp_entry.timestamp).total_seconds())
                
                f.write(f"SDP_line_{sdp_entry.line_num} | IDP_line_{idp_entry.line_num} | ")
                f.write(f"{sdp_entry.timestamp_str} | {idp_entry.timestamp_str} | ")
                f.write(f"{sdp_entry.result} | {idp_entry.result} | {time_diff:.3f}\n")
        
        print(f"✅ Match results written to {output_file}")
        
    except Exception as e:
        print(f"Error writing match log: {e}")


def main():
    """
    Main function to match SDP and IDP log entries
    """
    print("=" * 60)
    print("match.py - Match SDP and IDP log entries within 15 seconds")
    print("=" * 60)
    
    # Define file paths
    base_dir = "/home/rnd/studio-sdp-roulette/logs"
    sdp_file = os.path.join(base_dir, "sdp-simple.log")
    idp_file = os.path.join(base_dir, "idp-simple.log")
    output_file = os.path.join(base_dir, "match.log")
    
    # Parse log files
    print(f"\n1. Parsing SDP log: {sdp_file}")
    sdp_entries = parse_simple_log(sdp_file, "SDP")
    
    print(f"\n2. Parsing IDP log: {idp_file}")
    idp_entries = parse_simple_log(idp_file, "IDP")
    
    if not sdp_entries or not idp_entries:
        print("Error: Could not parse one or both log files!")
        return
    
    print(f"\n3. Finding matches...")
    print(f"SDP entries: {len(sdp_entries)}")
    print(f"IDP entries: {len(idp_entries)}")
    
    # Find matches within 15 seconds
    matches = find_matches(sdp_entries, idp_entries, time_window=15)
    
    print(f"\n4. Writing results...")
    write_match_log(matches, output_file)
    
    # Print summary statistics
    print(f"\n" + "=" * 60)
    print("Match Summary:")
    print(f"Total SDP entries: {len(sdp_entries)}")
    print(f"Total IDP entries: {len(idp_entries)}")
    print(f"Successful matches: {len(matches)}")
    print(f"Match rate: {len(matches)/len(sdp_entries)*100:.1f}%")
    print(f"Output file: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
