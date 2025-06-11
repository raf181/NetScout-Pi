/**
 * Dashboard JavaScript functionality for NetScout Pi
 */

// Initialize Socket.IO connection with explicit transport configuration
const socket = io({
    transports: ['polling', 'websocket'],  // Try polling first, then websocket
    reconnectionAttempts: 10,              // Increase reconnection attempts
    reconnectionDelay: 1000,
    timeout: 30000,                        // Increase timeout
    forceNew: true,                        // Force new connection
    autoConnect: true                      // Auto connect on initialization
});

// DOM Elements
const pluginsList = document.getElementById('plugins-list');
const noPluginsMessage = document.getElementById('no-plugins-message');
const pluginOutputSection = document.getElementById('plugin-output-section');
const pluginOutput = document.getElementById('plugin-output');
const currentPluginName = document.getElementById('current-plugin-name');
const closePluginOutput = document.getElementById('close-plugin-output');
const uploadPluginForm = document.getElementById('upload-plugin-form');
const uploadPluginBtn = document.getElementById('upload-plugin-btn');
const pluginFile = document.getElementById('plugin-file');
const pluginDetailsModal = new bootstrap.Modal(document.getElementById('pluginDetailsModal'));
const pluginDetailsTitle = document.getElementById('plugin-details-title');
const pluginDetailsContent = document.getElementById('plugin-details-content');
const uninstallPluginBtn = document.getElementById('uninstall-plugin-btn');
const runPluginBtn = document.getElementById('run-plugin-btn');
const settingsForm = document.getElementById('settings-form');
const refreshRateInput = document.getElementById('refresh-rate');

// Store current plugin ID
let currentPluginId = null;

// Load plugins on page load
document.addEventListener('DOMContentLoaded', () => {
    loadPlugins();
    loadSettings();
    
    // Event listeners
    uploadPluginBtn.addEventListener('click', uploadPlugin);
    closePluginOutput.addEventListener('click', hidePluginOutput);
    uninstallPluginBtn.addEventListener('click', uninstallCurrentPlugin);
    runPluginBtn.addEventListener('click', runCurrentPlugin);
    settingsForm.addEventListener('submit', saveSettings);
});

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    updateSystemStatus('Connected');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateSystemStatus('Disconnected');
    
    // Show reconnection message
    displayAlert('Connection to server lost. Attempting to reconnect...', 'warning');
    
    // Try to reconnect after 3 seconds
    setTimeout(() => {
        if (!socket.connected) {
            // Force a refresh after 10 seconds if still not connected
            displayAlert('Reconnection failed. The page will refresh in 10 seconds...', 'danger');
            setTimeout(() => {
                window.location.reload();
            }, 10000);
        }
    }, 3000);
});

socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    displayAlert('Error connecting to server: ' + error.message, 'danger');
});

socket.on('plugin_pending', (data) => {
    console.log('Plugin execution started:', data);
    if (data.plugin_id === currentPluginId) {
        // Show loading indicator with a timestamp
        const loadingMessage = `Executing plugin... (started at ${new Date().toLocaleTimeString()})`;
        displayPluginOutput({ type: 'loading', message: loadingMessage });
    }
});

socket.on('plugin_result', (data) => {
    console.log('Received plugin result:', data);
    if (data.plugin_id === currentPluginId) {
        // Add timestamp to the result display
        const timestamp = data.timestamp ? new Date(data.timestamp * 1000).toLocaleTimeString() : new Date().toLocaleTimeString();
        
        // If result has an error property, display it as an error
        if (data.result && data.result.error) {
            displayPluginError(data.result.error);
        } else {
            const resultWithTime = { 
                ...data.result,
                _executionTime: timestamp
            };
            displayPluginOutput(resultWithTime);
        }
    }
});

socket.on('plugin_error', (data) => {
    console.error('Plugin error:', data);
    if (data.plugin_id === currentPluginId) {
        // Add timestamp to the error display
        const timestamp = data.timestamp ? new Date(data.timestamp * 1000).toLocaleTimeString() : new Date().toLocaleTimeString();
        const errorWithTime = `Error at ${timestamp}: ${data.error}`;
        displayPluginError(errorWithTime);
    }
});

/**
 * Load all installed plugins
 */
function loadPlugins() {
    fetch('/api/plugins')
        .then(response => response.json())
        .then(data => {
            if (data.plugins && data.plugins.length > 0) {
                displayPlugins(data.plugins);
                noPluginsMessage.classList.add('d-none');
            } else {
                pluginsList.innerHTML = '';
                noPluginsMessage.classList.remove('d-none');
            }
        })
        .catch(error => {
            console.error('Error loading plugins:', error);
            displayError('Failed to load plugins. Please try again later.');
        });
}

/**
 * Display plugins in the dashboard
 * @param {Array} plugins - List of plugin objects
 */
function displayPlugins(plugins) {
    pluginsList.innerHTML = '';
    
    plugins.forEach(plugin => {
        const pluginCard = document.createElement('div');
        pluginCard.className = 'col-md-4 mb-4';
        pluginCard.innerHTML = `
            <div class="card plugin-card h-100" data-plugin-id="${plugin.id}">
                <div class="card-body text-center">
                    <div class="plugin-icon">
                        <i class="bi bi-puzzle"></i>
                    </div>
                    <h5 class="card-title">${plugin.name}</h5>
                    <p class="card-text">${plugin.description}</p>
                    <div class="text-muted small">Version ${plugin.version}</div>
                </div>
                <div class="card-footer bg-transparent">
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">By ${plugin.author}</small>
                        <button class="btn btn-sm btn-primary run-plugin" data-plugin-id="${plugin.id}">Run</button>
                    </div>
                </div>
            </div>
        `;
        
        pluginsList.appendChild(pluginCard);
        
        // Add click event to the card
        pluginCard.querySelector('.plugin-card').addEventListener('click', (e) => {
            if (!e.target.classList.contains('run-plugin')) {
                showPluginDetails(plugin.id);
            }
        });
        
        // Add click event to the run button
        pluginCard.querySelector('.run-plugin').addEventListener('click', (e) => {
            e.stopPropagation();
            executePlugin(plugin.id, {});
        });
    });
}

/**
 * Show plugin details in modal
 * @param {string} pluginId - The ID of the plugin to show details for
 */
function showPluginDetails(pluginId) {
    fetch(`/api/plugins/${pluginId}`)
        .then(response => response.json())
        .then(data => {
            if (data.plugin) {
                const plugin = data.plugin;
                currentPluginId = plugin.id;
                
                pluginDetailsTitle.textContent = plugin.name;
                
                let parametersHtml = '';
                if (plugin.parameters && plugin.parameters.length > 0) {
                    parametersHtml = '<h6>Parameters:</h6><ul>';
                    plugin.parameters.forEach(param => {
                        parametersHtml += `<li><strong>${param.name}</strong>: ${param.description || 'No description'}</li>`;
                    });
                    parametersHtml += '</ul>';
                }
                
                pluginDetailsContent.innerHTML = `
                    <p>${plugin.description}</p>
                    <p><strong>Version:</strong> ${plugin.version}</p>
                    <p><strong>Author:</strong> ${plugin.author}</p>
                    ${plugin.homepage ? `<p><strong>Homepage:</strong> <a href="${plugin.homepage}" target="_blank">${plugin.homepage}</a></p>` : ''}
                    ${parametersHtml}
                    ${plugin.has_ui ? '<p><a href="/plugins/' + plugin.id + '/ui" class="btn btn-sm btn-outline-primary">Open Plugin UI</a></p>' : ''}
                `;
                
                pluginDetailsModal.show();
            } else {
                displayError('Failed to load plugin details.');
            }
        })
        .catch(error => {
            console.error('Error loading plugin details:', error);
            displayError('Failed to load plugin details. Please try again later.');
        });
}

/**
 * Execute a plugin with parameters
 * @param {string} pluginId - The ID of the plugin to execute
 * @param {Object} params - The parameters to pass to the plugin
 */
function executePlugin(pluginId, params = {}) {
    // Hide modal if it's open
    pluginDetailsModal.hide();
    
    // Set current plugin ID and show output section
    currentPluginId = pluginId;
    
    // Get plugin name
    fetch(`/api/plugins/${pluginId}`)
        .then(response => response.json())
        .then(data => {
            if (data.plugin) {
                currentPluginName.textContent = data.plugin.name;
                showPluginOutput();
                
                // Clear previous output
                pluginOutput.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Running plugin...</p></div>';
                
                // Execute plugin via Socket.IO
                socket.emit('execute_plugin', {
                    plugin_id: pluginId,
                    params: params
                });
            }
        })
        .catch(error => {
            console.error('Error getting plugin details:', error);
            displayError('Failed to execute plugin. Please try again later.');
        });
}

/**
 * Display plugin output
 * @param {*} result - The result from the plugin execution
 */
/**
 * Display plugin execution output
 * @param {object|string} result - The plugin execution result
 */
function displayPluginOutput(result) {
    // Show plugin output section if hidden
    showPluginOutput();
    
    // Convert result to formatted HTML
    let outputHtml = '';
    
    if (result && result.type === 'loading') {
        // Display loading indicator
        outputHtml = `
            <div class="d-flex align-items-center">
                <div class="spinner-border text-primary me-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mb-0">${result.message || 'Executing plugin...'}</p>
            </div>
        `;
    } else if (result && result.type === 'table' && Array.isArray(result.data)) {
        // Format table data
        outputHtml = '<div class="table-responsive mt-3"><table class="table table-striped table-hover">';
        
        // Add execution time if available
        if (result._executionTime) {
            outputHtml += `<caption>Results from scan completed at ${result._executionTime}</caption>`;
        }
        
        // Add headers
        if (Array.isArray(result.headers) && result.headers.length > 0) {
            outputHtml += '<thead><tr>';
            for (const header of result.headers) {
                outputHtml += `<th>${header}</th>`;
            }
            outputHtml += '</tr></thead>';
        }
        
        // Add rows
        outputHtml += '<tbody>';
        for (const row of result.data) {
            outputHtml += '<tr>';
            if (Array.isArray(row)) {
                for (const cell of row) {
                    outputHtml += `<td>${cell}</td>`;
                }
            } else if (typeof row === 'object') {
                for (const key in row) {
                    outputHtml += `<td>${row[key]}</td>`;
                }
            }
            outputHtml += '</tr>';
        }
        outputHtml += '</tbody></table></div>';
        
        // Add summary if available
        if (result.subnet) {
            outputHtml += `
                <div class="alert alert-info mt-3">
                    <p><strong>Subnet:</strong> ${result.subnet}</p>
                    <p><strong>Hosts Found:</strong> ${result.hosts_found}</p>
                    <p><strong>Scan Time:</strong> ${result.scan_time} seconds</p>
                </div>
            `;
        }
    } else if (typeof result === 'object') {
        // Add execution time if available
        let timeInfo = '';
        if (result._executionTime) {
            timeInfo = `<div class="alert alert-info mb-3">Results from execution at ${result._executionTime}</div>`;
        }
        
        // Handle JSON objects
        outputHtml = `${timeInfo}<pre class="code-block">${JSON.stringify(result, null, 2)}</pre>`;
    } else if (typeof result === 'string') {
        // Handle strings
        if (result.startsWith('<')) {
            // Likely HTML content
            outputHtml = result;
        } else {
            // Regular text
            outputHtml = `<p>${result}</p>`;
        }
    } else {
        // Handle other types
        outputHtml = `<p>${result}</p>`;
    }
    
    pluginOutput.innerHTML = outputHtml;
}

/**
 * Display plugin execution error
 * @param {string} error - The error message
 */
function displayPluginError(error) {
    // Show plugin output section if hidden
    showPluginOutput();
    
    pluginOutput.innerHTML = `
        <div class="alert alert-danger" role="alert">
            <h5>Error:</h5>
            <p>${error}</p>
        </div>
        <div class="alert alert-info" role="alert">
            <p><strong>Troubleshooting Tips:</strong></p>
            <ul>
                <li>Check if the plugin is correctly installed</li>
                <li>Verify that your network settings are correct</li>
                <li>Try restarting the server if issues persist</li>
            </ul>
        </div>
    `;
}

/**
 * Show the plugin output section
 */
function showPluginOutput() {
    // Show plugin output section
    pluginOutputSection.classList.remove('d-none');
}

/**
 * Show the plugin output section
 */
function showPluginOutput() {
    pluginOutputSection.classList.remove('d-none');
}

/**
 * Hide the plugin output section
 */
function hidePluginOutput() {
    pluginOutputSection.classList.add('d-none');
    currentPluginId = null;
}

/**
 * Upload a new plugin
 */
function uploadPlugin() {
    if (!pluginFile.files[0]) {
        displayError('Please select a file to upload.');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', pluginFile.files[0]);
    
    // Show loading state
    uploadPluginBtn.disabled = true;
    uploadPluginBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...';
    
    fetch('/api/plugins', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // Reset button
        uploadPluginBtn.disabled = false;
        uploadPluginBtn.textContent = 'Upload';
        
        if (data.success) {
            // Hide modal and reset form
            const modal = bootstrap.Modal.getInstance(document.getElementById('uploadPluginModal'));
            modal.hide();
            uploadPluginForm.reset();
            
            // Reload plugins
            loadPlugins();
            
            // Show success message
            displayAlert('Plugin uploaded successfully!', 'success');
        } else {
            displayError(data.error || 'Failed to upload plugin.');
        }
    })
    .catch(error => {
        console.error('Error uploading plugin:', error);
        
        // Reset button
        uploadPluginBtn.disabled = false;
        uploadPluginBtn.textContent = 'Upload';
        
        displayError('Failed to upload plugin. Please try again later.');
    });
}

/**
 * Uninstall the current plugin
 */
function uninstallCurrentPlugin() {
    if (!currentPluginId) return;
    
    if (!confirm('Are you sure you want to uninstall this plugin? This action cannot be undone.')) {
        return;
    }
    
    fetch(`/api/plugins/${currentPluginId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Hide modal
            pluginDetailsModal.hide();
            
            // Reload plugins
            loadPlugins();
            
            // Show success message
            displayAlert('Plugin uninstalled successfully!', 'success');
        } else {
            displayError(data.error || 'Failed to uninstall plugin.');
        }
    })
    .catch(error => {
        console.error('Error uninstalling plugin:', error);
        displayError('Failed to uninstall plugin. Please try again later.');
    });
}

/**
 * Run the current plugin from the modal
 */
function runCurrentPlugin() {
    if (!currentPluginId) return;
    
    // Hide modal
    pluginDetailsModal.hide();
    
    // Execute plugin
    executePlugin(currentPluginId, {});
}

/**
 * Load user settings
 */
function loadSettings() {
    // Load settings from localStorage
    const settings = JSON.parse(localStorage.getItem('netscout_settings') || '{}');
    
    // Apply settings
    if (settings.refreshRate) {
        refreshRateInput.value = settings.refreshRate;
    }
}

/**
 * Save user settings
 * @param {Event} e - Form submit event
 */
function saveSettings(e) {
    e.preventDefault();
    
    const settings = {
        refreshRate: parseInt(refreshRateInput.value, 10) || 10
    };
    
    // Save settings to localStorage
    localStorage.setItem('netscout_settings', JSON.stringify(settings));
    
    // Show success message
    displayAlert('Settings saved successfully!', 'success');
}

/**
 * Update system status indicator
 * @param {string} status - The system status
 */
function updateSystemStatus(status) {
    const statusElement = document.getElementById('system-status');
    
    if (status === 'Connected') {
        statusElement.textContent = 'Running';
        statusElement.className = 'text-success';
    } else {
        statusElement.textContent = 'Disconnected';
        statusElement.className = 'text-danger';
    }
}

/**
 * Display an error message
 * @param {string} message - The error message to display
 */
function displayError(message) {
    displayAlert(message, 'danger');
}

/**
 * Display an alert message
 * @param {string} message - The message to display
 * @param {string} type - The type of alert (success, danger, warning, info)
 */
function displayAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed bottom-0 end-0 m-3`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Add to document
    document.body.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
    }, 5000);
}
