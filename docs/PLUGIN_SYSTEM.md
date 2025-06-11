# NetScout-Pi Plugin System

## Overview

The NetScout-Pi plugin system allows you to extend the functionality of the application with custom plugins. Each plugin is a standalone module that can be developed, installed, and managed independently.

## Plugin Structure

Plugins in NetScout-Pi are organized in a folder-based structure, where each plugin is contained in its own directory with the following components:

```
plugin_name/
├── plugin.py        # Main plugin implementation
└── config.json      # Plugin metadata and configuration
```

### plugin.py

The `plugin.py` file contains the implementation of your plugin, which should inherit from the `PluginBase` class. Here's an example:

```python
#!/usr/bin/env python3
# NetScout-Pi - Example Plugin

import os
import sys
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class ExamplePlugin(PluginBase):
    """
    Example plugin for NetScout-Pi.
    
    This serves as an example of a plugin implementation.
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
        self.name = self.metadata.get('name', 'example_plugin')
        self.description = self.metadata.get('description', 'Example plugin')
        self.version = self.metadata.get('version', '0.1.0')
        self.author = self.metadata.get('author', 'NetScout-Pi')
        self.permissions = self.metadata.get('permissions', [])
        self.category = self.metadata.get('category', 'general')
        self.tags = self.metadata.get('tags', [])
        
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
            
            # Example: Process arguments
            target = kwargs.get('target', 'example.com')
            self.logger.info(f"Target: {target}")
            
            # Set result data
            result['data'] = {
                'example': 'data',
                'value': 42,
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

### config.json

The `config.json` file contains the plugin metadata and configuration. Here's an example:

```json
{
    "metadata": {
        "name": "example_plugin",
        "description": "Example plugin for NetScout-Pi",
        "version": "0.1.0",
        "author": "NetScout-Pi",
        "permissions": [],
        "category": "general",
        "tags": ["example", "demo"]
    },
    "settings": {
        "enabled": true,
        "example_setting": "example_value",
        "timeout": 30
    }
}
```

## Plugin Manager

The `NewPluginManager` is responsible for discovering, loading, and running plugins. It scans the plugin directories for plugin folders and loads the available plugins based on their configuration.

## Creating a New Plugin

To create a new plugin, you can use the template provided in `src/plugins_new/template` as a starting point. Copy the template folder to a new location, and modify the `plugin.py` and `config.json` files to implement your custom functionality.

Alternatively, you can use the `create_plugin_from_template` method in the `NewPluginManager` class to create a new plugin:

```python
from src.core.new_plugin_manager import NewPluginManager

# Initialize plugin manager
plugin_manager = NewPluginManager(config)

# Create a new plugin from template
plugin_info = plugin_manager.create_plugin_from_template(
    plugin_name="my_custom_plugin",
    description="My custom plugin description",
    author="Your Name",
    category="custom"
)
```

## Installing a Plugin

Plugins can be installed by copying the plugin folder to one of the plugin directories:

- `src/plugins_new`: System plugins directory
- `plugins`: User plugins directory

You can also use the `install_plugin` method in the `NewPluginManager` class to install a plugin:

```python
from src.core.new_plugin_manager import NewPluginManager

# Initialize plugin manager
plugin_manager = NewPluginManager(config)

# Install a plugin
plugin_info = plugin_manager.install_plugin(
    source_dir="/path/to/plugin",
    overwrite=False
)
```

## Running a Plugin

Plugins can be run using the `run_plugin` method in the `NewPluginManager` class:

```python
from src.core.new_plugin_manager import NewPluginManager

# Initialize plugin manager
plugin_manager = NewPluginManager(config)

# Run a plugin
run_id = plugin_manager.run_plugin(
    plugin_name="example_plugin",
    target="example.com",
    timeout=30
)
```

## Plugin Lifecycle

1. **Discovery**: The plugin manager scans the plugin directories for plugin folders containing `plugin.py` and `config.json` files.
2. **Loading**: When a plugin is requested, the plugin manager loads the plugin class and creates an instance with the specified configuration.
3. **Execution**: The plugin's `run` method is called with the provided arguments.
4. **Result**: The plugin returns a result dictionary with the execution results.

## Plugin API

### PluginBase

The `PluginBase` class provides the following methods and attributes:

- `__init__(config, logger)`: Initialize the plugin with the specified configuration and logger.
- `run(**kwargs)`: Run the plugin with the specified arguments.
- `async_run(callback=None, progress_callback=None, **kwargs)`: Run the plugin asynchronously.
- `update_progress(progress, status=None)`: Update the progress of the plugin execution.
- `stop()`: Stop the plugin execution if it's running.
- `get_status()`: Get the current status of the plugin.

### PluginLogger

The `PluginLogger` class provides logging functionality for plugins:

- `log(message, level='INFO')`: Log a message with the specified level.
- `info(message)`: Log an info message.
- `warning(message)`: Log a warning message.
- `error(message)`: Log an error message.
- `debug(message)`: Log a debug message.
- `get_timestamp()`: Get the current timestamp.
- `start_run()`: Start a new run and initialize run metadata.
- `save_result(result)`: Save the plugin execution result.
- `save_error(error)`: Save an error that occurred during plugin execution.

## Plugin Permissions

Plugins can specify required permissions in their `config.json` file. These permissions are used to determine whether the plugin can be run based on the user's permissions.

Available permissions:

- `sudo`: The plugin requires sudo privileges.
- `network`: The plugin requires network access.
- `file_system`: The plugin requires file system access.
- `system`: The plugin requires system access (e.g., executing system commands).

## Plugin Categories

Plugins can be organized into categories based on their functionality. The following categories are available:

- `network`: Network-related plugins (e.g., ping, traceroute, port scan).
- `system`: System-related plugins (e.g., hardware info, disk usage).
- `security`: Security-related plugins (e.g., vulnerability scan, firewall test).
- `monitoring`: Monitoring plugins (e.g., bandwidth monitor, uptime monitor).
- `general`: General-purpose plugins.
- `custom`: Custom plugins created by users.

## Plugin Tags

Plugins can be tagged with keywords to make them easier to find and categorize. Tags are specified in the `config.json` file under the `metadata.tags` field.

## Plugin Settings

Plugin settings are specified in the `config.json` file under the `settings` field. These settings can be overridden by system-wide configuration settings, which are specified in the application configuration file under the `plugins.<plugin_name>` section.
