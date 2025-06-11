"""
Application factory module for NetScout-Pi-V2.
"""

import os
import logging
from flask import Flask, render_template
from flask_socketio import SocketIO

# Initialize Flask-SocketIO for real-time communication
socketio = SocketIO(cors_allowed_origins="*", 
                   async_mode='eventlet',
                   logger=True,
                   engineio_logger=True,
                   ping_timeout=70,  # Increased to 70 seconds
                   ping_interval=25,
                   always_connect=True)  # Force immediate connection
logger = logging.getLogger(__name__)

def create_app(test_config=None):
    """
    Create and configure the Flask application.
    
    Args:
        test_config (dict, optional): Test configuration. Defaults to None.
        
    Returns:
        Flask: Configured Flask application.
    """
    # Create and configure the app
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
                
    # Set default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_change_in_production'),
        PLUGIN_FOLDER=os.path.join(os.path.dirname(__file__), 'plugins'),
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the plugin folder exists
    os.makedirs(app.config['PLUGIN_FOLDER'], exist_ok=True)

    # Register blueprints
    from app.api.routes import api_bp
    app.register_blueprint(api_bp)

    # Initialize plugin manager
    from app.plugins.manager import init_plugin_manager
    init_plugin_manager(app)

    # Initialize dashboard routes
    from app.api.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    # Initialize Socket.IO with the app
    socketio.init_app(app, transports=['polling', 'websocket'])

    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', message="Page not found"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('error.html', message="Internal server error"), 500

    return app
