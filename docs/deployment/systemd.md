# Systemd Service Deployment

This guide explains how to deploy the Studio SDP Roulette System as systemd services.

## Overview

Systemd services provide:

- **Automatic Startup**: Services start automatically on boot
- **Process Management**: Automatic restart on failure
- **Logging**: Integrated with systemd journal
- **Resource Management**: CPU and memory limits

## Service Configuration

### SicBo Service

Create `/etc/systemd/system/sdp-sicbo.service`:

```ini
[Unit]
Description=SDP SicBo Game Service
After=network.target

[Service]
Type=simple
User=rnd
WorkingDirectory=/home/rnd
ExecStart=/home/rnd/sdp-env/bin/python /home/rnd/sdp-sicbo.pyz \
    --broker 192.168.88.54 \
    --port 1883 \
    --enable-logging \
    --log-dir /var/log/sdp
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment variables
Environment="MQTT_BROKER=192.168.88.54"
Environment="LOG_LEVEL=INFO"

[Install]
WantedBy=multi-user.target
```

### Speed Roulette Service

Create `/etc/systemd/system/sdp-speed.service`:

```ini
[Unit]
Description=SDP Speed Roulette Game Service
After=network.target

[Service]
Type=simple
User=rnd
WorkingDirectory=/home/rnd
ExecStart=/home/rnd/sdp-env/bin/python /home/rnd/sdp-speed.pyz
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### VIP Roulette Service

Create `/etc/systemd/system/sdp-vip.service`:

```ini
[Unit]
Description=SDP VIP Roulette Game Service
After=network.target

[Service]
Type=simple
User=rnd
WorkingDirectory=/home/rnd
ExecStart=/home/rnd/sdp-env/bin/python /home/rnd/sdp-vip.pyz
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Baccarat Service

Create `/etc/systemd/system/sdp-baccarat.service`:

```ini
[Unit]
Description=SDP Baccarat Game Service
After=network.target

[Service]
Type=simple
User=rnd
WorkingDirectory=/home/rnd
ExecStart=/home/rnd/sdp-env/bin/python /home/rnd/sdp-baccarat.pyz
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Service Management

### Enable and Start Service

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable sdp-sicbo

# Start service
sudo systemctl start sdp-sicbo

# Check status
sudo systemctl status sdp-sicbo
```

### Stop and Disable Service

```bash
# Stop service
sudo systemctl stop sdp-sicbo

# Disable service (don't start on boot)
sudo systemctl disable sdp-sicbo
```

### Restart Service

```bash
# Restart service
sudo systemctl restart sdp-sicbo

# Reload configuration (if service supports it)
sudo systemctl reload sdp-sicbo
```

## Logging

### View Logs

```bash
# View recent logs
sudo journalctl -u sdp-sicbo

# Follow logs (like tail -f)
sudo journalctl -u sdp-sicbo -f

# View logs since boot
sudo journalctl -u sdp-sicbo -b

# View logs for specific time range
sudo journalctl -u sdp-sicbo --since "2025-11-20 10:00:00" --until "2025-11-20 11:00:00"
```

### Log Rotation

Systemd automatically manages log rotation. To configure:

```bash
# Edit journald configuration
sudo nano /etc/systemd/journald.conf

# Set maximum log size
SystemMaxUse=500M
SystemKeepFree=1G
```

## Resource Limits

### CPU and Memory Limits

Add to service file:

```ini
[Service]
# CPU limit (percentage)
CPUQuota=50%

# Memory limit
MemoryLimit=1G

# Restart on OOM
OOMScoreAdjust=-1000
```

### Process Limits

```ini
[Service]
# Maximum number of open files
LimitNOFILE=65536

# Maximum number of processes
LimitNPROC=4096
```

## Environment Variables

### Service-Level Environment

```ini
[Service]
Environment="MQTT_BROKER=192.168.88.54"
Environment="MQTT_PORT=1883"
Environment="LOG_LEVEL=INFO"
Environment="LOG_DIR=/var/log/sdp"
```

### Environment File

Create `/etc/systemd/system/sdp-sicbo.service.d/env.conf`:

```ini
[Service]
EnvironmentFile=/etc/sdp/sdp-sicbo.env
```

Create `/etc/sdp/sdp-sicbo.env`:

```bash
MQTT_BROKER=192.168.88.54
MQTT_PORT=1883
LOG_LEVEL=INFO
LOG_DIR=/var/log/sdp
```

## Security

### User and Group

```ini
[Service]
User=rnd
Group=rnd

# Drop privileges
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/sdp
```

### Network Access

```ini
[Service]
# Restrict network access (if needed)
PrivateNetwork=false

# Allow specific network interfaces
BindReadOnlyPaths=/sys /proc
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status sdp-sicbo

# Check logs for errors
sudo journalctl -u sdp-sicbo -n 50

# Check if executable exists
ls -la /home/rnd/sdp-sicbo.pyz

# Test executable manually
/home/rnd/sdp-env/bin/python /home/rnd/sdp-sicbo.pyz --help
```

### Service Keeps Restarting

```bash
# Check restart count
systemctl status sdp-sicbo | grep "Active:"

# View recent errors
sudo journalctl -u sdp-sicbo -p err -n 20

# Check resource limits
systemctl show sdp-sicbo | grep -i limit
```

### Permission Issues

```bash
# Check file permissions
ls -la /home/rnd/sdp-sicbo.pyz

# Check user permissions
id rnd

# Check log directory permissions
ls -ld /var/log/sdp
```

## Best Practices

1. **Use Non-Root User**: Always run services as non-root user
2. **Set Resource Limits**: Prevent resource exhaustion
3. **Enable Logging**: Use systemd journal for centralized logging
4. **Configure Restart**: Set appropriate restart policy
5. **Test Before Enabling**: Test service before enabling on boot

## Related Documentation

- [Standalone Deployment](standalone.md) - Standalone executable deployment
- [Docker Deployment](docker.md) - Docker container deployment
- [Deployment Overview](overview.md) - General deployment guide

