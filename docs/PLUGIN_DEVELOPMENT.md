# NetProbe Pi Plugin Development Guide

This guide will walk you through the process of creating custom plugins for NetProbe Pi.

## Plugin Structure

A NetProbe Pi plugin is a Python module that defines a class inheriting from `PluginBase`. Each plugin must implement the `run()` method, which is called when the plugin is executed.

### Basic Plugin Template

```python
#!/usr/bin/env python3
# Example Plugin for NetProbe Pi

import os
import sys
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class MyExamplePlugin(PluginBase):
    """Example plugin for NetProbe Pi."""
    
    # Plugin metadata (required)
    name = "my_example"
    description = "An example plugin"
    version = "0.1.0"
    author = "Your Name"
    
    # Plugin metadata (optional)
    permissions = []
    category = "example"
    tags = ["example", "test"]
    
    def run(self, **kwargs):
        """Run the plugin.
        
        Args:
            **kwargs: Additional arguments.
            
        Returns:
            dict: Plugin result.
        """
        self.logger.info("Starting example plugin")
        
        # Plugin logic here
        result = {
            'timestamp': self.logger.get_timestamp(),
            'success': True,
            'message': "Hello, World!"
        }
        
        self.logger.info("Example plugin completed")
        return result
```

## Plugin Metadata

Each plugin must define the following metadata attributes:

- `name`: A unique identifier for the plugin (lowercase with underscores)
- `description`: A short description of what the plugin does
- `version`: The plugin version (semantic versioning recommended)
- `author`: The plugin author's name

Additionally, you can define these optional metadata attributes:

- `permissions`: List of required permissions (e.g., "sudo", "network")
- `category`: Plugin category for organization
- `tags`: Search tags for finding the plugin

## The `run()` Method

The `run()` method is the entry point for your plugin. It should:

1. Perform the plugin's main functionality
2. Return a dictionary with the results
3. Handle any errors gracefully

### Parameters

The `run()` method can accept any number of keyword arguments (`**kwargs`), which are passed from:

- The web dashboard when running the plugin manually
- The API when calling the plugin programmatically
- The configuration when running as part of a sequence

### Return Value

The `run()` method must return a dictionary containing the plugin results. At minimum, include:

- `timestamp`: When the plugin was run (use `self.logger.get_timestamp()`)
- `success`: Boolean indicating if the plugin ran successfully
- Any other relevant data specific to your plugin

## Available Utilities

The `PluginBase` class provides several utilities for your plugin:

### Configuration

Access configuration values with:

```python
# Get a config value with a default fallback
value = self.config.get('setting_name', 'default_value')
```

### Logging

Log messages at different levels:

```python
self.logger.debug("Debug message")
self.logger.info("Info message")
self.logger.warning("Warning message")
self.logger.error("Error message")
```

### Progress Updates

Update the progress during execution:

```python
# Update progress to 50% with a status message
self.update_progress(50, "Processing data...")
```

## Error Handling

Always handle exceptions in your plugin:

```python
try:
    # Code that might raise exceptions
    result = self._perform_action()
except Exception as e:
    self.logger.error(f"Error: {str(e)}")
    return {
        'timestamp': self.logger.get_timestamp(),
        'success': False,
        'error': str(e)
    }
```

## Installing Your Plugin

To install a custom plugin:

1. Navigate to the Plugins page in the NetProbe Pi dashboard
2. Click on "Install Plugin"
3. Upload your plugin file
4. The plugin will be available immediately if there are no errors

## Testing Your Plugin

Enable Developer Mode in the Settings page to get additional debugging information when running your plugin.

## Example Plugins

See the built-in plugins in the `src/plugins/` directory for examples:

- `ip_info.py`: Shows current IP and network information
- `ping_test.py`: Tests connectivity to specified targets
- `arp_scan.py`: Scans the local network for devices
- `speed_test.py`: Measures internet connection speed

## Best Practices

1. Always provide meaningful progress updates for long-running operations
2. Handle errors gracefully and provide useful error messages
3. Include detailed comments in your code
4. Keep the `run()` method focused; use helper methods for complex logic
5. Follow PEP 8 style guidelines
6. Use type hints for better code clarity

## Need Help?

If you need assistance with plugin development, check out:

- The NetProbe Pi GitHub repository
- The built-in plugin examples
- The developer documentation in the NetProbe Pi wiki
