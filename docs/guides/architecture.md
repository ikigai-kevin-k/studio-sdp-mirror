# System Architecture

This document describes the architecture of the Studio SDP System.

## Overview

The Studio SDP System follows a hierarchical state machine pattern with modular components for different game types.

## System Components

### Main Components

1. **Game Controllers** - Manage individual game logic
2. **State Machine** - Controls system state transitions
3. **Communication Modules** - Handle MQTT, Serial, WebSocket communication
4. **API Integration** - Integrate with LOS and Studio APIs
5. **Logging System** - Comprehensive logging and monitoring

## State Machine

### Main Program States

- **INITIALIZING**: Load configuration, setup logging, create controllers
- **RUNNING**: Game controllers active, processing game rounds
- **ERROR**: Error handling and retry mechanisms
- **STOPPING**: Graceful shutdown process
- **STOPPED**: System stopped and cleaned up

### State Transitions

```
INITIALIZING → RUNNING → ERROR → RUNNING
RUNNING → STOPPING → STOPPED
ERROR → STOPPING → STOPPED
```

## Game Controllers

### Roulette Controller

- RS232 serial communication
- Wheel speed and position monitoring
- Live Backend Service API integration

### SicBo Controller

- MQTT protocol for dice shaker control
- IDP integration for dice detection
- Real-time result processing

### Baccarat Controller

- HID barcode scanner integration
- Card detection and validation
- Game state management

## Communication Protocols

### RS232 (Roulette)

- Serial port communication
- Signal processing
- Real-time monitoring

### MQTT (SicBo)

- Message queue protocol
- Failover support
- Device status monitoring

### WebSocket (Live Backend Service integration)

- Real-time communication
- Status updates
- Authentication

### HID (Baccarat)

- Barcode scanning
- Card detection
- Game state management

## Related Documentation

- [MQTT System Guide](mqtt-system.md)
- [State Machine Guide](state-machine.md)
- [Game Controllers Guide](game-controllers.md)

