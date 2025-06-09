#!/bin/bash
# NetScout-Pi - Run Development Server

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root (sudo)."
  exit 1
fi

# Make sure environment is set up
if [ ! -d "/var/log/netprobe" ] || [ ! -d "/var/lib/netprobe" ] || [ ! -d "/etc/netprobe" ]; then
  echo "Setting up environment first..."
  bash scripts/setup_environment.sh
fi

# Run the app in development mode
python3 app.py --debug "$@"
