# TMUX Session Management

## Creating a TMUX Session with Multiple Windows

### Step 1: Create a new TMUX session with the first window
```bash
tmux new-session -d -s dp -n sdp
```
- `-d`: Create session in detached mode
- `-s dp`: Name the session "dp"
- `-n sdp`: Name the first window "sdp"

### Step 2: Create additional windows in the existing session
```bash
tmux new-window -t dp -n standby
```
- `-t dp`: Target the existing session "dp"
- `-n standby`: Name the new window "standby"

### Step 3: Verify the session and windows were created
```bash
# List all TMUX sessions
tmux list-sessions

# List windows within a specific session
tmux list-windows -t dp
```

## Connecting to the TMUX Session

### Connect to the session (will attach to the active window)
```bash
tmux attach-session -t dp
```

### Connect to a specific window
```bash
# Connect to window 0 (sdp)
tmux attach-session -t dp:0

# Connect to window 1 (standby)
tmux attach-session -t dp:1
```

## Navigation Within TMUX Session

### Switch between windows
- `Ctrl+b` then `0` - Switch to window 0 (sdp)
- `Ctrl+b` then `1` - Switch to window 1 (standby)
- `Ctrl+b` then `n` - Switch to next window
- `Ctrl+b` then `p` - Switch to previous window

### Detach from session
- `Ctrl+b` then `d` - Detach from current session (keeps it running)

## Session Information

The created session contains:
- **Session Name**: dp
- **Window 0**: sdp
- **Window 1**: standby (currently active)

## Useful Commands

### List all sessions
```bash
tmux list-sessions
```

### List windows in a session
```bash
tmux list-windows -t <session-name>
```

### Kill a session
```bash
tmux kill-session -t dp
```

### Rename a window
```bash
tmux rename-window -t dp:0 new-window-name
```
