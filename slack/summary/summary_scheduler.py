"""
TableAPI Error Summary Scheduler

Schedules and sends summary reports of tableAPI errors to Slack.
Sends reports at 6:00 AM and 6:00 PM every day.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from slack.summary.error_tracker import (
    get_error_summary,
    clear_old_errors,
    get_error_tracker,
)
from slack.slack_notifier import send_error_to_slack


class SummaryScheduler:
    """Scheduler for sending tableAPI error summaries"""

    def __init__(self):
        """Initialize scheduler"""
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

    def start(self):
        """Start the scheduler"""
        with self.lock:
            if self.running:
                return
            self.running = True
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True
            )
            self.scheduler_thread.start()

    def stop(self):
        """Stop the scheduler"""
        with self.lock:
            self.running = False

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                now = datetime.now()
                
                # Calculate next 6 AM and 6 PM
                next_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)
                next_6pm = now.replace(hour=18, minute=0, second=0, microsecond=0)
                
                # Adjust times based on current time
                if now.hour >= 18:
                    # Past 6 PM, next 6 AM is tomorrow
                    next_6am = next_6am + timedelta(days=1)
                    next_6pm = next_6pm + timedelta(days=1)
                elif now.hour >= 6:
                    # Past 6 AM but before 6 PM, next 6 PM is today, next 6 AM is tomorrow
                    next_6am = next_6am + timedelta(days=1)
                # else: before 6 AM, both are today
                
                # Determine next send time
                if now.hour >= 6 and now.hour < 18:
                    # Between 6 AM and 6 PM, next send is 6 PM today
                    next_send_time = next_6pm
                else:
                    # Before 6 AM or after 6 PM, next send is 6 AM
                    next_send_time = next_6am
                
                # Calculate seconds until next send time
                seconds_until_next = (next_send_time - now).total_seconds()
                
                # If it's exactly 6 AM or 6 PM (within 1 minute), send immediately
                if abs(seconds_until_next) < 60:
                    send_summary_report()
                    # Wait until after the send time to avoid duplicate sends
                    time.sleep(60)
                    continue
                
                # Wait until next send time (check every minute)
                while seconds_until_next > 0 and self.running:
                    sleep_time = min(60, seconds_until_next)  # Check every minute
                    time.sleep(sleep_time)
                    seconds_until_next -= sleep_time
                
                # Send summary if still running
                if self.running:
                    send_summary_report()
                    
            except Exception as e:
                print(f"[{datetime.now()}] Error in summary scheduler: {e}")
                time.sleep(60)  # Wait before retrying

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        with self.lock:
            return self.running


# Global scheduler instance
_global_scheduler: Optional[SummaryScheduler] = None


def start_summary_scheduler():
    """Start the global summary scheduler"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = SummaryScheduler()
    _global_scheduler.start()


def stop_summary_scheduler():
    """Stop the global summary scheduler"""
    global _global_scheduler
    if _global_scheduler is not None:
        _global_scheduler.stop()


def send_summary_report():
    """
    Send a summary report of tableAPI errors for the past 12 hours
    
    This function:
    1. Gets errors from the past 12 hours
    2. Formats them into a summary message
    3. Sends the summary to Slack
    4. Clears old errors (older than 24 hours)
    """
    try:
        now = datetime.now()
        twelve_hours_ago = now - timedelta(hours=12)
        twenty_four_hours_ago = now - timedelta(hours=24)
        
        # Get error summary for past 12 hours
        summary = get_error_summary(twelve_hours_ago, now)
        
        # Format summary message
        message_lines = [
            "📊 *TableAPI Error Summary (Past 12 Hours)*",
            f"Time Period: {twelve_hours_ago.strftime('%Y-%m-%d %H:%M:%S')} - {now.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        
        # Check if there are any errors
        total_errors = 0
        for env in summary.values():
            for count in env.values():
                total_errors += count
        
        if total_errors == 0:
            message_lines.append("✅ *No errors reported in the past 12 hours*")
        else:
            message_lines.append("*Error Counts by Environment and API:*")
            message_lines.append("")
            
            # Format as table
            # Header
            header = "| Environment | Start | BetStop | Deal | Finish |"
            separator = "|------------|-------|---------|------|--------|"
            message_lines.append(header)
            message_lines.append(separator)
            
            # Data rows
            for env in ["CIT", "QAT", "UAT", "STG", "PRD"]:
                env_data = summary.get(env, {})
                row = f"| {env} | {env_data.get('start', 0)} | {env_data.get('betStop', 0)} | {env_data.get('deal', 0)} | {env_data.get('finish', 0)} |"
                message_lines.append(row)
            
            message_lines.append("")
            message_lines.append(f"*Total Errors: {total_errors}*")
        
        message = "\n".join(message_lines)
        
        # Send to Slack
        # Use a generic environment since this is a summary
        success = send_error_to_slack(
            error_message=message,
            error_code="TABLEAPI_ERROR_SUMMARY",
            table_name="Summary Report",
            environment="SYSTEM",
        )
        
        if success:
            print(f"[{now}] TableAPI error summary sent to Slack successfully")
        else:
            print(f"[{now}] Failed to send TableAPI error summary to Slack")
        
        # Clear old errors (older than 24 hours)
        clear_old_errors(twenty_four_hours_ago)
        
        return success
        
    except Exception as e:
        print(f"[{datetime.now()}] Error sending summary report: {e}")
        return False

