# NetProbe Pi

A comprehensive network diagnostics system for Raspberry Pi Zero 2 W that provides a plugin-based framework for network testing and monitoring.

## 🧱 Core Architecture

- Headless Raspberry Pi OS (Lite)
- WiFi used for admin access (wlan0)
- USB-Ethernet dongle (eth0) used for diagnostics
- Boot-time detection of Ethernet link

## 🔌 Plugin System

- Python-based diagnostic modules (.py files in a /plugins/ folder)
- Plugin metadata: name, description, required permissions
- Built-in plugins: ping, traceroute, nmap, speedtest, etc.
- Support for custom plugins
- Upload plugins via web dashboard
- Create and run sequences of plugins

## 🖥️ Web Dashboard

- Flask-based web interface accessible at `http://netprobe.local`
- List and run available plugins
- Real-time plugin output via WebSockets
- Enable/disable plugins
- Configure default behavior and settings
- Mobile-friendly responsive design
- Plugin management (upload, enable, disable, uninstall)
- Sequence management (create, edit, delete, run)

## ⚙️ Event-Based Triggers

- Automatic detection of Ethernet connection
- Run predefined plugin sequences on connection
- Comprehensive logging
- Multiple detection methods: polling, netlink, ifplugd

## 🗃️ Storage & Logs

- Timestamped JSON and plain text logs
- Export results as ZIP
- Log rotation and management
- Per-plugin logging

## 🔐 Security

- Password-protected dashboard
- Network interface isolation (WiFi only access by default)
- SSH key-based authentication
- First-boot security setup

## 🛠️ Development

- Easy plugin development with documented interface
- Developer mode for plugin debugging
- Plugin template for quick development
- Comprehensive plugin API

## 🧪 Integrations

- Webhook support for external notifications
- MQTT integration for IoT applications
- Auto-update system
- Customizable event triggers

- Auto-updater via Git
- Webhook integration for alerts
- MQTT integration for IoT logging

## 📥 Installation

### Option 1: Automated Installation (Recommended)

1. Flash Raspberry Pi OS Lite to your SD card
2. Enable SSH by creating an empty file named `ssh` in the boot partition
3. Insert the SD card into your Raspberry Pi Zero 2 W and power it on
4. Connect to your Raspberry Pi via SSH: `ssh pi@raspberrypi.local`
5. Download and run the setup script:

    ```bash
    curl -sSL https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/setup.sh | sudo bash
    ```

6. After the installation is complete, the Raspberry Pi will reboot
7. Connect to the `NetProbe` WiFi network (password: `netprobe123`)
8. Access the dashboard at http://netprobe.local
9. Set your admin password during the first login

### Option 2: Manual Installation

1. Flash Raspberry Pi OS Lite to your SD card
2. Boot your Raspberry Pi and log in
3. Clone the repository:

    ```bash
    git clone https://github.com/raf181/NetScout-Pi.git
    cd NetScout-Pi
    ```

4. Run the installation script:

    ```bash
    sudo bash scripts/install.sh
    ```

5. Set up network interfaces:

    ```bash
    sudo bash scripts/setup.sh
    ```

6. Reboot your Raspberry Pi:

    ```bash
    sudo reboot
    ```

7. Connect to the `NetProbe` WiFi network and access the dashboard

### Note on GitHub Authentication

GitHub no longer supports password authentication for git operations. The scripts are designed to handle this automatically by using alternative methods if direct cloning fails. If you're manually cloning the repository, please refer to the [Installation Guide](docs/INSTALL.md) for detailed authentication options.

## 📖 Documentation

Full documentation is available in the `docs/` directory:

- [Installation Guide](docs/INSTALL.md)
- [User Manual](docs/USER_MANUAL.md)
- [Plugin Development](docs/PLUGIN_DEVELOPMENT.md)
- [API Reference](docs/API_REFERENCE.md)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
