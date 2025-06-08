# Installation Guide for NetProbe Pi

This guide will walk you through setting up NetProbe Pi on a Raspberry Pi Zero 2 W.

## Prerequisites

- Raspberry Pi Zero 2 W
- MicroSD card (at least 8GB)
- USB-Ethernet adapter
- Power supply for Raspberry Pi
- Computer with SD card reader
- WiFi network for admin access

## Step 1: Prepare the SD Card

1. Download the latest Raspberry Pi OS Lite from the [Raspberry Pi website](https://www.raspberrypi.org/software/operating-systems/)
2. Flash the OS to your microSD card using the [Raspberry Pi Imager](https://www.raspberrypi.org/software/)
3. After flashing, re-insert the SD card into your computer

## Step 2: Enable SSH and Configure WiFi

1. Create an empty file named `ssh` in the boot partition
2. Create a file named `wpa_supplicant.conf` in the boot partition with the following content:

```
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YOUR_WIFI_NAME"
    psk="YOUR_WIFI_PASSWORD"
    key_mgmt=WPA-PSK
}
```

3. Replace `YOUR_WIFI_NAME` and `YOUR_WIFI_PASSWORD` with your actual WiFi credentials
4. Save the file and eject the SD card safely

## Step 3: Boot and Connect to Raspberry Pi

1. Insert the SD card into your Raspberry Pi Zero 2 W
2. Connect the USB-Ethernet adapter
3. Power on the Raspberry Pi
4. Wait for it to boot and connect to your WiFi network
5. Find the IP address of your Raspberry Pi on your network (using your router's admin panel or a network scanner)
6. Connect to your Raspberry Pi via SSH:
   ```
   ssh pi@<IP_ADDRESS>
   ```
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

2. Install wget and unzip:
   ```bash
   sudo apt install wget unzip -y
   ```

3. Download and extract the NetProbe Pi repository:
   ```bash
   cd /tmp
   wget https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip -O netscout.zip
   unzip netscout.zip
   cd NetScout-Pi-main
   ```

4. Run the installation script:
   ```bash
   sudo ./scripts/install.sh
   ```

5. Follow the prompts to complete the installation

### Direct Installation

For the simplest installation method, run this single command:

```bash
curl -sSL https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/direct_install.sh | sudo bash
```

This command:
1. Downloads the installer script using curl
2. Runs it with sudo permissions
3. Handles the entire installation process automatically

This is the recommended method for most users.

## Step 5: Access the Web Dashboard

After installation completes and the system reboots:

1. The NetProbe Pi will create its own WiFi network
   - SSID: `NetProbe`
   - Password: `netprobe123`

2. Connect your device (laptop, smartphone, tablet) to this WiFi network

3. Open a web browser and navigate to:
   - http://netprobe.local
   - or http://192.168.4.1

4. On first access, you'll be prompted to set an administrator password

5. After setting the password, you'll have full access to the dashboard

## Alternative GitHub Access Methods

If you encounter authentication issues when cloning the repository, you can use one of these methods:

### Method 1: Use HTTPS with a Personal Access Token (PAT)

1. Create a Personal Access Token on GitHub:
   - Go to GitHub → Settings → Developer Settings → Personal Access Tokens
   - Generate a new token with 'repo' scope
   - Copy the token

2. Use the token when cloning:

   ```bash
   git clone https://[USERNAME]:[TOKEN]@github.com/raf181/NetScout-Pi.git
   ```

### Method 2: Use SSH

1. Generate an SSH key:

   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. Add the key to your SSH agent:

   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```

3. Add the SSH key to your GitHub account:
   - Copy the public key: `cat ~/.ssh/id_ed25519.pub`
   - Go to GitHub → Settings → SSH and GPG keys → New SSH key
   - Paste your key and save

4. Clone using SSH:

   ```bash
   git clone git@github.com:raf181/NetScout-Pi.git
   ```

### Method 3: Download ZIP

If you're just looking to install, you can download the ZIP file directly:

   ```bash
   wget https://github.com/raf181/NetScout-Pi/archive/refs/heads/main.zip
   unzip main.zip
   cd NetScout-Pi-main
   ```

## Security Recommendations

1. Change the default SSH password:
   ```
   passwd
   ```

2. Set up SSH key authentication and disable password login
3. Keep your Raspberry Pi OS updated regularly
4. Ensure your WiFi network has strong security (WPA2 or WPA3)

## Troubleshooting

### Installation Issues

1. **Authentication errors when cloning the repository**
   - The installation scripts now use direct ZIP download instead of git clone to avoid authentication issues

2. **"User 'pi' not found" errors**
   - The installation scripts automatically detect and use the current user if 'pi' doesn't exist
   - No action needed - this is handled automatically

3. **Cannot access dashboard after installation**
   - Make sure you're connected to the 'NetProbe' WiFi network
   - Try accessing via IP address (192.168.4.1) if hostname resolution fails
   - Check if the service is running: `sudo systemctl status netprobe`
   - Check logs: `sudo journalctl -u netprobe`

4. **WiFi network not appearing**
   - Ensure your Raspberry Pi model has built-in WiFi
   - Check hostapd status: `sudo systemctl status hostapd`
   - Check configuration: `sudo cat /etc/hostapd/hostapd.conf`

5. **Reset to factory defaults**
   If you encounter serious issues, you can reset the system to factory defaults:
   ```bash
   sudo /opt/netprobe/scripts/reset.sh
   ```

### Updating NetProbe Pi

To update to the latest version:

```bash
sudo /opt/netprobe/scripts/auto_update.sh
```

### Manual Installation on Non-Raspberry Pi Systems

NetProbe Pi is designed primarily for Raspberry Pi systems but can be installed on other Debian-based Linux systems with some modifications:

1. Download the repository as described in Option 2 of Step 4
2. Edit the installation script to match your system requirements
3. Run the modified installation script

Note that some features (like WiFi AP mode) may require additional configuration on non-Raspberry Pi systems.

## Additional Resources

- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [NetProbe Pi GitHub Repository](https://github.com/raf181/NetScout-Pi)
