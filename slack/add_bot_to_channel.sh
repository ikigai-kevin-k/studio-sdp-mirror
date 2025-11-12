#!/bin/bash
# Script to add Slack bot to a channel using bot token from .env file

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

# Channel name (without #)
CHANNEL_NAME="studio-rnd"

echo "=========================================="
echo "Slack Bot Channel Management Script"
echo "=========================================="
echo ""

# Step 1: Get channel ID
echo "Step 1: Getting channel ID for #${CHANNEL_NAME}..."
echo ""

# Get all channels (public and private)
CHANNEL_INFO=$(curl -s -X GET "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=1000" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json")

# Check if API call was successful
if echo "$CHANNEL_INFO" | grep -q '"ok":true'; then
    # Extract channel ID using jq (if available) or grep
    if command -v jq &> /dev/null; then
        CHANNEL_ID=$(echo "$CHANNEL_INFO" | jq -r ".channels[] | select(.name==\"$CHANNEL_NAME\") | .id")
    else
        # Fallback: use grep and sed (less reliable but works)
        CHANNEL_ID=$(echo "$CHANNEL_INFO" | grep -o "\"id\":\"[^\"]*\",\"name\":\"$CHANNEL_NAME\"" | grep -o "\"id\":\"[^\"]*\"" | cut -d'"' -f4)
        if [ -z "$CHANNEL_ID" ]; then
            # Try alternative pattern
            CHANNEL_ID=$(echo "$CHANNEL_INFO" | grep -A 5 "\"name\":\"$CHANNEL_NAME\"" | grep "\"id\"" | head -1 | grep -o "\"id\":\"[^\"]*\"" | cut -d'"' -f4)
        fi
    fi
    
    if [ -n "$CHANNEL_ID" ] && [ "$CHANNEL_ID" != "null" ]; then
        echo "✅ Found channel ID: $CHANNEL_ID"
        echo ""
    else
        echo "❌ Channel #${CHANNEL_NAME} not found in workspace"
        echo ""
        echo "Available channels:"
        if command -v jq &> /dev/null; then
            echo "$CHANNEL_INFO" | jq -r '.channels[] | "  - \(.name) (ID: \(.id))"'
        else
            echo "$CHANNEL_INFO" | grep -o '"name":"[^"]*"' | sed 's/"name":"/  - /' | sed 's/"$//'
        fi
        exit 1
    fi
else
    echo "❌ Failed to get channel list"
    echo ""
    echo "API Response:"
    echo "$CHANNEL_INFO" | jq '.' 2>/dev/null || echo "$CHANNEL_INFO"
    echo ""
    
    # Check for specific error types
    if echo "$CHANNEL_INFO" | grep -q "missing_scope"; then
        MISSING_SCOPE=$(echo "$CHANNEL_INFO" | grep -o '"needed":"[^"]*"' | cut -d'"' -f4)
        echo "⚠️  Missing scope: $MISSING_SCOPE"
        echo ""
        echo "解決方案："
        echo "  1. 前往 https://api.slack.com/apps"
        echo "  2. 選擇你的 Slack App"
        echo "  3. 進入 'OAuth & Permissions'"
        echo "  4. 在 'Bot Token Scopes' 中添加 '$MISSING_SCOPE' 權限"
        echo "  5. 點擊 'Reinstall App' 重新安裝到 workspace"
        echo ""
        echo "或者，如果你知道頻道 ID，可以直接使用："
        echo "  export \$(cat .env | grep SLACK_BOT_TOKEN | xargs)"
        echo "  curl -X POST https://slack.com/api/conversations.join \\"
        echo "    -H \"Authorization: Bearer \$SLACK_BOT_TOKEN\" \\"
        echo "    -H \"Content-Type: application/json\" \\"
        echo "    -d '{\"channel\": \"CHANNEL_ID\"}'"
    fi
    exit 1
fi

# Step 2: Join the channel
echo "Step 2: Joining channel #${CHANNEL_NAME} (ID: $CHANNEL_ID)..."
echo ""

JOIN_RESULT=$(curl -s -X POST "https://slack.com/api/conversations.join" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"channel\":\"$CHANNEL_ID\"}")

# Check if join was successful
if echo "$JOIN_RESULT" | grep -q '"ok":true'; then
    echo "✅ Successfully joined channel #${CHANNEL_NAME}"
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
    echo "Response: $JOIN_RESULT"
    echo ""
    echo "Possible reasons:"
    echo "  1. Bot is already in the channel"
    echo "  2. Bot doesn't have permission to join private channels"
    echo "  3. Channel ID is incorrect"
    exit 1
fi

echo ""
echo "=========================================="
echo "Done!"
echo "=========================================="

