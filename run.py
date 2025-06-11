#!/usr/bin/env python3
"""
NetScout-Pi-V2: Main application entry point.
This module initializes the Flask application and sets up the plugin system.
Optimized for running on a Raspberry Pi Zero 2W with an Ethernet USB dongle.
"""

import os
import sys
import logging
import socket
import subprocess
import netifaces
import eventlet

# Patch the standard library with eventlet's cooperative versions
eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)

from app import create_app, socketio

# Ensure /usr/sbin is in PATH for network commands like arp
if '/usr/sbin' not in os.environ.get('PATH', ''):
    os.environ['PATH'] += ':/usr/sbin'
    logging.info("Added /usr/sbin to PATH for network commands")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/netscout.log')
    ]
)

logger = logging.getLogger(__name__)

def get_ip_addresses():
    """
    Get all IP addresses of the device, prioritizing the Ethernet interface.
    
    Returns:
        dict: A dictionary of interface names and their IP addresses
    """
    ip_addresses = {}
    
    try:
        # Get list of network interfaces
        interfaces = netifaces.interfaces()
        
        for interface in interfaces:
            # Skip loopback interface
            if interface == 'lo':
                continue
                
            # Get address info for the interface
            try:
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    ip_addresses[interface] = addrs[netifaces.AF_INET][0]['addr']
            except Exception as e:
                logger.warning(f"Could not get address for interface {interface}: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting network interfaces: {str(e)}")
        
    return ip_addresses

def check_ethernet_dongle():
    """
    Check if an Ethernet USB dongle is connected and configured.
    
    Returns:
        bool: True if the Ethernet dongle is connected, False otherwise
    """
    try:
        # Common USB Ethernet interface names
        ethernet_interfaces = ['eth0', 'eth1', 'usb0', 'enx']
        
        for interface in netifaces.interfaces():
            # Check if interface name matches Ethernet pattern
            if any(interface.startswith(eth) for eth in ethernet_interfaces):
                if netifaces.AF_INET in netifaces.ifaddresses(interface):
                    return True
    except Exception as e:
        logger.error(f"Error checking Ethernet dongle: {str(e)}")
        
    return False

if __name__ == '__main__':
    # Check for Ethernet dongle
    has_ethernet = check_ethernet_dongle()
    if not has_ethernet:
        logger.warning("No Ethernet USB dongle detected. Network functionality may be limited.")
    
    # Get IP addresses
    ip_addresses = get_ip_addresses()
    if not ip_addresses:
        logger.warning("No network interfaces with IP addresses found!")
    else:
        for interface, ip in ip_addresses.items():
            logger.info(f"Interface {interface} has IP address {ip}")
    
    # Create Flask app
    app = create_app()
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    # Log startup message
    logger.info(f"Starting NetScout-Pi-V2 on {host}:{port}")
    if ip_addresses:
        logger.info("Access the dashboard at:")
        for interface, ip in ip_addresses.items():
            logger.info(f"  http://{ip}:{port}")
    
    try:
        # Use socketio.run which is the recommended way for Flask-SocketIO
        socketio.run(app, host=host, port=port, debug=False, log_output=True)
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        sys.exit(1)
