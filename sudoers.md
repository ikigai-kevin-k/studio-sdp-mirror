# Sudoers Configuration for Passwordless Execution

This document describes how to configure sudoers to allow passwordless execution of `main_speed_2.py` for the `rnd` user.

## Problem

The `sr_standby_client.py` script needs to execute `main_speed_2.py` using sudo without requiring password input, which would cause the automation to fail.

## Solution

Configure sudoers to allow the `rnd` user to execute `main_speed_2.py` without password authentication.

## Steps

### 1. Create Sudoers Configuration File

Create a new sudoers file specifically for the `rnd` user:

```bash
echo "# Allow rnd user to run main_speed_2.py without password
rnd ALL=(ALL) NOPASSWD: /home/rnd/studio-sdp-roulette/venv/bin/python3 /home/rnd/studio-sdp-roulette/main_speed_2.py" | sudo tee /etc/sudoers.d/rnd-nopasswd
```

### 2. Set Correct Permissions

Sudoers files must have specific permissions (0440) for security:

```bash
sudo chmod 0440 /etc/sudoers.d/rnd-nopasswd
```

### 3. Validate Configuration

Verify the sudoers configuration is syntactically correct:

```bash
sudo visudo -c
```

Expected output:
```
/etc/sudoers: parsed OK
/etc/sudoers.d/README: parsed OK
/etc/sudoers.d/rnd-nopasswd: parsed OK
```

### 4. Test Passwordless Execution

Test that the command can be executed without password:

```bash
sudo venv/bin/python3 main_speed_2.py --help
```

## Configuration Details

**File Location:** `/etc/sudoers.d/rnd-nopasswd`

**Content:**
```
# Allow rnd user to run main_speed_2.py without password
rnd ALL=(ALL) NOPASSWD: /home/rnd/studio-sdp-roulette/venv/bin/python3 /home/rnd/studio-sdp-roulette/main_speed_2.py
```

**Explanation:**
- `rnd`: The username
- `ALL=(ALL)`: Can run as any user on any host
- `NOPASSWD:`: No password required
- `/home/rnd/studio-sdp-roulette/venv/bin/python3 /home/rnd/studio-sdp-roulette/main_speed_2.py`: The specific command allowed

## Security Considerations

1. **Specificity**: Only the exact command path is allowed, not wildcards
2. **Limited Scope**: Only affects the `rnd` user
3. **File Permissions**: The sudoers file has restricted permissions (0440)
4. **Isolation**: Uses a separate file in `/etc/sudoers.d/` instead of modifying the main sudoers file

## Troubleshooting

### Permission Denied Error
If you get permission errors, ensure the file has correct permissions:
```bash
sudo chmod 0440 /etc/sudoers.d/rnd-nopasswd
```

### Syntax Error
If `visudo -c` reports syntax errors, check the file content:
```bash
sudo cat /etc/sudoers.d/rnd-nopasswd
```

### Command Not Found
Ensure the full path to the Python executable and script is correct:
```bash
which python
ls -la /home/rnd/studio-sdp-roulette/venv/bin/python
ls -la /home/rnd/studio-sdp-roulette/main_speed_2.py
```

## Usage in Code

The `sr_standby_client.py` script can now execute:

```python
tmux_command = [
    "tmux", "send-keys", "-t", "dp:sdp",
    f"cd {studio_dir} && sudo venv/bin/python3 main_speed_2.py",
    "Enter"
]
```

Without requiring password input, enabling automated failover functionality.
