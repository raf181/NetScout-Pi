#!/bin/bash
# NetScout-Pi - Enhanced Auto Fix Script v2
# Legacy wrapper for the unified installer

echo "NetScout-Pi - Enhanced Auto Fix Script v2"
echo "============================="
echo "This will automatically fix common issues with NetScout-Pi."
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Try 'sudo bash' before running this script."
    exit 1
fi

    exit 1
fi

echo "Using unified installer in fix mode..."

# Just call the unified installer with fix parameter
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
INSTALLER_PATH="$SCRIPT_DIR/unified_installer.sh"

# If the unified installer exists locally, use it
if [ -f "$INSTALLER_PATH" ]; then
    sudo bash "$INSTALLER_PATH" fix
else
    # Otherwise download and run it
    TMP_DIR=$(mktemp -d)
    cd "$TMP_DIR"
    
    echo "Downloading NetScout-Pi unified installer script..."
    wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/unified_installer.sh -O unified_installer.sh
    chmod +x unified_installer.sh
    
    echo "Running unified installer in fix mode..."
    sudo bash unified_installer.sh fix
    
    # Clean up
    cd /tmp
    rm -rf "$TMP_DIR"
fi
    echo "   - Hostname already in /etc/hosts"
else
    echo "127.0.1.1 netprobe" >> /etc/hosts
    echo "   - Added netprobe to /etc/hosts"
fi

# Fix WiFi issues
echo "2. Fixing WiFi issues..."

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
        # Create a basic wpa_supplicant.conf if it doesn't exist
        mkdir -p /etc/wpa_supplicant
        echo "country=US" > /etc/wpa_supplicant/wpa_supplicant.conf
        echo "     Created basic wpa_supplicant.conf with country code US"
    fi
fi

# Fix locale issues
echo "   - Fixing locale issues..."
# Only generate the locale if it's not already there
if ! locale -a 2>/dev/null | grep -q "en_US.utf8"; then
    echo "     Locale en_US.UTF-8 not found, attempting to generate (this may take a moment)..."
    if ! command -v locale-gen >/dev/null 2>&1; then
        echo "     locale-gen command not found, skipping locale generation"
    else
        # Check if localedef is already running and kill it if it's using too much CPU
        LOCALEDEF_PID=$(pgrep localedef || true)
        if [ -n "$LOCALEDEF_PID" ]; then
            CPU_USAGE=$(ps -p $LOCALEDEF_PID -o %cpu | tail -n 1 | tr -d ' ')
            if [ $(echo "$CPU_USAGE > 90" | bc -l 2>/dev/null || echo "1") -eq 1 ]; then
                echo "     Terminating existing high-CPU localedef process..."
                kill -9 $LOCALEDEF_PID 2>/dev/null || true
                sleep 1
            fi
        fi
        
        # Set a timeout for locale-gen to prevent it from running too long
        timeout 10s locale-gen en_US.UTF-8 > /dev/null 2>&1 || echo "     Locale generation timed out, continuing anyway"
    fi
else
    echo "     Locale en_US.UTF-8 already exists"
fi

# Set default locale without regenerating
echo 'LANG="en_US.UTF-8"' > /etc/default/locale
echo "     Set default locale to en_US.UTF-8"

# Check if interface exists
echo "   - Checking WiFi interface..."
if ip link show wlan0 > /dev/null 2>&1; then
    echo "     wlan0 interface exists"
else
    echo "     Warning: wlan0 interface not found, checking for other wireless interfaces..."
    WIRELESS_IF=$(ip link | grep -i "wlan" | cut -d: -f2 | tr -d ' ' | head -n1)
    if [ -n "$WIRELESS_IF" ]; then
        echo "     Found wireless interface: $WIRELESS_IF"
        echo "     Will use $WIRELESS_IF instead of wlan0"
        # Replace wlan0 with found interface in config files
        sed -i "s/wlan0/$WIRELESS_IF/g" /etc/hostapd/hostapd.conf 2>/dev/null || true
        sed -i "s/wlan0/$WIRELESS_IF/g" /etc/dnsmasq.conf 2>/dev/null || true
    else
        echo "     Error: No wireless interface found!"
        echo "     Please check if your WiFi hardware is properly connected and recognized."
    fi
fi

# Configure hostapd
echo "   - Configuring WiFi access point..."
mkdir -p /etc/hostapd
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
mkdir -p /etc/dnsmasq.d
cat > /etc/dnsmasq.conf << EOF
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=local
address=/netprobe.local/192.168.4.1
EOF

# Configure network based on what's available (dhcpcd or NetworkManager)
echo "   - Configuring network interfaces..."
if command -v dhcpcd >/dev/null 2>&1 || [ -f /etc/dhcpcd.conf ]; then
    echo "     Using dhcpcd for network configuration"
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
elif [ -d /etc/NetworkManager ]; then
    echo "     Using NetworkManager for network configuration"
    # Create a NetworkManager connection for the access point
    mkdir -p /etc/NetworkManager/system-connections
    cat > /etc/NetworkManager/system-connections/NetProbe.nmconnection << EOF
[connection]
id=NetProbe
type=wifi
interface-name=wlan0
autoconnect=true
permissions=

[wifi]
mode=ap
ssid=NetProbe

[ipv4]
method=shared
address1=192.168.4.1/24

[ipv6]
method=disabled

[proxy]
EOF
    chmod 600 /etc/NetworkManager/system-connections/NetProbe.nmconnection
    # Restart NetworkManager to apply changes
    systemctl restart NetworkManager || true
else
    echo "     Warning: Neither dhcpcd nor NetworkManager found. Trying direct interface configuration."
    # Try to configure interface directly
    ip addr add 192.168.4.1/24 dev wlan0 || true
    ip link set wlan0 up || true
fi

# Enable and configure services
echo "   - Configuring services..."

# hostapd setup
systemctl unmask hostapd
systemctl enable hostapd

# dnsmasq setup
systemctl enable dnsmasq

# Fix service issues
echo "3. Fixing NetProbe service..."

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
    find /opt/netprobe/scripts -name "*.sh" -exec chmod +x {} \; || true
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
systemctl restart netprobe || echo "     Warning: Failed to restart NetProbe service"

# Check status
echo "4. Checking NetProbe status..."

echo "   - WiFi status:"
rfkill list || echo "     Unable to check rfkill status"
ip addr show | grep -A 2 "wlan" || echo "     Unable to check wireless interface status"

echo "   - Service status:"
systemctl status netprobe --no-pager || echo "     Unable to check netprobe service status"

echo "   - Network service status:"
systemctl status hostapd --no-pager || echo "     Unable to check hostapd status"
systemctl status dnsmasq --no-pager || echo "     Unable to check dnsmasq status"

# Restart services one more time
echo "5. Final service restart..."
systemctl restart hostapd || echo "     Warning: Failed to restart hostapd"
systemctl restart dnsmasq || echo "     Warning: Failed to restart dnsmasq"
if command -v dhcpcd >/dev/null 2>&1; then
    systemctl restart dhcpcd || echo "     Warning: Failed to restart dhcpcd"
fi
systemctl restart netprobe || echo "     Warning: Failed to restart NetProbe service"

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
