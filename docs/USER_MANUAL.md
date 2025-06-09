# NetScout-Pi - User Manual

This guide provides everything you need to know about using NetScout-Pi, a powerful network diagnostics system for Raspberry Pi and other Linux systems.

## Table of Contents
- [Quick Installation](#quick-installation)
- [Accessing the Dashboard](#accessing-the-dashboard)
- [Dashboard Overview](#dashboard-overview)
- [Running Network Tests](#running-network-tests)
- [Viewing Results](#viewing-results)
- [Managing Logs](#managing-logs)
- [System Settings](#system-settings)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## Quick Installation

Install NetScout-Pi with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/raf181/NetScout-Pi/main/scripts/netscout_installer.sh | sudo bash
```

After installation:

1. Connect to the `NetScout` WiFi network (Password: `netscout123`)
2. Open a web browser and navigate to [http://netscout.local](http://netscout.local) or [http://192.168.4.1](http://192.168.4.1)
3. Set your admin password on first login

## Accessing the Dashboard

### WiFi Access (Default)

- Connect to the `NetScout` WiFi network
- Navigate to [http://netscout.local](http://netscout.local)

### Ethernet Access (If enabled in settings)

- Connect your computer to the same network as the Ethernet interface
- Navigate to the IP address assigned to the Ethernet interface

## Dashboard Overview

The dashboard consists of several sections:

1. **Home**: System status, network interfaces, and quick actions
2. **Plugins**: Network diagnostic tools ready to run
3. **Results**: View and export test results
4. **Logs**: System and plugin logs
5. **Settings**: Configure system preferences

## Running Network Tests

1. Navigate to the **Plugins** section
2. Select a plugin from the list:
   - **IP Info**: Shows current IP, MAC, gateway, subnet mask, DNS info
   - **Ping Test**: Tests connectivity to a host or IP address
   - **Speed Test**: Measures internet connection speed
   - **ARP Scan**: Discovers devices on local network
   - **Port Scan**: Scans for open ports on a target
   - **Traceroute**: Traces network path to a target
   - **Packet Capture**: Captures and analyzes network traffic
   - **VLAN Detector**: Detects VLAN configuration
3. Configure any required parameters
4. Click "Run" to start the test
5. View real-time results as they appear

## Viewing Results

1. Navigate to the **Results** section
2. Browse the list of previous test runs
3. Click on any result to view detailed information
4. Use the export options to save results as JSON, CSV, or PDF
5. Filter results by plugin type, date range, or success status

## Managing Logs

1. Navigate to the **Logs** section
2. View system logs, plugin logs, and network events
3. Filter logs by:
   - Severity level (info, warning, error, critical)
   - Time period (today, last week, last month)
   - Source (system, plugin, network)
4. Download logs for offline analysis or troubleshooting

## System Settings

The Settings page allows you to configure various aspects of NetScout-Pi:

### Network Settings

- Interface selection (eth0, wlan0)
- Network monitoring preferences
- WiFi access point configuration

### Security Settings

- Change admin password
- Session timeout configuration
- Access control settings

### Plugin Settings

- Default plugins to run on startup
- Plugin update preferences

### Integration Settings

- Webhook configuration
- API access tokens
- MQTT broker settings

## Security

### Changing Password

1. Navigate to the **Settings** section
2. Click on the "Security" tab
3. Enter current password
4. Enter and confirm new password
5. Click "Update Password"

### Access Control

- By default, the web interface is only accessible from the WiFi network
- Ethernet access can be enabled in the Security settings
- SSH access is available with key-based authentication

## Troubleshooting

### Dashboard Not Accessible

- Ensure you're connected to the `NetScout` WiFi network
- Check that the system is powered on
- Try accessing via IP address (192.168.4.1) instead of hostname

### Plugin Errors

- Check the plugin logs in the **Logs** section
- Ensure any required dependencies are installed
- Verify network connectivity on the appropriate interface

### Reset to Factory Defaults

1. SSH into the device: `ssh pi@netscout.local`
2. Run the reset script: `sudo /opt/netscout/scripts/reset.sh`
3. The system will reboot and reset to default settings

### Auto-Fix Script

If you're experiencing issues, run the automatic fix script:

```bash
sudo bash /opt/netscout/scripts/autofix_v2.sh
```

This script will fix common issues like WiFi configuration, permissions, and services.
