/**
 * Epic Metrics Browser component
 * Story 24.7 - Displays epic execution metrics with timeline visualization and accordion breakdown
 *
 * Provides:
 * - Timeline bar chart showing story execution time proportions
 * - Hover tooltips on timeline segments
 * - Accordion per-story breakdown with workflow details
 * - Duration formatting utilities
 */

// Segment color palette for timeline visualization (8 distinct colors)
const SEGMENT_COLORS = [
    'bg-blue-500',
    'bg-green-500',
    'bg-amber-500',
    'bg-purple-500',
    'bg-red-500',
    'bg-teal-500',
    'bg-pink-500',
    'bg-indigo-500'
];

window.epicMetricsComponent = function() {
    return {
        // ==========================================
        // State
        // ==========================================

        /**
         * Metrics modal state
         * @type {{show: boolean, epicId: number|string|null, data: object|null, loading: boolean}}
         */
        metricsModal: {
            show: false,
            epicId: null,
            data: null,
            loading: false
        },

        /**
         * Track which stories are expanded in accordion
         * @type {Set<number>}
         * @private
         */
        _expandedMetricsStories: new Set(),

        /**
         * Currently hovered segment data for tooltip
         * @type {{label: string}|null}
         * @private
         */
        _hoveredSegment: null,

        /**
         * Tooltip position tracking
         * @type {{x: number, y: number}}
         * @private
         */
        _tooltipPosition: { x: 0, y: 0 },

        // ==========================================
        // Modal Control Methods
        // ==========================================

        /**
         * Open epic metrics modal with data.
         * Called after successful API fetch from viewEpicMetrics().
         *
         * @param {number|string} epicId - Epic identifier
         * @param {object} data - Metrics data from API
         */
        openEpicMetrics(epicId, data) {
            this.metricsModal.epicId = epicId;
            this.metricsModal.data = data;
            this.metricsModal.loading = false;
            this.metricsModal.show = true;
            this._expandedMetricsStories.clear();
            // Refresh icons after modal renders (for chevrons)
            this.$nextTick(() => this.refreshIcons());
        },

        /**
         * Close metrics modal and cleanup state.
         * Clears expanded stories, hovered segment, and tooltip position to prevent leakage.
         */
        closeEpicMetrics() {
            this.metricsModal.show = false;
            this._expandedMetricsStories.clear();
            this._hoveredSegment = null;
            this._tooltipPosition = { x: 0, y: 0 };
        },

        // ==========================================
        // Duration Formatting
        // ==========================================

        /**
         * Format milliseconds to human-readable duration.
         * Matches existing pattern in tree-view.js:272-278.
         *
         * @param {number} ms - Duration in milliseconds
         * @returns {string} Formatted duration (e.g., "12m 34s", "1h 30m")
         */
        formatDuration(ms) {
            if (ms === null || ms === undefined) return '0s';
            if (ms < 1000) return `${ms}ms`;
            if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
            const mins = Math.floor(ms / 60000);
            const secs = Math.floor((ms % 60000) / 1000);
            if (mins < 60) return `${mins}m ${secs}s`;
            const hours = Math.floor(mins / 60);
            const remainMins = mins % 60;
            return `${hours}h ${remainMins}m`;
        },

        // ==========================================
        // Timeline Visualization Methods
        // ==========================================

        /**
         * Calculate segment width as percentage of total.
         * Zero-guard to prevent division by zero.
         *
         * @param {number} storyDurationMs - Story duration in ms
         * @param {number} totalDurationMs - Total epic duration in ms
         * @returns {number} Width percentage (0-100)
         */
        getSegmentWidth(storyDurationMs, totalDurationMs) {
            if (!totalDurationMs || totalDurationMs === 0) return 0;
            if (!storyDurationMs) return 0;
            return (storyDurationMs / totalDurationMs) * 100;
        },

        /**
         * Get segment color from cycling palette.
         *
         * @param {number} index - Story index (0-based)
         * @returns {string} Tailwind CSS color class
         */
        getSegmentColor(index) {
            return SEGMENT_COLORS[index % SEGMENT_COLORS.length];
        },

        // ==========================================
        // Tooltip Methods
        // ==========================================

        /**
         * Show segment tooltip on hover.
         * Includes viewport boundary detection to prevent overflow.
         *
         * @param {Event} event - Mouse event
         * @param {object} story - Story object with story_num, title, total_duration_ms
         */
        showSegmentTooltip(event, story) {
            const label = `${this.metricsModal.epicId}.${story.story_num} ${story.title} — ${this.formatDuration(story.total_duration_ms)}`;
            this._hoveredSegment = { label };

            const offset = 10;
            let x = event.clientX + offset;
            let y = event.clientY + offset;

            // Viewport boundary detection
            const tooltipWidth = 300; // max-width from CSS
            const tooltipHeight = 50; // approximate height
            if (x + tooltipWidth > window.innerWidth) {
                x = window.innerWidth - tooltipWidth - offset;
            }
            if (y + tooltipHeight > window.innerHeight) {
                y = event.clientY - tooltipHeight - offset;
            }
            // Top boundary check - prevent negative y position
            if (y < 0) {
                y = offset;
            }

            this._tooltipPosition = { x, y };
        },

        /**
         * Hide segment tooltip.
         */
        hideSegmentTooltip() {
            this._hoveredSegment = null;
        },

        // ==========================================
        // Accordion Methods
        // ==========================================

        /**
         * Toggle story expansion in accordion.
         * Refreshes icons after toggle for chevron update.
         *
         * @param {number} storyNum - Story number to toggle
         */
        toggleMetricsStory(storyNum) {
            if (this._expandedMetricsStories.has(storyNum)) {
                this._expandedMetricsStories.delete(storyNum);
            } else {
                this._expandedMetricsStories.add(storyNum);
            }
            // Refresh icons after toggle for chevron state
            this.$nextTick(() => this.refreshIcons());
        },

        /**
         * Check if story is expanded in accordion.
         *
         * @param {number} storyNum - Story number to check
         * @returns {boolean} True if expanded
         */
        isMetricsStoryExpanded(storyNum) {
            return this._expandedMetricsStories.has(storyNum);
        }
    };
};
