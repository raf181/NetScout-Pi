#!/usr/bin/env python3
# NetScout-Pi - Update application to use new plugin manager

import os
import sys
import re
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

def update_app_py(file_path):
    """Update app.py to use the new plugin manager.
    
    Args:
        file_path (str): Path to app.py.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        
        # Add import for NewPluginManager
        if 'from src.core.new_plugin_manager import NewPluginManager' not in code:
            code = re.sub(
                r'from src.core.plugin_manager import PluginManager',
                'from src.core.plugin_manager import PluginManager\nfrom src.core.new_plugin_manager import NewPluginManager',
                code
            )
        
        # Replace PluginManager with NewPluginManager
        code = re.sub(
            r'plugin_manager = PluginManager\(config\)',
            'plugin_manager = NewPluginManager(config)',
            code
        )
        
        # Write the updated code
        with open(file_path, 'w') as f:
            f.write(code)
            
        print(f"Successfully updated {file_path}")
        return True
        
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Main entry point."""
    # Update app.py
    app_path = os.path.join(base_dir, 'app.py')
    update_app_py(app_path)

if __name__ == "__main__":
    main()
