# Installation Guide for NetProbe Pi

This guide will walk you through setting up NetProbe Pi on a Raspberry Pi Zero 2 W or any Debian-based system.

## Prerequisites

- Raspberry Pi Zero 2 W (or any Debian-based system)
- MicroSD card (at least 8GB)
- USB-Ethernet adapter
- Power supply for Raspberry Pi
- Computer with SD card reader
- WiFi network for admin access

## Installation Methods

### Method 1: One-Line Direct Installation (Recommended)

This is the simplest way to install NetProbe Pi. Run the following command on your system:

```bash
curl -sSL https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/direct_install.sh | sudo bash
```

This script will:
1. Download the NetProbe Pi repository
2. Install all required dependencies
3. Set up the service
4. Configure the system for first boot

Once the installation is complete, you can access the web interface at http://netprobe.local or the IP address of your device.

### Method 2: Manual Installation

If you prefer to perform a manual installation or if you're having issues with the one-line installer:
   Default password is `raspberry`

## Step 4: Install NetProbe Pi

### Option 1: Quick Installation (Recommended)

Run the following command to download and install NetProbe Pi directly:

```bash
wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/quick_install.sh -O quick_install.sh && sudo bash quick_install.sh
```

This method:
- Downloads the repository directly as a ZIP file
- Installs all dependencies
- Sets up the service
- Works even if git is not installed
- Automatically adapts to your user account

### Option 2: One-Line Installation

If you prefer the standard installation process:

```bash
wget -q https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/install_oneline.sh -O install_oneline.sh && sudo bash install_oneline.sh
```

### Option 3: Manual Installation

1. Update your system:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. Install Git:
   ```bash
   sudo apt install -y git
   ```

3. Clone the repository:
   ```bash
   git clone https://github.com/raf181/NetScout-Pi.git
   ```

4. Navigate to the repository directory:
   ```bash
   cd NetScout-Pi
   ```

5. Run the installation script:
   ```bash
   sudo bash scripts/install.sh
   ```

## Troubleshooting

### "Authentication failed for GitHub" Error

If you see an error about GitHub authentication when cloning the repository, use the HTTPS URL instead:

```bash
git clone https://github.com/raf181/NetScout-Pi.git
```

Or download the ZIP file directly:

```bash
wget https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip
unzip main.zip
cd NetScout-Pi-main
```

### "Externally Managed Environment" Error

If you encounter an error about "externally-managed-environment" when installing Python packages, the script has been updated to handle this by:

1. Installing packages via apt when possible
2. Using the `--break-system-packages` flag for pip when necessary

If you're still having issues, you can install the packages manually:

```bash
sudo apt install -y python3-flask python3-socketio python3-dotenv python3-click python3-watchdog python3-psutil python3-netifaces python3-yaml python3-jsonschema python3-bcrypt python3-jwt python3-requests python3-paho-mqtt
```

### User Permissions Issues

The installation script automatically detects if the 'pi' user exists and uses the current user if not. If you see permission errors, you can manually set permissions:

```bash
sudo chown -R $(whoami):$(whoami) /opt/netprobe
sudo chown -R $(whoami):$(whoami) /var/log/netprobe
```

### WiFi Not Working

If the NetProbe WiFi access point is not showing up:

1. Check if WiFi is blocked by rfkill:
   ```bash
   sudo rfkill list
   ```

2. Unblock WiFi:
   ```bash
   sudo rfkill unblock wifi
   ```

3. Set your country code for WiFi regulation:
   ```bash
   sudo raspi-config
   ```
   Navigate to "Localisation Options" > "WLAN Country" and select your country.

4. Restart the WiFi services:
   ```bash
   sudo systemctl restart hostapd
   sudo systemctl restart dnsmasq
   ```

### Dashboard Not Accessible

If you can't access the dashboard after installation:

1. Check if the service is running:
   ```bash
   sudo systemctl status netprobe
   ```

2. If the service is not running, start it:
   ```bash
   sudo systemctl start netprobe
   ```

3. Check the logs for any errors:
   ```bash
   sudo journalctl -u netprobe
   ```

4. Verify network configuration:
   ```bash
   ip addr show wlan0
   ```
   The WiFi interface should have IP address 192.168.4.1

### Python Package Installation Issues

If you encounter the "externally-managed-environment" error when installing Python packages, the direct_install.sh script has been updated to handle this by:

1. Installing Python packages via apt-get instead of pip where possible
2. Using `--break-system-packages` flag for essential packages when needed

If you need to install additional Python packages manually, use:
```bash
sudo apt-get install python3-package-name
```
Or if the package is not available in apt:
```bash
sudo pip3 install --break-system-packages package-name
```

### GitHub Authentication Errors

If you're experiencing GitHub authentication errors when cloning the repository, the direct_install.sh script avoids this issue by downloading the ZIP file directly. If you need to clone manually, use:

```bash
git clone https://github.com/raf181/NetScout-Pi.git
```

Or download the ZIP file directly:
```bash
wget https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip
unzip main.zip
```

### Locale Issues and High CPU Usage

If you notice high CPU usage during installation or when running the fix scripts, it might be due to the `localedef` process which generates locale data. This can happen on some systems and cause them to become slow or unresponsive.

To fix this issue:

1. Check if localedef is using high CPU:
   ```bash
   top
   ```
   Look for a process called `localedef` with high CPU usage.

2. Run our dedicated locale fix script:
   ```bash
   curl -sSL https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/fix_locale.sh | sudo bash
   ```

3. If the above doesn't work, manually terminate the localedef process:
   ```bash
   sudo pkill -9 localedef
   ```

4. Set the locale manually without generating it:
   ```bash
   echo 'LANG="en_US.UTF-8"' | sudo tee /etc/default/locale
   export LANG=en_US.UTF-8
   ```

The enhanced autofix_v2.sh script has been updated to prevent locale generation from consuming too much CPU.

## First Boot Configuration

On first boot, NetProbe Pi will:

1. Set the hostname to "netprobe"
2. Configure mDNS for "netprobe.local"
3. Set up WiFi as an access point (SSID: "NetProbe", Password: "netprobe123")
4. Generate SSH keys for secure access
5. Configure network interfaces

## Accessing the Web Interface

After installation and first boot:

1. Connect to the "NetProbe" WiFi network (Password: "netprobe123")
2. Open a web browser and navigate to http://netprobe.local or http://192.168.4.1
3. Set your admin password on first login

## System Management

- Check service status: `sudo systemctl status netprobe`
- View logs: `sudo journalctl -u netprobe`
- Restart service: `sudo systemctl restart netprobe`
- Stop service: `sudo systemctl stop netprobe`

## Additional Information

For more details on how to use NetProbe Pi, refer to the [User Manual](USER_MANUAL.md)

### Quick Fix Script

If you're experiencing issues with your NetProbe Pi installation, we provide an automatic fix script that can resolve most common problems:

```bash
curl -sSL https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/autofix.sh | sudo bash
```

This script will automatically:
- Unblock WiFi
- Configure the WiFi access point
- Fix service permissions
- Restart all necessary services
- Add hostname resolution for netprobe.local

For interactive troubleshooting, you can use our menu-based fix script:

```bash
sudo bash /opt/netprobe/scripts/fix_netprobe.sh
```

## Common Installation Issues

### WiFi Access Point Not Appearing

If your WiFi access point isn't appearing after installation, try the enhanced auto-fix script:

```bash
curl -sSL https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/autofix_v2.sh | sudo bash
```

This improved script handles:
- Systems without dhcpcd (using NetworkManager instead)
- WiFi interface detection issues 
- Locale configuration problems
- Hostname resolution issues

### Dashboard Not Available After Installation

If you've connected to the NetProbe WiFi network but can't access the dashboard:

1. Check if the service is running:
   ```bash
   sudo systemctl status netprobe
   ```

2. If you see errors related to Python packages, install them system-wide:
   ```bash
   sudo apt-get install python3-flask python3-socketio python3-dotenv python3-click
   ```

3. Check the application logs:
   ```bash
   sudo journalctl -u netprobe -n 50
   ```

### Manual Network Configuration

If the automatic setup doesn't work, you can manually configure your wireless interface:

```bash
# Set static IP on your wireless interface
sudo ip addr add 192.168.4.1/24 dev wlan0

# Bring up the interface
sudo ip link set wlan0 up

# Start hostapd and dnsmasq
sudo systemctl restart hostapd
sudo systemctl restart dnsmasq
```

### Issues with "unable to resolve host"

If you see "sudo: unable to resolve host netprobe", fix your /etc/hosts file:

```bash
echo "127.0.1.1 netprobe" | sudo tee -a /etc/hosts
```

### Other Network Issues

To completely reset your network configuration:

```bash
# Restart network-related services
sudo systemctl restart NetworkManager  # If using NetworkManager
sudo systemctl restart networking      # If using traditional networking
sudo systemctl restart hostapd
sudo systemctl restart dnsmasq
```
