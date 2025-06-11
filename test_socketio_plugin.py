#!/usr/bin/env python3
"""
Test client for NetScout-Pi plugin execution via Socket.IO.
"""

import sys
import socketio
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create a Socket.IO client
sio = socketio.Client()

# Event handlers
@sio.event
def connect():
    print("Connected to server!")

@sio.event
def disconnect():
    print("Disconnected from server!")

@sio.event
def system_update(data):
    print(f"Received system update: {data.get('timestamp')}")

# Connect to the server
try:
    print("Attempting to connect to server...")
    sio.connect('http://127.0.0.1:5000', transports=['polling'])
    
    # Wait for some events
    print("Waiting for events (10 seconds)...")
    time.sleep(10)
    
    # Disconnect
    print("Disconnecting...")
    sio.disconnect()
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
