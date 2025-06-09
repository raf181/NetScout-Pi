/**
 * NetProbe Pi - Main JavaScript
 */

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips and popovers if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
    
    // Network status indicator
    updateNetworkStatus();
    
    // Automatically dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(alert => {
            if (alert && typeof bootstrap !== 'undefined') {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);
    
    // Setup WebSocket connection if available
    setupWebSocket();
});

/**
 * Update the network status indicator
 */
function updateNetworkStatus() {
    const networkStatus = document.getElementById('network-status');
    if (!networkStatus) return;
    
    // Simulate network check (would be replaced with actual WebSocket status)
    if (navigator.onLine) {
        networkStatus.innerHTML = '<i class="fas fa-circle text-success me-1"></i> Connected';
    } else {
        networkStatus.innerHTML = '<i class="fas fa-circle text-danger me-1"></i> Disconnected';
    }
}

/**
 * Setup WebSocket connection for real-time updates
 */
function setupWebSocket() {
    // Check if Socket.IO is available
    if (typeof io === 'undefined') return;
    
    const socket = io();
    
    socket.on('connect', function() {
        console.log('WebSocket connected');
        updateNetworkStatus();
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket disconnected');
        document.getElementById('network-status').innerHTML = 
            '<i class="fas fa-circle text-danger me-1"></i> Disconnected';
    });
    
    // Handle system status updates
    socket.on('system_status', function(data) {
        console.log('System status update:', data);
        // Update UI based on system status
        updateSystemStatus(data);
    });
    
    // Handle plugin updates
    socket.on('plugin_update', function(data) {
        console.log('Plugin update:', data);
        // Update UI based on plugin data
    });
    
    // Handle new test results
    socket.on('new_result', function(data) {
        console.log('New test result:', data);
        // Update UI to show new test result
        showNotification('New test result available');
    });
}

/**
 * Update system status displays
 */
function updateSystemStatus(data) {
    if (!data) return;
    
    // CPU Usage
    const cpuElement = document.getElementById('cpu-usage');
    if (cpuElement && data.cpu) {
        cpuElement.textContent = data.cpu + '%';
        
        // Update progress bar if exists
        const cpuProgress = document.getElementById('cpu-progress');
        if (cpuProgress) {
            cpuProgress.style.width = data.cpu + '%';
            cpuProgress.setAttribute('aria-valuenow', data.cpu);
            
            // Change color based on usage
            cpuProgress.className = 'progress-bar';
            if (data.cpu > 80) {
                cpuProgress.classList.add('bg-danger');
            } else if (data.cpu > 60) {
                cpuProgress.classList.add('bg-warning');
            } else {
                cpuProgress.classList.add('bg-success');
            }
        }
    }
    
    // Memory Usage
    const memElement = document.getElementById('memory-usage');
    if (memElement && data.memory) {
        memElement.textContent = data.memory + '%';
        
        const memProgress = document.getElementById('memory-progress');
        if (memProgress) {
            memProgress.style.width = data.memory + '%';
            memProgress.setAttribute('aria-valuenow', data.memory);
            
            memProgress.className = 'progress-bar';
            if (data.memory > 80) {
                memProgress.classList.add('bg-danger');
            } else if (data.memory > 60) {
                memProgress.classList.add('bg-warning');
            } else {
                memProgress.classList.add('bg-success');
            }
        }
    }
    
    // Disk Usage
    const diskElement = document.getElementById('disk-usage');
    if (diskElement && data.disk) {
        diskElement.textContent = data.disk + '%';
        
        const diskProgress = document.getElementById('disk-progress');
        if (diskProgress) {
            diskProgress.style.width = data.disk + '%';
            diskProgress.setAttribute('aria-valuenow', data.disk);
            
            diskProgress.className = 'progress-bar';
            if (data.disk > 90) {
                diskProgress.classList.add('bg-danger');
            } else if (data.disk > 75) {
                diskProgress.classList.add('bg-warning');
            } else {
                diskProgress.classList.add('bg-success');
            }
        }
    }
    
    // Temperature
    const tempElement = document.getElementById('temperature');
    if (tempElement && data.temperature) {
        tempElement.textContent = data.temperature + '°C';
        
        // Change color based on temperature
        tempElement.className = '';
        if (data.temperature > 75) {
            tempElement.classList.add('text-danger');
        } else if (data.temperature > 65) {
            tempElement.classList.add('text-warning');
        } else {
            tempElement.classList.add('text-success');
        }
    }
}

/**
 * Show a browser notification
 */
function showNotification(message) {
    // Check if browser supports notifications
    if (!("Notification" in window)) return;
    
    // Check if permission is already granted
    if (Notification.permission === "granted") {
        new Notification("NetProbe Pi", { body: message });
    } 
    // Otherwise, ask for permission
    else if (Notification.permission !== "denied") {
        Notification.requestPermission().then(function (permission) {
            if (permission === "granted") {
                new Notification("NetProbe Pi", { body: message });
            }
        });
    }
}
