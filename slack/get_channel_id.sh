#!/bin/bash
# Script to get Slack channel ID by channel name

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

# Get channel name from argument or use default
CHANNEL_NAME="${1:-studio-rnd}"

# Remove # prefix if present
CHANNEL_NAME="${CHANNEL_NAME#\#}"

echo "Looking for channel: #${CHANNEL_NAME}"
echo ""

# Get all channels (public and private)
RESPONSE=$(curl -s -X GET "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=1000" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json")

# Check if API call was successful
if echo "$RESPONSE" | grep -q '"ok":true'; then
    # Use jq if available for better parsing
    if command -v jq &> /dev/null; then
        CHANNEL_ID=$(echo "$RESPONSE" | jq -r ".channels[] | select(.name==\"$CHANNEL_NAME\") | .id")
        CHANNEL_IS_PRIVATE=$(echo "$RESPONSE" | jq -r ".channels[] | select(.name==\"$CHANNEL_NAME\") | .is_private")
        CHANNEL_IS_ARCHIVED=$(echo "$RESPONSE" | jq -r ".channels[] | select(.name==\"$CHANNEL_NAME\") | .is_archived")
        
        if [ -n "$CHANNEL_ID" ] && [ "$CHANNEL_ID" != "null" ]; then
            echo "✅ Found channel #${CHANNEL_NAME}"
            echo ""
            echo "Channel ID: $CHANNEL_ID"
            echo "Is Private: $CHANNEL_IS_PRIVATE"
            echo "Is Archived: $CHANNEL_IS_ARCHIVED"
            echo ""
            echo "Full channel info:"
            echo "$RESPONSE" | jq ".channels[] | select(.name==\"$CHANNEL_NAME\")"
        else
            echo "❌ Channel #${CHANNEL_NAME} not found"
            echo ""
            echo "Available channels:"
            echo "$RESPONSE" | jq -r '.channels[] | "  - \(.name) (ID: \(.id), Private: \(.is_private))"'
        fi
    else
        # Fallback: use grep (less reliable)
        echo "⚠️  jq not found, using basic parsing..."
        echo ""
        
        # Try to find channel ID
        CHANNEL_MATCH=$(echo "$RESPONSE" | grep -A 10 "\"name\":\"$CHANNEL_NAME\"")
        
        if [ -n "$CHANNEL_MATCH" ]; then
            CHANNEL_ID=$(echo "$CHANNEL_MATCH" | grep "\"id\"" | head -1 | grep -o "\"id\":\"[^\"]*\"" | cut -d'"' -f4)
            if [ -n "$CHANNEL_ID" ]; then
                echo "✅ Found channel #${CHANNEL_NAME}"
                echo "Channel ID: $CHANNEL_ID"
            else
                echo "❌ Could not extract channel ID"
                echo "Raw response: $RESPONSE"
            fi
        else
            echo "❌ Channel #${CHANNEL_NAME} not found"
            echo ""
            echo "Available channels (first 20):"
            echo "$RESPONSE" | grep -o '"name":"[^"]*"' | head -20 | sed 's/"name":"/  - /' | sed 's/"$//'
        fi
    fi
else
    echo "❌ Failed to get channel list"
    echo ""
    echo "API Response:"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    echo ""
    
    # Check for specific error types
    if echo "$RESPONSE" | grep -q "missing_scope"; then
        MISSING_SCOPE=$(echo "$RESPONSE" | grep -o '"needed":"[^"]*"' | cut -d'"' -f4)
        echo "⚠️  Missing scope: $MISSING_SCOPE"
        echo ""
        echo "解決方案："
        echo "  1. 前往 https://api.slack.com/apps"
        echo "  2. 選擇你的 Slack App"
        echo "  3. 進入 'OAuth & Permissions'"
        echo "  4. 在 'Bot Token Scopes' 中添加 '$MISSING_SCOPE' 權限"
        echo "  5. 點擊 'Reinstall App' 重新安裝到 workspace"
        echo ""
        echo "如果無法添加權限，可以使用頻道 ID 直接加入："
        echo "  curl -X POST https://slack.com/api/conversations.join \\"
        echo "    -H \"Authorization: Bearer \$SLACK_BOT_TOKEN\" \\"
        echo "    -H \"Content-Type: application/json\" \\"
        echo "    -d '{\"channel\": \"CHANNEL_ID\"}'"
    else
        echo "Possible reasons:"
        echo "  1. Invalid SLACK_BOT_TOKEN"
        echo "  2. Bot token doesn't have required permissions"
        echo "  3. Network error"
    fi
fi

