#!/usr/bin/env python3
# NetProbe Pi - ARP Scan Plugin

import os
import sys
import subprocess
import re
import socket
import time
import json
import netifaces
import ipaddress
from scapy.all import ARP, Ether, srp
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class ARPScanPlugin(PluginBase):
    """Plugin to perform ARP scan to detect devices in the subnet."""
    def __init__(self, config, logger):
        """Initialize plugin.
        
        Args:
            config: Plugin configuration.
            logger: PluginLogger instance.
        """
        super().__init__(config, logger)
        
        # Read metadata from config.json
        self.metadata = self.config.get('metadata', {})
        self.name = self.metadata.get('name', 'arp_scan')
        self.description = self.metadata.get('description', 'Detect devices in the subnet using ARP scan')
        self.version = self.metadata.get('version', '0.1.0')
        self.author = self.metadata.get('author', 'NetProbe')
        self.permissions = self.metadata.get('permissions', ['sudo'])
        self.category = self.metadata.get('category', 'general')
        self.tags = self.metadata.get('tags', [])
        
        # Initialize plugin-specific variables
        self.plugin_dir = Path(__file__).resolve().parent
    
    
    
    
    
    
    
    
    def run(self, interface=None, timeout=2, quick_scan=False, **kwargs):
        """Run the plugin.
        
        Args:
            interface (str, optional): Network interface to scan. Defaults to eth0.
            timeout (int, optional): Timeout in seconds for ARP responses.
            quick_scan (bool, optional): Perform a quick scan using system ARP cache.
            **kwargs: Additional arguments.
            
        Returns:
            dict: ARP scan results.
        """
        # Use specified interface or get from config
        interface = interface or self.config.get('interface') or 'eth0'
        timeout = int(kwargs.get('timeout', timeout))
        quick_scan = kwargs.get('quick_scan', quick_scan)
        
        self.logger.info(f"Starting ARP scan on interface: {interface}")
        
        result = {
            'timestamp': self.logger.get_timestamp(),
            'interface': interface,
            'devices': [],
            'scan_method': 'quick' if quick_scan else 'full',
            'error': None
        }
        
        try:
            # Check if interface exists and is up
            if interface not in netifaces.interfaces():
                raise ValueError(f"Interface {interface} not found")
            
            if not self._is_interface_up(interface):
                raise ValueError(f"Interface {interface} is down")
            
            # Get devices using quick scan (ARP cache) or full scan
            if quick_scan:
                result['devices'] = self._quick_scan()
                result['scan_method'] = 'quick (ARP cache)'
            else:
                subnet = self._get_subnet(interface)
                if not subnet:
                    raise ValueError(f"Could not determine subnet for interface {interface}")
                
                result['subnet'] = subnet
                self.logger.info(f"Scanning subnet: {subnet}")
                
                # Perform the ARP scan
                result['devices'] = self._perform_scan(interface, subnet, timeout)
                result['scan_method'] = 'full (active scanning)'
            
            self.logger.info(f"Found {len(result['devices'])} devices on network")
            
            # Try to get hostname for each device
            self._resolve_hostnames(result['devices'])
            
            # Try to get vendor information
            self._add_vendor_info(result['devices'])
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error during ARP scan: {str(e)}")
        
        return result
    
    def _is_interface_up(self, interface):
        """Check if interface is up."""
        try:
            with open(f"/sys/class/net/{interface}/operstate", 'r') as f:
                state = f.read().strip()
                return state.lower() == 'up'
        except Exception:
            return False
    
    def _get_subnet(self, interface):
        """Get subnet for the specified interface."""
        try:
            # Get IP address and netmask for the interface
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET not in addrs:
                return None
            
            inet_info = addrs[netifaces.AF_INET][0]
            ip_addr = inet_info.get('addr')
            netmask = inet_info.get('netmask')
            
            if not ip_addr or not netmask:
                return None
            
            # Calculate network address and CIDR
            ip = ipaddress.IPv4Address(ip_addr)
            mask = ipaddress.IPv4Address(netmask)
            netmask_bits = bin(int(mask)).count('1')
            
            # Create network object
            network = ipaddress.IPv4Network(f"{ip_addr}/{netmask_bits}", strict=False)
            return str(network)
        except Exception as e:
            self.logger.error(f"Error determining subnet: {str(e)}")
            return None
    
    def _quick_scan(self):
        """Get devices from ARP cache."""
        devices = []
        try:
            # Read the ARP cache
            output = subprocess.check_output(['arp', '-a'], text=True)
            
            # Parse the output
            pattern = r'(?P<hostname>.+?)\s+\((?P<ip>[0-9.]+)\)\s+at\s+(?P<mac>[0-9a-fA-F:]+)'
            for line in output.splitlines():
                match = re.search(pattern, line)
                if match:
                    devices.append({
                        'ip': match.group('ip'),
                        'mac': match.group('mac').lower(),
                        'hostname': match.group('hostname').strip(),
                        'source': 'arp_cache'
                    })
        except Exception as e:
            self.logger.error(f"Error reading ARP cache: {str(e)}")
        
        return devices
    
    def _perform_scan(self, interface, subnet, timeout):
        """Perform ARP scan on the subnet."""
        devices = []
        try:
            # Create ARP packet
            arp = ARP(pdst=subnet)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether/arp
            
            self.logger.info(f"Sending ARP packets on {interface} with timeout {timeout}s")
            
            # Send packet and get response
            result = srp(packet, timeout=timeout, verbose=0, iface=interface)[0]
            
            # Parse response
            for sent, received in result:
                devices.append({
                    'ip': received.psrc,
                    'mac': received.hwsrc.lower(),
                    'hostname': None,
                    'source': 'arp_scan'
                })
                
            self.logger.info(f"ARP scan complete, found {len(devices)} devices")
            
        except Exception as e:
            self.logger.error(f"Error during ARP scan: {str(e)}")
        
        return devices
    
    def _resolve_hostname(self, ip):
        """Resolve hostname for an IP address."""
        try:
            return socket.getfqdn(ip)
        except Exception:
            return None
    
    def _resolve_hostnames(self, devices):
        """Resolve hostnames for all devices in parallel."""
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Create mapping of futures to device indices
            future_to_idx = {executor.submit(self._resolve_hostname, device['ip']): i 
                            for i, device in enumerate(devices)}
            
            # Process results as they complete
            for future in future_to_idx:
                idx = future_to_idx[future]
                try:
                    hostname = future.result()
                    if hostname and hostname != devices[idx]['ip']:
                        devices[idx]['hostname'] = hostname
                except Exception as e:
                    self.logger.debug(f"Error resolving hostname for {devices[idx]['ip']}: {str(e)}")
    
    def _add_vendor_info(self, devices):
        """Add vendor information for MAC addresses."""
        # Load MAC vendor database if available
        vendors = {}
        vendor_db_path = os.path.join(base_dir, 'data', 'mac_vendors.json')
        
        try:
            if os.path.exists(vendor_db_path):
                with open(vendor_db_path, 'r') as f:
                    vendors = json.load(f)
            
                # Add vendor info to devices
                for device in devices:
                    mac_prefix = device['mac'][:8].upper()  # First 3 octets (xx:xx:xx)
                    if mac_prefix in vendors:
                        device['vendor'] = vendors[mac_prefix]
        except Exception as e:
            self.logger.warning(f"Error loading MAC vendor database: {str(e)}")
