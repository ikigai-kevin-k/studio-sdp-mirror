#!/usr/bin/env python3
"""
Unit test script for Roulette Relaunch Failed notification
Tests the specialized format for ROULETTE_RELAUNCH_FAILED errors
"""

import os
import sys
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables must be set manually.")

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slack.slack_notifier import (
    SlackNotifier,
    send_roulette_sensor_error_to_slack,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_roulette_relaunch_failed_notification(channel: str = "#alert-studio", mention_user: str = "Mark Bochkov"):
    """
    Test sending roulette relaunch failed notification with all required changes

    Args:
        channel: Channel to send to (e.g., "#alert-studio" or "#studio-rnd")
        mention_user: User to mention (e.g., "Mark Bochkov")
    """
    logger.info("=" * 60)
    logger.info("Test: Roulette Relaunch Failed Notification")
    logger.info("=" * 60)
    logger.info(f"Channel: {channel}")
    logger.info(f"Mention User: {mention_user}")
    logger.info("")

    try:
        notifier = SlackNotifier()

        if not notifier.bot_client:
            logger.warning(
                "⚠️  Bot client not available. "
                "Please set SLACK_BOT_TOKEN environment variable."
            )
            logger.info("Skipping test - Bot token required for notifications")
            return False

        # Send test notification message first to avoid confusion
        logger.info("Sending test notification message...")
        notifier.send_simple_message(
            "the following message is for the test",
            channel=channel,
        )
        logger.info("Test notification message sent")

        # Test sending roulette relaunch failed notification with all changes:
        # 1. Header: "Roulette error" (not "SDP Error - PRD")
        # 2. No Environment field
        # 3. Table: "ARO-001-1 (speed - main)"
        # 4. Action: "None (can be auto-recovered)"
        # 5. Error Code: "ROULETTE_RELAUNCH_FAILED"
        # 6. Mention: mention_user (parameterized)
        # 7. Channel: channel (parameterized)
        success = send_roulette_sensor_error_to_slack(
            action_message="None (can be auto-recovered)",
            table_name="ARO-001-1 (speed - main)",
            error_code="ROULETTE_RELAUNCH_FAILED",
            mention_user=mention_user,
            channel=channel,
        )

        if success:
            logger.info(
                "✅ Roulette relaunch failed notification sent successfully!"
            )
            logger.info("")
            logger.info("Expected message format:")
            logger.info("  Header: 🚨 Roulette error")
            logger.info(f"  Mention: @{mention_user}")
            logger.info("  Table: ARO-001-1 (speed - main)")
            logger.info("  Error Code: ROULETTE_RELAUNCH_FAILED")
            logger.info("  Action: None (can be auto-recovered)")
            logger.info(f"  Channel: {channel}")
            logger.info("  No Environment field")
            logger.info("")
            logger.info(
                f"   Please check {channel} channel to verify the message format."
            )
            return True
        else:
            logger.error("❌ Failed to send roulette relaunch failed notification")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """
    Main test function
    """
    # Parse command line arguments
    channel = "#alert-studio"
    mention_user = "Mark Bochkov"
    
    if len(sys.argv) > 1:
        channel_arg = sys.argv[1].lower()
        
        if channel_arg == "alert-studio":
            channel = "#alert-studio"
            mention_user = "Mark Bochkov"
            logger.info("📢 Using alert-studio channel with Mark Bochkov")
        elif channel_arg == "studio-rnd":
            channel = "#studio-rnd"
            mention_user = "Mark Bochkov"
            logger.info("📢 Using studio-rnd channel with Mark Bochkov")
        else:
            logger.warning(f"⚠️  Unknown channel argument: {channel_arg}")
            logger.info("   Using default: alert-studio with Mark Bochkov")
            logger.info("   Valid options: alert-studio, studio-rnd")
    else:
        logger.info("📢 No channel specified, using default: alert-studio with Mark Bochkov")
        logger.info("   Usage: python3 slack/test_roulette_relaunch_failed.py [alert-studio|studio-rnd]")

    logger.info("")
    logger.info("🚀 Starting Roulette Relaunch Failed Notification Tests")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Prerequisites:")
    logger.info("  1. SLACK_BOT_TOKEN must be set (required for notifications)")
    logger.info(f"  2. User '{mention_user}' must exist in the Slack workspace")
    logger.info(f"  3. Bot must be in {channel} channel")
    logger.info("")

    # Check environment variables
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if not bot_token and not webhook_url:
        logger.error(
            "❌ Error: Neither SLACK_BOT_TOKEN nor SLACK_WEBHOOK_URL is set!"
        )
        logger.error("   Please set at least one of these environment variables.")
        return False

    if not bot_token:
        logger.warning(
            "⚠️  Warning: SLACK_BOT_TOKEN not set. "
            "User lookup and mention features will not work."
        )
        logger.warning("   Some tests will be skipped.")

    # Run test
    logger.info("")
    try:
        result = test_roulette_relaunch_failed_notification(channel, mention_user)
        
        if result:
            logger.info("")
            logger.info("🎉 Test passed!")
            logger.info(f"   Please check {channel} channel to verify:")
            logger.info("   - Header shows 'Roulette error' (not 'SDP Error - PRD')")
            logger.info("   - No Environment field")
            logger.info("   - Table shows 'ARO-001-1 (speed - main)'")
            logger.info("   - Error Code shows 'ROULETTE_RELAUNCH_FAILED'")
            logger.info("   - Action shows 'None (can be auto-recovered)'")
            logger.info(f"   - {mention_user} is mentioned")
        else:
            logger.info("")
            logger.warning("⚠️  Test failed. Please review the error messages above.")
        
        return result
    except Exception as e:
        logger.error(f"❌ Test raised exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

