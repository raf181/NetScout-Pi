# NetScout-Pi-V2

A Python-based API running on a Raspberry Pi Zero 2W with an Ethernet USB dongle. This API acts as an intermediate layer for community-built plugins, providing a web dashboard for loading plugins and visualizing their output dynamically.

## Features

- **Plugin Management**: Upload, install, and manage community-built plugins
- **Web Dashboard**: Interactive web interface for monitoring and controlling your Pi
- **Real-time Updates**: Socket.IO integration for real-time plugin output visualization
- **Responsive Design**: Mobile-friendly interface that works on all devices
- **API Endpoints**: RESTful API for integration with other systems

## Requirements

- Raspberry Pi Zero 2W with Ethernet USB dongle
- Python 3.7+
- Flask and related packages (see requirements.txt)
- net-tools package (for the arp command used by the Network Scanner plugin)

## Installation

1. Clone this repository to your Raspberry Pi:

```bash
git clone https://github.com/yourusername/NetScout-Pi-V2.git
cd NetScout-Pi-V2
```

2. Run the automated setup script (recommended):

```bash
sudo ./setup.sh
```

The setup script will automatically:
- Install required system dependencies
- Set up a virtual environment if needed (for externally-managed Python environments)
- Install Python dependencies
- Configure and start the service

3. Alternatively, for manual installation:

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev iputils-ping net-tools ethtool

# For newer Raspberry Pi OS (externally-managed environment):
sudo apt-get install -y python3-venv python3-full
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# For older systems:
pip3 install -r requirements.txt

# Run the application
python3 run.py
```

4. Access the dashboard at `http://<your-pi-ip>:5000`

## Handling Externally-Managed Python Environments

Recent versions of Debian-based operating systems (including Raspberry Pi OS) implement PEP 668, which prevents pip from modifying system packages. If you encounter this error:

```
error: externally-managed-environment
```

Our setup script will automatically handle this by:

1. Detecting the externally-managed environment
2. Creating a Python virtual environment
3. Installing dependencies in the virtual environment
4. Configuring the service to use the virtual environment

If you're installing manually, use these commands:

```bash
# Install required packages
sudo apt-get install -y python3-venv python3-full

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies in the virtual environment
pip install -r requirements.txt

# Run the application within the virtual environment
python run.py
```

For convenience, you can also use the provided run script which automatically handles virtual environments:

```bash
# Make the script executable
chmod +x run.sh

# Run the application
./run.sh
```

## Plugin Development

Plugins for NetScout-Pi are simple Python modules packaged with a YAML manifest. Each plugin must include:

1. A `manifest.yaml` file that describes the plugin
2. A main Python module with an `execute()` function
3. Optional UI HTML files for custom visualizations

### Plugin Structure

```
myplugin/
├── manifest.yaml     # Plugin metadata and configuration
├── main.py           # Main plugin code
├── ui.html           # Optional custom UI (if has_ui is set to true)
└── static/           # Optional static assets for the UI
    ├── css/
    ├── js/
    └── img/
```

### Manifest Format

```yaml
name: My Plugin
id: myplugin
version: 1.0.0
description: A simple plugin for NetScout Pi
author: Your Name
homepage: https://github.com/yourusername/myplugin
main_module: main  # Python file containing the execute() function
parameters:
  - name: param1
    label: Parameter 1
    type: string
    description: A string parameter
    default: default value
    required: true
ui_path: ui.html  # Optional path to custom UI
```

### Plugin API

Your main module must include an `execute()` function that accepts parameters and returns results:

```python
def execute(params):
    """
    Execute the plugin with the given parameters.
    
    Args:
        params (dict): Parameters from the UI/API
        
    Returns:
        dict: Result data that will be displayed in the dashboard
    """
    # Your plugin code here
    return {
        "type": "table",  # Optional type for special rendering
        "data": [...]     # Your result data
    }
```

### Installing Plugins

Plugins can be installed via the web dashboard by uploading a ZIP file containing the plugin directory.

## API Documentation

### Plugin Management

- `GET /api/plugins` - List all installed plugins
- `GET /api/plugins/<plugin_id>` - Get plugin details
- `POST /api/plugins/<plugin_id>/execute` - Execute a plugin
- `POST /api/plugins` - Install a new plugin (multipart/form-data)
- `DELETE /api/plugins/<plugin_id>` - Uninstall a plugin

## Troubleshooting

### Network Scanner Plugin

If you encounter the error `/bin/sh: 1: arp: not found` when using the network scanner plugin, this indicates that the `arp` command is not in your system PATH. To fix this:

1. Run the dependencies installation script as root:

   ```bash
   sudo ./install_dependencies.sh
   ```

2. If the issue persists, make sure `/usr/sbin` is in your PATH by adding this line to your `.bashrc` file:

   ```bash
   export PATH=$PATH:/usr/sbin
   ```

3. Apply the change to your current session:

   ```bash
   source ~/.bashrc
   ```

4. Restart the NetScout-Pi-V2 application.

This issue typically occurs because the `arp` command is installed at `/usr/sbin/arp`, but `/usr/sbin` is not in the default PATH for some users.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
