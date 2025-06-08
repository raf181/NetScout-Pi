#!/bin/bash
# NetProbe Pi - Direct Installer
# This script can be used with curl | bash for a one-line installation

# Exit on error
set -e

# Create temporary directory
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "NetProbe Pi - Direct Installer"
echo "============================="
echo "This will install NetProbe Pi on your system."
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Try 'sudo bash' before running this script."
    exit 1
fi

# Install basic requirements
echo "Installing basic requirements..."
apt-get update > /dev/null
apt-get install -y wget unzip python3 python3-pip > /dev/null

# Download the repository
echo "Downloading NetProbe Pi..."
wget -q https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip -O netscout.zip

# Extract files
echo "Extracting files..."
unzip -q netscout.zip
cd NetScout-Pi-main

# Run the installation script
echo "Running installation script..."
bash scripts/install.sh

# Clean up
cd /
rm -rf "$TMP_DIR"

echo "Installation completed!"
