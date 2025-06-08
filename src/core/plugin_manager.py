#!/usr/bin/env python3
# NetProbe Pi - Plugin Manager

import os
import sys
import importlib.util
import inspect
import logging
import json
import yaml
import uuid
import threading
import time
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Callable, Union

from src.core.logger import PluginLogger

class PluginBase:
    """Base class for NetProbe plugins."""
    
    # Plugin metadata (to be overridden by subclasses)
    name = "base_plugin"
    description = "Base plugin class"
    version = "0.1.0"
    author = "NetProbe"
    permissions = []
    category = "general"
    tags = []
    
    def __init__(self, config, logger):
        """Initialize plugin.
        
        Args:
            config: Plugin configuration.
            logger: PluginLogger instance.
        """
        self.config = config
        self.logger = logger
        self.running = False
        self.run_thread = None
        self.result = None
        self.progress = 0
        self.status = 'idle'
        self.run_id = None
    
    def run(self, **kwargs):
        """Run the plugin.
        
        Args:
            **kwargs: Additional arguments.
            
        Returns:
            dict: Plugin result.
        """
        raise NotImplementedError("Plugin must implement run() method")
    
    def async_run(self, callback=None, progress_callback=None, **kwargs):
        """Run the plugin asynchronously.
        
        Args:
            callback (callable, optional): Function to call with result when done.
            progress_callback (callable, optional): Function to call with progress updates.
            **kwargs: Additional arguments.
            
        Returns:
            str: Run ID if started successfully, None otherwise.
        """
        if self.running:
            return None
        
        self.running = True
        self.status = 'running'
        self.progress = 0
        self.run_id = str(uuid.uuid4())
        
        self.run_thread = threading.Thread(
            target=self._run_wrapper,
            args=(callback, progress_callback),
            kwargs=kwargs
        )
        self.run_thread.daemon = True
        self.run_thread.start()
        return self.run_id
    
    def _run_wrapper(self, callback=None, progress_callback=None, **kwargs):
        """Wrapper for run() to handle logging and callbacks.
        
        Args:
            callback (callable, optional): Function to call with result when done.
            progress_callback (callable, optional): Function to call with progress updates.
            **kwargs: Additional arguments.
        """
        try:
            self.logger.log(f"Starting plugin execution: {self.name} v{self.version}")
            
            # Set initial progress
            self.progress = 0
            if progress_callback:
                progress_callback(self.run_id, self.progress, 'starting')
            
            # Run the plugin
            result = self.run(**kwargs)
            
            # Add run metadata
            if isinstance(result, dict):
                result['run_id'] = self.run_id
                result['plugin'] = {
                    'name': self.name,
                    'version': self.version,
                    'description': self.description,
                    'author': self.author
                }
                result['execution_time'] = time.time() - self.logger.run_start_time
            
            self.result = result
            self.logger.save_result(result)
            self.logger.log(f"Plugin execution completed: {self.name}")
            
            # Set final progress
            self.progress = 100
            self.status = 'completed'
            if progress_callback:
                progress_callback(self.run_id, 100, 'completed')
            
            if callback:
                callback(result)
                
        except Exception as e:
            error_msg = f"Plugin execution failed: {str(e)}"
            self.logger.log(error_msg, level='ERROR')
            self.logger.save_error(error_msg)
            
            # Set error progress
            self.status = 'error'
            if progress_callback:
                progress_callback(self.run_id, self.progress, 'error', str(e))
        
        finally:
            self.running = False
    
    def update_progress(self, progress, status=None):
        """Update the progress of the plugin execution.
        
        Args:
            progress (int): Progress percentage (0-100).
            status (str, optional): Status message.
        """
        self.progress = min(max(0, progress), 100)
        if status:
            self.status = status
        
    def stop(self):
        """Stop the plugin execution if it's running."""
        if self.running and self.run_thread and self.run_thread.is_alive():
            self.logger.log(f"Attempting to stop plugin execution: {self.name}", level='WARNING')
            self.running = False
            # We can't forcibly stop a thread in Python, but we can signal it to stop
            # The plugin implementation should check self.running periodically
            return True
        return False
    
    def get_status(self):
        """Get the current status of the plugin.
        
        Returns:
            dict: Status information.
        """
        return {
            'name': self.name,
            'running': self.running,
            'progress': self.progress,
            'status': self.status,
            'run_id': self.run_id
        }


class PluginManager:
    """Manages plugin discovery, loading, and execution."""
    
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
                os.path.join(base_dir, 'src', 'plugins'),
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
        
        # Plugin schemas
        self.metadata_schema = {
            'name': {'type': str, 'required': True},
            'description': {'type': str, 'required': True},
            'version': {'type': str, 'required': True},
            'author': {'type': str, 'required': True},
            'permissions': {'type': list, 'required': False},
            'category': {'type': str, 'required': False},
            'tags': {'type': list, 'required': False}
        }
        
        # Load plugins
        self.discover_plugins()
    
    def discover_plugins(self):
        """Discover available plugins in plugin directories."""
        self.plugins = {}
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                self.logger.warning(f"Plugin directory does not exist: {plugin_dir}")
                continue
                
            self.logger.info(f"Scanning for plugins in: {plugin_dir}")
            
            # Get Python files in directory
            for file_path in Path(plugin_dir).glob('*.py'):
                if file_path.name.startswith('__'):
                    continue
                    
                try:
                    plugin_class = self._load_plugin_class(file_path)
                    if plugin_class:
                        plugin_name = plugin_class.name
                        self.plugins[plugin_name] = {
                            'class': plugin_class,
                            'file_path': str(file_path),
                            'module_name': file_path.stem,
                            'metadata': self._extract_metadata(plugin_class),
                            'enabled': self.config.get(f'plugins.{plugin_name}.enabled', True)
                        }
                        self.logger.info(f"Discovered plugin: {plugin_name} v{plugin_class.version}")
                except Exception as e:
                    self.logger.error(f"Error loading plugin from {file_path}: {str(e)}")
        
        self.logger.info(f"Discovered {len(self.plugins)} plugins")
        return self.plugins
    
    def _load_plugin_class(self, file_path):
        """Load plugin class from file.
        
        Args:
            file_path (Path): Path to plugin file.
            
        Returns:
            Type[PluginBase]: Plugin class or None if not found.
        """
        try:
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin class (subclass of PluginBase)
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and issubclass(obj, PluginBase) and 
                    obj is not PluginBase and hasattr(obj, 'run')):
                    return obj
                    
            self.logger.warning(f"No valid plugin class found in {file_path}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading plugin from {file_path}: {str(e)}")
            return None
    
    def _extract_metadata(self, plugin_class):
        """Extract metadata from plugin class.
        
        Args:
            plugin_class (Type[PluginBase]): Plugin class.
            
        Returns:
            dict: Plugin metadata.
        """
        metadata = {}
        
        for field, props in self.metadata_schema.items():
            if hasattr(plugin_class, field):
                value = getattr(plugin_class, field)
                metadata[field] = value
            elif props.get('required', False):
                default_value = '' if props['type'] == str else [] if props['type'] == list else None
                metadata[field] = default_value
                self.logger.warning(f"Plugin {plugin_class.__name__} missing required metadata: {field}")
        
        return metadata
    
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
        
        # Add configuration
        plugin_info['config'] = self.config.get(f'plugins.{plugin_name}', {})
        
        # Add status
        if plugin_name in self.loaded_instances:
            instance = self.loaded_instances[plugin_name]
            plugin_info['status'] = instance.get_status()
        else:
            plugin_info['status'] = {
                'running': False,
                'progress': 0,
                'status': 'not_loaded'
            }
            
        return plugin_info
    
    def get_all_plugins(self):
        """Get information about all plugins.
        
        Returns:
            dict: Dictionary of plugin information.
        """
        return {name: self.get_plugin_info(name) for name in self.plugins}
    
    def load_plugin(self, plugin_name):
        """Load a plugin instance.
        
        Args:
            plugin_name (str): Name of the plugin.
            
        Returns:
            PluginBase: Plugin instance or None if not found.
        """
        if plugin_name not in self.plugins:
            self.logger.error(f"Plugin not found: {plugin_name}")
            return None
            
        # Return existing instance if already loaded
        if plugin_name in self.loaded_instances:
            return self.loaded_instances[plugin_name]
            
        try:
            # Get plugin class and create instance
            plugin_class = self.plugins[plugin_name]['class']
            plugin_config = self.config.get(f'plugins.{plugin_name}', {})
            
            # Create plugin logger
            plugin_logger = PluginLogger(
                plugin_name, 
                log_dir=os.path.join(self.log_dir, plugin_name)
            )
            
            # Create plugin instance
            plugin_instance = plugin_class(plugin_config, plugin_logger)
            self.loaded_instances[plugin_name] = plugin_instance
            
            return plugin_instance
            
        except Exception as e:
            self.logger.error(f"Error loading plugin {plugin_name}: {str(e)}")
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
    
    def run_plugin_sync(self, plugin_name, **kwargs):
        """Run a plugin synchronously.
        
        Args:
            plugin_name (str): Name of the plugin.
            **kwargs: Additional arguments to pass to the plugin.
            
        Returns:
            dict: Plugin result or None if error.
        """
        # Load plugin if not already loaded
        plugin = self.load_plugin(plugin_name)
        if not plugin:
            return None
            
        # Check if plugin is already running
        if plugin.running:
            self.logger.warning(f"Plugin {plugin_name} is already running")
            return None
            
        try:
            # Run plugin synchronously
            plugin.running = True
            plugin.status = 'running'
            plugin.progress = 0
            plugin.run_id = str(uuid.uuid4())
            
            self.logger.info(f"Running plugin {plugin_name} synchronously")
            result = plugin.run(**kwargs)
            
            # Add run metadata
            if isinstance(result, dict):
                result['run_id'] = plugin.run_id
                result['plugin'] = {
                    'name': plugin.name,
                    'version': plugin.version,
                    'description': plugin.description,
                    'author': plugin.author
                }
            
            plugin.result = result
            plugin.status = 'completed'
            plugin.progress = 100
            plugin.logger.save_result(result)
            
            return result
            
        except Exception as e:
            plugin.status = 'error'
            error_msg = f"Error running plugin {plugin_name}: {str(e)}"
            self.logger.error(error_msg)
            plugin.logger.save_error(error_msg)
            return None
            
        finally:
            plugin.running = False
    
    def stop_plugin(self, plugin_name):
        """Stop a running plugin.
        
        Args:
            plugin_name (str): Name of the plugin.
            
        Returns:
            bool: True if stopped, False otherwise.
        """
        if plugin_name not in self.loaded_instances:
            return False
            
        plugin = self.loaded_instances[plugin_name]
        return plugin.stop()
    
    def stop_all_plugins(self):
        """Stop all running plugins.
        
        Returns:
            int: Number of plugins stopped.
        """
        count = 0
        for plugin_name, plugin in self.loaded_instances.items():
            if plugin.stop():
                count += 1
                
        return count
    
    def get_plugin_result(self, plugin_name, run_id=None):
        """Get the result of a plugin run.
        
        Args:
            plugin_name (str): Name of the plugin.
            run_id (str, optional): Run ID. If None, get the most recent result.
            
        Returns:
            dict: Plugin result or None if not found.
        """
        if plugin_name not in self.loaded_instances:
            return None
            
        plugin = self.loaded_instances[plugin_name]
        
        if run_id:
            # Get specific run result from log
            return plugin.logger.get_result(run_id)
        else:
            # Get most recent result
            return plugin.result
    
    def get_plugin_results(self, plugin_name, limit=10):
        """Get recent results for a plugin.
        
        Args:
            plugin_name (str): Name of the plugin.
            limit (int, optional): Maximum number of results to return.
            
        Returns:
            list: List of plugin results.
        """
        if plugin_name not in self.plugins:
            return []
            
        # Ensure plugin logger is initialized
        if plugin_name not in self.loaded_instances:
            self.load_plugin(plugin_name)
            
        if plugin_name not in self.loaded_instances:
            return []
            
        plugin = self.loaded_instances[plugin_name]
        return plugin.logger.get_results(limit)
    
    def get_run_status(self, run_id):
        """Get the status of a plugin run.
        
        Args:
            run_id (str): Run ID.
            
        Returns:
            dict: Run status or None if not found.
        """
        if run_id not in self.active_runs:
            # Check if it's a completed run
            for plugin_name in self.loaded_instances:
                plugin = self.loaded_instances[plugin_name]
                if plugin.run_id == run_id:
                    return {
                        'run_id': run_id,
                        'plugin_name': plugin_name,
                        'status': plugin.status,
                        'progress': plugin.progress
                    }
            return None
            
        run_info = self.active_runs[run_id]
        plugin_name = run_info['plugin_name']
        
        if plugin_name not in self.loaded_instances:
            return None
            
        plugin = self.loaded_instances[plugin_name]
        
        return {
            'run_id': run_id,
            'plugin_name': plugin_name,
            'status': plugin.status,
            'progress': plugin.progress,
            'start_time': run_info['start_time'],
            'elapsed': time.time() - run_info['start_time']
        }
    
    def enable_plugin(self, plugin_name, enabled=True):
        """Enable or disable a plugin.
        
        Args:
            plugin_name (str): Name of the plugin.
            enabled (bool, optional): Whether to enable or disable the plugin.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        if plugin_name not in self.plugins:
            return False
            
        self.plugins[plugin_name]['enabled'] = enabled
        self.config.set(f'plugins.{plugin_name}.enabled', enabled)
        self.logger.info(f"Plugin {plugin_name} {'enabled' if enabled else 'disabled'}")
        return True
    
    def install_plugin(self, file_path, overwrite=False):
        """Install a plugin from a file.
        
        Args:
            file_path (str): Path to plugin file.
            overwrite (bool, optional): Whether to overwrite existing plugin.
            
        Returns:
            dict: Plugin info if successful, None otherwise.
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                self.logger.error(f"Plugin file not found: {file_path}")
                return None
                
            # Load plugin class to validate
            temp_plugin_class = self._load_plugin_class(Path(file_path))
            if not temp_plugin_class:
                self.logger.error(f"Invalid plugin file: {file_path}")
                return None
                
            plugin_name = temp_plugin_class.name
            
            # Check if plugin already exists
            if plugin_name in self.plugins and not overwrite:
                self.logger.error(f"Plugin {plugin_name} already exists")
                return None
                
            # Get user plugins directory
            user_plugins_dir = self.config.get('plugins.user_directory')
            if not user_plugins_dir:
                user_plugins_dir = os.path.join(Path(__file__).resolve().parent.parent.parent, 'plugins')
            os.makedirs(user_plugins_dir, exist_ok=True)
            
            # Copy plugin file to user plugins directory
            dest_path = os.path.join(user_plugins_dir, os.path.basename(file_path))
            shutil.copy2(file_path, dest_path)
            
            # Reload plugins
            self.discover_plugins()
            
            return self.get_plugin_info(plugin_name)
            
        except Exception as e:
            self.logger.error(f"Error installing plugin: {str(e)}")
            return None
    
    def uninstall_plugin(self, plugin_name):
        """Uninstall a plugin.
        
        Args:
            plugin_name (str): Name of the plugin.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        if plugin_name not in self.plugins:
            return False
            
        try:
            # Get plugin file path
            file_path = self.plugins[plugin_name]['file_path']
            
            # Check if plugin is in user plugins directory
            user_plugins_dir = self.config.get('plugins.user_directory')
            if not user_plugins_dir:
                user_plugins_dir = os.path.join(Path(__file__).resolve().parent.parent.parent, 'plugins')
                
            if not file_path.startswith(user_plugins_dir):
                self.logger.error(f"Cannot uninstall built-in plugin: {plugin_name}")
                return False
                
            # Stop plugin if running
            if plugin_name in self.loaded_instances:
                self.stop_plugin(plugin_name)
                del self.loaded_instances[plugin_name]
                
            # Delete plugin file
            os.remove(file_path)
            
            # Reload plugins
            del self.plugins[plugin_name]
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error uninstalling plugin: {str(e)}")
            return False
    
    def run_sequence(self, plugin_sequence, sequential=True, callback=None):
        """Run a sequence of plugins.
        
        Args:
            plugin_sequence (list): List of plugin names or dicts with plugin name and args.
            sequential (bool, optional): Whether to run plugins sequentially or in parallel.
            callback (callable, optional): Function to call with all results when done.
            
        Returns:
            str: Sequence ID if started successfully, None otherwise.
        """
        sequence_id = str(uuid.uuid4())
        results = {}
        
        def plugin_callback(result):
            """Callback for individual plugin results."""
            plugin_name = result.get('plugin', {}).get('name')
            if plugin_name:
                results[plugin_name] = result
                
                # If all plugins have completed, call the main callback
                if len(results) == len(plugin_sequence) and callback:
                    callback(sequence_id, results)
        
        # Parse plugin sequence
        parsed_sequence = []
        for item in plugin_sequence:
            if isinstance(item, dict):
                plugin_name = item.get('name')
                plugin_args = item.get('args', {})
            else:
                plugin_name = item
                plugin_args = {}
                
            if plugin_name in self.plugins:
                parsed_sequence.append((plugin_name, plugin_args))
            else:
                self.logger.warning(f"Plugin not found in sequence: {plugin_name}")
        
        if not parsed_sequence:
            self.logger.error("No valid plugins in sequence")
            return None
            
        # Run plugins
        if sequential:
            # Run plugins one after another
            self._run_sequential(parsed_sequence, 0, plugin_callback)
        else:
            # Run all plugins in parallel
            for plugin_name, plugin_args in parsed_sequence:
                self.run_plugin(plugin_name, callback=plugin_callback, **plugin_args)
                
        return sequence_id
    
    def _run_sequential(self, sequence, index, callback):
        """Run plugins sequentially.
        
        Args:
            sequence (list): List of (plugin_name, plugin_args) tuples.
            index (int): Current index in sequence.
            callback (callable): Function to call with each result.
        """
        if index >= len(sequence):
            return
            
        plugin_name, plugin_args = sequence[index]
        
        def seq_callback(result):
            """Callback for sequential plugin execution."""
            # Call the main callback
            if callback:
                callback(result)
                
            # Run the next plugin
            self._run_sequential(sequence, index + 1, callback)
            
        # Run the current plugin
        self.run_plugin(plugin_name, callback=seq_callback, **plugin_args)
        
    def get_plugin_by_capability(self, capability):
        """Get plugins that have a specific capability.
        
        Args:
            capability (str): Capability to look for.
            
        Returns:
            list: List of plugin names.
        """
        matches = []
        for plugin_name, plugin_info in self.plugins.items():
            metadata = plugin_info['metadata']
            
            # Check name, description, and tags
            if capability.lower() in plugin_name.lower():
                matches.append(plugin_name)
            elif capability.lower() in metadata['description'].lower():
                matches.append(plugin_name)
            elif 'tags' in metadata and capability.lower() in [t.lower() for t in metadata['tags']]:
                matches.append(plugin_name)
                
        return matches
        
    def export_results(self, plugin_name=None, format='json'):
        """Export plugin results.
        
        Args:
            plugin_name (str, optional): Name of the plugin. If None, export all results.
            format (str, optional): Export format ('json', 'csv', 'text').
            
        Returns:
            str: Path to exported file.
        """
        try:
            # Create exports directory
            exports_dir = os.path.join(Path(__file__).resolve().parent.parent.parent, 'exports')
            os.makedirs(exports_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if plugin_name:
                # Export results for a specific plugin
                if plugin_name not in self.plugins:
                    return None
                    
                results = self.get_plugin_results(plugin_name, limit=100)
                filename = f"{plugin_name}_results_{timestamp}.{format}"
                
            else:
                # Export results for all plugins
                results = {}
                for name in self.plugins:
                    plugin_results = self.get_plugin_results(name, limit=20)
                    if plugin_results:
                        results[name] = plugin_results
                        
                filename = f"all_results_{timestamp}.{format}"
                
            # Save to file
            file_path = os.path.join(exports_dir, filename)
            
            if format == 'json':
                with open(file_path, 'w') as f:
                    json.dump(results, f, indent=2)
                    
            elif format == 'csv':
                # CSV export is plugin-specific
                if plugin_name:
                    self._export_csv(file_path, results, plugin_name)
                else:
                    # For all plugins, export as JSON instead
                    file_path = os.path.join(exports_dir, f"all_results_{timestamp}.json")
                    with open(file_path, 'w') as f:
                        json.dump(results, f, indent=2)
                        
            elif format == 'text':
                with open(file_path, 'w') as f:
                    if plugin_name:
                        f.write(f"Results for plugin: {plugin_name}\n")
                        f.write("=" * 80 + "\n\n")
                        for result in results:
                            f.write(f"Run ID: {result.get('run_id', 'unknown')}\n")
                            f.write(f"Timestamp: {result.get('timestamp', 'unknown')}\n")
                            f.write("-" * 80 + "\n")
                            f.write(str(result) + "\n\n")
                    else:
                        for name, plugin_results in results.items():
                            f.write(f"Results for plugin: {name}\n")
                            f.write("=" * 80 + "\n\n")
                            for result in plugin_results:
                                f.write(f"Run ID: {result.get('run_id', 'unknown')}\n")
                                f.write(f"Timestamp: {result.get('timestamp', 'unknown')}\n")
                                f.write("-" * 80 + "\n")
                                f.write(str(result) + "\n\n")
                            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error exporting results: {str(e)}")
            return None
    
    def _export_csv(self, file_path, results, plugin_name):
        """Export plugin results to CSV.
        
        Args:
            file_path (str): Path to output file.
            results (list): List of results.
            plugin_name (str): Name of the plugin.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            import csv
            
            # Define CSV headers based on plugin type
            if plugin_name == 'ping_test':
                headers = ['timestamp', 'target', 'success', 'min', 'avg', 'max', 'packet_loss']
                rows = []
                
                for result in results:
                    for target_result in result.get('results', []):
                        row = {
                            'timestamp': result.get('timestamp', ''),
                            'target': target_result.get('target', ''),
                            'success': target_result.get('success', False),
                            'min': target_result.get('stats', {}).get('min'),
                            'avg': target_result.get('stats', {}).get('avg'),
                            'max': target_result.get('stats', {}).get('max'),
                            'packet_loss': target_result.get('packet_loss')
                        }
                        rows.append(row)
                        
            elif plugin_name == 'speed_test':
                headers = ['timestamp', 'download', 'upload', 'ping', 'server', 'isp']
                rows = []
                
                for result in results:
                    row = {
                        'timestamp': result.get('timestamp', ''),
                        'download': result.get('average', {}).get('download'),
                        'upload': result.get('average', {}).get('upload'),
                        'ping': result.get('average', {}).get('ping'),
                        'server': result.get('server_info', {}).get('name'),
                        'isp': result.get('client_info', {}).get('isp')
                    }
                    rows.append(row)
                    
            else:
                # Generic CSV export - use common fields
                if not results:
                    return False
                    
                # Use keys from first result as headers
                headers = list(results[0].keys())
                rows = results
                
            # Write CSV file
            with open(file_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for row in rows:
                    writer.writerow({k: row.get(k, '') for k in headers})
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {str(e)}")
            return False
