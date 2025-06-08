#!/usr/bin/env python3
# NetProbe Pi - Packet Capture Plugin

import os
import sys
import subprocess
import time
import datetime
import json
import shutil
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class PacketCapturePlugin(PluginBase):
    """Plugin to capture network packets using tcpdump."""
    
    name = "packet_capture"
    description = "Capture network packets with tcpdump"
    version = "0.1.0"
    author = "NetProbe"
    permissions = ["sudo"]
    
    def run(self, interface=None, packet_count=None, filter=None, output_format=None, **kwargs):
        """Run the plugin.
        
        Args:
            interface (str, optional): Network interface to capture on. Defaults to eth0.
            packet_count (int, optional): Number of packets to capture. Defaults to 100.
            filter (str, optional): tcpdump filter expression. Defaults to None.
            output_format (str, optional): Output format ('text', 'pcap', 'both'). Defaults to 'text'.
            **kwargs: Additional arguments.
            
        Returns:
            dict: Packet capture results.
        """
        # Get parameters from config if not specified
        interface = interface or self.config.get('interface') or 'eth0'
        packet_count = int(kwargs.get('packet_count') or packet_count or self.config.get('packet_count') or 100)
        filter = filter or kwargs.get('filter') or self.config.get('filter') or ''
        output_format = output_format or self.config.get('output_format') or 'text'
        
        self.logger.info(f"Starting packet capture on interface: {interface}, packets: {packet_count}")
        
        result = {
            'timestamp': self.logger.get_timestamp(),
            'interface': interface,
            'packet_count': packet_count,
            'filter': filter,
            'output_format': output_format,
            'packets': [],
            'summary': {},
            'error': None,
            'pcap_file': None
        }
        
        try:
            # Create directory for packet captures if it doesn't exist
            captures_dir = os.path.join(base_dir, 'data', 'captures')
            os.makedirs(captures_dir, exist_ok=True)
            
            # Generate timestamp for filenames
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Define output files
            pcap_file = os.path.join(captures_dir, f"capture_{timestamp}.pcap")
            text_file = os.path.join(captures_dir, f"capture_{timestamp}.txt")
            
            # Build tcpdump command
            cmd = ['tcpdump', '-i', interface, '-n']
            
            # Add packet count
            cmd.extend(['-c', str(packet_count)])
            
            # Add filter if specified
            if filter:
                cmd.append(filter)
                
            # Add output options
            if output_format in ('pcap', 'both'):
                cmd.extend(['-w', pcap_file])
                result['pcap_file'] = pcap_file
                
            # Execute tcpdump command
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            if output_format == 'pcap':
                # Just capture to pcap file
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise Exception(f"tcpdump failed: {stderr}")
                    
                # Run tcpdump again to read the pcap file and get text output
                read_cmd = ['tcpdump', '-n', '-r', pcap_file]
                read_output = subprocess.check_output(read_cmd, text=True)
                
                # Parse the output
                result['packets'] = self._parse_tcpdump_output(read_output)
                
            elif output_format == 'text':
                # Capture and parse output directly
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise Exception(f"tcpdump failed: {stderr}")
                    
                # Parse the output
                result['packets'] = self._parse_tcpdump_output(stdout)
                
                # Save text output to file
                with open(text_file, 'w') as f:
                    f.write(stdout)
                    
            elif output_format == 'both':
                # Capture to pcap, then read and parse
                # We need a separate command for text output
                text_cmd = cmd.copy()
                text_cmd = [x for x in text_cmd if x != pcap_file and x != '-w']
                
                # Run the pcap capture first
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    raise Exception(f"tcpdump failed: {stderr}")
                
                # Run tcpdump again to read the pcap file
                read_cmd = ['tcpdump', '-n', '-r', pcap_file]
                read_output = subprocess.check_output(read_cmd, text=True)
                
                # Parse the output
                result['packets'] = self._parse_tcpdump_output(read_output)
                
                # Save text output to file
                with open(text_file, 'w') as f:
                    f.write(read_output)
            
            # Analyze packet capture for summary information
            result['summary'] = self._analyze_capture(result['packets'])
            
            self.logger.info(f"Packet capture completed. Captured {len(result['packets'])} packets.")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error during packet capture: {str(e)}")
            
        return result
    
    def _parse_tcpdump_output(self, output):
        """Parse tcpdump output into structured data."""
        packets = []
        
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith('reading from file'):
                continue
                
            # Try to parse the packet line
            try:
                # Extract timestamp
                timestamp_end = line.find(' ')
                if timestamp_end > 0:
                    timestamp = line[:timestamp_end]
                    remaining = line[timestamp_end+1:].strip()
                else:
                    timestamp = None
                    remaining = line
                
                packet = {
                    'timestamp': timestamp,
                    'raw': line
                }
                
                # Extract protocol
                if 'ICMP' in line:
                    packet['protocol'] = 'ICMP'
                elif 'UDP' in line:
                    packet['protocol'] = 'UDP'
                elif 'TCP' in line:
                    packet['protocol'] = 'TCP'
                elif 'ARP' in line:
                    packet['protocol'] = 'ARP'
                elif 'IP6' in line:
                    packet['protocol'] = 'IPv6'
                elif 'IP' in line:
                    packet['protocol'] = 'IPv4'
                else:
                    packet['protocol'] = 'Unknown'
                
                # Extract source and destination
                ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:\.(\d+))? > (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:\.(\d+))?'
                import re
                ip_match = re.search(ip_pattern, line)
                if ip_match:
                    packet['src_ip'] = ip_match.group(1)
                    packet['src_port'] = ip_match.group(2)
                    packet['dst_ip'] = ip_match.group(3)
                    packet['dst_port'] = ip_match.group(4)
                
                # Extract packet length
                length_match = re.search(r'length (\d+)', line)
                if length_match:
                    packet['length'] = int(length_match.group(1))
                
                # Extract TCP flags if present
                if packet['protocol'] == 'TCP':
                    flags_match = re.search(r'\[(.*?)\]', line)
                    if flags_match:
                        packet['tcp_flags'] = flags_match.group(1)
                
                packets.append(packet)
                
            except Exception as e:
                self.logger.debug(f"Error parsing packet line: {line}, error: {str(e)}")
                # Add raw line even if parsing failed
                packets.append({
                    'raw': line,
                    'protocol': 'Unknown'
                })
        
        return packets
    
    def _analyze_capture(self, packets):
        """Analyze packet capture for summary information."""
        summary = {
            'total_packets': len(packets),
            'protocols': {},
            'top_talkers': {},
            'packet_sizes': {
                'min': 0,
                'max': 0,
                'avg': 0
            },
            'vlan_tags_detected': False
        }
        
        # Protocol distribution
        for packet in packets:
            protocol = packet.get('protocol', 'Unknown')
            if protocol in summary['protocols']:
                summary['protocols'][protocol] += 1
            else:
                summary['protocols'][protocol] = 1
                
        # Top talkers (source IPs)
        for packet in packets:
            src_ip = packet.get('src_ip')
            if src_ip:
                if src_ip in summary['top_talkers']:
                    summary['top_talkers'][src_ip] += 1
                else:
                    summary['top_talkers'][src_ip] = 1
        
        # Convert to sorted list of (ip, count) tuples
        summary['top_talkers'] = sorted(
            [(ip, count) for ip, count in summary['top_talkers'].items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]  # Top 10
        
        # Packet sizes
        sizes = [p.get('length', 0) for p in packets if 'length' in p]
        if sizes:
            summary['packet_sizes']['min'] = min(sizes)
            summary['packet_sizes']['max'] = max(sizes)
            summary['packet_sizes']['avg'] = sum(sizes) / len(sizes)
            
        # Check for VLAN tags
        for packet in packets:
            if 'vlan' in packet.get('raw', '').lower():
                summary['vlan_tags_detected'] = True
                break
                
        return summary
