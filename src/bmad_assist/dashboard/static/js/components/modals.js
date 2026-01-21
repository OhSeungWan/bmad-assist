/**
 * Modals component for content display and reports
 * Handles content modal, report modal, and toast notifications
 *
 * Story 23.8 - Validator Identity Mapping for report content
 */

window.modalsComponent = function() {
    return {
        // Content modal (Story 16.9 - AC 3, 4)
        // Story 24.5: Added browser field for Raw/Rendered toggle support
        contentModal: {
            show: false,
            title: '',
            content: '',
            type: 'text',  // 'text' | 'xml' | 'markdown'
            browser: null  // Story 24.5: Browser state for Raw/Rendered toggle (null when not using browser controls)
        },

        // Report list modal (Story 16.9 - AC 4)
        reportModal: {
            show: false,
            epic: '',
            story: '',
            validation: { reports: [], synthesis: null },
            code_review: { reports: [], synthesis: null }
        },

        // Toast notification
        toast: {
            message: '',
            visible: false
        },
        _toastTimeout: null,

        // Track pending Shiki highlight timeouts for cleanup (Story 23.3 - synthesis fix)
        _pendingShikiHighlights: [],

        // Story 23.8: Validator identity mapping for report content
        _reportValidatorMapping: {},
        _reportValidatorMappingLoaded: false,
        // Story 24.8: Track warned validators to avoid console spam
        _warnedValidators: new Set(),

        /**
         * Show toast notification
         * @param {string} message - Message to display
         * @param {number} duration - Duration in ms (default 3000)
         */
        showToast(message, duration = 3000) {
            this.toast = { message, visible: true };
            if (this._toastTimeout) clearTimeout(this._toastTimeout);
            this._toastTimeout = setTimeout(() => { this.toast.visible = false; }, duration);
        },

        /**
         * Copy text to clipboard
         * @param {string} text - Text to copy
         */
        async copyToClipboard(text) {
            if (!navigator.clipboard) {
                console.error('Clipboard API unavailable (requires secure context)');
                this.showToast('Clipboard not available');
                return;
            }
            try {
                await navigator.clipboard.writeText(text);
                this.showToast('Copied to clipboard!');
            } catch (err) {
                console.error('Clipboard write failed:', err);
                this.showToast('Failed to copy');
            }
        },

        /**
         * Format markdown content with full markdown parsing and Shiki code highlighting.
         * Uses marked.js for markdown parsing with custom renderer for code blocks.
         *
         * @param {string} content - Raw markdown content
         * @returns {string} HTML with rendered markdown and highlighted code blocks
         */
        formatMarkdownContent(content) {
            if (!content) return '';

            const escapeHtml = window.dashboardUtils.escapeHtml;
            const self = this;

            // Fallback if marked.js failed to load
            if (typeof marked === 'undefined') {
                return escapeHtml(content);
            }

            // Create marked instance with custom renderer (marked v15 API)
            const instance = new marked.Marked({
                breaks: true,
                renderer: {
                    // Custom code block renderer to preserve Shiki highlighting
                    code({ text, lang }) {
                        const language = lang || 'text';
                        const code = text || '';

                        if (window._shikiReady && window.shikiHighlighter) {
                            const escapedCode = escapeHtml(code);
                            const blockId = `shiki-block-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;

                            // Queue async highlighting
                            self._queueShikiHighlight(blockId, code, language);

                            return `<pre class="shiki shiki-loading" data-lang="${escapeHtml(language)}" data-block-id="${blockId}"><code>${escapedCode}</code></pre>`;
                        } else {
                            const escapedCode = escapeHtml(code);
                            return `<pre class="shiki shiki-fallback" data-lang="${escapeHtml(language)}"><code>${escapedCode}</code></pre>`;
                        }
                    },
                    // Strip raw HTML to prevent XSS
                    html() {
                        return '';
                    }
                }
            });

            return instance.parse(content);
        },

        /**
         * Queue async Shiki highlighting for a code block.
         * Tracks timeout IDs for cleanup on modal close (Story 23.3 - synthesis fix).
         * Removes shiki-loading class on completion or failure (Story 23.4 - AC7).
         * @private
         */
        _queueShikiHighlight(blockId, code, lang) {
            // Use setTimeout to run after DOM update
            const timeoutId = setTimeout(async () => {
                // Remove from tracking array
                const idx = this._pendingShikiHighlights.indexOf(timeoutId);
                if (idx > -1) this._pendingShikiHighlights.splice(idx, 1);

                // Skip if modal was closed
                if (!this.contentModal.show) return;

                const block = document.querySelector(`[data-block-id="${blockId}"]`);
                if (!block) return;

                try {
                    const html = await window.shikiHighlighter.highlightCode(code, lang);

                    // Parse highlighted HTML
                    const temp = document.createElement('div');
                    temp.innerHTML = html;
                    const newBlock = temp.firstElementChild;

                    if (newBlock && block.parentElement) {
                        // Copy over data attributes
                        newBlock.setAttribute('data-block-id', blockId);
                        newBlock.setAttribute('data-lang', lang);
                        block.parentElement.replaceChild(newBlock, block);
                    }
                } catch (err) {
                    console.warn('Async Shiki highlight failed:', err);
                    // Remove loading state and add fallback on failure (AC7)
                    block.classList.remove('shiki-loading');
                    block.classList.add('shiki-fallback');
                }
            }, 0);

            // Track timeout for cleanup
            this._pendingShikiHighlights.push(timeoutId);
        },

        /**
         * Cancel all pending Shiki highlights (call on modal close).
         * Prevents memory leaks and orphaned DOM operations (Story 23.3 - synthesis fix).
         * @private
         */
        _cancelPendingShikiHighlights() {
            for (const timeoutId of this._pendingShikiHighlights) {
                clearTimeout(timeoutId);
            }
            this._pendingShikiHighlights = [];
        },

        /**
         * Focus trap for modal (cycles Tab focus within modal boundaries)
         * @param {Event} event - Keyboard event
         * @param {string} refName - Optional ref name (defaults to 'busyModalContent')
         */
        trapFocus(event, refName = 'busyModalContent') {
            const modal = this.$refs[refName];
            if (!modal) return;

            const focusable = modal.querySelectorAll(
                'input, button, [tabindex]:not([tabindex="-1"])'
            );
            if (focusable.length === 0) return;

            const first = focusable[0];
            const last = focusable[focusable.length - 1];

            if (event.shiftKey && document.activeElement === first) {
                last.focus();
                event.preventDefault();
            } else if (!event.shiftKey && document.activeElement === last) {
                first.focus();
                event.preventDefault();
            }
        },

        // ==========================================
        // Story 23.8 - Validator Identity Mapping
        // ==========================================

        /**
         * Load validator mapping for report modal (Story 23.8 AC1, AC3).
         * Called when report modal opens to fetch mappings for the story.
         *
         * @param {string} epic - Epic identifier
         * @param {string} story - Story number
         */
        async loadReportValidatorMapping(epic, story) {
            this._reportValidatorMapping = {};
            this._reportValidatorMappingLoaded = false;
            this._warnedValidators.clear();  // Story 24.8: Reset warned validators for new story

            // Try loading both validation and code-review mappings
            const types = ['validation', 'code-review'];
            for (const type of types) {
                try {
                    const response = await fetch(`/api/mapping/${type}/${epic}/${story}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.validators) {
                            // Merge into mapping (later types override earlier)
                            Object.assign(this._reportValidatorMapping, data.validators);
                        }
                    }
                } catch (err) {
                    console.warn(`Failed to load ${type} mapping for reports:`, err);
                    // Graceful fallback - keep original identifiers (AC4)
                }
            }

            this._reportValidatorMappingLoaded = true;
        },

        /**
         * Replace validator IDs with actual model names in report content (Story 23.8 AC1).
         * Handles both "Validator X" and "Reviewer X" formats in prose text.
         *
         * @param {string} content - Report content
         * @returns {string} Content with model names
         */
        replaceValidatorIdsInContent(content) {
            if (!content || !this._reportValidatorMappingLoaded) return content;

            const mapping = this._reportValidatorMapping;
            if (!mapping || Object.keys(mapping).length === 0) return content;

            // Replace both "Validator X" and "Reviewer X" formats (prose text in reports)
            // Use word boundary to avoid partial matches
            // Supports: Validator A, Reviewer B, Validators C, Reviewers D (singular/plural)
            return content.replace(/\b(Validator|Reviewer)s?\s+([A-Z])\b/gi, (match, type, letter) => {
                const key = `Validator ${letter.toUpperCase()}`;
                return mapping[key] || match;
            });
        },

        /**
         * Format markdown content with validator ID replacement (Story 23.8 AC1).
         * Applies validator mapping before markdown formatting.
         *
         * @param {string} content - Raw markdown content
         * @returns {string} HTML with model names and highlighted code blocks
         */
        formatMarkdownContentWithMapping(content) {
            if (!content) return '';
            // Apply validator ID replacement first, then format markdown
            const mappedContent = this.replaceValidatorIdsInContent(content);
            return this.formatMarkdownContent(mappedContent);
        },

        /**
         * Check if report path is a synthesis report (Story 23.8 AC6).
         *
         * @param {string} path - Report file path
         * @returns {boolean} True if synthesis report
         */
        isSynthesisReport(path) {
            if (!path) return false;
            return path.includes('/story-validations/synthesis-') ||
                   path.includes('/code-reviews/synthesis-');
        },

        /**
         * Get report type from path (Story 23.8).
         *
         * @param {string} path - Report file path
         * @returns {'validation' | 'code-review' | null}
         */
        getReportType(path) {
            if (!path) return null;
            if (path.includes('/story-validations/')) return 'validation';
            if (path.includes('/code-reviews/')) return 'code-review';
            return null;
        },

        /**
         * Reset validator mapping state (call on modal close).
         */
        resetReportValidatorMapping() {
            this._reportValidatorMapping = {};
            this._reportValidatorMappingLoaded = false;
        },

        /**
         * Get display name for a report in the report list (Story 24.8 AC3).
         * Converts single letter provider (a, b, c) to mapped model name.
         *
         * @param {object} report - Report object with provider and name fields
         * @returns {string} Mapped model name or fallback to original letter
         */
        getReportDisplayName(report) {
            // AC4: Graceful fallback if report or provider missing
            if (!report || !report.provider) {
                return report?.name || 'Unknown';
            }

            // AC4: Return original letter if mapping not loaded yet
            if (!this._reportValidatorMappingLoaded) {
                return report.provider;
            }

            // Convert lowercase letter to "Validator X" format for lookup
            // Backend extracts single letter from filename: validation-24-7-a-*.md → "a"
            const letter = report.provider.toUpperCase();
            const key = `Validator ${letter}`;
            const mapped = this._reportValidatorMapping[key];

            // AC4: Log warning if letter not found in mapping (debugging)
            // Story 24.8: Only warn once per letter to avoid console spam
            if (!mapped && !this._warnedValidators.has(letter)) {
                this._warnedValidators.add(letter);
                console.warn(`No mapping found for validator ${letter}, showing original identifier`);
            }

            // Return mapped name or fallback to original letter
            return mapped || report.provider;
        }
    };
};
