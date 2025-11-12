#!/usr/bin/env python3
"""
Unit test script for Roulette Sensor Error notification
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


def test_roulette_sensor_error_notification():
    """
    Test sending roulette sensor error notification with all required changes
    """
    logger.info("=" * 60)
    logger.info("Test: Roulette Sensor Error Notification")
    logger.info("=" * 60)

    try:
        notifier = SlackNotifier()

        if not notifier.bot_client:
            logger.warning(
                "⚠️  Bot client not available. "
                "Please set SLACK_BOT_TOKEN environment variable."
            )
            logger.info("Skipping test - Bot token required for notifications")
            return False

        # Test sending roulette sensor error notification with all changes:
        # 1. Header: "Roulette error" (not "SDP Error - PRD")
        # 2. No Environment field
        # 3. Table: "ARO-001-1 (speed - main)" (not "Speed Roulette")
        # 4. Action: "relaunch the wheel controller with *P 1" (not error message)
        # 5. Mention: "Mark Bochkov" (not "Kevin Kuo")
        # 6. Channel: "#studio-rnd"
        success = notifier.send_roulette_sensor_error_notification(
            action_message="relaunch the wheel controller with *P 1",
            table_name="ARO-001-1 (speed - main)",
            error_code="SENSOR_STUCK",
            mention_user="Mark Bochkov",
            channel="#studio-rnd",
        )

        if success:
            logger.info(
                "✅ Roulette sensor error notification sent successfully!"
            )
            logger.info("")
            logger.info("Expected message format:")
            logger.info("  Header: 🚨 Roulette error")
            logger.info("  Mention: @Mark Bochkov")
            logger.info("  Table: ARO-001-1 (speed - main)")
            logger.info("  Error Code: SENSOR_STUCK")
            logger.info("  Action: relaunch the wheel controller with *P 1")
            logger.info("  Channel: #studio-rnd")
            logger.info("  No Environment field")
            logger.info("")
            logger.info(
                "   Please check #studio-rnd channel to verify the message format."
            )
            return True
        else:
            logger.error("❌ Failed to send roulette sensor error notification")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_convenience_function():
    """
    Test using convenience function send_roulette_sensor_error_to_slack
    """
    logger.info("=" * 60)
    logger.info("Test: Convenience Function for Roulette Sensor Error")
    logger.info("=" * 60)

    try:
        # Test using convenience function
        success = send_roulette_sensor_error_to_slack(
            action_message="relaunch the wheel controller with *P 1",
            table_name="ARO-001-1 (speed - main)",
            error_code="SENSOR_STUCK",
            mention_user="Mark Bochkov",
            channel="#studio-rnd",
        )

        if success:
            logger.info(
                "✅ Convenience function executed successfully!"
            )
            logger.info(
                "   Please check #studio-rnd channel to verify Mark Bochkov was mentioned."
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


def test_user_lookup():
    """
    Test looking up Mark Bochkov by display name
    """
    logger.info("=" * 60)
    logger.info("Test: User Lookup for Mark Bochkov")
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

        # Test lookup for Mark Bochkov
        user_id = notifier.get_user_id_by_name("Mark Bochkov")

        if user_id:
            logger.info(f"✅ Successfully found user: {user_id}")
            logger.info(f"   User can be mentioned using: <@{user_id}>")
            return True
        else:
            logger.warning(
                "⚠️  User 'Mark Bochkov' not found. "
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
    logger.info("🚀 Starting Roulette Sensor Error Notification Tests")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Prerequisites:")
    logger.info("  1. SLACK_BOT_TOKEN must be set (required for notifications)")
    logger.info("  2. User 'Mark Bochkov' must exist in the Slack workspace")
    logger.info("  3. Bot must be in #studio-rnd channel")
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
        ("User Lookup for Mark Bochkov", test_user_lookup),
        ("Roulette Sensor Error Notification", test_roulette_sensor_error_notification),
        ("Convenience Function", test_convenience_function),
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
        logger.info("   Please check #studio-rnd channel to verify:")
        logger.info("   - Header shows 'Roulette error' (not 'SDP Error - PRD')")
        logger.info("   - No Environment field")
        logger.info("   - Table shows 'ARO-001-1 (speed - main)'")
        logger.info("   - Action shows 'relaunch the wheel controller with *P 1'")
        logger.info("   - Mark Bochkov is mentioned")
    else:
        logger.info("")
        logger.warning("⚠️  Some tests failed. Please review the error messages above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

