/**
 * Plugin Dashboard functionality for NetScout Pi
 * This file contains functions for the plugin dashboard section that embeds plugin UIs in iframes
 */

/**
 * Load all enabled plugins with UI components into the dashboard
 */
function loadPluginDashboards() {
    console.log("Loading plugin dashboards...");
    // Get the plugin dashboards container
    const pluginDashboardsContainer = document.getElementById('plugin-dashboards-container');
    const noPluginDashboardsMessage = document.getElementById('no-plugin-dashboards-message');
    
    if (!pluginDashboardsContainer) {
        console.error("Plugin dashboards container not found");
        return;
    }
    
    // Clear existing content
    pluginDashboardsContainer.innerHTML = '';
    let pluginsWithUICount = 0;
    
    // Show loading indicator
    pluginDashboardsContainer.innerHTML = '<div class="col-12 text-center py-3"><div class="spinner-border" role="status"></div><p>Loading plugin dashboards...</p></div>';
    
    // Get all plugins
    fetch('/api/plugins')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Clear loading indicator
            pluginDashboardsContainer.innerHTML = '';
            
            // Check if any plugins exist
            if (!data.plugins || data.plugins.length === 0) {
                noPluginDashboardsMessage.classList.remove('d-none');
                return;
            }
            
            // Process each plugin
            data.plugins.forEach(plugin => {
                // Get more details about the plugin to check if it has UI
                fetch(`/api/plugins/${plugin.id}`)
                    .then(response => response.json())
                    .then(pluginData => {
                        if (pluginData.plugin && pluginData.plugin.has_ui) {
                            // Create a card for this plugin
                            const pluginCard = document.createElement('div');
                            pluginCard.className = 'col-lg-6 col-xl-4 mb-4';
                            pluginCard.innerHTML = `
                                <div class="card plugin-dashboard-card" data-plugin-id="${plugin.id}">
                                    <div class="card-header d-flex justify-content-between align-items-center">
                                        <h5 class="mb-0">
                                            <button class="btn btn-link text-decoration-none" type="button" data-bs-toggle="collapse"
                                                data-bs-target="#plugin-dashboard-${plugin.id}" aria-expanded="true">
                                                ${plugin.name}
                                            </button>
                                        </h5>
                                        <div class="btn-group">
                                            <button class="btn btn-sm btn-outline-secondary refresh-plugin-ui" data-plugin-id="${plugin.id}">
                                                <i class="bi bi-arrow-clockwise"></i>
                                            </button>
                                            <button class="btn btn-sm btn-outline-primary run-plugin" data-plugin-id="${plugin.id}">
                                                <i class="bi bi-play-fill"></i> Run
                                            </button>
                                        </div>
                                    </div>
                                    <div id="plugin-dashboard-${plugin.id}" class="collapse show">
                                        <div class="card-body p-0">
                                            <div class="plugin-ui-container">
                                                <iframe src="/plugins/${plugin.id}/ui/content" 
                                                        class="plugin-iframe w-100" 
                                                        style="border: none; min-height: 300px;"
                                                        title="${plugin.name} Dashboard"
                                                        loading="lazy"
                                                        sandbox="allow-same-origin allow-scripts allow-forms"
                                                        data-plugin-id="${plugin.id}"></iframe>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `;
                            pluginDashboardsContainer.appendChild(pluginCard);
                            pluginsWithUICount++;
                            
                            // Add event listeners to the buttons
                            const refreshBtn = pluginCard.querySelector('.refresh-plugin-ui');
                            const runBtn = pluginCard.querySelector('.run-plugin');
                            
                            refreshBtn.addEventListener('click', (e) => {
                                e.preventDefault();
                                refreshPluginUI(plugin.id);
                            });
                            
                            runBtn.addEventListener('click', (e) => {
                                e.preventDefault();
                                runPlugin(plugin.id);
                            });
                        }
                        
                        // If no plugins with UI were found, show the message
                        if (pluginsWithUICount === 0) {
                            noPluginDashboardsMessage.classList.remove('d-none');
                        } else {
                            noPluginDashboardsMessage.classList.add('d-none');
                        }
                    });
            });
        })
        .catch(error => {
            console.error('Error loading plugin dashboards:', error);
            pluginDashboardsContainer.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-danger">
                        <strong>Error:</strong> Failed to load plugin dashboards. ${error.message}
                    </div>
                </div>
            `;
        });
}

/**
 * Refresh a specific plugin UI
 * @param {string} pluginId - The ID of the plugin to refresh
 */
function refreshPluginUI(pluginId) {
    // Find the iframe for this plugin
    const iframe = document.querySelector(`.plugin-iframe[data-plugin-id="${pluginId}"]`);
    if (iframe) {
        // Add a timestamp parameter to bust cache
        iframe.src = `/plugins/${pluginId}/ui/content?t=${Date.now()}`;
    }
}

/**
 * Run a specific plugin and update its UI
 * @param {string} pluginId - The ID of the plugin to run
 */
function runPlugin(pluginId) {
    console.log(`Running plugin: ${pluginId}`);
    // Show loading indicator
    const pluginCard = document.querySelector(`.plugin-dashboard-card[data-plugin-id="${pluginId}"]`);
    if (pluginCard) {
        const iframe = pluginCard.querySelector('.plugin-iframe');
        if (iframe) {
            // Create a loading overlay for the iframe
            const loadingOverlay = document.createElement('div');
            loadingOverlay.className = 'loading-overlay position-absolute top-0 start-0 w-100 h-100 bg-light bg-opacity-75 d-flex justify-content-center align-items-center';
            loadingOverlay.style.zIndex = '10';
            loadingOverlay.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border text-primary" role="status"></div>
                    <p class="mt-2">Running plugin...</p>
                </div>
            `;
            
            // Set the iframe container to position relative if it's not already
            const iframeContainer = iframe.parentNode;
            if (getComputedStyle(iframeContainer).position === 'static') {
                iframeContainer.style.position = 'relative';
            }
            
            // Add the overlay as a child of the iframe container
            iframeContainer.appendChild(loadingOverlay);
            iframe.style.opacity = '0.5';
            
            // Set a timeout to remove the overlay after a reasonable time if no response
            setTimeout(() => {
                if (iframeContainer.contains(loadingOverlay)) {
                    iframeContainer.removeChild(loadingOverlay);
                    iframe.style.opacity = '1';
                    // Show a toast or alert that the operation might be taking longer than expected
                    displayToast('Plugin execution is taking longer than expected. The results will appear when complete.', 'warning');
                }
            }, 30000); // 30 seconds timeout
        }
    }
    
    // Execute the plugin
    socket.emit('execute_plugin', {
        plugin_id: pluginId,
        params: {}
    });
    
    // After a slight delay, refresh the UI
    setTimeout(() => {
        refreshPluginUI(pluginId);
        
        // Remove the loading overlay
        const loadingOverlay = document.querySelector('.loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
            
            // Restore iframe opacity
            const iframe = document.querySelector(`.plugin-iframe[data-plugin-id="${pluginId}"]`);
            if (iframe) {
                iframe.style.opacity = '1';
            }
        }
    }, 3000);
}

/**
 * Display a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, warning, danger, info)
 */
function displayToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    
    // Create toast container if it doesn't exist
    if (!toastContainer) {
        const newToastContainer = document.createElement('div');
        newToastContainer.id = 'toast-container';
        newToastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        newToastContainer.style.zIndex = '11';
        document.body.appendChild(newToastContainer);
    }
    
    // Get the container (now it definitely exists)
    const container = document.getElementById('toast-container');
    
    // Create a unique ID for this toast
    const toastId = 'toast-' + Date.now();
    
    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    toastEl.id = toastId;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to container
    container.appendChild(toastEl);
    
    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 5000
    });
    toast.show();
    
    // Remove from DOM after hiding
    toastEl.addEventListener('hidden.bs.toast', () => {
        if (container.contains(toastEl)) {
            container.removeChild(toastEl);
        }
    });
}

// Initialize expand/collapse all functionality
document.addEventListener('DOMContentLoaded', () => {
    // Get the expand/collapse buttons
    const expandAllBtn = document.getElementById('expand-all-plugins');
    const collapseAllBtn = document.getElementById('collapse-all-plugins');
    const refreshDashboardBtn = document.getElementById('refresh-plugin-dashboard');
    
    // Add event listeners
    if (expandAllBtn) {
        expandAllBtn.addEventListener('click', () => {
            document.querySelectorAll('.plugin-dashboard-card .collapse').forEach(element => {
                const bsCollapse = new bootstrap.Collapse(element, { toggle: false });
                bsCollapse.show();
            });
        });
    }
    
    if (collapseAllBtn) {
        collapseAllBtn.addEventListener('click', () => {
            document.querySelectorAll('.plugin-dashboard-card .collapse').forEach(element => {
                const bsCollapse = new bootstrap.Collapse(element, { toggle: false });
                bsCollapse.hide();
            });
        });
    }
    
    if (refreshDashboardBtn) {
        refreshDashboardBtn.addEventListener('click', () => {
            loadPluginDashboards();
        });
    }
});

// Socket.IO event handlers for plugin execution
document.addEventListener('DOMContentLoaded', () => {
    // Listen for plugin execution events
    socket.on('plugin_result', (data) => {
        console.log('Plugin execution result:', data);
        
        if (data && data.plugin_id) {
            // Find the plugin iframe
            const iframe = document.querySelector(`.plugin-iframe[data-plugin-id="${data.plugin_id}"]`);
            if (iframe) {
                // Find and remove any loading overlay
                const iframeContainer = iframe.parentNode;
                const loadingOverlay = iframeContainer.querySelector('.loading-overlay');
                if (loadingOverlay) {
                    iframeContainer.removeChild(loadingOverlay);
                }
                
                // Restore iframe opacity
                iframe.style.opacity = '1';
                
                // Refresh the iframe to show updated content
                refreshPluginUI(data.plugin_id);
                
                // If there's an error, show it
                if (data.error) {
                    displayToast(`Plugin execution error: ${data.error}`, 'danger');
                } else {
                    displayToast('Plugin executed successfully!', 'success');
                }
            }
        }
    });
    
    socket.on('plugin_pending', (data) => {
        console.log('Plugin execution started:', data);
        // No need to add additional UI feedback here as runPlugin already does this
    });
    
    socket.on('plugin_error', (data) => {
        console.error('Plugin execution error:', data);
        
        if (data && data.plugin_id) {
            // Find the plugin iframe
            const iframe = document.querySelector(`.plugin-iframe[data-plugin-id="${data.plugin_id}"]`);
            if (iframe) {
                // Find and remove any loading overlay
                const iframeContainer = iframe.parentNode;
                const loadingOverlay = iframeContainer.querySelector('.loading-overlay');
                if (loadingOverlay) {
                    iframeContainer.removeChild(loadingOverlay);
                }
                
                // Restore iframe opacity
                iframe.style.opacity = '1';
                
                // Show error message
                displayToast(`Plugin execution error: ${data.error || 'Unknown error'}`, 'danger');
            }
        }
    });
});

// Add CSS styles for the plugin dashboard
const style = document.createElement('style');
style.textContent = `
    .plugin-dashboard-card {
        transition: all 0.3s ease;
    }
    
    .plugin-dashboard-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .plugin-iframe {
        transition: opacity 0.3s ease;
    }
    
    .loading-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        background-color: rgba(255,255,255,0.8);
        z-index: 10;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
    }
`;
document.head.appendChild(style);
