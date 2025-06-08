#!/bin/bash
# NetProbe Pi - One-line installer

# Create temporary directory
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "Downloading NetProbe Pi setup script..."
wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/setup.sh -O setup.sh
chmod +x setup.sh

echo "Running setup script..."
sudo bash setup.sh

# Clean up
cd /tmp
rm -rf "$TMP_DIR"
