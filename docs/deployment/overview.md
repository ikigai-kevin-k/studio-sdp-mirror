# Deployment Overview

This guide covers deployment options for the Studio SDP System.

## Deployment Options

The system supports multiple deployment methods:

1. **Standalone Executables** - Using Shiv to create `.pyz` files
2. **Docker Containers** - Containerized deployment with systemd
3. **Systemd Services** - Native Linux service deployment
4. **Manual Deployment** - Direct Python script execution

## Quick Reference

### Standalone Executables

```bash
# Build executable
shiv --compressed --compile-pyc \
     --python "/home/rnd/sdp-env/bin/python" \
     --output-file sdp-sicbo.pyz \
     --entry-point main_sicbo:main .

# Run executable
./sdp-sicbo.pyz --help
```

### Docker Deployment

```bash
cd daemon
docker-compose up -d
```

### Systemd Service

```bash
sudo systemctl enable sdp-sicbo
sudo systemctl start sdp-sicbo
```

## Deployment Guides

- **[Standalone Deployment](standalone.md)** - Deploy using standalone executables
- **[Docker Deployment](docker.md)** - Deploy using Docker containers
- **[Systemd Deployment](systemd.md)** - Deploy as systemd services
- **[CI/CD Deployment](ci-cd.md)** - Automated deployment with GitHub Actions

## Environment-Specific Deployment

### Development

- Manual execution
- Local testing
- Debug mode enabled

### Staging

- Docker containers
- Automated testing
- Monitoring enabled

### Production

- Systemd services
- Standalone executables
- Full monitoring and logging

## Prerequisites

Before deployment, ensure:

1. **Python 3.12+** installed
2. **Virtual environment** created
3. **Dependencies** installed
4. **Configuration files** prepared
5. **Hardware** connected and tested

## Deployment Checklist

- [ ] Environment prepared
- [ ] Dependencies installed
- [ ] Configuration files updated
- [ ] Hardware tested
- [ ] Logging configured
- [ ] Monitoring enabled
- [ ] Backup strategy in place
- [ ] Rollback plan prepared

## Related Documentation

- [Installation Guide](../getting-started/installation.md)
- [Configuration Guide](../getting-started/configuration.md)
- [Troubleshooting Guide](../troubleshooting/common-issues.md)

