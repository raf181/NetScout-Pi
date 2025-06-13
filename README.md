# NetScout-Pi: Network Diagnostic Tool for Raspberry Pi

![NetScout-Pi Logo](/app/static/img/favicon.ico)

NetScout-Pi is a comprehensive network diagnostic and monitoring tool designed specifically for Raspberry Pi devices. It provides a web-based interface to run various network diagnostic tools and view real-time network information.

## Features

- **Web-Based Dashboard**: Access all network tools through an intuitive web interface
- **Real-Time Network Information**: Monitor your Pi's network connections with live updates
- **Modular Plugin System**: Easily extend functionality with new diagnostic tools
- **Mobile-Friendly Interface**: Use on any device with responsive design
- **RESTful API**: Programmatically access all tools through a JSON API
- **WebSocket Updates**: Receive real-time network statistics via WebSocket

## Included Diagnostic Tools

- **Network Information**: View detailed information about your Pi's network interfaces
- **Ping**: Test connectivity to hosts with ICMP echo requests
- **Traceroute**: Trace the route packets take to a network host
- **Port Scanner**: Scan for open ports on a target host
- **DNS Lookup**: Perform DNS lookups for domains
- **Bandwidth Test**: Measure network bandwidth
- **And more...**: The modular plugin system makes it easy to add more tools

## Prerequisites

- Raspberry Pi (Zero 2W, 3B+, 4, or newer recommended)
- Raspberry Pi OS (or other compatible Linux distribution)
- Go 1.16 or newer
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
   ExecStart=/home/pi/NetScout-Pi/netscout-pi
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

NetScout-Pi uses a modular plugin system that makes it easy to add new diagnostic tools. Each plugin consists of:

1. A **plugin.json** file defining metadata and parameters
2. A **plugin.go** file implementing the plugin's functionality

See the [Plugin Development Guide](app/plugins/DEVELOPMENT.md) for details on creating custom plugins.

### Available Plugins

| Plugin | Description | Parameters |
|--------|-------------|------------|
| ping | Test connectivity to hosts | host, count, interval, size |
| traceroute | Trace network path | host, maxHops, timeout |
| dns_lookup | Perform DNS lookups | domain, type (A, AAAA, MX, etc.) |
| port_scanner | Scan for open ports | host, portRange, timeout |
| bandwidth_test | Measure network speed | duration, direction, server |
| network_info | Get detailed network info | interface |

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
