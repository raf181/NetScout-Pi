"""
System utilities for monitoring and controlling the Raspberry Pi.
"""

import os
import psutil
import platform
import socket
import netifaces
import logging
import subprocess
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

def get_system_info() -> Dict[str, Any]:
    """
    Get basic system information.
    
    Returns:
        dict: System information.
    """
    try:
        # Get CPU temperature (Raspberry Pi specific)
        cpu_temp = None
        if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                cpu_temp = float(f.read().strip()) / 1000
        
        # Get network interfaces
        network_info = {}
        for interface in netifaces.interfaces():
            if interface == 'lo':  # Skip loopback
                continue
                
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                ipv4 = addrs[netifaces.AF_INET][0]
                network_info[interface] = {
                    'ip': ipv4.get('addr'),
                    'netmask': ipv4.get('netmask')
                }
                
                # Get interface statistics
                try:
                    stats = psutil.net_io_counters(pernic=True).get(interface)
                    if stats:
                        network_info[interface]['bytes_sent'] = stats.bytes_sent
                        network_info[interface]['bytes_recv'] = stats.bytes_recv
                except Exception as e:
                    logger.warning(f"Could not get network stats for {interface}: {str(e)}")
        
        # Build system info dict
        system_info = {
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'cpu_usage': psutil.cpu_percent(interval=0.1),
            'memory_total': psutil.virtual_memory().total,
            'memory_used': psutil.virtual_memory().used,
            'memory_percent': psutil.virtual_memory().percent,
            'disk_total': psutil.disk_usage('/').total,
            'disk_used': psutil.disk_usage('/').used,
            'disk_percent': psutil.disk_usage('/').percent,
            'network': network_info,
            'cpu_temperature': cpu_temp,
            'uptime': int(psutil.boot_time())
        }
        
        return system_info
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return {'error': str(e)}

def get_network_usage() -> Dict[str, Dict[str, int]]:
    """
    Get current network usage statistics.
    
    Returns:
        dict: Network usage by interface.
    """
    try:
        usage = {}
        net_io = psutil.net_io_counters(pernic=True)
        
        for interface, stats in net_io.items():
            if interface == 'lo':  # Skip loopback
                continue
                
            usage[interface] = {
                'bytes_sent': stats.bytes_sent,
                'bytes_recv': stats.bytes_recv,
                'packets_sent': stats.packets_sent,
                'packets_recv': stats.packets_recv,
                'errin': stats.errin,
                'errout': stats.errout,
                'dropin': stats.dropin,
                'dropout': stats.dropout
            }
            
        return usage
    except Exception as e:
        logger.error(f"Error getting network usage: {str(e)}")
        return {'error': str(e)}

def get_active_connections() -> List[Dict[str, Any]]:
    """
    Get list of active network connections.
    
    Returns:
        list: Active connections.
    """
    try:
        connections = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'ESTABLISHED':
                try:
                    process = psutil.Process(conn.pid).name() if conn.pid else None
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    process = None
                    
                connections.append({
                    'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                    'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    'status': conn.status,
                    'pid': conn.pid,
                    'process': process
                })
                
        return connections
    except Exception as e:
        logger.error(f"Error getting active connections: {str(e)}")
        return []

def get_ethernet_info() -> Dict[str, Any]:
    """
    Get information about Ethernet interfaces.
    
    Returns:
        dict: Ethernet interface information.
    """
    try:
        ethernet_info = {}
        # Common USB Ethernet interface names
        ethernet_interfaces = ['eth', 'enx', 'usb']
        
        for interface in netifaces.interfaces():
            # Check if interface name matches Ethernet pattern
            if any(interface.startswith(eth) for eth in ethernet_interfaces):
                info = {}
                
                # Get MAC address
                if netifaces.AF_LINK in netifaces.ifaddresses(interface):
                    link_info = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]
                    info['mac'] = link_info.get('addr')
                
                # Get IP address
                if netifaces.AF_INET in netifaces.ifaddresses(interface):
                    inet_info = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]
                    info['ip'] = inet_info.get('addr')
                    info['netmask'] = inet_info.get('netmask')
                    
                # Try to get connection speed
                try:
                    # This command works on Linux but requires root
                    output = subprocess.check_output(['ethtool', interface], 
                                                   stderr=subprocess.STDOUT).decode('utf-8')
                    
                    # Extract speed if available
                    for line in output.split('\n'):
                        if 'Speed:' in line:
                            info['speed'] = line.strip().split('Speed:')[1].strip()
                except Exception:
                    info['speed'] = 'Unknown'
                    
                ethernet_info[interface] = info
                
        return ethernet_info
    except Exception as e:
        logger.error(f"Error getting Ethernet info: {str(e)}")
        return {'error': str(e)}

def restart_service(service_name: str) -> Tuple[bool, str]:
    """
    Restart a system service.
    
    Args:
        service_name (str): Name of the service to restart.
        
    Returns:
        tuple: (success, message)
    """
    try:
        subprocess.check_output(['sudo', 'systemctl', 'restart', service_name], 
                               stderr=subprocess.STDOUT)
        return True, f"Service {service_name} restarted successfully"
    except subprocess.CalledProcessError as e:
        error_message = e.output.decode('utf-8')
        logger.error(f"Error restarting service {service_name}: {error_message}")
        return False, f"Failed to restart service: {error_message}"
    except Exception as e:
        logger.error(f"Error restarting service {service_name}: {str(e)}")
        return False, f"Failed to restart service: {str(e)}"
