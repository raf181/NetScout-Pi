#!/bin/bash
# NetScout-Pi - Dependency Installation Script

# Make script exit on any error
set -e

echo "Installing NetScout-Pi dependencies..."

# Update package lists
echo "Updating package lists..."
apt-get update

# Install Python and development tools
echo "Installing Python and development tools..."
apt-get install -y python3 python3-dev python3-pip python3-venv

# Install required system packages
echo "Installing required system packages..."
apt-get install -y \
  python3-yaml \
  python3-flask \
  python3-flask-socketio \
  python3-netifaces \
  python3-psutil \
  python3-requests \
  python3-cryptography \
  python3-socketio \
  python3-eventlet \
  python3-setuptools \
  python3-wheel \
  python3-bcrypt \
  python3-scapy \
  python3-pandas \
  python3-pyroute2 \
  python3-redis \
  python3-jwt \
  python3-jinja2 \
  python3-markupsafe \
  python3-itsdangerous \
  python3-dnspython \
  python3-dotenv \
  python3-bidict \
  python3-click \
  python3-jsonschema \
  python3-watchdog \
  python3-crontab \
  python3-matplotlib \
  python3-sqlalchemy \
  nmap \
  arp-scan \
  tcpdump \
  iproute2 \
  net-tools

# Create required directories
echo "Creating required directories..."
mkdir -p /var/log/netprobe /var/lib/netprobe /etc/netprobe/plugins

# Set directory permissions
echo "Setting directory permissions..."
if [ -n "$SUDO_USER" ]; then
  # If script was run with sudo, set the original user as owner
  chown -R $SUDO_USER:$SUDO_USER /var/log/netprobe /var/lib/netprobe /etc/netprobe
else
  # Otherwise set more permissive permissions
  chmod 777 /var/log/netprobe /var/lib/netprobe /etc/netprobe
fi

# Install remaining Python packages system-wide using pip
echo "Installing additional Python packages..."
pip3 install --break-system-packages \
  flask-socketio>=5.1.1 \
  python-dotenv>=0.19.0 \
  click>=8.0.1 \
  watchdog>=2.1.5 \
  speedtest-cli>=2.1.3 \
  python-nmap>=0.7.1 \
  ping3>=4.0.4 \
  netaddr>=0.8.0 \
  websocket-client>=1.5.1 \
  aiohttp>=3.8.5

# Create default config if it doesn't exist
if [ ! -f /etc/netprobe/config.yaml ]; then
  echo "Creating default configuration..."
  cat > /etc/netprobe/config.yaml << EOF
system:
  log_dir: /var/log/netprobe
  data_dir: /var/lib/netprobe
  plugin_dir: /etc/netprobe/plugins
  log_level: INFO
  debug: false
network:
  interface: eth0
  wifi_interface: wlan0
  auto_run_on_connect: true
  default_plugins:
    - ip_info
    - ping_test
  poll_interval: 5
web:
  host: 0.0.0.0
  port: 8080  # Using 8080 instead of 80 to avoid needing root
  auth_required: true
security:
  allow_eth0_access: true
setup:
  completed: false
EOF
fi

echo "Installation complete!"
echo "You can now run NetScout-Pi with: sudo python3 app.py"
echo "For first-time setup: sudo python3 app.py --setup"
echo "Access the web interface at: http://localhost:8080"
echo "For root privileges (needed for some network operations): sudo python3 app.py"
