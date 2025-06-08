#!/bin/bash
# NetProbe Pi - Setup Script for Raspberry Pi Zero 2 W
# This script should be run on a fresh installation of Raspberry Pi OS Lite

set -e

echo "NetProbe Pi - Initial Setup"
echo "============================="
echo

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Try 'sudo $0'"
    exit 1
fi

# Update and upgrade system
echo "Updating system..."
apt-get update
apt-get upgrade -y

# Install Git and other essential tools
echo "Installing Git and essential tools..."
apt-get install -y git curl wget net-tools unzip

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

# Enable SSH
echo "Enabling SSH..."
systemctl enable ssh
systemctl start ssh

# Clone NetProbe Pi repository
echo "Cloning NetProbe Pi repository..."
cd /tmp
git clone --depth 1 https://github.com/raf181/NetScout-Pi.git netprobe || {
  echo "Failed to clone repository using HTTPS. Trying to download ZIP file..."
  wget https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip -O netprobe.zip
  unzip netprobe.zip
  mv NetScout-Pi-main netprobe
}
cd netprobe

# Run installer script
echo "Running NetProbe Pi installer..."
bash scripts/install.sh

echo
echo "NetProbe Pi setup completed successfully!"
echo "Please reboot the system to complete the installation."
echo "After reboot, connect to the 'NetProbe' WiFi network and access the dashboard at http://netprobe.local"
echo

exit 0
