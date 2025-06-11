#!/usr/bin/env python3
"""
Simple test to check if the server is running.
"""

import requests

try:
    response = requests.get('http://127.0.0.1:5000/api/plugins')
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
