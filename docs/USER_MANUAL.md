# NetProbe Pi - User Manual

This document provides comprehensive information on how to use NetProbe Pi, a network diagnostics system designed for Raspberry Pi Zero 2 W.

## Table of Contents
- [Initial Setup](#initial-setup)
- [Accessing the Dashboard](#accessing-the-dashboard)
- [Dashboard Overview](#dashboard-overview)
- [Running Plugins](#running-plugins)
- [Plugin Sequences](#plugin-sequences)
- [Managing Plugins](#managing-plugins)
- [System Settings](#system-settings)
- [Exporting Logs](#exporting-logs)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## Initial Setup

After installing NetProbe Pi following the [Installation Guide](INSTALL.md), the system will reboot and be accessible through its WiFi network.

1. Connect to the `NetProbe` WiFi network
   - SSID: `NetProbe`
   - Password: `netprobe123`

2. Open a web browser and navigate to http://netprobe.local or http://192.168.4.1

3. On first access, you'll be prompted to set an admin password.

## Accessing the Dashboard

### WiFi Access (Default)
- Connect to the `NetProbe` WiFi network
- Navigate to http://netprobe.local

### Ethernet Access (If enabled in settings)
- Connect your computer to the same network as the Ethernet port
- Navigate to the IP address assigned to the Ethernet interface

## Dashboard Overview

The dashboard consists of several sections:

1. **Home**: System status, network interfaces, and quick actions
2. **Plugins**: List of available plugins with controls to run them
3. **Sequences**: Create and manage sequences of plugins
4. **Results**: View and export previous plugin results
5. **Settings**: Configure system settings

## Running Plugins

1. Navigate to the **Plugins** section
2. Select a plugin from the list
3. Configure any required parameters
4. Click "Run Plugin"
5. View real-time output in the results panel

## Plugin Sequences

Sequences allow you to run multiple plugins in a specific order.

### Creating a Sequence

1. Navigate to the **Sequences** section
2. Click "Create Sequence"
3. Enter a name and description
4. Add plugins to the sequence by dragging from the available plugins list
5. Configure parameters for each plugin
6. Click "Save Sequence"

### Running a Sequence

1. Navigate to the **Sequences** section
2. Find your sequence in the list
3. Click "Run Sequence"

## Managing Plugins

### Installing a Plugin

1. Navigate to the **Plugins** section
2. Click "Upload Plugin"
3. Select a Python (.py) file
4. Review the plugin information and permissions
5. Click "Install"

### Enabling/Disabling Plugins

1. Navigate to the **Plugins** section
2. Toggle the switch next to the plugin name

### Uninstalling a Plugin

1. Navigate to the **Plugins** section
2. Click the "Delete" icon next to the plugin
3. Confirm the deletion

## System Settings

The settings page allows you to configure various aspects of the system:

### Network Settings
- Interface selection (eth0, wlan0)
- Poll interval for connection detection
- Monitoring method (poll, netlink, ifplugd)

### Security Settings
- Change admin password
- Allow/disallow Ethernet access
- Session timeout

### Plugin Settings
- Default plugins to run on connection
- Auto-run on connect option

### Integration Settings
- Webhook configuration
- MQTT settings

## Exporting Logs

1. Navigate to the **Results** section
2. Click "Export Logs"
3. Select the time range (1 day, 1 week, 1 month, or all)
4. Click "Download ZIP"

## Security

### Changing Password

1. Navigate to the **Settings** section
2. Click "Security" tab
3. Enter current password
4. Enter and confirm new password
5. Click "Update Password"

### SSH Key-based Authentication

SSH keys are generated on first boot for secure remote access.

To access via SSH:
```
ssh pi@netprobe.local
```

### Network Isolation

By default, the web interface is only accessible from the WiFi network to enhance security.

## Troubleshooting

### Dashboard Not Accessible
- Ensure you're connected to the `NetProbe` WiFi network
- Check that the system is powered on (LED indicators should be lit)
- Try accessing via IP address (192.168.4.1) instead of hostname

### Plugin Errors
- Check the plugin logs in the **Results** section
- Ensure any required dependencies are installed
- Verify network connectivity on the appropriate interface

### Reset to Factory Defaults
1. SSH into the device: `ssh pi@netprobe.local`
2. Run the reset script: `sudo /opt/netprobe/scripts/reset.sh`
3. The system will reboot and reset to default settings

For more assistance, please refer to the [Troubleshooting Guide](TROUBLESHOOTING.md) or open an issue on the GitHub repository.
