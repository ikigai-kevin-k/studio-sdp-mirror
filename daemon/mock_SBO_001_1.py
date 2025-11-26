#!/usr/bin/env python3
"""
Mock SBO 001 Service Daemon
This script simulates a system daemon that starts automatically on boot
"""

import time
import logging
import signal
import sys
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/mock_sbo_001.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("MockSBO001")


class MockSBODaemon:
    def __init__(self):
        self.running = False
        self.pid_file = "/var/run/mock_sbo_001.pid"

    def MockGetDeviceInfo(self):
        """Mock function to enumerate device status"""
        logger.info("=== MockGetDeviceInfo() - Enumerating device status ===")

        # Mock device enumeration
        devices = {
            "idp": "UP",
            "broker": "UP",
            "shaker": "UP",
            "nfcScanner": "UP",
        }

        # Log device status
        for device_name, status in devices.items():
            logger.info(f"Device {device_name}: {status}")

        logger.info("All devices are UP and ready")
        return devices

    def MockSendWsMsgToStudioAPI(self, device_info):
        """Mock function to send WebSocket message to StudioAPI"""
        logger.info(
            "=== MockSendWsMsgToStudioAPI() - Sending message to StudioAPI ==="
        )

        # Mock WebSocket message
        message = {
            "type": "device_status_update",
            "timestamp": datetime.now().isoformat(),
            "devices": device_info,
            "status": "all_devices_up",
            "message": "All devices are UP and operational",
        }

        # Log the message that would be sent
        logger.info(f"WebSocket message to StudioAPI: {message}")
        logger.info("Mock: Message sent successfully to StudioAPI")

        return True

    def signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def write_pid_file(self):
        """Write PID to file for system service management"""
        try:
            with open(self.pid_file, "w") as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.error(f"Failed to write PID file: {e}")

    def remove_pid_file(self):
        """Remove PID file on shutdown"""
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
        except Exception as e:
            logger.error(f"Failed to remove PID file: {e}")

    def daemonize(self):
        """Daemonize the process"""
        try:
            # Fork first time
            pid = os.fork()
            if pid > 0:
                sys.exit(0)

            # Decouple from parent environment
            os.chdir("/")
            os.umask(0)
            os.setsid()

            # Fork second time
            pid = os.fork()
            if pid > 0:
                sys.exit(0)

            # Redirect standard file descriptors
            sys.stdout.flush()
            sys.stderr.flush()

            with open("/dev/null", "r") as f:
                os.dup2(f.fileno(), sys.stdin.fileno())
            with open("/dev/null", "a+") as f:
                os.dup2(f.fileno(), sys.stdout.fileno())
            with open("/dev/null", "a+") as f:
                os.dup2(f.fileno(), sys.stderr.fileno())

        except Exception as e:
            logger.error(f"Failed to daemonize: {e}")
            sys.exit(1)

    def run(self):
        """Main daemon loop"""
        logger.info("Mock SBO 001 daemon starting...")

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

        # Write PID file
        self.write_pid_file()

        # Execute device enumeration and notification on startup
        logger.info("=== Starting device enumeration and notification ===")
        try:
            # Get device information
            device_info = self.MockGetDeviceInfo()

            # Send WebSocket message to StudioAPI
            self.MockSendWsMsgToStudioAPI(device_info)

            logger.info(
                "=== Device enumeration and notification completed ==="
            )
        except Exception as e:
            logger.error(f"Error during device enumeration: {e}")

        self.running = True
        counter = 0

        while self.running:
            try:
                counter += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(
                    f"Mock SBO 001 daemon running - Counter: {counter}, "
                    f"Time: {current_time}"
                )

                # Simulate some work
                time.sleep(10)  # Sleep for 10 seconds

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)

        logger.info("Mock SBO 001 daemon shutting down...")
        self.remove_pid_file()
        logger.info("Mock SBO 001 daemon stopped")


def main():
    """Main entry point"""
    daemon = MockSBODaemon()

    if len(sys.argv) > 1:
        if sys.argv[1] == "start":
            daemon.daemonize()
            daemon.run()
        elif sys.argv[1] == "run":
            # Run in foreground for debugging
            daemon.run()
        elif sys.argv[1] == "stop":
            # Stop the daemon
            try:
                with open("/var/run/mock_sbo_001.pid", "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to process {pid}")
            except Exception as e:
                print(f"Failed to stop daemon: {e}")
        else:
            print("Usage: python3 mock_SBO_001_1.py [start|run|stop]")
    else:
        print("Usage: python3 mock_SBO_001_1.py [start|run|stop]")


if __name__ == "__main__":
    main()
