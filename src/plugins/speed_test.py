#!/usr/bin/env python3
# NetProbe Pi - Speed Test Plugin

import os
import sys
import json
import time
import subprocess
import statistics
from pathlib import Path

# Add the src directory to the path
base_dir = Path(__file__).resolve().parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

from src.core.plugin_manager import PluginBase

class SpeedTestPlugin(PluginBase):
    """Plugin to measure internet connection speed using speedtest-cli."""
    
    name = "speed_test"
    description = "Measure internet connection speed"
    version = "0.1.0"
    author = "NetProbe"
    permissions = []
    
    def run(self, server=None, runs=None, **kwargs):
        """Run the plugin.
        
        Args:
            server (int, optional): Speedtest.net server ID to test against. Defaults to None (auto).
            runs (int, optional): Number of test runs to perform. Defaults to 1.
            **kwargs: Additional arguments.
            
        Returns:
            dict: Speed test results.
        """
        server = server or self.config.get('server')
        runs = int(kwargs.get('runs') or runs or self.config.get('runs') or 1)
        
        self.logger.info(f"Starting speed test with {runs} run(s)")
        
        result = {
            'timestamp': self.logger.get_timestamp(),
            'runs': runs,
            'server': server,
            'results': [],
            'average': {},
            'error': None
        }
        
        try:
            for i in range(runs):
                self.logger.info(f"Speed test run {i+1}/{runs}")
                run_result = self._run_speed_test(server)
                if run_result:
                    result['results'].append(run_result)
                    
            # Calculate averages if we have results
            if result['results']:
                download_speeds = [r['download'] for r in result['results'] if 'download' in r]
                upload_speeds = [r['upload'] for r in result['results'] if 'upload' in r]
                ping_values = [r['ping'] for r in result['results'] if 'ping' in r]
                
                if download_speeds:
                    result['average']['download'] = sum(download_speeds) / len(download_speeds)
                if upload_speeds:
                    result['average']['upload'] = sum(upload_speeds) / len(upload_speeds)
                if ping_values:
                    result['average']['ping'] = sum(ping_values) / len(ping_values)
                    
                # Add more statistics for multiple runs
                if runs > 1:
                    result['stats'] = {
                        'download': {
                            'min': min(download_speeds) if download_speeds else None,
                            'max': max(download_speeds) if download_speeds else None,
                            'stddev': statistics.stdev(download_speeds) if len(download_speeds) > 1 else 0
                        },
                        'upload': {
                            'min': min(upload_speeds) if upload_speeds else None,
                            'max': max(upload_speeds) if upload_speeds else None,
                            'stddev': statistics.stdev(upload_speeds) if len(upload_speeds) > 1 else 0
                        },
                        'ping': {
                            'min': min(ping_values) if ping_values else None,
                            'max': max(ping_values) if ping_values else None,
                            'stddev': statistics.stdev(ping_values) if len(ping_values) > 1 else 0
                        }
                    }
                
                # Add the best server info from the last run
                if 'server_info' in result['results'][-1]:
                    result['server_info'] = result['results'][-1]['server_info']
                
                self.logger.info(f"Speed test completed. Avg download: {result['average'].get('download', 0):.2f} Mbps, " +
                               f"Avg upload: {result['average'].get('upload', 0):.2f} Mbps, " +
                               f"Avg ping: {result['average'].get('ping', 0):.2f} ms")
            else:
                result['error'] = "No successful speed test runs"
                
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error during speed test: {str(e)}")
            
        return result
    
    def _run_speed_test(self, server=None):
        """Run a single speed test and return the results."""
        try:
            # Build command
            cmd = ['speedtest', '--json']
            if server:
                cmd.extend(['--server', str(server)])
                
            # Execute speedtest command
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            output = subprocess.check_output(cmd, stderr=subprocess.PIPE, text=True)
            
            # Parse JSON output
            data = json.loads(output)
            
            # Extract relevant information
            result = {
                'download': data['download'] / 1000000,  # Convert to Mbps
                'upload': data['upload'] / 1000000,      # Convert to Mbps
                'ping': data['ping'],
                'timestamp': time.time(),
                'bytes_sent': data.get('bytes_sent'),
                'bytes_received': data.get('bytes_received')
            }
            
            # Extract server information
            if 'server' in data:
                result['server_info'] = {
                    'id': data['server'].get('id'),
                    'name': data['server'].get('name'),
                    'location': data['server'].get('location'),
                    'country': data['server'].get('country'),
                    'host': data['server'].get('host'),
                    'distance': data['server'].get('d')
                }
                
            # Extract client information
            if 'client' in data:
                result['client_info'] = {
                    'ip': data['client'].get('ip'),
                    'isp': data['client'].get('isp'),
                    'location': f"{data['client'].get('city', '')}, {data['client'].get('country', '')}",
                    'lat': data['client'].get('lat'),
                    'lon': data['client'].get('lon')
                }
                
            return result
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Speedtest command failed: {e.stderr}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse speedtest output: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error during speed test: {str(e)}")
            return None
