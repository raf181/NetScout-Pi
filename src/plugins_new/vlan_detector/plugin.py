#!/usr/bin/env python3
# NetProbe Pi - VLAN Detector Plugin

import os
import sys
import subprocess
import time
import datetime
import re
from pathlib import Path
from scapy.all import sniff, Dot1Q

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class VLANDetectorPlugin(PluginBase):
    """Plugin to detect VLAN tags in network packets."""
    def __init__(self, config, logger):
        """Initialize plugin.
        
        Args:
            config: Plugin configuration.
            logger: PluginLogger instance.
        """
        super().__init__(config, logger)
        
        # Read metadata from config.json
        self.metadata = self.config.get('metadata', {})
        self.name = self.metadata.get('name', 'vlan_detector')
        self.description = self.metadata.get('description', 'Detect VLAN tags in network packets')
        self.version = self.metadata.get('version', '0.1.0')
        self.author = self.metadata.get('author', 'NetProbe')
        self.permissions = self.metadata.get('permissions', ['sudo'])
        self.category = self.metadata.get('category', 'general')
        self.tags = self.metadata.get('tags', [])
        
        # Initialize plugin-specific variables
        self.plugin_dir = Path(__file__).resolve().parent
    
    
    
    
    
    
    
    
    def run(self, interface=None, packet_count=None, duration=None, **kwargs):
        """Run the plugin.
        
        Args:
            interface (str, optional): Network interface to monitor. Defaults to eth0.
            packet_count (int, optional): Number of packets to analyze. Defaults to 1000.
            duration (int, optional): Duration in seconds to sniff for. Defaults to 30.
            **kwargs: Additional arguments.
            
        Returns:
            dict: VLAN detection results.
        """
        # Get parameters from config if not specified
        interface = interface or self.config.get('interface') or 'eth0'
        packet_count = int(kwargs.get('packet_count') or packet_count or self.config.get('packet_count') or 1000)
        duration = int(kwargs.get('duration') or duration or self.config.get('duration') or 30)
        
        self.logger.info(f"Starting VLAN detection on interface: {interface}, packets: {packet_count}, duration: {duration}s")
        
        result = {
            'timestamp': self.logger.get_timestamp(),
            'interface': interface,
            'packet_count': packet_count,
            'duration': duration,
            'vlans_detected': False,
            'vlan_stats': {},
            'total_packets': 0,
            'vlan_packets': 0,
            'error': None
        }
        
        try:
            # Check if interface supports promiscuous mode
            try:
                self._check_promisc_support(interface)
            except Exception as e:
                self.logger.warning(f"Promiscuous mode check failed: {str(e)}")
            
            # Use both methods for better detection coverage
            scapy_result = self._detect_with_scapy(interface, packet_count, duration)
            tcpdump_result = self._detect_with_tcpdump(interface, packet_count)
            
            # Merge results
            result['vlans_detected'] = scapy_result['vlans_detected'] or tcpdump_result['vlans_detected']
            result['total_packets'] = scapy_result['total_packets'] + tcpdump_result['total_packets']
            result['vlan_packets'] = scapy_result['vlan_packets'] + tcpdump_result['vlan_packets']
            
            # Merge VLAN stats
            for vlan_id, count in scapy_result['vlan_stats'].items():
                if vlan_id in result['vlan_stats']:
                    result['vlan_stats'][vlan_id] += count
                else:
                    result['vlan_stats'][vlan_id] = count
                    
            for vlan_id, count in tcpdump_result['vlan_stats'].items():
                if vlan_id in result['vlan_stats']:
                    result['vlan_stats'][vlan_id] += count
                else:
                    result['vlan_stats'][vlan_id] = count
            
            # Convert to sorted list
            result['vlan_stats'] = sorted(
                [(vlan_id, count) for vlan_id, count in result['vlan_stats'].items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Additional analysis
            if result['vlans_detected']:
                result['vlan_percentage'] = (result['vlan_packets'] / result['total_packets']) * 100 if result['total_packets'] > 0 else 0
                result['primary_vlan'] = result['vlan_stats'][0][0] if result['vlan_stats'] else None
            
            self.logger.info(f"VLAN detection completed. VLANs detected: {result['vlans_detected']}")
            if result['vlans_detected']:
                vlan_ids = [vlan_id for vlan_id, _ in result['vlan_stats']]
                self.logger.info(f"Detected VLAN IDs: {vlan_ids}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error during VLAN detection: {str(e)}")
            
        return result
    
    def _check_promisc_support(self, interface):
        """Check if interface supports promiscuous mode."""
        try:
            # Try to set promiscuous mode
            subprocess.check_call(['ip', 'link', 'set', interface, 'promisc', 'on'])
            
            # Verify that it was set
            output = subprocess.check_output(['ip', 'link', 'show', interface], text=True)
            if 'PROMISC' not in output:
                self.logger.warning(f"Failed to enable promiscuous mode on {interface}")
                
            # Set it back to normal
            subprocess.check_call(['ip', 'link', 'set', interface, 'promisc', 'off'])
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Error setting promiscuous mode: {str(e)}")
    
    def _detect_with_scapy(self, interface, packet_count, duration):
        """Detect VLANs using Scapy packet sniffing."""
        result = {
            'vlans_detected': False,
            'vlan_stats': {},
            'total_packets': 0,
            'vlan_packets': 0
        }
        
        try:
            # Initialize stats
            vlan_counter = {}
            packet_counter = 0
            vlan_packet_counter = 0
            
            # Define packet handler
            def packet_handler(pkt):
                nonlocal packet_counter, vlan_packet_counter
                
                packet_counter += 1
                
                # Check for VLAN tag (802.1Q)
                if Dot1Q in pkt:
                    vlan_id = pkt[Dot1Q].vlan
                    vlan_packet_counter += 1
                    
                    if vlan_id in vlan_counter:
                        vlan_counter[vlan_id] += 1
                    else:
                        vlan_counter[vlan_id] = 1
                        
                # Stop after enough packets
                return packet_counter >= packet_count
            
            # Start sniffing
            self.logger.info(f"Starting Scapy packet sniffing on {interface} for {duration}s or {packet_count} packets")
            sniff(iface=interface, prn=packet_handler, store=0, timeout=duration)
            
            # Update result
            result['total_packets'] = packet_counter
            result['vlan_packets'] = vlan_packet_counter
            result['vlan_stats'] = vlan_counter
            result['vlans_detected'] = vlan_packet_counter > 0
            
            self.logger.info(f"Scapy detection: {result['vlan_packets']}/{result['total_packets']} packets had VLAN tags")
            
        except Exception as e:
            self.logger.error(f"Error in Scapy VLAN detection: {str(e)}")
            
        return result
    
    def _detect_with_tcpdump(self, interface, packet_count):
        """Detect VLANs using tcpdump."""
        result = {
            'vlans_detected': False,
            'vlan_stats': {},
            'total_packets': 0,
            'vlan_packets': 0
        }
        
        try:
            # Build tcpdump command
            cmd = [
                'tcpdump', '-i', interface, '-n', '-c', str(packet_count),
                '-v'  # Verbose to see VLAN tags
            ]
            
            # Execute tcpdump command
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Process output in real-time
            vlan_counter = {}
            packet_counter = 0
            vlan_packet_counter = 0
            
            # Regular expression to extract VLAN ID
            vlan_pattern = r'vlan (\d+)'
            
            # Read output line by line
            for line in iter(process.stdout.readline, ''):
                if not line.strip():
                    continue
                    
                packet_counter += 1
                
                # Check for VLAN tag
                vlan_match = re.search(vlan_pattern, line.lower())
                if vlan_match:
                    vlan_id = int(vlan_match.group(1))
                    vlan_packet_counter += 1
                    
                    if vlan_id in vlan_counter:
                        vlan_counter[vlan_id] += 1
                    else:
                        vlan_counter[vlan_id] = 1
            
            # Wait for process to complete
            process.wait()
            
            # Check stderr for errors
            stderr = process.stderr.read()
            if stderr and process.returncode != 0:
                self.logger.warning(f"tcpdump error: {stderr}")
            
            # Update result
            result['total_packets'] = packet_counter
            result['vlan_packets'] = vlan_packet_counter
            result['vlan_stats'] = vlan_counter
            result['vlans_detected'] = vlan_packet_counter > 0
            
            self.logger.info(f"tcpdump detection: {result['vlan_packets']}/{result['total_packets']} packets had VLAN tags")
            
        except Exception as e:
            self.logger.error(f"Error in tcpdump VLAN detection: {str(e)}")
            
        return result
        
    def get_vlan_info(self, vlan_id):
        """Get information about a specific VLAN ID."""
        # Common VLAN ranges and their typical usage
        vlan_ranges = {
            (1, 1): "Default VLAN (often native/untagged)",
            (2, 99): "Normal range for user VLANs",
            (100, 999): "Extended user VLANs",
            (1000, 1999): "Often used for voice VLANs or special services",
            (2000, 2999): "Often used for management purposes",
            (3000, 3999): "Often used for guest networks or DMZ",
            (4000, 4094): "Reserved or special purpose VLANs"
        }
        
        # Find the range that contains this VLAN ID
        for (start, end), description in vlan_ranges.items():
            if start <= vlan_id <= end:
                return {
                    'vlan_id': vlan_id,
                    'range': f"{start}-{end}",
                    'typical_usage': description
                }
                
        return {
            'vlan_id': vlan_id,
            'range': "unknown",
            'typical_usage': "Unknown purpose"
        }
