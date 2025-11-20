# Studio SDP Roulette System

Welcome to the comprehensive documentation for the **Studio SDP Roulette System** - a sophisticated gaming platform that manages multiple casino games through different communication protocols and hardware integrations.

## Overview

The Studio SDP Roulette System is a multi-game type casino control system that provides real-time control and management for:

- **Roulette (Speed & VIP)**: RS232-controlled roulette wheels with LOS integration
- **SicBo**: MQTT-controlled dice shakers with IDP (Image Detection Processor) integration
- **Baccarat**: HID barcode scanner integration for card detection and game management

## Key Features

- **Multi-Game Support**: Unified system for managing different casino games
- **Real-time Communication**: WebSocket and MQTT protocols for instant updates
- **Hardware Integration**: Support for RS232, MQTT, HID, and camera-based detection
- **LOS Integration**: Seamless integration with Live Operations System
- **State Machine Architecture**: Robust state management with error handling
- **Docker Support**: Containerized deployment options
- **Comprehensive Logging**: Detailed logging and monitoring capabilities
- **Auto-failover**: Automatic failover mechanisms for reliability

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/studio-sdp/studio-sdp-roulette.git
cd studio-sdp-roulette

# Create virtual environment
python3 -m venv ~/sdp-env
source ~/sdp-env/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### Running Games

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

## Documentation Structure

- **[Getting Started](getting-started/installation.md)**: Installation and setup instructions
- **[Guides](guides/architecture.md)**: Detailed guides on system architecture and components
- **[API Reference](api-reference/overview.md)**: Complete API documentation
- **[Deployment](deployment/overview.md)**: Deployment guides for different environments
- **[Development](development/setup.md)**: Development setup and contribution guidelines
- **[Troubleshooting](troubleshooting/common-issues.md)**: Common issues and solutions

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

#### Baccarat controller (HID + LOS Integration, WIP)
- Uses HID barcode scanner for card detection
- Manages game rounds and player turns
- Handles card validation and game rules
- Supports dealing order validation

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

## Requirements

- Python 3.12 or higher
- Linux system (recommended)
- Hardware devices (roulette wheels, dice shakers, barcode scanners)

## Support

For questions, issues, or contributions:

- **GitHub Issues**: [Report Issues](https://github.com/studio-sdp/studio-sdp-roulette/issues)
- **Documentation**: Browse the guides and API reference
- **Email**: kevin.k@ikigai.team

## License

This project is licensed under the MIT License.

---

**Last Updated**: 2025-11-20  
**Version**: 1.0.0

# Trigger deployment
