#!/usr/bin/env python3
"""
Find the git branch that was checked out just before a process started.

This script finds the most recent git checkout operation that occurred
before a specified process (identified by PID or process name) started.
"""

import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path


def get_process_start_time(pid):
    """Get the start time of a process by PID."""
    try:
        # Try to get start time from /proc
        proc_stat = Path(f"/proc/{pid}/stat").read_text()
        # Field 22 is starttime (clock ticks since boot)
        starttime_ticks = int(proc_stat.split()[21])
        
        # Get system uptime and boot time
        uptime_sec = float(Path("/proc/uptime").read_text().split()[0])
        boot_time = datetime.now().timestamp() - uptime_sec
        
        # Calculate process start time
        # Get clock ticks per second
        clock_ticks = Path("/proc/self/stat").read_text().split()[21]
        # Actually, we need to use sysconf(_SC_CLK_TCK) which is usually 100
        clock_ticks_per_sec = 100
        
        proc_start_timestamp = boot_time + (starttime_ticks / clock_ticks_per_sec)
        return datetime.fromtimestamp(proc_start_timestamp)
    except Exception as e:
        # Fallback to ps command
        try:
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "lstart="],
                capture_output=True,
                text=True,
                check=True
            )
            time_str = result.stdout.strip()
            # Format: "Fri Nov 14 07:13:55 2025"
            return datetime.strptime(time_str, "%a %b %d %H:%M:%S %Y")
        except Exception as e2:
            print(f"Error getting process start time: {e2}", file=sys.stderr)
            return None


def find_process_by_name(name):
    """Find process ID by process name."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", name],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split()
            if pids:
                return int(pids[0])  # Return first matching PID
        return None
    except Exception:
        return None


def find_tmux_process(session_name):
    """Find process running in a tmux session."""
    try:
        # Get tmux session info
        result = subprocess.run(
            ["tmux", "list-panes", "-t", session_name, "-F", "#{pane_pid}"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split()
            if pids:
                # Get the main process (first PID)
                return int(pids[0])
        return None
    except Exception:
        return None


def get_git_checkouts_before_time(repo_path, target_time):
    """Get all git checkout operations before a specific time."""
    try:
        result = subprocess.run(
            ["git", "reflog", "show", "--date=iso"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_path
        )
        
        checkouts = []
        for line in result.stdout.split('\n'):
            if 'checkout: moving from' in line or 'checkout: moving to' in line:
                # Parse time from reflog entry
                # Format: f43e356 HEAD@{2025-11-14 07:10:34 +0400}: checkout: ...
                match = re.search(r'\{([^}]+)\}', line)
                if match:
                    time_str = match.group(1).split(' +')[0]  # Remove timezone
                    try:
                        checkout_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        if checkout_time < target_time:
                            # Extract branch name
                            branch = None
                            if 'to origin/' in line:
                                branch = line.split('to origin/')[1].split()[0]
                            elif 'to ' in line:
                                branch_part = line.split('to ')[1].split()[0]
                                # Check if it's a branch name or commit hash
                                if not re.match(r'^[0-9a-f]{40}$', branch_part):
                                    branch = branch_part
                            
                            checkouts.append((checkout_time, branch, line.strip()))
                    except ValueError:
                        continue
        
        # Sort by time descending (most recent first)
        checkouts.sort(key=lambda x: x[0], reverse=True)
        return checkouts
        
    except subprocess.CalledProcessError as e:
        print(f"Error reading git reflog: {e}", file=sys.stderr)
        return []


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 find_branch_at_process_start.py <pid>")
        print("  python3 find_branch_at_process_start.py --name <process_name>")
        print("  python3 find_branch_at_process_start.py --tmux <session_name>")
        print("\nExample:")
        print("  python3 find_branch_at_process_start.py 19340")
        print("  python3 find_branch_at_process_start.py --name main_speed.py")
        print("  python3 find_branch_at_process_start.py --tmux dp:sdp")
        sys.exit(1)
    
    # Get process ID
    pid = None
    if sys.argv[1] == '--name' and len(sys.argv) > 2:
        process_name = sys.argv[2]
        pid = find_process_by_name(process_name)
        if not pid:
            print(f"Process '{process_name}' not found", file=sys.stderr)
            sys.exit(1)
        print(f"Found process '{process_name}' with PID: {pid}")
    elif sys.argv[1] == '--tmux' and len(sys.argv) > 2:
        session_name = sys.argv[2]
        pid = find_tmux_process(session_name)
        if not pid:
            print(f"Tmux session '{session_name}' not found or has no processes", file=sys.stderr)
            sys.exit(1)
        print(f"Found tmux session '{session_name}' with main PID: {pid}")
    else:
        try:
            pid = int(sys.argv[1])
        except ValueError:
            print(f"Invalid PID: {sys.argv[1]}", file=sys.stderr)
            sys.exit(1)
    
    # Get process start time
    proc_start_time = get_process_start_time(pid)
    if not proc_start_time:
        print("Could not determine process start time", file=sys.stderr)
        sys.exit(1)
    
    print(f"\nProcess start time: {proc_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get repository path (current directory or workspace)
    repo_path = Path.cwd()
    if not (repo_path / ".git").exists():
        # Try workspace path
        workspace_path = Path("/home/rnd/studio-sdp-roulette")
        if (workspace_path / ".git").exists():
            repo_path = workspace_path
        else:
            print("Not in a git repository", file=sys.stderr)
            sys.exit(1)
    
    # Find checkouts before process start
    checkouts = get_git_checkouts_before_time(repo_path, proc_start_time)
    
    if not checkouts:
        print("\nNo git checkout operations found before process start time.")
        sys.exit(0)
    
    # Display the most recent checkout
    latest = checkouts[0]
    print(f"\n最鄰近的 checkout 時間: {latest[0].strftime('%Y-%m-%d %H:%M:%S')}")
    
    if latest[1]:
        print(f"切換到的 branch: {latest[1]}")
    else:
        print("切換到的 commit (非 branch): 請查看完整記錄")
    
    print(f"\n完整記錄:")
    print(f"  {latest[2]}")
    
    # Show additional recent checkouts if available
    if len(checkouts) > 1:
        print(f"\n其他在執行前的 checkout 記錄 (共 {len(checkouts)} 筆):")
        for i, (time, branch, line) in enumerate(checkouts[1:6], 1):  # Show up to 5 more
            branch_info = f" -> {branch}" if branch else ""
            print(f"  {i}. {time.strftime('%Y-%m-%d %H:%M:%S')}{branch_info}")


if __name__ == "__main__":
    main()

