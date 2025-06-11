#!/usr/bin/env python3
"""
Simple test client for NetScout-Pi WebSocket connection.
"""

import sys
import socketio
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create a Socket.IO client
sio = socketio.Client(logger=True, engineio_logger=True)

# Event handlers
@sio.event
def connect():
    print("Connected to server!")

@sio.event
def disconnect():
    print("Disconnected from server!")

@sio.event
def system_update(data):
    print(f"Received system update: {data}")

# Connect to the server
try:
    print("Attempting to connect to server...")
    sio.connect('http://127.0.0.1:5000', transports=['polling', 'websocket'])
    
    # Wait for events
    print("Waiting for events...")
    time.sleep(10)
    
    # Disconnect
    sio.disconnect()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
