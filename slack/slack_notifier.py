"""
Slack notification module for sending messages to Slack channels
Supports multiple methods: Webhook, Bot Token, and User Token
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    from slack_sdk.webhook import WebhookClient
    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False
    print("Warning: slack-sdk not installed. "
          "Install with: pip install slack-sdk")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not installed. "
          "Install with: pip install requests")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlackNotifier:
    """
    Slack notification class with multiple sending methods
    """
    
    def __init__(self, 
                 webhook_url: Optional[str] = None,
                 bot_token: Optional[str] = None,
                 user_token: Optional[str] = None,
                 default_channel: str = "#general"):
        """
        Initialize Slack notifier
        
        Args:
            webhook_url: Slack webhook URL for simple messages
            bot_token: Bot user OAuth token for advanced features
            user_token: User OAuth token for user-specific actions
            default_channel: Default channel to send messages to
        """
        self.webhook_url = webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
        self.user_token = user_token or os.getenv('SLACK_USER_TOKEN')
        self.default_channel = default_channel
        
        # Initialize clients
        self.webhook_client = None
        self.bot_client = None
        self.user_client = None
        
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
    
    def send_simple_message(self, 
                           message: str, 
                           channel: Optional[str] = None,
                           username: str = "SDP Roulette Bot",
                           icon_emoji: str = ":game_die:") -> bool:
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
        if not self.webhook_client:
            logger.error("Webhook client not available")
            return False
            
        channel = channel or self.default_channel
        
        try:
            response = self.webhook_client.send(
                text=message
            )
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to {channel}")
                return True
            else:
                logger.error(f"Failed to send message: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending webhook message: {e}")
            return False
    
    def send_rich_message(self,
                          channel: str,
                          blocks: List[Dict[str, Any]],
                          text: Optional[str] = None) -> bool:
        """
        Send rich message with blocks using bot token
        
        Args:
            channel: Channel to send to
            blocks: List of block elements for rich formatting
            text: Fallback text for notifications
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.bot_client:
            logger.error("Bot client not available")
            return False
            
        try:
            response = self.bot_client.chat_postMessage(
                channel=channel,
                text=text or "SDP Roulette Notification",
                blocks=blocks
            )
            
            if response["ok"]:
                logger.info(f"Rich message sent successfully to {channel}")
                return True
            else:
                logger.error(f"Failed to send rich message: {response.get('error')}")
                return False
                
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"Error sending rich message: {e}")
            return False
    
    def send_error_notification(self,
                               error_message: str,
                               error_code: Optional[str] = None,
                               table_name: Optional[str] = None,
                               environment: str = "Unknown") -> bool:
        """
        Send formatted error notification
        
        Args:
            error_message: Error message
            error_code: Error code if available
            table_name: Table name if relevant
            environment: Environment (CIT/UAT/QAT/STG/PRD)
            
        Returns:
            bool: True if successful, False otherwise
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create rich message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 SDP Roulette Error - {environment}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Environment:*\n{environment}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{timestamp}"
                    }
                ]
            }
        ]
        
        if table_name:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Table:*\n{table_name}"
                    }
                ]
            })
        
        if error_code:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Error Code:*\n{error_code}"
                    }
                ]
            })
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Error Message:*\n```{error_message}```"
            }
        })
        
        # Try to send rich message first, fallback to simple message
        if self.bot_client:
            success = self.send_rich_message(self.default_channel, blocks)
            if success:
                return True
        
        # Fallback to simple message
        simple_message = f"🚨 SDP Roulette Error in {environment}\n"
        if table_name:
            simple_message += f"Table: {table_name}\n"
        if error_code:
            simple_message += f"Error Code: {error_code}\n"
        simple_message += f"Error: {error_message}\nTime: {timestamp}"
        
        return self.send_simple_message(simple_message)
    
    def send_success_notification(self,
                                 message: str,
                                 environment: str = "Unknown",
                                 table_name: Optional[str] = None) -> bool:
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
        
        simple_message = f"✅ SDP Roulette Success in {environment}\n"
        if table_name:
            simple_message += f"Table: {table_name}\n"
        simple_message += f"Message: {message}\nTime: {timestamp}"
        
        return self.send_simple_message(simple_message, icon_emoji=":white_check_mark:")
    
    def send_webhook_fallback(self, message: str, channel: str = "#general") -> bool:
        """
        Fallback method using requests library if slack-sdk is not available
        
        Args:
            message: Message to send
            channel: Channel to send to
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not REQUESTS_AVAILABLE:
            logger.error("Requests library not available for webhook fallback")
            return False
            
        if not self.webhook_url:
            logger.error("Webhook URL not configured")
            return False
            
        payload = {
            "text": message,
            "channel": channel,
            "username": "SDP Roulette Bot",
            "icon_emoji": ":game_die:"
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"Webhook message sent successfully to {channel}")
                return True
            else:
                logger.error(f"Webhook failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending webhook fallback: {e}")
            return False


# Convenience functions for quick usage
def send_error_to_slack(error_message: str, 
                        environment: str = "Unknown",
                        table_name: Optional[str] = None,
                        error_code: Optional[str] = None) -> bool:
    """
    Quick function to send error notification
    
    Args:
        error_message: Error message
        environment: Environment name
        table_name: Table name if relevant
        error_code: Error code if available
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Load environment variables if not already loaded
    from dotenv import load_dotenv
    load_dotenv()
    
    notifier = SlackNotifier()
    return notifier.send_error_notification(error_message, error_code, table_name, environment)


def send_success_to_slack(message: str,
                          environment: str = "Unknown",
                          table_name: Optional[str] = None) -> bool:
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
    notifier.send_simple_message("Hello from SDP Roulette!")
    
    # Test error notification
    notifier.send_error_notification(
        "Table round not finished yet",
        "13003",
        "BCR-001",
        "STG"
    )
