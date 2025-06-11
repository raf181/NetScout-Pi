"""
Network Scanner Plugin for NetScout Pi.
Scans the local network for connected devices using ping.
"""

import subprocess
import ipaddress
import platform
import socket
import time
import re
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any

def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the network scanner plugin using ping.
    
    Args:
        params (dict): Parameters for the plugin.
            - subnet (str): The subnet to scan (e.g., 192.168.1.0/24)
            - timeout (float): Timeout in seconds for each host scan
            - quick_scan (bool): Use a faster scan method
            
    Returns:
        dict: The scan results.
    """
    subnet = params.get('subnet', '192.168.1.0/24')
    timeout = float(params.get('timeout', 1))
    quick_scan = bool(params.get('quick_scan', True))
    
    try:
        # Check if ping command is available
        try:
            subprocess.check_output("which ping", shell=True)
        except subprocess.CalledProcessError:
            return {
                'error': "Ping command not available. Please ensure ping is installed."
            }
            
        # Parse subnet to get IP addresses to scan
        network = ipaddress.ip_network(subnet, strict=False)
        
        # Skip network and broadcast addresses for IPv4
        hosts = list(network.hosts()) if network.version == 4 else list(network)
        
        # Perform scan
        scan_results = scan_network(hosts, timeout, quick_scan)
        
        # Format results
        return {
            'type': 'table',
            'headers': ['IP Address', 'Hostname', 'Status', 'Response Time'],
            'data': scan_results
        }
    except Exception as e:
        return {
            'error': f"Scan failed: {str(e)}"
        }

def scan_network(hosts, timeout, quick_scan):
    """
    Scan a list of IP addresses to find active hosts.
    
    Args:
        hosts (list): List of IP addresses to scan
        timeout (float): Timeout for each scan
        quick_scan (bool): Use a faster scan method
        
    Returns:
        list: List of scan results
    """
    results = []
    
    # Use multithreading for faster scanning
    with ThreadPoolExecutor(max_workers=50 if quick_scan else 25) as executor:
        # Use ICMP ping for all scans (simplifies and makes more reliable)
        futures = {executor.submit(ping_host, str(host), timeout): host for host in hosts}
        
        for future in futures:
            host = futures[future]
            try:
                result = future.result()
                if result['status'] == 'active':
                    # Format: [IP, Hostname, Status, Response Time]
                    results.append([
                        result['ip_address'],
                        result['hostname'],
                        'Active',
                        result.get('response_time', 'N/A')
                    ])
            except Exception:
                # Skip hosts that failed to scan
                pass
    
    # Sort results by IP address for better readability
    results.sort(key=lambda x: [int(i) for i in x[0].split('.')])
    return results

def ping_host(ip_address, timeout):
    """
    Ping a host to check if it's active.
    
    Args:
        ip_address (str): The IP address to ping
        timeout (float): Timeout in seconds
        
    Returns:
        dict: Result of the ping
    """
    # Determine the ping command based on OS
    if platform.system().lower() == 'windows':
        ping_cmd = f'ping -n 1 -w {int(timeout * 1000)}'
    else:
        ping_cmd = f'ping -c 1 -W {int(timeout)}'
    
    # Execute the ping command
    try:
        start_time = time.time()
        subprocess.check_output(f"{ping_cmd} {ip_address}", shell=True)
        response_time = int((time.time() - start_time) * 1000)  # ms
        
        # If we get here, the ping was successful
        return {
            'ip_address': ip_address,
            'hostname': get_hostname(ip_address),
            'mac_address': 'Not Available',  # Skip MAC address lookup
            'status': 'active',
            'response_time': f"{response_time}ms"
        }
    except subprocess.CalledProcessError:
        # Ping failed
        return {
            'ip_address': ip_address,
            'status': 'inactive'
        }

def scan_host(ip_address, timeout):
    """
    Scan common ports on a host to check if it's active.
    
    Args:
        ip_address (str): The IP address to scan
        timeout (float): Timeout in seconds
        
    Returns:
        dict: Result of the scan
    """
    # Common ports to check
    common_ports = [22, 80, 443, 8080, 445, 139]
    
    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip_address, port))
            sock.close()
            
            if result == 0:
                # Port is open, host is active
                return {
                    'ip_address': ip_address,
                    'hostname': get_hostname(ip_address),
                    'mac_address': get_mac_address(ip_address),
                    'status': 'active'
                }
        except socket.error:
            continue
    
    # No open ports found
    return {
        'ip_address': ip_address,
        'status': 'inactive'
    }

def get_hostname(ip_address):
    """Get hostname for an IP address."""
    try:
        return socket.getfqdn(ip_address)
    except Exception:
        return "Unknown"

def get_mac_address(ip_address):
    """Get the MAC address for an IP address."""
    return "Not Available"  # Simplified version that doesn't depend on arp
