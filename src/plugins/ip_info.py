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
base_dir = Path(__file__).resolve().parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class IPInfoPlugin(PluginBase):
    """Plugin to show current IP, MAC, gateway, subnet mask, DNS info."""
    
    name = "ip_info"
    description = "Show current IP, MAC, gateway, subnet mask, DNS info"
    version = "0.1.0"
    author = "NetProbe"
    permissions = []
    
    def run(self, interface=None, **kwargs):
        """Run the plugin.
        
        Args:
            interface (str, optional): Network interface to check. Defaults to eth0.
            **kwargs: Additional arguments.
            
        Returns:
            dict: IP information.
        """
        # Use specified interface or get from config
        interface = interface or self.config.get('interface') or 'eth0'
        
        self.logger.info(f"Collecting IP information for interface: {interface}")
        
        result = {
            'timestamp': self.logger.get_timestamp(),
            'interface': interface,
            'status': 'up' if self._is_interface_up(interface) else 'down',
            'addresses': {},
            'gateway': None,
            'dns_servers': [],
            'hostname': socket.gethostname(),
            'fqdn': socket.getfqdn(),
            'mac_address': None,
            'link_detected': self._check_link_status(interface),
            'routing_table': self._get_routing_table(),
            'error': None
        }
        
        try:
            # Check if interface exists
            if interface not in netifaces.interfaces():
                raise ValueError(f"Interface {interface} not found")
            
            # Get MAC address
            try:
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_LINK in addrs:
                    result['mac_address'] = addrs[netifaces.AF_LINK][0].get('addr')
            except Exception as e:
                self.logger.warning(f"Failed to get MAC address: {str(e)}")
            
            # Get IP addresses (IPv4 and IPv6)
            try:
                if netifaces.AF_INET in addrs:
                    inet_info = addrs[netifaces.AF_INET][0]
                    result['addresses']['ipv4'] = {
                        'address': inet_info.get('addr'),
                        'netmask': inet_info.get('netmask'),
                        'broadcast': inet_info.get('broadcast')
                    }
                    
                    # Calculate CIDR notation
                    if inet_info.get('addr') and inet_info.get('netmask'):
                        netmask = inet_info.get('netmask')
                        cidr = sum([bin(int(x)).count('1') for x in netmask.split('.')])
                        result['addresses']['ipv4']['cidr'] = f"{inet_info.get('addr')}/{cidr}"
                
                if netifaces.AF_INET6 in addrs:
                    result['addresses']['ipv6'] = [
                        {
                            'address': x.get('addr').split('%')[0],
                            'scope': x.get('addr').split('%')[1] if '%' in x.get('addr', '') else None
                        }
                        for x in addrs[netifaces.AF_INET6]
                    ]
            except Exception as e:
                self.logger.warning(f"Failed to get IP addresses: {str(e)}")
            
            # Get default gateway
            try:
                gateways = netifaces.gateways()
                if 'default' in gateways and netifaces.AF_INET in gateways['default']:
                    result['gateway'] = gateways['default'][netifaces.AF_INET][0]
            except Exception as e:
                self.logger.warning(f"Failed to get gateway: {str(e)}")
            
            # Get DNS servers
            try:
                result['dns_servers'] = self._get_dns_servers()
            except Exception as e:
                self.logger.warning(f"Failed to get DNS servers: {str(e)}")
            
            # Get DHCP status
            try:
                result['dhcp'] = self._is_dhcp(interface)
            except Exception as e:
                self.logger.warning(f"Failed to determine DHCP status: {str(e)}")
                result['dhcp'] = 'unknown'
                
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error collecting IP information: {str(e)}")
        
        self.logger.info(f"IP information collection completed for {interface}")
        return result
    
    def _is_interface_up(self, interface):
        """Check if interface is up."""
        try:
            with open(f"/sys/class/net/{interface}/operstate", 'r') as f:
                state = f.read().strip()
                return state.lower() == 'up'
        except Exception:
            return False
    
    def _check_link_status(self, interface):
        """Check if link is detected on interface."""
        try:
            with open(f"/sys/class/net/{interface}/carrier", 'r') as f:
                carrier = f.read().strip()
                return carrier == '1'
        except Exception:
            return False
    
    def _get_dns_servers(self):
        """Get DNS servers from /etc/resolv.conf."""
        dns_servers = []
        try:
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('nameserver'):
                        parts = line.split()
                        if len(parts) >= 2:
                            dns_servers.append(parts[1])
        except Exception as e:
            self.logger.warning(f"Failed to read /etc/resolv.conf: {str(e)}")
        
        return dns_servers
    
    def _is_dhcp(self, interface):
        """Check if interface is using DHCP."""
        try:
            # Check if dhclient is running for this interface
            output = subprocess.check_output(['ps', 'aux'], text=True)
            return bool(re.search(f'dhclient.*{interface}', output))
        except Exception as e:
            self.logger.warning(f"Failed to check DHCP status: {str(e)}")
            return 'unknown'
    
    def _get_routing_table(self):
        """Get routing table."""
        try:
            output = subprocess.check_output(['ip', 'route', 'show'], text=True)
            return output.splitlines()
        except Exception as e:
            self.logger.warning(f"Failed to get routing table: {str(e)}")
            return []
