#!/usr/bin/env python3
"""
Real-time diagnostic tool for IDP result processing
Monitors MQTT logs and comparison logs to verify the fix is working
"""

import os
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class IDPResultDiagnostic:
    """Diagnostic tool for IDP result processing"""
    
    def __init__(self):
        self.mqtt_log_file = "logs/sdp_mqtt.log"
        self.compare_log_file = "logs/serial_idp_result_compare.log"
        self.last_checked_mqtt = 0
        self.last_checked_compare = 0
        
        # Track recent results for analysis
        self.recent_idp_results = {}  # round_id -> result
        self.recent_comparisons = {}  # round_id -> comparison_data
        
    def extract_idp_results_from_mqtt_log(self, since_timestamp: float = None) -> Dict[str, any]:
        """Extract IDP results from MQTT log file"""
        if not os.path.exists(self.mqtt_log_file):
            return {}
        
        results = {}
        
        try:
            with open(self.mqtt_log_file, 'r', encoding='utf-8') as f:
                # If since_timestamp provided, seek to approximately the right position
                if since_timestamp:
                    f.seek(self.last_checked_mqtt)
                
                for line in f:
                    # Look for IDP response messages
                    if 'ikg/idp/ARO-001/response' in line and '"response": "result"' in line:
                        # Extract timestamp
                        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3})', line)
                        if timestamp_match:
                            timestamp_str = f"{timestamp_match.group(1)}.{timestamp_match.group(2)}"
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f').timestamp()
                            
                            if since_timestamp and timestamp <= since_timestamp:
                                continue
                        
                        # Extract round_id and result
                        round_id_match = re.search(r'"round_id":\s*"([^"]+)"', line)
                        result_match = re.search(r'"res":\s*([^,}]+)', line)
                        error_match = re.search(r'"err":\s*([^,}]+)', line)
                        
                        if round_id_match and result_match:
                            round_id = round_id_match.group(1)
                            result_str = result_match.group(1).strip()
                            error = error_match.group(1).strip() if error_match else "unknown"
                            
                            # Convert result to appropriate type
                            try:
                                if result_str == "null":
                                    result = None
                                elif result_str.isdigit() or (result_str.startswith('-') and result_str[1:].isdigit()):
                                    result = int(result_str)
                                else:
                                    result = result_str.strip('"')
                            except:
                                result = result_str
                            
                            results[round_id] = {
                                'result': result,
                                'error': error,
                                'timestamp': timestamp_str,
                                'line': line.strip()
                            }
                
                # Update last checked position
                self.last_checked_mqtt = f.tell()
                
        except Exception as e:
            print(f"Error reading MQTT log: {e}")
        
        return results
    
    def extract_comparisons_from_compare_log(self, since_timestamp: float = None) -> Dict[str, Dict]:
        """Extract comparison results from comparison log file"""
        if not os.path.exists(self.compare_log_file):
            return {}
        
        comparisons = {}
        
        try:
            with open(self.compare_log_file, 'r', encoding='utf-8') as f:
                # If since_timestamp provided, seek to approximately the right position
                if since_timestamp:
                    f.seek(self.last_checked_compare)
                
                for line in f:
                    # Skip header lines
                    if line.startswith('#') or line.strip() == '':
                        continue
                    
                    # Parse comparison line
                    # Format: [TIMESTAMP] ROUND_ID | SERIAL: X | IDP: Y | STATUS | NOTES
                    match = re.match(r'\[([^\]]+)\]\s+([^\s]+)\s+\|\s+SERIAL:\s+([^\s]+)\s+\|\s+IDP:\s+([^\s]+)\s+\|\s+([^\s]+)\s+\|\s+(.+)', line)
                    if match:
                        timestamp_str, round_id, serial_result, idp_result, status, notes = match.groups()
                        
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f').timestamp()
                        except:
                            timestamp = time.time()
                        
                        if since_timestamp and timestamp <= since_timestamp:
                            continue
                        
                        comparisons[round_id] = {
                            'serial_result': serial_result,
                            'idp_result': idp_result,
                            'status': status,
                            'notes': notes,
                            'timestamp': timestamp_str,
                            'line': line.strip()
                        }
                
                # Update last checked position
                self.last_checked_compare = f.tell()
                
        except Exception as e:
            print(f"Error reading comparison log: {e}")
        
        return comparisons
    
    def analyze_recent_results(self, minutes_back: int = 10) -> Dict:
        """Analyze recent results for diagnostic purposes"""
        since_timestamp = time.time() - (minutes_back * 60)
        
        # Get recent IDP results and comparisons
        idp_results = self.extract_idp_results_from_mqtt_log(since_timestamp)
        comparisons = self.extract_comparisons_from_compare_log(since_timestamp)
        
        # Analysis
        analysis = {
            'summary': {
                'total_idp_results': len(idp_results),
                'total_comparisons': len(comparisons),
                'minutes_analyzed': minutes_back
            },
            'idp_results': idp_results,
            'comparisons': comparisons,
            'issues': [],
            'success_rate': 0
        }
        
        # Find issues
        matches = 0
        mismatches = 0
        missing_idp = 0
        
        for round_id, comparison in comparisons.items():
            if comparison['status'] == 'MATCH':
                matches += 1
            elif comparison['status'] == 'MISMATCH':
                mismatches += 1
                
                # Check if this is due to missing IDP result
                if comparison['idp_result'] in ["['']", "[]", "None", "NOT_RECEIVED"]:
                    missing_idp += 1
                    
                    # Check if IDP actually sent a result for this round
                    if round_id in idp_results:
                        analysis['issues'].append({
                            'type': 'IDP_RESULT_NOT_PROCESSED',
                            'round_id': round_id,
                            'idp_sent': idp_results[round_id]['result'],
                            'comparison_shows': comparison['idp_result'],
                            'description': f"IDP sent result {idp_results[round_id]['result']} but comparison shows {comparison['idp_result']}"
                        })
        
        # Calculate success rate
        total_rounds = matches + mismatches
        if total_rounds > 0:
            analysis['success_rate'] = (matches / total_rounds) * 100
        
        analysis['summary'].update({
            'matches': matches,
            'mismatches': mismatches,
            'missing_idp_results': missing_idp,
            'success_rate_percent': analysis['success_rate']
        })
        
        return analysis
    
    def print_analysis(self, analysis: Dict):
        """Print analysis results in a readable format"""
        print("=" * 80)
        print("IDP RESULT PROCESSING DIAGNOSTIC REPORT")
        print("=" * 80)
        
        summary = analysis['summary']
        print(f"Time Period: Last {summary['minutes_analyzed']} minutes")
        print(f"IDP Results Received: {summary['total_idp_results']}")
        print(f"Comparisons Logged: {summary['total_comparisons']}")
        print(f"Match Rate: {summary['success_rate_percent']:.1f}%")
        print(f"  - Matches: {summary['matches']}")
        print(f"  - Mismatches: {summary['mismatches']}")
        print(f"  - Missing IDP: {summary['missing_idp_results']}")
        
        # Print issues
        if analysis['issues']:
            print("\n" + "!" * 60)
            print("ISSUES DETECTED:")
            print("!" * 60)
            
            for issue in analysis['issues']:
                print(f"\n❌ {issue['type']}")
                print(f"   Round ID: {issue['round_id']}")
                print(f"   IDP Sent: {issue['idp_sent']}")
                print(f"   Comparison Shows: {issue['comparison_shows']}")
                print(f"   Description: {issue['description']}")
        else:
            print("\n✅ NO ISSUES DETECTED")
        
        # Print recent examples
        if analysis['comparisons']:
            print("\n" + "-" * 60)
            print("RECENT COMPARISONS:")
            print("-" * 60)
            
            # Show last 5 comparisons
            recent_comparisons = list(analysis['comparisons'].items())[-5:]
            for round_id, comp in recent_comparisons:
                status_emoji = "✅" if comp['status'] == 'MATCH' else "❌"
                print(f"{status_emoji} {comp['timestamp']} | {round_id[:20]}... | S:{comp['serial_result']} I:{comp['idp_result']} | {comp['status']}")
    
    def monitor_real_time(self, interval_seconds: int = 10):
        """Monitor in real-time"""
        print("Starting real-time IDP result monitoring...")
        print(f"Checking every {interval_seconds} seconds. Press Ctrl+C to stop.")
        
        try:
            while True:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking...")
                
                # Analyze last 5 minutes
                analysis = self.analyze_recent_results(minutes_back=5)
                
                # Print summary
                summary = analysis['summary']
                if summary['total_comparisons'] > 0:
                    print(f"Last 5min: {summary['matches']}✅ {summary['mismatches']}❌ ({summary['success_rate_percent']:.0f}% success)")
                    
                    if analysis['issues']:
                        print(f"⚠️  {len(analysis['issues'])} issues detected!")
                else:
                    print("No activity in last 5 minutes")
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")

def main():
    """Main diagnostic function"""
    import sys
    
    diagnostic = IDPResultDiagnostic()
    
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        # Real-time monitoring mode
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        diagnostic.monitor_real_time(interval)
    else:
        # One-time analysis mode
        minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 30
        print(f"Analyzing last {minutes} minutes...")
        
        analysis = diagnostic.analyze_recent_results(minutes_back=minutes)
        diagnostic.print_analysis(analysis)

if __name__ == "__main__":
    main()
