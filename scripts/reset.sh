#!/bin/bash
# NetScout-Pi - Reset to Factory Defaults
# This script runs the unified installer with the reset parameter

# Just call the unified installer with reset parameter
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
INSTALLER_PATH="$SCRIPT_DIR/unified_installer.sh"

# If the unified installer exists locally, use it
if [ -f "$INSTALLER_PATH" ]; then
    sudo bash "$INSTALLER_PATH" reset
else
    # Otherwise download and run it
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    echo "Downloading NetScout-Pi unified installer script..."
    wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/unified_installer.sh -O unified_installer.sh
    chmod +x unified_installer.sh
    
    echo "Running unified installer in reset mode..."
    sudo bash unified_installer.sh reset
    
    # Clean up
    cd /tmp
    rm -rf "$TMP_DIR"
fi

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    log "This script must be run as root. Try 'sudo $0'"
    exit 1
fi

# Determine the user
if id "pi" &>/dev/null; then
    USER="pi"
    GROUP="pi"
else
    # Use current user (non-root) or the user who sudo'ed
    if [ -n "$SUDO_USER" ]; then
        USER="$SUDO_USER"
        GROUP="$SUDO_USER"
    else
        USER=$(whoami)
        GROUP=$(whoami)
    fi
    log "User 'pi' not found, using user '$USER' instead"
fi

# Prompt for confirmation
echo "WARNING: This will reset NetProbe Pi to factory defaults."
echo "All custom plugins, sequences, and settings will be lost."
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Reset cancelled by user"
    exit 0
fi

# Stop service
log "Stopping NetProbe service..."
systemctl stop $SERVICE_NAME

# Reset configuration
log "Resetting configuration..."
if [ -d "$CONFIG_DIR" ]; then
    rm -f $CONFIG_DIR/config.yaml
fi

# Reset logs
log "Resetting logs..."
find /var/log/netprobe -type f -name "*.log" -exec rm {} \;
find /var/log/netprobe -type f -name "*.json" -exec rm {} \;

# Reset plugins
log "Resetting custom plugins..."
PLUGINS_DIR="$INSTALL_DIR/src/plugins"
for plugin in $PLUGINS_DIR/*; do
    # Check if it's a built-in plugin
    filename=$(basename "$plugin")
    if [[ ! "$filename" =~ ^(ip_info|ping_test|arp_scan|traceroute|speed_test|port_scan|vlan_detector|packet_capture)\.py$ ]]; then
        if [ -f "$plugin" ]; then
            log "Removing custom plugin: $filename"
            rm "$plugin"
        fi
    fi
done

# Reset sequences
log "Resetting sequences..."
if [ -d "$INSTALL_DIR/sequences" ]; then
    rm -f $INSTALL_DIR/sequences/*.json
fi

# Reset first boot flag to trigger setup on next boot
log "Resetting first boot flag..."
rm -f $INSTALL_DIR/.first_boot_completed

# Start service
log "Starting NetProbe service..."
systemctl start $SERVICE_NAME

log "Reset to factory defaults completed"
echo "NetProbe Pi has been reset to factory defaults."
echo "The system will reboot in 5 seconds..."
sleep 5
reboot
