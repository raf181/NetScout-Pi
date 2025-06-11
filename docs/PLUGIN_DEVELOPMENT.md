# NetScout-Pi Plugin Development Guide

This guide walks you through creating custom plugins for NetScout-Pi.

## Plugin Structure

Plugins in NetScout-Pi are organized in a folder-based structure, where each plugin is contained in its own directory with the following components:

```
plugin_name/
├── plugin.py        # Main plugin implementation
└── config.json      # Plugin metadata and configuration
```

## Quick Start

### Step 1: Create Plugin Directory

Create a new directory for your plugin in one of the plugin directories:

```bash
mkdir -p ~/NetScout-Pi/src/plugins_new/my_custom_plugin
```

### Step 2: Create config.json

Create a `config.json` file with your plugin metadata and configuration:

```json
{
    "metadata": {
        "name": "my_custom_plugin",
        "description": "My custom plugin description",
        "version": "0.1.0",
        "author": "Your Name",
        "permissions": [],
        "category": "custom",
        "tags": ["custom", "example"]
    },
    "settings": {
        "enabled": true,
        "example_setting": "example_value",
        "timeout": 30
    }
}
```

### Step 3: Create plugin.py

```python
#!/usr/bin/env python3
# NetScout-Pi - Custom Plugin Example

import os
import sys
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class MyCustomPlugin(PluginBase):
    """
    Custom plugin for NetScout-Pi.
    
    Replace this description with information about what your plugin does.
    """
    
    def __init__(self, config, logger):
        """Initialize plugin.
        
        Args:
            config: Plugin configuration.
            logger: PluginLogger instance.
        """
        super().__init__(config, logger)
        
        # Read metadata from config.json
        self.metadata = self.config.get('metadata', {})
        self.name = self.metadata.get('name', 'my_custom_plugin')
        self.description = self.metadata.get('description', 'My custom plugin')
        self.version = self.metadata.get('version', '0.1.0')
        self.author = self.metadata.get('author', 'Your Name')
        self.permissions = self.metadata.get('permissions', [])
        self.category = self.metadata.get('category', 'custom')
        self.tags = self.metadata.get('tags', ['custom', 'example'])
        
        # Initialize plugin-specific variables
        self.plugin_dir = Path(__file__).resolve().parent
        
    def run(self, **kwargs):
        """Run the plugin.
        
        Args:
            **kwargs: Additional arguments.
            
        Returns:
            dict: Plugin result.
        """
        self.logger.info(f"Running {self.name} plugin...")
        
        # Initialize result
        result = {
            'timestamp': self.logger.get_timestamp(),
            'success': False,
            'data': None,
            'message': ''
        }
        
        try:
            # Plugin implementation goes here
            self.update_progress(10, "Starting...")
            
            # Example: Access plugin-specific configuration
            example_setting = self.config.get('settings', {}).get('example_setting', 'default_value')
            self.logger.info(f"Example setting: {example_setting}")
            
            # Example: Process arguments
            target = kwargs.get('target', 'example.com')
            self.logger.info(f"Target: {target}")
            
            self.update_progress(50, "Processing...")
            
            # Example: Perform custom functionality
            # ...
            
            # Set result data
            result['data'] = {
                'example': 'data',
                'target': target
            }
            result['success'] = True
            result['message'] = "Plugin executed successfully"
            
            self.update_progress(100, "Completed")
            
        except Exception as e:
            error_msg = f"Plugin execution failed: {str(e)}"
            self.logger.error(error_msg)
            result['success'] = False
            result['message'] = error_msg
            self.update_progress(100, "Failed")
            
        return result
```

### Step 4: Using the Plugin Template

Alternatively, you can use the provided template plugin:

1. Copy the template directory:
   ```bash
   cp -r ~/NetScout-Pi/src/plugins_new/template ~/NetScout-Pi/src/plugins_new/my_custom_plugin
   ```

2. Edit the `config.json` file to update plugin metadata.

3. Edit the `plugin.py` file to implement your custom functionality.

## Core Concepts

1. **Folder-Based Structure**: Each plugin has its own folder with `plugin.py` and `config.json`
2. **Configuration**: Plugin settings and metadata are stored in `config.json`
3. **Inheritance**: All plugins inherit from `PluginBase`
4. **The `run()` method**: Core functionality of your plugin
5. **Results**: Return a dictionary with your findings
6. **Logging**: Use `self.logger` for consistent logging

## Essential Features

### Configuration Access

```python
# Get metadata from config.json
self.metadata = self.config.get('metadata', {})
self.name = self.metadata.get('name', 'default_name')

# Get plugin settings with default fallback
settings = self.config.get('settings', {})
interface = settings.get('interface', 'eth0')
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
        # Get settings from config
        settings = self.config.get('settings', {})
        network = network or settings.get('network', '192.168.1.0/24')
        
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

1. Create your plugin folder in `src/plugins_new/`
2. Create `plugin.py` and `config.json` files
3. Restart NetScout-Pi or reload plugins
4. Go to the Plugins page in the web UI
5. Find your plugin and run it

## Advanced Topics

### Asynchronous Execution

Plugins can be run asynchronously using the `async_run` method:

```python
run_id = plugin.async_run(
    callback=my_callback_function,
    progress_callback=my_progress_callback,
    **kwargs
)
```

### Custom Settings

You can add custom settings to your plugin by adding them to the `settings` section of the `config.json` file:

```json
"settings": {
    "enabled": true,
    "custom_setting_1": "value1",
    "custom_setting_2": 42,
    "custom_setting_3": {
        "nested": "value"
    }
}
```

### Plugin Dependencies

If your plugin depends on external modules, you should document these dependencies in the plugin description and check for their presence in the `__init__` method:

```python
def __init__(self, config, logger):
    super().__init__(config, logger)
    
    # Check for required modules
    try:
        import required_module
    except ImportError:
        raise ImportError("Required module 'required_module' is not installed. Please install it with 'pip install required_module'.")
```
