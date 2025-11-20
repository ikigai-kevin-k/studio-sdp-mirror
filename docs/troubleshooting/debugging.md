# Debugging Guide

This guide explains debugging techniques.

## Enable Debug Logging

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG

# Or in code
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Common Debugging Tools

- **Logs**: Check log files in `logs/` directory
- **Systemd Journal**: `journalctl -u sdp-sicbo -f`
- **Python Debugger**: Use `pdb` or `ipdb`

## Related Documentation

- [Common Issues](common-issues.md)
- [FAQ](faq.md)

