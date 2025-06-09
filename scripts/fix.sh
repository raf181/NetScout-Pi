#!/bin/bash
# NetScout-Pi - Fix Script
# This script runs the unified installer with the fix parameter

# Just call the unified installer with fix parameter
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
INSTALLER_PATH="$SCRIPT_DIR/unified_installer.sh"

# If the unified installer exists locally, use it
if [ -f "$INSTALLER_PATH" ]; then
    sudo bash "$INSTALLER_PATH" fix
else
    # Otherwise download and run it
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    echo "Downloading NetScout-Pi unified installer script..."
    wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/unified_installer.sh -O unified_installer.sh
    chmod +x unified_installer.sh
    
    echo "Running unified installer in fix mode..."
    sudo bash unified_installer.sh fix
    
    # Clean up
    cd /tmp
    rm -rf "$TMP_DIR"
fi
