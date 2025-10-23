#!/bin/bash
# Setup tmux session with separate log windows for SDP Roulette System

SESSION_NAME="dp"

# Check if tmux session exists
if ! tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Session $SESSION_NAME does not exist. Please create it first."
    exit 1
fi

echo "Adding log windows to existing session: $SESSION_NAME"

# Create log windows
echo "Creating log windows..."

# Check if log windows already exist and remove them
if tmux list-windows -t $SESSION_NAME | grep -q "log_mqtt"; then
    echo "Removing existing log_mqtt window..."
    tmux kill-window -t $SESSION_NAME:log_mqtt 2>/dev/null || true
fi

if tmux list-windows -t $SESSION_NAME | grep -q "log_api"; then
    echo "Removing existing log_api window..."
    tmux kill-window -t $SESSION_NAME:log_api 2>/dev/null || true
fi

if tmux list-windows -t $SESSION_NAME | grep -q "log_serial"; then
    echo "Removing existing log_serial window..."
    tmux kill-window -t $SESSION_NAME:log_serial 2>/dev/null || true
fi

# Create log_mqtt window
tmux new-window -t $SESSION_NAME -n "log_mqtt"
tmux send-keys -t $SESSION_NAME:log_mqtt "echo 'MQTT Log Window - Ready to receive MQTT logs'" Enter
tmux send-keys -t $SESSION_NAME:log_mqtt "echo 'Use: tail -f logs/sdp_mqtt.log' to view logs" Enter

# Create log_api window  
tmux new-window -t $SESSION_NAME -n "log_api"
tmux send-keys -t $SESSION_NAME:log_api "echo 'API Log Window - Ready to receive API logs'" Enter
tmux send-keys -t $SESSION_NAME:log_api "echo 'Use: tail -f logs/sdp_api.log' to view logs" Enter

# Create log_serial window
tmux new-window -t $SESSION_NAME -n "log_serial"
tmux send-keys -t $SESSION_NAME:log_serial "echo 'Serial Log Window - Ready to receive Serial logs'" Enter
tmux send-keys -t $SESSION_NAME:log_serial "echo 'Use: tail -f logs/sdp_serial.log' to view logs" Enter

# Set up log monitoring in each window
echo "Setting up log monitoring..."

# Setup MQTT log monitoring
tmux send-keys -t $SESSION_NAME:log_mqtt "tail -f logs/sdp_mqtt.log" Enter

# Setup API log monitoring  
tmux send-keys -t $SESSION_NAME:log_api "tail -f logs/sdp_api.log" Enter

# Setup Serial log monitoring
tmux send-keys -t $SESSION_NAME:log_serial "tail -f logs/sdp_serial.log" Enter

# Create logs directory and log files
mkdir -p logs
touch logs/sdp_mqtt.log logs/sdp_api.log logs/sdp_serial.log

echo "Tmux session setup complete!"
echo ""
echo "Session name: $SESSION_NAME"
echo "Windows available:"
echo "  - bash: Terminal window"
echo "  - sdp: Run main_speed.py here (existing window)"
echo "  - idp: IDP related window (existing window)"
echo "  - log_mqtt: MQTT related logs (new)"
echo "  - log_api: Table API related logs (new)" 
echo "  - log_serial: Serial port related logs (new)"
echo ""
echo "To attach to session: tmux attach -t $SESSION_NAME"
echo "To switch windows: Ctrl+b then window number"
echo ""
echo "Log files location:"
echo "  - MQTT: logs/sdp_mqtt.log"
echo "  - API: logs/sdp_api.log"
echo "  - Serial: logs/sdp_serial.log"
