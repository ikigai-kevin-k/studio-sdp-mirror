# Installation Guide

This guide will help you install and set up the Studio SDP Roulette System.

## Prerequisites

### System Requirements

- **Operating System**: Linux (recommended), macOS, or Windows
- **Python**: Python 3.12 or higher
- **Hardware**: 
  - Roulette wheels (for Roulette games)
  - Dice shakers (for SicBo games)
  - Barcode scanners (for Baccarat games)

### Required Tools

- `git` - Version control
- `pip` - Python package manager
- `virtualenv` or `venv` - Python virtual environment

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/studio-sdp/studio-sdp-roulette.git
cd studio-sdp-roulette
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv ~/sdp-env

# Activate virtual environment
source ~/sdp-env/bin/activate
```

### 3. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

### 4. Verify Installation

```bash
# Check Python version
python --version  # Should be 3.12.x

# Verify installation
sdp-vip --help
sdp-speed --help
sdp-sicbo --help
sdp-baccarat --help
```

## Configuration

### Configuration Files

Configuration files are located in the `conf/` directory:

- `roulette_machine_speed.json` - Speed roulette configuration
- `roulette_machine_vip.json` - VIP roulette configuration
- `table-config-sicbo-v2.json` - SicBo game configuration
- `table-config-baccarat-v2.json` - Baccarat game configuration

### Environment Variables

Create a `.env` file in the project root for environment-specific settings:

```bash
# MQTT Configuration
MQTT_BROKER=192.168.88.54
MQTT_PORT=1883

# LOS API Configuration
LOS_API_URL=https://los-api-uat.sdp.com.tw/api/v2/sdp/config
LOS_API_TOKEN=YOUR_TOKEN

# Slack Configuration (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_BOT_TOKEN=xoxb-your-bot-token
```

## Development Setup

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

This installs additional development tools:
- `pytest` - Testing framework
- `black` - Code formatter
- `flake8` - Linter
- `mypy` - Type checker
- `shiv` - Packaging tool

### Verify Development Tools

```bash
# Check code formatter
black --version

# Check linter
flake8 --version

# Check type checker
mypy --version

# Check test framework
pytest --version
```

## Docker Setup (Optional)

### Using Docker Compose

```bash
cd daemon
docker-compose up -d
```

### Manual Docker Build

```bash
docker build -t studio-sdp-roulette .
docker run -d --name sdp-roulette studio-sdp-roulette
```

## Troubleshooting

### Common Issues

#### Python Version Mismatch

If you encounter Python version issues:

```bash
# Use pyenv to manage Python versions
pyenv install 3.12.0
pyenv local 3.12.0
```

#### Permission Errors

If you encounter permission errors:

```bash
# Use sudo (not recommended for development)
sudo pip install -r requirements.txt

# Or use user installation
pip install --user -r requirements.txt
```

#### Missing Dependencies

If dependencies fail to install:

```bash
# Upgrade pip
pip install --upgrade pip

# Clear pip cache
pip cache purge

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Serial Port Access

For serial communication, ensure your user has access to serial ports:

```bash
# Add user to dialout group (Linux)
sudo usermod -a -G dialout $USER

# Log out and log back in for changes to take effect
```

## Next Steps

After installation, you can:

1. **[Quick Start Guide](quick-start.md)** - Learn how to run your first game
2. **[Configuration Guide](configuration.md)** - Configure the system for your environment
3. **[Development Setup](../development/setup.md)** - Set up your development environment

## Support

If you encounter issues during installation:

1. Check the [Troubleshooting](../troubleshooting/common-issues.md) section
2. Review the [FAQ](../troubleshooting/faq.md)
3. Open an issue on [GitHub](https://github.com/studio-sdp/studio-sdp-roulette/issues)

