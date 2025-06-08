#!/bin/bash
# NetProbe Pi - First Boot Script
# This script runs on the first boot of the Raspberry Pi

set -e

LOG_FILE="/var/log/netprobe/first_boot.log"
NETPROBE_DIR="/opt/netprobe"
SSH_DIR="/home/pi/.ssh"

# Create log directory
mkdir -p /var/log/netprobe

# Log function
log() {
    echo "$(date): $1" | tee -a $LOG_FILE
}

log "Starting NetProbe Pi first boot script"

# Check if script has already run
if [ -f "${NETPROBE_DIR}/.first_boot_completed" ]; then
    log "First boot script has already been executed. Exiting."
    exit 0
fi

# Install dependencies if needed
log "Checking dependencies..."
apt-get update
apt-get install -y python3-pip python3-venv git dnsmasq hostapd

# Generate SSH key if it doesn't exist
if [ ! -f "${SSH_DIR}/id_rsa" ]; then
    log "Generating SSH key pair..."
    mkdir -p ${SSH_DIR}
    ssh-keygen -t rsa -b 4096 -f ${SSH_DIR}/id_rsa -N "" -C "netprobe@raspberrypi"
    cat ${SSH_DIR}/id_rsa.pub >> ${SSH_DIR}/authorized_keys
    chmod 600 ${SSH_DIR}/authorized_keys
    chown -R pi:pi ${SSH_DIR}
    log "SSH key pair generated"
fi

# Set up hostname
log "Setting hostname to netprobe..."
echo "netprobe" > /etc/hostname
sed -i 's/127.0.1.1.*raspberrypi/127.0.1.1\tnetprobe/g' /etc/hosts
hostnamectl set-hostname netprobe

# Set up mDNS for netprobe.local
log "Setting up mDNS for netprobe.local..."
apt-get install -y avahi-daemon
systemctl enable avahi-daemon
systemctl restart avahi-daemon

# Create network interface configuration for WiFi and Ethernet
log "Configuring network interfaces..."
cat > /etc/netplan/99-netprobe.yaml << EOF
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
      optional: true
  wifis:
    wlan0:
      dhcp4: true
      optional: true
      access-points:
        "NetProbe":
          password: "netprobe123"
          mode: ap
EOF

# Apply network configuration
netplan apply

# Set up ifplugd for Ethernet connection detection
log "Setting up ifplugd for Ethernet connection detection..."
apt-get install -y ifplugd
systemctl enable ifplugd@eth0
systemctl start ifplugd@eth0

# Create directory for ifplugd scripts
mkdir -p /etc/ifplugd/netprobe

# Create ifplugd action script
cat > /etc/ifplugd/netprobe.action << EOF
#!/bin/sh
# ifplugd action script for NetProbe
INTERFACE="\$1"
ACTION="\$2"

if [ "\$ACTION" = "up" ]; then
    echo "Interface \$INTERFACE is up" > /tmp/netprobe_eth_status
    # Run NetProbe trigger
    python3 ${NETPROBE_DIR}/scripts/trigger_event.py eth_connect
elif [ "\$ACTION" = "down" ]; then
    echo "Interface \$INTERFACE is down" > /tmp/netprobe_eth_status
    # Run NetProbe trigger
    python3 ${NETPROBE_DIR}/scripts/trigger_event.py eth_disconnect
fi
EOF

chmod +x /etc/ifplugd/netprobe.action

# Create network trigger script
mkdir -p ${NETPROBE_DIR}/scripts
cat > ${NETPROBE_DIR}/scripts/trigger_event.py << EOF
#!/usr/bin/env python3
# Script to trigger network events for NetProbe Pi

import sys
import os
import json
import time
from datetime import datetime

if len(sys.argv) < 2:
    print("Usage: trigger_event.py <event_name>")
    sys.exit(1)

event_name = sys.argv[1]
event_file = "/tmp/netprobe_event"

# Create event data
event_data = {
    "timestamp": datetime.now().isoformat(),
    "event": event_name
}

# Write event to file
with open(event_file, 'w') as f:
    json.dump(event_data, f)

print(f"Event {event_name} triggered")
EOF

chmod +x ${NETPROBE_DIR}/scripts/trigger_event.py

# Mark first boot as completed
touch ${NETPROBE_DIR}/.first_boot_completed
log "First boot script completed successfully"

# Reboot to apply all changes
log "Rebooting system..."
reboot
