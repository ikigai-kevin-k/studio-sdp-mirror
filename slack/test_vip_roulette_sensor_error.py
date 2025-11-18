#!/usr/bin/env python3
"""
Unit test script for VIP Roulette Sensor Error notification
Tests the specialized format for hardware sensor errors
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


def test_vip_roulette_sensor_error_notification(channel: str = "#studio-rnd", mention_user: str = "Mark Bochkov"):
    """
    Test sending VIP roulette sensor error notification with all required changes
    
    Args:
        channel: Channel to send to (e.g., "#studio-rnd" or "#alert-studio")
        mention_user: User to mention (e.g., "Mark Bochkov" or "Kevin Kuo")
    """
    logger.info("=" * 60)
    logger.info("Test: VIP Roulette Sensor Error Notification")
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
            "The following message is for testing",
            channel=channel,
        )
        logger.info("Test notification message sent")

        # Test sending VIP roulette sensor error notification with all changes:
        # 1. Header: "Roulette error" (not "SDP Error - PRD")
        # 2. No Environment field
        # 3. Table: "ARO-002-1 (vip - main)" (not "VIP Roulette")
        # 4. Action: "relaunch the wheel controller with *P 1" (not error message)
        # 5. Mention: User specified (Mark Bochkov or Kevin Kuo)
        # 6. Channel: Specified channel (#studio-rnd or #alert-studio)
        success = notifier.send_roulette_sensor_error_notification(
            action_message="relaunch the wheel controller with *P 1",
            table_name="ARO-002-1 (vip - main)",
            error_code="SENSOR_STUCK",
            mention_user=mention_user,
            channel=channel,
        )

        if success:
            logger.info(
                "✅ VIP Roulette sensor error notification sent successfully!"
            )
            logger.info("")
            logger.info("Expected message format:")
            logger.info("  Header: 🚨 Roulette error")
            logger.info(f"  Mention: @{mention_user}")
            logger.info("  Table: ARO-002-1 (vip - main)")
            logger.info("  Error Code: SENSOR_STUCK")
            logger.info("  Action: relaunch the wheel controller with *P 1")
            logger.info(f"  Channel: {channel}")
            logger.info("  No Environment field")
            logger.info("")
            logger.info(
                f"   Please check {channel} channel to verify the message format."
            )
            return True
        else:
            logger.error("❌ Failed to send VIP roulette sensor error notification")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_convenience_function(channel: str = "#studio-rnd", mention_user: str = "Mark Bochkov"):
    """
    Test using convenience function send_roulette_sensor_error_to_slack for VIP

    Args:
        channel: Channel to send to (e.g., "#studio-rnd" or "#alert-studio")
        mention_user: User to mention (e.g., "Mark Bochkov" or "Kevin Kuo")
    """
    logger.info("=" * 60)
    logger.info("Test: Convenience Function for VIP Roulette Sensor Error")
    logger.info("=" * 60)
    logger.info(f"Channel: {channel}")
    logger.info(f"Mention User: {mention_user}")
    logger.info("")

    try:
        # Send test notification message first to avoid confusion
        logger.info("Sending test notification message...")
        notifier = SlackNotifier()
        notifier.send_simple_message(
            "The following message is for testing",
            channel=channel,
        )
        logger.info("Test notification message sent")

        # Test using convenience function for VIP
        success = send_roulette_sensor_error_to_slack(
            action_message="relaunch the wheel controller with *P 1",
            table_name="ARO-002-1 (vip - main)",
            error_code="SENSOR_STUCK",
            mention_user=mention_user,
            channel=channel,
        )

        if success:
            logger.info(
                "✅ Convenience function executed successfully!"
            )
            logger.info(
                f"   Please check {channel} channel to verify {mention_user} was mentioned."
            )
            return True
        else:
            logger.error("❌ Convenience function failed")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_user_lookup(display_name: str = "Mark Bochkov"):
    """
    Test looking up user by display name

    Args:
        display_name: User display name to lookup (e.g., "Mark Bochkov" or "Kevin Kuo")
    """
    logger.info("=" * 60)
    logger.info(f"Test: User Lookup for {display_name}")
    logger.info("=" * 60)

    try:
        notifier = SlackNotifier()

        if not notifier.bot_client:
            logger.warning(
                "⚠️  Bot client not available. "
                "Please set SLACK_BOT_TOKEN environment variable."
            )
            logger.info("Skipping test - Bot token required for user lookup")
            return False

        # Test lookup for user
        user_id = notifier.get_user_id_by_name(display_name)

        if user_id:
            logger.info(f"✅ Successfully found user: {user_id}")
            logger.info(f"   User can be mentioned using: <@{user_id}>")
            return True
        else:
            logger.warning(
                f"⚠️  User '{display_name}' not found. "
                "Please verify the display name is correct."
            )
            logger.info(
                "   Note: User lookup requires the user to be in the workspace"
            )
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False


def main():
    """
    Main test function
    """
    # Parse command line arguments
    channel = "#studio-rnd"
    mention_user = "Mark Bochkov"
    
    if len(sys.argv) > 1:
        channel_arg = sys.argv[1].lower()
        
        if channel_arg == "alert-studio":
            channel = "#alert-studio"
            mention_user = "Kevin Kuo"
            logger.info("📢 Using alert-studio channel with Kevin Kuo")
        elif channel_arg in ["studio-rnd", "rnd-studio"]:
            channel = "#studio-rnd"
            mention_user = "Mark Bochkov"
            logger.info("📢 Using studio-rnd channel with Mark Bochkov")
        else:
            logger.warning(f"⚠️  Unknown channel argument: {channel_arg}")
            logger.info("   Using default: studio-rnd with Mark Bochkov")
            logger.info("   Valid options: alert-studio, studio-rnd, rnd-studio")
    else:
        logger.info("📢 No channel specified, using default: studio-rnd with Mark Bochkov")
        logger.info("   Usage: python3 slack/test_vip_roulette_sensor_error.py [alert-studio|studio-rnd|rnd-studio]")

    logger.info("")
    logger.info("🚀 Starting VIP Roulette Sensor Error Notification Tests")
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

    # Run tests
    tests = [
        (f"User Lookup for {mention_user}", lambda: test_user_lookup(mention_user)),
        ("VIP Roulette Sensor Error Notification", lambda: test_vip_roulette_sensor_error_notification(channel, mention_user)),
        ("Convenience Function", lambda: test_convenience_function(channel, mention_user)),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            logger.info("")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} raised exception: {e}")
            results.append((test_name, False))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 Test Results Summary")
    logger.info("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1

    logger.info("")
    logger.info(f"Total: {passed}/{total} Tests Passed")

    if passed == total:
        logger.info("")
        logger.info("🎉 All tests passed!")
        logger.info(f"   Please check {channel} channel to verify:")
        logger.info("   - Header shows 'Roulette error' (not 'SDP Error - PRD')")
        logger.info("   - No Environment field")
        logger.info("   - Table shows 'ARO-002-1 (vip - main)'")
        logger.info("   - Action shows 'relaunch the wheel controller with *P 1'")
        logger.info(f"   - {mention_user} is mentioned")
    else:
        logger.info("")
        logger.warning("⚠️  Some tests failed. Please review the error messages above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

