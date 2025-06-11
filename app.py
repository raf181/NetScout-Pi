#!/usr/bin/env python3
# NetProbe Pi - Main Application Entry Point

import os
import sys
import logging
import argparse
import signal
import json
import time
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Add src directory to path
base_dir = Path(__file__).resolve().parent
if str(base_dir) not in sys.path:
    sys.path.append(str(base_dir))

# Import core modules
try:
    from src.core.config import Config
    from src.core.plugin_manager import PluginManager
    from src.core.new_plugin_manager import NewPluginManager
    from src.core.network_monitor import NetworkMonitor
    from src.core.logger import setup_logging
    from src.web.app import create_app as create_web_app
except Exception as e:
    print(f"Failed to import core modules: {str(e)}")
    sys.exit(1)

# Configure logging
logger = logging.getLogger(__name__)

def init_logging():
    """Initialize logging system."""
    try:
        # Set up logging configuration
        setup_logging()
        logger.info("Logging system initialized")
    except Exception as e:
        print(f"Failed to initialize logging: {str(e)}")
        sys.exit(1)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='NetProbe Pi - Network Diagnostics System')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', type=str, default='config/config.yaml', 
                        help='Path to configuration file')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Set logging level')
    parser.add_argument('--no-web', action='store_true', help='Do not start the web interface')
    parser.add_argument('--no-monitor', action='store_true', help='Do not start the network monitor')
    parser.add_argument('--setup', action='store_true', help='Force first-time setup mode')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    
    return parser.parse_args()

def main():
    """Main application entry point."""
    # Parse command line arguments
    args = parse_args()

    # Initialize logging
    init_logging()

    try:
        # Initialize config
        config_path = os.path.join(base_dir, args.config)
        logger.info(f"Loading configuration from {config_path}")
        config = Config(config_path)
        
        # Initialize plugin manager
        plugin_manager = NewPluginManager(config)
        
        # Initialize network monitor
        network_monitor = NetworkMonitor(config, plugin_manager)
        
        # Start network monitor if requested
        if not args.no_monitor:
            network_monitor.start()
            
        # Start web interface if requested
        if not args.no_web:
            # Initialize the web application
            socketio, app = create_web_app(config, plugin_manager, network_monitor)
            
            # Get web host and port
            host = args.host or config.get('web.host', '0.0.0.0')
            port = args.port or config.get('web.port', 8080)
            
            # Start the web server
            logger.info(f"Starting web server on {host}:{port}")
            socketio.run(app, host=host, port=port, debug=args.debug)
        else:
            logger.info("Web interface disabled, running in headless mode")
            # Keep the application running
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
