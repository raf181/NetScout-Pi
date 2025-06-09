/**
 * NetProbe Pi - Theme Switch
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check for saved theme preference or respect OS preference
    initTheme();
    
    // Add theme toggle to navbar if it doesn't exist yet
    addThemeToggle();
});

/**
 * Initialize theme based on user preference or system preference
 */
function initTheme() {
    // Check if user has a saved preference
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme) {
        // Apply saved preference
        document.body.classList.toggle('dark-theme', savedTheme === 'dark');
        updateThemeIcon(savedTheme === 'dark');
    } else {
        // Check if user prefers dark mode at OS level
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (prefersDark) {
            document.body.classList.add('dark-theme');
            updateThemeIcon(true);
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.remove('dark-theme');
            updateThemeIcon(false);
            localStorage.setItem('theme', 'light');
        }
    }
    
    // Add transition class after initial load
    setTimeout(() => {
        document.body.classList.add('theme-transition');
    }, 100);
}

/**
 * Add theme toggle button to navbar if not already present
 */
function addThemeToggle() {
    // Check if navbar flex container exists
    const navFlex = document.querySelector('.navbar .d-flex');
    
    if (navFlex && !document.getElementById('theme-toggle')) {
        // Create theme toggle button
        const themeToggle = document.createElement('button');
        themeToggle.id = 'theme-toggle';
        themeToggle.className = 'theme-toggle ms-2';
        themeToggle.setAttribute('type', 'button');
        themeToggle.setAttribute('aria-label', 'Toggle theme');
        
        // Set initial icon based on current theme
        const isDark = document.body.classList.contains('dark-theme');
        themeToggle.innerHTML = isDark ? 
            '<i class="fas fa-sun"></i>' : 
            '<i class="fas fa-moon"></i>';
        
        // Add click event listener
        themeToggle.addEventListener('click', toggleTheme);
        
        // Insert before logout button if it exists, or append to flex container
        const logoutButton = navFlex.querySelector('a.btn');
        if (logoutButton) {
            navFlex.insertBefore(themeToggle, logoutButton);
        } else {
            navFlex.appendChild(themeToggle);
        }
    }
}

/**
 * Toggle between light and dark themes
 */
function toggleTheme() {
    // Toggle dark theme class
    const isDark = document.body.classList.toggle('dark-theme');
    
    // Update toggle button icon
    updateThemeIcon(isDark);
    
    // Save preference
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    
    // Emit theme change event for components to react
    window.dispatchEvent(new CustomEvent('themechange', {
        detail: { theme: isDark ? 'dark' : 'light' }
    }));
}

/**
 * Update theme toggle icon
 */
function updateThemeIcon(isDark) {
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.innerHTML = isDark ? 
            '<i class="fas fa-sun"></i>' : 
            '<i class="fas fa-moon"></i>';
    }
}
