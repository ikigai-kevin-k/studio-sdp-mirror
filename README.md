# Studio SDP Roulette System

A comprehensive gaming system that provides real-time control and management for multiple casino game types including Roulette, SicBo, and Baccarat. The system integrates with various hardware devices and external APIs to deliver seamless gaming experiences.

## Overview

The Studio SDP Roulette System is a sophisticated gaming platform that manages multiple casino games through different communication protocols and hardware integrations. It features a hierarchical state machine architecture that ensures reliable game flow control and error handling.

### Supported Games

- **Roulette (Speed & VIP)**: RS232-controlled roulette wheels with LOS integration
- **SicBo**: MQTT-controlled dice shakers with IDP (Image Detection Processor) integration
- **Baccarat**: HID barcode scanner integration for card detection and game management

## Features

- **Multi-Game Support**: Unified system for managing different casino games
- **Real-time Communication**: WebSocket and MQTT protocols for instant updates
- **Hardware Integration**: Support for RS232, MQTT, HID, and camera-based detection
- **LOS Integration**: Seamless integration with Live Operations System
- **State Machine Architecture**: Robust state management with error handling
- **Docker Support**: Containerized deployment options
- **Comprehensive Logging**: Detailed logging and monitoring capabilities
- **Auto-failover**: Automatic failover mechanisms for reliability

## System Architecture

The system follows a hierarchical state machine pattern with the following main components:

### Main Program State Machine
- **INITIALIZING**: Load configuration, setup logging, create controllers
- **RUNNING**: Game controllers active, processing game rounds
- **ERROR**: Error handling and retry mechanisms
- **STOPPING**: Graceful shutdown process
- **STOPPED**: System stopped and cleaned up

### Game Controllers

#### Roulette Controller (RS232 + LOS Integration)
- Manages roulette wheel via RS232 communication
- Controls game rounds and result detection
- Handles wheel speed and positioning
- Integrates with LOS API for round management

#### SicBo Controller (MQTT + IDP + LOS Integration)
- Controls dice shaker via MQTT protocol
- Uses IDP for dice detection and validation
- Manages shake patterns and result processing
- Real-time integration with LOS system

#### Baccarat Controller (HID + LOS Integration)
- Uses HID barcode scanner for card detection
- Manages game rounds and player turns
- Handles card validation and game rules
- Supports dealing order validation

## Installation

### Prerequisites

- Python 3.12 or higher
- Linux system (recommended)
- Hardware devices (roulette wheels, dice shakers, barcode scanners)

### Quick Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/studio-sdp/studio-sdp-roulette.git
   cd studio-sdp-roulette
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv ~/sdp-env
   source ~/sdp-env/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install the package**:
   ```bash
   pip install -e .
   ```

## Usage

### Running Individual Games

The system provides console scripts for each game type:

```bash
# VIP Roulette
sdp-vip

# Speed Roulette  
sdp-speed

# SicBo
sdp-sicbo

# Baccarat
sdp-baccarat
```

### Command Line Options

Each game supports various command line options:

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

### Configuration

Configuration files are located in the `conf/` directory:

- `roulette_machine_speed.json` - Speed roulette configuration
- `roulette_machine_vip.json` - VIP roulette configuration  
- `table-config-sicbo-v2.json` - SicBo game configuration
- `table-config-baccarat-v2.json` - Baccarat game configuration

## Development

### Project Structure

```
studio-sdp-roulette/
├── main_*.py              # Main game controllers
├── controller.py          # Core game controller logic
├── gameStateController.py # State machine implementation
├── mqttController.py      # MQTT communication handler
├── table_api/            # LOS API integrations
├── studio_api/           # WebSocket and HTTP APIs
├── mqtt/                 # MQTT device controllers
├── serial_comm/          # RS232 communication modules
├── proto/                # Protocol definitions
├── conf/                 # Configuration files
├── tests/                # Test suite
├── daemon/               # Docker deployment files
└── scripts/              # Utility scripts
```

### Running Tests

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

### Code Quality

The project uses several tools for code quality:

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Deployment

### Docker Deployment

The system supports Docker deployment with systemd integration:

```bash
# Build and start daemon
cd daemon
docker-compose up -d

# View logs
docker-compose logs -f

# Stop daemon
docker-compose down
```

### Standalone Executables

Create standalone executables using Shiv:

```bash
# Create executable for SicBo
shiv --compressed --compile-pyc \
     --python "/home/rnd/sdp-env/bin/python" \
     --output-file sdp-sicbo.pyz \
     --entry-point main_sicbo:main \
     .

# Run executable
./sdp-sicbo.pyz --help
```

### Production Deployment

1. **Prepare production environment**:
   ```bash
   python3 -m venv ~/sdp-env
   source ~/sdp-env/bin/activate
   pip install -r requirements.txt
   ```

2. **Deploy executables**:
   ```bash
   scp sdp-*.pyz user@production-server:~/
   ```

3. **Run as service**:
   ```bash
   # Using systemd
   sudo systemctl enable sdp-service
   sudo systemctl start sdp-service
   ```

## Communication Protocols

### RS232 (Roulette)
- Serial communication for roulette wheel control
- Signal processing for X2/X5 wheel position detection
- Real-time wheel speed and position monitoring

### MQTT (SicBo)
- Message queue protocol for dice shaker control
- Device status monitoring and control
- Failover and redundancy support

### WebSocket (LOS Integration)
- Real-time communication with Live Operations System
- Status updates and game state synchronization
- Authentication and session management

### HID (Baccarat)
- Human Interface Device for barcode scanning
- Card detection and validation
- Game state management

## API Integration

### LOS (Live Operations System)
The system integrates with LOS through REST APIs:

- `start_post`: Initiate new game round
- `deal_post`: Submit game results
- `finish_post`: Complete current round
- `pause_post`: Temporarily suspend game
- `resume_post`: Resume suspended game
- `visibility_post`: Control table visibility
- `cancel_post`: Cancel current round

### Studio API
WebSocket-based API for real-time communication:

- Device status updates
- Game state synchronization
- Error reporting and monitoring