#!/usr/bin/env python3
# NetProbe Pi - Ping Test Plugin

import os
import sys
import subprocess
import re
import socket
import time
import statistics
import concurrent.futures
import platform
import netifaces
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class PingTestPlugin(PluginBase):
    """Plugin to perform ping tests to various targets."""
    
    name = "ping_test"
    description = "Ping test to various targets"
    version = "0.1.0"
    author = "NetProbe"
    permissions = []
    
    DEFAULT_TARGETS = ['1.1.1.1', '8.8.8.8', 'google.com']
    
    def run(self, targets=None, count=None, timeout=None, interval=None, interface=None, parallel=True, **kwargs):
        """Run the plugin.
        
        Args:
            targets (list, optional): List of targets to ping. Defaults to config value.
            count (int, optional): Number of pings to perform. Defaults to config value.
            timeout (int, optional): Timeout in seconds. Defaults to config value.
            interval (float, optional): Interval between pings in seconds. Defaults to config value.
            interface (str, optional): Network interface to use. Defaults to eth0.
            parallel (bool, optional): Whether to ping targets in parallel. Defaults to True.
            **kwargs: Additional arguments.
            
        Returns:
            dict: Ping test results.
        """
        # Get parameters from config if not specified
        targets = targets or self.config.get('targets') or self.DEFAULT_TARGETS
        count = int(kwargs.get('count') or count or self.config.get('count') or 4)
        timeout = int(kwargs.get('timeout') or timeout or self.config.get('timeout') or 2)
        interval = float(kwargs.get('interval') or interval or self.config.get('interval') or 0.2)
        interface = interface or self.config.get('interface') or 'eth0'
        parallel = kwargs.get('parallel', parallel)
        
        # Make sure targets is a list
        if isinstance(targets, str):
            targets = [targets]
            
        self.logger.info(f"Starting ping test with targets: {targets}")
        
        result = {
            'timestamp': self.logger.get_timestamp(),
            'interface': interface,
            'targets': targets,
            'count': count,
            'timeout': timeout,
            'interval': interval,
            'results': [],
            'error': None
        }
        
        try:
            # Check if interface exists
            if interface not in self._get_interfaces():
                self.logger.warning(f"Interface {interface} not found, using default")
                interface = None
            
            # Get gateway IP for checking local connectivity
            gateway = self._get_gateway()
            if gateway and gateway not in targets:
                targets.insert(0, gateway)
                result['targets'] = targets
                self.logger.info(f"Added gateway {gateway} to ping targets")
            
            # Ping targets in parallel or sequentially
            if parallel:
                result['results'] = self._ping_parallel(targets, count, timeout, interval, interface)
            else:
                result['results'] = []
                for target in targets:
                    ping_result = self._ping(target, count, timeout, interval, interface)
                    result['results'].append(ping_result)
                    
            # Calculate overall statistics
            success_count = sum(1 for r in result['results'] if r['success'])
            result['success_rate'] = (success_count / len(targets)) * 100 if targets else 0
            
            # Add summary statistics
            successful_pings = [r for r in result['results'] if r['success']]
            if successful_pings:
                avg_times = [r['stats']['avg'] for r in successful_pings if r['stats']['avg'] is not None]
                if avg_times:
                    result['avg_time'] = sum(avg_times) / len(avg_times)
                
            # Determine overall connectivity status
            if result['success_rate'] == 100:
                result['status'] = 'excellent'
            elif result['success_rate'] >= 75:
                result['status'] = 'good'
            elif result['success_rate'] >= 25:
                result['status'] = 'poor'
            else:
                result['status'] = 'critical'
                
            self.logger.info(f"Ping test completed with {success_count}/{len(targets)} successful targets")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error during ping test: {str(e)}")
            
        return result
    
    def _get_interfaces(self):
        """Get available network interfaces."""
        try:
            return netifaces.interfaces()
        except Exception:
            return []
    
    def _get_gateway(self):
        """Get default gateway IP."""
        try:
            gateways = netifaces.gateways()
            if 'default' in gateways and netifaces.AF_INET in gateways['default']:
                return gateways['default'][netifaces.AF_INET][0]
        except Exception:
            pass
        return None
    
    def _ping(self, target, count, timeout, interval, interface=None):
        """Ping a single target and parse results."""
        start_time = time.time()
        result = {
            'target': target,
            'success': False,
            'packets_sent': 0,
            'packets_received': 0,
            'packet_loss': 100.0,
            'error': None,
            'raw_output': '',
            'stats': {
                'min': None,
                'avg': None,
                'max': None,
                'mdev': None
            },
            'times': []
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
            
            # Build ping command
            cmd = ['ping']
            
            # Add platform-specific options
            if platform.system().lower() == 'windows':
                cmd.extend(['-n', str(count), '-w', str(timeout * 1000)])
            else:  # Linux, macOS, etc.
                cmd.extend(['-c', str(count), '-W', str(timeout)])
                if interval:
                    cmd.extend(['-i', str(interval)])
                if interface:
                    cmd.extend(['-I', interface])
            
            # Add target
            cmd.append(target)
            
            # Execute ping command
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
            
            # Parse ping output
            result.update(self._parse_ping_output(stdout))
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error pinging {target}: {str(e)}")
            
        result['duration'] = time.time() - start_time
        return result
    
    def _ping_parallel(self, targets, count, timeout, interval, interface=None):
        """Ping multiple targets in parallel."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(targets), 10)) as executor:
            # Create tasks
            future_to_target = {
                executor.submit(self._ping, target, count, timeout, interval, interface): target
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
    
    def _parse_ping_output(self, output):
        """Parse ping command output."""
        result = {
            'success': False,
            'packets_sent': 0,
            'packets_received': 0,
            'packet_loss': 100.0,
            'stats': {
                'min': None,
                'avg': None,
                'max': None,
                'mdev': None
            },
            'times': []
        }
        
        if not output:
            return result
        
        # Extract times from ping output
        time_pattern = r'time=(\d+\.?\d*) ms'
        times = re.findall(time_pattern, output)
        result['times'] = [float(t) for t in times]
        
        # Calculate statistics if we have times
        if result['times']:
            result['success'] = True
            result['stats']['min'] = min(result['times'])
            result['stats']['max'] = max(result['times'])
            result['stats']['avg'] = statistics.mean(result['times'])
            if len(result['times']) > 1:
                result['stats']['mdev'] = statistics.stdev(result['times'])
        
        # Extract packet statistics
        if platform.system().lower() == 'windows':
            # Windows ping output
            packets_pattern = r'Sent = (\d+), Received = (\d+), Lost = (\d+)'
            match = re.search(packets_pattern, output)
            if match:
                result['packets_sent'] = int(match.group(1))
                result['packets_received'] = int(match.group(2))
                result['packet_loss'] = (int(match.group(3)) / int(match.group(1))) * 100
        else:
            # Linux/macOS ping output
            packets_pattern = r'(\d+) packets transmitted, (\d+) received, (\d+\.?\d*)% packet loss'
            match = re.search(packets_pattern, output)
            if match:
                result['packets_sent'] = int(match.group(1))
                result['packets_received'] = int(match.group(2))
                result['packet_loss'] = float(match.group(3))
        
        return result
