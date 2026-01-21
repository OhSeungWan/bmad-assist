/**
 * Shared utility functions for bmad-dashboard
 * These functions are used across multiple components
 */

/**
 * Refresh Lucide icons (call after DOM updates)
 */
function refreshIcons() {
    if (typeof lucide !== 'undefined' && lucide.createIcons) {
        lucide.createIcons();
    }
}

/**
 * Show toast notification
 * @param {Object} context - Alpine component context (this)
 * @param {string} message - Message to display
 * @param {number} duration - Duration in ms (default 3000)
 */
function showToast(context, message, duration = 3000) {
    context.toast = { message, visible: true };
    if (context._toastTimeout) clearTimeout(context._toastTimeout);
    context._toastTimeout = setTimeout(() => { context.toast.visible = false; }, duration);
}

/**
 * Copy text to clipboard with toast feedback
 * @param {Object} context - Alpine component context (this)
 * @param {string} text - Text to copy
 */
async function copyToClipboard(context, text) {
    if (!navigator.clipboard) {
        console.error('Clipboard API unavailable (requires secure context)');
        showToast(context, 'Clipboard not available');
        return;
    }
    try {
        await navigator.clipboard.writeText(text);
        showToast(context, 'Copied to clipboard!');
    } catch (err) {
        console.error('Clipboard write failed:', err);
        showToast(context, 'Failed to copy');
    }
}

// ==========================================
// Format Helpers
// ==========================================

/**
 * Format bytes to human-readable string
 * @param {number} bytes - Byte count
 * @returns {string} Formatted string (e.g., "1.5 KB")
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Format duration from milliseconds
 * @param {number} ms - Duration in milliseconds
 * @returns {string} Formatted string (e.g., "2m 30s")
 */
function formatDuration(ms) {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    const mins = Math.floor(ms / 60000);
    const secs = ((ms % 60000) / 1000).toFixed(0);
    return `${mins}m ${secs}s`;
}

/**
 * Format timestamp to locale time string
 * @param {number} timestamp - Unix timestamp in seconds
 * @returns {string} Formatted time string (HH:MM:SS)
 */
function formatTimestamp(timestamp) {
    return new Date(timestamp * 1000).toLocaleTimeString('en-US', { hour12: false });
}

/**
 * Format backup timestamp for display
 * @param {string} timestamp - ISO timestamp string
 * @returns {string} Formatted date/time
 */
function formatBackupTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

// ==========================================
// Status Color/Icon Helpers
// ==========================================

/**
 * Get background color class for status
 * @param {string} status - Status string
 * @returns {string} Tailwind class
 */
function getStatusColor(status) {
    const colors = {
        done: 'bg-accent',
        'in-progress': 'bg-primary',
        review: 'bg-bp-warning',
        'ready-for-dev': 'bg-chart-3',
        backlog: 'bg-border'
    };
    return colors[status] || 'bg-border';
}

/**
 * Get Lucide icon name for story status
 * @param {string} status - Status string
 * @returns {string} Icon name
 */
function getStatusIcon(status) {
    const icons = {
        done: 'check-circle',
        'in-progress': 'play-circle',
        review: 'eye',
        'ready-for-dev': 'clipboard-list',
        drafted: 'file-text',
        draft: 'file-text',
        pending: 'circle-dashed',
        backlog: 'square'
    };
    return icons[status] || 'square';
}

/**
 * Get text color class for status icons
 * @param {string} status - Status string
 * @returns {string} Tailwind class
 */
function getStatusTextColor(status) {
    const colors = {
        done: 'text-accent',
        'in-progress': 'text-primary',
        review: 'text-bp-warning',
        'ready-for-dev': 'text-chart-3',
        drafted: 'text-muted-foreground',
        draft: 'text-muted-foreground',
        pending: 'text-muted-foreground',
        deferred: 'text-muted-foreground',
        backlog: 'text-muted-foreground'
    };
    return colors[status] || 'text-muted-foreground';
}

/**
 * Get Lucide icon name for phase status
 * @param {string} status - Phase status
 * @returns {string} Icon name
 */
function getPhaseStatusIcon(status) {
    const icons = {
        completed: 'check-circle',
        'in-progress': 'play-circle',
        pending: 'circle-dashed'
    };
    return icons[status] || 'circle-dashed';
}

/**
 * Get text color class for phase icons
 * @param {string} status - Phase status
 * @returns {string} Tailwind class
 */
function getPhaseStatusColor(status) {
    const colors = {
        completed: 'text-accent',
        'in-progress': 'text-primary',
        pending: 'text-muted-foreground'
    };
    return colors[status] || 'text-muted-foreground';
}

/**
 * Get provider color class
 * @param {string} provider - Provider name
 * @returns {string} CSS class
 */
function getProviderColor(provider) {
    const colors = {
        opus: 'provider-opus',
        gemini: 'provider-gemini',
        glm: 'provider-glm',
        claude: 'provider-claude'
    };
    return colors[provider] || 'provider-bmad';
}

/**
 * Get Lucide icon name for epic status
 * @param {string} status - Epic status
 * @returns {string} Icon name
 */
function getEpicStatusIcon(status) {
    const icons = {
        done: 'folder-check',
        'in-progress': 'folder-open',
        deferred: 'pause-circle',
        draft: 'folder',
        backlog: 'folder'
    };
    return icons[status] || 'folder';
}

/**
 * Get Lucide icon name for context menu action emoji
 * @param {string} emoji - Emoji icon
 * @returns {string} Lucide icon name
 */
function getActionIcon(emoji) {
    const iconMap = {
        '📄': 'file-text',
        '📊': 'bar-chart-2',
        '▶️': 'play',
        '📋': 'clipboard',
        '📝': 'edit',
        '👀': 'eye',
        '🔄': 'refresh-cw',
        '✅': 'check-square',
        '⏭️': 'skip-forward',
        '⚠️': 'alert-triangle'
    };
    return iconMap[emoji] || 'circle';
}

// ==========================================
// Security Helpers
// ==========================================

/**
 * Escape HTML entities to prevent XSS.
 * Centralized function used across components (Story 23.3).
 *
 * @param {string} text - Raw text to escape
 * @returns {string} HTML-escaped text
 */
function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Export utilities as window globals for use by components
window.dashboardUtils = {
    refreshIcons,
    showToast,
    copyToClipboard,
    escapeHtml,
    formatBytes,
    formatDuration,
    formatTimestamp,
    formatBackupTime,
    getStatusColor,
    getStatusIcon,
    getStatusTextColor,
    getPhaseStatusIcon,
    getPhaseStatusColor,
    getProviderColor,
    getEpicStatusIcon,
    getActionIcon
};
