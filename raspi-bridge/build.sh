#!/bin/bash
# build.sh — Build the raspi-bridge Debian package
#
# Usage: bash build.sh
# Output: raspi-bridge_1.0.0_all.deb in the current directory

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_DIR="${SCRIPT_DIR}/raspi-bridge"

# If this script is inside the raspi-bridge directory, use parent
if [ "$(basename "$SCRIPT_DIR")" == "raspi-bridge" ]; then
    PACKAGE_DIR="$SCRIPT_DIR"
    SCRIPT_DIR="$(dirname "$SCRIPT_DIR")"
fi

echo "Building raspi-bridge package..."

# Ensure correct permissions for scripts
chmod 755 "${PACKAGE_DIR}/DEBIAN/postinst"
chmod 755 "${PACKAGE_DIR}/DEBIAN/prerm"
chmod 755 "${PACKAGE_DIR}/usr/bin/raspi-bridge-setup"
chmod 755 "${PACKAGE_DIR}/usr/lib/raspi-bridge/iptables-rules.sh"

# Build the .deb
dpkg-deb --build "${PACKAGE_DIR}" "${SCRIPT_DIR}/raspi-bridge_1.0.0_all.deb"

echo ""
echo "✓ Package built: ${SCRIPT_DIR}/raspi-bridge_1.0.0_all.deb"
echo ""
echo "Install with: sudo dpkg -i raspi-bridge_1.0.0_all.deb"
echo "Then run:     sudo raspi-bridge-setup"
