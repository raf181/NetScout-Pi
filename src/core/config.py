#!/usr/bin/env python3
# NetProbe Pi - Configuration Manager

import os
import yaml
import logging
from pathlib import Path

class Config:
    """Configuration manager for NetProbe Pi."""
    
    DEFAULT_CONFIG = {
        'system': {
            'log_dir': '/var/log/netprobe',
            'data_dir': '/var/lib/netprobe',
            'plugin_dir': '/etc/netprobe/plugins',
            'log_level': 'INFO',
            'debug': False
        },
        'network': {
            'interface': 'eth0',
            'wifi_interface': 'wlan0',
            'auto_run_on_connect': True,
            'default_plugins': ['ip_info', 'ping_test'],
            'poll_interval': 5  # seconds
        },
        'web': {
            'host': '0.0.0.0',
            'port': 80,
            'auth_required': True,
            'session_timeout': 3600,  # 1 hour
            'cookie_secure': True,
            'log_requests': True
        },
        'security': {
            'password_hash': None,  # Will be set on first run
            'allow_eth0_access': False,
            'jwt_secret': None,  # Will be set on first run
            'rate_limit': 60  # requests per minute
        },
        'plugins': {
            'ip_info': {
                'enabled': True,
                'targets': ['gateway', '8.8.8.8', '1.1.1.1']
            },
            'ping_test': {
                'enabled': True,
                'count': 4,
                'targets': ['gateway', '8.8.8.8', '1.1.1.1']
            },
            'traceroute': {
                'enabled': True,
                'targets': ['8.8.8.8', '1.1.1.1']
            },
            'arp_scan': {
                'enabled': True
            },
            'speedtest': {
                'enabled': True,
                'server': None  # Auto-select
            },
            'port_scan': {
                'enabled': True,
                'targets': ['gateway'],
                'ports': 'common'
            },
            'packet_capture': {
                'enabled': True,
                'count': 100,
                'filter': ''
            },
            'vlan_detector': {
                'enabled': True
            }
        }
    }
    
    def __init__(self, config_path=None):
        """Initialize configuration manager.
        
        Args:
            config_path (str, optional): Path to configuration file. Defaults to None.
                If None, uses default configuration.
        """
        self.logger = logging.getLogger(__name__)
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_path:
            self.config_path = Path(config_path)
            self._load_config()
        else:
            self.config_path = None
            self.logger.warning("No configuration file specified, using default configuration")
    
    def _load_config(self):
        """Load configuration from file."""
        if not self.config_path.exists():
            self.logger.warning(f"Configuration file {self.config_path} does not exist, using default configuration")
            return
        
        try:
            with open(self.config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    self._merge_config(self.config, user_config)
                    self.logger.debug(f"Configuration loaded from {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load configuration from {self.config_path}: {e}")
            raise
    
    def _merge_config(self, default_config, user_config):
        """Recursively merge user config into default config."""
        for key, value in user_config.items():
            if key in default_config and isinstance(default_config[key], dict) and isinstance(value, dict):
                self._merge_config(default_config[key], value)
            else:
                default_config[key] = value
    
    def get(self, key_path, default=None):
        """Get configuration value by dot-separated path.
        
        Args:
            key_path (str): Dot-separated path to configuration value.
            default: Default value to return if key doesn't exist.
            
        Returns:
            Configuration value or default.
        """
        keys = key_path.split('.')
        config = self.config
        
        for key in keys:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                return default
        
        return config
    
    def set(self, key_path, value):
        """Set configuration value by dot-separated path.
        
        Args:
            key_path (str): Dot-separated path to configuration value.
            value: Value to set.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        keys = key_path.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if isinstance(config, dict):
                if key not in config:
                    config[key] = {}
                config = config[key]
            else:
                return False
        
        # Set the value
        if isinstance(config, dict):
            config[keys[-1]] = value
            self._save_config()
            return True
        
        return False
    
    def _save_config(self):
        """Save configuration to file."""
        if not self.config_path:
            self.logger.warning("No configuration file specified, configuration not saved")
            return
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
                self.logger.debug(f"Configuration saved to {self.config_path}")
        except Exception as e:
            self.logger.error(f"Failed to save configuration to {self.config_path}: {e}")
            raise
