#!/bin/bash
# NetScout-Pi - Direct Installer
# This script can be used with curl | bash for a one-line installation

# Create temporary directory
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo "NetScout-Pi - Direct Installer"
echo "============================="
echo "This will install NetScout-Pi on your system."
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Try 'sudo bash' before running this script."
    exit 1
fi

echo "Downloading NetScout-Pi unified installer script..."
wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/unified_installer.sh -O unified_installer.sh
chmod +x unified_installer.sh

echo "Running unified installer script..."
bash unified_installer.sh

# Clean up
cd /tmp
rm -rf "$TMP_DIR"
echo "Installing Python packages system-wide..."
apt-get install -y python3-flask python3-dotenv python3-click python3-watchdog python3-psutil \
                  python3-netifaces python3-yaml python3-jsonschema python3-bcrypt python3-jwt \
                  python3-requests python3-socketio

# Download the repository
echo "Downloading NetProbe Pi..."
wget -q https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip -O netscout.zip

# Extract files
echo "Extracting files..."
unzip -q netscout.zip

# Create installation directory
echo "Creating installation directory..."
mkdir -p /opt/netprobe
mkdir -p /var/log/netprobe

# Move files to installation directory
echo "Moving files to installation directory..."
cp -r NetScout-Pi-main/* /opt/netprobe/

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
        # Try to find a non-root user
        for user in $(ls /home); do
            if id "$user" &>/dev/null; then
                USER="$user"
                GROUP="$user"
                break
            fi
        done
        
        # If still no user found, use current user
        if [ -z "$USER" ]; then
            USER=$(whoami)
            GROUP=$(whoami)
        fi
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

# Configure WiFi access point
echo "Configuring WiFi access point..."
systemctl unmask hostapd
systemctl enable hostapd

# Configure hostapd for WiFi access point
cat > /etc/hostapd/hostapd.conf << EOF
interface=wlan0
driver=nl80211
ssid=NetProbe
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=netprobe123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# Configure dnsmasq for DHCP
cat > /etc/dnsmasq.conf << EOF
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=local
address=/netprobe.local/192.168.4.1
EOF

# Configure network interfaces
echo "Configuring network interfaces..."
cat > /etc/dhcpcd.conf << EOF
# NetProbe Pi network configuration

# Default behavior for all interfaces
interface *
allowinterfaces wlan0 eth0 lo
option rapid_commit
option domain_name_servers, 8.8.8.8, 8.8.4.4
require dhcp_server_identifier
slaac private

# Configure wlan0 for admin access
interface wlan0
static ip_address=192.168.4.1/24
nohook wpa_supplicant
EOF

# Unblock WiFi
echo "Unblocking WiFi..."
rfkill unblock wifi

# Set country code for WiFi if raspi-config is available
if command -v raspi-config >/dev/null 2>&1; then
    echo "Setting WiFi country code..."
    COUNTRY="US"  # Change this to your country code if needed
    raspi-config nonint do_wifi_country $COUNTRY
fi

# Start the services
systemctl restart dnsmasq
systemctl restart hostapd
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
