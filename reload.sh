#!/bin/bash
# -*- coding: utf-8 -*-
"""
Reload command for manual hot reload
Usage: ./reload.sh
"""

RELOAD_TRIGGER_FILE="$HOME/sdp_hotreload_trigger"

if [ ! -f "$RELOAD_TRIGGER_FILE" ]; then
    echo "❌ Hot reload not available - main_speed.py is not running"
    echo "   Start main_speed.py first to enable hot reload"
    exit 1
fi

echo "🔄 Triggering hot reload..."
echo "reload" > "$RELOAD_TRIGGER_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Reload command sent successfully"
    echo "   Check main_speed.py logs for reload status"
else
    echo "❌ Failed to send reload command"
    exit 1
fi
