# Mock SBO 001 Daemon Container

This project creates a Docker container to simulate a system daemon service, allowing `mock_SBO_001_1.py` to automatically start as a system service.

## Features

- **System Daemon**: Uses systemd to manage service lifecycle
- **Auto-start**: Automatically starts the daemon service when the container boots
- **Device Enumeration**: Automatically enumerates idp, broker, shaker, nfcScanner device status on startup
- **StudioAPI Notification**: Automatically sends WebSocket messages to StudioAPI on startup
- **Logging**: Complete logging and monitoring
- **Health Check**: Built-in health check mechanism
- **Easy Management**: Provides simple scripts for service management

## File Structure

```
daemon/
├── mock_SBO_001_1.py      # Python daemon script
├── Dockerfile             # Docker image definition (using systemd)
├── docker-compose.yml     # Docker Compose configuration (using systemd)
├── start-daemon.sh        # Startup and management script
├── test-boot-autostart.sh # Boot auto-start test script (systemd version)
├── Dockerfile.simple      # Simplified Docker image definition
├── docker-compose.simple.yml # Simplified Docker Compose configuration
├── test-simple-daemon.sh  # Simplified boot auto-start test script
├── README.md              # Documentation
├── logs/                  # Log directory (auto-created)
└── run/                   # PID file directory (auto-created)
```

## Prerequisites

- Docker
- Docker Compose
- Linux system (supports systemd)

## Quick Start

### 1. Start the Daemon

```bash
# Grant execution permissions
chmod +x start-daemon.sh

# Start the daemon
./start-daemon.sh start
```

### 2. View Startup Logs

After startup, you can see the device enumeration and StudioAPI notification process in the logs:

```bash
# View container logs
docker logs kevin-sdp-daemon

# View daemon logs
docker exec kevin-sdp-daemon tail -f /var/log/mock_sbo_001.log
```

### 3. Test Boot Auto-start Functionality

#### Method A: Use Simplified Version (Recommended)

```bash
# Grant test script execution permissions
chmod +x test-simple-daemon.sh

# Execute simplified boot auto-start test
./test-simple-daemon.sh
```

#### Method B: Use systemd Version

```bash
# Grant test script execution permissions
chmod +x test-boot-autostart.sh

# Execute complete boot auto-start test
./test-boot-autostart.sh
```

### 4. Check Status

```bash
./start-daemon.sh status
```

### 5. View Logs

```bash
./start-daemon.sh logs
```

### 6. Stop Service

```bash
./start-daemon.sh stop
```

## Script Commands

### Main Management Script (`start-daemon.sh`)

| Command | Description |
|---------|-------------|
| `start` | Start the daemon container |
| `stop` | Stop the daemon container |
| `restart` | Restart the daemon container |
| `status` | Check daemon status |
| `logs` | View daemon logs |
| `help` | Show help message |

### Test Scripts

#### Simplified Version (`test-simple-daemon.sh`) - Recommended

Executes simplified boot auto-start tests, including the following test items:

1. **Initial Container Startup Test**: Tests if the daemon starts automatically when the container first boots
2. **Container Restart Test**: Tests if the daemon starts automatically after container restart
3. **Log Verification Test**: Verifies logging functionality

**Advantages**: More stable, faster, easier to debug

#### systemd Version (`test-boot-autostart.sh`)

Executes complete boot auto-start tests, including the following test items:

1. **Initial Container Startup Test**: Tests if the service starts automatically when the container first boots
2. **Container Restart Test**: Tests if the service starts automatically after container restart
3. **Service Restart Test**: Tests service restart functionality
4. **Boot Sequence Verification**: Verifies systemd boot sequence configuration
5. **Log Verification Test**: Verifies logging functionality

**Note**: May be unstable in some environments

## Manual Operations

### Using Docker Compose

```bash
# Build and start container
docker compose up -d --build

# View logs
docker compose logs -f

# Stop container
docker compose down
```

### Direct Docker Usage

```bash
# Build image
docker build -t mock-sbo-daemon .

# Start container
docker run -d --name kevin-sdp-daemon \
  --privileged \
  --network host \
  -v $(pwd)/logs:/var/log \
  -v $(pwd)/run:/var/run \
  -v /sys/fs/cgroup:/sys/fs/cgroup:ro \
  mock-sbo-daemon

# Check service status
docker exec kevin-sdp-daemon systemctl status mock-sbo-001.service
```

## Core Features

### Device Enumeration (MockGetDeviceInfo)

The daemon automatically executes device enumeration functionality on startup:

- **idp**: Device status check
- **broker**: Device status check  
- **shaker**: Device status check
- **nfcScanner**: Device status check

All device statuses are logged and a device status dictionary is returned.

### StudioAPI Notification (MockSendWsMsgToStudioAPI)

After device enumeration is complete, it automatically sends WebSocket messages to StudioAPI:

```json
{
  "type": "device_status_update",
  "timestamp": "2025-08-26T07:48:21.488118",
  "devices": {
    "idp": "UP",
    "broker": "UP", 
    "shaker": "UP",
    "nfcScanner": "UP"
  },
  "status": "all_devices_up",
  "message": "All devices are UP and operational"
}
```

### Startup Process

1. Daemon starts
2. Execute device enumeration (MockGetDeviceInfo)
3. Send StudioAPI notification (MockSendWsMsgToStudioAPI)
4. Begin normal daemon loop

## Service Configuration

### systemd Service File

The service file is located at `/etc/systemd/system/mock-sbo-001.service` inside the container:

```ini
[Unit]
Description=Mock SBO 001 Service Daemon
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/mock_SBO_001_1.py start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Environment Variables

- `PYTHONUNBUFFERED=1`: Ensures Python output is not buffered
- `DEBIAN_FRONTEND=noninteractive`: Avoids interactive prompts during installation

## Monitoring and Logging

### Log Locations

- **Inside container**: `/var/log/mock_sbo_001.log`
- **On host**: `./logs/mock_sbo_001.log`

### Health Check

The container includes a health check mechanism that checks service status every 30 seconds:

```yaml
healthcheck:
  test: ["CMD", "systemctl", "is-active", "mock-sbo-001.service"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## Troubleshooting

### Common Issues

1. **Container cannot start**
   - Check if Docker is running
   - Confirm sufficient permissions to run privileged containers

2. **Service cannot start**
   - Check container logs: `docker-compose logs`
   - Confirm Python script has execution permissions

3. **Permission issues**
   - Ensure `--privileged` flag is used
   - Check cgroup mount points

### Debug Mode

```bash
# Run container in foreground mode
docker run -it --rm --privileged \
  --network host \
  -v $(pwd)/logs:/var/log \
  -v $(pwd)/run:/var/run \
  -v /sys/fs/cgroup:/sys/fs/cgroup:ro \
  mock-sbo-daemon

# Manually start service inside container
systemctl start mock-sbo-001.service
systemctl status mock-sbo-001.service
```

## Custom Configuration

### Modify Service Configuration

Edit the service file section in `Dockerfile` to modify service behavior:

```dockerfile
RUN cat > /etc/systemd/system/mock-sbo-001.service << 'EOF'
[Unit]
Description=Custom Service Description
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/mock_SBO_001_1.py start
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

### Add Environment Variables

Add environment variables in `docker-compose.yml`:

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - CUSTOM_VAR=value
  - DEBUG_MODE=true
```

## Security Considerations

- Container runs in `--privileged` mode with complete system permissions
- Service runs as root user
- Recommend limiting permissions and network access in production environments

