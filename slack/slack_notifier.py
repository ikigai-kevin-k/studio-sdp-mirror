"""
Slack notification module for sending messages to Slack channels
Supports multiple methods: Webhook, Bot Token, and User Token
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import hashlib

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    from slack_sdk.webhook import WebhookClient

    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False
    print(
        "Warning: slack-sdk not installed. "
        "Install with: pip install slack-sdk"
    )

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print(
        "Warning: requests not installed. "
        "Install with: pip install requests"
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlackNotifier:
    """
    Slack notification class with multiple sending methods
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        bot_token: Optional[str] = None,
        user_token: Optional[str] = None,
        default_channel: str = "#general",
    ):
        """
        Initialize Slack notifier

        Args:
            webhook_url: Slack webhook URL for simple messages
            bot_token: Bot user OAuth token for advanced features
            user_token: User OAuth token for user-specific actions
            default_channel: Default channel to send messages to
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.user_token = user_token or os.getenv("SLACK_USER_TOKEN")
        self.default_channel = default_channel

        # Initialize clients
        self.webhook_client = None
        self.bot_client = None
        self.user_client = None
        
        # Duplicate message prevention
        self.sent_messages = {}  # Store message hashes and timestamps
        self.duplicate_threshold = 30  # seconds

        if self.webhook_url and SLACK_SDK_AVAILABLE:
            try:
                self.webhook_client = WebhookClient(self.webhook_url)
                logger.info("Webhook client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize webhook client: {e}")
                self.webhook_client = None

        if self.bot_token and SLACK_SDK_AVAILABLE:
            try:
                self.bot_client = WebClient(token=self.bot_token)
                logger.info("Bot client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize bot client: {e}")
                self.bot_client = None

        if self.user_token and SLACK_SDK_AVAILABLE:
            try:
                self.user_client = WebClient(token=self.user_token)
                logger.info("User client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize user client: {e}")
                self.user_client = None

    def _is_duplicate_message(self, message_content: str) -> bool:
        """
        Check if a message is a duplicate within the threshold time
        
        Args:
            message_content: Message content to check
            
        Returns:
            bool: True if duplicate, False otherwise
        """
        # Create hash of message content
        message_hash = hashlib.md5(message_content.encode()).hexdigest()
        current_time = datetime.now()
        
        # Clean old entries
        cutoff_time = current_time - timedelta(seconds=self.duplicate_threshold)
        self.sent_messages = {
            hash_key: timestamp 
            for hash_key, timestamp in self.sent_messages.items() 
            if timestamp > cutoff_time
        }
        
        # Check if message was sent recently
        if message_hash in self.sent_messages:
            logger.info(f"Duplicate message detected, skipping: {message_content[:50]}...")
            return True
        
        # Record this message
        self.sent_messages[message_hash] = current_time
        return False

    def send_simple_message(
        self,
        message: str,
        channel: Optional[str] = None,
        username: str = "SDP Bot",
        icon_emoji: str = ":game_die:",
    ) -> bool:
        """
        Send simple text message using webhook (most reliable)

        Args:
            message: Text message to send
            channel: Channel to send to (defaults to default_channel)
            username: Bot username
            icon_emoji: Bot icon emoji

        Returns:
            bool: True if successful, False otherwise
        """
        # Check for duplicate message
        if self._is_duplicate_message(message):
            return True  # Return True to indicate "success" (message was handled)
        
        if not self.webhook_client:
            logger.error("Webhook client not available")
            return False

        channel = channel or self.default_channel

        try:
            response = self.webhook_client.send(text=message)

            if response.status_code == 200:
                logger.info(f"Message sent successfully to {channel}")
                return True
            else:
                logger.error(f"Failed to send message: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending webhook message: {e}")
            return False

    def send_rich_message(
        self,
        channel: str,
        blocks: List[Dict[str, Any]],
        text: Optional[str] = None,
        use_user_token: bool = True,
    ) -> bool:
        """
        Send rich message with blocks using bot token or user token

        Args:
            channel: Channel to send to
            blocks: List of block elements for rich formatting
            text: Fallback text for notifications
            use_user_token: If True, prefer user token (messages can be deleted).
                           If False, use bot token. Default: True

        Returns:
            bool: True if successful, False otherwise
        """
        # Prefer user token if available and requested (messages sent with user token can be deleted)
        client = None
        token_type = None
        
        if use_user_token and self.user_client:
            client = self.user_client
            token_type = "user"
        elif self.bot_client:
            client = self.bot_client
            token_type = "bot"
        else:
            logger.error("No client available (neither user nor bot token)")
            return False

        try:
            response = client.chat_postMessage(
                channel=channel,
                text=text or "SDP Notification",
                blocks=blocks,
            )

            if response["ok"]:
                logger.info(
                    f"Rich message sent successfully to {channel} using {token_type} token"
                )
                return True
            else:
                logger.error(
                    f"Failed to send rich message: {response.get('error')}"
                )
                return False

        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending rich message: {e}")
            return False

    def get_user_id_by_name(
        self, display_name: str, email: Optional[str] = None
    ) -> Optional[str]:
        """
        Get Slack user ID by display name or email

        Args:
            display_name: User's display name (e.g., "Mark Bochkov")
            email: User's email address (optional, more reliable)

        Returns:
            str: User ID if found, None otherwise
        """
        if not self.bot_client:
            logger.warning("Bot client not available, cannot lookup user")
            return None

        try:
            # Try email lookup first if provided
            if email:
                try:
                    response = self.bot_client.users_lookupByEmail(email=email)
                    if response["ok"]:
                        user_id = response["user"]["id"]
                        logger.info(
                            f"Found user {display_name} by email: {user_id}"
                        )
                        return user_id
                except SlackApiError as e:
                    if e.response["error"] != "users_not_found":
                        logger.warning(
                            f"Email lookup failed for {email}: {e.response['error']}"
                        )

            # Fallback to list all users and search by name
            response = self.bot_client.users_list()
            if not response["ok"]:
                logger.error(f"Failed to get users list: {response.get('error')}")
                return None

            # Search for user by display name or real name
            display_name_lower = display_name.lower()
            for user in response["members"]:
                # Check display name
                if (
                    user.get("profile", {}).get("display_name", "").lower()
                    == display_name_lower
                ):
                    user_id = user["id"]
                    logger.info(
                        f"Found user {display_name} by display name: {user_id}"
                    )
                    return user_id

                # Check real name
                if (
                    user.get("profile", {}).get("real_name", "").lower()
                    == display_name_lower
                ):
                    user_id = user["id"]
                    logger.info(
                        f"Found user {display_name} by real name: {user_id}"
                    )
                    return user_id

            logger.warning(f"User {display_name} not found")
            return None

        except SlackApiError as e:
            logger.error(f"Slack API error looking up user: {e.response['error']}")
            return None
        except Exception as e:
            logger.error(f"Error looking up user: {e}")
            return None

    def send_roulette_sensor_error_notification(
        self,
        action_message: str,
        table_name: str,
        error_code: Optional[str] = None,
        mention_user: Optional[str] = None,
        mention_user_email: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> bool:
        """
        Send formatted roulette sensor error notification
        Specialized format for hardware sensor errors

        Args:
            action_message: Action message (e.g., "relaunch the wheel controller with *P 1")
            table_name: Table name (e.g., "ARO-001-1 (speed - main)")
            error_code: Error code if available
            mention_user: Display name of user to mention (e.g., "Mark Bochkov")
            mention_user_email: Email of user to mention (optional, more reliable)
            channel: Channel to send to (defaults to default_channel)

        Returns:
            bool: True if successful, False otherwise
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Use provided channel or fallback to default_channel
        target_channel = channel or self.default_channel

        # Get user ID if mention is requested
        mention_text = ""
        if mention_user:
            user_id = self.get_user_id_by_name(mention_user, mention_user_email)
            if user_id:
                mention_text = f"<@{user_id}> "
                logger.info(f"Mentioning user {mention_user} ({user_id})")
            else:
                logger.warning(
                    f"Could not find user {mention_user} to mention, "
                    "sending without mention"
                )

        # Create rich message blocks for roulette error
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Roulette error",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{mention_text}*Error requires your attention*"
                    if mention_text
                    else "*Error occurred*",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Time:*\n{timestamp}"},
                ],
            },
        ]

        # Add table name
        if table_name:
            blocks.append(
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Table:*\n{table_name}"}
                    ],
                }
            )

        # Add error code
        if error_code:
            blocks.append(
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Error Code:*\n{error_code}",
                        }
                    ],
                }
            )

        # Add action message
        if action_message:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Action:*\n```{action_message}```",
                    },
                }
            )

        # Try to send rich message first, fallback to simple message
        # Use user token if available so messages can be deleted
        if self.bot_client or self.user_client:
            success = self.send_rich_message(
                target_channel, blocks, use_user_token=True
            )
            if success:
                return True

        # Fallback to simple message
        simple_message = "🚨 Roulette error\n"
        if mention_text:
            simple_message = f"{mention_text}{simple_message}"
        if table_name:
            simple_message += f"Table: {table_name}\n"
        if error_code:
            simple_message += f"Error Code: {error_code}\n"
        if action_message:
            simple_message += f"Action: {action_message}\n"
        simple_message += f"Time: {timestamp}"

        return self.send_simple_message(simple_message, channel=target_channel)

    def send_error_notification(
        self,
        error_message: str,
        error_code: Optional[str] = None,
        table_name: Optional[str] = None,
        environment: str = "Unknown",
        mention_user: Optional[str] = None,
        mention_user_email: Optional[str] = None,
        channel: Optional[str] = None,
        action_message: Optional[str] = None,
    ) -> bool:
        """
        Send formatted error notification

        Args:
            error_message: Error message
            error_code: Error code if available
            table_name: Table name if relevant
            environment: Environment (CIT/UAT/QAT/STG/PRD)
            mention_user: Display name of user to mention (e.g., "Kevin Kuo")
            mention_user_email: Email of user to mention (optional, more reliable)
            channel: Channel to send to (defaults to default_channel)
            action_message: Action message (e.g., "None (auto-recoverable)")

        Returns:
            bool: True if successful, False otherwise
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Use provided channel or fallback to default_channel
        target_channel = channel or self.default_channel

        # Get user ID if mention is requested
        mention_text = ""
        if mention_user:
            user_id = self.get_user_id_by_name(mention_user, mention_user_email)
            if user_id:
                mention_text = f"<@{user_id}> "
                logger.info(f"Mentioning user {mention_user} ({user_id})")
            else:
                logger.warning(
                    f"Could not find user {mention_user} to mention, "
                    "sending without mention"
                )

        # Create rich message blocks (similar to Roulette error format)
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 SDP Error",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{mention_text}*Error requires your attention*"
                    if mention_text
                    else "*Error occurred*",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Env:*\n{environment}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{timestamp}"},
                ],
            },
        ]

        if table_name:
            blocks.append(
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Table:*\n{table_name}"}
                    ],
                }
            )

        if error_code:
            blocks.append(
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Error Code:*\n{error_code}",
                        }
                    ],
                }
            )

        # Add action message
        if action_message:
            blocks.append(
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Action:*\n{action_message}",
                        }
                    ],
                }
            )

        # Try to send rich message first, fallback to simple message
        # Use user token if available so messages can be deleted
        if self.bot_client or self.user_client:
            success = self.send_rich_message(
                target_channel, blocks, use_user_token=True
            )
            if success:
                return True

        # Fallback to simple message (simplified format)
        simple_message = "🚨 SDP Error\n"
        if mention_text:
            simple_message = f"{mention_text}{simple_message}"
        simple_message += f"Env: {environment}\n"
        if table_name:
            simple_message += f"Table: {table_name}\n"
        if error_code:
            simple_message += f"Error Code: {error_code}\n"
        if action_message:
            simple_message += f"Action: {action_message}\n"
        simple_message += f"Time: {timestamp}"

        return self.send_simple_message(simple_message, channel=target_channel)

    def send_success_notification(
        self,
        message: str,
        environment: str = "Unknown",
        table_name: Optional[str] = None,
    ) -> bool:
        """
        Send success notification

        Args:
            message: Success message
            environment: Environment name
            table_name: Table name if relevant

        Returns:
            bool: True if successful, False otherwise
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        simple_message = f"✅ SDP Success in {environment}\n"
        if table_name:
            simple_message += f"Table: {table_name}\n"
        simple_message += f"Message: {message}\nTime: {timestamp}"

        return self.send_simple_message(
            simple_message, icon_emoji=":white_check_mark:"
        )

    def send_webhook_fallback(
        self, message: str, channel: str = "#general"
    ) -> bool:
        """
        Fallback method using requests library if slack-sdk is not available

        Args:
            message: Message to send
            channel: Channel to send to

        Returns:
            bool: True if successful, False otherwise
        """
        # Check for duplicate message
        if self._is_duplicate_message(message):
            return True  # Return True to indicate "success" (message was handled)
        
        if not REQUESTS_AVAILABLE:
            logger.error("Requests library not available for webhook fallback")
            return False

        if not self.webhook_url:
            logger.error("Webhook URL not configured")
            return False

        payload = {
            "text": message,
            "channel": channel,
            "username": "SDP Bot",
            "icon_emoji": ":game_die:",
        }

        try:
            response = requests.post(
                self.webhook_url, json=payload, timeout=10
            )
            if response.status_code == 200:
                logger.info(f"Webhook message sent successfully to {channel}")
                return True
            else:
                logger.error(
                    f"Webhook failed: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending webhook fallback: {e}")
            return False


# Convenience functions for quick usage
def send_roulette_sensor_error_to_slack(
    action_message: str,
    table_name: str,
    error_code: Optional[str] = None,
    mention_user: Optional[str] = None,
    mention_user_email: Optional[str] = None,
    channel: Optional[str] = None,
) -> bool:
    """
    Quick function to send roulette sensor error notification

    Args:
        action_message: Action message (e.g., "relaunch the wheel controller with *P 1")
        table_name: Table name (e.g., "ARO-001-1 (speed - main)")
        error_code: Error code if available
        mention_user: Display name of user to mention (e.g., "Mark Bochkov")
        mention_user_email: Email of user to mention (optional, more reliable)
        channel: Channel to send to (defaults to #studio-rnd for sensor errors)

    Returns:
        bool: True if successful, False otherwise
    """
    # Load environment variables if not already loaded
    from dotenv import load_dotenv

    load_dotenv()

    # Get default channel from environment or use studio-rnd as default for sensor errors
    default_channel = os.getenv("SLACK_DEFAULT_CHANNEL", "#studio-rnd")
    
    notifier = SlackNotifier(default_channel=default_channel)
    return notifier.send_roulette_sensor_error_notification(
        action_message,
        table_name,
        error_code,
        mention_user,
        mention_user_email,
        channel or "#studio-rnd",
    )


def send_error_to_slack(
    error_message: str,
    environment: str = "Unknown",
    table_name: Optional[str] = None,
    error_code: Optional[str] = None,
    mention_user: Optional[str] = None,
    mention_user_email: Optional[str] = None,
    channel: Optional[str] = None,
    action_message: Optional[str] = None,
) -> bool:
    """
    Quick function to send error notification

    Args:
        error_message: Error message
        environment: Environment name
        table_name: Table name if relevant
        error_code: Error code if available
        mention_user: Display name of user to mention (e.g., "Kevin Kuo")
        mention_user_email: Email of user to mention (optional, more reliable)
        channel: Channel to send to (defaults to default_channel)
        action_message: Action message (e.g., "None (auto-recoverable)")

    Returns:
        bool: True if successful, False otherwise
    """
    # Load environment variables if not already loaded
    from dotenv import load_dotenv

    load_dotenv()

    notifier = SlackNotifier()
    return notifier.send_error_notification(
        error_message,
        error_code,
        table_name,
        environment,
        mention_user,
        mention_user_email,
        channel,
        action_message,
    )


def send_success_to_slack(
    message: str,
    environment: str = "Unknown",
    table_name: Optional[str] = None,
) -> bool:
    """
    Quick function to send success notification

    Args:
        message: Success message
        environment: Environment name
        table_name: Table name if relevant

    Returns:
        bool: True if successful, False otherwise
    """
    # Load environment variables if not already loaded
    from dotenv import load_dotenv

    load_dotenv()

    notifier = SlackNotifier()
    return notifier.send_success_notification(message, environment, table_name)


# Example usage
if __name__ == "__main__":
    # Test the notifier
    notifier = SlackNotifier()

    # Test simple message
    notifier.send_simple_message("Hello from SDP!")

    # Test error notification
    notifier.send_error_notification(
        "Table round not finished yet", "13003", "BCR-001", "STG"
    )
