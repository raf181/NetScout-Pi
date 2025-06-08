#!/usr/bin/env python3
# NetProbe Pi - Web Application

import os
import sys
import logging
import datetime
import json
import secrets
import bcrypt
import jwt
from functools import wraps
from pathlib import Path

from flask import (
    Flask, request, session, g, redirect, url_for, render_template,
    flash, jsonify, Response, send_from_directory, abort
)
from flask_socketio import SocketIO, emit

def create_app(config, plugin_manager, network_monitor):
    """Create and configure Flask application.
    
    Args:
        config: Application configuration.
        plugin_manager: Plugin manager instance.
        network_monitor: Network monitor instance.
        
    Returns:
        Flask application instance.
    """
    # Create Flask app
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Configure app
    app.config['SECRET_KEY'] = config.get('security.jwt_secret')
    if not app.config['SECRET_KEY']:
        app.config['SECRET_KEY'] = secrets.token_hex(32)
        config.set('security.jwt_secret', app.config['SECRET_KEY'])
    
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(
        seconds=config.get('web.session_timeout', 3600))
    
    # Create SocketIO instance
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Configure logger
    logger = logging.getLogger(__name__)
    
    # Store app state
    app.config['NETPROBE_CONFIG'] = config
    app.config['PLUGIN_MANAGER'] = plugin_manager
    app.config['NETWORK_MONITOR'] = network_monitor
    
    # Authentication
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_required = config.get('web.auth_required', True)
            
            if not auth_required:
                return f(*args, **kwargs)
            
            # Check if user is logged in
            if 'user_id' in session:
                return f(*args, **kwargs)
            
            # Check for JWT token
            token = request.headers.get('Authorization')
            if token and token.startswith('Bearer '):
                token = token[7:]
                try:
                    jwt_secret = config.get('security.jwt_secret')
                    payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
                    if 'user_id' in payload:
                        return f(*args, **kwargs)
                except jwt.PyJWTError:
                    pass
            
            # API requests should return 401
            if request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized"}), 401
            
            # Web requests should redirect to login
            return redirect(url_for('login', next=request.url))
        
        return decorated_function
    
    # Restrict access based on interface
    def interface_access_control():
        allow_eth0 = config.get('security.allow_eth0_access', False)
        if not allow_eth0:
            # Check if request is coming from eth0
            client_ip = request.remote_addr
            if client_ip != '127.0.0.1':  # Always allow localhost
                # Check if eth0 has this IP in its subnet
                eth0_info = network_monitor.get_interface_info('eth0')
                if eth0_info and 'addresses' in eth0_info and 'ipv4' in eth0_info['addresses']:
                    eth0_ip = eth0_info['addresses']['ipv4']['address']
                    eth0_netmask = eth0_info['addresses']['ipv4']['netmask']
                    # Very basic network check (would need to properly check subnet)
                    if client_ip.startswith(eth0_ip.split('.')[0]):
                        return False
        return True
    
    @app.before_request
    def before_request():
        # Perform interface access control
        if not interface_access_control():
            if request.path.startswith('/api/'):
                return jsonify({"error": "Access denied from this network interface"}), 403
            else:
                return render_template('error.html', 
                                       error="Access denied from this network interface"), 403
    
    # Routes
    @app.route('/')
    @login_required
    def index():
        return render_template('index.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        
        if request.method == 'POST':
            password = request.form['password']
            stored_hash = config.get('security.password_hash')
            
            if not stored_hash:
                # First-time login, set the password
                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
                config.set('security.password_hash', hashed.decode('utf-8'))
                session['user_id'] = 'admin'
                flash('Password set successfully')
                return redirect(url_for('index'))
            
            # Verify password
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                session['user_id'] = 'admin'
                next_url = request.args.get('next') or url_for('index')
                return redirect(next_url)
            else:
                error = 'Invalid password'
        
        # First time setup?
        first_time = not config.get('security.password_hash')
        
        return render_template('login.html', error=error, first_time=first_time)
    
    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        return redirect(url_for('login'))
    
    @app.route('/settings')
    @login_required
    def settings():
        return render_template('settings.html')
    
    # API routes
    @app.route('/api/status')
    @login_required
    def api_status():
        eth0_info = network_monitor.get_interface_info('eth0')
        wlan0_info = network_monitor.get_interface_info('wlan0')
        
        return jsonify({
            "version": "0.1.0",
            "uptime": get_uptime(),
            "interfaces": {
                "eth0": eth0_info,
                "wlan0": wlan0_info
            }
        })
    
    @app.route('/api/plugins')
    @login_required
    def api_plugins():
        plugins = plugin_manager.get_all_plugins()
        return jsonify(plugins)
    
    @app.route('/api/plugin/<plugin_name>')
    @login_required
    def api_plugin(plugin_name):
        plugin_status = plugin_manager.get_plugin_status(plugin_name)
        if not plugin_status:
            return jsonify({"error": f"Plugin not found: {plugin_name}"}), 404
        
        return jsonify(plugin_status)
    
    @app.route('/api/plugin/<plugin_name>/run', methods=['POST'])
    @login_required
    def api_run_plugin(plugin_name):
        # Get plugin parameters from request
        params = request.json or {}
        
        # Start plugin
        plugin = plugin_manager.get_plugin(plugin_name)
        if not plugin:
            return jsonify({"error": f"Plugin not found: {plugin_name}"}), 404
        
        # Function to send updates via SocketIO
        def send_updates(result):
            socketio.emit(f'plugin_result_{plugin_name}', result)
        
        # Run plugin
        success = plugin_manager.run_plugin(plugin_name, callback=send_updates, **params)
        if not success:
            return jsonify({"error": f"Failed to start plugin: {plugin_name}"}), 500
        
        return jsonify({"status": "running", "plugin": plugin_name})
    
    @app.route('/api/plugin/<plugin_name>/stop', methods=['POST'])
    @login_required
    def api_stop_plugin(plugin_name):
        success = plugin_manager.stop_plugin(plugin_name)
        if not success:
            return jsonify({"error": f"Failed to stop plugin: {plugin_name}"}), 500
        
        return jsonify({"status": "stopped", "plugin": plugin_name})
    
    @app.route('/api/settings', methods=['GET'])
    @login_required
    def api_get_settings():
        """Get system settings."""
        try:
            # Get settings that can be exposed to the user
            exposed_settings = {
                "network": {
                    "interface": config.get('network.interface', 'eth0'),
                    "poll_interval": config.get('network.poll_interval', 5),
                    "auto_run": config.get('network.auto_run_on_connect', True),
                    "default_plugins": config.get('network.default_plugins', []),
                    "monitor_method": config.get('network.monitor_method', 'poll')
                },
                "security": {
                    "allow_eth0_access": config.get('security.allow_eth0_access', False),
                    "session_timeout": config.get('web.session_timeout', 3600)
                },
                "logging": {
                    "log_level": config.get('logging.level', 'INFO'),
                    "max_logs": config.get('logging.max_logs', 100)
                },
                "web": {
                    "port": config.get('web.port', 5000),
                    "host": config.get('web.host', '0.0.0.0')
                }
            }
            
            return jsonify(exposed_settings)
            
        except Exception as e:
            logger.error(f"Error getting settings: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/settings', methods=['POST'])
    @login_required
    def api_update_settings():
        """Update system settings."""
        try:
            # Get settings from request
            new_settings = request.json
            
            if not new_settings:
                return jsonify({"error": "No settings provided"}), 400
                
            # Update settings
            for section, items in new_settings.items():
                for key, value in items.items():
                    setting_key = f"{section}.{key}"
                    config.set(setting_key, value)
            
            # Save configuration
            config.save()
            
            return jsonify({"message": "Settings updated successfully"})
            
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/settings/password', methods=['POST'])
    @login_required
    def api_change_password():
        """Change admin password."""
        try:
            # Get current and new passwords
            data = request.json
            
            if not data or 'current_password' not in data or 'new_password' not in data:
                return jsonify({"error": "Current and new passwords are required"}), 400
                
            current_password = data['current_password']
            new_password = data['new_password']
            
            # Verify current password
            stored_hash = config.get('security.password_hash')
            
            if not stored_hash:
                return jsonify({"error": "No password set"}), 400
                
            if not bcrypt.checkpw(current_password.encode('utf-8'), stored_hash.encode('utf-8')):
                return jsonify({"error": "Current password is incorrect"}), 401
                
            # Hash new password
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), salt)
            
            # Save new password
            config.set('security.password_hash', hashed.decode('utf-8'))
            config.save()
            
            return jsonify({"message": "Password changed successfully"})
            
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/logs/<plugin_name>')
    @login_required
    def api_plugin_logs(plugin_name):
        plugin = plugin_manager.get_plugin(plugin_name)
        if not plugin:
            return jsonify({"error": f"Plugin not found: {plugin_name}"}), 404
        
        runs = plugin.logger.get_recent_runs()
        return jsonify({"plugin": plugin_name, "runs": runs})
    
    @app.route('/api/logs/<plugin_name>/<run_id>')
    @login_required
    def api_plugin_log(plugin_name, run_id):
        plugin = plugin_manager.get_plugin(plugin_name)
        if not plugin:
            return jsonify({"error": f"Plugin not found: {plugin_name}"}), 404
        
        log_dir = plugin.logger.plugin_log_dir
        log_file = os.path.join(log_dir, f'{run_id}.json')
        
        if not os.path.exists(log_file):
            return jsonify({"error": f"Log not found: {run_id}"}), 404
        
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
                return jsonify(log_data)
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            return jsonify({"error": f"Error reading log file: {e}"}), 500
    
    @app.route('/api/logs/export', methods=['GET'])
    @login_required
    def api_export_logs():
        """Export logs as ZIP file."""
        from src.core.logger import export_logs
        import tempfile
        
        try:
            # Create temporary directory for ZIP file
            with tempfile.TemporaryDirectory() as temp_dir:
                # Get number of days from query parameter, default to 7
                days = int(request.args.get('days', 7))
                
                # Export logs
                zip_file = export_logs(temp_dir, days=days)
                
                if not zip_file or not os.path.exists(zip_file):
                    return jsonify({"error": "Failed to export logs"}), 500
                
                # Send file to client
                return send_from_directory(
                    os.path.dirname(zip_file),
                    os.path.basename(zip_file),
                    as_attachment=True,
                    attachment_filename=os.path.basename(zip_file)
                )
                
        except Exception as e:
            logger.error(f"Error exporting logs: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/plugin/upload', methods=['POST'])
    @login_required
    def api_upload_plugin():
        """Upload and install a new plugin."""
        try:
            # Check if file was uploaded
            if 'plugin_file' not in request.files:
                return jsonify({"error": "No file uploaded"}), 400
                
            file = request.files['plugin_file']
            
            # Check if file has a name
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
                
            # Check if file is a Python file
            if not file.filename.endswith('.py'):
                return jsonify({"error": "Only Python files (.py) are allowed"}), 400
            
            # Save file to temporary location
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp:
                file.save(temp.name)
                temp_path = temp.name
            
            # Install plugin
            result = plugin_manager.install_plugin(temp_path, file.filename)
            
            # Remove temporary file
            os.remove(temp_path)
            
            if not result:
                return jsonify({"error": "Failed to install plugin"}), 500
                
            return jsonify({"message": "Plugin installed successfully", "plugin": result})
            
        except Exception as e:
            logger.error(f"Error uploading plugin: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/plugin/<plugin_name>/uninstall', methods=['POST'])
    @login_required
    def api_uninstall_plugin(plugin_name):
        """Uninstall a plugin."""
        try:
            # Check if plugin exists
            if not plugin_manager.get_plugin_status(plugin_name):
                return jsonify({"error": f"Plugin not found: {plugin_name}"}), 404
                
            # Uninstall plugin
            result = plugin_manager.uninstall_plugin(plugin_name)
            
            if not result:
                return jsonify({"error": f"Failed to uninstall plugin: {plugin_name}"}), 500
                
            return jsonify({"message": f"Plugin {plugin_name} uninstalled successfully"})
            
        except Exception as e:
            logger.error(f"Error uninstalling plugin: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/sequences', methods=['GET'])
    @login_required
    def api_get_sequences():
        """Get plugin sequences."""
        try:
            sequences = plugin_manager.get_sequences()
            return jsonify(sequences)
            
        except Exception as e:
            logger.error(f"Error getting sequences: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/sequences', methods=['POST'])
    @login_required
    def api_create_sequence():
        """Create a new plugin sequence."""
        try:
            data = request.json
            
            if not data or 'name' not in data or 'plugins' not in data:
                return jsonify({"error": "Sequence name and plugins are required"}), 400
                
            name = data['name']
            plugins = data['plugins']
            description = data.get('description', '')
            
            # Create sequence
            result = plugin_manager.create_sequence(name, plugins, description)
            
            if not result:
                return jsonify({"error": "Failed to create sequence"}), 500
                
            return jsonify({"message": "Sequence created successfully", "sequence": result})
            
        except Exception as e:
            logger.error(f"Error creating sequence: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/sequences/<sequence_name>', methods=['PUT'])
    @login_required
    def api_update_sequence(sequence_name):
        """Update a plugin sequence."""
        try:
            data = request.json
            
            if not data or 'plugins' not in data:
                return jsonify({"error": "Plugins list is required"}), 400
                
            plugins = data['plugins']
            description = data.get('description')
            
            # Update sequence
            result = plugin_manager.update_sequence(sequence_name, plugins, description)
            
            if not result:
                return jsonify({"error": f"Sequence not found: {sequence_name}"}), 404
                
            return jsonify({"message": "Sequence updated successfully", "sequence": result})
            
        except Exception as e:
            logger.error(f"Error updating sequence: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/sequences/<sequence_name>', methods=['DELETE'])
    @login_required
    def api_delete_sequence(sequence_name):
        """Delete a plugin sequence."""
        try:
            # Delete sequence
            result = plugin_manager.delete_sequence(sequence_name)
            
            if not result:
                return jsonify({"error": f"Sequence not found: {sequence_name}"}), 404
                
            return jsonify({"message": f"Sequence {sequence_name} deleted successfully"})
            
        except Exception as e:
            logger.error(f"Error deleting sequence: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/sequences/<sequence_name>/run', methods=['POST'])
    @login_required
    def api_run_sequence(sequence_name):
        """Run a plugin sequence."""
        try:
            # Get parameters from request
            params = request.json or {}
            
            # Run sequence
            run_id = plugin_manager.run_sequence(sequence_name, **params)
            
            if not run_id:
                return jsonify({"error": f"Failed to run sequence: {sequence_name}"}), 500
                
            return jsonify({"message": f"Sequence {sequence_name} started", "run_id": run_id})
            
        except Exception as e:
            logger.error(f"Error running sequence: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    # SocketIO events
    @socketio.on('connect')
    def handle_connect():
        logger.debug(f"Client connected: {request.sid}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.debug(f"Client disconnected: {request.sid}")
    
    # Helper functions
    def get_uptime():
        """Get system uptime in seconds."""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return int(uptime_seconds)
        except Exception as e:
            logger.error(f"Error getting uptime: {e}")
            return 0
    
    # Return app with SocketIO
    return socketio.init_app(app) or app
