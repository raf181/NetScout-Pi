#!/bin/bash
# NetProbe Pi - Installation Script

set -e

LOG_FILE="./install.log"
INSTALL_DIR="/opt/netprobe"
SERVICE_NAME="netprobe"

# Log function
log() {
    echo "$(date): $1" | tee -a $LOG_FILE
}

# Check if pi user exists, otherwise use current user
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

log "Starting NetProbe Pi installation"
log "Installation will use user: $USER"

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    log "This script must be run as root. Try 'sudo $0'"
    exit 1
fi

# Update system
log "Updating system..."
apt-get update
apt-get upgrade -y

# Install dependencies
log "Installing dependencies..."
apt-get install -y \
    python3 python3-pip python3-venv \
    git nmap tcpdump arp-scan speedtest-cli \
    ifplugd avahi-daemon iproute2 \
    build-essential libffi-dev libssl-dev \
    wget unzip curl python3-yaml python3-netifaces

# Create installation directory
log "Creating installation directory..."
mkdir -p $INSTALL_DIR
mkdir -p /var/log/netprobe
mkdir -p /var/lib/netprobe
mkdir -p /etc/netprobe/plugins

# Set up environment
log "Setting up environment..."
bash $INSTALL_DIR/scripts/setup_environment.sh

# Copy files to installation directory
log "Copying files to installation directory..."
cp -r ./* $INSTALL_DIR/

# Install Python dependencies
log "Installing Python dependencies..."
# First try to install with apt (for Debian-based systems)
log "Attempting to install Python packages with apt..."
apt-get install -y \
    python3-flask python3-socketio python3-dotenv python3-click python3-watchdog \
    python3-psutil python3-netifaces python3-yaml python3-jsonschema \
    python3-bcrypt python3-jwt python3-requests python3-paho-mqtt

# If apt installation fails for some packages, try pip with --break-system-packages
log "Installing remaining packages with pip..."
# Use --break-system-packages to override the externally managed environment
pip3 install --break-system-packages -r $INSTALL_DIR/requirements.txt

# Set permissions
log "Setting permissions..."
if getent passwd $USER > /dev/null && getent group $GROUP > /dev/null; then
    chown -R $USER:$GROUP $INSTALL_DIR
    chown -R $USER:$GROUP /var/log/netprobe
    log "Permissions set to $USER:$GROUP"
else
    log "Warning: User $USER or group $GROUP not found, skipping permission setting"
fi
chmod +x $INSTALL_DIR/scripts/*.sh
chmod +x $INSTALL_DIR/app.py

# Create systemd service
log "Creating systemd service..."
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
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

# Enable and start the service
log "Enabling and starting service..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

# Set up first boot script to run on next boot
log "Setting up first boot script..."
mkdir -p /etc/netprobe
cp $INSTALL_DIR/scripts/first_boot.sh /etc/netprobe/
chmod +x /etc/netprobe/first_boot.sh

# Add first boot script to rc.local
if [ -f /etc/rc.local ]; then
    sed -i '/exit 0/i\/etc/netprobe/first_boot.sh &' /etc/rc.local
else
    cat > /etc/rc.local << EOF
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# NetProbe Pi additions
/etc/netprobe/first_boot.sh &

exit 0
EOF
    chmod +x /etc/rc.local
fi

# Create config directory and default config
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

# Display installation summary
echo "============================================="
echo "NetProbe Pi Installation Summary"
echo "============================================="
echo "Installation directory: $INSTALL_DIR"
echo "Log directory: /var/log/netprobe"
echo "Service name: $SERVICE_NAME"
echo "User: $USER"
echo "Dashboard URL: http://netprobe.local"
echo "============================================="
echo "To check the service status, run: systemctl status $SERVICE_NAME"
echo "To view logs, run: journalctl -u $SERVICE_NAME"
echo "============================================="

# Final success message
log "NetProbe Pi has been successfully installed!"
log "The web interface is accessible at: http://netprobe.local"
log "Default password will be set on first login"

exit 0`
