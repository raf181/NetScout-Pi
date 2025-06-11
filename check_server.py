#!/usr/bin/env python3
"""
Simple script to verify server connectivity
"""
import time
import requests
import sys

def check_server():
    """Check if the server is accessible"""
    urls = [
        'http://127.0.0.1:5000/',
        'http://127.0.0.1:5000/api/plugins',
        'http://127.0.0.1:5000/api/test'
    ]
    
    print("Testing server connectivity...")
    
    for url in urls:
        try:
            print(f"Testing {url}...")
            response = requests.get(url, timeout=5)
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text[:100]}...")
        except Exception as e:
            print(f"Error accessing {url}: {str(e)}")
    
    print("Server connectivity test complete.")

if __name__ == '__main__':
    time.sleep(2)  # Give the server a moment to start
    check_server()
