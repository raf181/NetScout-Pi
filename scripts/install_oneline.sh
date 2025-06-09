#!/bin/bash
# NetScout-Pi - One-line installer 
# This script downloads and runs the unified installer script

# Create temporary directory
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "Downloading NetScout-Pi unified installer script..."
wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/unified_installer.sh -O unified_installer.sh
chmod +x unified_installer.sh

echo "Running unified installer script..."
sudo bash unified_installer.sh

# Clean up
cd /tmp
rm -rf "$TMP_DIR"
