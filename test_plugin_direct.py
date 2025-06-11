#!/usr/bin/env python3
"""
Test the network_scanner plugin directly
"""
import sys
import os
import importlib.util

def test_plugin():
    """Load and test the network_scanner plugin directly"""
    plugin_path = os.path.join(os.path.dirname(__file__), 'app/plugins/network_scanner/main.py')
    
    if not os.path.exists(plugin_path):
        print(f"Plugin file not found: {plugin_path}")
        return
    
    try:
        # Load the plugin module
        spec = importlib.util.spec_from_file_location("network_scanner.main", plugin_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check if the module has the execute function
        if not hasattr(module, 'execute'):
            print("Plugin missing execute function")
            return
        
        # Execute the plugin
        params = {
            'subnet': '192.168.10.0/24',
            'timeout': 1,
            'quick_scan': True
        }
        
        print(f"Executing plugin with params: {params}")
        result = module.execute(params)
        print(f"Plugin execution result: {result}")
    except Exception as e:
        print(f"Error executing plugin: {e}")

if __name__ == '__main__':
    test_plugin()
