#!/usr/bin/env python3
# NetProbe Pi - Main Application Entry Point

import os
import sys
import logging
import argparse
from pathlib import Path

# Add the src directory to the path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Check for required packages before importing our modules
try:
    import yaml
except ImportError:
    print("Error: PyYAML is required but not found.")
    print("Please install it with one of these commands:")
    print("  sudo apt-get install python3-yaml")
    print("  pip install pyyaml --break-system-packages")
    print("Or run our dependency installer script:")
    print("  sudo bash scripts/install_dependencies.sh")
    sys.exit(1)

# Import core modules
try:
    from src.core.config import Config
    from src.core.plugin_manager import PluginManager
    from src.core.network_monitor import NetworkMonitor
    from src.core.logger import setup_logging
    from src.web.app import create_app
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all required packages are installed.")
    print("See requirements.txt for the list of dependencies.")
    print("You can install all dependencies with:")
    print("  sudo bash scripts/install_dependencies.sh")
    sys.exit(1)

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
    args = parse_args()
    
    # Setup logging
    log_level = getattr(logging, args.log_level)
    setup_logging(log_level=log_level, debug=args.debug)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting NetProbe Pi...")
    
    # Load configuration
    try:
        config = Config(args.config)
        logger.info(f"Configuration loaded from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        if args.debug:
            logger.exception("Configuration error details:")
        sys.exit(1)
    
    # Check for setup mode
    if args.setup:
        config.set('setup.completed', False)
        logger.info("Forcing setup mode")
    
    # Initialize plugin manager
    try:
        plugin_manager = PluginManager(config)
        plugin_manager.discover_plugins()
        logger.info(f"Discovered {len(plugin_manager.plugins)} plugins")
    except Exception as e:
        logger.error(f"Failed to initialize plugin manager: {e}")
        if args.debug:
            logger.exception("Plugin manager error details:")
        sys.exit(1)
    
    # Start network monitor if enabled
    if not args.no_monitor:
        try:
            network_monitor = NetworkMonitor(config, plugin_manager)
            network_monitor.start()
            logger.info("Network monitor started")
        except Exception as e:
            logger.error(f"Failed to start network monitor: {e}")
            if args.debug:
                logger.exception("Network monitor error details:")
            sys.exit(1)
    else:
        logger.info("Network monitor disabled")
        network_monitor = None
    
    # Start web interface if enabled
    if not args.no_web:
        try:
            app = create_app(config, plugin_manager, network_monitor)
            host = config.get('web.host', '0.0.0.0')
            port = config.get('web.port', 8080)  # Default to 8080 instead of 80 to avoid requiring root
            debug = args.debug
            
            logger.info(f"Starting web interface on {host}:{port}")
            app.run(host=host, port=port, debug=debug)
        except Exception as e:
            logger.error(f"Failed to start web interface: {e}")
            if args.debug:
                logger.exception("Web interface error details:")
            sys.exit(1)
    else:
        logger.info("Web interface disabled")
    
    logger.info("NetProbe Pi started successfully")

if __name__ == "__main__":
    main()
