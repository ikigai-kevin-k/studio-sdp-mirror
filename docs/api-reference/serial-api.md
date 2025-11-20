# Serial API Reference

Complete serial communication API documentation.

## Serial Port

### Opening Port

```python
import serial

ser = serial.Serial(
    port="/dev/ttyUSB0",
    baudrate=9600,
    timeout=1.0,
    rtscts=True
)
```

### Reading Data

```python
if ser.in_waiting > 0:
    data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
```

### Writing Data

```python
ser.write(command.encode('utf-8'))
```

## Related Documentation

- [Serial Communication Guide](../guides/serial-communication.md)

