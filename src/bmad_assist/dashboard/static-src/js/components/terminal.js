/**
 * Terminal component for output display
 * Handles terminal output, tabs, filtering, auto-scroll, and font size
 */

window.terminalComponent = function() {
    return {
        // State
        output: [],
        activeTab: 'All',
        autoScroll: true,
        terminalStatus: 'idle',  // 'idle' | 'running' | 'complete' | 'stopped'
        providerCounts: {
            claude: 0,
            opus: 0,
            gemini: 0,
            glm: 0
        },
        _scrollTimeout: null,
        _validatorResetTimeout: null,  // Story 22.11: Cancelable progress reset

        // Story 22.11 Task 7: Validator progress tracking
        validatorProgress: {
            total: 0,
            completed: 0,
            failed: 0,
            validators: {}  // { validator_id: { status, duration_ms } }
        },

        // Terminal font size (px) - adjustable with Ctrl+scroll or Ctrl+/-
        terminalFontSize: 13,
        terminalFontSizeMin: 9,
        terminalFontSizeMax: 24,

        // Initialize terminal (called from main init)
        initTerminal() {
            // Load persisted terminal font size
            const savedFontSize = localStorage.getItem('bmad-terminal-font-size');
            if (savedFontSize) {
                const size = parseInt(savedFontSize, 10);
                if (size >= this.terminalFontSizeMin && size <= this.terminalFontSizeMax) {
                    this.terminalFontSize = size;
                }
            }
        },

        // Add output line
        addOutput(data) {
            const time = new Date(data.timestamp * 1000).toLocaleTimeString('en-US', { hour12: false });
            this.output.push({
                time,
                provider: data.provider,
                text: data.line
            });

            // Update provider counts (using lowercase keys to match SSE provider values)
            if (data.provider && this.providerCounts[data.provider] !== undefined) {
                this.providerCounts[data.provider]++;
            }

            // Limit output buffer and recalculate provider counts after trim
            if (this.output.length > 1000) {
                this.output = this.output.slice(-500);
                // Recalculate provider counts from remaining buffer
                this.recalculateProviderCounts();
            }

            // Check for loop end message from dashboard
            if (data.provider === 'dashboard' && data.line.includes('🏁 Loop ended')) {
                this.loopRunning = false;
                this.pauseRequested = false;
            }

            // Auto-scroll
            if (this.autoScroll) {
                this.$nextTick(() => this.scrollToBottom());
            }
        },

        // Get filtered output based on active tab
        get filteredOutput() {
            if (this.activeTab === 'All') {
                return this.output;
            }
            const provider = this.activeTab.toLowerCase();
            return this.output.filter(line => line.provider === provider);
        },

        // Get count for tab
        getTabCount(tab) {
            if (tab === 'All') return this.output.length;
            // Tab names are PascalCase, providerCounts keys are lowercase
            return this.providerCounts[tab.toLowerCase()] || 0;
        },

        // Recalculate provider counts from buffer
        recalculateProviderCounts() {
            // Reset all counts
            for (const key of Object.keys(this.providerCounts)) {
                this.providerCounts[key] = 0;
            }
            // Recount from remaining buffer
            for (const line of this.output) {
                if (line.provider && this.providerCounts[line.provider] !== undefined) {
                    this.providerCounts[line.provider]++;
                }
            }
        },

        // Format line with clickable file paths
        formatLine(text) {
            // Escape HTML entities first to prevent XSS
            const escaped = text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");

            // Convert file paths to clickable links (uses data-path for event delegation)
            // Supports: .py, .md, .yaml, .yml, .json, .toml, .ts, .js, .html, .css
            // Supports absolute paths starting with / or ~/
            // Excludes URL paths by requiring path to start at word boundary or start of string
            // and not be preceded by :// (protocol separator)
            return escaped.replace(
                /(?<![:/])((?:\/|~\/|(?<=\s))[\w\-\.\/]+\.(py|md|yaml|yml|json|toml|ts|js|html|css))(?=[\s,;:)"']|$)/g,
                '<a href="#" class="file-link text-bp-accent hover:underline" data-path="$1">$1</a>'
            );
        },

        // Handle click on terminal (event delegation for file links)
        handleTerminalClick(event) {
            // Event delegation for file links in terminal output
            const link = event.target.closest('.file-link');
            if (link) {
                event.preventDefault();
                const path = link.dataset.path;
                if (path) {
                    this.openFile(path);
                }
            }
        },

        // Open file (copy path to clipboard)
        openFile(path) {
            // Copy path to clipboard and show toast notification
            // Guard against non-secure contexts where clipboard API is unavailable
            if (!navigator.clipboard) {
                console.error('Clipboard API unavailable (requires secure context)');
                return;
            }
            navigator.clipboard.writeText(path)
                .then(() => {
                    this.showToast(`Path copied: ${path}`);
                })
                .catch(err => {
                    console.error('Clipboard write failed:', err);
                });
        },

        // Handle scroll event (detect manual scroll to disable auto-scroll)
        handleScroll(event) {
            // Debounce scroll handler (100ms)
            if (this._scrollTimeout) {
                clearTimeout(this._scrollTimeout);
            }
            this._scrollTimeout = setTimeout(() => {
                const el = event.target;
                const atBottom = el.scrollHeight - el.scrollTop <= el.clientHeight + 50;
                this.autoScroll = atBottom;
            }, 100);
        },

        // Scroll to bottom of terminal
        scrollToBottom() {
            const terminal = this.$refs.terminal;
            if (terminal) {
                terminal.scrollTop = terminal.scrollHeight;
                this.autoScroll = true;
            }
        },

        // Adjust terminal font size
        adjustTerminalFontSize(delta) {
            const newSize = this.terminalFontSize + delta;
            if (newSize >= this.terminalFontSizeMin && newSize <= this.terminalFontSizeMax) {
                this.terminalFontSize = newSize;
                localStorage.setItem('bmad-terminal-font-size', newSize);
            }
        },

        // Handle mouse wheel with Ctrl key for font size
        handleTerminalWheel(e) {
            if (e.ctrlKey) {
                e.preventDefault();
                // Scroll up = zoom in, scroll down = zoom out
                this.adjustTerminalFontSize(e.deltaY < 0 ? 1 : -1);
            }
        },

        // Handle keyboard shortcuts for font size
        handleTerminalKeydown(e) {
            if (e.ctrlKey && (e.key === '+' || e.key === '=' || e.key === 'NumpadAdd')) {
                e.preventDefault();
                this.adjustTerminalFontSize(1);
            } else if (e.ctrlKey && (e.key === '-' || e.key === 'NumpadSubtract')) {
                e.preventDefault();
                this.adjustTerminalFontSize(-1);
            } else if (e.ctrlKey && e.key === '0') {
                e.preventDefault();
                this.terminalFontSize = 13; // Reset to default
                localStorage.setItem('bmad-terminal-font-size', 13);
            }
        },

        // Get provider color class
        getProviderColor(provider) {
            const colors = {
                opus: 'provider-opus',
                gemini: 'provider-gemini',
                glm: 'provider-glm',
                claude: 'provider-claude'
            };
            return colors[provider] || 'provider-bmad';
        },

        // Story 22.11 Task 7: Handle validator progress event
        _handleValidatorProgress(data) {
            const { validator_id, status, duration_ms } = data.data || {};
            if (!validator_id) return;

            // Cancel pending reset if new validation is starting
            if (this._validatorResetTimeout) {
                clearTimeout(this._validatorResetTimeout);
                this._validatorResetTimeout = null;
            }

            // Track validator completion
            this.validatorProgress.validators[validator_id] = { status, duration_ms };

            // Update counts
            if (status === 'completed') {
                this.validatorProgress.completed++;
            } else if (status === 'timeout' || status === 'failed') {
                this.validatorProgress.failed++;
            }

            // Update total based on unique validators seen
            this.validatorProgress.total = Object.keys(this.validatorProgress.validators).length;

            console.debug(`Validator ${validator_id}: ${status}`,
                `(${this.validatorProgress.completed}/${this.validatorProgress.total})`);
        },

        // Story 22.11 Task 7: Handle phase complete event
        _handlePhaseComplete(data) {
            const { phase_name, success, validator_count, failed_count } = data.data || {};

            // Cancel any pending reset to prevent race condition
            if (this._validatorResetTimeout) {
                clearTimeout(this._validatorResetTimeout);
                this._validatorResetTimeout = null;
            }

            // Update final counts from authoritative source
            this.validatorProgress.total = validator_count || this.validatorProgress.total;
            this.validatorProgress.failed = failed_count || this.validatorProgress.failed;
            this.validatorProgress.completed = validator_count - failed_count;

            console.log(`Phase ${phase_name} complete:`,
                `${this.validatorProgress.completed}/${this.validatorProgress.total} succeeded`,
                success ? '(SUCCESS)' : '(FAILED)');

            // Reset progress after a delay to allow UI to show final state
            // Use cancelable timeout to prevent race condition with new validation
            this._validatorResetTimeout = setTimeout(() => {
                this.validatorProgress = {
                    total: 0,
                    completed: 0,
                    failed: 0,
                    validators: {}
                };
                this._validatorResetTimeout = null;
            }, 3000);
        },

        // Story 22.11 Task 7: Get validator progress percentage
        get validatorProgressPercent() {
            if (this.validatorProgress.total === 0) return 0;
            const done = this.validatorProgress.completed + this.validatorProgress.failed;
            return Math.round((done / this.validatorProgress.total) * 100);
        },

        // Story 22.11 Task 7: Check if validation is in progress
        get isValidating() {
            return this.validatorProgress.total > 0 &&
                (this.validatorProgress.completed + this.validatorProgress.failed) < this.validatorProgress.total;
        }
    };
};
