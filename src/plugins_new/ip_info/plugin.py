#!/usr/bin/env python3
# NetProbe Pi - IP Info Plugin

import os
import sys
import socket
import netifaces
import subprocess
import json
import re
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class IPInfoPlugin(PluginBase):
    """Plugin to show current IP, MAC, gateway, subnet mask, DNS info."""
    def __init__(self, config, logger):
        """Initialize plugin.
        
        Args:
            config: Plugin configuration.
            logger: PluginLogger instance.
        """
        super().__init__(config, logger)
        
        # Read metadata from config.json
        self.metadata = self.config.get('metadata', {})
        self.name = self.metadata.get('name', 'ip_info')
        self.description = self.metadata.get('description', 'Show current IP, MAC, gateway, subnet mask, DNS info')
        self.version = self.metadata.get('version', '0.1.0')
        self.author = self.metadata.get('author', 'NetProbe')
        self.permissions = self.metadata.get('permissions', [])
        self.category = self.metadata.get('category', 'general')
        self.tags = self.metadata.get('tags', [])
        
        # Initialize plugin-specific variables
        self.plugin_dir = Path(__file__).resolve().parent
    
    
    
    
    
    
    
    
    def run(self, interface=None, **kwargs):
        """Run the plugin.
        
        Args:
            interface (str, optional): Network interface to check. Defaults to eth0.
            **kwargs: Additional arguments.
            
        Returns:
            dict: IP information.
        """
        # Use specified interface or get from config
        interface = interface or self.config.get('interface')
        
        # If no interface specified or not found, auto-detect
        if not interface or interface not in netifaces.interfaces():
            self.logger.info("Interface not specified or not found, auto-detecting...")
            # Get all non-loopback interfaces
            available_interfaces = [iface for iface in netifaces.interfaces() 
                                 if iface != 'lo' and not iface.startswith(('dummy', 'tun', 'tap'))]
            if available_interfaces:
                interface = available_interfaces[0]
                self.logger.info(f"Auto-selected interface: {interface}")
            else:
                interface = None
                self.logger.error("No suitable network interfaces found")
                return {"error": "No suitable network interfaces found"}

        self.logger.info(f"Collecting IP information for interface: {interface}")
        
        try:
            # Get interface details
            info = {}
            if interface in netifaces.interfaces():
                info['interface'] = interface
                addrs = netifaces.ifaddresses(interface)
                
                # MAC address
                if netifaces.AF_LINK in addrs and addrs[netifaces.AF_LINK]:
                    info['mac'] = addrs[netifaces.AF_LINK][0].get('addr')
                
                # IPv4 info
                if netifaces.AF_INET in addrs and addrs[netifaces.AF_INET]:
                    info['ipv4'] = {}
                    info['ipv4']['address'] = addrs[netifaces.AF_INET][0].get('addr')
                    info['ipv4']['netmask'] = addrs[netifaces.AF_INET][0].get('netmask')
                
                # IPv6 info
                if netifaces.AF_INET6 in addrs and addrs[netifaces.AF_INET6]:
                    info['ipv6'] = {}
                    # Filter out link-local addresses
                    ipv6_addrs = [addr for addr in addrs[netifaces.AF_INET6]
                                if not addr['addr'].startswith('fe80:')]
                    if ipv6_addrs:
                        info['ipv6']['address'] = ipv6_addrs[0]['addr'].split('%')[0]
                        info['ipv6']['netmask'] = ipv6_addrs[0].get('netmask')
                
                # Gateway info
                try:
                    gws = netifaces.gateways()
                    if 'default' in gws and netifaces.AF_INET in gws['default']:
                        info['gateway'] = gws['default'][netifaces.AF_INET][0]
                except Exception as e:
                    self.logger.error(f"Error fetching gateway info: {str(e)}")
                
                # DNS servers
                try:
                    with open('/etc/resolv.conf', 'r') as f:
                        resolv = f.readlines()
                    dns_servers = []
                    for line in resolv:
                        if line.startswith('nameserver'):
                            dns_servers.append(line.split()[1])
                    if dns_servers:
                        info['dns_servers'] = dns_servers
                except Exception as e:
                    self.logger.error(f"Error fetching DNS servers: {str(e)}")
            else:
                self.logger.error(f"Interface {interface} not found")
                return {"error": f"Interface {interface} not found"}

            # Calculate success rate
            values_present = sum(1 for k in ['interface', 'mac', 'ipv4', 'gateway', 'dns_servers'] if k in info)
            success_rate = (values_present / 5.0) * 100  # 5 is the total number of expected fields
            info['success_rate'] = success_rate
            
            self.logger.info(f"IP information collection completed for {interface}")
            return info

        except Exception as e:
            self.logger.error(f"Error collecting IP information: {str(e)}")
            return {"error": str(e), "success_rate": 0}
