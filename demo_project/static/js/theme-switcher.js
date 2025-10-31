/**
 * Theme Switcher
 * Manages light/dark theme switching with cookie persistence
 */

(function() {
    'use strict';

    const THEME_COOKIE_NAME = 'theme';
    const THEME_COOKIE_DAYS = 365;

    /**
     * Get cookie value by name
     */
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    /**
     * Set cookie
     */
    function setCookie(name, value, days) {
        const expires = new Date();
        expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
        document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
    }

    /**
     * Get current theme from cookie or system preference
     */
    function getTheme() {
        const savedTheme = getCookie(THEME_COOKIE_NAME);
        if (savedTheme) {
            return savedTheme;
        }

        // Check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }

        return 'light';
    }

    /**
     * Set theme
     */
    function setTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
        setCookie(THEME_COOKIE_NAME, theme, THEME_COOKIE_DAYS);
        updateToggleButton(theme);
    }

    /**
     * Toggle theme
     */
    function toggleTheme() {
        const currentTheme = getTheme();
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
    }

    /**
     * Update toggle button icons
     */
    function updateToggleButton(theme) {
        const toggleButtons = [
            document.getElementById('theme-toggle'),
            document.getElementById('theme-toggle-mobile')
        ];

        toggleButtons.forEach(toggleBtn => {
            if (!toggleBtn) return;

            const sunIcon = toggleBtn.querySelector('.sun-icon');
            const moonIcon = toggleBtn.querySelector('.moon-icon');

            if (theme === 'dark') {
                if (sunIcon) sunIcon.classList.remove('hidden');
                if (moonIcon) moonIcon.classList.add('hidden');
            } else {
                if (sunIcon) sunIcon.classList.add('hidden');
                if (moonIcon) moonIcon.classList.remove('hidden');
            }
        });
    }

    /**
     * Initialize theme on page load
     */
    function initTheme() {
        const theme = getTheme();
        setTheme(theme);

        // Add click handlers to toggle buttons
        const toggleBtn = document.getElementById('theme-toggle');
        const toggleBtnMobile = document.getElementById('theme-toggle-mobile');

        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
        }
        if (toggleBtnMobile) {
            toggleBtnMobile.addEventListener('click', toggleTheme);
        }
    }

    /**
     * Initialize mobile menu
     */
    function initMobileMenu() {
        const menuToggle = document.getElementById('mobile-menu-toggle');
        const mobileMenu = document.getElementById('mobile-menu');

        if (menuToggle && mobileMenu) {
            menuToggle.addEventListener('click', function() {
                mobileMenu.classList.toggle('hidden');
            });

            // Close menu when clicking outside
            document.addEventListener('click', function(event) {
                const isClickInsideMenu = mobileMenu.contains(event.target);
                const isClickOnToggle = menuToggle.contains(event.target);

                if (!isClickInsideMenu && !isClickOnToggle && !mobileMenu.classList.contains('hidden')) {
                    mobileMenu.classList.add('hidden');
                }
            });

            // Close menu when clicking on a link
            const menuLinks = mobileMenu.querySelectorAll('a');
            menuLinks.forEach(link => {
                link.addEventListener('click', function() {
                    mobileMenu.classList.add('hidden');
                });
            });
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initTheme();
            initMobileMenu();
        });
    } else {
        initTheme();
        initMobileMenu();
    }

    // Expose API
    window.ThemeSwitcher = {
        getTheme,
        setTheme,
        toggleTheme
    };
})();
