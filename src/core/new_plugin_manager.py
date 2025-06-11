#!/usr/bin/env python3
# NetScout-Pi - New Plugin Manager Implementation

import os
import sys
import importlib.util
import inspect
import logging
import json
import uuid
import threading
import time
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Callable, Union

from src.core.logger import PluginLogger

class NewPluginManager:
    """Manages plugin discovery, loading, and execution with folder-based structure."""
    
    def __init__(self, config, log_dir=None):
        """Initialize plugin manager.
        
        Args:
            config: Application configuration.
            log_dir (str, optional): Directory for plugin logs and results.
        """
        self.config = config
        self.plugins = {}
        self.loaded_instances = {}
        self.active_runs = {}
        self.logger = logging.getLogger(__name__)
        
        # Set plugin directories
        self.plugin_dirs = config.get('plugins.directories', [])
        if not self.plugin_dirs:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.plugin_dirs = [
                os.path.join(base_dir, 'src', 'plugins_new'),
                os.path.join(base_dir, 'plugins')
            ]
            
        # Add user plugins directory
        user_plugins_dir = config.get('plugins.user_directory')
        if user_plugins_dir:
            os.makedirs(user_plugins_dir, exist_ok=True)
            if user_plugins_dir not in self.plugin_dirs:
                self.plugin_dirs.append(user_plugins_dir)
        
        # Set log directory
        self.log_dir = log_dir or config.get('logging.directory')
        if not self.log_dir:
            self.log_dir = os.path.join(Path(__file__).resolve().parent.parent.parent, 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Load plugins
        self.discover_plugins()
    
    def discover_plugins(self):
        """Discover available plugins in plugin directories.
        
        This method scans the plugin directories for plugin folders containing
        a plugin.py file and a config.json file.
        """
        self.plugins = {}
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                self.logger.warning(f"Plugin directory does not exist: {plugin_dir}")
                continue
                
            self.logger.info(f"Scanning for plugins in: {plugin_dir}")
            
            # Get subdirectories (plugin folders)
            for item in os.listdir(plugin_dir):
                folder_path = os.path.join(plugin_dir, item)
                
                # Skip non-directories and those starting with underscore
                if not os.path.isdir(folder_path) or item.startswith('_'):
                    continue
                
                # Check for plugin.py and config.json
                plugin_file = os.path.join(folder_path, 'plugin.py')
                config_file = os.path.join(folder_path, 'config.json')
                
                if not os.path.exists(plugin_file):
                    self.logger.warning(f"Missing plugin.py in: {folder_path}")
                    continue
                    
                if not os.path.exists(config_file):
                    self.logger.warning(f"Missing config.json in: {folder_path}")
                    continue
                
                # Load plugin configuration
                try:
                    with open(config_file, 'r') as f:
                        plugin_config = json.load(f)
                    
                    # Extract metadata
                    metadata = plugin_config.get('metadata', {})
                    if not metadata.get('name'):
                        self.logger.warning(f"Missing plugin name in config: {config_file}")
                        continue
                        
                    plugin_name = metadata['name']
                    
                    # Try to load the plugin class
                    plugin_class = self._load_plugin_class(Path(plugin_file))
                    
                    if plugin_class:
                        self.plugins[plugin_name] = {
                            'class': plugin_class,
                            'folder_path': folder_path,
                            'file_path': plugin_file,
                            'config_file': config_file,
                            'dir_path': folder_path,  # Add dir_path for easier config.json access
                            'metadata': metadata,
                            'settings': plugin_config.get('settings', {}),
                            'enabled': plugin_config.get('settings', {}).get('enabled', True),
                            'available': True,
                            'error': None
                        }
                        self.logger.info(f"Discovered plugin: {plugin_name} v{metadata.get('version', '0.1.0')}")
                    else:
                        self.logger.warning(f"Failed to load plugin class from: {plugin_file}")
                        self.plugins[plugin_name] = {
                            'class': None,
                            'folder_path': folder_path,
                            'file_path': plugin_file,
                            'config_file': config_file,
                            'dir_path': folder_path,  # Add dir_path for easier config.json access
                            'metadata': metadata,
                            'settings': plugin_config.get('settings', {}),
                            'enabled': False,
                            'available': False,
                            'error': "Failed to load plugin class"
                        }
                        
                except Exception as e:
                    self.logger.error(f"Error loading plugin from {folder_path}: {str(e)}")
                    # Try to extract plugin name from directory name if config loading failed
                    plugin_name = item.lower()
                    self.plugins[plugin_name] = {
                        'class': None,
                        'folder_path': folder_path,
                        'file_path': plugin_file,
                        'config_file': config_file,
                        'dir_path': folder_path,  # Add dir_path for easier config.json access
                        'metadata': {
                            'name': plugin_name,
                            'description': 'Plugin failed to load',
                            'version': 'Unknown',
                            'author': 'Unknown'
                        },
                        'enabled': False,
                        'available': False,
                        'error': str(e)
                    }
        
        self.logger.info(f"Discovered {len(self.plugins)} plugins")
        return self.plugins
    
    def _load_plugin_class(self, file_path):
        """Load plugin class from file.
        
        Args:
            file_path (Path): Path to plugin.py file.
            
        Returns:
            Type: Plugin class or None if not found.
        """
        try:
            # Generate a unique module name
            module_name = f"plugin_{file_path.parent.name}_{uuid.uuid4().hex[:8]}"
            
            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class (looking for any class that inherits from PluginBase)
            from src.core.plugin_manager import PluginBase
            
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginBase) and 
                    obj is not PluginBase and 
                    hasattr(obj, 'run')):
                    return obj
                    
            self.logger.warning(f"No valid plugin class found in {file_path}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading plugin from {file_path}: {str(e)}")
            return None
    
    def get_plugin_info(self, plugin_name):
        """Get information about a plugin.
        
        Args:
            plugin_name (str): Name of the plugin.
            
        Returns:
            dict: Plugin information or None if not found.
        """
        if plugin_name not in self.plugins:
            return None
            
        plugin_info = self.plugins[plugin_name].copy()
        plugin_info.pop('class', None)  # Remove class object
        
        # Add system-wide configuration
        system_config = self.config.get(f'plugins.{plugin_name}', {})
        plugin_info['system_config'] = system_config
        
        # Read metadata from config.json if it exists
        plugin_dir_path = plugin_info.get('dir_path')
        if plugin_dir_path and os.path.exists(plugin_dir_path):
            config_json_path = os.path.join(plugin_dir_path, 'config.json')
            if os.path.exists(config_json_path):
                try:
                    with open(config_json_path, 'r') as f:
                        config_data = json.load(f)
                        # Update metadata with config.json content
                        if 'metadata' in config_data:
                            plugin_info['metadata'] = config_data['metadata']
                        if 'settings' in config_data:
                            plugin_info['settings'] = config_data['settings']
                except Exception as e:
                    self.logger.error(f"Error reading config.json for plugin {plugin_name}: {e}")
        
        # Add status
        if plugin_name in self.loaded_instances:
            instance = self.loaded_instances[plugin_name]
            plugin_info['status'] = instance.get_status()
        else:
            plugin_info['status'] = {
                'running': False,
                'progress': 0,
                'status': 'not_loaded' if plugin_info.get('available', True) else 'unavailable'
            }
            
        # Add availability information
        if not plugin_info.get('available', True):
            plugin_info['status']['status'] = 'unavailable'
            plugin_info['status']['error'] = plugin_info.get('error', 'Unknown error')
            
        return plugin_info
    
    def get_all_plugins(self):
        """Get information about all plugins.
        
        Returns:
            dict: Dictionary of plugin information.
        """
        return {name: self.get_plugin_info(name) for name in self.plugins}
    
    def get_plugin_status(self, plugin_name):
        """Get status information about a plugin.
        
        Args:
            plugin_name (str): Name of the plugin.
            
        Returns:
            dict: Status information or None if not found.
        """
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            return None
            
        # Get plugin instance if loaded
        plugin = self.loaded_instances.get(plugin_name)
        
        # Add additional status information
        status = {
            'name': plugin_name,
            'metadata': plugin_info.get('metadata', {}),
            'enabled': plugin_info.get('enabled', True),
            'available': plugin_info.get('available', True),
            'error': plugin_info.get('error'),
            'file_path': plugin_info.get('folder_path'),
            'config_file': plugin_info.get('config_file'),
            'status': plugin_info.get('status', {})
        }
        
        # Add recent results if available
        recent_results = []
        log_dir = os.path.join(self.log_dir, plugin_name)
        if os.path.exists(log_dir):
            results_dir = os.path.join(log_dir, 'results')
            if os.path.exists(results_dir):
                try:
                    # Get list of result files
                    result_files = sorted(
                        [f for f in os.listdir(results_dir) if f.endswith('.json')],
                        key=lambda x: os.path.getmtime(os.path.join(results_dir, x)),
                        reverse=True
                    )
                    
                    # Get the 5 most recent results
                    for result_file in result_files[:5]:
                        result_path = os.path.join(results_dir, result_file)
                        try:
                            with open(result_path, 'r') as f:
                                result = json.load(f)
                                recent_results.append(result)
                        except Exception as e:
                            self.logger.warning(f"Error reading result file {result_path}: {str(e)}")
                except Exception as e:
                    self.logger.warning(f"Error getting recent results for {plugin_name}: {str(e)}")
        
        status['recent_results'] = recent_results
        
        return status
    
    def load_plugin(self, plugin_name):
        """Load a plugin instance.
        
        Args:
            plugin_name (str): Name of the plugin.
            
        Returns:
            object: Plugin instance or None if not found or unavailable.
        """
        if plugin_name not in self.plugins:
            self.logger.error(f"Plugin not found: {plugin_name}")
            return None
            
        # Check if plugin is available
        if not self.plugins[plugin_name].get('available', True):
            error_msg = self.plugins[plugin_name].get('error', 'Unknown error')
            self.logger.error(f"Cannot load unavailable plugin {plugin_name}: {error_msg}")
            return None
            
        # Return existing instance if already loaded
        if plugin_name in self.loaded_instances:
            return self.loaded_instances[plugin_name]
            
        try:
            # Get plugin class and create instance
            plugin_class = self.plugins[plugin_name]['class']
            if not plugin_class:
                self.logger.error(f"Plugin class not found for {plugin_name}")
                return None
            
            # Merge plugin settings from config.json with system-wide settings
            plugin_settings = self.plugins[plugin_name].get('settings', {}).copy()
            system_settings = self.config.get(f'plugins.{plugin_name}', {})
            plugin_settings.update(system_settings)
            
            # Create a merged config object with metadata and settings
            plugin_config = {
                'metadata': self.plugins[plugin_name].get('metadata', {}),
                'settings': plugin_settings
            }
            
            # Create plugin logger
            plugin_logger = PluginLogger(
                plugin_name, 
                log_dir=os.path.join(self.log_dir, plugin_name)
            )
            
            # Initialize run metadata in logger
            plugin_logger.start_run()
            
            # Create plugin instance
            plugin_instance = plugin_class(plugin_config, plugin_logger)
            self.loaded_instances[plugin_name] = plugin_instance
            
            return plugin_instance
            
        except Exception as e:
            self.logger.error(f"Error loading plugin {plugin_name}: {str(e)}")
            # Mark plugin as unavailable due to runtime error
            self.plugins[plugin_name]['available'] = False
            self.plugins[plugin_name]['error'] = str(e)
            return None
    
    def run_plugin(self, plugin_name, callback=None, progress_callback=None, **kwargs):
        """Run a plugin.
        
        Args:
            plugin_name (str): Name of the plugin.
            callback (callable, optional): Function to call with result when done.
            progress_callback (callable, optional): Function to call with progress updates.
            **kwargs: Additional arguments to pass to the plugin.
            
        Returns:
            str: Run ID if started successfully, None otherwise.
        """
        # Load plugin if not already loaded
        plugin = self.load_plugin(plugin_name)
        if not plugin:
            return None
            
        # Check if plugin is already running
        if plugin.running:
            self.logger.warning(f"Plugin {plugin_name} is already running")
            return None
            
        # Run plugin asynchronously
        run_id = plugin.async_run(
            callback=callback,
            progress_callback=progress_callback,
            **kwargs
        )
        
        if run_id:
            self.active_runs[run_id] = {
                'plugin_name': plugin_name,
                'start_time': time.time(),
                'kwargs': kwargs
            }
            
            self.logger.info(f"Started plugin {plugin_name} with run ID {run_id}")
            return run_id
            
        return None
        
    def stop_plugin(self, plugin_name):
        """Stop a running plugin.
        
        Args:
            plugin_name (str): Name of the plugin.
            
        Returns:
            bool: True if plugin was stopped, False otherwise.
        """
        if plugin_name not in self.loaded_instances:
            self.logger.warning(f"Cannot stop plugin {plugin_name}: not loaded")
            return False
            
        plugin = self.loaded_instances[plugin_name]
        if not plugin.running:
            self.logger.warning(f"Cannot stop plugin {plugin_name}: not running")
            return False
            
        try:
            plugin.stop()
            self.logger.info(f"Stopped plugin {plugin_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error stopping plugin {plugin_name}: {e}")
            return False
            
        return run_id
    
    def get_plugin(self, plugin_name):
        """Get a plugin instance by name.
        
        Args:
            plugin_name (str): Name of the plugin.
            
        Returns:
            object: Plugin instance or None if not found.
        """
        if plugin_name not in self.plugins:
            self.logger.warning(f"Plugin not found: {plugin_name}")
            return None
            
        return self.load_plugin(plugin_name)
    
    def install_plugin(self, source_dir, overwrite=False):
        """Install a plugin from a directory.
        
        Args:
            source_dir (str): Path to plugin directory containing plugin.py and config.json.
            overwrite (bool, optional): Whether to overwrite existing plugin.
            
        Returns:
            dict: Plugin info if successful, None otherwise.
        """
        try:
            # Check if directory exists
            if not os.path.isdir(source_dir):
                self.logger.error(f"Plugin directory not found: {source_dir}")
                return None
                
            # Check for plugin.py and config.json
            plugin_file = os.path.join(source_dir, 'plugin.py')
            config_file = os.path.join(source_dir, 'config.json')
            
            if not os.path.exists(plugin_file):
                self.logger.error(f"Missing plugin.py in: {source_dir}")
                return None
                
            if not os.path.exists(config_file):
                self.logger.error(f"Missing config.json in: {source_dir}")
                return None
                
            # Load plugin configuration to get name
            with open(config_file, 'r') as f:
                plugin_config = json.load(f)
                
            plugin_name = plugin_config.get('metadata', {}).get('name')
            if not plugin_name:
                self.logger.error(f"Missing plugin name in config: {config_file}")
                return None
                
            # Check if plugin already exists
            if plugin_name in self.plugins and not overwrite:
                self.logger.error(f"Plugin {plugin_name} already exists")
                return None
                
            # Get user plugins directory
            user_plugins_dir = self.config.get('plugins.user_directory')
            if not user_plugins_dir:
                user_plugins_dir = os.path.join(Path(__file__).resolve().parent.parent.parent, 'plugins')
            os.makedirs(user_plugins_dir, exist_ok=True)
            
            # Create destination directory
            dest_dir = os.path.join(user_plugins_dir, os.path.basename(source_dir))
            if os.path.exists(dest_dir) and overwrite:
                shutil.rmtree(dest_dir)
            elif os.path.exists(dest_dir):
                self.logger.error(f"Destination directory already exists: {dest_dir}")
                return None
                
            # Copy plugin directory
            shutil.copytree(source_dir, dest_dir)
            
            # Reload plugins
            self.discover_plugins()
            
            return self.get_plugin_info(plugin_name)
            
        except Exception as e:
            self.logger.error(f"Error installing plugin: {str(e)}")
            return None
    
    def create_plugin_from_template(self, plugin_name, description=None, author=None, category=None):
        """Create a new plugin from the template.
        
        Args:
            plugin_name (str): Name of the new plugin.
            description (str, optional): Plugin description.
            author (str, optional): Plugin author.
            category (str, optional): Plugin category.
            
        Returns:
            dict: Plugin info if successful, None otherwise.
        """
        try:
            # Validate plugin name
            if not plugin_name or not re.match(r'^[a-z][a-z0-9_]*$', plugin_name):
                self.logger.error(f"Invalid plugin name: {plugin_name}. Must start with a letter and contain only lowercase letters, numbers, and underscores.")
                return None
                
            # Check if plugin already exists
            if plugin_name in self.plugins:
                self.logger.error(f"Plugin {plugin_name} already exists")
                return None
                
            # Get template directory
            base_dir = Path(__file__).resolve().parent.parent.parent
            template_dir = os.path.join(base_dir, 'src', 'plugins_new', 'template')
            
            if not os.path.exists(template_dir):
                self.logger.error(f"Template directory not found: {template_dir}")
                return None
                
            # Get user plugins directory
            user_plugins_dir = self.config.get('plugins.user_directory')
            if not user_plugins_dir:
                user_plugins_dir = os.path.join(base_dir, 'plugins')
            os.makedirs(user_plugins_dir, exist_ok=True)
            
            # Create destination directory
            dest_dir = os.path.join(user_plugins_dir, plugin_name)
            if os.path.exists(dest_dir):
                self.logger.error(f"Destination directory already exists: {dest_dir}")
                return None
                
            # Copy template directory
            shutil.copytree(template_dir, dest_dir)
            
            # Update config.json
            config_file = os.path.join(dest_dir, 'config.json')
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            config['metadata']['name'] = plugin_name
            if description:
                config['metadata']['description'] = description
            if author:
                config['metadata']['author'] = author
            if category:
                config['metadata']['category'] = category
                
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            # Update plugin.py
            plugin_file = os.path.join(dest_dir, 'plugin.py')
            with open(plugin_file, 'r') as f:
                content = f.read()
                
            # Replace class name and comments
            content = content.replace('PluginTemplate', f"{plugin_name.title().replace('_', '')}Plugin")
            content = content.replace('Template plugin for NetScout-Pi', description or f"{plugin_name} plugin for NetScout-Pi")
            
            with open(plugin_file, 'w') as f:
                f.write(content)
                
            # Reload plugins
            self.discover_plugins()
            
            return self.get_plugin_info(plugin_name)
            
        except Exception as e:
            self.logger.error(f"Error creating plugin: {str(e)}")
            return None
