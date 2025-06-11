"""
Network Scanner Plugin for NetScout Pi.
Scans the local network for connected devices using ping.
"""

import subprocess
import ipaddress
import platform
import socket
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any

def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the network scanner plugin using ping.
    
    Args:
        params (dict): Parameters for the plugin.
            - subnet (str): The subnet to scan (e.g., 192.168.1.0/24)
            - timeout (float): Timeout in seconds for each host scan
            - quick_scan (bool): Use a faster scan method
            - max_hosts (int): Maximum number of hosts to scan
            
    Returns:
        dict: The scan results.
    """
    # Parse parameters with safe defaults
    subnet = params.get('subnet', '192.168.1.0/24')
    timeout = float(params.get('timeout', 0.3))  # Further reduced default timeout
    quick_scan = bool(params.get('quick_scan', True))
    max_hosts = int(params.get('max_hosts', 25))  # Default to 25 hosts max
    
    # Start tracking time immediately
    start_time = time.time()
    
    try:
        # Check if ping command is available
        try:
            subprocess.check_output("which ping", shell=True)
        except subprocess.CalledProcessError:
            return {
                'error': "Ping command not available. Please ensure ping is installed."
            }
            
        # Parse subnet to get IP addresses to scan
        try:
            network = ipaddress.ip_network(subnet, strict=False)
        except ValueError as e:
            return {'error': f"Invalid subnet format: {str(e)}"}
        
        # Skip network and broadcast addresses for IPv4
        hosts = list(network.hosts()) if network.version == 4 else list(network)
        
        # For socket.io safety, limit total hosts regardless of user input
        total_hosts_in_network = len(hosts)
        if len(hosts) > max_hosts:
            hosts = hosts[:max_hosts]
        
        # Convert hosts to strings
        hosts = [str(h) for h in hosts]
        
        # Perform scan with a hard timeout to ensure we don't exceed Socket.IO timeout
        # Maximum 40 seconds for total scan (to allow time for result processing and transmission)
        max_scan_time = 40
        scan_results = scan_network_with_timeout(hosts, timeout, quick_scan, max_scan_time)
        
        # Calculate scan duration
        scan_time = round(time.time() - start_time, 2)
        
        # Format the results
        result = {
            'type': 'table',
            'headers': ['IP Address', 'Hostname', 'Status', 'Response Time'],
            'data': scan_results,
            'subnet': subnet,
            'hosts_found': len(scan_results),
            'scan_time': scan_time,
            'hosts_scanned': len(hosts),
            'total_hosts': total_hosts_in_network
        }
        
        # Add note if scan was limited
        if len(hosts) < total_hosts_in_network:
            result['note'] = f"Limited scan to {len(hosts)} of {total_hosts_in_network} hosts due to max_hosts setting"
        
        # Add warning if scan reached the time limit
        if time.time() - start_time >= max_scan_time:
            result['warning'] = f"Scan terminated early due to timeout ({max_scan_time}s limit)"
        
        return result
        
    except Exception as e:
        return {
            'error': f"Scan failed: {str(e)}"
        }

def scan_network_with_timeout(hosts, timeout, quick_scan, max_scan_time):
    """
    Scan a network with a hard timeout to prevent socket.io timeouts.
    
    Args:
        hosts (list): List of IP addresses to scan
        timeout (float): Timeout for each scan
        quick_scan (bool): Use a faster scan method
        max_scan_time (float): Maximum time for the entire scan in seconds
        
    Returns:
        list: List of scan results
    """
    start_time = time.time()
    results = []
    
    # Calculate batch size based on host count and available time
    # Use smaller batches for more frequent progress checks
    batch_size = min(len(hosts), 5)
    
    # Process hosts in batches
    for i in range(0, len(hosts), batch_size):
        # Check if we're approaching the timeout (leave 1s margin)
        elapsed = time.time() - start_time
        if elapsed > (max_scan_time - 1):
            print(f"Scan time limit reached ({elapsed:.1f}s). Scanned {i} of {len(hosts)} hosts.")
            break
        
        # Adjust timeout for remaining time
        remaining_time = max_scan_time - elapsed
        if remaining_time < 5 and i < len(hosts) - batch_size:
            # If little time remains but many hosts left, use a more aggressive strategy
            # Just scan a few more high-priority hosts with reduced timeout
            last_batch = hosts[i:i+min(5, len(hosts)-i)]
            batch_results = scan_network(last_batch, min(timeout, 0.2), True)
            results.extend(batch_results)
            break
            
        # Get the next batch of hosts
        batch = hosts[i:i+batch_size]
        
        # Scan this batch
        batch_results = scan_network(batch, timeout, quick_scan)
        results.extend(batch_results)
    
    # Sort results by IP address for better readability
    results.sort(key=lambda x: [int(i) for i in x[0].split('.')])
    return results

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
    
    # Determine max workers - use more workers for quick scan
    max_workers = 15 if quick_scan else 8
    
    def ping_host(ip_address):
        """Ping a host and return result as a table row"""
        # Construct ping command based on OS
        if platform.system().lower() == 'windows':
            cmd = f'ping -n 1 -w {int(timeout * 1000)} {ip_address} > nul 2>&1'
        else:
            # Use quiet mode and redirect output
            cmd = f'ping -c 1 -W {int(timeout)} -q {ip_address} > /dev/null 2>&1'
        
        try:
            start_time = time.time()
            exit_code = os.system(cmd)
            response_time = int((time.time() - start_time) * 1000)  # ms
            
            # If ping was successful
            if exit_code == 0:
                # Only attempt hostname lookup for responsive hosts
                hostname = "Unknown"
                try:
                    # Set a short timeout for hostname lookup
                    socket.setdefaulttimeout(0.3)
                    hostname = socket.getfqdn(ip_address)
                    # If hostname is just the IP, mark as unknown
                    if hostname == ip_address:
                        hostname = "Unknown"
                except Exception:
                    pass
                
                return [
                    ip_address,
                    hostname,
                    'Active',
                    f"{response_time}ms"
                ]
        except Exception:
            pass
        
        return None
    
    # Use ThreadPoolExecutor for parallel scanning
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks and track them
        future_to_ip = {executor.submit(ping_host, ip): ip for ip in hosts}
        
        # Process results as they complete
        for future in as_completed(future_to_ip):
            try:
                result = future.result()
                if result:  # Only add non-None results
                    results.append(result)
            except Exception:
                # Skip any errors in individual host scans
                pass
    
    return results
