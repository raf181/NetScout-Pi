"""
Network utilities for the NetScout Pi application.
"""

import socket
import ipaddress
import subprocess
import platform
import logging
import re
import netifaces
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def ping(host: str, timeout: float = 1.0) -> Dict[str, Any]:
    """
    Ping a host and return the result.
    
    Args:
        host (str): The hostname or IP address to ping.
        timeout (float): Timeout in seconds.
        
    Returns:
        dict: Ping result.
    """
    try:
        # Determine the ping command based on OS
        ping_cmd = ['ping', '-c', '1', '-W', str(int(timeout))]
        if platform.system().lower() == 'windows':
            ping_cmd = ['ping', '-n', '1', '-w', str(int(timeout * 1000))]
            
        ping_cmd.append(host)
        
        # Execute the ping command
        output = subprocess.check_output(ping_cmd, stderr=subprocess.STDOUT).decode('utf-8')
        
        # Parse the output
        time_ms = None
        time_match = re.search(r'time=(\d+\.?\d*)\s*ms', output)
        if time_match:
            time_ms = float(time_match.group(1))
            
        return {
            'success': True,
            'host': host,
            'time_ms': time_ms,
            'output': output
        }
    except subprocess.CalledProcessError as e:
        logger.debug(f"Ping failed for {host}: {e.output.decode('utf-8')}")
        return {
            'success': False,
            'host': host,
            'error': 'Host unreachable',
            'output': e.output.decode('utf-8') if hasattr(e, 'output') else str(e)
        }
    except Exception as e:
        logger.error(f"Error pinging {host}: {str(e)}")
        return {
            'success': False,
            'host': host,
            'error': str(e)
        }

def scan_network(subnet: str, timeout: float = 1.0, quick: bool = True) -> List[Dict[str, Any]]:
    """
    Scan a network subnet for active hosts.
    
    Args:
        subnet (str): The subnet to scan (e.g., 192.168.1.0/24).
        timeout (float): Timeout in seconds for each host scan.
        quick (bool): If True, only scan common hosts in the subnet.
        
    Returns:
        list: List of active hosts.
    """
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        active_hosts = []
        
        # If quick scan, only check common hosts plus a few random ones
        hosts_to_scan = []
        if quick:
            # Always check the gateway (usually .1)
            gateway_ip = get_default_gateway()
            if gateway_ip:
                hosts_to_scan.append(ipaddress.ip_address(gateway_ip))
                
            # Add common host addresses
            for i in [1, 2, 100, 101, 254]:
                try:
                    hosts_to_scan.append(network.network_address + i)
                except (IndexError, ValueError):
                    pass
        else:
            # Full scan
            hosts_to_scan = list(network.hosts())
            
        # Perform the scan
        for host in hosts_to_scan:
            result = ping(str(host), timeout)
            if result['success']:
                # Get hostname
                hostname = 'Unknown'
                try:
                    hostname = socket.getfqdn(str(host))
                except Exception:
                    pass
                    
                active_hosts.append({
                    'ip': str(host),
                    'hostname': hostname,
                    'response_time': result.get('time_ms')
                })
                
        return active_hosts
    except Exception as e:
        logger.error(f"Error scanning network {subnet}: {str(e)}")
        return []

def get_default_gateway() -> Optional[str]:
    """
    Get the default gateway IP address.
    
    Returns:
        str: Default gateway IP address, or None if not found.
    """
    try:
        gateways = netifaces.gateways()
        if 'default' in gateways and netifaces.AF_INET in gateways['default']:
            return gateways['default'][netifaces.AF_INET][0]
    except Exception as e:
        logger.error(f"Error getting default gateway: {str(e)}")
    return None

def get_mac_address(ip: str) -> str:
    """
    Get the MAC address for an IP address using ARP.
    
    Args:
        ip (str): IP address to lookup.
        
    Returns:
        str: MAC address or "Unknown".
    """
    try:
        if platform.system().lower() == 'windows':
            # Use ARP on Windows
            output = subprocess.check_output(f"arp -a {ip}", shell=True).decode('utf-8')
        else:
            # Use ARP on Linux/Mac - check if arp command exists
            try:
                output = subprocess.check_output(f"arp -n {ip}", shell=True).decode('utf-8')
            except subprocess.CalledProcessError:
                # Try using ip neighbor which is available in most modern Linux systems
                try:
                    output = subprocess.check_output(f"ip neighbor show {ip}", shell=True).decode('utf-8')
                except subprocess.CalledProcessError:
                    logger.debug(f"Neither 'arp' nor 'ip neighbor' commands are available on this system")
                    return "Unknown"
            
        mac_matches = re.findall(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', output)
        if mac_matches:
            # Format can be different on different OSes, just return what we found
            return mac_matches[0]
    except Exception as e:
        logger.debug(f"Error getting MAC address for {ip}: {str(e)}")
    
    return "Unknown"

def traceroute(host: str, max_hops: int = 30) -> List[Dict[str, Any]]:
    """
    Perform a traceroute to a host.
    
    Args:
        host (str): The hostname or IP address to traceroute.
        max_hops (int): Maximum number of hops.
        
    Returns:
        list: Traceroute results.
    """
    try:
        # Determine the traceroute command based on OS
        if platform.system().lower() == 'windows':
            cmd = ['tracert', '-d', '-h', str(max_hops), host]
        else:
            cmd = ['traceroute', '-n', '-m', str(max_hops), host]
            
        # Execute the traceroute command
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=30).decode('utf-8')
        
        # Parse the output
        hops = []
        lines = output.split('\n')
        
        # Skip the header line(s)
        for line in lines:
            if not line.strip():
                continue
                
            # Try to extract hop information
            hop_match = re.search(r'^\s*(\d+)\s+([\d\.]+|[*]+)\s+(\d+\.?\d*)\s*ms', line)
            if hop_match:
                hop_num = int(hop_match.group(1))
                hop_ip = hop_match.group(2) if hop_match.group(2) != '*' else None
                hop_time = float(hop_match.group(3))
                
                hops.append({
                    'hop': hop_num,
                    'ip': hop_ip,
                    'time_ms': hop_time
                })
                
        return hops
    except subprocess.TimeoutExpired:
        logger.warning(f"Traceroute to {host} timed out")
        return []
    except Exception as e:
        logger.error(f"Error performing traceroute to {host}: {str(e)}")
        return []

def nslookup(host: str) -> Dict[str, Any]:
    """
    Perform a DNS lookup for a hostname.
    
    Args:
        host (str): The hostname to lookup.
        
    Returns:
        dict: DNS lookup results.
    """
    try:
        # Get IP address
        ip_address = socket.gethostbyname(host)
        
        # Try to get hostname from IP
        try:
            hostname = socket.gethostbyaddr(ip_address)[0]
        except socket.herror:
            hostname = None
            
        return {
            'hostname': host,
            'ip': ip_address,
            'resolved_hostname': hostname
        }
    except socket.gaierror:
        return {
            'hostname': host,
            'error': 'Could not resolve hostname'
        }
    except Exception as e:
        logger.error(f"Error performing DNS lookup for {host}: {str(e)}")
        return {
            'hostname': host,
            'error': str(e)
        }
