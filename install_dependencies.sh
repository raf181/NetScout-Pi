#!/bin/bash
# Script to install the net-tools package which provides the arp command

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
    print_error "Please run as root (sudo ./install_dependencies.sh)"
    exit 1
fi

# Check if /usr/sbin is in PATH
if [[ ":$PATH:" != *":/usr/sbin:"* ]]; then
    print_warning "/usr/sbin is not in your PATH. Adding it temporarily for this script."
    export PATH="$PATH:/usr/sbin"
    
    # Suggest adding it permanently
    print_message "Consider adding /usr/sbin to your PATH permanently by adding this line to your ~/.bashrc file:"
    print_message "export PATH=\$PATH:/usr/sbin"
fi

# Check for net-tools (arp)
if ! command -v arp &> /dev/null && [ ! -f /usr/sbin/arp ]; then
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
        print_warning "Could not automatically determine your Linux distribution."
        print_warning "Please install net-tools package manually using your distribution's package manager."
        exit 1
    fi
    
    print_message "net-tools package installed successfully!"
else
    print_message "arp command is already installed."
fi

# Verify installation
if command -v arp &> /dev/null; then
    print_message "arp command is now available."
    print_message "You can now use the Network Scanner plugin."
else
    print_error "Failed to install arp command. Please install net-tools package manually."
    exit 1
fi
