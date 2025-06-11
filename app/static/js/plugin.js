/**
 * Plugin page JavaScript functionality for NetScout Pi
 */

// Initialize Socket.IO connection with explicit transport configuration
const socket = io({
    transports: ['websocket', 'polling'],
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    timeout: 20000
});

// DOM Elements
const runPluginBtn = document.getElementById('run-plugin-btn');
const pluginParamsForm = document.getElementById('plugin-params-form');
const pluginOutput = document.getElementById('plugin-output');

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

socket.on('plugin_result', (data) => {
    console.log('Received plugin result:', data);
    if (data.plugin_id === plugin.id) {
        displayPluginOutput(data.result);
    }
});

socket.on('plugin_error', (data) => {
    console.error('Plugin error:', data);
    if (data.plugin_id === plugin.id) {
        displayPluginError(data.error);
    }
});

// Add event listeners
document.addEventListener('DOMContentLoaded', () => {
    runPluginBtn.addEventListener('click', runPlugin);
});

/**
 * Run the plugin with form parameters
 */
function runPlugin() {
    // Get parameters from form
    const params = {};
    const formData = new FormData(pluginParamsForm);
    
    for (const [key, value] of formData.entries()) {
        params[key] = value;
    }
    
    // Handle checkbox inputs separately (they don't appear in FormData if unchecked)
    const checkboxes = pluginParamsForm.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        params[checkbox.name] = checkbox.checked;
    });
    
    // Show loading state
    pluginOutput.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div><p>Running plugin...</p></div>';
    
    // Run plugin via Socket.IO
    socket.emit('execute_plugin', {
        plugin_id: plugin.id,
        params: params
    });
}

/**
 * Display plugin output
 * @param {*} result - The result from the plugin execution
 */
function displayPluginOutput(result) {
    // Convert result to formatted HTML
    let outputHtml = '';
    
    if (typeof result === 'object') {
        // Handle JSON objects
        outputHtml = `<pre class="code-block">${JSON.stringify(result, null, 2)}</pre>`;
        
        // Special handling for some result types
        if (result.type === 'chart' && result.data) {
            // Render chart if the plugin returns chart data
            outputHtml += '<div class="chart-container mt-3"><canvas id="result-chart"></canvas></div>';
            
            // Create chart after HTML is inserted
            setTimeout(() => {
                const ctx = document.getElementById('result-chart').getContext('2d');
                new Chart(ctx, result.data);
            }, 0);
        } else if (result.type === 'table' && result.data) {
            // Render table if the plugin returns table data
            let tableHtml = '<div class="table-responsive mt-3"><table class="table table-striped">';
            
            // Add headers
            if (result.headers) {
                tableHtml += '<thead><tr>';
                result.headers.forEach(header => {
                    tableHtml += `<th>${header}</th>`;
                });
                tableHtml += '</tr></thead>';
            }
            
            // Add rows
            tableHtml += '<tbody>';
            result.data.forEach(row => {
                tableHtml += '<tr>';
                if (Array.isArray(row)) {
                    row.forEach(cell => {
                        tableHtml += `<td>${cell}</td>`;
                    });
                } else {
                    Object.values(row).forEach(cell => {
                        tableHtml += `<td>${cell}</td>`;
                    });
                }
                tableHtml += '</tr>';
            });
            tableHtml += '</tbody></table></div>';
            
            outputHtml += tableHtml;
        }
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
    pluginOutput.innerHTML = `
        <div class="alert alert-danger" role="alert">
            <h5>Error:</h5>
            <p>${error}</p>
        </div>
    `;
}
