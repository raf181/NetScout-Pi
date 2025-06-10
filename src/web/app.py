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
import netifaces
import socket
import subprocess
import werkzeug.routing
import werkzeug.exceptions
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
    # Configure logger
    logger = logging.getLogger(__name__)
    
    # Create Flask app
    template_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
    static_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
    
    app = Flask(__name__, 
                template_folder=template_folder,
                static_folder=static_folder)
    
    # Debug template paths
    logger.info(f"Template folder: {template_folder}")
    try:
        logger.info(f"Available templates: {os.listdir(template_folder)}")
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
    
    # Configure app
    app.config['SECRET_KEY'] = config.get('security.jwt_secret')
    if not app.config['SECRET_KEY']:
        app.config['SECRET_KEY'] = secrets.token_hex(32)
        config.set('security.jwt_secret', app.config['SECRET_KEY'])
    
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(
        seconds=config.get('web.session_timeout', 3600, type_cast=int))
    
    # Create SocketIO instance
    socketio = SocketIO(app, cors_allowed_origins="*")
    
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
                eth0_info = network_monitor.get_interface_status('eth0')
                if eth0_info and 'addresses' in eth0_info and 'ipv4' in eth0_info['addresses']:
                    eth0_ip = eth0_info['addresses']['ipv4'][0]['addr']
                    eth0_netmask = eth0_info['addresses']['ipv4'][0]['netmask']
                    # Very basic network check (would need to properly check subnet)
                    if client_ip.startswith(eth0_ip.split('.')[0]):
                        return False
        return True
    
    @app.before_request
    def before_request():
        # Check if setup is needed and redirect if necessary
        if not config.get('setup.completed', False) and request.endpoint != 'setup' and request.endpoint != 'static':
            return redirect(url_for('setup'))
            
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
    
    @app.route('/setup', methods=['GET', 'POST'])
    def setup():
        """First-time setup wizard."""
        # Check if setup already completed
        if config.get('setup.completed', False) and not request.args.get('force'):
            flash('Setup already completed', 'info')
            return redirect(url_for('index'))
        
        error = None
        
        if request.method == 'POST':
            # Get form data
            network_interface = request.form.get('network_interface')
            wifi_interface = request.form.get('wifi_interface')
            log_dir = request.form.get('log_dir')
            data_dir = request.form.get('data_dir')
            web_port = request.form.get('web_port')
            auth_required = 'auth_required' in request.form
            
            # Validate
            if not network_interface:
                error = "Primary network interface is required"
            elif not log_dir:
                error = "Log directory is required"
            elif not data_dir:
                error = "Data directory is required"
            elif not web_port or not web_port.isdigit():
                error = "Valid web port is required"
            
            if not error:
                try:
                    # Update configuration
                    config.set('network.interface', network_interface)
                    if wifi_interface:
                        config.set('network.wifi_interface', wifi_interface)
                    
                    config.set('logging.directory', log_dir)
                    config.set('system.data_dir', data_dir)
                    config.set('web.port', int(web_port))
                    config.set('web.auth_required', auth_required)
                    
                    # Create directories if they don't exist
                    os.makedirs(log_dir, exist_ok=True)
                    os.makedirs(data_dir, exist_ok=True)
                    
                    # Mark setup as completed
                    config.set('setup.completed', True)
                    config.save()
                    
                    # Restart network monitor with new interface
                    if network_monitor:
                        network_monitor.stop()
                        network_monitor.interface = network_interface
                        network_monitor.start()
                    
                    flash('Setup completed successfully!', 'success')
                    
                    # Redirect to login if auth required, otherwise dashboard
                    if auth_required:
                        return redirect(url_for('login'))
                    else:
                        session['user_id'] = 'admin'  # Auto-login if no auth required
                        return redirect(url_for('index'))
                        
                except Exception as e:
                    logger.error(f"Setup error: {e}")
                    error = f"Setup failed: {str(e)}"
        
        # Get available network interfaces
        interfaces = []
        wifi_interfaces = []
        
        try:
            for iface in netifaces.interfaces():
                if iface == 'lo':  # Skip loopback
                    continue
                
                # Get IP addresses
                addresses = netifaces.ifaddresses(iface)
                ipv4 = addresses.get(netifaces.AF_INET, [])
                ipv6 = addresses.get(netifaces.AF_INET6, [])
                
                # Get interface description
                description = ""
                if ipv4:
                    description = f"IPv4: {ipv4[0].get('addr', 'N/A')}"
                elif ipv6:
                    description = f"IPv6: {ipv6[0].get('addr', 'N/A')}"
                else:
                    description = "No IP address"
                
                # Check if interface is up
                is_up = False
                try:
                    with open(f"/sys/class/net/{iface}/operstate", "r") as f:
                        state = f.read().strip()
                        is_up = state == "up" or state == "unknown"
                    if is_up:
                        description += " (Active)"
                except:
                    pass
                
                # Determine if it's a WiFi interface (simplified heuristic)
                is_wifi = iface.startswith(('wl', 'wlan', 'wifi', 'ath', 'ra'))
                
                # Check if it's the primary interface
                is_default = False
                try:
                    with open("/proc/net/route", "r") as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 2 and parts[0] == iface and parts[1] == '00000000':
                                is_default = True
                                description += " (Default Route)"
                                break
                except:
                    pass
                
                interface_info = {
                    'name': iface,
                    'description': description,
                    'default': is_default or iface == config.get('network.interface', 'eth0')
                }
                
                # Determine if it's a WiFi interface (simplified heuristic)
                is_wifi = iface.startswith(('wl', 'wlan', 'wifi', 'ath', 'ra'))
                
                # Get MAC address if available
                mac = ""
                link_info = addresses.get(netifaces.AF_LINK, [{}])
                if link_info and 'addr' in link_info[0]:
                    mac = link_info[0]['addr']
                    if mac:
                        description += f" | MAC: {mac}"
                
                # Get interface status using ip link
                try:
                    ip_output = subprocess.check_output(['ip', 'link', 'show', iface], 
                                                       universal_newlines=True)
                    if "UP" in ip_output:
                        description += " | Status: UP"
                    else:
                        description += " | Status: DOWN"
                except:
                    pass
                
                interface_info = {
                    'name': iface,
                    'description': description,
                    'default': iface == config.get('network.interface', 'eth0')
                }
                
                interfaces.append(interface_info)
                if is_wifi:
                    wifi_interfaces.append(interface_info)
                    
            # Sort interfaces by name
            interfaces.sort(key=lambda x: x['name'])
            wifi_interfaces.sort(key=lambda x: x['name'])
        except Exception as e:
            logger.error(f"Error detecting network interfaces: {e}")
            interfaces = [{'name': 'eth0', 'description': 'Default Ethernet', 'default': True}]
            wifi_interfaces = [{'name': 'wlan0', 'description': 'Default WiFi', 'default': False}]
        
        # Default paths
        default_log_dir = config.get('logging.directory', '/var/log/netprobe')
        default_data_dir = config.get('system.data_dir', '/var/lib/netprobe')
        
        return render_template('setup.html', 
                              interfaces=interfaces,
                              wifi_interfaces=wifi_interfaces,
                              default_log_dir=default_log_dir,
                              default_data_dir=default_data_dir,
                              error=error)
    
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
        
        # If this is first time and setup is not completed, redirect to setup
        if first_time and not config.get('setup.completed', False):
            return redirect(url_for('setup'))
        
        return render_template('login.html', error=error, first_time=first_time)
    
    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        return redirect(url_for('login'))
    
    @app.route('/settings')
    @login_required
    def settings():
        return render_template('settings.html')
    
    @app.route('/plugins')
    @login_required
    def plugins():
        """Plugin management page."""
        return render_template('plugins.html')
    
    @app.route('/results')
    @login_required
    def results():
        """Results overview page."""
        return render_template('results.html')
    
    @app.route('/results/<run_id>')
    @login_required
    def result_detail(run_id):
        """Detailed result view for a specific run."""
        return render_template('result_detail.html', run_id=run_id)
    
    @app.route('/logs')
    @login_required
    def logs():
        """System logs page."""
        return render_template('logs.html')
    
    # API routes
    @app.route('/api/status')
    @login_required
    def api_status():
        eth0_info = network_monitor.get_interface_status('eth0')
        wlan0_info = network_monitor.get_interface_status('wlan0')
        
        return jsonify({
            "version": "0.1.0",
            "uptime": get_uptime(),
            "interfaces": {
                "eth0": eth0_info,
                "wlan0": wlan0_info
            }
        })
    
    @app.route('/api/plugins')
    def api_plugins():
        plugins = plugin_manager.get_all_plugins()
        return jsonify(plugins)
    
    @app.route('/api/plugin/<plugin_name>')
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
    
    @app.route('/api/plugin/<plugin_name>/toggle', methods=['POST'])
    @login_required
    def api_toggle_plugin(plugin_name):
        """Toggle plugin enabled state."""
        data = request.json or {}
        enabled = data.get('enabled', True)
        
        # Update plugin config
        config.set(f'plugins.{plugin_name}.enabled', enabled)
        config.save()
        
        # Reload plugin if needed
        if enabled and plugin_name in plugin_manager.plugins:
            plugin_manager.load_plugin(plugin_name)
        
        return jsonify({"status": "success"})
    
    @app.route('/api/settings', methods=['GET'])
    @login_required
    def api_get_settings():
        """Get system settings."""
        try:
            # Get settings that can be exposed to the user
            exposed_settings = {
                "network": {
                    "interface": config.get('network.interface', 'eth0'),
                    "poll_interval": config.get('network.poll_interval', 5, type_cast=int),
                    "auto_run": config.get('network.auto_run_on_connect', True),
                    "default_plugins": config.get('network.default_plugins', []),
                    "monitor_method": config.get('network.monitor_method', 'poll')
                },
                "security": {
                    "allow_eth0_access": config.get('security.allow_eth0_access', False),
                    "session_timeout": config.get('web.session_timeout', 3600, type_cast=int)
                },
                "logging": {
                    "log_level": config.get('logging.level', 'INFO'),
                    "max_logs": config.get('logging.max_logs', 100, type_cast=int)
                },
                "web": {
                    "port": config.get('web.port', 5000, type_cast=int),
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
    
    @app.route('/api/logs', methods=['GET'])
    @login_required
    def api_system_logs():
        """Get system logs."""
        try:
            # Parse query parameters
            log_type = request.args.get('type', 'system')
            log_level = request.args.get('level', 'all')
            time_range = request.args.get('time', '24h')
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('size', 50))
            
            # Set default log directory based on type
            if log_type == 'system':
                log_dir = config.get('logging.directory', '/var/log/netprobe')
            elif log_type == 'network':
                log_dir = os.path.join(config.get('logging.directory', '/var/log/netprobe'), 'network')
            elif log_type == 'plugins':
                log_dir = os.path.join(config.get('logging.directory', '/var/log/netprobe'), 'plugins')
            elif log_type == 'web':
                log_dir = os.path.join(config.get('logging.directory', '/var/log/netprobe'), 'web')
            else:
                log_dir = config.get('logging.directory', '/var/log/netprobe')
            
            # Set log file path
            log_file = os.path.join(log_dir, 'netprobe.log')
            if not os.path.exists(log_file):
                log_file = next((f for f in os.listdir(log_dir) if f.endswith('.log')), None)
                if log_file:
                    log_file = os.path.join(log_dir, log_file)
                else:
                    return jsonify({"logs": [], "total": 0})
            
            # Read and parse log file
            logs = []
            
            # Convert level filter to numeric value
            level_map = {
                'all': 0,
                'debug': 10,
                'info': 20,
                'warning': 30,
                'error': 40
            }
            min_level = level_map.get(log_level, 0)
            
            # Convert time range to timestamp
            now = datetime.datetime.now()
            if time_range == '24h':
                min_time = now - datetime.timedelta(hours=24)
            elif time_range == '7d':
                min_time = now - datetime.timedelta(days=7)
            elif time_range == '30d':
                min_time = now - datetime.timedelta(days=30)
            else:
                min_time = now - datetime.timedelta(days=365*10)  # Effectively "all time"
            
            # Parse log entries
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            # Basic log parsing - assumes format: "2025-06-09 10:50:35,185 - __main__ - INFO - Discovered 8 plugins"
                            parts = line.split(' - ', 3)
                            if len(parts) >= 4:
                                timestamp_str = parts[0].strip()
                                source = parts[1].strip()
                                level = parts[2].strip()
                                message = parts[3].strip()
                                
                                # Filter by level
                                level_value = level_map.get(level.lower(), 0)
                                if level_value < min_level:
                                    continue
                                
                                # Filter by time
                                try:
                                    timestamp = datetime.datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                                    if timestamp < min_time:
                                        continue
                                except:
                                    # If we can't parse the timestamp, include it anyway
                                    pass
                                
                                logs.append({
                                    'timestamp': timestamp_str,
                                    'source': source,
                                    'level': level,
                                    'message': message
                                })
                        except Exception as e:
                            logger.error(f"Error parsing log line: {e}")
            
            # Sort logs by timestamp (newest first)
            logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Paginate results
            total_logs = len(logs)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paged_logs = logs[start_idx:end_idx]
            
            return jsonify({
                "logs": paged_logs,
                "total": total_logs
            })
            
        except Exception as e:
            logger.error(f"Error retrieving logs: {str(e)}")
            return jsonify({"error": str(e), "logs": [], "total": 0}), 500
    
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
    
    @app.route('/api/results')
    @login_required
    def api_results():
        """Get all results."""
        results = []
        try:
            # Assuming each plugin stores its results in a directory structure
            for plugin_name in plugin_manager.get_plugin_names():
                plugin = plugin_manager.get_plugin(plugin_name)
                if plugin and hasattr(plugin, 'logger') and hasattr(plugin.logger, 'get_recent_runs'):
                    plugin_results = plugin.logger.get_recent_runs()
                    for result in plugin_results:
                        result['plugin_name'] = plugin_name
                        results.append(result)
            
            # If no results yet, add some sample data for testing
            if not results:
                results = [
                    {
                        "plugin_name": "ip_info",
                        "timestamp": datetime.datetime.now().isoformat(),
                        "run_id": "sample-1",
                        "success": True,
                        "plugin": {
                            "name": "ip_info",
                            "version": "0.1.0",
                            "description": "IP Information"
                        }
                    },
                    {
                        "plugin_name": "ping_test",
                        "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=30)).isoformat(),
                        "run_id": "sample-2",
                        "success": True,
                        "plugin": {
                            "name": "ping_test",
                            "version": "0.1.0",
                            "description": "Ping Test"
                        }
                    }
                ]
            
            # Sort by timestamp (newest first)
            results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return jsonify(results)
        except Exception as e:
            logger.error(f"Error getting results: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/results/recent')
    @login_required
    def api_recent_results():
        """Get recent results (last 10)."""
        try:
            # Get all results and return the most recent 10
            all_results = api_results().json
            return jsonify(all_results[:10] if isinstance(all_results, list) else [])
        except Exception as e:
            logger.error(f"Error getting recent results: {e}")
            # Return sample data in case of error
            sample_data = [
                {
                    "run_id": "sample-1",
                    "plugin": {
                        "name": "ping_test",
                        "version": "0.1.0",
                        "description": "Tests ping to default gateway and internet"
                    },
                    "timestamp": datetime.datetime.now().isoformat(),
                    "success": True,
                    "data": {
                        "gateway_ping": 1.5,
                        "internet_ping": 45.2
                    }
                },
                {
                    "run_id": "sample-2",
                    "plugin": {
                        "name": "ip_info",
                        "version": "0.1.0",
                        "description": "Gets IP address information"
                    },
                    "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=5)).isoformat(),
                    "success": True,
                    "data": {
                        "public_ip": "203.0.113.1",
                        "isp": "Sample ISP"
                    }
                }
            ]
            return jsonify(sample_data)
    
    @app.route('/api/results/<run_id>')
    def api_result_detail(run_id):
        """Get details for a specific result."""
        try:
            # Search for the result across all plugins
            for plugin_name in plugin_manager.get_plugin_names():
                plugin = plugin_manager.get_plugin(plugin_name)
                if not (hasattr(plugin, 'logger') and hasattr(plugin.logger, 'get_run')):
                    continue
                
                result = plugin.logger.get_run(run_id)
                if result:
                    result['plugin_name'] = plugin_name
                    return jsonify(result)
            
            return jsonify({"error": "Result not found"}), 404
        except Exception as e:
            logger.error(f"Error getting result detail: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/results/<run_id>/export')
    @login_required
    def api_export_result(run_id):
        """Export a specific result as JSON."""
        try:
            # Get the result
            result_response = api_result_detail(run_id)
            if isinstance(result_response, tuple) and result_response[1] != 200:
                return result_response
            
            result = result_response.json
            
            # Create a response with the result as a downloadable file
            response = Response(
                json.dumps(result, indent=2),
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment;filename=result_{run_id}.json'}
            )
            
            return response
        except Exception as e:
            logger.error(f"Error exporting result: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/system/status')
    @login_required
    def api_system_status():
        """Get system status information (CPU, memory, disk, etc.)"""
        try:
            import psutil
            
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Get temperature if available
            temperature = None
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Try to find CPU temperature
                    for name, entries in temps.items():
                        if name.lower() in ['cpu_thermal', 'coretemp', 'cpu-thermal']:
                            temperature = entries[0].current
                            break
            
            # Get uptime
            uptime = get_uptime()
            
            return jsonify({
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "temperature": temperature,
                "uptime": uptime
            })
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            # Return sample data in case of error
            return jsonify({
                "cpu_percent": 25,
                "memory_percent": 40,
                "disk_percent": 65,
                "temperature": 45,
                "uptime": 3600  # 1 hour
            })
    
    @app.route('/api/network/status')
    @login_required
    def api_network_status():
        """Get detailed network status information."""
        try:
            # Get interface information
            interfaces = {}
            
            # Get primary interface
            primary_interface = config.get('network.interface', 'eth0')
            interfaces[primary_interface] = network_monitor.get_interface_status(primary_interface)
            
            # Get WiFi interface if different
            wifi_interface = config.get('network.wifi_interface', 'wlan0')
            if wifi_interface and wifi_interface != primary_interface:
                interfaces[wifi_interface] = network_monitor.get_interface_status(wifi_interface)
            
            # If we couldn't get interface data, create some sample data
            if not interfaces.get(primary_interface):
                interfaces[primary_interface] = {
                    'carrier': True,
                    'addresses': {
                        'ipv4': [
                            {
                                'addr': '192.168.1.100',
                                'netmask': '255.255.255.0',
                                'broadcast': '192.168.1.255'
                            }
                        ]
                    },
                    'mac': '00:11:22:33:44:55'
                }
            
            # Get default gateway
            default_gateway = None
            try:
                import netifaces
                gws = netifaces.gateways()
                if 'default' in gws and netifaces.AF_INET in gws['default']:
                    default_gateway = gws['default'][netifaces.AF_INET][0]
            except Exception as e:
                logger.warning(f"Error getting default gateway: {str(e)}")
            
            # Get DNS servers
            dns_servers = []
            try:
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        if line.startswith('nameserver'):
                            dns_servers.append(line.split()[1])
            except Exception as e:
                logger.warning(f"Error getting DNS servers: {str(e)}")
            
            # Get Internet connection status
            internet_status = "unknown"
            try:
                import socket
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                internet_status = "connected"
            except Exception:
                internet_status = "disconnected"
            
            return jsonify({
                "primary_interface": primary_interface,
                "wifi_interface": wifi_interface if wifi_interface != primary_interface else None,
                "default_gateway": default_gateway,
                "dns_servers": dns_servers,
                "internet_status": internet_status,
                **interfaces
            })
        except Exception as e:
            logger.error(f"Error getting network status: {str(e)}")
            # Return sample data in case of error
            return jsonify({
                "primary_interface": "eth0",
                "wifi_interface": "wlan0",
                "default_gateway": "192.168.1.1",
                "dns_servers": ["8.8.8.8", "8.8.4.4"],
                "internet_status": "connected",
                "eth0": {
                    "carrier": True,
                    "up": True,
                    "addresses": {
                        "ipv4": [
                            {
                                "addr": "192.168.1.100",
                                "netmask": "255.255.255.0",
                                "broadcast": "192.168.1.255"
                            }
                        ]
                    },
                    "mac": "00:11:22:33:44:55"
                },
                "wlan0": {
                    "carrier": False,
                    "up": False,
                    "addresses": {}
                }
            })
    
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        logger.warning(f"404 error: {request.path}")
        return render_template('error.html', error="Page not found", details="The requested page could not be found."), 404
        
    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"500 error: {str(e)}")
        return render_template('error.html', error="Internal server error", details="An unexpected error occurred."), 500
    
    @app.errorhandler(werkzeug.routing.BuildError)
    def handle_url_build_error(e):
        logger.error(f"URL build error: {str(e)}")
        return render_template('error.html', error="Navigation error", 
                              details="There was an error generating a URL. This might be due to a missing endpoint."), 500

    # Register SocketIO event handlers
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
    
    # Initialize SocketIO with the app
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Initialize web routes
    # Return both SocketIO instance and app for proper server initialization
    return socketio, app

# Remove the init_routes function as routes are already defined in create_app
# def init_routes(app, plugin_manager, socketio):
#     """Initialize web routes for the application."""
#     # Routes are already defined in create_app
#     # Store references
#     app.config['PLUGIN_MANAGER'] = plugin_manager
#     app.config['SOCKETIO'] = socketio
#     
#     @app.route('/')
#     def index():
#         """Main application page."""
#         return render_template('index.html')
# 
#     @app.route('/plugins')
#     def plugins():
#         """Plugin management page."""
#         plugin_list = plugin_manager.get_plugins()
#         return render_template('plugins.html', plugins=plugin_list)
#         
#     @app.route('/results')
#     def results():
#         """View plugin execution results."""
#         return render_template('results.html')
#         
#     @app.route('/logs')
#     def logs():
#         """View application logs."""
#         return render_template('logs.html')
#         
#     @app.route('/settings')
#     def settings():
#         """Application settings page."""
#         return render_template('settings.html')
#         
#     @app.route('/api/plugins')
#     def api_plugins():
#         """API endpoint for plugin list."""
#         plugins = plugin_manager.get_plugins()
#         return jsonify(plugins)
#         
#     @app.route('/api/plugins/<plugin_id>/run', methods=['POST'])
#     def api_run_plugin(plugin_id):
#         """API endpoint to run a plugin.
#         
#         Args:
#             plugin_id: ID of the plugin to run.
#         """
#         # Get plugin parameters from request
#         params = request.json or {}
#         
#         # Run the plugin
#         try:
#             result = plugin_manager.run_plugin(plugin_id, **params)
#             return jsonify(result)
#         except Exception as e:
#             return jsonify({"error": str(e)}), 500
#             
#     @app.route('/api/plugins/<plugin_id>/stop', methods=['POST'])
#     def api_stop_plugin(plugin_id):
#         """API endpoint to stop a running plugin.
#         
#         Args:
#             plugin_id: ID of the plugin to stop.
#         """
#         try:
#             plugin_manager.stop_plugin(plugin_id)
#             return jsonify({"status": "stopped"})
#         except Exception as e:
#             return jsonify({"error": str(e)}), 500
#             
#     @app.route('/api/results')
#     def api_results():
#         """API endpoint for plugin execution results."""
#         return jsonify(plugin_manager.get_results())
#         
#     @app.route('/api/logs')
#     def api_logs():
#         """API endpoint for application logs."""
#         try:
#             with open(app.config['NETPROBE_CONFIG'].get('logging.file'), 'r') as f:
#                 logs = f.readlines()
#             return jsonify(logs)
#         except Exception as e:
#             return jsonify({"error": str(e)}), 500
#             
#     # Socket.IO event handlers
#     @socketio.on('connect')
#     def socket_connect():
#         """Handle client connection."""
#         emit('status', {'connected': True})
#         
#     @socketio.on('disconnect')
#     def socket_disconnect():
#         """Handle client disconnection."""
#         pass
#         
#     @socketio.on('run_plugin')
#     def socket_run_plugin(data):
#         """Run a plugin via Socket.IO.
#         
#         Args:
#             data: Dictionary containing plugin_id and parameters.
#         """
#         plugin_id = data.get('plugin_id')
#         params = data.get('params', {})
#         
#         if not plugin_id:
#             emit('error', {'message': 'Missing plugin_id'})
# 
#         try:
#             result = plugin_manager.run_plugin(plugin_id, **params)
#             emit('plugin_result', {'plugin_id': plugin_id, 'result': result})
#         except Exception as e:
#             emit('error', {'message': str(e)})
