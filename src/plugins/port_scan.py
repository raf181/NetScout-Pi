#!/usr/bin/env python3
# NetProbe Pi - Port Scan Plugin

import os
import sys
import json
import nmap
import socket
import time
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class PortScanPlugin(PluginBase):
    """Plugin to perform port scanning using nmap."""
    
    name = "port_scan"
    description = "Scan for open ports on network hosts"
    version = "0.1.0"
    author = "NetProbe"
    permissions = ["sudo"]
    
    def run(self, target=None, ports=None, scan_type=None, interface=None, **kwargs):
        """Run the plugin.
        
        Args:
            target (str, optional): Target IP, hostname, or CIDR range. Defaults to config value.
            ports (str, optional): Ports to scan (e.g., '22,80,443' or '1-1000'). Defaults to config value.
            scan_type (str, optional): Scan type ('quick', 'default', 'intense'). Defaults to 'default'.
            interface (str, optional): Network interface to use. Defaults to eth0.
            **kwargs: Additional arguments.
            
        Returns:
            dict: Port scan results.
        """
        # Get parameters from config if not specified
        target = target or self.config.get('target') or '127.0.0.1'
        ports = ports or self.config.get('ports') or '22,80,443,8080'
        scan_type = scan_type or self.config.get('scan_type') or 'default'
        interface = interface or self.config.get('interface') or 'eth0'
        
        self.logger.info(f"Starting port scan on target: {target}, ports: {ports}, type: {scan_type}")
        
        result = {
            'timestamp': self.logger.get_timestamp(),
            'target': target,
            'ports': ports,
            'scan_type': scan_type,
            'interface': interface,
            'hosts': [],
            'error': None
        }
        
        try:
            # Initialize nmap scanner
            scanner = nmap.PortScanner()
            
            # Build arguments based on scan type
            args = self._get_scan_arguments(scan_type, interface)
            
            # Add target and ports
            args = f"{args} -p {ports}"
            
            self.logger.info(f"Running nmap with arguments: {args}")
            
            # Run the scan
            scanner.scan(hosts=target, arguments=args)
            
            # Process scan results
            for host in scanner.all_hosts():
                host_info = {
                    'ip': host,
                    'hostname': None,
                    'state': scanner[host].state(),
                    'ports': []
                }
                
                # Try to get hostname
                try:
                    host_info['hostname'] = socket.getfqdn(host)
                    if host_info['hostname'] == host:
                        host_info['hostname'] = None
                except Exception:
                    pass
                
                # Process ports
                if 'tcp' in scanner[host]:
                    for port, port_info in scanner[host]['tcp'].items():
                        port_data = {
                            'port': port,
                            'protocol': 'tcp',
                            'state': port_info['state'],
                            'service': port_info['name'],
                            'product': port_info.get('product', ''),
                            'version': port_info.get('version', ''),
                            'extrainfo': port_info.get('extrainfo', '')
                        }
                        host_info['ports'].append(port_data)
                        
                # Process UDP if available
                if 'udp' in scanner[host]:
                    for port, port_info in scanner[host]['udp'].items():
                        port_data = {
                            'port': port,
                            'protocol': 'udp',
                            'state': port_info['state'],
                            'service': port_info['name'],
                            'product': port_info.get('product', ''),
                            'version': port_info.get('version', ''),
                            'extrainfo': port_info.get('extrainfo', '')
                        }
                        host_info['ports'].append(port_data)
                
                # Sort ports by number
                host_info['ports'].sort(key=lambda x: x['port'])
                
                # Add to hosts list
                result['hosts'].append(host_info)
                
            # Add scan info
            if hasattr(scanner, 'scaninfo'):
                result['scan_info'] = scanner.scaninfo()
                
            # Add scan time
            if hasattr(scanner, 'scanstats'):
                result['scan_stats'] = scanner.scanstats()
                
            self.logger.info(f"Port scan completed. Found {len(result['hosts'])} hosts.")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error during port scan: {str(e)}")
            
        return result
    
    def _get_scan_arguments(self, scan_type, interface=None):
        """Get nmap arguments based on scan type."""
        args = ''
        
        # Add interface if specified
        if interface:
            args += f"-e {interface} "
        
        # Basic arguments for all scan types
        args += "-n "  # No DNS resolution
        
        # Scan type specific arguments
        if scan_type == 'quick':
            args += "-T4 -F "  # Fast scan (100 most common ports)
        elif scan_type == 'intense':
            args += "-T4 -A -v "  # Aggressive scan with version detection and script scanning
        else:  # default
            args += "-T3 -sV "  # Normal timing, with version detection
            
        return args.strip()
    
    def get_common_ports(self, protocol='tcp'):
        """Get a list of common ports for a protocol."""
        common_tcp_ports = {
            21: 'FTP',
            22: 'SSH',
            23: 'Telnet',
            25: 'SMTP',
            53: 'DNS',
            80: 'HTTP',
            110: 'POP3',
            111: 'RPC',
            135: 'RPC',
            139: 'NetBIOS',
            143: 'IMAP',
            443: 'HTTPS',
            445: 'SMB',
            993: 'IMAPS',
            995: 'POP3S',
            1723: 'PPTP',
            3306: 'MySQL',
            3389: 'RDP',
            5900: 'VNC',
            8080: 'HTTP Proxy'
        }
        
        common_udp_ports = {
            53: 'DNS',
            67: 'DHCP',
            68: 'DHCP',
            69: 'TFTP',
            123: 'NTP',
            137: 'NetBIOS',
            138: 'NetBIOS',
            161: 'SNMP',
            162: 'SNMP',
            500: 'ISAKMP',
            514: 'Syslog',
            520: 'RIP',
            1194: 'OpenVPN',
            1701: 'L2TP',
            1900: 'UPNP',
            5353: 'mDNS'
        }
        
        if protocol.lower() == 'tcp':
            return common_tcp_ports
        elif protocol.lower() == 'udp':
            return common_udp_ports
        else:
            return {}
            
    def analyze_security(self, scan_result):
        """Analyze scan results for security issues."""
        issues = []
        
        for host in scan_result.get('hosts', []):
            host_issues = []
            
            # Check for potentially dangerous open ports
            dangerous_ports = {
                21: 'FTP (unencrypted file transfer)',
                23: 'Telnet (unencrypted remote access)',
                135: 'RPC (potential Windows vulnerability)',
                139: 'NetBIOS (legacy Windows networking)',
                445: 'SMB (potential file sharing vulnerability)',
                3389: 'RDP (remote desktop access)'
            }
            
            for port_data in host.get('ports', []):
                if port_data['state'] == 'open':
                    port = port_data['port']
                    
                    # Check against dangerous ports list
                    if port in dangerous_ports:
                        host_issues.append({
                            'type': 'dangerous_port',
                            'port': port,
                            'service': port_data['service'],
                            'description': f"Potentially insecure service: {dangerous_ports[port]}",
                            'severity': 'high'
                        })
                    
                    # Check for outdated versions
                    if port_data.get('version') and port_data.get('product'):
                        product = port_data['product'].lower()
                        version = port_data['version']
                        
                        # This would need a database of known vulnerable versions
                        # For now, just a placeholder for the concept
                        if 'openssh' in product and version.startswith('4.'):
                            host_issues.append({
                                'type': 'outdated_version',
                                'port': port,
                                'service': port_data['service'],
                                'product': port_data['product'],
                                'version': version,
                                'description': f"Outdated version: {product} {version}",
                                'severity': 'medium'
                            })
            
            if host_issues:
                issues.append({
                    'ip': host['ip'],
                    'hostname': host['hostname'],
                    'issues': host_issues
                })
                
        return issues
