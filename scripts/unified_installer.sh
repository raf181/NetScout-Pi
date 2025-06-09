#!/bin/bash
# NetScout-Pi - Unified Installer and Fix Script
# This script combines installation, update, fixing, and reset functionality
# Can be used with: curl -sSL https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/unified_installer.sh | sudo bash
# 
# Usage: 
#   sudo bash unified_installer.sh [install|update|fix|reset|clean]
#
# Author: NetScout-Pi Team
# Updated: June 9, 2025

set -e

# Configuration
INSTALL_DIR="/opt/netprobe"
LOG_DIR="/var/log/netprobe"
CONFIG_DIR="/etc/netprobe"
SERVICE_NAME="netprobe"
REPO_URL="https://github.com/raf181/NetScout-Pi.git"
ZIP_URL="https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip"
LOG_FILE="${LOG_DIR}/installer.log"
BACKUP_DIR="/opt/netprobe_backup"
TMP_DIR=$(mktemp -d)
WIFI_SSID="NetProbe"
WIFI_PASSWORD="netprobe123"
VERSION="1.0.0"

# Log function with timestamp and improved formatting
log() {
    # Create log directory if it doesn't exist yet
    mkdir -p $(dirname $LOG_FILE)
    
    # Get current timestamp in ISO 8601 format
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    # Format the message with timestamp and log level
    local level="${2:-INFO}"
    local message="[$timestamp] [$level] $1"
    
    # Output to console and log file
    echo -e "$message" | tee -a $LOG_FILE
}

# Log error messages
log_error() {
    log "$1" "ERROR"
}

# Log warning messages
log_warning() {
    log "$1" "WARNING"
}

# Print a section header for better visual organization
print_section() {
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    
    # Also log this section
    log "SECTION: $1" "SECTION"
}

# Check if script is run as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root. Try 'sudo $0'"
        exit 1
    fi
}

# Determine the user to run the service
get_user() {
    log "Determining user for service..."
    
    # First try the pi user (common on Raspberry Pi)
    if id "pi" &>/dev/null; then
        USER="pi"
        GROUP="pi"
        log "Found Raspberry Pi default user: $USER"
    else
        # Try to use sudo user if available
        if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ] && id "$SUDO_USER" &>/dev/null; then
            USER="$SUDO_USER"
            GROUP="$SUDO_USER"
            log "Using sudo user: $USER"
        else
            # Try to find a non-root user in /home
            for potential_user in $(ls /home 2>/dev/null); do
                if id "$potential_user" &>/dev/null; then
                    USER="$potential_user"
                    GROUP="$potential_user"
                    log "Using home directory user: $USER"
                    break
                fi
            done
            
            # If no user found yet, default to current user
            if [ -z "${USER:-}" ]; then
                USER=$(whoami)
                GROUP=$(whoami)
                log "Using current user: $USER"
                
                # If we're root, consider creating a dedicated user
                if [ "$USER" = "root" ]; then
                    log_warning "Running service as root is not recommended"
                    
                    # Optionally create a netprobe user for better security
                    if ! id "netprobe" &>/dev/null; then
                        read -p "Create dedicated 'netprobe' user for the service? (y/N): " -n 1 -r
                        echo
                        if [[ $REPLY =~ ^[Yy]$ ]]; then
                            useradd -m -s /bin/bash netprobe
                            USER="netprobe"
                            GROUP="netprobe"
                            log "Created dedicated user: $USER"
                        fi
                    fi
                fi
            fi
        fi
    fi
    
    log "Selected user: $USER and group: $GROUP for service execution"
}

# Create necessary directories with proper permissions
create_directories() {
    log "Creating required directories..."
    
    # Create main directories
    mkdir -p $INSTALL_DIR
    mkdir -p $LOG_DIR
    mkdir -p $CONFIG_DIR
    mkdir -p $BACKUP_DIR
    
    # Create subdirectories that might be needed
    mkdir -p $INSTALL_DIR/scripts
    mkdir -p $INSTALL_DIR/src/plugins
    mkdir -p $INSTALL_DIR/sequences
    
    # Set proper permissions immediately
    if getent passwd $USER > /dev/null && getent group $GROUP > /dev/null; then
        chown -R $USER:$GROUP $INSTALL_DIR
        chown -R $USER:$GROUP $LOG_DIR
        log "Directory permissions set to $USER:$GROUP"
    else
        log_warning "User $USER or group $GROUP not found, permissions will be set later"
    fi
}

# Install required packages with error handling
install_dependencies() {
    print_section "Installing Dependencies"
    
    # Update package lists
    log "Updating package lists..."
    apt-get update || { log_error "Failed to update package lists"; return 1; }
    
    # Install essential system packages
    log "Installing essential system packages..."
    apt-get install -y \
        python3 python3-pip git wget unzip \
        nmap tcpdump arp-scan speedtest-cli \
        ifplugd avahi-daemon iproute2 \
        dnsmasq hostapd \
        build-essential libffi-dev libssl-dev || {
            log_error "Failed to install essential packages"
            log_warning "Trying to install packages one by one..."
            
            # Try to install essential packages one by one
            for pkg in python3 python3-pip git wget unzip nmap tcpdump arp-scan speedtest-cli ifplugd avahi-daemon iproute2 dnsmasq hostapd build-essential libffi-dev libssl-dev; do
                log "Installing $pkg..."
                apt-get install -y $pkg || log_warning "Failed to install $pkg, continuing anyway"
            done
        }
    
    # Try to install Python packages with apt first (system packages are more stable)
    log "Installing Python packages via apt..."
    apt-get install -y \
        python3-flask python3-dotenv python3-click \
        python3-watchdog python3-psutil \
        python3-netifaces python3-yaml python3-jsonschema \
        python3-bcrypt python3-jwt python3-requests \
        python3-socketio || log_warning "Some Python packages could not be installed via apt"
    
    # Check if requirements.txt exists
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        # Install any remaining packages with pip, handling the externally-managed environment issue
        log "Installing Python packages from requirements.txt..."
        if pip3 install -r $INSTALL_DIR/requirements.txt 2>/dev/null; then
            log "Successfully installed Python packages with pip"
        else
            log_warning "Standard pip install failed, trying with --break-system-packages"
            pip3 install --break-system-packages -r $INSTALL_DIR/requirements.txt || {
                log_error "Failed to install Python packages with pip"
                log "Will continue installation, but some functionality may be limited"
            }
        fi
    else
        log_warning "requirements.txt not found in $INSTALL_DIR"
    fi
}

# Download NetScout-Pi repository with fallbacks
download_repo() {
    print_section "Downloading NetScout-Pi Repository"
    cd $TMP_DIR
    
    # Try using git first (allows for branch selection and better versioning)
    if command -v git >/dev/null 2>&1; then
        log "Attempting to clone repository with git..."
        if git clone --depth=1 $REPO_URL netscout-git 2>/dev/null; then
            log "Successfully cloned repository with git"
            cp -r netscout-git/* $INSTALL_DIR/
            rm -rf netscout-git
            return 0
        else
            log_warning "Git clone failed, falling back to ZIP download"
        fi
    else
        log "Git not available, using direct ZIP download"
    fi
    
    # Download ZIP file with retry
    log "Downloading repository as ZIP..."
    for i in {1..3}; do
        if wget -q $ZIP_URL -O netscout.zip; then
            log "Successfully downloaded ZIP file"
            break
        else
            log_warning "Download attempt $i failed"
            if [ $i -eq 3 ]; then
                log_error "Failed to download repository after 3 attempts"
                return 1
            fi
            sleep 2
        fi
    done
    
    # Extract and copy files
    log "Extracting files..."
    if unzip -q netscout.zip; then
        cp -r NetScout-Pi-main/* $INSTALL_DIR/
        rm -rf NetScout-Pi-main netscout.zip
        log "Repository content copied to $INSTALL_DIR"
        return 0
    else
        log_error "Failed to extract repository ZIP file"
        return 1
    fi
}

# Set correct permissions
set_permissions() {
    print_section "Setting File Permissions"
    
    # Check if user and group exist
    if getent passwd $USER > /dev/null && getent group $GROUP > /dev/null; then
        log "Setting ownership to $USER:$GROUP..."
        
        # Set ownership recursively for all relevant directories
        chown -R $USER:$GROUP $INSTALL_DIR
        chown -R $USER:$GROUP $LOG_DIR
        chown -R $USER:$GROUP $CONFIG_DIR
        
        log "Ownership set to $USER:$GROUP"
    else
        log_error "User $USER or group $GROUP not found, skipping ownership changes"
    fi
    
    # Make scripts executable
    log "Making scripts executable..."
    find $INSTALL_DIR/scripts -name "*.sh" -exec chmod +x {} \; 2>/dev/null || log_warning "No shell scripts found to make executable"
    
    # Set executable permissions for main application
    if [ -f "$INSTALL_DIR/app.py" ]; then
        chmod +x $INSTALL_DIR/app.py
        log "Set executable permission for app.py"
    else
        log_warning "app.py not found in $INSTALL_DIR"
    fi
    
    # Set correct permissions for configuration directory
    chmod 750 $CONFIG_DIR
    
    # Set permissions for SSH keys if they exist
    if [ -d "/home/$USER/.ssh" ]; then
        log "Setting SSH directory permissions..."
        chown -R $USER:$GROUP /home/$USER/.ssh
        chmod 700 /home/$USER/.ssh
        
        if [ -f "/home/$USER/.ssh/id_rsa" ]; then
            chmod 600 /home/$USER/.ssh/id_rsa
        fi
        
        if [ -f "/home/$USER/.ssh/id_rsa.pub" ]; then
            chmod 644 /home/$USER/.ssh/id_rsa.pub
        fi
    fi
    
    # Set special permissions for specific directories if they exist
    for dir in "$INSTALL_DIR/sequences" "$INSTALL_DIR/src/plugins"; do
        if [ -d "$dir" ]; then
            log "Setting permissions for $dir"
            chmod -R 750 "$dir"
            chown -R $USER:$GROUP "$dir"
        fi
    done
}

# Create systemd service with improved dependencies and security
create_service() {
    print_section "Setting Up System Service"
    
    log "Creating systemd service..."
    
    cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=NetScout-Pi Network Diagnostics System
Documentation=https://github.com/raf181/NetScout-Pi
After=network.target avahi-daemon.service dnsmasq.service hostapd.service
Wants=avahi-daemon.service dnsmasq.service hostapd.service

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/app.py
Restart=on-failure
RestartSec=10
StandardOutput=append:$LOG_DIR/service.log
StandardError=append:$LOG_DIR/service-error.log

# Security enhancements
PrivateTmp=true
ProtectHome=read-only
ProtectSystem=full
NoNewPrivileges=true
PrivateDevices=true

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd manager
    log "Reloading systemd manager..."
    systemctl daemon-reload
    
    # Enable service to start at boot
    log "Enabling service to start at boot..."
    systemctl enable $SERVICE_NAME
    
    log "Service configuration completed"
}

# Configure WiFi access point with interface detection
configure_wifi_ap() {
    print_section "Configuring WiFi Access Point"
    
    # Unblock WiFi
    log "Unblocking WiFi..."
    rfkill unblock wifi 2>/dev/null || log "WiFi unblock not needed or rfkill not available"
    
    # Detect WiFi interface
    log "Detecting WiFi interface..."
    WIFI_INTERFACE="wlan0"  # Default
    
    if ! ip link show $WIFI_INTERFACE &>/dev/null; then
        log_warning "Default interface $WIFI_INTERFACE not found, looking for alternatives..."
        
        # Try to find a wireless interface
        ALTERNATIVE_IF=$(ip link | grep -i "wlan" | cut -d: -f2 | tr -d ' ' | head -n1)
        
        if [ -n "$ALTERNATIVE_IF" ]; then
            WIFI_INTERFACE="$ALTERNATIVE_IF"
            log "Found alternative wireless interface: $WIFI_INTERFACE"
        else
            log_warning "No wireless interface found. WiFi AP configuration may not work."
        fi
    else
        log "Using wireless interface: $WIFI_INTERFACE"
    fi
    
    # Set country code if possible
    log "Setting WiFi country code..."
    if command -v raspi-config >/dev/null 2>&1; then
        # Default to US, but can be customized
        COUNTRY=${WIFI_COUNTRY:-"US"}
        raspi-config nonint do_wifi_country $COUNTRY
        log "Country code set to $COUNTRY using raspi-config"
    else
        # Manually set country code
        if [ -f /etc/wpa_supplicant/wpa_supplicant.conf ]; then
            if ! grep -q "country=" /etc/wpa_supplicant/wpa_supplicant.conf; then
                sed -i '1s/^/country=US\n/' /etc/wpa_supplicant/wpa_supplicant.conf
                log "Country code set to US in wpa_supplicant.conf"
            else
                log "Country code already set in wpa_supplicant.conf"
            fi
        else
            # Create a basic wpa_supplicant.conf if it doesn't exist
            mkdir -p /etc/wpa_supplicant
            echo "country=US" > /etc/wpa_supplicant/wpa_supplicant.conf
            log "Created basic wpa_supplicant.conf with country code US"
        fi
    fi
    
    # Configure hostapd for access point
    log "Configuring hostapd..."
    mkdir -p /etc/hostapd
    cat > /etc/hostapd/hostapd.conf << EOF
# NetScout-Pi WiFi Access Point Configuration
interface=$WIFI_INTERFACE
driver=nl80211
ssid=$WIFI_SSID
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$WIFI_PASSWORD
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
country_code=US
ieee80211n=1
EOF
    
    # Unmask and enable hostapd
    log "Enabling hostapd service..."
    systemctl unmask hostapd
    systemctl enable hostapd
    
    # Configure dnsmasq for DHCP and DNS
    log "Configuring dnsmasq..."
    mkdir -p /etc/dnsmasq.d
    cat > /etc/dnsmasq.conf << EOF
# NetScout-Pi DHCP and DNS Configuration
interface=$WIFI_INTERFACE
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=local
address=/netscout.local/192.168.4.1
bogus-priv
domain-needed
expand-hosts
local=/local/
listen-address=127.0.0.1
listen-address=192.168.4.1
server=8.8.8.8
server=8.8.4.4
EOF
    
    # Enable dnsmasq
    log "Enabling dnsmasq service..."
    systemctl enable dnsmasq
    
    # Configure network based on available system tools
    log "Configuring network interfaces..."
    if command -v dhcpcd >/dev/null 2>&1 || [ -f /etc/dhcpcd.conf ]; then
        log "Using dhcpcd for network configuration..."
        cat > /etc/dhcpcd.conf << EOF
# NetScout-Pi network configuration

# Default behavior for all interfaces
interface *
allowinterfaces $WIFI_INTERFACE eth0 lo
option rapid_commit
option domain_name_servers, 8.8.8.8, 8.8.4.4
require dhcp_server_identifier
slaac private

# Configure $WIFI_INTERFACE for admin access
interface $WIFI_INTERFACE
static ip_address=192.168.4.1/24
nohook wpa_supplicant
EOF
    elif [ -d /etc/NetworkManager ]; then
        log "Using NetworkManager for network configuration..."
        mkdir -p /etc/NetworkManager/system-connections
        cat > /etc/NetworkManager/system-connections/NetScout.nmconnection << EOF
[connection]
id=NetScout
type=wifi
interface-name=$WIFI_INTERFACE
autoconnect=true
permissions=

[wifi]
mode=ap
ssid=$WIFI_SSID

[ipv4]
method=shared
address1=192.168.4.1/24

[ipv6]
method=disabled

[proxy]
EOF
        chmod 600 /etc/NetworkManager/system-connections/NetScout.nmconnection
        systemctl restart NetworkManager || log_warning "Failed to restart NetworkManager"
    else
        log_warning "Could not find dhcpcd or NetworkManager, using direct interface configuration"
        ip link set $WIFI_INTERFACE up 2>/dev/null || log_warning "Failed to bring up $WIFI_INTERFACE"
        ip addr add 192.168.4.1/24 dev $WIFI_INTERFACE 2>/dev/null || log_warning "Failed to set IP on $WIFI_INTERFACE"
    fi
    
    log "WiFi access point configuration completed"
}

# Fix locale issues with CPU protection
fix_locale() {
    print_section "Fixing Locale Issues"
    
    # First check if localedef is using too much CPU
    log "Checking for high CPU usage by localedef..."
    LOCALEDEF_PID=$(pgrep localedef)
    if [ -n "$LOCALEDEF_PID" ]; then
        # Check CPU usage
        if command -v ps >/dev/null 2>&1; then
            CPU_USAGE=$(ps -p $LOCALEDEF_PID -o %cpu | tail -n 1 | tr -d ' ')
            if [ -n "$CPU_USAGE" ] && [ "${CPU_USAGE%.*}" -gt 50 ]; then
                log_warning "localedef process is using ${CPU_USAGE}% CPU, terminating it"
                kill -9 $LOCALEDEF_PID 2>/dev/null || log_warning "Failed to kill localedef process"
            fi
        else
            log_warning "Cannot check CPU usage, terminating localedef as precaution"
            kill -9 $LOCALEDEF_PID 2>/dev/null || true
        fi
    else
        log "No localedef process running"
    fi
    
    # Set default locale without regenerating (fast and safe)
    log "Setting default locale..."
    mkdir -p /etc/default
    echo 'LANG="en_US.UTF-8"' > /etc/default/locale
    echo 'LC_ALL="en_US.UTF-8"' >> /etc/default/locale
    export LANG=en_US.UTF-8
    export LC_ALL=en_US.UTF-8
    
    # Check if the locale exists already
    if locale -a 2>/dev/null | grep -q "en_US.utf8"; then
        log "Locale en_US.UTF-8 already exists, skipping generation"
    else
        log "Locale en_US.UTF-8 not found, generating..."
        
        # Update locale.gen file
        if [ -f /etc/locale.gen ]; then
            sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
            log "Updated locale.gen to enable en_US.UTF-8"
            
            # Generate locale with timeout to prevent CPU overload
            log "Generating locale with timeout protection..."
            timeout 15s locale-gen || log_warning "Locale generation timed out or failed"
        else
            log_warning "locale.gen file not found, cannot generate locale"
        fi
    fi
    
    log "Locale configuration completed"
}

# Create default configuration with dynamic values
create_default_config() {
    print_section "Creating Default Configuration"
    
    if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        log "Creating new default configuration file..."
        
        # Determine preferred network interface for monitoring
        MONITOR_INTERFACE="eth0"
        if ! ip link show $MONITOR_INTERFACE &>/dev/null; then
            MONITOR_INTERFACE=$(ip -o link show | grep -v "lo\|wlan" | head -n 1 | cut -d: -f2 | tr -d ' ')
            [ -z "$MONITOR_INTERFACE" ] && MONITOR_INTERFACE="eth0"  # Fallback
        fi
        
        cat > $CONFIG_DIR/config.yaml << EOF
# NetScout-Pi - Default Configuration
# Auto-generated by unified installer on $(date)

network:
  interface: $MONITOR_INTERFACE
  poll_interval: 5
  auto_run_on_connect: true
  default_plugins:
    - ip_info
    - ping_test
    - arp_scan
  monitor_method: poll
  ping_targets:
    - 8.8.8.8
    - 1.1.1.1

security:
  allow_eth0_access: false
  ssh_keypair_gen: true
  failed_login_limit: 5
  session_expiry_days: 30
  enable_api_key: true

web:
  port: 80
  host: 0.0.0.0
  session_timeout: 3600
  auth_required: true
  enable_https: false
  # https_cert: /etc/netprobe/cert.pem
  # https_key: /etc/netprobe/key.pem

logging:
  directory: $LOG_DIR
  level: INFO
  max_logs: 100
  rotation_size_mb: 10
  retention_days: 30

plugins:
  allowed_install: true
  auto_update: false
  custom_dir: $INSTALL_DIR/src/plugins
EOF
        
        # Set proper permissions
        chmod 640 $CONFIG_DIR/config.yaml
        chown $USER:$GROUP $CONFIG_DIR/config.yaml
        
        log "Default configuration created"
    else
        log "Configuration file already exists, preserving"
    fi
}

# Set up hostname and mDNS
configure_hostname() {
    print_section "Configuring Hostname and Network Discovery"
    
    HOSTNAME="netscout"
    log "Setting hostname to $HOSTNAME..."
    
    # Set hostname in multiple ways for compatibility
    echo "$HOSTNAME" > /etc/hostname
    hostname "$HOSTNAME"
    if command -v hostnamectl >/dev/null 2>&1; then
        hostnamectl set-hostname "$HOSTNAME"
        log "Hostname set using hostnamectl"
    else
        log "hostnamectl not available, using alternative method"
    fi
    
    # Update hosts file
    log "Updating hosts file..."
    if grep -q "127.0.1.1" /etc/hosts; then
        # Replace existing entry
        sed -i "s/127.0.1.1.*/127.0.1.1\t$HOSTNAME/" /etc/hosts
        log "Updated existing 127.0.1.1 entry in hosts file"
    else
        # Add new entry
        echo "127.0.1.1\t$HOSTNAME" >> /etc/hosts
        log "Added new 127.0.1.1 entry to hosts file"
    fi
    
    # Set up mDNS for network discovery
    log "Setting up mDNS for $HOSTNAME.local..."
    apt-get install -y avahi-daemon
    
    # Configure Avahi for better compatibility
    if [ -f /etc/avahi/avahi-daemon.conf ]; then
        log "Configuring Avahi daemon..."
        sed -i 's/#host-name=.*/host-name='$HOSTNAME'/' /etc/avahi/avahi-daemon.conf
        sed -i 's/#domain-name=.*/domain-name=local/' /etc/avahi/avahi-daemon.conf
        sed -i 's/#publish-hinfo=.*/publish-hinfo=yes/' /etc/avahi/avahi-daemon.conf
        sed -i 's/#publish-workstation=.*/publish-workstation=yes/' /etc/avahi/avahi-daemon.conf
        log "Avahi configuration updated"
    fi
    
    # Enable and restart Avahi
    systemctl enable avahi-daemon
    systemctl restart avahi-daemon || log_warning "Failed to restart avahi-daemon"
    
    log "Hostname and mDNS configuration completed"
}

# Install action with better error handling
install() {
    print_section "Starting NetScout-Pi Installation"
    log "Starting full NetScout-Pi installation..."
    
    # Create directories first
    create_directories || {
        log_error "Failed to create required directories"
        exit 1
    }
    
    # Download repository
    download_repo || {
        log_error "Failed to download repository"
        exit 1
    }
    
    # Install dependencies
    install_dependencies || {
        log_warning "Some dependencies could not be installed, continuing anyway"
    }
    
    # Set permissions
    set_permissions || {
        log_warning "Failed to set some permissions, continuing anyway"
    }
    
    # Create service
    create_service || {
        log_error "Failed to create system service"
        exit 1
    }
    
    # Configure WiFi access point
    configure_wifi_ap || {
        log_warning "WiFi access point configuration may be incomplete"
    }
    
    # Fix locale issues
    fix_locale || {
        log_warning "Locale configuration may be incomplete"
    }
    
    # Create default configuration
    create_default_config || {
        log_warning "Default configuration may be incomplete"
    }
    
    # Configure hostname
    configure_hostname || {
        log_warning "Hostname configuration may be incomplete"
    }
    
    # Set up first boot script if needed
    setup_first_boot || {
        log_warning "First boot setup may be incomplete"
    }
    
    # Start services
    log "Starting services..."
    systemctl restart dnsmasq || log_warning "Failed to restart dnsmasq"
    systemctl restart hostapd || log_warning "Failed to restart hostapd"
    systemctl start $SERVICE_NAME || log_warning "Failed to start $SERVICE_NAME"
    
    # Final verification
    verify_installation
    
    print_section "Installation Summary"
    echo "✅ NetScout-Pi has been successfully installed!"
    echo
    echo "📋 Installation Details:"
    echo "   - Installation directory: $INSTALL_DIR"
    echo "   - Log directory: $LOG_DIR"
    echo "   - Configuration: $CONFIG_DIR/config.yaml"
    echo "   - Service name: $SERVICE_NAME"
    echo "   - Running as user: $USER"
    echo
    echo "🌐 Access Information:"
    echo "   - Dashboard URL: http://netscout.local"
    echo "   - Alternative URL: http://192.168.4.1"
    echo "   - WiFi Access Point: $WIFI_SSID"
    echo "   - WiFi Password: $WIFI_PASSWORD"
    echo
    echo "🔧 Management Commands:"
    echo "   - Check service status: systemctl status $SERVICE_NAME"
    echo "   - View logs: journalctl -u $SERVICE_NAME"
    echo "   - Fix issues: sudo bash $INSTALL_DIR/scripts/unified_installer.sh fix"
    echo "   - Update: sudo bash $INSTALL_DIR/scripts/unified_installer.sh update"
    echo
    
    log "Installation completed successfully"
}

# Set up first boot script
setup_first_boot() {
    log "Setting up first boot script..."
    
    # Copy first boot script to appropriate location
    if [ -f "$INSTALL_DIR/scripts/first_boot.sh" ]; then
        cp "$INSTALL_DIR/scripts/first_boot.sh" "$CONFIG_DIR/"
        chmod +x "$CONFIG_DIR/first_boot.sh"
        
        # Add first boot script to rc.local if it exists
        if [ -f /etc/rc.local ]; then
            # Remove any existing entries
            sed -i '/netprobe/d' /etc/rc.local
            sed -i '/netscout/d' /etc/rc.local
            # Add before exit 0
            sed -i '/exit 0/i'"$CONFIG_DIR"'/first_boot.sh &' /etc/rc.local
            log "Added first boot script to rc.local"
        else
            # Create rc.local if it doesn't exist
            cat > /etc/rc.local << EOF
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# NetScout-Pi additions
$CONFIG_DIR/first_boot.sh &

exit 0
EOF
            chmod +x /etc/rc.local
            log "Created rc.local with first boot script"
        fi
    else
        log_warning "first_boot.sh not found in $INSTALL_DIR/scripts"
    fi
}

# Verify installation
verify_installation() {
    log "Verifying installation..."
    
    local errors=0
    
    # Check if directories exist
    for dir in "$INSTALL_DIR" "$LOG_DIR" "$CONFIG_DIR"; do
        if [ ! -d "$dir" ]; then
            log_error "Directory $dir does not exist"
            errors=$((errors+1))
        fi
    done
    
    # Check if app.py exists and is executable
    if [ ! -f "$INSTALL_DIR/app.py" ]; then
        log_error "Main application file app.py not found"
        errors=$((errors+1))
    elif [ ! -x "$INSTALL_DIR/app.py" ]; then
        log_warning "app.py is not executable"
    fi
    
    # Check if service is enabled
    if ! systemctl is-enabled $SERVICE_NAME &>/dev/null; then
        log_error "Service $SERVICE_NAME is not enabled"
        errors=$((errors+1))
    fi
    
    if [ $errors -gt 0 ]; then
        log_warning "Verification found $errors issues that may need attention"
    else
        log "Verification completed successfully"
    fi
}

# Update action with better backup and version handling
update() {
    print_section "Starting NetScout-Pi Update"
    
    # Check if NetScout-Pi is installed
    if [ ! -d "$INSTALL_DIR" ]; then
        log_error "NetScout-Pi not found in $INSTALL_DIR"
        echo "NetScout-Pi does not appear to be installed. Run the installer first."
        exit 1
    fi
    
    # Get current version
    log "Checking current version..."
    CURRENT_VERSION=$(cat $INSTALL_DIR/VERSION 2>/dev/null || echo "0.0.0")
    
    # Download repository to temp directory to check version
    log "Downloading repository to check for updates..."
    cd $TMP_DIR
    
    if ! wget -q $ZIP_URL -O netscout.zip; then
        log_error "Failed to download repository"
        exit 1
    fi
    
    if ! unzip -q netscout.zip; then
        log_error "Failed to extract repository"
        exit 1
    fi
    
    REMOTE_VERSION=$(cat NetScout-Pi-main/VERSION 2>/dev/null || echo "0.0.0")
    
    log "Current version: $CURRENT_VERSION"
    log "Remote version: $REMOTE_VERSION"
    
    # Check if update is needed
    if [ "$CURRENT_VERSION" == "$REMOTE_VERSION" ]; then
        log "No update needed. Exiting."
        echo "NetScout-Pi is already at the latest version ($CURRENT_VERSION)."
        rm -rf $TMP_DIR
        return 0
    fi
    
    print_section "Update Available: $CURRENT_VERSION → $REMOTE_VERSION"
    log "Update available. Proceeding with update..."
    
    # Backup current installation
    log "Creating backup..."
    BACKUP_NAME="netscout_backup_$(date +%Y%m%d_%H%M%S)"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    mkdir -p $BACKUP_PATH
    
    if ! cp -r $INSTALL_DIR/* $BACKUP_PATH/; then
        log_warning "Backup may be incomplete"
    else
        log "Backup created at $BACKUP_PATH"
    fi
    
    # Stop service
    log "Stopping NetScout-Pi service..."
    systemctl stop $SERVICE_NAME || log_warning "Failed to stop service cleanly"
    
    # Update files while preserving configuration
    log "Updating files..."
    
    # Save list of custom plugins before update
    if [ -d "$INSTALL_DIR/src/plugins" ]; then
        CUSTOM_PLUGINS=$(find "$INSTALL_DIR/src/plugins" -type f -name "*.py" | grep -v "ip_info\|ping_test\|arp_scan\|traceroute\|speed_test\|port_scan\|vlan_detector\|packet_capture")
    fi
    
    # Copy new files, preserving config
    rsync -av --exclude '.git' --exclude 'config.yaml' NetScout-Pi-main/ $INSTALL_DIR/ || {
        log_error "Failed to update files"
        log "Attempting to restore from backup..."
        rsync -av $BACKUP_PATH/ $INSTALL_DIR/
        systemctl start $SERVICE_NAME
        log_error "Update failed, restored from backup"
        exit 1
    }
    
    # Restore custom plugins
    if [ -n "$CUSTOM_PLUGINS" ]; then
        log "Restoring custom plugins..."
        for plugin in $CUSTOM_PLUGINS; do
            plugin_name=$(basename "$plugin")
            if [ -f "$BACKUP_PATH/src/plugins/$plugin_name" ] && [ ! -f "$INSTALL_DIR/src/plugins/$plugin_name" ]; then
                cp "$BACKUP_PATH/src/plugins/$plugin_name" "$INSTALL_DIR/src/plugins/"
                log "Restored custom plugin: $plugin_name"
            fi
        done
    fi
    
    # Update dependencies
    log "Updating dependencies..."
    install_dependencies
    
    # Fix permissions
    log "Updating permissions..."
    set_permissions
    
    # Restart service
    log "Starting NetScout-Pi service..."
    systemctl start $SERVICE_NAME || log_warning "Failed to start service"
    
    print_section "Update Complete"
    echo "✅ NetScout-Pi has been updated from $CURRENT_VERSION to $REMOTE_VERSION"
    echo 
    echo "🔄 Update Details:"
    echo "   - Backup created: $BACKUP_PATH"
    echo "   - Configuration preserved: $CONFIG_DIR/config.yaml"
    echo "   - Custom plugins preserved"
    echo
    echo "🔧 Management Commands:"
    echo "   - Check service status: systemctl status $SERVICE_NAME"
    echo "   - View logs: journalctl -u $SERVICE_NAME"
    echo "   - Revert to previous version: sudo cp -r $BACKUP_PATH/* $INSTALL_DIR/"
    echo
    
    log "Update completed successfully"
}

# Fix action with comprehensive repairs
fix() {
    print_section "Starting NetScout-Pi Fix Routine"
    
    # Check if NetScout-Pi is installed
    if [ ! -d "$INSTALL_DIR" ]; then
        log_warning "NetScout-Pi not found in $INSTALL_DIR, will attempt to install"
        install
        return
    fi
    
    log "Diagnosing issues..."
    
    # First stop the service to avoid conflicts
    log "Stopping service for maintenance..."
    systemctl stop $SERVICE_NAME 2>/dev/null || log_warning "Service not running or failed to stop"
    
    # Fix directory permissions
    log "Fixing directory permissions..."
    create_directories
    set_permissions
    
    # Fix WiFi and network issues
    log "Fixing network configuration..."
    configure_wifi_ap
    
    # Fix hostname and DNS issues
    log "Fixing hostname and DNS..."
    configure_hostname
    
    # Fix locale issues
    log "Fixing locale settings..."
    fix_locale
    
    # Fix service configuration
    log "Fixing service configuration..."
    create_service
    
    # Check configuration file
    log "Checking configuration file..."
    if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        log_warning "Configuration file missing, creating default"
        create_default_config
    fi
    
    # Check for missing files and attempt to restore
    log "Checking for missing files..."
    if [ ! -f "$INSTALL_DIR/app.py" ]; then
        log_warning "Main application file missing, downloading repository"
        download_repo
        set_permissions
    fi
    
    # Check and fix Python dependencies
    log "Checking Python dependencies..."
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        log "Reinstalling Python dependencies..."
        install_dependencies
    fi
    
    # Restart system services
    log "Restarting system services..."
    systemctl restart avahi-daemon 2>/dev/null || log_warning "Failed to restart avahi-daemon"
    systemctl restart dnsmasq 2>/dev/null || log_warning "Failed to restart dnsmasq"
    systemctl restart hostapd 2>/dev/null || log_warning "Failed to restart hostapd"
    
    # Start NetScout-Pi service
    log "Starting NetScout-Pi service..."
    systemctl start $SERVICE_NAME || log_warning "Failed to start service"
    
    # Check service status
    log "Checking service status..."
    if systemctl is-active --quiet $SERVICE_NAME; then
        log "Service is running correctly"
    else
        log_warning "Service failed to start, checking logs"
        journalctl -u $SERVICE_NAME -n 20 >> $LOG_FILE
    fi
    
    print_section "Fix Routine Complete"
    echo "✅ NetScout-Pi fix routine has been completed"
    echo
    echo "🔧 The following items were checked and fixed:"
    echo "   - Directory permissions"
    echo "   - WiFi access point configuration"
    echo "   - Network service configuration"
    echo "   - Hostname and DNS settings"
    echo "   - Locale configuration"
    echo "   - Service configuration"
    echo "   - Python dependencies"
    echo
    echo "📊 Current Status:"
    echo "   - Service status: $(systemctl is-active $SERVICE_NAME)"
    echo "   - WiFi status: $(rfkill list wifi 2>/dev/null || echo 'Unknown')"
    echo "   - Hostname: $(hostname)"
    echo
    echo "🔄 You should reboot your system to ensure all changes take effect."
    echo "    Would you like to reboot now? (y/N): "
    read -t 30 -n 1 -r REPLY || REPLY="n"
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "User requested reboot"
        echo "System will reboot in 5 seconds..."
        sleep 5
        reboot
    else
        log "User skipped reboot"
        echo "Please reboot manually when convenient."
    fi
    
    log "Fix routine completed successfully"
}

# Reset action with better confirmation and backup
reset() {
    print_section "Reset NetScout-Pi to Factory Defaults"
    
    # Check if NetScout-Pi is installed
    if [ ! -d "$INSTALL_DIR" ]; then
        log_error "NetScout-Pi not found in $INSTALL_DIR"
        echo "NetScout-Pi does not appear to be installed. Run the installer first."
        exit 1
    fi
    
    # Multiple confirmation prompts to prevent accidental reset
    echo "⚠️ WARNING: This will reset NetScout-Pi to factory defaults."
    echo "    All custom plugins, sequences, and settings will be lost."
    echo
    echo "The following will be reset:"
    echo "   - Configuration files"
    echo "   - Custom plugins"
    echo "   - Log files"
    echo "   - Sequence definitions"
    echo "   - User preferences"
    echo
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM
    
    if [[ ! "$CONFIRM" =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Reset cancelled by user"
        echo "Reset cancelled."
        return 0
    fi
    
    # Second confirmation
    echo
    echo "⚠️ FINAL WARNING: This action cannot be undone!"
    read -p "Type 'RESET' to confirm: " FINAL_CONFIRM
    
    if [ "$FINAL_CONFIRM" != "RESET" ]; then
        log "Reset cancelled by user at final confirmation"
        echo "Reset cancelled."
        return 0
    fi
    
    log "Starting reset to factory defaults..."
    
    # Create backup before reset
    log "Creating backup before reset..."
    BACKUP_NAME="netscout_pre_reset_$(date +%Y%m%d_%H%M%S)"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    mkdir -p $BACKUP_PATH
    
    if cp -r $INSTALL_DIR/* $BACKUP_PATH/; then
        log "Backup created at $BACKUP_PATH"
        echo "Backup created at $BACKUP_PATH"
    else
        log_warning "Backup may be incomplete"
    fi
    
    # Stop service
    log "Stopping NetScout-Pi service..."
    systemctl stop $SERVICE_NAME || log_warning "Failed to stop service cleanly"
    
    # Reset configuration
    log "Resetting configuration..."
    if [ -d "$CONFIG_DIR" ]; then
        rm -f $CONFIG_DIR/config.yaml
    fi
    
    # Reset logs
    log "Clearing logs..."
    find $LOG_DIR -type f -name "*.log" -exec rm {} \; 2>/dev/null
    find $LOG_DIR -type f -name "*.json" -exec rm {} \; 2>/dev/null
    
    # Reset plugins
    log "Resetting custom plugins..."
    PLUGINS_DIR="$INSTALL_DIR/src/plugins"
    if [ -d "$PLUGINS_DIR" ]; then
        for plugin in $PLUGINS_DIR/*; do
            # Check if it's a built-in plugin
            filename=$(basename "$plugin")
            if [[ ! "$filename" =~ ^(ip_info|ping_test|arp_scan|traceroute|speed_test|port_scan|vlan_detector|packet_capture)\.py$ ]]; then
                if [ -f "$plugin" ]; then
                    log "Removing custom plugin: $filename"
                    rm "$plugin"
                fi
            fi
        done
    else
        log_warning "Plugins directory not found"
    fi
    
    # Reset sequences
    log "Clearing sequences..."
    if [ -d "$INSTALL_DIR/sequences" ]; then
        rm -f $INSTALL_DIR/sequences/*.json
    fi
    
    # Reset first boot flag to trigger setup on next boot
    log "Resetting first boot flag..."
    rm -f $INSTALL_DIR/.first_boot_completed
    
    # Recreate default configuration
    log "Creating new default configuration..."
    create_default_config
    
    # Fix permissions
    log "Resetting permissions..."
    set_permissions
    
    # Start service
    log "Starting NetScout-Pi service..."
    systemctl start $SERVICE_NAME || log_warning "Failed to start service"
    
    print_section "Reset Complete"
    echo "✅ NetScout-Pi has been reset to factory defaults"
    echo
    echo "🔄 The system will reboot in 5 seconds to complete the reset process..."
    echo "    Press Ctrl+C to cancel reboot"
    
    log "Reset to factory defaults completed"
    
    # Set a countdown for reboot
    for i in {5..1}; do
        echo -ne "\rRebooting in $i seconds... "
        sleep 1
    done
    echo -e "\rRebooting now!            "
    
    reboot
}

# Clean action to remove NetScout-Pi completely
clean() {
    print_section "Complete Removal of NetScout-Pi"
    
    # Check if NetScout-Pi is installed
    if [ ! -d "$INSTALL_DIR" ] && [ ! -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
        log_warning "NetScout-Pi does not appear to be installed"
        echo "NetScout-Pi does not appear to be installed."
        return 0
    fi
    
    # Multiple confirmation prompts to prevent accidental removal
    echo "⚠️ WARNING: This will completely remove NetScout-Pi from your system."
    echo "    All files, configurations, and data will be permanently deleted."
    echo
    read -p "Are you sure you want to continue? (yes/no): " CONFIRM
    
    if [[ ! "$CONFIRM" =~ ^[Yy][Ee][Ss]$ ]]; then
        log "Clean cancelled by user"
        echo "Operation cancelled."
        return 0
    fi
    
    # Second confirmation
    echo
    echo "⚠️ FINAL WARNING: This action cannot be undone!"
    read -p "Type 'REMOVE' to confirm: " FINAL_CONFIRM
    
    if [ "$FINAL_CONFIRM" != "REMOVE" ]; then
        log "Clean cancelled by user at final confirmation"
        echo "Operation cancelled."
        return 0
    fi
    
    log "Starting complete removal of NetScout-Pi..."
    
    # Create backup before removal
    log "Creating backup before removal..."
    BACKUP_NAME="netscout_pre_removal_$(date +%Y%m%d_%H%M%S)"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    mkdir -p $BACKUP_PATH
    
    if [ -d "$INSTALL_DIR" ]; then
        if cp -r $INSTALL_DIR/* $BACKUP_PATH/; then
            log "Backup created at $BACKUP_PATH"
            echo "Backup created at $BACKUP_PATH"
        else
            log_warning "Backup may be incomplete"
        fi
    fi
    
    # Stop and disable service
    log "Stopping and disabling service..."
    systemctl stop $SERVICE_NAME 2>/dev/null || true
    systemctl disable $SERVICE_NAME 2>/dev/null || true
    
    # Remove service file
    log "Removing service configuration..."
    rm -f /etc/systemd/system/$SERVICE_NAME.service
    systemctl daemon-reload
    
    # Remove configuration files
    log "Removing configuration files..."
    rm -rf $CONFIG_DIR
    
    # Remove installation directory
    log "Removing installation directory..."
    rm -rf $INSTALL_DIR
    
    # Remove log directory
    log "Removing log files..."
    rm -rf $LOG_DIR
    
    # Cleanup network configuration
    log "Cleaning up network configuration..."
    
    # Clean hostapd configuration
    if [ -f /etc/hostapd/hostapd.conf ]; then
        if grep -q "NetScout\|NetProbe" /etc/hostapd/hostapd.conf; then
            rm -f /etc/hostapd/hostapd.conf
            log "Removed hostapd configuration"
        fi
    fi
    
    # Clean dnsmasq configuration
    if [ -f /etc/dnsmasq.conf ]; then
        if grep -q "netscout\|netprobe" /etc/dnsmasq.conf; then
            rm -f /etc/dnsmasq.conf
            log "Removed dnsmasq configuration"
        fi
    fi
    
    # Remove from rc.local if present
    if [ -f /etc/rc.local ]; then
        if grep -q "netscout\|netprobe" /etc/rc.local; then
            sed -i '/netscout/d' /etc/rc.local
            sed -i '/netprobe/d' /etc/rc.local
            log "Removed from rc.local"
        fi
    fi
    
    # Remove from hosts file
    if grep -q "netscout\|netprobe" /etc/hosts; then
        sed -i '/netscout/d' /etc/hosts
        sed -i '/netprobe/d' /etc/hosts
        log "Removed from hosts file"
    fi
    
    print_section "Removal Complete"
    echo "✅ NetScout-Pi has been completely removed from your system"
    echo
    echo "🔄 A backup of your configuration has been created at:"
    echo "    $BACKUP_PATH"
    echo
    echo "⚠️ The following services were not removed as they may be used by other applications:"
    echo "   - hostapd (WiFi access point)"
    echo "   - dnsmasq (DHCP server)"
    echo "   - avahi-daemon (mDNS)"
    echo
    echo "🔄 You should reboot your system to complete the cleanup process."
    echo "    Would you like to reboot now? (y/N): "
    read -t 30 -n 1 -r REPLY || REPLY="n"
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "User requested reboot after removal"
        echo "System will reboot in 5 seconds..."
        sleep 5
        reboot
    else
        log "User skipped reboot after removal"
        echo "Please reboot manually when convenient."
    fi
    
    log "Complete removal process finished"
}

# Display version information
show_version() {
    echo "NetScout-Pi Unified Installer"
    echo "Version: $VERSION"
    echo "https://github.com/raf181/NetScout-Pi"
    echo
    
    if [ -f "$INSTALL_DIR/VERSION" ]; then
        INSTALLED_VERSION=$(cat $INSTALL_DIR/VERSION)
        echo "Installed NetScout-Pi version: $INSTALLED_VERSION"
    else
        echo "NetScout-Pi not installed or version information missing"
    fi
}

# Show help message
show_help() {
    echo "NetScout-Pi Unified Installer and Maintenance Script"
    echo "======================================================"
    echo
    echo "Usage: sudo bash $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  install    Install NetScout-Pi (default if no command specified)"
    echo "  update     Update an existing NetScout-Pi installation"
    echo "  fix        Fix common issues with NetScout-Pi"
    echo "  reset      Reset NetScout-Pi to factory defaults"
    echo "  clean      Completely remove NetScout-Pi from the system"
    echo "  version    Display version information"
    echo "  help       Show this help message"
    echo
    echo "Examples:"
    echo "  sudo bash $0                  # Install NetScout-Pi"
    echo "  sudo bash $0 update           # Update NetScout-Pi"
    echo "  sudo bash $0 fix              # Fix NetScout-Pi installation"
    echo
    echo "For more information, visit: https://github.com/raf181/NetScout-Pi"
}

# Main function
main() {
    # Create log directory if it doesn't exist
    mkdir -p $LOG_DIR
    
    # Check if running as root
    check_root
    
    # Determine the user
    get_user
    
    # Parse command line arguments
    ACTION="install"  # Default action
    
    if [ $# -gt 0 ]; then
        case "$1" in
            install|update|fix|reset|clean)
                ACTION=$1
                ;;
            version|-v|--version)
                show_version
                exit 0
                ;;
            help|-h|--help)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown action: $1"
                show_help
                exit 1
                ;;
        esac
    fi
    
    # Execute the requested action
    case $ACTION in
        install)
            install
            ;;
        update)
            update
            ;;
        fix)
            fix
            ;;
        reset)
            reset
            ;;
        clean)
            clean
            ;;
    esac
    
    # Clean up
    if [ -d "$TMP_DIR" ]; then
        rm -rf $TMP_DIR
    fi
    
    log "Script execution completed: $ACTION"
}

# Call main function with all arguments
main "$@"
