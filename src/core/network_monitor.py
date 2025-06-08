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
        
        self.interface = config.get('network.interface', 'eth0')
        self.poll_interval = config.get('network.poll_interval', 5)
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
            # Check carrier state from sysfs
            carrier_file = f"/sys/class/net/{interface}/carrier"
            
            if os.path.exists(carrier_file):
                with open(carrier_file, 'r') as f:
                    return f.read().strip() == '1'
            
            # Fallback: check with ip link
            output = subprocess.check_output(['ip', 'link', 'show', interface], text=True)
            return 'NO-CARRIER' not in output
            
        except Exception as e:
            self.logger.error(f"Error checking carrier: {str(e)}")
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
    
    def _log_event(self, event):
        """Log a network event.
        
        Args:
            event (str): Event name.
        """
        try:
            timestamp = datetime.datetime.now().isoformat()
            log_file = os.path.join(self.log_dir, 'events.log')
            
            with open(log_file, 'a') as f:
                f.write(f"{timestamp} {event}\n")
                
            # Also log as JSON for easier parsing
            json_log = os.path.join(self.log_dir, 'events.json')
            
            # Read existing log if it exists
            events = []
            if os.path.exists(json_log):
                try:
                    with open(json_log, 'r') as f:
                        events = json.load(f)
                except Exception:
                    # If file is corrupted, start fresh
                    events = []
            
            # Add new event
            events.append({
                'timestamp': timestamp,
                'event': event,
                'interface': self.interface
            })
            
            # Limit number of events (keep last 1000)
            if len(events) > 1000:
                events = events[-1000:]
                
            # Write updated log
            with open(json_log, 'w') as f:
                json.dump(events, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error logging event: {str(e)}")
    
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
            if not status['exists']:
                status['error'] = f"Interface {interface} not found"
                return status
                
            # Check if interface is up
            with open(f"/sys/class/net/{interface}/operstate", 'r') as f:
                state = f.read().strip()
                status['up'] = state.lower() == 'up'
                
            # Check carrier
            status['carrier'] = self._check_carrier(interface)
            
            # Get addresses
            try:
                addrs = netifaces.ifaddresses(interface)
                
                # IPv4
                if netifaces.AF_INET in addrs:
                    status['addresses']['ipv4'] = addrs[netifaces.AF_INET]
                    
                # IPv6
                if netifaces.AF_INET6 in addrs:
                    status['addresses']['ipv6'] = addrs[netifaces.AF_INET6]
                    
                # MAC
                if netifaces.AF_LINK in addrs:
                    status['addresses']['mac'] = addrs[netifaces.AF_LINK]
            except Exception as e:
                status['error'] = f"Error getting addresses: {str(e)}"
                
        except Exception as e:
            status['error'] = str(e)
            
        return status
    
    def get_recent_events(self, limit=100):
        """Get recent network events.
        
        Args:
            limit (int, optional): Maximum number of events to return.
            
        Returns:
            list: List of recent events.
        """
        try:
            json_log = os.path.join(self.log_dir, 'events.json')
            
            if not os.path.exists(json_log):
                return []
                
            with open(json_log, 'r') as f:
                events = json.load(f)
                
            # Return last N events
            return events[-limit:] if limit else events
            
        except Exception as e:
            self.logger.error(f"Error getting recent events: {str(e)}")
            return []
    
    def set_auto_run(self, enabled, plugins=None):
        """Set auto-run settings.
        
        Args:
            enabled (bool): Whether to auto-run plugins on connect.
            plugins (list, optional): List of plugins to run. Defaults to current settings.
            
        Returns:
            bool: True if settings were updated, False otherwise.
        """
        try:
            self.auto_run = bool(enabled)
            
            if plugins is not None:
                self.default_plugins = plugins
                
            # Update configuration
            self.config.set('network.auto_run_on_connect', self.auto_run)
            if plugins is not None:
                self.config.set('network.default_plugins', self.default_plugins)
                
            self.logger.info(f"Auto-run settings updated: enabled={self.auto_run}, plugins={self.default_plugins}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating auto-run settings: {str(e)}")
            return False
