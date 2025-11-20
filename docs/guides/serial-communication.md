# Serial Communication Guide

This guide explains serial communication for Roulette games.

## Overview

Roulette games use RS232 serial communication to control the roulette wheel.

## Configuration

### Serial Port Settings

```python
{
  "port": "/dev/ttyUSB0",
  "baudrate": 9600,
  "bytesize": 8,
  "parity": "N",
  "stopbits": 1,
  "timeout": 1.0,
  "rtscts": true
}
```

## Usage

### Opening Serial Port

```python
import serial

ser = serial.Serial(
    port="/dev/ttyUSB0",
    baudrate=9600,
    timeout=1.0,
    rtscts=True
)
```

### Reading from Serial

```python
def read_from_serial(ser, callback_func):
    try:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            callback_func(data)
    except Exception as e:
        log_to_file(f"Serial read error: {e}", "ERROR >>>")
```

### Writing to Serial

```python
def write_to_serial(ser, command):
    try:
        ser.write(command.encode('utf-8'))
    except Exception as e:
        log_to_file(f"Serial write error: {e}", "ERROR >>>")
```

## Troubleshooting

### Permission Issues

```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
```

### Port Not Found

```bash
# List available serial ports
ls -la /dev/ttyUSB*

# Check port permissions
ls -la /dev/ttyUSB0
```

## Related Documentation

- [Game Controllers Guide](game-controllers.md)
- [Troubleshooting Guide](../troubleshooting/common-issues.md)

