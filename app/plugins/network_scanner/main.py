"""
Network Scanner Plugin for NetScout Pi.
Scans the local network for connected devices.
"""

import subprocess
import ipaddress
import platform
import socket
import time
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any

def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the network scanner plugin.
    
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
        # Check if required tools are installed
        missing_tools = []
        
        # Check if ip command is available
        try:
            subprocess.check_output("which ip", shell=True)
        except subprocess.CalledProcessError:
            missing_tools.append("ip")
            
        # Check if arp command is available (either in PATH or at /usr/sbin/arp)
        try:
            subprocess.check_output("which arp || [ -f /usr/sbin/arp ]", shell=True)
        except subprocess.CalledProcessError:
            missing_tools.append("arp (net-tools)")
            
        if missing_tools:
            return {
                'error': f"Network tools not available: {', '.join(missing_tools)}. Please run 'sudo ./install_dependencies.sh' from the project root directory."
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
            'headers': ['IP Address', 'Hostname', 'MAC Address', 'Status'],
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
    with ThreadPoolExecutor(max_workers=20) as executor:
        if quick_scan:
            # Use ICMP ping for quick scan
            futures = {executor.submit(ping_host, str(host), timeout): host for host in hosts}
        else:
            # Use port scan for more thorough scan
            futures = {executor.submit(scan_host, str(host), timeout): host for host in hosts}
        
        for future in futures:
            host = futures[future]
            try:
                result = future.result()
                if result['status'] == 'active':
                    results.append([
                        result['ip_address'],
                        result['hostname'],
                        result['mac_address'],
                        'Active'
                    ])
            except Exception:
                # Skip hosts that failed to scan
                pass
    
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
    ping_cmd = 'ping -c 1 -W {}'.format(int(timeout * 1000))
    if platform.system().lower() == 'windows':
        ping_cmd = 'ping -n 1 -w {}'.format(int(timeout * 1000))
    
    # Execute the ping command
    try:
        subprocess.check_output(f"{ping_cmd} {ip_address}", shell=True)
        # If we get here, the ping was successful
        return {
            'ip_address': ip_address,
            'hostname': get_hostname(ip_address),
            'mac_address': get_mac_address(ip_address),
            'status': 'active'
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
    try:
        # Different approaches based on the OS
        if platform.system().lower() == 'windows':
            # Use ARP on Windows
            arp_output = subprocess.check_output(f"arp -a {ip_address}", shell=True).decode('utf-8')
            mac_match = re.search(r'([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})', arp_output)
            if mac_match:
                return mac_match.group(1)
        else:
            # Linux/Mac - try multiple methods in order of preference
            methods = [
                # Method 1: ip neighbor (modern Linux)
                lambda: subprocess.check_output(f"ip neighbor show {ip_address}", shell=True).decode('utf-8'),
                # Method 2: arp with full path (most reliable)
                lambda: subprocess.check_output(f"/usr/sbin/arp -n {ip_address}", shell=True).decode('utf-8'),
                # Method 3: regular arp command (if in PATH)
                lambda: subprocess.check_output(f"arp -n {ip_address}", shell=True).decode('utf-8')
            ]
            
            for method in methods:
                try:
                    output = method()
                    mac_match = re.search(r'([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})', output)
                    if mac_match:
                        return mac_match.group(1)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
    except Exception:
        pass
    
    return "Unknown"
