"""
Network Information Plugin for NetScout Pi.
Retrieves detailed information about the current network connection
including DNS, DHCP, VLAN, and other network configuration details.
"""

import subprocess
import socket
import re
import os
import json
import platform
import time
from typing import Dict, List, Any, Tuple, Optional

def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the network information plugin.
    
    Args:
        params (dict): Parameters for the plugin.
            - interface (str): The network interface to check (leave blank for auto-detection)
            - deep_scan (bool): Perform a more comprehensive scan of network settings
            
    Returns:
        dict: The network information results.
    """
    # Parse parameters with safe defaults
    interface = params.get('interface', '')
    deep_scan = bool(params.get('deep_scan', False))
    
    # Start tracking time
    start_time = time.time()
    
    try:
        # If no interface specified, detect the primary interface
        if not interface:
            interface = detect_primary_interface()
            if not interface:
                return {
                    'error': "Could not automatically detect a primary network interface."
                }
        
        # Collect basic network information
        basic_info = get_basic_network_info(interface)
        
        # Collect DNS information
        dns_info = get_dns_servers()
        
        # Collect DHCP information
        dhcp_info = get_dhcp_info(interface)
        
        # Get routing information
        routing_info = get_routing_info()
        
        # Get VLAN information if available
        vlan_info = get_vlan_info(interface)
        
        # Additional network data if deep scan is enabled
        additional_info = {}
        if deep_scan:
            additional_info = get_additional_network_info(interface)
        
        # Combine all information
        result = {
            'type': 'network_info',
            'interface': interface,
            'basic_info': basic_info,
            'dns_info': dns_info,
            'dhcp_info': dhcp_info,
            'routing_info': routing_info,
            'vlan_info': vlan_info,
            'scan_time': round(time.time() - start_time, 2)
        }
        
        # Add additional info for deep scans
        if deep_scan:
            result['additional_info'] = additional_info
        
        # Format the results in a user-friendly way for display
        formatted_sections = format_network_info_for_display(result)
        result['sections'] = formatted_sections
        
        return result
        
    except Exception as e:
        return {
            'error': f"Failed to retrieve network information: {str(e)}"
        }

def detect_primary_interface() -> str:
    """
    Detect the primary network interface by checking the default route.
    
    Returns:
        str: The name of the primary network interface.
    """
    try:
        if platform.system() == "Linux":
            # Method 1: Check the default route
            output = subprocess.check_output("ip route | grep default", shell=True, text=True)
            match = re.search(r'dev\s+(\S+)', output)
            if match:
                return match.group(1)
            
            # Method 2: Try to find an interface with an IP (excluding loopback)
            output = subprocess.check_output("ip -o addr show | grep 'inet ' | grep -v '127.0.0.1'", shell=True, text=True)
            if output:
                match = re.search(r'^\d+:\s+(\S+)', output.split('\n')[0])
                if match:
                    return match.group(1)
                    
        elif platform.system() == "Darwin":  # macOS
            # Check for default route on macOS
            output = subprocess.check_output("route -n get default | grep interface", shell=True, text=True)
            match = re.search(r'interface:\s+(\S+)', output)
            if match:
                return match.group(1)
                
        elif platform.system() == "Windows":
            # On Windows, this is more complex - simplified version
            output = subprocess.check_output("ipconfig", shell=True, text=True)
            # Find first adapter with IPv4 address that's not loopback
            sections = output.split('\n\n')
            for section in sections:
                if 'IPv4 Address' in section and '127.0.0.1' not in section:
                    match = re.search(r'Ethernet adapter\s+(.+):', section)
                    if match:
                        return match.group(1).strip()
        
        # Fallback: return the first non-loopback interface
        interfaces = socket.if_nameindex()
        for idx, name in interfaces:
            if name != 'lo' and not name.startswith('docker') and not name.startswith('veth'):
                return name
                
    except Exception as e:
        print(f"Error detecting primary interface: {e}")
        
    return ""

def get_basic_network_info(interface: str) -> Dict[str, Any]:
    """
    Get basic information about a network interface.
    
    Args:
        interface (str): The network interface name.
        
    Returns:
        dict: Basic network information.
    """
    info = {
        'ip_address': '',
        'mac_address': '',
        'netmask': '',
        'broadcast': '',
        'status': 'Unknown'
    }
    
    try:
        if platform.system() == "Linux":
            # Get IP, netmask, and broadcast
            ip_output = subprocess.check_output(f"ip addr show {interface}", shell=True, text=True)
            
            # Extract MAC address
            mac_match = re.search(r'link/ether\s+([0-9a-f:]{17})', ip_output, re.IGNORECASE)
            if mac_match:
                info['mac_address'] = mac_match.group(1)
                
            # Extract IPv4 address and netmask
            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)', ip_output)
            if ip_match:
                info['ip_address'] = ip_match.group(1)
                info['netmask'] = cidr_to_netmask(int(ip_match.group(2)))
                
            # Extract broadcast
            bcast_match = re.search(r'brd\s+(\d+\.\d+\.\d+\.\d+)', ip_output)
            if bcast_match:
                info['broadcast'] = bcast_match.group(1)
                
            # Check interface status
            if 'UP' in ip_output and 'RUNNING' in ip_output:
                info['status'] = 'Up'
            else:
                info['status'] = 'Down'
                
            # Get link speed and duplex mode if available
            try:
                ethtool_output = subprocess.check_output(f"ethtool {interface} 2>/dev/null", shell=True, text=True)
                speed_match = re.search(r'Speed:\s+(\d+[GMK]b/s)', ethtool_output)
                if speed_match:
                    info['speed'] = speed_match.group(1)
                    
                duplex_match = re.search(r'Duplex:\s+(\w+)', ethtool_output)
                if duplex_match:
                    info['duplex'] = duplex_match.group(1)
            except:
                # ethtool might not be available
                pass
                
        elif platform.system() == "Darwin":  # macOS
            # Get interface details on macOS
            ifconfig_output = subprocess.check_output(f"ifconfig {interface}", shell=True, text=True)
            
            # Extract MAC address
            mac_match = re.search(r'ether\s+([0-9a-f:]{17})', ifconfig_output, re.IGNORECASE)
            if mac_match:
                info['mac_address'] = mac_match.group(1)
                
            # Extract IPv4 address
            ip_match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)\s+netmask\s+0x([0-9a-f]{8})', ifconfig_output)
            if ip_match:
                info['ip_address'] = ip_match.group(1)
                netmask_hex = ip_match.group(2)
                # Convert hex netmask to dotted decimal
                netmask_parts = [str(int(netmask_hex[i:i+2], 16)) for i in range(0, 8, 2)]
                info['netmask'] = '.'.join(netmask_parts)
                
            # Extract broadcast
            bcast_match = re.search(r'broadcast\s+(\d+\.\d+\.\d+\.\d+)', ifconfig_output)
            if bcast_match:
                info['broadcast'] = bcast_match.group(1)
                
            # Check interface status
            if 'active' in ifconfig_output:
                info['status'] = 'Up'
            else:
                info['status'] = 'Down'
                
        elif platform.system() == "Windows":
            # Get interface details on Windows
            ipconfig_output = subprocess.check_output(f"ipconfig /all", shell=True, text=True)
            
            # Find the section for our interface
            pattern = rf"{interface}.*?(?=\n\n)"
            section_match = re.search(pattern, ipconfig_output, re.DOTALL)
            if section_match:
                section = section_match.group(0)
                
                # Extract IP address
                ip_match = re.search(r'IPv4 Address[^:]*:\s+(\d+\.\d+\.\d+\.\d+)', section)
                if ip_match:
                    info['ip_address'] = ip_match.group(1)
                    
                # Extract subnet mask
                mask_match = re.search(r'Subnet Mask[^:]*:\s+(\d+\.\d+\.\d+\.\d+)', section)
                if mask_match:
                    info['netmask'] = mask_match.group(1)
                    
                # Extract MAC address
                mac_match = re.search(r'Physical Address[^:]*:\s+([0-9A-F-]{17})', section)
                if mac_match:
                    info['mac_address'] = mac_match.group(1)
                    
                # Status is harder to determine on Windows via ipconfig
                info['status'] = 'Up' if info['ip_address'] else 'Down'
    
    except Exception as e:
        print(f"Error getting basic network info: {e}")
        info['error'] = str(e)
        
    return info

def get_dns_servers() -> Dict[str, Any]:
    """
    Get DNS server information.
    
    Returns:
        dict: DNS server information.
    """
    dns_info = {
        'servers': [],
        'search_domains': []
    }
    
    try:
        if platform.system() in ["Linux", "Darwin"]:
            # Check /etc/resolv.conf for DNS information
            if os.path.exists('/etc/resolv.conf'):
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('nameserver'):
                            dns_info['servers'].append(line.split()[1])
                        elif line.startswith('search'):
                            dns_info['search_domains'].extend(line.split()[1:])
                            
            # Try systemd-resolved if available (modern Linux systems)
            try:
                resolved_output = subprocess.check_output("systemd-resolve --status", shell=True, text=True)
                for line in resolved_output.split('\n'):
                    line = line.strip()
                    if 'DNS Servers' in line:
                        server = line.split(':')[1].strip()
                        if server and server not in dns_info['servers']:
                            dns_info['servers'].append(server)
            except:
                # systemd-resolved might not be available
                pass
                
        elif platform.system() == "Windows":
            # Get DNS servers on Windows
            ipconfig_output = subprocess.check_output("ipconfig /all", shell=True, text=True)
            dns_servers = re.findall(r'DNS Servers[^:]*:\s+(\d+\.\d+\.\d+\.\d+)', ipconfig_output)
            dns_info['servers'] = dns_servers
            
            # Get search domains (suffix)
            search_domains = re.findall(r'DNS Suffix Search List[^:]*:\s+(.+)', ipconfig_output)
            if search_domains:
                dns_info['search_domains'] = [d.strip() for d in search_domains[0].split(',')]
    
    except Exception as e:
        print(f"Error getting DNS info: {e}")
        dns_info['error'] = str(e)
        
    return dns_info

def get_dhcp_info(interface: str) -> Dict[str, Any]:
    """
    Get DHCP information for a network interface.
    
    Args:
        interface (str): The network interface name.
        
    Returns:
        dict: DHCP information.
    """
    dhcp_info = {
        'enabled': False,
        'server': '',
        'lease_time': '',
        'obtained': '',
        'expires': ''
    }
    
    try:
        if platform.system() == "Linux":
            # Check if dhclient is running for this interface
            try:
                ps_output = subprocess.check_output(f"ps -ef | grep dhclient | grep {interface}", shell=True, text=True)
                dhcp_info['enabled'] = bool(ps_output.strip())
            except:
                # If error, the process might not be running
                dhcp_info['enabled'] = False
                
            # Try to get DHCP information from lease file
            lease_files = [
                f"/var/lib/dhcp/dhclient.{interface}.leases",
                f"/var/lib/dhclient/dhclient.{interface}.leases",
                "/var/lib/dhcp/dhclient.leases"
            ]
            
            for lease_file in lease_files:
                if os.path.exists(lease_file):
                    with open(lease_file, 'r') as f:
                        content = f.read()
                        # Find the most recent lease block
                        lease_blocks = re.findall(r'lease {(.*?)}', content, re.DOTALL)
                        if lease_blocks:
                            latest_lease = lease_blocks[-1]  # Assume the last one is the latest
                            
                            # Extract server identifier
                            server_match = re.search(r'option dhcp-server-identifier (\d+\.\d+\.\d+\.\d+);', latest_lease)
                            if server_match:
                                dhcp_info['server'] = server_match.group(1)
                                dhcp_info['enabled'] = True
                                
                            # Extract lease times
                            start_match = re.search(r'starts \d+ (\d+/\d+/\d+ \d+:\d+:\d+);', latest_lease)
                            if start_match:
                                dhcp_info['obtained'] = start_match.group(1)
                                
                            end_match = re.search(r'ends \d+ (\d+/\d+/\d+ \d+:\d+:\d+);', latest_lease)
                            if end_match:
                                dhcp_info['expires'] = end_match.group(1)
                                
                            # Calculate lease time if we have both start and end
                            if dhcp_info['obtained'] and dhcp_info['expires']:
                                # Simplified for now - just show the values
                                dhcp_info['lease_time'] = 'See obtained and expires times'
                                
                    break  # Stop after finding the first valid lease file
                    
            # NetworkManager might have DHCP info
            try:
                nm_output = subprocess.check_output(f"nmcli -t -f DHCP4 device show {interface}", shell=True, text=True)
                for line in nm_output.split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if 'dhcp_server_identifier' in key and value:
                            dhcp_info['server'] = value
                            dhcp_info['enabled'] = True
                        elif 'dhcp_lease_time' in key and value:
                            dhcp_info['lease_time'] = f"{value} seconds"
            except:
                # NetworkManager might not be available
                pass
                
        elif platform.system() == "Darwin":  # macOS
            # Use ipconfig to get DHCP info on macOS
            try:
                ipconfig_output = subprocess.check_output(f"ipconfig getpacket {interface}", shell=True, text=True)
                
                # Check if DHCP is enabled
                dhcp_info['enabled'] = 'BOOTREPLY' in ipconfig_output
                
                # Extract DHCP server
                server_match = re.search(r'server_identifier \(ip\): (\d+\.\d+\.\d+\.\d+)', ipconfig_output)
                if server_match:
                    dhcp_info['server'] = server_match.group(1)
                    
                # Extract lease time
                lease_match = re.search(r'lease_time \(seconds\): (\d+)', ipconfig_output)
                if lease_match:
                    dhcp_info['lease_time'] = f"{lease_match.group(1)} seconds"
            except:
                # Interface might not have DHCP enabled
                pass
                
        elif platform.system() == "Windows":
            # Get DHCP info on Windows
            ipconfig_output = subprocess.check_output("ipconfig /all", shell=True, text=True)
            
            # Find the section for our interface
            pattern = rf"{interface}.*?(?=\n\n)"
            section_match = re.search(pattern, ipconfig_output, re.DOTALL)
            if section_match:
                section = section_match.group(0)
                
                # Check if DHCP is enabled
                dhcp_match = re.search(r'DHCP Enabled[^:]*:\s+Yes', section, re.IGNORECASE)
                dhcp_info['enabled'] = bool(dhcp_match)
                
                # Extract DHCP server
                server_match = re.search(r'DHCP Server[^:]*:\s+(\d+\.\d+\.\d+\.\d+)', section)
                if server_match:
                    dhcp_info['server'] = server_match.group(1)
                    
                # Extract lease times
                obtained_match = re.search(r'Lease Obtained[^:]*:\s+(.+)', section)
                if obtained_match:
                    dhcp_info['obtained'] = obtained_match.group(1)
                    
                expires_match = re.search(r'Lease Expires[^:]*:\s+(.+)', section)
                if expires_match:
                    dhcp_info['expires'] = expires_match.group(1)
    
    except Exception as e:
        print(f"Error getting DHCP info: {e}")
        dhcp_info['error'] = str(e)
        
    return dhcp_info

def get_routing_info() -> Dict[str, Any]:
    """
    Get routing information.
    
    Returns:
        dict: Routing information.
    """
    routing_info = {
        'default_gateway': '',
        'routes': []
    }
    
    try:
        if platform.system() == "Linux":
            # Get default gateway
            try:
                ip_route = subprocess.check_output("ip route | grep default", shell=True, text=True)
                match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', ip_route)
                if match:
                    routing_info['default_gateway'] = match.group(1)
            except:
                pass
                
            # Get routing table (simplified)
            try:
                routes_output = subprocess.check_output("ip route | grep -v default", shell=True, text=True)
                for line in routes_output.strip().split('\n'):
                    if line:
                        routing_info['routes'].append(line.strip())
            except:
                pass
                
        elif platform.system() == "Darwin":  # macOS
            # Get default gateway on macOS
            try:
                route_output = subprocess.check_output("route -n get default", shell=True, text=True)
                match = re.search(r'gateway: (\d+\.\d+\.\d+\.\d+)', route_output)
                if match:
                    routing_info['default_gateway'] = match.group(1)
            except:
                pass
                
            # Get routing table (simplified)
            try:
                routes_output = subprocess.check_output("netstat -nr -f inet", shell=True, text=True)
                for line in routes_output.strip().split('\n'):
                    if not line.startswith(('Destination', 'default', '-')):
                        routing_info['routes'].append(line.strip())
            except:
                pass
                
        elif platform.system() == "Windows":
            # Get default gateway on Windows
            try:
                ipconfig_output = subprocess.check_output("ipconfig", shell=True, text=True)
                match = re.search(r'Default Gateway[^:]*:\s+(\d+\.\d+\.\d+\.\d+)', ipconfig_output)
                if match:
                    routing_info['default_gateway'] = match.group(1)
            except:
                pass
                
            # Get routing table (simplified)
            try:
                routes_output = subprocess.check_output("route print", shell=True, text=True)
                route_section = False
                for line in routes_output.strip().split('\n'):
                    if "Persistent Routes:" in line:
                        route_section = False
                    if route_section and re.match(r'^\s+\d+\.\d+\.\d+\.\d+', line):
                        routing_info['routes'].append(line.strip())
                    if "Active Routes:" in line:
                        route_section = True
            except:
                pass
    
    except Exception as e:
        print(f"Error getting routing info: {e}")
        routing_info['error'] = str(e)
        
    return routing_info

def get_vlan_info(interface: str) -> Dict[str, Any]:
    """
    Get VLAN information for a network interface.
    
    Args:
        interface (str): The network interface name.
        
    Returns:
        dict: VLAN information.
    """
    vlan_info = {
        'enabled': False,
        'id': '',
        'parent_interface': '',
        'qos': ''
    }
    
    try:
        if platform.system() == "Linux":
            # Check if this is a VLAN interface
            if '.' in interface:
                vlan_info['enabled'] = True
                vlan_info['id'] = interface.split('.')[-1]
                vlan_info['parent_interface'] = interface.split('.')[0]
                
            # Check with ip command for explicit VLAN info
            try:
                ip_output = subprocess.check_output(f"ip -d link show {interface}", shell=True, text=True)
                vlan_match = re.search(r'vlan protocol 802.1Q id (\d+) ', ip_output)
                if vlan_match:
                    vlan_info['enabled'] = True
                    vlan_info['id'] = vlan_match.group(1)
                    
                # Try to find the parent interface
                parent_match = re.search(r'vlan protocol 802.1Q id \d+ <[^>]*> dev (\S+)', ip_output)
                if parent_match:
                    vlan_info['parent_interface'] = parent_match.group(1)
            except:
                pass
                
            # Another method: check /proc/net/vlan
            if os.path.exists(f"/proc/net/vlan/{interface}"):
                vlan_info['enabled'] = True
                try:
                    with open(f"/proc/net/vlan/{interface}", 'r') as f:
                        content = f.read()
                        id_match = re.search(r'VID: (\d+)', content)
                        if id_match:
                            vlan_info['id'] = id_match.group(1)
                            
                        parent_match = re.search(r'Device: (\S+)', content)
                        if parent_match:
                            vlan_info['parent_interface'] = parent_match.group(1)
                except:
                    pass
        
        elif platform.system() == "Darwin":  # macOS
            # macOS VLAN information can be checked with ifconfig
            try:
                ifconfig_output = subprocess.check_output(f"ifconfig {interface}", shell=True, text=True)
                vlan_match = re.search(r'vlan: (\d+) parent interface: (\S+)', ifconfig_output)
                if vlan_match:
                    vlan_info['enabled'] = True
                    vlan_info['id'] = vlan_match.group(1)
                    vlan_info['parent_interface'] = vlan_match.group(2)
            except:
                pass
                
        elif platform.system() == "Windows":
            # Windows VLAN information is less straightforward
            # For now, we'll use a heuristic approach based on interface naming
            if 'VLAN' in interface:
                vlan_info['enabled'] = True
                # Try to extract VLAN ID from the interface name
                vlan_match = re.search(r'VLAN\s*(\d+)', interface)
                if vlan_match:
                    vlan_info['id'] = vlan_match.group(1)
    
    except Exception as e:
        print(f"Error getting VLAN info: {e}")
        vlan_info['error'] = str(e)
        
    return vlan_info

def get_additional_network_info(interface: str) -> Dict[str, Any]:
    """
    Get additional network information for deep scan.
    
    Args:
        interface (str): The network interface name.
        
    Returns:
        dict: Additional network information.
    """
    additional_info = {
        'gateway_mac': '',
        'connection_type': '',
        'mtu': '',
        'ipv6_address': '',
        'netbios': {},
        'network_services': []
    }
    
    try:
        if platform.system() == "Linux":
            # Get interface MTU
            try:
                ip_output = subprocess.check_output(f"ip link show {interface}", shell=True, text=True)
                mtu_match = re.search(r'mtu (\d+)', ip_output)
                if mtu_match:
                    additional_info['mtu'] = mtu_match.group(1)
            except:
                pass
                
            # Get IPv6 address
            try:
                ip_output = subprocess.check_output(f"ip -6 addr show {interface}", shell=True, text=True)
                ipv6_match = re.search(r'inet6 ([0-9a-f:]+)/\d+', ip_output)
                if ipv6_match:
                    additional_info['ipv6_address'] = ipv6_match.group(1)
            except:
                pass
                
            # Try to determine connection type
            try:
                if os.path.exists(f"/sys/class/net/{interface}/wireless"):
                    additional_info['connection_type'] = 'Wireless'
                elif 'eth' in interface or interface.startswith('en'):
                    additional_info['connection_type'] = 'Ethernet'
                elif interface.startswith('wwan'):
                    additional_info['connection_type'] = 'Cellular'
                elif interface.startswith('tun') or interface.startswith('tap'):
                    additional_info['connection_type'] = 'VPN/Tunnel'
            except:
                pass
                
            # Get gateway MAC address
            try:
                routing_info = get_routing_info()
                if routing_info['default_gateway']:
                    # Use ARP to get the MAC of the gateway
                    arp_output = subprocess.check_output(f"arp -n {routing_info['default_gateway']}", shell=True, text=True)
                    mac_match = re.search(r'([0-9a-f:]{17})', arp_output, re.IGNORECASE)
                    if mac_match:
                        additional_info['gateway_mac'] = mac_match.group(1)
            except:
                pass
                
            # Get running network services
            try:
                ss_output = subprocess.check_output("ss -tuln | grep LISTEN", shell=True, text=True)
                services = []
                for line in ss_output.strip().split('\n'):
                    if ':' in line:
                        match = re.search(r':(\d+)\s', line)
                        if match:
                            port = match.group(1)
                            # Determine service based on common port numbers
                            service = get_service_name(port)
                            services.append(f"{service} (Port {port})")
                
                additional_info['network_services'] = services
            except:
                pass
                
        elif platform.system() == "Darwin":  # macOS
            # Get interface MTU
            try:
                ifconfig_output = subprocess.check_output(f"ifconfig {interface}", shell=True, text=True)
                mtu_match = re.search(r'mtu (\d+)', ifconfig_output)
                if mtu_match:
                    additional_info['mtu'] = mtu_match.group(1)
            except:
                pass
                
            # Get IPv6 address
            try:
                ifconfig_output = subprocess.check_output(f"ifconfig {interface}", shell=True, text=True)
                ipv6_match = re.search(r'inet6 ([0-9a-f:]+)%', ifconfig_output)
                if ipv6_match:
                    additional_info['ipv6_address'] = ipv6_match.group(1)
            except:
                pass
                
            # Determine connection type
            try:
                if interface.startswith('en'):
                    # Check if it's Wi-Fi
                    system_profiler = subprocess.check_output(f"system_profiler SPNetworkDataType | grep -A 10 '{interface}'", shell=True, text=True)
                    if 'Wi-Fi' in system_profiler:
                        additional_info['connection_type'] = 'Wireless'
                    else:
                        additional_info['connection_type'] = 'Ethernet'
                elif interface.startswith('utun'):
                    additional_info['connection_type'] = 'VPN/Tunnel'
            except:
                pass
                
            # Get gateway MAC address
            try:
                routing_info = get_routing_info()
                if routing_info['default_gateway']:
                    # Use arp to get the MAC of the gateway
                    arp_output = subprocess.check_output(f"arp -n {routing_info['default_gateway']}", shell=True, text=True)
                    mac_match = re.search(r'([0-9a-f:]{17})', arp_output, re.IGNORECASE)
                    if mac_match:
                        additional_info['gateway_mac'] = mac_match.group(1)
            except:
                pass
                
            # Get running network services
            try:
                netstat_output = subprocess.check_output("netstat -an | grep LISTEN", shell=True, text=True)
                services = []
                for line in netstat_output.strip().split('\n'):
                    if '.' in line:
                        match = re.search(r'\.(\d+)\s', line)
                        if match:
                            port = match.group(1)
                            # Determine service based on common port numbers
                            service = get_service_name(port)
                            services.append(f"{service} (Port {port})")
                
                additional_info['network_services'] = services
            except:
                pass
                
        elif platform.system() == "Windows":
            # Get network information on Windows
            ipconfig_output = subprocess.check_output("ipconfig /all", shell=True, text=True)
            
            # Find the section for our interface
            pattern = rf"{interface}.*?(?=\n\n)"
            section_match = re.search(pattern, ipconfig_output, re.DOTALL)
            if section_match:
                section = section_match.group(0)
                
                # Get IPv6 address
                ipv6_match = re.search(r'IPv6 Address[^:]*:\s+([0-9a-f:]+)', section)
                if ipv6_match:
                    additional_info['ipv6_address'] = ipv6_match.group(1)
                    
                # Get MTU (not available in ipconfig, need netsh)
                try:
                    netsh_output = subprocess.check_output(f"netsh interface ipv4 show subinterfaces", shell=True, text=True)
                    lines = netsh_output.strip().split('\n')
                    for i, line in enumerate(lines):
                        if interface in line:
                            mtu_match = re.search(r'(\d+)\s*$', line)
                            if mtu_match:
                                additional_info['mtu'] = mtu_match.group(1)
                except:
                    pass
                    
                # Determine connection type
                if 'Wireless' in section:
                    additional_info['connection_type'] = 'Wireless'
                elif 'Ethernet' in section:
                    additional_info['connection_type'] = 'Ethernet'
                elif 'Tunnel' in section or 'VPN' in section:
                    additional_info['connection_type'] = 'VPN/Tunnel'
                    
                # Get NetBIOS information
                netbios_match = re.search(r'NetBIOS over Tcpip[^:]*:\s+(\S+)', section)
                if netbios_match:
                    additional_info['netbios']['enabled'] = netbios_match.group(1).lower() == 'enabled'
                    
            # Get running network services
            try:
                netstat_output = subprocess.check_output("netstat -an | findstr LISTENING", shell=True, text=True)
                services = []
                for line in netstat_output.strip().split('\n'):
                    if ':' in line:
                        match = re.search(r':(\d+)\s', line)
                        if match:
                            port = match.group(1)
                            # Determine service based on common port numbers
                            service = get_service_name(port)
                            services.append(f"{service} (Port {port})")
                
                additional_info['network_services'] = services
            except:
                pass
    
    except Exception as e:
        print(f"Error getting additional network info: {e}")
        additional_info['error'] = str(e)
        
    return additional_info

def format_network_info_for_display(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Format network information for display in the UI.
    
    Args:
        info (dict): The network information.
        
    Returns:
        list: Formatted sections for display.
    """
    sections = []
    
    # Basic network information section
    basic_section = {
        'title': 'Basic Network Information',
        'type': 'key_value',
        'data': []
    }
    
    if 'basic_info' in info:
        basic_info = info['basic_info']
        basic_section['data'] = [
            {'key': 'Interface', 'value': info['interface']},
            {'key': 'IP Address', 'value': basic_info.get('ip_address', 'Not available')},
            {'key': 'MAC Address', 'value': basic_info.get('mac_address', 'Not available')},
            {'key': 'Netmask', 'value': basic_info.get('netmask', 'Not available')},
            {'key': 'Broadcast', 'value': basic_info.get('broadcast', 'Not available')},
            {'key': 'Status', 'value': basic_info.get('status', 'Unknown')}
        ]
        
        # Add speed and duplex if available
        if 'speed' in basic_info:
            basic_section['data'].append({'key': 'Speed', 'value': basic_info['speed']})
        if 'duplex' in basic_info:
            basic_section['data'].append({'key': 'Duplex', 'value': basic_info['duplex']})
            
    sections.append(basic_section)
    
    # DNS information section
    dns_section = {
        'title': 'DNS Information',
        'type': 'key_value',
        'data': []
    }
    
    if 'dns_info' in info:
        dns_info = info['dns_info']
        dns_servers = dns_info.get('servers', [])
        dns_section['data'].append({
            'key': 'DNS Servers',
            'value': ', '.join(dns_servers) if dns_servers else 'None detected'
        })
        
        search_domains = dns_info.get('search_domains', [])
        dns_section['data'].append({
            'key': 'Search Domains',
            'value': ', '.join(search_domains) if search_domains else 'None detected'
        })
        
    sections.append(dns_section)
    
    # DHCP information section
    dhcp_section = {
        'title': 'DHCP Information',
        'type': 'key_value',
        'data': []
    }
    
    if 'dhcp_info' in info:
        dhcp_info = info['dhcp_info']
        dhcp_section['data'] = [
            {'key': 'DHCP Enabled', 'value': 'Yes' if dhcp_info.get('enabled', False) else 'No'},
            {'key': 'DHCP Server', 'value': dhcp_info.get('server', 'Not available')},
            {'key': 'Lease Time', 'value': dhcp_info.get('lease_time', 'Not available')},
            {'key': 'Lease Obtained', 'value': dhcp_info.get('obtained', 'Not available')},
            {'key': 'Lease Expires', 'value': dhcp_info.get('expires', 'Not available')}
        ]
        
    sections.append(dhcp_section)
    
    # Routing information section
    routing_section = {
        'title': 'Routing Information',
        'type': 'key_value',
        'data': []
    }
    
    if 'routing_info' in info:
        routing_info = info['routing_info']
        routing_section['data'].append({
            'key': 'Default Gateway',
            'value': routing_info.get('default_gateway', 'Not available')
        })
        
        # Add routing table as a separate section if not empty
        routes = routing_info.get('routes', [])
        if routes:
            routes_section = {
                'title': 'Routing Table',
                'type': 'list',
                'data': routes
            }
            sections.append(routes_section)
        
    sections.append(routing_section)
    
    # VLAN information section
    vlan_section = {
        'title': 'VLAN Information',
        'type': 'key_value',
        'data': []
    }
    
    if 'vlan_info' in info:
        vlan_info = info['vlan_info']
        vlan_enabled = vlan_info.get('enabled', False)
        vlan_section['data'] = [
            {'key': 'VLAN Enabled', 'value': 'Yes' if vlan_enabled else 'No'}
        ]
        
        if vlan_enabled:
            vlan_section['data'].extend([
                {'key': 'VLAN ID', 'value': vlan_info.get('id', 'Not available')},
                {'key': 'Parent Interface', 'value': vlan_info.get('parent_interface', 'Not available')},
                {'key': 'QoS Priority', 'value': vlan_info.get('qos', 'Not available')}
            ])
        
    sections.append(vlan_section)
    
    # Additional information section (for deep scan)
    if 'additional_info' in info:
        additional_info = info['additional_info']
        
        # Additional basic info
        additional_basic = {
            'title': 'Additional Network Information',
            'type': 'key_value',
            'data': [
                {'key': 'IPv6 Address', 'value': additional_info.get('ipv6_address', 'Not available')},
                {'key': 'Connection Type', 'value': additional_info.get('connection_type', 'Unknown')},
                {'key': 'MTU', 'value': additional_info.get('mtu', 'Not available')},
                {'key': 'Gateway MAC', 'value': additional_info.get('gateway_mac', 'Not available')}
            ]
        }
        sections.append(additional_basic)
        
        # NetBIOS information
        if 'netbios' in additional_info and additional_info['netbios']:
            netbios_section = {
                'title': 'NetBIOS Information',
                'type': 'key_value',
                'data': [
                    {'key': 'NetBIOS Enabled', 'value': 'Yes' if additional_info['netbios'].get('enabled', False) else 'No'}
                ]
            }
            sections.append(netbios_section)
        
        # Network services
        services = additional_info.get('network_services', [])
        if services:
            services_section = {
                'title': 'Network Services',
                'type': 'list',
                'data': services
            }
            sections.append(services_section)
    
    # Add scan info
    scan_section = {
        'title': 'Scan Information',
        'type': 'key_value',
        'data': [
            {'key': 'Scan Time', 'value': f"{info.get('scan_time', 0)} seconds"},
            {'key': 'Deep Scan', 'value': 'Yes' if 'additional_info' in info else 'No'}
        ]
    }
    sections.append(scan_section)
    
    return sections

def cidr_to_netmask(cidr: int) -> str:
    """
    Convert CIDR notation to a dotted decimal netmask.
    
    Args:
        cidr (int): The CIDR prefix length.
        
    Returns:
        str: The dotted decimal netmask.
    """
    binary_str = '1' * cidr + '0' * (32 - cidr)
    octets = [binary_str[i:i+8] for i in range(0, 32, 8)]
    decimal_octets = [str(int(octet, 2)) for octet in octets]
    return '.'.join(decimal_octets)

def get_service_name(port: str) -> str:
    """
    Get a common service name for a port number.
    
    Args:
        port (str): The port number as a string.
        
    Returns:
        str: The service name.
    """
    port_map = {
        '21': 'FTP',
        '22': 'SSH',
        '23': 'Telnet',
        '25': 'SMTP',
        '53': 'DNS',
        '67': 'DHCP',
        '68': 'DHCP',
        '80': 'HTTP',
        '110': 'POP3',
        '123': 'NTP',
        '143': 'IMAP',
        '161': 'SNMP',
        '443': 'HTTPS',
        '445': 'SMB',
        '465': 'SMTPS',
        '993': 'IMAPS',
        '995': 'POP3S',
        '3306': 'MySQL',
        '3389': 'RDP',
        '5432': 'PostgreSQL',
        '8000': 'HTTP Alt',
        '8080': 'HTTP Proxy',
        '8443': 'HTTPS Alt'
    }
    
    return port_map.get(port, 'Unknown Service')
