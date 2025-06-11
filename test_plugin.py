#!/usr/bin/env python3
"""
Simple test client for NetScout-Pi plugin execution.
"""

import requests
import json
import sys

# Plugin to test
plugin_id = 'network_scanner'
params = {
    'subnet': '192.168.10.0/24',
    'timeout': 0.5,
    'quick_scan': True
}

# URL to the plugin execution endpoint
url = f'http://127.0.0.1:5000/api/plugins/{plugin_id}/execute'

# Execute the plugin
try:
    print(f"Executing plugin {plugin_id} with params: {params}")
    response = requests.post(url, json=params, timeout=10)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Plugin execution successful:")
        print(json.dumps(result, indent=2))
    else:
        print(f"Error executing plugin: {response.status_code}")
        print(response.text)
except requests.exceptions.Timeout:
    print("Request timed out. The plugin might be taking too long to execute.")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
