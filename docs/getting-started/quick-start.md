# Quick Start Guide

This guide will help you get started with the Studio SDP System quickly.

## Running Your First Game

### VIP Roulette

```bash
# Activate virtual environment
source ~/sdp-env/bin/activate

# Run VIP Roulette
sdp-vip
```

### Speed Roulette

```bash
sdp-speed
```

### SicBo

```bash
sdp-sicbo --broker 192.168.88.54 --port 1883
```

### Baccarat

```bash
sdp-baccarat
```

## Command Line Options

### Common Options

All games support these common options:

```bash
# Show help
sdp-vip --help

# Specify configuration file
sdp-speed --config conf/roulette_machine_speed.json

# Enable debug mode
sdp-sicbo --debug

# Set log level
sdp-baccarat --log-level DEBUG
```

### SicBo Specific Options

```bash
sdp-sicbo \
  --broker 192.168.88.54 \
  --port 1883 \
  --game-type sicbo \
  --enable-logging \
  --log-dir ./logs \
  --get-url https://live-backend-service-api-uat.sdp.com.tw/api/v2/sdp/config \
  --token YOUR_TOKEN \
  -r
```

### Baccarat Specific Options

```bash
# IDP development mode (no barcode scanning)
sdp-baccarat --idp-dev

# IDP-only development mode (no CIT API calls)
sdp-baccarat --idp-only-dev
```

## Basic Configuration

### MQTT Configuration

For SicBo games, configure MQTT broker:

```bash
sdp-sicbo --broker 192.168.88.54 --port 1883
```

### Live Backend Service API Configuration

Configure Live Backend Service API endpoint and token:

```bash
sdp-sicbo \
  --get-url https://live-backend-service-api-uat.sdp.com.tw/api/v2/sdp/config \
  --token YOUR_TOKEN
```

### Logging Configuration

Enable logging and specify log directory:

```bash
sdp-sicbo --enable-logging --log-dir ./logs
```

## Running as a Service

### Using systemd

Create a systemd service file:

```ini
[Unit]
Description=SDP SicBo Game Service
After=network.target

[Service]
Type=simple
User=rnd
WorkingDirectory=/home/rnd
ExecStart=/home/rnd/sdp-env/bin/python /home/rnd/sdp-sicbo.pyz --broker 192.168.88.54
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable sdp-sicbo
sudo systemctl start sdp-sicbo
sudo systemctl status sdp-sicbo
```

## Docker Deployment

### Using Docker Compose

```bash
cd daemon
docker-compose up -d
```

### View Logs

```bash
# Docker logs
docker-compose logs -f

# Service logs
docker exec kevin-sdp-daemon tail -f /var/log/mock_sbo_001.log
```

## Testing the Installation

### Verify Game Controllers

```bash
# Test VIP Roulette
sdp-vip --help

# Test Speed Roulette
sdp-speed --help

# Test SicBo
sdp-sicbo --help

# Test Baccarat
sdp-baccarat --help
```

### Run Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m "not slow"  # Skip slow tests
pytest -m integration # Integration tests only
pytest -m unit        # Unit tests only

# With coverage
pytest --cov=. --cov-report=html
```

## Next Steps

Now that you have the system running:

1. **[Configuration Guide](configuration.md)** - Learn about advanced configuration
2. **[Architecture Guide](../guides/architecture.md)** - Understand system architecture
3. **[API Reference](../api-reference/overview.md)** - Explore the API documentation
4. **[Deployment Guide](../deployment/overview.md)** - Deploy to production

## Common Tasks

### Check System Status

```bash
# Check game status
systemctl status sdp-sicbo

# View logs
journalctl -u sdp-sicbo -f
```

### Restart Service

```bash
sudo systemctl restart sdp-sicbo
```

### Stop Service

```bash
sudo systemctl stop sdp-sicbo
```

## Troubleshooting

If you encounter issues:

1. Check the [Common Issues](../troubleshooting/common-issues.md) guide
2. Review logs in `./logs` directory
3. Verify configuration files in `conf/` directory
4. Check hardware connections

## Support

For additional help:

- **Documentation**: Browse the full documentation
- **GitHub Issues**: [Report Issues](https://github.com/studio-sdp/studio-sdp-roulette/issues)
- **Email**: kevin.k@ikigai.team

