#!/bin/bash
# Setup script for NetScout-Pi-V2
# This script will install all dependencies and set up the service

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print colored message
function print_message() {
    echo -e "${GREEN}[NetScout] ${1}${NC}"
}

function print_warning() {
    echo -e "${YELLOW}[Warning] ${1}${NC}"
}

function print_error() {
    echo -e "${RED}[Error] ${1}${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
cd "$SCRIPT_DIR"

print_message "Setting up NetScout-Pi-V2..."

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$PYTHON_VERSION < 3.7" | bc -l) )); then
    print_warning "Python version $PYTHON_VERSION detected. Recommended version is 3.7 or higher."
fi

# Install system dependencies
print_message "Installing system dependencies..."
apt-get update
apt-get install -y python3-pip python3-dev iputils-ping net-tools ethtool

# Check and install net-tools (for arp command)
if ! command -v arp &> /dev/null; then
    print_message "Installing net-tools package for arp command..."
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        apt-get update
        apt-get install -y net-tools
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS/Fedora
        yum install -y net-tools
    elif [ -f /etc/arch-release ]; then
        # Arch Linux
        pacman -S --noconfirm net-tools
    else
        print_warning "Could not automatically install net-tools. Please install manually to use arp command."
    fi
fi

# Install Python dependencies
print_message "Installing Python dependencies..."

# Check if we're in an externally managed environment (PEP 668)
if pip3 install --dry-run -r requirements.txt 2>&1 | grep -q "externally-managed-environment"; then
    print_warning "Detected externally-managed environment. Setting up a virtual environment instead."
    
    # Make sure python3-venv is installed
    apt-get install -y python3-venv python3-full
    
    # Create virtual environment
    VENV_DIR="$SCRIPT_DIR/venv"
    print_message "Creating virtual environment at $VENV_DIR"
    
    # Create virtual environment as the non-root user
    if [ -n "$SUDO_USER" ]; then
        su - $SUDO_USER -c "python3 -m venv $VENV_DIR"
    else
        python3 -m venv $VENV_DIR
    fi
    
    # Install dependencies in the virtual environment
    print_message "Installing dependencies in virtual environment..."
    if [ -n "$SUDO_USER" ]; then
        su - $SUDO_USER -c "$VENV_DIR/bin/pip install -r $SCRIPT_DIR/requirements.txt"
    else
        $VENV_DIR/bin/pip install -r $SCRIPT_DIR/requirements.txt
    fi
    
    # Update service file to use the virtual environment
    PYTHON_PATH="$VENV_DIR/bin/python"
    
    # Create a wrapper script to run from systemd
    cat > "$SCRIPT_DIR/run_netscout.sh" << EOL
#!/bin/bash
$VENV_DIR/bin/python $SCRIPT_DIR/run.py
EOL
    chmod +x "$SCRIPT_DIR/run_netscout.sh"
    
    print_message "Virtual environment setup complete."
else
    # Standard installation if not externally managed
    pip3 install -r requirements.txt
    PYTHON_PATH="/usr/bin/python3"
fi

# Create log directory
if [ ! -d "/var/log/netscout" ]; then
    mkdir -p /var/log/netscout
    chown $SUDO_USER:$SUDO_USER /var/log/netscout
fi

# Set up the service
print_message "Setting up the NetScout service..."
cp "$SCRIPT_DIR/netscout.service" /etc/systemd/system/
sed -i "s|/home/pi/NetScout-Pi-V2|$SCRIPT_DIR|g" /etc/systemd/system/netscout.service
sed -i "s|User=pi|User=$SUDO_USER|g" /etc/systemd/system/netscout.service

# Update ExecStart path based on whether we're using a virtual environment
if [ -f "$SCRIPT_DIR/run_netscout.sh" ]; then
    # Using virtual environment with wrapper script
    sed -i "s|ExecStart=/usr/bin/python3 /home/pi/NetScout-Pi-V2/run.py|ExecStart=$SCRIPT_DIR/run_netscout.sh|g" /etc/systemd/system/netscout.service
fi

# Reload systemd
systemctl daemon-reload

# Enable and start the service
print_message "Enabling and starting the NetScout service..."
systemctl enable netscout
systemctl start netscout

# Check if the service is running
if systemctl is-active --quiet netscout; then
    print_message "NetScout service is now running!"
else
    print_error "Failed to start NetScout service. Check the logs with 'journalctl -u netscout'"
    exit 1
fi

# Get IP addresses
IP_ADDRESSES=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1')

print_message "Installation complete!"
print_message "You can access the NetScout dashboard at:"
for IP in $IP_ADDRESSES; do
    echo -e "${GREEN}http://$IP:5000${NC}"
done

print_message "To manage the service:"
echo -e "  ${YELLOW}Start:${NC}   sudo systemctl start netscout"
echo -e "  ${YELLOW}Stop:${NC}    sudo systemctl stop netscout"
echo -e "  ${YELLOW}Restart:${NC} sudo systemctl restart netscout"
echo -e "  ${YELLOW}Status:${NC}  sudo systemctl status netscout"
echo -e "  ${YELLOW}Logs:${NC}    sudo journalctl -u netscout -f"
