#!/bin/bash
# NetProbe Pi - Enhanced Direct Installer
# This script can be used with curl | bash for a one-line installation

# Exit on error
set -e

# Create temporary directory
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "NetProbe Pi - Direct Installer"
echo "============================="
echo "This will install NetProbe Pi on your system."
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Try 'sudo bash' before running this script."
    exit 1
fi

# Install basic requirements
echo "Installing basic requirements..."
apt-get update > /dev/null
apt-get install -y wget unzip python3 python3-pip > /dev/null

# Download the repository
echo "Downloading NetProbe Pi..."
wget -q https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip -O netscout.zip

# Extract files
echo "Extracting files..."
unzip -q netscout.zip

# Create installation directory
echo "Creating installation directory..."
mkdir -p /opt/netprobe

# Move files to installation directory
echo "Moving files to installation directory..."
cp -r NetScout-Pi-main/* /opt/netprobe/

# Install Python dependencies with apt (safer approach)
echo "Installing Python dependencies..."
apt-get install -y \
    python3-flask python3-socketio python3-dotenv python3-click python3-watchdog \
    python3-psutil python3-netifaces python3-yaml python3-jsonschema \
    python3-bcrypt python3-jwt python3-requests python3-paho-mqtt

# Use pip with --break-system-packages for remaining dependencies
echo "Installing remaining Python dependencies..."
pip3 install --break-system-packages -r /opt/netprobe/requirements.txt

# Set correct permissions
echo "Setting permissions..."
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

if getent passwd $USER > /dev/null && getent group $GROUP > /dev/null; then
    chown -R $USER:$GROUP /opt/netprobe
    chown -R $USER:$GROUP /var/log/netprobe
    echo "Permissions set to $USER:$GROUP"
else
    echo "Warning: User $USER or group $GROUP not found, skipping permission setting"
fi

# Make scripts executable
chmod +x /opt/netprobe/scripts/*.sh
chmod +x /opt/netprobe/app.py

# Setup systemd service
echo "Setting up system service..."
cat > /etc/systemd/system/netprobe.service << EOF
[Unit]
Description=NetProbe Pi Network Diagnostics System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/netprobe
ExecStart=/usr/bin/python3 /opt/netprobe/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
echo "Enabling and starting service..."
systemctl daemon-reload
systemctl enable netprobe
systemctl start netprobe

# Set up first boot
mkdir -p /etc/netprobe
cp /opt/netprobe/scripts/first_boot.sh /etc/netprobe/
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

# Clean up
cd /
rm -rf "$TMP_DIR"

echo "Installation completed!"
echo "------------------------------------------------------"
echo "NetProbe Pi has been installed to /opt/netprobe"
echo "The service is running as user: $USER"
echo "After reboot, connect to the 'NetProbe' WiFi network"
echo "Access the dashboard at: http://netprobe.local"
echo "Default password will be set on first login"
echo "------------------------------------------------------"
