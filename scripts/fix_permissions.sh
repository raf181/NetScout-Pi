#!/bin/bash
# Fix permissions script for NetScout-Pi

# Create log directory if it doesn't exist
mkdir -p ~/logs/netprobe

# Create configuration directory if it doesn't exist
mkdir -p ~/.config/netprobe

# If using sudo, create system directories
if [ "$EUID" -eq 0 ]; then
  echo "Creating system directories with root permissions..."
  mkdir -p /var/log/netprobe
  chown -R $SUDO_USER:$SUDO_USER /var/log/netprobe
  
  mkdir -p /etc/netprobe
  chown -R $SUDO_USER:$SUDO_USER /etc/netprobe
else
  echo "Running without root privileges, using local directories instead."
  echo "For system-wide installation, run this script with sudo."
fi

echo "Configuration directories created."
echo "To use local log directory, run the application with:"
echo "python app.py --log-dir ~/logs/netprobe"
