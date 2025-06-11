"""
Utilities for working with plugins in the NetScout Pi application.
"""

import os
import yaml
import json
import zipfile
import tempfile
import shutil
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def validate_plugin_structure(plugin_path: str) -> Dict[str, Any]:
    """
    Validate a plugin directory structure.
    
    Args:
        plugin_path (str): Path to the plugin directory.
        
    Returns:
        dict: Validation results.
    """
    errors = []
    warnings = []
    
    # Check if the directory exists
    if not os.path.isdir(plugin_path):
        errors.append(f"Plugin directory {plugin_path} does not exist")
        return {
            'valid': False,
            'errors': errors,
            'warnings': warnings
        }
    
    # Check for manifest file
    manifest_path = os.path.join(plugin_path, 'manifest.yaml')
    if not os.path.exists(manifest_path):
        manifest_path = os.path.join(plugin_path, 'manifest.yml')
        if not os.path.exists(manifest_path):
            errors.append("Missing manifest.yaml file")
            return {
                'valid': False,
                'errors': errors,
                'warnings': warnings
            }
    
    # Load and validate manifest
    try:
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
            
        # Required fields
        required_fields = ['name', 'version', 'description']
        for field in required_fields:
            if field not in manifest:
                errors.append(f"Manifest missing required field: {field}")
        
        # Check for id field or use name
        if 'id' not in manifest:
            if 'name' in manifest:
                warnings.append("No 'id' field in manifest, using 'name' instead")
                manifest['id'] = manifest['name']
            else:
                errors.append("Manifest must have either 'id' or 'name' field")
        
        # Check for main module
        main_module = manifest.get('main_module', 'main')
        main_file = os.path.join(plugin_path, f"{main_module}.py")
        if not os.path.exists(main_file):
            errors.append(f"Missing main module file: {main_module}.py")
        
        # Check for UI file if specified
        if 'ui_path' in manifest:
            ui_path = os.path.join(plugin_path, manifest['ui_path'])
            if not os.path.exists(ui_path):
                errors.append(f"Missing UI file: {manifest['ui_path']}")
        
        # Check parameters format if present
        if 'parameters' in manifest:
            if not isinstance(manifest['parameters'], list):
                errors.append("'parameters' must be a list")
            else:
                for i, param in enumerate(manifest['parameters']):
                    if not isinstance(param, dict):
                        errors.append(f"Parameter at index {i} must be an object")
                    elif 'name' not in param:
                        errors.append(f"Parameter at index {i} missing 'name' field")
    except Exception as e:
        errors.append(f"Error parsing manifest: {str(e)}")
    
    # Final validation result
    valid = len(errors) == 0
    
    return {
        'valid': valid,
        'errors': errors,
        'warnings': warnings,
        'manifest': manifest if valid else None
    }

def validate_plugin_zip(zip_path: str) -> Dict[str, Any]:
    """
    Validate a plugin ZIP file.
    
    Args:
        zip_path (str): Path to the plugin ZIP file.
        
    Returns:
        dict: Validation results.
    """
    errors = []
    warnings = []
    
    # Check if the file exists
    if not os.path.isfile(zip_path):
        errors.append(f"Plugin ZIP file {zip_path} does not exist")
        return {
            'valid': False,
            'errors': errors,
            'warnings': warnings
        }
    
    # Create a temporary directory to extract the ZIP
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Extract the ZIP file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        # Check if the manifest exists
        manifest_path = os.path.join(temp_dir, 'manifest.yaml')
        if not os.path.exists(manifest_path):
            manifest_path = os.path.join(temp_dir, 'manifest.yml')
            if not os.path.exists(manifest_path):
                errors.append("Missing manifest.yaml file in ZIP")
                return {
                    'valid': False,
                    'errors': errors,
                    'warnings': warnings
                }
        
        # Validate the extracted plugin
        validation = validate_plugin_structure(temp_dir)
        errors.extend(validation['errors'])
        warnings.extend(validation['warnings'])
        
        # Get the manifest if valid
        manifest = validation.get('manifest')
        
        return {
            'valid': validation['valid'],
            'errors': errors,
            'warnings': warnings,
            'manifest': manifest
        }
    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)

def generate_plugin_template(output_dir: str, plugin_info: Dict[str, Any]) -> str:
    """
    Generate a template plugin structure.
    
    Args:
        output_dir (str): Directory to create the plugin in.
        plugin_info (dict): Plugin information.
            - name (str): Plugin name
            - id (str): Plugin ID
            - description (str): Plugin description
            - author (str): Plugin author
            - version (str): Plugin version
            
    Returns:
        str: Path to the generated plugin directory.
    """
    try:
        # Create plugin directory
        plugin_id = plugin_info.get('id', plugin_info.get('name', 'my_plugin')).lower().replace(' ', '_')
        plugin_dir = os.path.join(output_dir, plugin_id)
        
        if os.path.exists(plugin_dir):
            shutil.rmtree(plugin_dir)
            
        os.makedirs(plugin_dir)
        
        # Create manifest file
        manifest = {
            'name': plugin_info.get('name', 'My Plugin'),
            'id': plugin_id,
            'version': plugin_info.get('version', '1.0.0'),
            'description': plugin_info.get('description', 'A plugin for NetScout Pi'),
            'author': plugin_info.get('author', 'NetScout User'),
            'main_module': 'main',
            'parameters': [
                {
                    'name': 'example_param',
                    'label': 'Example Parameter',
                    'type': 'string',
                    'description': 'An example parameter',
                    'default': 'example',
                    'required': False
                }
            ]
        }
        
        with open(os.path.join(plugin_dir, 'manifest.yaml'), 'w') as f:
            yaml.dump(manifest, f, default_flow_style=False)
        
        # Create main module
        main_py = """\"\"\"
{name} Plugin for NetScout Pi.
{description}
\"\"\"

from typing import Dict, Any

def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"
    Execute the plugin with the given parameters.
    
    Args:
        params (dict): Parameters from the UI/API
        
    Returns:
        dict: Result data that will be displayed in the dashboard
    \"\"\"
    # Your plugin code here
    example_param = params.get('example_param', 'example')
    
    # Return a simple result
    return {{
        'message': f'Hello from {name}!',
        'parameters': params
    }}
""".format(name=manifest['name'], description=manifest['description'])
        
        with open(os.path.join(plugin_dir, 'main.py'), 'w') as f:
            f.write(main_py)
        
        # Create an empty static directory
        os.makedirs(os.path.join(plugin_dir, 'static'), exist_ok=True)
        
        return plugin_dir
    except Exception as e:
        logger.error(f"Error generating plugin template: {str(e)}")
        return None
