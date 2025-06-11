"""
API routes for the NetScout-Pi-V2 application.
"""

import logging
from flask import Blueprint, jsonify, request, current_app
from app.plugins.manager import get_plugin_manager
from app.utils import system, network

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

@api_bp.route('/plugins', methods=['GET'])
def list_plugins():
    """
    List all available plugins.
    
    Returns:
        JSON response with a list of all available plugins.
    """
    plugin_manager = get_plugin_manager()
    plugins = plugin_manager.get_all_plugins()
    return jsonify({'plugins': plugins})

@api_bp.route('/plugins/<plugin_id>', methods=['GET'])
def get_plugin(plugin_id):
    """
    Get information about a specific plugin.
    
    Args:
        plugin_id (str): The ID of the plugin to get information about.
        
    Returns:
        JSON response with information about the plugin.
    """
    plugin_manager = get_plugin_manager()
    plugin = plugin_manager.get_plugin(plugin_id)
    
    if plugin:
        return jsonify({'plugin': plugin})
    return jsonify({'error': f'Plugin {plugin_id} not found'}), 404

@api_bp.route('/plugins/<plugin_id>/execute', methods=['POST'])
def execute_plugin(plugin_id):
    """
    Execute a plugin with the provided parameters.
    
    Args:
        plugin_id (str): The ID of the plugin to execute.
        
    Returns:
        JSON response with the result of the plugin execution.
    """
    plugin_manager = get_plugin_manager()
    params = request.json or {}
    
    try:
        result = plugin_manager.execute_plugin(plugin_id, params)
        return jsonify({'result': result})
    except Exception as e:
        logger.error(f"Error executing plugin {plugin_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/plugins', methods=['POST'])
def install_plugin():
    """
    Install a new plugin from an uploaded file.
    
    Returns:
        JSON response with the result of the plugin installation.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    plugin_manager = get_plugin_manager()
    
    try:
        plugin_id = plugin_manager.install_plugin(file)
        return jsonify({'success': True, 'plugin_id': plugin_id})
    except Exception as e:
        logger.error(f"Error installing plugin: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/plugins/<plugin_id>', methods=['DELETE'])
def uninstall_plugin(plugin_id):
    """
    Uninstall a plugin.
    
    Args:
        plugin_id (str): The ID of the plugin to uninstall.
        
    Returns:
        JSON response with the result of the plugin uninstallation.
    """
    plugin_manager = get_plugin_manager()
    
    try:
        plugin_manager.uninstall_plugin(plugin_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error uninstalling plugin {plugin_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/system/info', methods=['GET'])
def get_system_info():
    """
    Get system information.
    
    Returns:
        JSON response with system information.
    """
    try:
        info = system.get_system_info()
        return jsonify({'system_info': info})
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/system/network', methods=['GET'])
def get_network_info():
    """
    Get network information.
    
    Returns:
        JSON response with network information.
    """
    try:
        usage = system.get_network_usage()
        ethernet = system.get_ethernet_info()
        active = system.get_active_connections()
        
        return jsonify({
            'network_usage': usage,
            'ethernet_info': ethernet,
            'active_connections': active
        })
    except Exception as e:
        logger.error(f"Error getting network info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/network/scan', methods=['POST'])
def scan_network():
    """
    Scan the network for devices.
    
    Returns:
        JSON response with scan results.
    """
    try:
        data = request.json or {}
        subnet = data.get('subnet', '192.168.1.0/24')
        timeout = float(data.get('timeout', 1.0))
        quick = bool(data.get('quick', True))
        
        results = network.scan_network(subnet, timeout, quick)
        return jsonify({'scan_results': results})
    except Exception as e:
        logger.error(f"Error scanning network: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/network/ping', methods=['POST'])
def ping_host():
    """
    Ping a host.
    
    Returns:
        JSON response with ping results.
    """
    try:
        data = request.json or {}
        host = data.get('host')
        timeout = float(data.get('timeout', 1.0))
        
        if not host:
            return jsonify({'error': 'No host provided'}), 400
            
        result = network.ping(host, timeout)
        return jsonify({'ping_result': result})
    except Exception as e:
        logger.error(f"Error pinging host: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/test', methods=['GET'])
def test_endpoint():
    """
    A simple test endpoint to verify the API is working.
    
    Returns:
        JSON response with a success message.
    """
    logger.info("Test endpoint accessed")
    return jsonify({'status': 'ok', 'message': 'API is working!'})

@api_bp.route('/test_plugin/<plugin_id>', methods=['GET'])
def test_plugin(plugin_id):
    """
    Test execution of a plugin with default parameters.
    
    Args:
        plugin_id (str): The ID of the plugin to test.
        
    Returns:
        JSON response with the result of the plugin execution.
    """
    logger.info(f"Testing plugin {plugin_id}")
    plugin_manager = get_plugin_manager()
    
    if plugin_id not in plugin_manager.plugins:
        return jsonify({'error': f'Plugin {plugin_id} not found'}), 404
        
    try:
        # Use default parameters
        params = {}
        for param in plugin_manager.plugins[plugin_id]['manifest'].get('parameters', []):
            if 'default' in param:
                params[param['name']] = param['default']
        
        logger.info(f"Executing plugin {plugin_id} with params: {params}")
        result = plugin_manager.execute_plugin(plugin_id, params)
        return jsonify({'result': result})
    except Exception as e:
        logger.error(f"Error testing plugin {plugin_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500
