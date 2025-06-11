#!/usr/bin/env python3
"""
Check package versions
"""
import sys
import importlib
import pkg_resources

packages = [
    'Flask', 
    'flask_socketio', 
    'socketio', 
    'eventlet', 
    'werkzeug'
]

print("Python version:", sys.version)
print("\nPackage versions:")
for package in packages:
    try:
        module = importlib.import_module(package.lower())
        print(f"{package}: {module.__version__}")
    except (ImportError, AttributeError):
        try:
            version = pkg_resources.get_distribution(package).version
            print(f"{package}: {version}")
        except:
            print(f"{package}: Not found or version unknown")
