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

For more details on how to use NetProbe Pi, refer to the [User Manual](USER_MANUAL.md).
