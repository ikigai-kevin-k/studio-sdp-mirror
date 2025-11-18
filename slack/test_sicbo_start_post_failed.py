#!/usr/bin/env python3
"""
Unit test script for Sicbo START_POST_FAILED error notification
Tests the new format with Env, Table, Error Code, and Action fields
"""

import os
import sys
import logging
import argparse

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print(
        "Warning: python-dotenv not installed. "
        "Environment variables must be set manually."
    )

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slack.slack_notifier import SlackNotifier, send_error_to_slack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_sicbo_start_post_failed_notification(
    channel: str = "#alert-studio", mention_user: str = "Kevin Kuo", environment: str = "STG"
):
    """
    Test sending Sicbo START_POST_FAILED error notification with new format

    Args:
        channel: Channel to send to (e.g., "#alert-studio" or "#studio-rnd")
        mention_user: User to mention (e.g., "Kevin Kuo" or "Mark Bochkov")
        environment: Environment name (e.g., "STG", "PRD", "CIT")
    """
    logger.info("=" * 60)
    logger.info("Test: Sicbo START_POST_FAILED Error Notification")
    logger.info("=" * 60)
    logger.info(f"Channel: {channel}")
    logger.info(f"Mention User: {mention_user}")
    logger.info(f"Environment: {environment}")
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
            "The following message is for the test",
            channel=channel,
        )
        logger.info("Test notification message sent")

        # Test sending Sicbo START_POST_FAILED error notification with new format:
        # 1. Header: "🚨 SDP Error" (not "🚨 SDP Error - {environment}")
        # 2. Env: {environment} (e.g., "STG", "PRD")
        # 3. Table: "SBO-001-1" (fixed value)
        # 4. Error Code: "START_POST_FAILED"
        # 5. Action: "None (auto-recoverable)"
        # 6. Mention: User specified (Kevin Kuo or other)
        # 7. Channel: Specified channel (#alert-studio or other)
        success = send_error_to_slack(
            error_message=f"{environment} Start Post Failed",
            environment=environment,
            table_name="SBO-001-1",
            error_code="START_POST_FAILED",
            mention_user=mention_user,
            channel=channel,
            action_message="None (auto-recoverable)",
        )

        if success:
            logger.info(
                "✅ Sicbo START_POST_FAILED error notification sent successfully!"
            )
            logger.info("")
            logger.info("Expected message format:")
            logger.info("  Header: 🚨 SDP Error")
            logger.info(f"  Mention: @{mention_user}")
            logger.info(f"  Env: {environment}")
            logger.info("  Table: SBO-001-1")
            logger.info("  Error Code: START_POST_FAILED")
            logger.info("  Action: None (auto-recoverable)")
            logger.info(f"  Channel: {channel}")
            logger.info("")
            logger.info(
                f"   Please check {channel} channel to verify the message format."
            )
            return True
        else:
            logger.error(
                "❌ Failed to send Sicbo START_POST_FAILED error notification"
            )
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_user_lookup(display_name: str = "Kevin Kuo"):
    """
    Test looking up user by display name

    Args:
        display_name: User display name to lookup (e.g., "Kevin Kuo" or "Mark Bochkov")
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
    parser = argparse.ArgumentParser(
        description="Test Sicbo START_POST_FAILED error notification"
    )
    parser.add_argument(
        "--channel",
        type=str,
        default="#alert-studio",
        help="Slack channel to send to (default: #alert-studio)",
    )
    parser.add_argument(
        "--mention-user",
        type=str,
        default="Kevin Kuo",
        help="User to mention in notification (default: Kevin Kuo)",
    )
    parser.add_argument(
        "--env",
        type=str,
        default="STG",
        choices=["CIT", "UAT", "STG", "PRD", "QAT", "GLC"],
        help="Environment name (default: STG)",
    )

    args = parser.parse_args()

    channel = args.channel
    mention_user = args.mention_user
    environment = args.env

    # Ensure channel starts with #
    if not channel.startswith("#"):
        channel = f"#{channel}"

    logger.info("")
    logger.info("🚀 Starting Sicbo START_POST_FAILED Error Notification Tests")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"  Channel: {channel}")
    logger.info(f"  Mention User: {mention_user}")
    logger.info(f"  Environment: {environment}")
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
        (
            f"User Lookup for {mention_user}",
            lambda: test_user_lookup(mention_user),
        ),
        (
            f"Sicbo START_POST_FAILED Error Notification ({environment})",
            lambda: test_sicbo_start_post_failed_notification(
                channel, mention_user, environment
            ),
        ),
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
        logger.info("   - Header shows '🚨 SDP Error'")
        logger.info("   - Env field shows the environment name")
        logger.info("   - Table shows 'SBO-001-1'")
        logger.info("   - Error Code shows 'START_POST_FAILED'")
        logger.info("   - Action shows 'None (auto-recoverable)'")
        logger.info(f"   - {mention_user} is mentioned")
    else:
        logger.info("")
        logger.warning(
            "⚠️  Some tests failed. Please review the error messages above."
        )

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

