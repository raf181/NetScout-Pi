#!/bin/bash
# NetProbe Pi - Fix Script
# This script fixes common issues with NetProbe Pi installation

set -e

echo "NetProbe Pi - Fix Script"
echo "============================="
echo "This will fix common issues with NetProbe Pi."
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Try 'sudo bash' before running this script."
    exit 1
fi

# Function to fix WiFi issues
fix_wifi() {
    echo "Fixing WiFi issues..."
    
    # Unblock WiFi
    echo "Unblocking WiFi..."
    rfkill unblock wifi
    
    # Set country code
    echo "Setting WiFi country code..."
    if command -v raspi-config >/dev/null 2>&1; then
        # Default to US, but allow user to change
        echo "Available country codes: US, GB, DE, FR, ES, IT, AU, CA, JP, CN, etc."
        read -p "Enter your country code [US]: " COUNTRY
        COUNTRY=${COUNTRY:-US}
        raspi-config nonint do_wifi_country $COUNTRY
    else
        echo "raspi-config not found, setting country code manually..."
        # Try to set country code manually
        if [ -f /etc/wpa_supplicant/wpa_supplicant.conf ]; then
            if ! grep -q "country=" /etc/wpa_supplicant/wpa_supplicant.conf; then
                sed -i '1s/^/country=US\n/' /etc/wpa_supplicant/wpa_supplicant.conf
            fi
        fi
    fi
    
    # Configure hostapd
    echo "Configuring WiFi access point..."
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
    echo "Configuring DHCP server..."
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
    
    # Restart services
    echo "Restarting network services..."
    systemctl unmask hostapd
    systemctl enable hostapd
    systemctl restart hostapd
    systemctl restart dnsmasq
    systemctl restart dhcpcd
    
    echo "WiFi configuration completed. The access point should now be available as 'NetProbe'."
}

# Function to fix service issues
fix_service() {
    echo "Fixing NetProbe service..."
    
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
    
    echo "Using user: $USER"
    
    # Update service file
    echo "Updating service configuration..."
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
    echo "Setting permissions..."
    chown -R $USER:$USER /opt/netprobe
    chown -R $USER:$USER /var/log/netprobe
    chmod +x /opt/netprobe/scripts/*.sh
    chmod +x /opt/netprobe/app.py
    
    # Reload and restart service
    echo "Restarting service..."
    systemctl daemon-reload
    systemctl enable netprobe
    systemctl restart netprobe
    
    echo "Service fixed and restarted."
}

# Function to check status
check_status() {
    echo "Checking NetProbe status..."
    
    echo "1. WiFi status:"
    rfkill list
    ip addr show wlan0
    
    echo "2. Service status:"
    systemctl status netprobe
    
    echo "3. Network service status:"
    systemctl status hostapd
    systemctl status dnsmasq
}

# Main menu
PS3="Select an option: "
options=("Fix WiFi Issues" "Fix Service Issues" "Check Status" "Fix Everything" "Exit")
select opt in "${options[@]}"
do
    case $opt in
        "Fix WiFi Issues")
            fix_wifi
            ;;
        "Fix Service Issues")
            fix_service
            ;;
        "Check Status")
            check_status
            ;;
        "Fix Everything")
            fix_wifi
            fix_service
            check_status
            echo "All fixes applied. You may need to reboot for all changes to take effect."
            read -p "Would you like to reboot now? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                reboot
            fi
            ;;
        "Exit")
            break
            ;;
        *) 
            echo "Invalid option"
            ;;
    esac
done

exit 0
