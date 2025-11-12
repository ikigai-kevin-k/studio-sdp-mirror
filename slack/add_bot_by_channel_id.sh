#!/bin/bash
# Script to add Slack bot to a channel using channel ID directly
# Use this if you know the channel ID but don't have groups:read permission

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Error: .env file not found"
    exit 1
fi

# Check if SLACK_BOT_TOKEN is set
if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "Error: SLACK_BOT_TOKEN not found in .env file"
    exit 1
fi

# Get channel ID from argument
if [ -z "$1" ]; then
    echo "Usage: $0 <CHANNEL_ID>"
    echo ""
    echo "Example:"
    echo "  $0 C1234567890"
    echo ""
    echo "To find channel ID:"
    echo "  1. Open Slack web app"
    echo "  2. Right-click on the channel name"
    echo "  3. Select 'View channel details' or 'Copy link'"
    echo "  4. Channel ID is in the URL: https://workspace.slack.com/archives/CHANNEL_ID"
    exit 1
fi

CHANNEL_ID="$1"

echo "=========================================="
echo "Adding Slack Bot to Channel"
echo "=========================================="
echo ""
echo "Channel ID: $CHANNEL_ID"
echo ""

# Join the channel
echo "Joining channel..."
JOIN_RESULT=$(curl -s -X POST "https://slack.com/api/conversations.join" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"channel\":\"$CHANNEL_ID\"}")

# Check if join was successful
if echo "$JOIN_RESULT" | grep -q '"ok":true'; then
    echo "✅ Successfully joined channel"
    echo ""
    
    # Display channel info
    if command -v jq &> /dev/null; then
        echo "Channel information:"
        echo "$JOIN_RESULT" | jq '.'
    else
        echo "Join result: $JOIN_RESULT"
    fi
else
    echo "❌ Failed to join channel"
    echo ""
    echo "API Response:"
    echo "$JOIN_RESULT" | jq '.' 2>/dev/null || echo "$JOIN_RESULT"
    echo ""
    
    # Check for specific errors
    if echo "$JOIN_RESULT" | grep -q "channel_not_found"; then
        echo "⚠️  Channel not found. Please verify the channel ID is correct."
    elif echo "$JOIN_RESULT" | grep -q "already_in_channel"; then
        echo "✅ Bot is already in the channel"
    elif echo "$JOIN_RESULT" | grep -q "missing_scope"; then
        MISSING_SCOPE=$(echo "$JOIN_RESULT" | grep -o '"needed":"[^"]*"' | cut -d'"' -f4)
        echo "⚠️  Missing scope: $MISSING_SCOPE"
        echo ""
        echo "請添加此權限到 Bot Token Scopes"
    fi
    exit 1
fi

echo ""
echo "=========================================="
echo "Done!"
echo "=========================================="

