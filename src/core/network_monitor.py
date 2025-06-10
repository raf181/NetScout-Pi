#!/usr/bin/env python3
# NetProbe Pi - Network Monitor

import os
import sys
import threading
import time
import logging
import subprocess
import netifaces
import json
import datetime
from pathlib import Path
from pyroute2 import IPRoute
import fcntl
import struct
import socket

class NetworkMonitor:
    """Monitor network interfaces and trigger events on connectivity changes."""
    
    def __init__(self, config, plugin_manager):
        """Initialize network monitor.
        
        Args:
            config: Application configuration.
            plugin_manager: Plugin manager instance.
        """
        self.config = config
        self.plugin_manager = plugin_manager
        self.logger = logging.getLogger(__name__)
        
        # Get configured interfaces or auto-detect
        self.interface = config.get('network.interface', 'eth0')
        self.wifi_interface = config.get('network.wifi_interface', 'wlan0')
        
        # Verify interfaces exist, otherwise try to auto-detect
        if self.interface not in netifaces.interfaces():
            self.logger.warning(f"Interface {self.interface} not found")
            # Try to find a suitable interface
            available_interfaces = [iface for iface in netifaces.interfaces() 
                                    if iface != 'lo' and not iface.startswith(('wl', 'wlan', 'wifi'))]
            if available_interfaces:
                self.interface = available_interfaces[0]
                self.logger.info(f"Auto-selected interface: {self.interface}")
            else:
                self.logger.warning("No suitable network interfaces found")
        
        # Same for WiFi
        if self.wifi_interface not in netifaces.interfaces():
            # Try to find a suitable WiFi interface
            wifi_interfaces = [iface for iface in netifaces.interfaces() 
                               if iface.startswith(('wl', 'wlan', 'wifi'))]
            if wifi_interfaces:
                self.wifi_interface = wifi_interfaces[0]
                self.logger.info(f"Auto-selected WiFi interface: {self.wifi_interface}")
        
        self.poll_interval = config.get('network.poll_interval', 5, type_cast=int)
        self.auto_run = config.get('network.auto_run_on_connect', True)
        self.default_plugins = config.get('network.default_plugins', ['ip_info', 'ping_test'])
        self.monitor_method = config.get('network.monitor_method', 'poll')  # 'poll', 'netlink', or 'ifplugd'
        
        self.running = False
        self.monitor_thread = None
        self.last_state = False  # Interface state (True = up and connected)
        self.event_handlers = {}
        
        # Create log directory
        self.log_dir = config.get('logging.directory')
        if not self.log_dir:
            self.log_dir = os.path.join(Path(__file__).resolve().parent.parent.parent, 'logs', 'network')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Register default event handlers
        self.register_event_handler('eth_connect', self._handle_ethernet_connect)
        self.register_event_handler('eth_disconnect', self._handle_ethernet_disconnect)
    
    def start(self):
        """Start the network monitor."""
        if self.running:
            return
            
        self.running = True
        
        # Choose monitoring method
        if self.monitor_method == 'netlink':
            self.monitor_thread = threading.Thread(target=self._monitor_netlink)
        elif self.monitor_method == 'ifplugd':
            self.monitor_thread = threading.Thread(target=self._monitor_ifplugd)
        else:
            self.monitor_thread = threading.Thread(target=self._monitor_poll)
            
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        self.logger.info(f"Network monitor started with {self.monitor_method} method")
    
    def stop(self):
        """Stop the network monitor."""
        if not self.running:
            return
            
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
            
        self.logger.info("Network monitor stopped")
    
    def _monitor_poll(self):
        """Monitor network interface state by polling."""
        while self.running:
            try:
                # Check if interface exists
                if self.interface not in netifaces.interfaces():
                    self.logger.warning(f"Interface {self.interface} not found")
                    time.sleep(self.poll_interval)
                    continue
                
                # Check carrier state
                current_state = self._check_carrier(self.interface)
                
                # If state changed, trigger event
                if current_state != self.last_state:
                    if current_state:
                        self._trigger_event('eth_connect')
                    else:
                        self._trigger_event('eth_disconnect')
                        
                    self.last_state = current_state
                    
            except Exception as e:
                self.logger.error(f"Error in network monitor: {str(e)}")
                
            time.sleep(self.poll_interval)
    
    def _monitor_netlink(self):
        """Monitor network interface state using netlink."""
        try:
            # Initialize IPRoute
            ip = IPRoute()
            
            # Get initial state
            self.last_state = self._check_carrier(self.interface)
            
            # Register for link updates
            ip.bind()
            
            while self.running:
                # Receive netlink messages with timeout
                for message in ip.get():
                    if not self.running:
                        break
                        
                    # Filter for link messages for our interface
                    if (message.get('event') == 'RTM_NEWLINK' and
                        message.get('attrs') and
                        message.get('index')):
                            
                        # Find interface name in attributes
                        ifname = None
                        for attr in message.get('attrs', []):
                            if attr[0] == 'IFLA_IFNAME' and attr[1] == self.interface:
                                ifname = attr[1]
                                break
                        
                        if ifname:
                            # Check current state
                            current_state = self._check_carrier(self.interface)
                            
                            # If state changed, trigger event
                            if current_state != self.last_state:
                                if current_state:
                                    self._trigger_event('eth_connect')
                                else:
                                    self._trigger_event('eth_disconnect')
                                    
                                self.last_state = current_state
                
                time.sleep(0.1)  # Small sleep to prevent CPU overuse
                
        except Exception as e:
            self.logger.error(f"Error in netlink monitor: {str(e)}")
            # Fall back to polling method
            self._monitor_poll()
            
        finally:
            if 'ip' in locals():
                ip.close()
    
    def _monitor_ifplugd(self):
        """Monitor network interface state using ifplugd events."""
        try:
            # Check if ifplugd is installed
            subprocess.check_call(['which', 'ifplugd'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Configure ifplugd for our interface if not already running
            try:
                subprocess.check_call(['pgrep', '-f', f'ifplugd -i {self.interface}'], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                # ifplugd not running for this interface, start it
                self.logger.info(f"Starting ifplugd for interface {self.interface}")
                subprocess.Popen(['ifplugd', '-i', self.interface, '-f', '-u0', '-d0', 
                                 '-a', '-r', '/etc/ifplugd/netprobe.action'],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Create action script if it doesn't exist
                action_dir = '/etc/ifplugd'
                action_file = f'{action_dir}/netprobe.action'
                
                if not os.path.exists(action_dir):
                    os.makedirs(action_dir, exist_ok=True)
                    
                if not os.path.exists(action_file):
                    with open(action_file, 'w') as f:
                        f.write('#!/bin/sh\n\n')
                        f.write('# ifplugd action script for NetProbe\n\n')
                        f.write('INTERFACE="$1"\n')
                        f.write('ACTION="$2"\n\n')
                        f.write('if [ "$ACTION" = "up" ]; then\n')
                        f.write('    echo "Interface $INTERFACE is up" > /tmp/netprobe_eth_status\n')
                        f.write('elif [ "$ACTION" = "down" ]; then\n')
                        f.write('    echo "Interface $INTERFACE is down" > /tmp/netprobe_eth_status\n')
                        f.write('fi\n')
                    os.chmod(action_file, 0o755)
            
            # Get initial state
            self.last_state = self._check_carrier(self.interface)
            
            # Monitor the status file
            status_file = '/tmp/netprobe_eth_status'
            last_modified = 0
            
            while self.running:
                try:
                    # Check if status file exists and has been modified
                    if os.path.exists(status_file):
                        mod_time = os.path.getmtime(status_file)
                        
                        if mod_time > last_modified:
                            # Read status
                            with open(status_file, 'r') as f:
                                status = f.read().strip()
                                
                            # Update last modified time
                            last_modified = mod_time
                            
                            # Parse status and trigger events
                            current_state = 'up' in status.lower()
                            
                            if current_state != self.last_state:
                                if current_state:
                                    self._trigger_event('eth_connect')
                                else:
                                    self._trigger_event('eth_disconnect')
                                    
                                self.last_state = current_state
                    
                    # Also check carrier state directly as a fallback
                    current_state = self._check_carrier(self.interface)
                    if current_state != self.last_state:
                        if current_state:
                            self._trigger_event('eth_connect')
                        else:
                            self._trigger_event('eth_disconnect')
                            
                        self.last_state = current_state
                        
                except Exception as e:
                    self.logger.error(f"Error reading ifplugd status: {str(e)}")
                    
                time.sleep(self.poll_interval)
                
        except Exception as e:
            self.logger.error(f"Error in ifplugd monitor: {str(e)}")
            # Fall back to polling method
            self._monitor_poll()
    
    def _check_carrier(self, interface):
        """Check if interface has link carrier.
        
        Args:
            interface (str): Interface name.
            
        Returns:
            bool: True if interface has carrier, False otherwise.
        """
        try:
            # First check if the interface exists
            if interface not in netifaces.interfaces():
                self.logger.warning(f"Interface {interface} not found")
                return False
                
            # Check carrier state using sysfs
            carrier_file = f"/sys/class/net/{interface}/carrier"
            if os.path.exists(carrier_file):
                with open(carrier_file, 'r') as f:
                    carrier = f.read().strip()
                    return carrier == '1'
            
            # Fallback: check if interface has an IPv4 address
            addresses = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addresses:
                return True
                
            return False
        except Exception as e:
            self.logger.error(f"Error checking carrier for {interface}: {e}")
            return False
    
    def register_event_handler(self, event, handler):
        """Register an event handler.
        
        Args:
            event (str): Event name ('eth_connect' or 'eth_disconnect').
            handler (callable): Function to call when event occurs.
            
        Returns:
            bool: True if registered, False otherwise.
        """
        if event not in self.event_handlers:
            self.event_handlers[event] = []
            
        if handler not in self.event_handlers[event]:
            self.event_handlers[event].append(handler)
            return True
            
        return False
    
    def unregister_event_handler(self, event, handler):
        """Unregister an event handler.
        
        Args:
            event (str): Event name.
            handler (callable): Handler function.
            
        Returns:
            bool: True if unregistered, False otherwise.
        """
        if event in self.event_handlers and handler in self.event_handlers[event]:
            self.event_handlers[event].remove(handler)
            return True
            
        return False
    
    def _trigger_event(self, event):
        """Trigger an event and call all handlers.
        
        Args:
            event (str): Event name.
        """
        self.logger.info(f"Network event triggered: {event}")
        
        # Log the event
        self._log_event(event)
        
        # Call handlers
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(f"Error in event handler: {str(e)}")
    
    def get_interface_status(self, interface=None):
        """Get status of a network interface.
        
        Args:
            interface (str, optional): Interface name. Defaults to monitored interface.
            
        Returns:
            dict: Interface status.
        """
        interface = interface or self.interface
        
        status = {
            'interface': interface,
            'exists': interface in netifaces.interfaces(),
            'up': False,
            'carrier': False,
            'addresses': {},
            'error': None
        }
        
        try:
            # Check if interface exists and is up
            if status['exists']:
                # Get interface flags
                with open(f'/sys/class/net/{interface}/flags', 'r') as f:
                    flags = int(f.read().strip(), 16)
                    status['up'] = bool(flags & 1)  # IFF_UP flag
                
                # Check carrier state
                status['carrier'] = self._check_carrier(interface)
                
                # Get IP addresses
                addresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addresses:
                    status['addresses']['ipv4'] = addresses[netifaces.AF_INET][0]
                if netifaces.AF_INET6 in addresses:
                    status['addresses']['ipv6'] = addresses[netifaces.AF_INET6][0]
                
                # Get MAC address
                if netifaces.AF_LINK in addresses:
                    status['addresses']['mac'] = addresses[netifaces.AF_LINK][0]['addr']
                
                # Get gateway
                gateways = netifaces.gateways()
                if 'default' in gateways and netifaces.AF_INET in gateways['default']:
                    status['gateway'] = gateways['default'][netifaces.AF_INET][0]
                
                # Get DNS servers
                try:
                    with open('/etc/resolv.conf', 'r') as f:
                        status['dns_servers'] = [l.split()[1] for l in f if l.startswith('nameserver')]
                except:
                    status['dns_servers'] = []
                    
        except Exception as e:
            status['error'] = str(e)
            self.logger.error(f"Error getting interface status: {e}")
            
        return status
        
    def get_recent_events(self, limit=100):
        """Get recent network events.
        
        Args:
            limit (int, optional): Maximum number of events to return.
            
        Returns:
            list: List of recent events.
        """
        try:
            events = []
            log_file = os.path.join(self.log_dir, 'events.log')
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    events = [json.loads(line) for line in f.readlines()[-limit:]]
                    
            return events
        except Exception as e:
            self.logger.error(f"Error getting recent events: {e}")
            return []
    
    def _log_event(self, event):
        """Log a network event.
        
        Args:
            event (str): Event name.
        """
        try:
            log_file = os.path.join(self.log_dir, 'events.log')
            
            event_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'event': event,
                'interface': self.interface,
                'status': self.get_interface_status()
            }
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(event_data) + '\n')
                
        except Exception as e:
            self.logger.error(f"Error logging event: {e}")
    
    def set_auto_run(self, enabled, plugins=None):
        """Set auto-run settings.
        
        Args:
            enabled (bool): Whether to auto-run plugins on connect.
            plugins (list, optional): List of plugins to run. Defaults to current settings.
            
        Returns:
            bool: True if settings were updated, False otherwise.
        """
        try:
            self.auto_run = enabled
            if plugins is not None:
                self.default_plugins = plugins
            
            # Save to config
            self.config.set('network.auto_run_on_connect', enabled)
            if plugins is not None:
                self.config.set('network.default_plugins', plugins)
                
            return True
        except Exception as e:
            self.logger.error(f"Error setting auto-run: {e}")
            return False
    
    def _handle_ethernet_connect(self, event):
        """Handle Ethernet connect event.
        
        Args:
            event (str): Event name.
        """
        self.logger.info(f"Ethernet connected: {self.interface}")
        
        # Run default plugins if auto_run is enabled
        if self.auto_run and self.default_plugins:
            self.logger.info(f"Auto-running plugins: {self.default_plugins}")
            
            # Run plugins in sequence
            self.plugin_manager.run_sequence(self.default_plugins, sequential=True)
    
    def _handle_ethernet_disconnect(self, event):
        """Handle Ethernet disconnect event.
        
        Args:
            event (str): Event name.
        """
        self.logger.info(f"Ethernet disconnected: {self.interface}")
