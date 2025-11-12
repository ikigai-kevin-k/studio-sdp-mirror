#!/usr/bin/env python3
"""
Unit test script for Slack user mention functionality
Tests the ability to @ mention specific users in error notifications
Uses display name only (no email required)
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

from slack.slack_notifier import send_error_to_slack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_convenience_function_with_mention():
    """
    Test using convenience function with mention
    """
    logger.info("=" * 60)
    logger.info("Test: Error Notification with User Mention (TEST002)")
    logger.info("=" * 60)

    try:
        # Test using convenience function
        success = send_error_to_slack(
            error_message="VIP Roulette Sensor Error, please relaunch the wheel",
            error_code="TEST002",
            table_name="ARO-002",
            environment="PRD",
            mention_user="Kevin Kuo",
        )

        if success:
            logger.info(
                "✅ Error notification with mention sent successfully!"
            )
            logger.info(
                "   Please check your Slack channel to verify "
                "Kevin Kuo was mentioned and error message is displayed."
            )
            return True
        else:
            logger.error("❌ Failed to send error notification with mention")
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
    logger.info("🚀 Starting Slack User Mention Functionality Test")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Prerequisites:")
    logger.info("  1. SLACK_BOT_TOKEN must be set (required for user lookup)")
    logger.info("  2. SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN must be set")
    logger.info("  3. User 'Kevin Kuo' must exist in the Slack workspace")
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
        logger.warning("   Test will be skipped.")
        return False

    # Run test
    logger.info("")
    result = test_convenience_function_with_mention()

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 Test Result")
    logger.info("=" * 60)

    status = "✅ PASSED" if result else "❌ FAILED"
    logger.info(f"Error Notification with Mention: {status}")

    if result:
        logger.info("")
        logger.info("🎉 Test passed!")
        logger.info("   Please check your Slack channel to verify the mention and error message.")
    else:
        logger.info("")
        logger.warning("⚠️  Test failed. Please review the error messages above.")

    return result


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
