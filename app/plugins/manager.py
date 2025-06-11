"""
Plugin manager for NetScout-Pi-V2.
Handles loading, executing, and managing community plugins.
"""

import os
import sys
import json
import yaml
import shutil
import logging
import importlib.util
import zipfile
from typing import Dict, List, Any, Optional
from flask import current_app
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

class PluginManager:
    """
    Plugin manager class for handling community plugins.
    """
    def __init__(self, plugin_folder: str):
        """
        Initialize the plugin manager.
        
        Args:
            plugin_folder (str): The folder where plugins are stored.
        """
        self.plugin_folder = plugin_folder
        self.plugins = {}
        self.load_plugins()
        
    def load_plugins(self):
        """
        Load all plugins from the plugin folder.
        """
        logger.info(f"Loading plugins from {self.plugin_folder}")
        if not os.path.exists(self.plugin_folder):
            os.makedirs(self.plugin_folder, exist_ok=True)
            
        # Scan plugin folders
        for plugin_id in os.listdir(self.plugin_folder):
            plugin_path = os.path.join(self.plugin_folder, plugin_id)
            
            if not os.path.isdir(plugin_path):
                continue
                
            manifest_path = os.path.join(plugin_path, 'manifest.yaml')
            if not os.path.exists(manifest_path):
                logger.warning(f"Plugin {plugin_id} missing manifest.yaml, skipping")
                continue
                
            try:
                with open(manifest_path, 'r') as f:
                    manifest = yaml.safe_load(f)
                    
                # Validate manifest
                if not self._validate_manifest(manifest):
                    logger.warning(f"Plugin {plugin_id} has invalid manifest, skipping")
                    continue
                    
                # Load the plugin
                main_module = manifest.get('main_module', 'main')
                module_path = os.path.join(plugin_path, f"{main_module}.py")
                
                if not os.path.exists(module_path):
                    logger.warning(f"Plugin {plugin_id} missing main module {main_module}.py, skipping")
                    continue
                
                # Load the plugin module
                spec = importlib.util.spec_from_file_location(
                    f"app.plugins.{plugin_id}.{main_module}", 
                    module_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Check if the module has the required functions
                if not hasattr(module, 'execute'):
                    logger.warning(f"Plugin {plugin_id} missing execute function, skipping")
                    continue
                    
                # Store the plugin
                self.plugins[plugin_id] = {
                    'id': plugin_id,
                    'name': manifest.get('name', plugin_id),
                    'description': manifest.get('description', ''),
                    'version': manifest.get('version', '0.0.1'),
                    'author': manifest.get('author', 'Unknown'),
                    'homepage': manifest.get('homepage', ''),
                    'module': module,
                    'manifest': manifest
                }
                
                logger.info(f"Successfully loaded plugin: {plugin_id}")
                
            except Exception as e:
                logger.error(f"Error loading plugin {plugin_id}: {str(e)}")
                
    def _validate_manifest(self, manifest: Dict) -> bool:
        """
        Validate the plugin manifest.
        
        Args:
            manifest (dict): The plugin manifest to validate.
            
        Returns:
            bool: True if the manifest is valid, False otherwise.
        """
        required_fields = ['name', 'version', 'description']
        for field in required_fields:
            if field not in manifest:
                logger.warning(f"Manifest missing required field: {field}")
                return False
        return True
        
    def get_all_plugins(self) -> List[Dict]:
        """
        Get information about all loaded plugins.
        
        Returns:
            list: A list of dictionaries containing plugin information.
        """
        return [{
            'id': plugin_id,
            'name': info['name'],
            'description': info['description'],
            'version': info['version'],
            'author': info['author'],
            'homepage': info['homepage']
        } for plugin_id, info in self.plugins.items()]
        
    def get_plugin(self, plugin_id: str) -> Optional[Dict]:
        """
        Get information about a specific plugin.
        
        Args:
            plugin_id (str): The ID of the plugin to get information about.
            
        Returns:
            dict: A dictionary containing plugin information.
        """
        if plugin_id not in self.plugins:
            return None
            
        info = self.plugins[plugin_id]
        return {
            'id': plugin_id,
            'name': info['name'],
            'description': info['description'],
            'version': info['version'],
            'author': info['author'],
            'homepage': info['homepage'],
            'has_ui': 'ui_path' in info['manifest'],
            'parameters': info['manifest'].get('parameters', [])
        }
        
    def execute_plugin(self, plugin_id: str, params: Dict = None) -> Any:
        """
        Execute a plugin with the provided parameters.
        
        Args:
            plugin_id (str): The ID of the plugin to execute.
            params (dict, optional): Parameters to pass to the plugin. Defaults to None.
            
        Returns:
            Any: The result of the plugin execution.
            
        Raises:
            ValueError: If the plugin is not found.
        """
        if plugin_id not in self.plugins:
            logger.error(f"Plugin {plugin_id} not found")
            raise ValueError(f"Plugin {plugin_id} not found")
            
        if params is None:
            params = {}
            
        plugin = self.plugins[plugin_id]
        logger.info(f"Executing plugin {plugin_id} with params: {params}")
        
        try:
            # Validate the module has an execute function
            if not hasattr(plugin['module'], 'execute'):
                error_msg = f"Plugin {plugin_id} is missing the execute function"
                logger.error(error_msg)
                raise AttributeError(error_msg)
                
            # Set a timeout for the plugin execution to prevent hangs
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(plugin['module'].execute, params)
                try:
                    # 60 second timeout (increased from 30)
                    result = future.result(timeout=60)
                    logger.info(f"Plugin {plugin_id} execution completed")
                    
                    # Ensure the result is JSON serializable
                    try:
                        json.dumps(result)
                    except (TypeError, OverflowError):
                        logger.warning(f"Plugin {plugin_id} returned non-JSON serializable result")
                        result = {'warning': 'Plugin returned non-serializable data', 'data': str(result)}
                        
                    return result
                except concurrent.futures.TimeoutError:
                    logger.error(f"Plugin {plugin_id} execution timed out after 60 seconds")
                    raise TimeoutError(f"Plugin execution timed out after 60 seconds")
        except TimeoutError:
            raise
        except Exception as e:
            logger.error(f"Error executing plugin {plugin_id}: {str(e)}")
            raise
            
    def install_plugin(self, file) -> str:
        """
        Install a new plugin from a ZIP file.
        
        Args:
            file: The uploaded file object (ZIP file).
            
        Returns:
            str: The ID of the installed plugin.
            
        Raises:
            ValueError: If the plugin file is invalid.
        """
        filename = secure_filename(file.filename)
        if not filename.endswith('.zip'):
            raise ValueError("Plugin file must be a ZIP archive")
            
        # Create a temporary file to store the uploaded file
        temp_path = os.path.join(self.plugin_folder, '_temp')
        os.makedirs(temp_path, exist_ok=True)
        
        temp_file = os.path.join(temp_path, filename)
        file.save(temp_file)
        
        try:
            # Extract the plugin
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                # Check if the zip contains a manifest.yaml file at the root
                manifest_file = None
                for info in zip_ref.infolist():
                    if info.filename == 'manifest.yaml' or info.filename == 'manifest.yml':
                        manifest_file = info.filename
                        break
                        
                if not manifest_file:
                    raise ValueError("Plugin archive must contain a manifest.yaml file")
                    
                # Read the manifest to get the plugin ID
                with zip_ref.open(manifest_file) as f:
                    manifest = yaml.safe_load(f)
                    
                plugin_id = secure_filename(manifest.get('id', manifest.get('name', '')))
                if not plugin_id:
                    raise ValueError("Plugin manifest must specify an id or name")
                    
                # Create the plugin directory
                plugin_path = os.path.join(self.plugin_folder, plugin_id)
                if os.path.exists(plugin_path):
                    # Remove existing plugin
                    shutil.rmtree(plugin_path)
                    
                os.makedirs(plugin_path, exist_ok=True)
                
                # Extract all files
                zip_ref.extractall(plugin_path)
                
                # Reload the plugin
                self.load_plugins()
                
                return plugin_id
                
        finally:
            # Clean up temporary files
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)
                
    def uninstall_plugin(self, plugin_id: str):
        """
        Uninstall a plugin.
        
        Args:
            plugin_id (str): The ID of the plugin to uninstall.
            
        Raises:
            ValueError: If the plugin is not found.
        """
        if plugin_id not in self.plugins:
            raise ValueError(f"Plugin {plugin_id} not found")
            
        plugin_path = os.path.join(self.plugin_folder, plugin_id)
        if os.path.exists(plugin_path):
            shutil.rmtree(plugin_path)
            
        # Remove the plugin from the loaded plugins
        if plugin_id in self.plugins:
            del self.plugins[plugin_id]

# Global plugin manager instance
_plugin_manager = None

def init_plugin_manager(app):
    """
    Initialize the plugin manager with the Flask app.
    
    Args:
        app: The Flask application.
    """
    global _plugin_manager
    plugin_folder = app.config['PLUGIN_FOLDER']
    _plugin_manager = PluginManager(plugin_folder)
    return _plugin_manager

def get_plugin_manager():
    """
    Get the plugin manager instance.
    
    Returns:
        PluginManager: The plugin manager instance.
        
    Raises:
        RuntimeError: If the plugin manager is not initialized.
    """
    global _plugin_manager
    if _plugin_manager is None:
        raise RuntimeError("Plugin manager not initialized. Call init_plugin_manager first.")
    return _plugin_manager
