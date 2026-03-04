#!/bin/bash
# install-service.sh — Install and enable the bridge-monitor logging service
#
# Usage: sudo bash install-service.sh
#
# Installs bridge-monitor into a Python virtual environment at
# /opt/bridge-monitor/venv to comply with PEP 668 (externally-managed-environment).

set -e

INSTALL_DIR="/opt/bridge-monitor"
VENV_DIR="${INSTALL_DIR}/venv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing bridge-monitor logging service..."

# Ensure python3-venv is available
if ! dpkg -s python3-venv >/dev/null 2>&1; then
    echo "  Installing python3-venv..."
    apt-get update -qq && apt-get install -y python3-venv python3-full
fi

# Create install directory and virtual environment
echo "  Creating virtual environment at ${VENV_DIR}..."
mkdir -p "${INSTALL_DIR}"
python3 -m venv "${VENV_DIR}"

# Install bridge-monitor into the venv
echo "  Installing bridge-monitor into virtual environment..."
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install "${SCRIPT_DIR}"

# Create a system-wide symlink so `bridge-monitor` works from anywhere
ln -sf "${VENV_DIR}/bin/bridge-monitor" /usr/local/bin/bridge-monitor
echo "  ✓ Symlinked /usr/local/bin/bridge-monitor → ${VENV_DIR}/bin/bridge-monitor"

# Create config directory and copy default config
mkdir -p /etc/bridge-monitor
if [ ! -f /etc/bridge-monitor/config.json ]; then
    cp "${SCRIPT_DIR}/config.json" /etc/bridge-monitor/config.json
    echo "  ✓ Default config installed to /etc/bridge-monitor/config.json"
else
    echo "  ℹ Config already exists at /etc/bridge-monitor/config.json (not overwritten)"
fi

# Create log directory
mkdir -p /var/log/bridge-monitor
echo "  ✓ Log directory created at /var/log/bridge-monitor/"

# Update systemd service to use the venv Python
sed "s|ExecStart=.*|ExecStart=${VENV_DIR}/bin/bridge-monitor log|" \
    "${SCRIPT_DIR}/bridge-monitor-logger.service" > /etc/systemd/system/bridge-monitor-logger.service

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
