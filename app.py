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
    from src.core.network_monitor import NetworkMonitor
    from src.core.logger import setup_logging
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

def create_app():
    """Create and configure Flask application.
    
    Returns:
        tuple: (socketio, app) The SocketIO and Flask application instances.
    """
    try:
        # Create Flask app
        app = Flask(__name__, 
                   template_folder=os.path.join(base_dir, 'src', 'web', 'templates'),
                   static_folder=os.path.join(base_dir, 'src', 'web', 'static'))
        
        # Configure app
        app.config['SECRET_KEY'] = os.urandom(24)
        
        # Initialize SocketIO
        socketio = SocketIO(app, async_mode='eventlet')
        
        return socketio, app
    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}")
        raise

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='NetProbe Pi - Network Diagnostics System')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', type=str, default='/etc/netprobe/config.yaml', 
                        help='Path to configuration file')
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Set logging level')
    parser.add_argument('--no-web', action='store_true', help='Do not start the web interface')
    parser.add_argument('--no-monitor', action='store_true', help='Do not start the network monitor')
    parser.add_argument('--setup', action='store_true', help='Force first-time setup mode')
    
    return parser.parse_args()

def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description='NetProbe Pi Network Monitoring Tool')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    args = parser.parse_args()

    # Initialize logging
    init_logging()

    try:
        # Create app and get socket instance
        socketio, app = create_app()

        # Start the application
        logger.info(f"Starting application on {args.host}:{args.port}")
        socketio.run(app, host=args.host, port=args.port, debug=args.debug)

    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
