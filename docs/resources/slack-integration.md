# Slack Integration

This guide explains Slack notification integration.

## Overview

The system can send notifications to Slack channels for errors and important events.

## Configuration

Set environment variables:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_BOT_TOKEN=xoxb-your-bot-token
```

## Usage

```python
from slack import send_error_to_slack

send_error_to_slack(
    error_message="Error description",
    error_code="ERROR_CODE",
    table_name="Table Name",
    environment="Environment"
)
```

## Related Documentation

- [Slack README](../../slack/README.md)
- [Slack Setup Guide](../../slack/SLACK_SETUP_GUIDE.md)

