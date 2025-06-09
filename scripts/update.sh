#!/bin/bash
# NetScout-Pi - Auto Update Script
# This script checks for updates and applies them automatically

# Just call the unified installer with update parameter
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
INSTALLER_PATH="$SCRIPT_DIR/unified_installer.sh"

# If the unified installer exists locally, use it
if [ -f "$INSTALLER_PATH" ]; then
    sudo bash "$INSTALLER_PATH" update
else
    # Otherwise download and run it
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    echo "Downloading NetScout-Pi unified installer script..."
    wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/unified_installer.sh -O unified_installer.sh
    chmod +x unified_installer.sh
    
    echo "Running unified installer in update mode..."
    sudo bash unified_installer.sh update
    
    # Clean up
    cd /tmp
    rm -rf "$TMP_DIR"
fi
