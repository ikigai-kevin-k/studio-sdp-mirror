# Game Controllers Guide

This guide explains the game controllers in the Studio SDP System.

## Overview

Each game type has its own controller that manages game-specific logic and hardware communication.

## Roulette Controllers

### Speed Roulette

- **Controller**: `RealRouletteController`
- **Communication**: RS232 serial
- **Hardware**: Roulette wheel
- **Features**: Speed control, position detection, result processing

### VIP Roulette

- **Controller**: `RealRouletteController`
- **Communication**: RS232 serial
- **Hardware**: Roulette wheel
- **Features**: VIP-specific game logic

## SicBo Controller

- **Controller**: `DiceShakerController`
- **Communication**: MQTT
- **Hardware**: Dice shaker, IDP
- **Features**: Shake control, dice detection, result validation

## Baccarat Controller

- **Controller**: `BaccaratController`
- **Communication**: HID barcode scanner
- **Hardware**: Barcode scanner, IDP (optional)
- **Features**: Card detection, dealing order validation

## Controller Interface

All controllers implement a common interface:

```python
class Controller:
    async def start(self):
        """Start the controller"""
        pass
    
    async def stop(self):
        """Stop the controller"""
        pass
    
    async def cleanup(self):
        """Cleanup resources"""
        pass
```

## Related Documentation

- [Architecture Guide](architecture.md)
- [State Machine Guide](state-machine.md)
- [Serial Communication Guide](serial-communication.md)

