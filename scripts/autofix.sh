#!/bin/bash
# NetProbe Pi - Auto Fix Script
# This script automatically fixes common issues with NetProbe Pi installation
# Non-interactive version for use with curl | bash

set -e

echo "NetProbe Pi - Auto Fix Script"
echo "============================="
echo "This will automatically fix common issues with NetProbe Pi."
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Try 'sudo bash' before running this script."
    exit 1
fi

echo "Applying all fixes automatically..."

# Fix WiFi issues
echo "1. Fixing WiFi issues..."

# Unblock WiFi
echo "   - Unblocking WiFi..."
rfkill unblock wifi

# Set country code
echo "   - Setting WiFi country code..."
if command -v raspi-config >/dev/null 2>&1; then
    # Default to US
    COUNTRY="US"
    raspi-config nonint do_wifi_country $COUNTRY
    echo "     Country code set to $COUNTRY"
else
    echo "     raspi-config not found, setting country code manually..."
    # Try to set country code manually
    if [ -f /etc/wpa_supplicant/wpa_supplicant.conf ]; then
        if ! grep -q "country=" /etc/wpa_supplicant/wpa_supplicant.conf; then
            sed -i '1s/^/country=US\n/' /etc/wpa_supplicant/wpa_supplicant.conf
            echo "     Country code set to US in wpa_supplicant.conf"
        else
            echo "     Country code already set in wpa_supplicant.conf"
        fi
    else
        echo "     wpa_supplicant.conf not found, skipping country code setting"
    fi
fi

# Configure hostapd
echo "   - Configuring WiFi access point..."
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

# Configure dnsmasq
echo "   - Configuring DHCP server..."
cat > /etc/dnsmasq.conf << EOF
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=local
address=/netprobe.local/192.168.4.1
EOF

# Configure network interfaces
echo "   - Configuring network interfaces..."
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

# Fix hostname resolution
echo "   - Fixing hostname resolution..."
if grep -q "netprobe" /etc/hosts; then
    echo "     Hostname already in /etc/hosts"
else
    echo "127.0.1.1 netprobe" >> /etc/hosts
    echo "     Added netprobe to /etc/hosts"
fi

# Restart services
echo "   - Restarting network services..."
systemctl unmask hostapd
systemctl enable hostapd
if ! systemctl restart hostapd; then
    echo "     Warning: Failed to restart hostapd, will try again after other fixes"
fi
if ! systemctl restart dnsmasq; then
    echo "     Warning: Failed to restart dnsmasq, will try again after other fixes"
fi
if ! systemctl restart dhcpcd; then
    echo "     Warning: Failed to restart dhcpcd, will try again after other fixes"
fi

echo "   WiFi configuration completed."

# Fix service issues
echo "2. Fixing NetProbe service..."

# Get current user
if id "pi" &>/dev/null; then
    USER="pi"
else
    # Try to find a non-root user
    for user in $(ls /home); do
        if id "$user" &>/dev/null; then
            USER="$user"
            break
        fi
    done
    
    # If still no user found, use current user
    if [ -z "$USER" ]; then
        if [ -n "$SUDO_USER" ]; then
            USER="$SUDO_USER"
        else
            USER=$(whoami)
        fi
    fi
fi

echo "   - Using user: $USER"

# Create required directories
echo "   - Creating required directories..."
mkdir -p /opt/netprobe
mkdir -p /var/log/netprobe
mkdir -p /etc/netprobe

# Update service file
echo "   - Updating service configuration..."
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

# Fix permissions
echo "   - Setting permissions..."
chown -R $USER:$USER /opt/netprobe || true
chown -R $USER:$USER /var/log/netprobe || true

# Make scripts executable
if [ -d "/opt/netprobe/scripts" ]; then
    chmod +x /opt/netprobe/scripts/*.sh || true
fi
if [ -f "/opt/netprobe/app.py" ]; then
    chmod +x /opt/netprobe/app.py || true
fi

# Create basic config if it doesn't exist
if [ ! -f "/etc/netprobe/config.yaml" ]; then
    echo "   - Creating default configuration..."
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

# Reload and restart service
echo "   - Restarting service..."
systemctl daemon-reload
systemctl enable netprobe
if ! systemctl restart netprobe; then
    echo "     Warning: Failed to restart NetProbe service"
fi

echo "   Service configuration completed."

# Check status
echo "3. Checking NetProbe status..."

echo "   - WiFi status:"
rfkill list || echo "     Unable to check rfkill status"
ip addr show wlan0 || echo "     Unable to check wlan0 status"

echo "   - Service status:"
systemctl status netprobe || echo "     Unable to check netprobe service status"

echo "   - Network service status:"
systemctl status hostapd || echo "     Unable to check hostapd status"
systemctl status dnsmasq || echo "     Unable to check dnsmasq status"

# Restart services one more time
echo "4. Final service restart..."
systemctl restart hostapd || true
systemctl restart dnsmasq || true
systemctl restart dhcpcd || true
systemctl restart netprobe || true

echo
echo "All fixes applied. You should reboot the system for all changes to take effect."
echo "After reboot, connect to the 'NetProbe' WiFi network (password: netprobe123)"
echo "and access the dashboard at http://netprobe.local or http://192.168.4.1"
echo
echo "Would you like to reboot now? (y/n)"
read -t 10 -n 1 -r REPLY || REPLY="y"
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting in 5 seconds..."
    sleep 5
    reboot
else
    echo "Please reboot manually when convenient."
fi

exit 0
