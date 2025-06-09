#!/bin/bash
# NetScout-Pi - Quick Installer
# This script downloads and installs NetScout-Pi directly without using git

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Try 'sudo $0'"
    exit 1
fi

echo "NetScout-Pi - Quick Installer"
echo "============================"
echo "This script is deprecated. Using unified installer instead."
echo

# Create temporary directory
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "Downloading NetScout-Pi unified installer script..."
wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/unified_installer.sh -O unified_installer.sh
chmod +x unified_installer.sh

echo "Running unified installer script..."
bash unified_installer.sh

# Clean up
cd /tmp
rm -rf "$TMP_DIR"

# Install required packages
echo "Installing required packages..."
apt-get update
apt-get install -y wget unzip python3 python3-pip

# Create installation directory
INSTALL_DIR="/opt/netprobe"
mkdir -p "$INSTALL_DIR"
mkdir -p /var/log/netprobe

# Download the repository
echo "Downloading NetProbe Pi..."
wget -q https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip -O /tmp/netscout.zip

# Extract files
echo "Extracting files..."
unzip -q /tmp/netscout.zip -d /tmp
cp -r /tmp/NetScout-Pi-main/* "$INSTALL_DIR/"
rm -rf /tmp/NetScout-Pi-main /tmp/netscout.zip

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
    echo "User 'pi' not found, using user '$USER' instead"
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r "$INSTALL_DIR/requirements.txt"

# Set permissions
echo "Setting permissions..."
if getent passwd $USER > /dev/null && getent group $GROUP > /dev/null; then
    chown -R $USER:$GROUP "$INSTALL_DIR"
    chown -R $USER:$GROUP /var/log/netprobe
else
    echo "Warning: User $USER or group $GROUP not found, skipping permission setting"
fi
chmod +x "$INSTALL_DIR/scripts/"*.sh
chmod +x "$INSTALL_DIR/app.py"

# Create systemd service
echo "Creating systemd service..."
cat > /etc/systemd/system/netprobe.service << EOF
[Unit]
Description=NetProbe Pi Network Diagnostics System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create config
mkdir -p /etc/netprobe
if [ ! -f /etc/netprobe/config.yaml ]; then
    cat > /etc/netprobe/config.yaml << EOF
# NetProbe Pi - Default Configuration
network:
  interface: eth0
  poll_interval: 5
  auto_run_on_connect: true
  default_plugins:
    - ip_info
    - ping_test
  monitor_method: poll

security:
  allow_eth0_access: false
  ssh_keypair_gen: true

web:
  port: 80
  host: 0.0.0.0
  session_timeout: 3600
  auth_required: true

logging:
  directory: /var/log/netprobe
  level: INFO
  max_logs: 100
EOF
fi

# Enable and start service
echo "Enabling service..."
systemctl daemon-reload
systemctl enable netprobe
systemctl start netprobe

# Set up first boot script
cp "$INSTALL_DIR/scripts/first_boot.sh" /etc/netprobe/
chmod +x /etc/netprobe/first_boot.sh

# Success message
echo "============================================="
echo "NetProbe Pi has been successfully installed!"
echo "============================================="
echo "Access the web dashboard at:"
echo "- http://netprobe.local (after first boot)"
echo "- http://YOUR_IP_ADDRESS"
echo
echo "Default password will be set on first login"
echo "============================================="
