# NetScout-Pi: Network Diagnostic Tool for Raspberry Pi

![NetScout-Pi Logo](/Resources/Banner.png)
> [!warning]
> Do not use for production environments. This is a personal project for educational purposes and may not be secure or stable enough for critical applications. Most of the plugins are not optimized for production use and may require additional configuration (some even dont behave correctly outside the environment that they were developed in) or security measures.

NetScout-Pi is a comprehensive network diagnostic and monitoring tool designed specifically for Raspberry Pi devices. It provides a web-based interface to run various network diagnostic tools and view real-time network information.

## Features

- **Web-Based Dashboard**: Access all network tools through an intuitive web interface
- **Real-Time Network Information**: Monitor your Pi's network connections with live updates
- **Modular Plugin System**: Easily extend functionality with new diagnostic tools
- **Categorized Plugin Interface**: Plugins organized by function for easier navigation
- **Mobile-Friendly Interface**: Use on any device with responsive design
- **RESTful API**: Programmatically access all tools through a JSON API
- **WebSocket Updates**: Receive real-time network statistics via WebSocket
- **External Plugin Support**: Extend functionality with custom scripts in Python, Bash, and more

## Included Diagnostic Tools

### Network Analysis

- **Network Information**: View detailed information about your Pi's network interfaces
- **Bandwidth Test**: Measure network bandwidth
- **Network Quality Monitor**: Measure jitter, latency, and packet loss over time
- **MTU Size Tester**: Find the optimal MTU size for your connection
- **Packet Capture**: Capture and analyze network packets using tcpdump

### Connectivity Testing

- **Ping**: Test connectivity to hosts with ICMP echo requests
- **Traceroute**: Trace the route packets take to a network host

### Network Discovery

- **Port Scanner**: Scan for open ports on a target host
- **Network Device Discovery**: Find devices on your local network
- **Wi-Fi Scanner**: Discover and analyze nearby wireless networks

### DNS Tools

- **DNS Lookup**: Perform DNS lookups for domains
- **DNS Propagation Checker**: Test DNS propagation across multiple servers
- **Reverse DNS Lookup**: Find hostnames associated with IP addresses

### Security

- **SSL/TLS Certificate Checker**: Analyze and verify SSL certificates

## Requirements

- Raspberry Pi (Zero 2W, 3B+, 4, or newer recommended but compatible with any hardware)
- Raspberry Pi OS (or other compatible Linux distribution)
- Go programming language installed (version 1.16 or newer)
- Internet connection (for installation)

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/anoam/NetScout-Pi.git
    cd NetScout-Pi
    ```

2. Build the application:

    ```bash
    go build
    ```

    **Note for Raspberry Pi Zero 2W users**: If you encounter compilation errors related to CGO, use:

    ```bash
    env CGO_ENABLED=0 go build
    ```

3. Run the application:

    ```bash
    ./netscout-pi
    ```

    You should not need to run this with sudo, but if you encounter permission issues, try:

    ```bash
    sudo ./netscout-pi
    ```

    By default, it will start on port 8080. You can change the port by using the `--port` flag.

4. Access the web interface:
   Open a browser and navigate to `http://<your-pi-ip>:8080`

## Running as a Service

To run NetScout-Pi as a background service that starts on boot:

1. Create a systemd service file:

    ```bash
    sudo nano /etc/systemd/system/netscout.service
    ```

2. Add the following content (adjust paths as needed):

    ```ini
    [Unit]
    Description=NetScout-Pi Network Diagnostic Tool
    After=network.target

    [Service]
    ExecStart=/home/pi/NetScout-Pi/netscout-pi #You may need to adjust this path
    WorkingDirectory=/home/pi/NetScout-Pi
    StandardOutput=inherit
    StandardError=inherit
    Restart=always
    User=pi

    [Install]
    WantedBy=multi-user.target
    ```

3. Enable and start the service:

    ```bash
    sudo systemctl enable netscout.service
    sudo systemctl start netscout.service
    sudo systemctl status netscout.service # Check the service status and if it's running correctly
    ```

## Configuration

By default, NetScout-Pi runs on port 8080. To use a different port:

```bash
./netscout-pi --port=8888
```

You can also configure the application by creating a config.json file in the root directory:

```json
{
  "port": 8888,
  "debug": true,
  "allowCORS": false,
  "refreshInterval": 5
}
```

## Dashboard Features

The main dashboard provides real-time information about your network interfaces:

- **Connection Status**: Current connection state and uptime
- **IP Configuration**: IPv4/IPv6 addresses, subnet mask, and gateway
- **Interface Details**: MAC address, link speed, and duplex settings
- **Traffic Statistics**: Bytes/packets sent and received
- **DNS Servers**: Currently configured DNS servers
- **DHCP Information**: DHCP lease status and expiration
- **ARP Table**: Address Resolution Protocol entries
- **Network Topology**: Simple visualization of network devices

## Plugin System

NetScout-Pi uses a modular plugin system that makes it easy to add new diagnostic tools. Plugins are now organized into categories for easier navigation through an accordion menu in the sidebar. Each plugin consists of:

1. A **plugin.json** file defining metadata and parameters
2. A **plugin.go** file implementing the plugin's functionality

See the [Plugin Development Guide](app/plugins/DEVELOPMENT.md) for details on creating custom plugins.

### Available Plugins

| Plugin | Description | Parameters |
|--------|-------------|------------|
| **Network Analysis** | | |
| network_info | Get detailed network info | interface |
| bandwidth_test | Measure network speed | duration, direction, server |
| network_quality | Monitor network quality metrics | duration, target, interval |
| mtu_tester | Find optimal MTU size | host, startSize, endSize, step |
| packet_capture | Capture network packets | interface, duration, filter, outputFile |
| **Connectivity Testing** | | |
| ping | Test connectivity to hosts | host, count, interval, size |
| traceroute | Trace network path | host, maxHops, timeout |
| **Network Discovery** | | |
| port_scanner | Scan for open ports | host, portRange, timeout |
| device_discovery | Find devices on local network | subnet, timeout |
| wifi_scanner | Scan for wireless networks | interface |
| **DNS Tools** | | |
| dns_lookup | Perform DNS lookups | domain, type (A, AAAA, MX, etc.) |
| dns_propagation | Check DNS propagation | domain, recordType, nameservers |
| reverse_dns_lookup | Find hostnames for IPs | ipAddress |
| **Security** | | |
| ssl_checker | Verify SSL/TLS certificates | domain, port |

## API Usage

All plugins can be accessed via the RESTful API:

- List all plugins: `GET /api/plugins`
- Get plugin details: `GET /api/plugins/{id}`
- Run a plugin: `POST /api/plugins/{id}/run` (with JSON parameters)
- Get network info: `GET /api/network-info`

Example API call to run the ping plugin:

```bash
curl -X POST http://<your-pi-ip>:8080/api/plugins/ping/run \
  -H "Content-Type: application/json" \
  -d '{"host": "example.com", "count": 4}'
```

Example response:

```json
{
  "host": "example.com",
  "sent": 4,
  "received": 4,
  "loss": 0,
  "minRtt": 24.5,
  "avgRtt": 27.2,
  "maxRtt": 30.1,
  "results": [
    {"seq": 1, "ttl": 54, "time": 24.5},
    {"seq": 2, "ttl": 54, "time": 27.8},
    {"seq": 3, "ttl": 54, "time": 30.1},
    {"seq": 4, "ttl": 54, "time": 26.4}
  ],
  "timestamp": "2025-06-12T14:22:35Z"
}
```

## WebSocket Support

NetScout-Pi provides real-time updates through WebSockets:

```javascript
const ws = new WebSocket('ws://<your-pi-ip>:8080/ws');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

## External Plugin Support

NetScout-Pi supports external plugins written in languages like Python and Bash. See the [External Plugin Guide](app/plugins/plugins/external_plugin/README.md) for more information.

## Troubleshooting

### Common Issues

- **Compilation Errors on Raspberry Pi Zero**: Use `env CGO_ENABLED=0 go build`
- **Permission Denied**: Run with sudo for network tools that require elevated privileges
- **Interface Not Found**: Check if the network interface name is correct (e.g., wlan0, eth0)
- **WebSocket Connection Failed**: Check if firewall is blocking WebSocket connections

### Logs

Check the application logs for detailed error information:

```bash
journalctl -u netscout.service -f
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The Go community for excellent networking libraries
- Raspberry Pi Foundation for creating such a versatile platform
- All contributors who have helped improve this project
