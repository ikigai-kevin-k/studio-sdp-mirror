# Common Issues

This guide covers common issues and their solutions.

## Installation Issues

### Python Version Mismatch

**Problem**: Wrong Python version

**Solution**:
```bash
python --version  # Should be 3.12.x
pyenv install 3.12.0
pyenv local 3.12.0
```

### Missing Dependencies

**Problem**: Import errors

**Solution**:
```bash
pip install -r requirements.txt --force-reinstall
```

## Runtime Issues

### Serial Port Access

**Problem**: Permission denied

**Solution**:
```bash
sudo usermod -a -G dialout $USER
```

### MQTT Connection Failed

**Problem**: Cannot connect to MQTT broker

**Solution**:
- Check broker address and port
- Verify network connectivity
- Check firewall settings

## Related Documentation

- [Debugging Guide](debugging.md)
- [FAQ](faq.md)

