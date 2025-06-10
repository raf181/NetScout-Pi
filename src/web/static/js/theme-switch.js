/**
 * NetProbe Pi - Theme Switch 2025
 * Integrates with Tailwind Dark Mode and modern system preferences
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Alpine.js theme data
    window.Alpine = window.Alpine || {};
    window.Alpine.store('theme', {
        isDark: false,
        init() {
            this.isDark = this.getThemePreference();
            this.applyTheme();
        },
        toggle() {
            this.isDark = !this.isDark;
            this.applyTheme();
            this.savePreference();
        },
        getThemePreference() {
            // Check localStorage first
            const stored = localStorage.getItem('theme');
            if (stored) {
                return stored === 'dark';
            }
            // Fall back to system preference
            return window.matchMedia('(prefers-color-scheme: dark)').matches;
        },
        applyTheme() {
            // Update data-theme attribute for DaisyUI
            document.documentElement.setAttribute('data-theme', this.isDark ? 'dark' : 'light');
            // Update Tailwind dark mode class
            document.documentElement.classList.toggle('dark', this.isDark);
            // Update theme icons
            this.updateThemeIcon();
            // Dispatch event for other components
            window.dispatchEvent(new CustomEvent('theme-changed', { 
                detail: { theme: this.isDark ? 'dark' : 'light' } 
            }));
        },
        savePreference() {
            localStorage.setItem('theme', this.isDark ? 'dark' : 'light');
        },
        updateThemeIcon() {
            const toggle = document.getElementById('theme-toggle');
            if (toggle) {
                const icon = toggle.querySelector('i');
                if (icon) {
                    icon.className = this.isDark ? 'fas fa-sun' : 'fas fa-moon';
                }
                // Update ARIA label
                toggle.setAttribute('aria-label', 
                    this.isDark ? 'Switch to light theme' : 'Switch to dark theme'
                );
            }
        }
    });

    // Add theme toggle if not present
    addThemeToggle();

    // Listen for OS theme changes
    window.matchMedia('(prefers-color-scheme: dark)')
        .addEventListener('change', e => {
            if (!localStorage.getItem('theme')) {
                Alpine.store('theme').isDark = e.matches;
                Alpine.store('theme').applyTheme();
            }
        });
});

/**
 * Add theme toggle button to navbar if not present
 */
function addThemeToggle() {
    const navbarControls = document.querySelector('.navbar .navbar-controls');
    if (!navbarControls || document.getElementById('theme-toggle')) return;

    const toggle = document.createElement('button');
    toggle.id = 'theme-toggle';
    toggle.className = 'theme-toggle';
    toggle.setAttribute('type', 'button');
    toggle.setAttribute('x-data', '');
    toggle.setAttribute('@click', '$store.theme.toggle()');
    toggle.setAttribute('aria-label', 'Toggle theme');
    
    // Initial icon state
    const isDark = Alpine.store('theme').isDark;
    toggle.innerHTML = `<i class="fas ${isDark ? 'fa-sun' : 'fa-moon'}"></i>`;
    
    // Find appropriate insert position
    const logoutButton = navbarControls.querySelector('.btn-logout');
    if (logoutButton) {
        navbarControls.insertBefore(toggle, logoutButton);
    } else {
        navbarControls.appendChild(toggle);
    }

    // Add keyboard support
    toggle.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            Alpine.store('theme').toggle();
        }
    });
}
