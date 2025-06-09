#!/bin/bash
# NetScout-Pi - Setup Script for Raspberry Pi
# This script has been replaced by the unified installer

echo "NetScout-Pi - Initial Setup"
echo "============================="
echo "This script has been replaced by the unified installer."
echo "Running the unified installer instead."
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Try 'sudo $0'"
    exit 1
fi

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

exit 0
else
    IS_RASPBERRY_PI=false
    echo "Non-Raspberry Pi system detected. Some features may not work as expected."
fi

# Update and upgrade system
echo "Updating system..."
apt-get update
apt-get upgrade -y

# Install Git and other essential tools
echo "Installing Git and essential tools..."
apt-get install -y git curl wget net-tools unzip python3 python3-pip

# Configure network interfaces if Raspberry Pi
if [ "$IS_RASPBERRY_PI" = true ]; then
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

# Configure eth0 for USB-Ethernet
interface eth0
static ip_address=192.168.7.1/24
nohook wpa_supplicant

# Configure wlan0 for admin access
interface wlan0
static ip_address=192.168.4.1/24
nohook wpa_supplicant
EOF

# Set up hostapd for WiFi access point
echo "Setting up WiFi access point..."
apt-get install -y hostapd dnsmasq
systemctl unmask hostapd
systemctl enable hostapd

cat > /etc/hostapd/hostapd.conf << EOF
# NetProbe Pi WiFi AP configuration
interface=wlan0
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

cat > /etc/dnsmasq.conf << EOF
# NetProbe Pi DNS/DHCP configuration
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=local
address=/netprobe.local/192.168.4.1
EOF

# Close the conditional for Raspberry Pi
fi

# Enable SSH
echo "Enabling SSH..."
systemctl enable ssh
systemctl start ssh

# Download NetProbe Pi repository
echo "Downloading NetProbe Pi repository..."
cd /tmp

# Download the repository as a ZIP file (doesn't require authentication)
echo "Downloading repository as ZIP..."
wget -q https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip -O netscout.zip

# Create a clean directory for extraction
echo "Extracting files..."
rm -rf NetScout-Pi-main
unzip -q netscout.zip
cd NetScout-Pi-main

# Run installer script
echo "Running NetProbe Pi installer..."
bash scripts/install.sh

# Clean up
cd /tmp
rm -rf NetScout-Pi-main netscout.zip

# Final message
echo
echo "============================================="
echo "NetProbe Pi Setup Complete"
echo "============================================="
echo "The system will now reboot to complete setup."
echo "After reboot:"
echo "1. Connect to the 'NetProbe' WiFi network"
echo "   SSID: NetProbe"
echo "   Password: netprobe123"
echo "2. Access the dashboard at http://netprobe.local"
echo "3. Set your admin password on first login"
echo "============================================="
echo "Rebooting in 10 seconds... Press Ctrl+C to cancel"
echo

# Countdown before reboot
for i in {10..1}; do
  echo -n "$i... "
  sleep 1
done
echo

reboot
