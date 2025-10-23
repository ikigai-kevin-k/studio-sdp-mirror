# Use Ubuntu 24.04 as base image for systemd support
FROM ubuntu:24.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    systemd \
    systemd-sysv \
    dbus \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for running the service
RUN useradd -r -s /bin/bash -m -d /home/daemon daemon

# Create necessary directories
RUN mkdir -p /var/log /var/run /etc/systemd/system

# Copy the daemon script
COPY mock_SBO_001_1.py /usr/local/bin/
RUN chmod +x /usr/local/bin/mock_SBO_001_1.py

# Create systemd service file
RUN cat > /etc/systemd/system/mock-sbo-001.service << 'EOF'
[Unit]
Description=Mock SBO 001 Service Daemon
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/mock_SBO_001_1.py start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable the service
RUN systemctl enable mock-sbo-001.service

# Create startup script
RUN cat > /startup.sh << 'EOF'
#!/bin/bash
# Start systemd
exec /lib/systemd/systemd --system --show-status=false
EOF

RUN chmod +x /startup.sh

# Expose port if needed (optional)
# EXPOSE 8080

# Set the startup script as entrypoint
ENTRYPOINT ["/startup.sh"]
