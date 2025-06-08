#!/bin/bash
# NetProbe Pi - Auto Update Script

set -e

LOG_FILE="/var/log/netprobe/update.log"
INSTALL_DIR="/opt/netprobe"
REPO_URL="https://github.com/raf181/NetScout-Pi.git"
BACKUP_DIR="/opt/netprobe_backup"
SERVICE_NAME="netprobe"

# Create log directory
mkdir -p /var/log/netprobe

# Log function
log() {
    echo "$(date): $1" | tee -a $LOG_FILE
}

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

log "Starting NetProbe Pi update check"

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    log "This script must be run as root. Try 'sudo $0'"
    exit 1
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
log "Created temporary directory: $TEMP_DIR"

# Download repository as ZIP to avoid authentication issues
log "Downloading repository to check for updates..."
wget -q https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip -O $TEMP_DIR/netprobe.zip
unzip -q $TEMP_DIR/netprobe.zip -d $TEMP_DIR
mv $TEMP_DIR/NetScout-Pi-main/* $TEMP_DIR/
rm -rf $TEMP_DIR/NetScout-Pi-main $TEMP_DIR/netprobe.zip

# Get current version
CURRENT_VERSION=$(cat $INSTALL_DIR/VERSION 2>/dev/null || echo "0.0.0")
# Get remote version
REMOTE_VERSION=$(cat $TEMP_DIR/VERSION 2>/dev/null || echo "0.0.0")

log "Current version: $CURRENT_VERSION"
log "Remote version: $REMOTE_VERSION"

# Check if update is needed
if [ "$CURRENT_VERSION" == "$REMOTE_VERSION" ]; then
    log "No update needed. Exiting."
    rm -rf $TEMP_DIR
    exit 0
fi

log "Update available. Proceeding with update..."

# Backup current installation
log "Backing up current installation..."
mkdir -p $BACKUP_DIR
BACKUP_NAME="netprobe_backup_$(date +%Y%m%d_%H%M%S)"
cp -r $INSTALL_DIR $BACKUP_DIR/$BACKUP_NAME

# Stop service
log "Stopping NetProbe service..."
systemctl stop $SERVICE_NAME

# Update files
log "Updating files..."
rsync -av --exclude '.git' $TEMP_DIR/ $INSTALL_DIR/

# Update dependencies
log "Updating dependencies..."
pip3 install --upgrade -r $INSTALL_DIR/requirements.txt

# Fix permissions
log "Setting permissions..."
if getent passwd $USER > /dev/null && getent group $GROUP > /dev/null; then
    chown -R $USER:$GROUP $INSTALL_DIR
    log "Permissions set to $USER:$GROUP"
else
    log "Warning: User $USER or group $GROUP not found, skipping permission setting"
fi
chmod +x $INSTALL_DIR/scripts/*.sh
chmod +x $INSTALL_DIR/app.py

# Start service
log "Starting NetProbe service..."
systemctl start $SERVICE_NAME

# Clean up
log "Cleaning up..."
rm -rf $TEMP_DIR

log "Update completed successfully!"
exit 0
