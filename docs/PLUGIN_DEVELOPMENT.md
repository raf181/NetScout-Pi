# NetScout-Pi Plugin Development Guide

This guide walks you through creating custom plugins for NetScout-Pi.

## Quick Start

Create a new Python file in the `src/plugins/` directory with the following structure:

```python
#!/usr/bin/env python3
# Example Plugin for NetScout-Pi

import os
import sys
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class MyExamplePlugin(PluginBase):
    """Example plugin for NetScout-Pi."""
    
    # Required metadata
    name = "my_example"
    description = "An example plugin"
    version = "0.1.0"
    author = "Your Name"
    
    # Optional metadata
    permissions = []
    category = "example"
    tags = ["example", "test"]
    
    def run(self, **kwargs):
        """Run the plugin.
        
        Args:
            **kwargs: Parameters from the web UI or API.
            
        Returns:
            dict: Plugin result.
        """
        self.logger.info("Starting example plugin")
        
        # Your plugin logic here
        result = {
            'timestamp': self.logger.get_timestamp(),
            'success': True,
            'message': "Hello, World!"
        }
        
        self.logger.info("Example plugin completed")
        return result
```

## Core Concepts

1. **Inheritance**: All plugins inherit from `PluginBase`
2. **Metadata**: Define name, description, version, and author
3. **The `run()` method**: Core functionality of your plugin
4. **Results**: Return a dictionary with your findings
5. **Logging**: Use `self.logger` for consistent logging

## Essential Features

### Configuration Access

```python
# Get config value with default fallback
interface = self.config.get('interface', 'eth0')
```

### Progress Updates

```python
# Update progress (0-100) with message
self.update_progress(50, "Processing data...")
```

### Logging

```python
self.logger.debug("Debug message")
self.logger.info("Info message")
self.logger.warning("Warning message")
self.logger.error("Error message")
```

### Result Format

```python
return {
    'timestamp': self.logger.get_timestamp(),
    'success': True,
    'message': "Operation completed successfully",
    'data': {
        'key1': 'value1',
        'key2': 'value2'
    }
}
```

## Best Practices

1. **Handle Errors**: Catch exceptions and return meaningful error messages
2. **Provide Progress Updates**: Especially for long-running operations
3. **Respect Permissions**: Only use resources you declare in permissions[]
4. **Clean Up**: Release resources when your plugin finishes
5. **Follow Naming Conventions**: Use lowercase with underscores

## Example: Network Scanner Plugin

```python
def run(self, network=None, **kwargs):
    """Run network scanner.
    
    Args:
        network (str): Network to scan (e.g. '192.168.1.0/24')
        **kwargs: Additional arguments.
        
    Returns:
        dict: Scan results.
    """
    try:
        network = network or self.config.get('network', '192.168.1.0/24')
        self.logger.info(f"Starting network scan on {network}")
        
        # Update progress
        self.update_progress(10, f"Starting scan of {network}")
        
        # Scan logic here
        devices = []
        # ... your scanning code ...
        
        self.update_progress(100, "Scan completed")
        
        return {
            'timestamp': self.logger.get_timestamp(),
            'success': True,
            'message': f"Scanned {network} and found {len(devices)} devices",
            'data': {
                'network': network,
                'devices': devices
            }
        }
    except Exception as e:
        self.logger.error(f"Scan failed: {str(e)}")
        return {
            'timestamp': self.logger.get_timestamp(),
            'success': False,
            'error': str(e)
        }
```

## Testing Your Plugin

1. Save your plugin to `src/plugins/my_plugin.py`
2. Restart NetScout-Pi or reload plugins
3. Go to the Plugins page in the web UI
4. Find your plugin and run it
