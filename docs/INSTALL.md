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

1. Update your system:
   ```
   sudo apt update && sudo apt upgrade -y
   ```

2. Install git:
   ```
   sudo apt install git -y
   ```

3. Clone the NetProbe Pi repository:
   ```
   git clone https://github.com/raf181/NetScout-Pi.git
   ```

4. Navigate to the project directory:
   ```
   cd NetProbe-Pi
   ```

5. Run the installation script:
   ```
   sudo ./scripts/install.sh
   ```

6. Follow the prompts to complete the installation

## Step 5: Access the Web Dashboard

1. After installation, the NetProbe Pi will automatically set up a web server
2. You can access the dashboard at `http://netprobe.local` or `http://<IP_ADDRESS>`
3. Log in with the default credentials:
   - Username: `admin`
   - Password: `netprobe`
   
   (You will be prompted to change these on first login)

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

- If you can't connect to WiFi, check your `wpa_supplicant.conf` file
- If the web dashboard isn't accessible, check if the service is running:
  ```
  sudo systemctl status netprobe
  ```
- For log information:
  ```
  sudo journalctl -u netprobe
  ```

## Additional Resources

- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [NetProbe Pi GitHub Repository](https://github.com/raf181/NetScout-Pi)
