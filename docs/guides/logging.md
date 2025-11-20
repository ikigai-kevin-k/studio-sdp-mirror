# Logging Guide

This guide explains the logging system.

## Overview

The system provides comprehensive logging for debugging and monitoring.

## Log Levels

- **DEBUG**: Detailed debug information
- **INFO**: General informational messages
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical error messages

## Log Directory Structure

```
logs/
├── sicbo/
│   ├── sicbo_2025-01-13.log
│   └── sicbo_errors_2025-01-13.log
├── speed/
│   ├── speed_2025-01-13.log
│   └── speed_errors_2025-01-13.log
└── vip/
    ├── vip_2025-01-13.log
    └── vip_errors_2025-01-13.log
```

## Usage

### Basic Logging

```python
from logger import log_to_file, get_timestamp

log_to_file("Message", "INFO")
```

### Error Logging

```python
log_to_file(f"Error: {error}", "ERROR >>>")
```

## Related Documentation

- [Configuration Guide](../getting-started/configuration.md)
- [Troubleshooting Guide](../troubleshooting/debugging.md)

