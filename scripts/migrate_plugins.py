#!/usr/bin/env python3
# NetScout-Pi Plugin Migration Script
# Migrates old plugins to the new folder-based structure

import os
import sys
import re
import json
import importlib.util
import inspect
import shutil
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

def get_plugin_class(file_path):
    """Get the plugin class from a Python file.
    
    Args:
        file_path (str): Path to the plugin file.
        
    Returns:
        tuple: (class, class_name) or (None, None) if not found.
    """
    try:
        # Generate a unique module name
        module_name = f"plugin_{Path(file_path).stem}_{hash(file_path)}"
        
        # Import the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find plugin class (looking for any class that inherits from PluginBase)
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, PluginBase) and 
                obj is not PluginBase):
                return obj, name
                
        return None, None
            
    except Exception as e:
        print(f"Error loading plugin from {file_path}: {e}")
        return None, None

def extract_plugin_metadata(plugin_class):
    """Extract metadata from the plugin class.
    
    Args:
        plugin_class (class): Plugin class.
        
    Returns:
        dict: Plugin metadata.
    """
    metadata = {
        'name': getattr(plugin_class, 'name', 'unknown'),
        'description': getattr(plugin_class, 'description', ''),
        'version': getattr(plugin_class, 'version', '0.1.0'),
        'author': getattr(plugin_class, 'author', 'NetScout-Pi'),
        'permissions': getattr(plugin_class, 'permissions', []),
        'category': getattr(plugin_class, 'category', 'general'),
        'tags': getattr(plugin_class, 'tags', [])
    }
    return metadata

def transform_plugin_code(file_path, class_name, plugin_class):
    """Transform plugin code to the new format.
    
    Args:
        file_path (str): Path to the plugin file.
        class_name (str): Name of the plugin class.
        plugin_class (class): The plugin class.
        
    Returns:
        str: Transformed plugin code.
    """
    with open(file_path, 'r') as f:
        code = f.read()
    
    # Update imports
    code = re.sub(r'(base_dir = Path\(__file__\).resolve\(\).parent\.parent\.parent)',
                 r'base_dir = Path(__file__).resolve().parent.parent.parent.parent',
                 code)
    
    # Add __init__ method to replace static metadata
    init_method = f"""
    def __init__(self, config, logger):
        \"\"\"Initialize plugin.
        
        Args:
            config: Plugin configuration.
            logger: PluginLogger instance.
        \"\"\"
        super().__init__(config, logger)
        
        # Read metadata from config.json
        self.metadata = self.config.get('metadata', {{}})
        self.name = self.metadata.get('name', '{getattr(plugin_class, "name", "unknown")}')
        self.description = self.metadata.get('description', '{getattr(plugin_class, "description", "")}')
        self.version = self.metadata.get('version', '{getattr(plugin_class, "version", "0.1.0")}')
        self.author = self.metadata.get('author', '{getattr(plugin_class, "author", "NetScout-Pi")}')
        self.permissions = self.metadata.get('permissions', {getattr(plugin_class, "permissions", [])})
        self.category = self.metadata.get('category', '{getattr(plugin_class, "category", "general")}')
        self.tags = self.metadata.get('tags', {getattr(plugin_class, "tags", [])})
        
        # Initialize plugin-specific variables
        self.plugin_dir = Path(__file__).resolve().parent
    """
    
    # Remove static metadata attributes
    code = re.sub(r'name = ".*?"', '', code)
    code = re.sub(r'description = ".*?"', '', code)
    code = re.sub(r'version = ".*?"', '', code)
    code = re.sub(r'author = ".*?"', '', code)
    code = re.sub(r'permissions = \[.*?\]', '', code)
    code = re.sub(r'category = ".*?"', '', code)
    code = re.sub(r'tags = \[.*?\]', '', code)
    
    # Insert __init__ method after class definition
    class_pattern = f"class {class_name}\\(PluginBase\\):"
    class_match = re.search(class_pattern, code)
    
    if class_match:
        insert_pos = class_match.end()
        docstring_match = re.search(r'""".*?"""', code[insert_pos:], re.DOTALL)
        
        if docstring_match:
            insert_pos += docstring_match.end()
        
        code = code[:insert_pos] + init_method + code[insert_pos:]
    
    return code

def create_config_json(metadata, file_path):
    """Create config.json file with plugin metadata.
    
    Args:
        metadata (dict): Plugin metadata.
        file_path (str): Path to save the config.json file.
    """
    # Extract settings from plugin code
    settings = {
        'enabled': True
    }
    
    # Create config structure
    config = {
        'metadata': metadata,
        'settings': settings
    }
    
    # Write config.json file
    with open(file_path, 'w') as f:
        json.dump(config, f, indent=4)

def migrate_plugin(source_file, dest_dir):
    """Migrate a plugin to the new folder-based structure.
    
    Args:
        source_file (str): Path to the source plugin file.
        dest_dir (str): Directory to save the migrated plugin.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        print(f"Migrating plugin: {source_file}")
        
        # Get plugin class and name
        plugin_class, class_name = get_plugin_class(source_file)
        if not plugin_class:
            print(f"Error: No plugin class found in {source_file}")
            return False
        
        # Extract plugin metadata
        metadata = extract_plugin_metadata(plugin_class)
        
        # Create destination directory
        plugin_name = metadata['name']
        plugin_dir = os.path.join(dest_dir, plugin_name)
        os.makedirs(plugin_dir, exist_ok=True)
        
        # Transform plugin code
        new_code = transform_plugin_code(source_file, class_name, plugin_class)
        
        # Write plugin.py file
        plugin_file = os.path.join(plugin_dir, 'plugin.py')
        with open(plugin_file, 'w') as f:
            f.write(new_code)
        
        # Create config.json file
        config_file = os.path.join(plugin_dir, 'config.json')
        create_config_json(metadata, config_file)
        
        print(f"Successfully migrated plugin to {plugin_dir}")
        return True
        
    except Exception as e:
        print(f"Error migrating plugin {source_file}: {e}")
        return False

def main():
    """Main entry point."""
    # Source and destination directories
    src_plugins_dir = os.path.join(base_dir, 'src', 'plugins')
    dest_plugins_dir = os.path.join(base_dir, 'src', 'plugins_new')
    
    # Create destination directory if it doesn't exist
    os.makedirs(dest_plugins_dir, exist_ok=True)
    
    # Get list of plugin files
    plugin_files = [os.path.join(src_plugins_dir, f) for f in os.listdir(src_plugins_dir)
                   if f.endswith('.py') and not f.startswith('__')]
    
    # Migrate each plugin
    success_count = 0
    for plugin_file in plugin_files:
        if migrate_plugin(plugin_file, dest_plugins_dir):
            success_count += 1
    
    print(f"Migration complete. Successfully migrated {success_count} of {len(plugin_files)} plugins.")

if __name__ == "__main__":
    main()
