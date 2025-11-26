#!/bin/bash
# Start SDP Roulette System with separated logs

echo "Starting SDP Roulette System with separated logs..."

# Check if tmux session exists
if ! tmux has-session -t dp 2>/dev/null; then
    echo "Session 'dp' does not exist. Please create it first."
    exit 1
fi

# Check if log windows exist, if not create them
if ! tmux list-windows -t dp | grep -q "log_mqtt"; then
    echo "Setting up log windows..."
    ./setup_tmux_logs.sh
fi

# Attach to tmux session
echo "Attaching to tmux session..."
echo "Windows available:"
echo "  0: bash - Terminal window"
echo "  1: sdp - Run main_speed.py here (existing window)"
echo "  2: idp - IDP related window (existing window)"
echo "  3: log_mqtt - MQTT logs (new)"
echo "  4: log_api - API logs (new)" 
echo "  5: log_serial - Serial logs (new)"
echo ""
echo "Press Ctrl+b then window number to switch windows"
echo ""

# Switch to sdp window and run the application
echo "Starting main_speed.py in sdp window..."
tmux send-keys -t dp:sdp "python main_speed.py" Enter

# Attach to the session
tmux attach -t dp
