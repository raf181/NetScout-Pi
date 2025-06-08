#!/usr/bin/env python3
# NetProbe Pi - Traceroute Plugin

import os
import sys
import subprocess
import re
import socket
import time
import concurrent.futures
import platform
import ipaddress
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class TraceroutePlugin(PluginBase):
    """Plugin to perform traceroute to various targets."""
    
    name = "traceroute"
    description = "Traceroute to various targets"
    version = "0.1.0"
    author = "NetProbe"
    permissions = []
    
    DEFAULT_TARGETS = ['1.1.1.1', '8.8.8.8', 'google.com']
    
    def run(self, targets=None, max_hops=None, timeout=None, interface=None, parallel=True, **kwargs):
        """Run the plugin.
        
        Args:
            targets (list, optional): List of targets to trace. Defaults to config value.
            max_hops (int, optional): Maximum number of hops. Defaults to config value.
            timeout (int, optional): Timeout in seconds. Defaults to config value.
            interface (str, optional): Network interface to use. Defaults to eth0.
            parallel (bool, optional): Whether to trace targets in parallel. Defaults to True.
            **kwargs: Additional arguments.
            
        Returns:
            dict: Traceroute results.
        """
        # Get parameters from config if not specified
        targets = targets or self.config.get('targets') or self.DEFAULT_TARGETS
        max_hops = int(kwargs.get('max_hops') or max_hops or self.config.get('max_hops') or 30)
        timeout = int(kwargs.get('timeout') or timeout or self.config.get('timeout') or 2)
        interface = interface or self.config.get('interface') or 'eth0'
        parallel = kwargs.get('parallel', parallel)
        
        # Make sure targets is a list
        if isinstance(targets, str):
            targets = [targets]
            
        self.logger.info(f"Starting traceroute with targets: {targets}")
        
        result = {
            'timestamp': self.logger.get_timestamp(),
            'interface': interface,
            'targets': targets,
            'max_hops': max_hops,
            'timeout': timeout,
            'results': [],
            'error': None
        }
        
        try:
            # Trace targets in parallel or sequentially
            if parallel:
                result['results'] = self._trace_parallel(targets, max_hops, timeout, interface)
            else:
                result['results'] = []
                for target in targets:
                    trace_result = self._trace(target, max_hops, timeout, interface)
                    result['results'].append(trace_result)
                    
            # Process the results for additional insights
            for trace_result in result['results']:
                if trace_result['success']:
                    # Calculate RTT statistics
                    rtts = [hop['rtt'] for hop in trace_result['hops'] 
                           if hop['rtt'] is not None and hop['rtt'] > 0]
                    if rtts:
                        trace_result['rtt_stats'] = {
                            'min': min(rtts),
                            'max': max(rtts),
                            'avg': sum(rtts) / len(rtts)
                        }
                    
                    # Analyze for common network issues
                    self._analyze_trace(trace_result)
            
            # Calculate overall statistics
            success_count = sum(1 for r in result['results'] if r['success'])
            result['success_rate'] = (success_count / len(targets)) * 100 if targets else 0
            
            self.logger.info(f"Traceroute completed with {success_count}/{len(targets)} successful targets")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error during traceroute: {str(e)}")
            
        return result
    
    def _trace(self, target, max_hops, timeout, interface=None):
        """Trace a single target and parse results."""
        start_time = time.time()
        result = {
            'target': target,
            'success': False,
            'error': None,
            'raw_output': '',
            'hops': [],
            'hop_count': 0,
            'issues': []
        }
        
        try:
            # Resolve hostname to IP if possible
            try:
                ip = socket.gethostbyname(target)
                result['ip'] = ip
                result['hostname'] = target if target != ip else None
            except socket.gaierror:
                result['ip'] = None
                result['hostname'] = None
                
            # Determine the command based on the platform
            if platform.system().lower() == 'windows':
                cmd = ['tracert', '-d', '-h', str(max_hops), '-w', str(timeout * 1000)]
            else:  # Linux, macOS, etc.
                cmd = ['traceroute', '-n', '-m', str(max_hops), '-w', str(timeout)]
                if interface:
                    cmd.extend(['-i', interface])
                    
            # Add target
            cmd.append(target)
            
            # Execute traceroute command
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Collect output in real-time
            stdout, stderr = process.communicate()
            
            result['raw_output'] = stdout
            if stderr:
                result['error'] = stderr.strip()
            
            # Parse traceroute output
            if platform.system().lower() == 'windows':
                result.update(self._parse_windows_traceroute(stdout))
            else:
                result.update(self._parse_linux_traceroute(stdout))
                
            # Mark as successful if we have hops
            result['success'] = len(result['hops']) > 0
            result['hop_count'] = len(result['hops'])
            
            # Determine if destination was reached
            if result['hops'] and 'destination_reached' not in result:
                last_hop = result['hops'][-1]
                result['destination_reached'] = (
                    last_hop.get('ip') == result.get('ip') or
                    '*' not in last_hop.get('ip', '')
                )
                
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error tracing {target}: {str(e)}")
            
        result['duration'] = time.time() - start_time
        return result
    
    def _trace_parallel(self, targets, max_hops, timeout, interface=None):
        """Trace multiple targets in parallel."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(targets), 5)) as executor:
            # Create tasks
            future_to_target = {
                executor.submit(self._trace, target, max_hops, timeout, interface): target
                for target in targets
            }
            
            # Collect results
            results = []
            for future in concurrent.futures.as_completed(future_to_target):
                results.append(future.result())
                
        # Sort results to match original target order
        target_to_idx = {target: i for i, target in enumerate(targets)}
        results.sort(key=lambda r: target_to_idx.get(r['target'], 9999))
        
        return results
    
    def _parse_windows_traceroute(self, output):
        """Parse Windows tracert output."""
        result = {
            'hops': []
        }
        
        if not output:
            return result
            
        # Windows tracert output format:
        # Tracing route to google.com [216.58.201.238]
        # over a maximum of 30 hops:
        #
        #   1     1 ms     1 ms     1 ms  192.168.1.1
        #   2    15 ms    14 ms    14 ms  10.0.0.1
        #   3     *        *        *     Request timed out.
        
        hop_pattern = r'^\s*(\d+)\s+(?:(<?\d+)\s*ms\s+)?(?:(<?\d+)\s*ms\s+)?(?:(<?\d+)\s*ms\s+)?(.+)$'
        
        for line in output.splitlines():
            match = re.match(hop_pattern, line)
            if match:
                hop_num = int(match.group(1))
                rtts = [float(x) if x else None for x in [match.group(2), match.group(3), match.group(4)]]
                rtts = [x for x in rtts if x is not None]
                
                target_info = match.group(5).strip()
                
                # Parse IP address if present
                ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', target_info)
                ip = ip_match.group(1) if ip_match else None
                
                # Check if this is a timeout
                is_timeout = "Request timed out" in target_info or "*" in target_info
                
                hop = {
                    'hop': hop_num,
                    'ip': ip or ('*' if is_timeout else target_info),
                    'rtts': rtts,
                    'rtt': sum(rtts) / len(rtts) if rtts else None,
                    'timeout': is_timeout,
                    'hostname': None if is_timeout or ip is None else target_info.replace(ip, '').strip() or None
                }
                
                result['hops'].append(hop)
                
        return result
    
    def _parse_linux_traceroute(self, output):
        """Parse Linux/macOS traceroute output."""
        result = {
            'hops': []
        }
        
        if not output:
            return result
            
        # Linux traceroute output format:
        # traceroute to google.com (216.58.201.238), 30 hops max, 60 byte packets
        #  1  192.168.1.1  1.123 ms  1.456 ms  1.789 ms
        #  2  10.0.0.1  15.123 ms  14.456 ms  14.789 ms
        #  3  * * *
        
        hop_pattern = r'^\s*(\d+)(?:\s+(.+?))?(?:\s+(\d+\.\d+)\s*ms)?(?:\s+(\d+\.\d+)\s*ms)?(?:\s+(\d+\.\d+)\s*ms)?'
        
        for line in output.splitlines()[1:]:  # Skip the header line
            match = re.match(hop_pattern, line)
            if match:
                hop_num = int(match.group(1))
                target_info = match.group(2).strip() if match.group(2) else None
                rtts = [float(x) for x in [match.group(3), match.group(4), match.group(5)] if x]
                
                # Check if this is a timeout
                is_timeout = target_info is None or target_info == '*'
                
                # Parse IP address if present
                ip = None
                hostname = None
                
                if not is_timeout:
                    # If using -n flag, target_info should be just the IP
                    ip = target_info
                    
                    # Try to extract IP and hostname if both are present
                    ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', target_info)
                    if ip_match:
                        ip = ip_match.group(1)
                        hostname_part = target_info.replace(ip, '').strip()
                        if hostname_part and hostname_part != '(' and hostname_part != ')':
                            hostname = hostname_part.strip('()')
                
                hop = {
                    'hop': hop_num,
                    'ip': ip or '*',
                    'rtts': rtts,
                    'rtt': sum(rtts) / len(rtts) if rtts else None,
                    'timeout': is_timeout,
                    'hostname': hostname
                }
                
                result['hops'].append(hop)
                
        return result
    
    def _analyze_trace(self, trace_result):
        """Analyze traceroute results for common network issues."""
        issues = []
        hops = trace_result['hops']
        
        if not hops:
            return
            
        # Check for timeouts at the beginning (indicates local network issues)
        if hops[0]['timeout']:
            issues.append({
                'type': 'local_network',
                'description': 'Could not reach first hop, suggests local network issues',
                'severity': 'high'
            })
            
        # Check for multiple consecutive timeouts (black holes)
        timeout_sequences = []
        current_seq = []
        
        for i, hop in enumerate(hops):
            if hop['timeout']:
                current_seq.append(i)
            elif current_seq:
                if len(current_seq) >= 3:  # 3 or more consecutive timeouts
                    timeout_sequences.append(current_seq)
                current_seq = []
                
        # Add the last sequence if it exists
        if current_seq and len(current_seq) >= 3:
            timeout_sequences.append(current_seq)
            
        # Report black holes
        for seq in timeout_sequences:
            issues.append({
                'type': 'black_hole',
                'description': f'Network black hole detected between hops {hops[seq[0]-1]["hop"] if seq[0] > 0 else "unknown"} and {hops[seq[-1]+1]["hop"] if seq[-1] < len(hops)-1 else "destination"}',
                'severity': 'medium',
                'hops': seq
            })
            
        # Check for high latency jumps
        prev_rtt = None
        for i, hop in enumerate(hops):
            if hop['rtt'] is not None and prev_rtt is not None:
                # If latency increases by more than 30ms between hops
                if hop['rtt'] - prev_rtt > 30:
                    issues.append({
                        'type': 'latency_jump',
                        'description': f'Large latency increase of {hop["rtt"] - prev_rtt:.1f}ms between hops {i} and {i+1}',
                        'severity': 'low',
                        'hops': [i, i+1],
                        'latency_increase': hop['rtt'] - prev_rtt
                    })
            if hop['rtt'] is not None:
                prev_rtt = hop['rtt']
                
        # Check for routing loops
        ip_to_hops = {}
        for i, hop in enumerate(hops):
            if not hop['timeout'] and hop['ip'] != '*':
                if hop['ip'] in ip_to_hops:
                    issues.append({
                        'type': 'routing_loop',
                        'description': f'Routing loop detected: {hop["ip"]} appears at hops {ip_to_hops[hop["ip"]]+1} and {i+1}',
                        'severity': 'medium',
                        'hops': [ip_to_hops[hop['ip']], i]
                    })
                else:
                    ip_to_hops[hop['ip']] = i
                    
        # Check for destination not reached
        if not trace_result.get('destination_reached', False) and len(hops) > 0 and len(hops) >= trace_result.get('max_hops', 30) - 1:
            issues.append({
                'type': 'destination_unreached',
                'description': 'Destination not reached within maximum hop count',
                'severity': 'medium'
            })
            
        # Add issues to the result
        trace_result['issues'] = issues
