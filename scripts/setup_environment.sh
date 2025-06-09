#!/bin/bash
# NetScout-Pi - Environment Setup Script
# This script creates necessary directories and sets appropriate permissions

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root (sudo)."
  exit 1
fi

# Configuration
LOG_DIR="/var/log/netprobe"
DATA_DIR="/var/lib/netprobe"
CONFIG_DIR="/etc/netprobe"
PLUGIN_DIR="$CONFIG_DIR/plugins"
CURRENT_USER=$(logname || echo "$SUDO_USER")

# Create directories if they don't exist
echo "Creating system directories..."
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$PLUGIN_DIR"

# Set permissions
echo "Setting permissions..."
if [ -n "$CURRENT_USER" ]; then
  echo "Granting ownership to user: $CURRENT_USER"
  chown -R "$CURRENT_USER:$CURRENT_USER" "$LOG_DIR" "$DATA_DIR" "$CONFIG_DIR"
  chmod -R 755 "$LOG_DIR" "$DATA_DIR" "$CONFIG_DIR"
else
  echo "Could not determine current user, setting directories to world-writable (less secure)"
  chmod -R 777 "$LOG_DIR" "$DATA_DIR" "$CONFIG_DIR"
fi

# Create default config if it doesn't exist
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
  echo "Creating default configuration file..."
  cat > "$CONFIG_DIR/config.yaml" << EOF
# NetScout-Pi Configuration
system:
  log_dir: $LOG_DIR
  data_dir: $DATA_DIR
  plugin_dir: $PLUGIN_DIR
  log_level: INFO
  debug: false

web:
  host: 0.0.0.0
  port: 8080
  auth_required: true

setup:
  completed: false
EOF
fi

echo "Environment setup complete!"
echo "Log directory: $LOG_DIR"
echo "Data directory: $DATA_DIR" 
echo "Configuration directory: $CONFIG_DIR"

echo "You can now run NetScout-Pi with: python3 app.py"
