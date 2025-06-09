#!/bin/bash
# NetScout-Pi - All-in-One Installer
# This script handles downloading, setup, and installation in one step
# 
# Usage: sudo bash netscout_installer.sh [--no-deps] [--local] [--dev]
#   --no-deps: Skip system dependency installation
#   --local: Install in local mode (user directories instead of system)
#   --dev: Set up development environment with venv
#
# Author: NetScout-Pi Team
# Updated: June 9, 2025

set -e

# Terminal colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/netprobe"
LOG_DIR="/var/log/netprobe"
DATA_DIR="/var/lib/netprobe"
CONFIG_DIR="/etc/netprobe"
PLUGIN_DIR="${CONFIG_DIR}/plugins"
SERVICE_NAME="netprobe"
REPO_URL="https://github.com/raf181/NetScout-Pi.git"
ZIP_URL="https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip"
TMP_DIR=$(mktemp -d)
WIFI_SSID="NetProbe"
WIFI_PASSWORD="netprobe123"

# Parse arguments
NO_DEPS=false
LOCAL_MODE=false
DEV_MODE=false

for arg in "$@"; do
  case $arg in
    --no-deps)
      NO_DEPS=true
      shift
      ;;
    --local)
      LOCAL_MODE=true
      shift
      ;;
    --dev)
      DEV_MODE=true
      shift
      ;;
    *)
      # Unknown option
      ;;
  esac
done

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}==================================================${NC}"
    echo -e "${BLUE}    $1${NC}"
    echo -e "${BLUE}==================================================${NC}"
}

# Function to print status messages
print_status() {
    echo -e "${CYAN}$1${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

# Set up logging
setup_logging() {
    # Create log directory
    mkdir -p "${LOG_DIR}"
    LOG_FILE="${LOG_DIR}/installer_$(date +%Y%m%d_%H%M%S).log"
    
    # Start logging
    exec > >(tee -a "$LOG_FILE") 2>&1
    print_success "Logging to $LOG_FILE"
}

# Check if script is run as root
check_root() {
    if [ "$EUID" -ne 0 ] && [ "$LOCAL_MODE" = false ]; then
        print_error "This script must be run as root (sudo) unless using --local mode."
        echo "Try: sudo bash $0 $*"
        exit 1
    fi
}

# Determine the user to run the service
get_user() {
    if [ -n "$SUDO_USER" ]; then
        USER="$SUDO_USER"
    elif id "pi" &>/dev/null; then
        USER="pi"
    else
        USER="$(whoami)"
    fi
    
    if [ "$USER" = "root" ]; then
        print_warning "Running as root user. This is not recommended for security reasons."
        print_warning "Consider using a regular user with sudo privileges."
    else
        print_success "Using user: $USER"
    fi
}

# Set up local directories if in local mode
setup_local_mode() {
    if [ "$LOCAL_MODE" = true ]; then
        BASE_DIR="$(pwd)"
        INSTALL_DIR="${BASE_DIR}"
        LOG_DIR="${BASE_DIR}/logs"
        DATA_DIR="${BASE_DIR}/data"
        CONFIG_DIR="${BASE_DIR}/config"
        PLUGIN_DIR="${CONFIG_DIR}/plugins"
        
        print_success "Local mode enabled. Using directories under ${BASE_DIR}"
    fi
}

# Create necessary directories with proper permissions
create_directories() {
    print_status "Creating required directories..."
    
    mkdir -p "${LOG_DIR}"
    mkdir -p "${DATA_DIR}"
    mkdir -p "${CONFIG_DIR}"
    mkdir -p "${PLUGIN_DIR}"
    
    if [ "$LOCAL_MODE" = false ]; then
        # Set correct ownership for system directories
        if [ -n "$USER" ] && [ "$USER" != "root" ]; then
            chown -R "$USER:$USER" "${LOG_DIR}" "${DATA_DIR}" "${CONFIG_DIR}"
        fi
        chmod -R 755 "${LOG_DIR}" "${DATA_DIR}" "${CONFIG_DIR}"
        print_success "Created system directories with proper permissions"
    else
        print_success "Created local directories"
    fi
}

# Install required packages with error handling
install_dependencies() {
    if [ "$NO_DEPS" = true ]; then
        print_warning "Skipping dependency installation (--no-deps flag used)"
        return
    fi
    
    print_section "Installing System Dependencies"
    
    if [ "$LOCAL_MODE" = false ]; then
        print_status "Updating package lists..."
        apt-get update || {
            print_error "Failed to update package lists"
            exit 1
        }
        
        print_status "Installing Python and development tools..."
        apt-get install -y python3 python3-dev python3-pip python3-venv || {
            print_error "Failed to install Python and development tools"
            exit 1
        }
        
        print_status "Installing required system packages..."
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
          python3-scapy \
          python3-pandas \
          python3-jinja2 \
          python3-markupsafe \
          python3-itsdangerous \
          python3-dnspython \
          python3-dotenv \
          python3-click \
          python3-watchdog \
          python3-matplotlib \
          nmap \
          arp-scan \
          tcpdump \
          iproute2 \
          net-tools || {
            print_warning "Some packages failed to install. Will try with pip later."
        }
    fi
    
    # Set up Python environment
    if [ "$DEV_MODE" = true ]; then
        print_status "Setting up Python virtual environment..."
        
        if [ ! -d "${INSTALL_DIR}/venv" ]; then
            python3 -m venv "${INSTALL_DIR}/venv"
            print_success "Created Python virtual environment"
        else
            print_warning "Virtual environment already exists"
        fi
        
        # Install pip dependencies in the virtual environment
        print_status "Installing Python packages in virtual environment..."
        "${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
        "${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt" || {
            print_error "Failed to install Python packages in virtual environment"
            exit 1
        }
    else
        # Install pip dependencies system-wide
        print_status "Installing Python packages system-wide..."
        
        if [ "$LOCAL_MODE" = false ]; then
            # System-wide installation
            pip3 install --break-system-packages -r "${INSTALL_DIR}/requirements.txt" || {
                print_warning "Failed to install some Python packages. Application may not work correctly."
            }
        else
            # User installation
            pip3 install --user -r "${INSTALL_DIR}/requirements.txt" || {
                print_warning "Failed to install some Python packages. Application may not work correctly."
            }
        fi
    fi
    
    print_success "Dependency installation completed"
}

# Download NetScout-Pi repository with fallbacks
download_repo() {
    print_section "Downloading NetScout-Pi"
    
    # If we're already in a NetScout-Pi directory, no need to download
    if [ -f "${PWD}/app.py" ] && [ -d "${PWD}/src" ]; then
        print_status "Already in NetScout-Pi directory, skipping download"
        
        if [ "$LOCAL_MODE" = true ]; then
            # For local mode, just use the current directory
            INSTALL_DIR="${PWD}"
            print_success "Using current directory as installation directory"
            return
        else
            # For system mode, copy from current directory to install directory
            print_status "Copying files to installation directory..."
            mkdir -p "${INSTALL_DIR}"
            cp -r "${PWD}"/* "${INSTALL_DIR}/"
            print_success "Files copied to installation directory"
            return
        fi
    fi
    
    # Try to download using git first
    print_status "Attempting to download using git..."
    if command -v git &>/dev/null; then
        if [ "$LOCAL_MODE" = true ]; then
            git clone "${REPO_URL}" "${INSTALL_DIR}" && {
                print_success "Successfully downloaded using git"
                return
            }
        else
            git clone "${REPO_URL}" "${TMP_DIR}/netscout" && {
                print_status "Copying files to installation directory..."
                mkdir -p "${INSTALL_DIR}"
                cp -r "${TMP_DIR}/netscout"/* "${INSTALL_DIR}/"
                print_success "Successfully downloaded using git"
                return
            }
        fi
    fi
    
    # Fallback to using wget and unzip
    print_status "Attempting to download using wget..."
    if command -v wget &>/dev/null && command -v unzip &>/dev/null; then
        wget -q "${ZIP_URL}" -O "${TMP_DIR}/netscout.zip" && {
            unzip -q "${TMP_DIR}/netscout.zip" -d "${TMP_DIR}" && {
                print_status "Copying files to installation directory..."
                mkdir -p "${INSTALL_DIR}"
                cp -r "${TMP_DIR}"/NetScout-Pi-main/* "${INSTALL_DIR}/"
                print_success "Successfully downloaded using wget"
                return
            }
        }
    fi
    
    # If all download methods fail
    print_error "Failed to download NetScout-Pi. Please check your internet connection and try again."
    exit 1
}

# Set correct permissions for executables
set_permissions() {
    print_status "Setting file permissions..."
    
    chmod +x "${INSTALL_DIR}/scripts"/*.sh
    chmod +x "${INSTALL_DIR}/app.py"
    
    print_success "Permissions set"
}

# Create default configuration
create_config() {
    if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
        print_status "Creating default configuration..."
        
        cat > "${CONFIG_DIR}/config.yaml" << EOF
# NetScout-Pi Configuration
system:
  log_dir: ${LOG_DIR}
  data_dir: ${DATA_DIR}
  plugin_dir: ${PLUGIN_DIR}
  log_level: INFO
  debug: false

web:
  host: 0.0.0.0
  port: 8080
  auth_required: true

setup:
  completed: false
EOF
        print_success "Default configuration created"
    else
        print_warning "Configuration file already exists, not overwriting"
    fi
}

# Create systemd service for system-wide installation
create_service() {
    if [ "$LOCAL_MODE" = true ]; then
        print_warning "Skipping service creation in local mode"
        return
    fi
    
    print_status "Creating systemd service..."
    
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=NetScout-Pi Network Diagnostics System
Documentation=https://github.com/raf181/NetScout-Pi
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/app.py
Restart=on-failure
RestartSec=10
StandardOutput=append:${LOG_DIR}/service.log
StandardError=append:${LOG_DIR}/service-error.log

# Security enhancements
PrivateTmp=true
ProtectHome=read-only
ProtectSystem=full
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd to recognize the new service
    systemctl daemon-reload
    
    print_success "Systemd service created"
}

# Create run scripts for convenience
create_run_scripts() {
    print_status "Creating run scripts..."
    
    if [ "$DEV_MODE" = true ]; then
        # Create run script for development mode
        cat > "${INSTALL_DIR}/run.sh" << EOF
#!/bin/bash
# Run NetScout-Pi in development mode
BASE_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$BASE_DIR"
source venv/bin/activate
python3 app.py --debug "\$@"
EOF
        
        chmod +x "${INSTALL_DIR}/run.sh"
        print_success "Created development run script: run.sh"
    else
        # Create regular run script
        cat > "${INSTALL_DIR}/run.sh" << EOF
#!/bin/bash
# Run NetScout-Pi
BASE_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$BASE_DIR"
python3 app.py "\$@"
EOF
        
        chmod +x "${INSTALL_DIR}/run.sh"
        print_success "Created run script: run.sh"
        
        # Create sudo run script
        cat > "${INSTALL_DIR}/run_with_sudo.sh" << EOF
#!/bin/bash
# Run NetScout-Pi with sudo (for access to privileged ports and operations)
BASE_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "\$BASE_DIR"
sudo PYTHONPATH="\${BASE_DIR}" python3 app.py "\$@"
EOF
        
        chmod +x "${INSTALL_DIR}/run_with_sudo.sh"
        print_success "Created sudo run script: run_with_sudo.sh"
    fi
}

# Fix permissions issue
fix_permissions() {
    print_status "Fixing permissions..."
    
    # Make log directory writable
    if [ -d "${LOG_DIR}" ]; then
        chmod -R 755 "${LOG_DIR}"
        if [ -n "$USER" ] && [ "$USER" != "root" ]; then
            chown -R "$USER:$USER" "${LOG_DIR}"
        fi
        print_success "Log directory permissions fixed"
    fi
    
    # Make data directory writable
    if [ -d "${DATA_DIR}" ]; then
        chmod -R 755 "${DATA_DIR}"
        if [ -n "$USER" ] && [ "$USER" != "root" ]; then
            chown -R "$USER:$USER" "${DATA_DIR}"
        fi
        print_success "Data directory permissions fixed"
    fi
    
    # Make config directory writable
    if [ -d "${CONFIG_DIR}" ]; then
        chmod -R 755 "${CONFIG_DIR}"
        if [ -n "$USER" ] && [ "$USER" != "root" ]; then
            chown -R "$USER:$USER" "${CONFIG_DIR}"
        fi
        print_success "Config directory permissions fixed"
    fi
}

# Start the service if requested
start_service() {
    if [ "$LOCAL_MODE" = true ]; then
        print_warning "Skipping service start in local mode"
        return
    fi
    
    print_status "Starting NetScout-Pi service..."
    
    systemctl enable "${SERVICE_NAME}" && {
        systemctl start "${SERVICE_NAME}" && {
            print_success "Service started successfully"
        } || {
            print_error "Failed to start service"
        }
    } || {
        print_error "Failed to enable service"
    }
}

# Print final message and instructions
print_instructions() {
    print_section "Installation Complete!"
    
    echo -e "${GREEN}NetScout-Pi has been successfully installed.${NC}"
    echo
    
    if [ "$LOCAL_MODE" = true ]; then
        echo "To run NetScout-Pi:"
        echo "  cd ${INSTALL_DIR}"
        if [ "$DEV_MODE" = true ]; then
            echo "  ./run.sh"
            echo
            echo "This will activate the virtual environment and start NetScout-Pi in debug mode."
        else
            echo "  ./run.sh          # Run without root privileges"
            echo "  ./run_with_sudo.sh # Run with root privileges (for network operations)"
        fi
    else
        echo "To manage the NetScout-Pi service:"
        echo "  sudo systemctl start ${SERVICE_NAME}   # Start the service"
        echo "  sudo systemctl stop ${SERVICE_NAME}    # Stop the service"
        echo "  sudo systemctl restart ${SERVICE_NAME} # Restart the service"
        echo "  sudo systemctl status ${SERVICE_NAME}  # Check service status"
        echo
        echo "You can also run NetScout-Pi manually:"
        echo "  cd ${INSTALL_DIR}"
        echo "  ./run.sh          # Run without root privileges"
        echo "  ./run_with_sudo.sh # Run with root privileges"
    fi
    
    echo
    echo "Access the web interface at:"
    echo "  http://localhost:8080"
    echo
    echo -e "${YELLOW}NOTE:${NC} For first-time setup, you will need to create an admin account."
    echo "      Follow the instructions in the web interface."
    echo
    echo -e "${BLUE}Documentation:${NC} ${INSTALL_DIR}/docs/"
    echo -e "${BLUE}Log files:${NC} ${LOG_DIR}/"
    echo -e "${BLUE}Configuration:${NC} ${CONFIG_DIR}/config.yaml"
    echo
    echo -e "${GREEN}Thank you for installing NetScout-Pi!${NC}"
}

# Cleanup temporary files
cleanup() {
    if [ -d "${TMP_DIR}" ]; then
        rm -rf "${TMP_DIR}"
    fi
}

# Main installation function
main() {
    print_section "NetScout-Pi All-in-One Installer"
    
    # Set up logging
    setup_logging
    
    # Check if running as root (unless in local mode)
    check_root
    
    # Get user
    get_user
    
    # Set up local mode if enabled
    setup_local_mode
    
    # Create directories
    create_directories
    
    # Download repository
    download_repo
    
    # Install dependencies
    install_dependencies
    
    # Set permissions
    set_permissions
    
    # Create default configuration
    create_config
    
    # Create systemd service (if not in local mode)
    create_service
    
    # Create run scripts
    create_run_scripts
    
    # Fix permissions
    fix_permissions
    
    # Start service (if not in local mode)
    start_service
    
    # Print instructions
    print_instructions
    
    # Cleanup
    cleanup
}

# Run the main function
main

exit 0
