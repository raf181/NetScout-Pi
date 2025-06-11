"""
Dashboard routes for the NetScout-Pi-V2 application.
"""

import os
import logging
from flask import Blueprint, render_template, current_app, jsonify, send_from_directory
from app.plugins.manager import get_plugin_manager
from app.utils import system, network
from flask_socketio import emit
from app import socketio
import json
import time
import threading

# Create dashboard blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')
logger = logging.getLogger(__name__)

# Background thread for system monitoring
monitor_thread = None
thread_stop_event = threading.Event()

def background_monitor():
    """
    Background thread for monitoring system stats and emitting to clients.
    """
    while not thread_stop_event.is_set():
        try:
            # Get system info
            sys_info = system.get_system_info()
            net_usage = system.get_network_usage()
            
            # Emit to connected clients
            socketio.emit('system_update', {
                'timestamp': time.time(),
                'system': sys_info,
                'network': net_usage
            })
            
            # Sleep for 5 seconds
            time.sleep(5)
        except Exception as e:
            logger.error(f"Error in monitoring thread: {str(e)}")
            time.sleep(10)  # Sleep longer on error

@dashboard_bp.route('/')
def index():
    """
    Render the main dashboard page.
    
    Returns:
        Rendered template for the main dashboard.
    """
    return render_template('dashboard.html')

@dashboard_bp.route('/plugins/<plugin_id>/ui')
def plugin_ui(plugin_id):
    """
    Render the UI for a specific plugin.
    
    Args:
        plugin_id (str): The ID of the plugin to render the UI for.
        
    Returns:
        Rendered template for the plugin UI.
    """
    plugin_manager = get_plugin_manager()
    plugin = plugin_manager.get_plugin(plugin_id)
    
    if not plugin:
        return render_template('error.html', message=f"Plugin {plugin_id} not found")
        
    return render_template('plugin.html', plugin=plugin)

@dashboard_bp.route('/plugins/<plugin_id>/static/<path:filename>')
def plugin_static(plugin_id, filename):
    """
    Serve static files for a specific plugin.
    
    Args:
        plugin_id (str): The ID of the plugin to serve static files for.
        filename (str): The name of the static file to serve.
        
    Returns:
        Static file from the plugin directory.
    """
    plugin_folder = current_app.config['PLUGIN_FOLDER']
    plugin_static_folder = os.path.join(plugin_folder, plugin_id, 'static')
    return send_from_directory(plugin_static_folder, filename)

@dashboard_bp.route('/system/stats')
def system_stats():
    """
    Get system statistics for the dashboard.
    
    Returns:
        Rendered template for system statistics.
    """
    return render_template('system.html')

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """
    Handle a new socket connection.
    """
    logger.info("Client connected")
    
    # Start the background monitor thread if not running
    global monitor_thread
    if monitor_thread is None or not monitor_thread.is_alive():
        thread_stop_event.clear()
        monitor_thread = threading.Thread(target=background_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        logger.info("Started monitoring thread")
    
    # Send initial system info
    try:
        sys_info = system.get_system_info()
        net_usage = system.get_network_usage()
        
        emit('system_update', {
            'timestamp': time.time(),
            'system': sys_info,
            'network': net_usage
        })
    except Exception as e:
        logger.error(f"Error sending initial system info: {str(e)}")

@socketio.on('disconnect')
def handle_disconnect():
    """
    Handle a socket disconnect.
    """
    logger.info("Client disconnected")
    
    # If no clients, stop the monitoring thread
    if not socketio.server.eio.sockets:
        thread_stop_event.set()
        logger.info("Stopped monitoring thread - no clients connected")

@socketio.on('execute_plugin')
def handle_execute_plugin(data):
    """
    Handle a plugin execution request from the client.
    
    Args:
        data (dict): The plugin execution request data.
    """
    plugin_id = data.get('plugin_id')
    params = data.get('params', {})
    
    if not plugin_id:
        emit('plugin_error', {'error': 'No plugin ID provided'})
        return
        
    try:
        plugin_manager = get_plugin_manager()
        result = plugin_manager.execute_plugin(plugin_id, params)
        emit('plugin_result', {
            'plugin_id': plugin_id,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error executing plugin {plugin_id}: {str(e)}")
        emit('plugin_error', {
            'plugin_id': plugin_id,
            'error': str(e)
        })
