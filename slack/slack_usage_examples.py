#!/usr/bin/env python3
"""
Slack notification usage examples for SDP Roulette system
Demonstrates different ways to send messages to Slack
"""

import os
from slack_notifier import (
    SlackNotifier, 
    send_error_to_slack, 
    send_success_to_slack
)


def example_1_simple_webhook():
    """Example 1: Simple webhook message"""
    print("=== Example 1: Simple Webhook Message ===")
    
    # Initialize with webhook URL
    notifier = SlackNotifier(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        default_channel="#sdp-alerts"
    )
    
    # Send simple message
    success = notifier.send_simple_message(
        "Hello from SDP Roulette! 🎲",
        channel="#general"
    )
    
    if success:
        print("✅ Message sent successfully!")
    else:
        print("❌ Failed to send message")


def example_2_error_notification():
    """Example 2: Error notification with rich formatting"""
    print("\n=== Example 2: Error Notification ===")
    
    # Using convenience function
    success = send_error_to_slack(
        error_message="the round on Table \"BCR-001\" isn't finished yet",
        error_code="13003",
        table_name="BCR-001",
        environment="STG"
    )
    
    if success:
        print("✅ Error notification sent!")
    else:
        print("❌ Failed to send error notification")


def example_3_success_notification():
    """Example 3: Success notification"""
    print("\n=== Example 3: Success Notification ===")
    
    success = send_success_to_slack(
        message="Table BCR-001 round completed successfully",
        environment="PRD",
        table_name="BCR-001"
    )
    
    if success:
        print("✅ Success notification sent!")
    else:
        print("❌ Failed to send success notification")


def example_4_environment_variables():
    """Example 4: Using environment variables"""
    print("\n=== Example 4: Environment Variables ===")
    
    # Set these in your .env file or environment
    os.environ['SLACK_WEBHOOK_URL'] = 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    os.environ['SLACK_BOT_TOKEN'] = 'xoxb-your-bot-token'
    os.environ['SLACK_USER_TOKEN'] = 'xoxp-your-user-token'
    
    # Initialize without parameters - will use environment variables
    notifier = SlackNotifier(default_channel="#sdp-roulette")
    
    # Send message
    success = notifier.send_simple_message("Testing environment variables!")
    
    if success:
        print("✅ Environment variable test successful!")
    else:
        print("❌ Environment variable test failed")


def example_5_rich_message():
    """Example 5: Rich message with blocks"""
    print("\n=== Example 5: Rich Message with Blocks ===")
    
    notifier = SlackNotifier(
        bot_token="xoxb-your-bot-token",
        default_channel="#sdp-roulette"
    )
    
    # Create rich message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🎯 SDP Roulette Status Update",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Current system status and recent activities"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Active Tables:*\nBCR-001, BCR-002"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Environment:*\nSTG"
                }
            ]
        }
    ]
    
    success = notifier.send_rich_message(
        channel="#sdp-roulette",
        blocks=blocks,
        text="SDP Roulette Status Update"
    )
    
    if success:
        print("✅ Rich message sent successfully!")
    else:
        print("❌ Failed to send rich message")


def example_6_integration_with_error_handling():
    """Example 6: Integration with error handling"""
    print("\n=== Example 6: Integration with Error Handling ===")
    
    def process_table_operation(table_name, environment):
        """Simulate table operation with error handling"""
        try:
            # Simulate some operation
            if table_name == "BCR-001":
                raise Exception("Table round not finished yet")
            
            # Success case
            send_success_to_slack(
                f"Table {table_name} operation completed",
                environment,
                table_name
            )
            return True
            
        except Exception as e:
            # Send error notification
            send_error_to_slack(
                str(e),
                environment=environment,
                table_name=table_name
            )
            return False
    
    # Test error case
    result1 = process_table_operation("BCR-001", "STG")
    print(f"BCR-001 result: {'Success' if result1 else 'Error'}")
    
    # Test success case
    result2 = process_table_operation("BCR-002", "PRD")
    print(f"BCR-002 result: {'Success' if result2 else 'Error'}")


def main():
    """Main function to run all examples"""
    print("🚀 Slack Notification Examples for SDP Roulette")
    print("=" * 50)
    
    # Note: These examples require proper Slack configuration
    print("⚠️  Note: These examples require proper Slack configuration")
    print("   - Set SLACK_WEBHOOK_URL for webhook messages")
    print("   - Set SLACK_BOT_TOKEN for rich messages")
    print("   - Set SLACK_USER_TOKEN for user-specific actions")
    print()
    
    # Run examples (commented out to avoid errors without proper config)
    print("Examples are ready to run with proper Slack configuration:")
    print("1. example_1_simple_webhook()")
    print("2. example_2_error_notification()")
    print("3. example_3_success_notification()")
    print("4. example_4_environment_variables()")
    print("5. example_5_rich_message()")
    print("6. example_6_integration_with_error_handling()")
    
    print("\nTo run examples, configure your Slack tokens and uncomment the calls.")


if __name__ == "__main__":
    main()
