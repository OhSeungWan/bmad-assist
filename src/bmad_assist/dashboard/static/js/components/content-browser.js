/**
 * Content Browser shared component for dashboard content browsers
 * Provides Raw/Rendered toggle, Copy button, and path utilities
 *
 * Story 24.1 - Shared Browser Infrastructure
 *
 * This component provides reusable infrastructure for content browsers:
 * - Prompt Browser (Story 23.5)
 * - Story Browser (Story 24.5)
 * - Epic Details Browser (Story 24.6)
 * - Epic Metrics Browser (Story 24.7)
 * - Review Browser (Stories 24.8, 24.9)
 *
 * Usage:
 * - Utilities via window.contentBrowserUtils (pure functions)
 * - Component API via window.contentBrowserComponent (Alpine.js integration)
 */

// ==========================================
// Path Utilities (Pure Functions)
// ==========================================

/**
 * Detect project root from file path variables.
 * Finds common prefix among absolute paths or uses project markers as fallback.
 *
 * Extracted from prompt-browser.js _detectProjectRoot() for reuse.
 *
 * @param {Array<{name: string, value: string}>} variables - Array of variable objects
 * @returns {string|null} Project root path or null
 */
function detectProjectRoot(variables) {
    if (!variables || variables.length === 0) return null;

    // Get all absolute file paths from *_file variables and known path variables
    const pathVarNames = ['output_folder', 'implementation_artifacts', 'planning_artifacts', 'project_knowledge', 'story_dir'];
    const filePaths = variables
        .filter(v => {
            // Include *_file variables and known path variables
            return (v.name.endsWith('_file') || pathVarNames.includes(v.name)) &&
                   v.value && v.value.startsWith('/');
        })
        .map(v => v.value);

    if (filePaths.length === 0) return null;

    if (filePaths.length === 1) {
        // Single path: find last project marker
        const markers = ['/docs/', '/src/', '/_bmad-output/', '/tests/'];
        for (const marker of markers) {
            const idx = filePaths[0].indexOf(marker);
            if (idx !== -1) return filePaths[0].slice(0, idx);
        }
        return null;
    }

    // Find longest common directory prefix
    // Check directory boundary - path must equal prefix OR start with prefix + '/'
    let prefix = filePaths[0];
    for (const path of filePaths.slice(1)) {
        while (prefix && !(path === prefix || path.startsWith(prefix + '/'))) {
            // Remove last path segment
            const lastSlash = prefix.lastIndexOf('/');
            if (lastSlash <= 0) {
                prefix = '';
                break;
            }
            prefix = prefix.slice(0, lastSlash);
        }
        if (!prefix) return null;
    }

    return prefix || null;
}

/**
 * Shorten an absolute path relative to project root.
 *
 * Extracted from prompt-browser.js shortenPath() for reuse.
 *
 * @param {string} fullPath - Full absolute path
 * @param {string|null} projectRoot - Detected project root
 * @returns {string} Shortened path (relative) or original path
 */
function shortenPath(fullPath, projectRoot) {
    if (!fullPath) return '';

    // If we have a project root and path starts with it, make relative
    // Check directory boundary - path must equal root OR start with root + '/'
    if (projectRoot && (fullPath === projectRoot || fullPath.startsWith(projectRoot + '/'))) {
        return fullPath.slice(projectRoot.length).replace(/^\//, '');
    }

    // Fallback: Try to detect common project markers
    const markers = ['/docs/', '/src/', '/_bmad-output/', '/tests/'];
    for (const marker of markers) {
        const idx = fullPath.indexOf(marker);
        if (idx !== -1) {
            // Return from marker onwards (keep leading slash for clarity)
            return fullPath.slice(idx);
        }
    }

    return fullPath;  // No shortening possible
}

/**
 * Check if a path is external to the project root.
 * A path is external if it doesn't start with the project root.
 *
 * @param {string} fullPath - Full absolute path
 * @param {string|null} projectRoot - Detected project root
 * @returns {boolean} True if path is external to project
 */
function isExternalPath(fullPath, projectRoot) {
    if (!fullPath || !projectRoot) return false;
    return !(fullPath === projectRoot || fullPath.startsWith(projectRoot + '/'));
}

/**
 * Format a path with external indicator information.
 * Returns display path, external flag, and base directory for tooltip.
 *
 * @param {string} fullPath - Full absolute path
 * @param {string|null} projectRoot - Detected project root
 * @returns {{displayPath: string, isExternal: boolean, externalBase: string|null}}
 */
function formatPathWithExternal(fullPath, projectRoot) {
    if (!fullPath) return { displayPath: '', isExternal: false, externalBase: null };

    const isExternal = isExternalPath(fullPath, projectRoot);
    let displayPath;
    let externalBase = null;

    if (isExternal) {
        // Find a reasonable base directory to show in tooltip
        const lastSlash = fullPath.lastIndexOf('/');
        externalBase = lastSlash > 0 ? fullPath.slice(0, lastSlash + 1) : fullPath;

        // Still try to shorten for display using markers
        displayPath = shortenPath(fullPath, null);
    } else {
        displayPath = shortenPath(fullPath, projectRoot);
    }

    return { displayPath, isExternal, externalBase };
}

// ==========================================
// Export Utilities as window global
// Story 24.1 AC6: window.contentBrowserUtils
// ==========================================

window.contentBrowserUtils = {
    shortenPath,
    isExternalPath,
    formatPathWithExternal,
    detectProjectRoot
};

// ==========================================
// Alpine.js Component
// ==========================================

/**
 * Content Browser Alpine.js component factory.
 * Provides shared state management and methods for content browsers.
 *
 * Story 24.1 AC6: window.contentBrowserComponent
 */
window.contentBrowserComponent = function() {
    return {
        /**
         * Create a new browser state object.
         * Each browser instance should call this to get its own state.
         *
         * Story 24.1 AC1: Defaults to 'rendered' view
         *
         * @returns {{view: 'rendered'|'raw', projectRoot: string|null}}
         */
        createBrowserState() {
            return {
                view: 'rendered',
                projectRoot: null
            };
        },

        /**
         * Toggle view between 'rendered' and 'raw'.
         * Synchronous state change for < 100ms response (AC1).
         *
         * @param {object} browser - Browser state object from createBrowserState()
         */
        toggleView(browser) {
            browser.view = browser.view === 'rendered' ? 'raw' : 'rendered';
        },

        /**
         * Copy raw content to clipboard.
         * Always copies raw content regardless of current view mode (AC2).
         *
         * @param {string} content - Raw content to copy
         * @param {function} toastCallback - Callback for toast messages (receives message string)
         * @returns {Promise<boolean>} True if copy succeeded
         */
        async copyRawContent(content, toastCallback) {
            if (!navigator.clipboard) {
                console.error('Clipboard API unavailable (requires secure context)');
                toastCallback?.('Clipboard not available');
                return false;
            }
            try {
                await navigator.clipboard.writeText(content);
                toastCallback?.('Copied to clipboard!');
                return true;
            } catch (err) {
                console.error('Clipboard write failed:', err);
                toastCallback?.('Failed to copy');
                return false;
            }
        },

        // ==========================================
        // Path Utility Methods (delegating to pure functions)
        // These allow Alpine components to call this.shortenPath() etc.
        // ==========================================

        /**
         * Shorten path relative to project root.
         * Delegates to window.contentBrowserUtils.shortenPath.
         */
        shortenPath(fullPath, projectRoot) {
            return window.contentBrowserUtils.shortenPath(fullPath, projectRoot);
        },

        /**
         * Check if path is external to project.
         * Delegates to window.contentBrowserUtils.isExternalPath.
         */
        isExternalPath(fullPath, projectRoot) {
            return window.contentBrowserUtils.isExternalPath(fullPath, projectRoot);
        },

        /**
         * Format path with external indicator.
         * Delegates to window.contentBrowserUtils.formatPathWithExternal.
         */
        formatPathWithExternal(fullPath, projectRoot) {
            return window.contentBrowserUtils.formatPathWithExternal(fullPath, projectRoot);
        },

        /**
         * Detect project root from variables.
         * Delegates to window.contentBrowserUtils.detectProjectRoot.
         */
        detectProjectRoot(variables) {
            return window.contentBrowserUtils.detectProjectRoot(variables);
        }
    };
};
