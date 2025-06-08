#!/usr/bin/env python3
# NetProbe Pi - Logging System

import os
import sys
import logging
import logging.handlers
from pathlib import Path
import json
import uuid
import time
import shutil
import gzip
from datetime import datetime, timedelta
import traceback

# Constants
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOG_DIR = '/var/log/netprobe'
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_LOG_BACKUPS = 5
MAX_RESULTS_STORED = 100
LOG_ROTATION_INTERVAL = 24  # hours

def setup_logging(log_dir=None, log_level=logging.INFO, debug=False, file_logging=True):
    """Configure logging system.
    
    Args:
        log_dir (str, optional): Directory for log files. Defaults to DEFAULT_LOG_DIR.
        log_level (int, optional): Logging level. Defaults to logging.INFO.
        debug (bool, optional): Enable debug mode. Defaults to False.
        file_logging (bool, optional): Enable file logging. Defaults to True.
    """
    if debug:
        log_level = logging.DEBUG
    
    log_dir = log_dir or DEFAULT_LOG_DIR
    
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Add file handlers if file logging is enabled
    if file_logging:
        # Main log file with rotation
        log_file = os.path.join(log_dir, 'netprobe.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=MAX_LOG_SIZE, backupCount=MAX_LOG_BACKUPS)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
        
        # Error log file with rotation
        error_log = os.path.join(log_dir, 'error.log')
        error_handler = logging.handlers.RotatingFileHandler(
            error_log, maxBytes=MAX_LOG_SIZE, backupCount=MAX_LOG_BACKUPS)
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
        
    # Log startup message
    root_logger.info("Logging system initialized")
    if debug:
        root_logger.info("Debug logging enabled")
        
    return root_logger


class PluginLogger:
    """Logger for plugin execution and results."""
    
    def __init__(self, plugin_name, log_dir=None):
        """Initialize plugin logger.
        
        Args:
            plugin_name (str): Name of the plugin.
            log_dir (str, optional): Directory for log files. Defaults to None.
        """
        self.plugin_name = plugin_name
        
        # Set log directory
        base_log_dir = log_dir or DEFAULT_LOG_DIR
        self.log_dir = os.path.join(base_log_dir, plugin_name)
        
        # Create directories
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(os.path.join(self.log_dir, 'results'), exist_ok=True)
        os.makedirs(os.path.join(self.log_dir, 'errors'), exist_ok=True)
        
        # Initialize logger
        self.logger = logging.getLogger(f"plugin.{plugin_name}")
        
        # Setup plugin log file
        log_file = os.path.join(self.log_dir, f"{plugin_name}.log")
        if not any(isinstance(h, logging.FileHandler) for h in self.logger.handlers):
            handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=MAX_LOG_SIZE, backupCount=MAX_LOG_BACKUPS)
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            self.logger.addHandler(handler)
        
        # Current run info
        self.current_run_id = None
        self.run_start_time = None
        self.log_buffer = []
    
    def start_run(self):
        """Start a new plugin run.
        
        Returns:
            str: Run ID.
        """
        self.current_run_id = str(uuid.uuid4())
        self.run_start_time = time.time()
        self.log_buffer = []
        
        self.logger.info(f"Starting plugin run: {self.current_run_id}")
        return self.current_run_id
    
    def end_run(self):
        """End the current plugin run."""
        if self.current_run_id:
            duration = time.time() - self.run_start_time if self.run_start_time else 0
            self.logger.info(f"Ended plugin run: {self.current_run_id}, duration: {duration:.2f}s")
            
            # Write buffered logs to run-specific log file
            run_log_file = os.path.join(self.log_dir, 'runs', f"{self.current_run_id}.log")
            os.makedirs(os.path.dirname(run_log_file), exist_ok=True)
            
            with open(run_log_file, 'w') as f:
                for entry in self.log_buffer:
                    f.write(f"{entry}\n")
            
            self.current_run_id = None
            self.run_start_time = None
            self.log_buffer = []
    
    def log(self, message, level='INFO'):
        """Log a message.
        
        Args:
            message (str): Message to log.
            level (str, optional): Log level. Defaults to 'INFO'.
        """
        # Get current timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Format message
        formatted_message = f"{timestamp} - {level} - {message}"
        
        # Buffer message if this is part of a run
        if self.current_run_id:
            self.log_buffer.append(formatted_message)
        
        # Log with appropriate level
        if level == 'DEBUG':
            self.logger.debug(message)
        elif level == 'INFO':
            self.logger.info(message)
        elif level == 'WARNING':
            self.logger.warning(message)
        elif level == 'ERROR':
            self.logger.error(message)
        elif level == 'CRITICAL':
            self.logger.critical(message)
        else:
            self.logger.info(message)
    
    def save_result(self, result):
        """Save plugin result.
        
        Args:
            result: Result to save.
            
        Returns:
            str: Path to saved result file.
        """
        if not self.current_run_id:
            self.current_run_id = str(uuid.uuid4())
            
        try:
            # Create timestamp
            timestamp = self.get_timestamp()
            
            # Add metadata to result if it's a dict
            if isinstance(result, dict):
                result['run_id'] = self.current_run_id
                result['timestamp'] = timestamp
                result['plugin_name'] = self.plugin_name
                
                # Add execution time if not present
                if 'execution_time' not in result and self.run_start_time:
                    result['execution_time'] = time.time() - self.run_start_time
            
            # Create result file
            result_file = os.path.join(
                self.log_dir, 'results', 
                f"{self.plugin_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
                
            # Maintain index of results
            self._update_result_index(result_file, result)
            
            # Clean up old results
            self._cleanup_old_results()
            
            return result_file
            
        except Exception as e:
            self.logger.error(f"Error saving result: {str(e)}")
            self.save_error(f"Error saving result: {str(e)}")
            return None
    
    def save_error(self, error_message):
        """Save error message.
        
        Args:
            error_message (str): Error message to save.
            
        Returns:
            str: Path to saved error file.
        """
        try:
            # Create timestamp
            timestamp = self.get_timestamp()
            
            # Get stack trace
            stack_trace = traceback.format_exc()
            
            # Create error data
            error_data = {
                'run_id': self.current_run_id or str(uuid.uuid4()),
                'timestamp': timestamp,
                'plugin_name': self.plugin_name,
                'error': error_message,
                'stack_trace': stack_trace if stack_trace != 'NoneType: None\n' else None
            }
            
            # Create error file
            error_file = os.path.join(
                self.log_dir, 'errors', 
                f"{self.plugin_name}_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            with open(error_file, 'w') as f:
                json.dump(error_data, f, indent=2)
                
            return error_file
            
        except Exception as e:
            self.logger.error(f"Error saving error message: {str(e)}")
            return None
    
    def get_result(self, run_id):
        """Get result by run ID.
        
        Args:
            run_id (str): Run ID.
            
        Returns:
            dict: Result or None if not found.
        """
        try:
            # Check index file
            index_file = os.path.join(self.log_dir, 'results', 'index.json')
            
            if not os.path.exists(index_file):
                return None
                
            with open(index_file, 'r') as f:
                index = json.load(f)
                
            # Find result file for this run ID
            for entry in index:
                if entry.get('run_id') == run_id:
                    result_file = entry.get('file')
                    
                    if result_file and os.path.exists(result_file):
                        with open(result_file, 'r') as f:
                            return json.load(f)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting result: {str(e)}")
            return None
    
    def get_results(self, limit=MAX_RESULTS_STORED):
        """Get recent results.
        
        Args:
            limit (int, optional): Maximum number of results to return.
            
        Returns:
            list: List of results.
        """
        try:
            # Check index file
            index_file = os.path.join(self.log_dir, 'results', 'index.json')
            
            if not os.path.exists(index_file):
                return []
                
            with open(index_file, 'r') as f:
                index = json.load(f)
                
            # Sort by timestamp (newest first)
            index.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Limit number of results
            index = index[:limit]
            
            # Load result files
            results = []
            for entry in index:
                result_file = entry.get('file')
                
                if result_file and os.path.exists(result_file):
                    try:
                        with open(result_file, 'r') as f:
                            results.append(json.load(f))
                    except Exception as e:
                        self.logger.error(f"Error loading result file {result_file}: {str(e)}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting results: {str(e)}")
            return []
    
    def get_timestamp(self):
        """Get current timestamp.
        
        Returns:
            str: ISO format timestamp.
        """
        return datetime.now().isoformat()
    
    def _update_result_index(self, result_file, result):
        """Update result index.
        
        Args:
            result_file (str): Path to result file.
            result: Result data.
        """
        try:
            index_file = os.path.join(self.log_dir, 'results', 'index.json')
            
            # Load existing index
            index = []
            if os.path.exists(index_file):
                try:
                    with open(index_file, 'r') as f:
                        index = json.load(f)
                except Exception:
                    # If index is corrupted, start fresh
                    index = []
            
            # Extract key information
            run_id = result.get('run_id') if isinstance(result, dict) else self.current_run_id or str(uuid.uuid4())
            timestamp = result.get('timestamp') if isinstance(result, dict) else self.get_timestamp()
            
            # Add new entry
            index.append({
                'run_id': run_id,
                'timestamp': timestamp,
                'file': result_file
            })
            
            # Sort by timestamp (newest first)
            index.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Limit index size
            if len(index) > MAX_RESULTS_STORED:
                index = index[:MAX_RESULTS_STORED]
                
            # Save updated index
            with open(index_file, 'w') as f:
                json.dump(index, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error updating result index: {str(e)}")
    
    def _cleanup_old_results(self):
        """Clean up old result files."""
        try:
            # Get all result files
            results_dir = os.path.join(self.log_dir, 'results')
            result_files = [os.path.join(results_dir, f) for f in os.listdir(results_dir) 
                           if os.path.isfile(os.path.join(results_dir, f)) and f.endswith('.json') and f != 'index.json']
            
            # Sort by modification time (oldest first)
            result_files.sort(key=lambda x: os.path.getmtime(x))
            
            # Remove excess files
            if len(result_files) > MAX_RESULTS_STORED:
                for old_file in result_files[:-MAX_RESULTS_STORED]:
                    try:
                        os.remove(old_file)
                    except Exception as e:
                        self.logger.error(f"Error removing old result file {old_file}: {str(e)}")
                        
        except Exception as e:
            self.logger.error(f"Error cleaning up old results: {str(e)}")


def rotate_logs(log_dir=None):
    """Rotate old log files.
    
    Args:
        log_dir (str, optional): Directory for log files. Defaults to DEFAULT_LOG_DIR.
    """
    log_dir = log_dir or DEFAULT_LOG_DIR
    
    try:
        # Find log files older than LOG_ROTATION_INTERVAL
        cutoff_time = datetime.now() - timedelta(hours=LOG_ROTATION_INTERVAL)
        
        for root, _, files in os.walk(log_dir):
            for file in files:
                if file.endswith('.log'):
                    file_path = os.path.join(root, file)
                    
                    # Check file modification time
                    mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if mtime < cutoff_time:
                        # Compress file
                        try:
                            with open(file_path, 'rb') as f_in:
                                with gzip.open(f"{file_path}.gz", 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                            
                            # Remove original file
                            os.remove(file_path)
                            
                        except Exception as e:
                            logging.error(f"Error compressing log file {file_path}: {str(e)}")
                            
    except Exception as e:
        logging.error(f"Error rotating logs: {str(e)}")


def export_logs(output_dir, log_dir=None, days=7):
    """Export logs to a ZIP file.
    
    Args:
        output_dir (str): Directory to save ZIP file.
        log_dir (str, optional): Directory for log files. Defaults to DEFAULT_LOG_DIR.
        days (int, optional): Number of days of logs to include. Defaults to 7.
        
    Returns:
        str: Path to ZIP file.
    """
    import zipfile
    from datetime import datetime, timedelta
    
    log_dir = log_dir or DEFAULT_LOG_DIR
    
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Create ZIP filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_file = os.path.join(output_dir, f"netprobe_logs_{timestamp}.zip")
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Create ZIP file
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through log directory
            for root, _, files in os.walk(log_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Check file modification time
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if mtime >= cutoff_date:
                            # Add file to ZIP with relative path
                            rel_path = os.path.relpath(file_path, start=os.path.dirname(log_dir))
                            zipf.write(file_path, rel_path)
                    except Exception as e:
                        logging.error(f"Error adding {file_path} to ZIP: {str(e)}")
        
        return zip_file
        
    except Exception as e:
        logging.error(f"Error exporting logs: {str(e)}")
        return None
