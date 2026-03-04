#!/bin/bash
# install-service.sh — Install and enable the bridge-monitor logging service
#
# Usage: sudo bash install-service.sh

set -e

echo "Installing bridge-monitor logging service..."

# Install the Python package
pip3 install . || pip install .

# Create config directory and copy default config
mkdir -p /etc/bridge-monitor
if [ ! -f /etc/bridge-monitor/config.json ]; then
    cp config.json /etc/bridge-monitor/config.json
    echo "  ✓ Default config installed to /etc/bridge-monitor/config.json"
else
    echo "  ℹ Config already exists at /etc/bridge-monitor/config.json (not overwritten)"
fi

# Create log directory
mkdir -p /var/log/bridge-monitor
echo "  ✓ Log directory created at /var/log/bridge-monitor/"

# Install systemd service
cp bridge-monitor-logger.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable bridge-monitor-logger.service
systemctl start bridge-monitor-logger.service

echo ""
echo "✓ Service installed and started!"
echo ""
echo "  Useful commands:"
echo "    sudo systemctl status bridge-monitor-logger   # Check status"
echo "    sudo journalctl -u bridge-monitor-logger -f   # View live logs"
echo "    sudo systemctl restart bridge-monitor-logger   # Restart"
echo "    bridge-monitor                                 # Launch dashboard"
echo "    bridge-monitor config                          # View config"
echo ""
echo "  Edit config: sudo nano /etc/bridge-monitor/config.json"
echo "  Then restart: sudo systemctl restart bridge-monitor-logger"
