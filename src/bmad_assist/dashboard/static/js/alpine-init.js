/**
 * Alpine.js initialization for bmad-dashboard
 */

function dashboard() {
    return {
        // Connection state
        connected: false,
        eventSource: null,

        // Story 22.9: Dashboard event processing
        dashboardEventState: {
            currentRunId: null,
            lastSequenceId: 0,
            processedEvents: new Set(),
            eventBuffer: {},
        },

        // Data
        stories: {},
        output: [],

        // UI state
        expandedEpics: [],
        expandedStories: [],
        activeTab: 'All',
        autoScroll: true,
        loopRunning: false,
        pauseRequested: false,  // Pause requested, waiting for current workflow to complete
        isPaused: false,  // Story 22.10: Actual pause state (paused vs running)
        terminalStatus: 'idle',  // Story 22.11 Task 7.4: 'idle' | 'running' | 'complete' | 'stopped'

        // Context menu
        contextMenu: {
            show: false,
            ready: false,
            x: 0,
            y: 0,
            type: null,
            item: null,
            epic: null,
            story: null,
            actions: []
        },


        // Content modal (Story 16.9 - AC 3, 4)
        contentModal: {
            show: false,
            title: '',
            content: '',
            type: 'text'  // 'text' | 'xml' | 'markdown'
        },

        // Report list modal (Story 16.9 - AC 4)
        reportModal: {
            show: false,
            reports: [],
            synthesis: null,
            epic: '',
            story: ''
        },

        // Toast notification
        toast: {
            message: '',
            visible: false
        },

        // Settings view state (Story 17.4)
        settingsView: {
            open: false,           // Panel visibility
            scope: 'project',      // 'global' | 'project'
            activeTab: 'testing',  // 'testing' | 'benchmarking' | 'providers'
            loading: false,
            error: null,
            hasChanges: false,     // Enable/disable Apply button
            applying: false,       // Loading state for Apply button
            staleData: false       // Set true when SSE config_reloaded received while open
        },
        // Backups view state (Story 17.10)
        backupsView: {
            expanded: false,       // Collapsible section toggle
            loading: false,        // Loading state for backup list
            globalBackups: [],     // Global config backups
            projectBackups: [],    // Project config backups
            restoring: false,      // Restore operation in progress
            viewing: null          // Backup being viewed (null or {scope, version})
        },
        configData: {},            // Current config values with provenance
        globalConfigData: {},      // Global config for "Reset to global" functionality in project scope (Story 17.8)
        configSchema: null,        // Schema from /api/config/schema (fetched once, cached)
        pendingUpdates: [],        // Track changes before Apply (populated by Stories 17.5-17.7)
        validationErrors: {},      // Keyed by path, e.g., { 'testarch.playwright.timeout': 'Must be between...' }

        // Playwright status state (Story 17.11)
        playwrightStatus: {
            loading: false,
            data: null,      // Response from /api/playwright/status
            error: null,     // Error message if fetch failed
            lastFetch: 0,    // Timestamp of last successful fetch
            showCommands: false,  // Toggle for install commands section
        },
        // Debounce threshold (30 seconds)
        PLAYWRIGHT_STATUS_CACHE_MS: 30000,

        // Config Export/Import state (Story 17.12)
        exportView: {
            loading: false,
            dropdownOpen: false,
        },
        importView: {
            loading: false,
            modalOpen: false,
            filename: '',
            scope: 'project',   // Target scope for import
            diff: null,         // {added: {}, modified: {}, removed: []}
            riskyFields: [],    // Fields requiring confirmation
            errors: null,       // Validation errors or error string
            content: '',        // Raw YAML content (stored for scope switching)
        },

        // Experiments view state (Story 19.1)
        experimentsView: {
            open: false,           // Panel visibility
            activeTab: 'runs',     // Active tab: 'runs', 'fixtures' (Story 19.3), or 'templates' (Story 19.5)
            loading: false,        // Data fetch in progress
            error: null,           // Error message
            runs: [],              // List of experiment runs
            pagination: {          // Pagination state
                total: 0,
                offset: 0,
                limit: 20,
                has_more: false
            },
            filters: {             // Active filters
                status: '',
                fixture: '',
                config: '',
                patch_set: '',
                loop: '',
                start_date: '',
                end_date: ''
            },
            sort: {                // Sort state
                by: 'started',
                order: 'desc'
            },
            selected: [],          // Selected run IDs for comparison
        },

        // Experiment details view state (Story 19.2)
        experimentDetails: {
            open: false,           // Panel visibility
            loading: false,        // Data fetch in progress
            error: null,           // Error message
            runId: null,           // Current run ID being viewed
            data: null,            // ExperimentRunDetails data
        },

        // Fixtures view state (Story 19.3)
        fixturesView: {
            open: false,           // Panel visibility (tab is active)
            loading: false,        // Data fetch in progress
            error: null,           // Error message
            fixtures: [],          // List of fixtures
            total: 0,              // Total count
            filters: {             // Active filters
                difficulty: '',
                tags: ''
            },
            sort: {                // Sort state
                by: 'name',
                order: 'asc'
            },
            selectedFixture: null, // Selected fixture for details modal
        },

        // Templates view state (Story 19.5)
        templatesView: {
            open: false,           // Panel visibility (tab is active)
            loading: false,        // Data fetch in progress
            error: null,           // Error message
            activeSubTab: 'configs', // Active sub-tab: 'configs', 'loops', or 'patch-sets'
            configs: [],           // List of config templates
            loops: [],             // List of loop templates
            patchSets: [],         // List of patch-set manifests
            configsTotal: 0,       // Total configs count
            loopsTotal: 0,         // Total loops count
            patchSetsTotal: 0,     // Total patch-sets count
            sort: {                // Sort state
                by: 'name',
                order: 'asc'
            },
            selectedTemplate: null, // Selected template for details modal
        },

        // Comparison view state (Story 19.4)
        comparisonView: {
            open: false,           // Panel visibility
            loading: false,        // Data fetch in progress
            error: null,           // Error message
            runIds: [],            // Run IDs being compared
            report: null,          // ComparisonReport data
            exporting: false,      // Export in progress
        },

        // Run trigger view state (Story 19.6)
        runTrigger: {
            modalOpen: false,      // Modal visibility
            loading: false,        // Submit in progress
            error: null,           // Error message
            // Form fields
            fixture: '',           // Selected fixture
            config: '',            // Selected config
            patchSet: '',          // Selected patch-set
            loop: '',              // Selected loop
            // Available options (fetched from API)
            fixtures: [],          // Available fixtures
            configs: [],           // Available configs
            patchSets: [],         // Available patch-sets
            loops: [],             // Available loops
            optionsLoaded: false,  // Options have been loaded
        },

        // Active experiment run state (Story 19.6)
        activeExperiment: {
            runId: null,           // Currently running experiment ID
            status: null,          // Current status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
            phase: null,           // Current phase
            story: null,           // Current story
            position: null,        // Current position
            percent: 0,            // Progress percentage
            storiesCompleted: 0,   // Completed stories count
            storiesTotal: 0,       // Total stories count
            eventSource: null,     // SSE event source for progress streaming
        },

        // Self-reload timestamp for detecting external vs self-initiated config reloads (Story 17.9)
        _selfReloadTimestamp: 0,

        // Selection state (Story 16.5)
        selectedItem: {
            type: null,      // 'epic' | 'story' | 'phase'
            epic: null,      // Epic object
            story: null,     // Story object (if type is 'story' or 'phase')
            phase: null      // Phase object (if type is 'phase')
        },

        // Loading state (Story 16.5)
        loading: true,
        loadError: null,

        // Version info
        version: null,

        // Provider output counts
        providerCounts: {
            claude: 0,
            opus: 0,
            gemini: 0,
            glm: 0
        },
        _toastTimeout: null,
        _loopStatusInterval: null,

        // Terminal font size (px) - adjustable with Ctrl+scroll or Ctrl+/-
        terminalFontSize: 13,
        terminalFontSizeMin: 9,
        terminalFontSizeMax: 24,

        init() {
            // Load persisted terminal font size
            const savedFontSize = localStorage.getItem('bmad-terminal-font-size');
            if (savedFontSize) {
                const size = parseInt(savedFontSize, 10);
                if (size >= this.terminalFontSizeMin && size <= this.terminalFontSizeMax) {
                    this.terminalFontSize = size;
                }
            }

            this.connectSSE();
            this.fetchStories();
            this.checkLoopStatus();
            this.fetchVersion();
            // Initialize Lucide icons after Alpine mounts
            this.$nextTick(() => this.refreshIcons());

            // Poll loop status every 2 seconds to detect external runs
            // (CLI, context menu actions, etc.)
            this._loopStatusInterval = setInterval(() => {
                this.checkLoopStatus();
            }, 2000);
        },

        async fetchVersion() {
            try {
                const res = await fetch('/api/version');
                const data = await res.json();
                this.version = data.version;
            } catch (err) {
                console.error('Failed to fetch version:', err);
            }
        },

        // Refresh Lucide icons (call after DOM updates)
        refreshIcons() {
            if (typeof lucide !== 'undefined' && lucide.createIcons) {
                lucide.createIcons();
            }
        },

        connectSSE() {
            if (this.eventSource) {
                this.eventSource.close();
            }

            this.eventSource = new EventSource('/sse/output');

            this.eventSource.onopen = () => {
                this.connected = true;
                // Story 22.9: Reset reconnect delay on successful connection
                this._sseReconnectDelay = 1000;
                console.log('SSE connected');
                // Story 22.9: Resync state after reconnect (fetch fresh tree data)
                if (this._wasConnected) {
                    console.log('SSE reconnected, resyncing state...');
                    this.fetchStories();
                }
                this._wasConnected = true;
            };

            this.eventSource.onerror = () => {
                this.connected = false;
                // Story 22.11: Check readyState to distinguish EOF from temporary errors
                // readyState: 0=connecting, 1=open, 2=closed
                if (this.eventSource.readyState === 2) {
                    // Normal EOF (subprocess exited)
                    console.log('SSE connection closed (process ended)');
                    // Story 22.11 Task 7.2: Update terminal status on EOF
                    this.terminalStatus = 'complete';
                    // Don't reconnect on normal EOF - wait for user action or new workflow
                    return;
                }
                // Temporary error - reconnect with exponential backoff
                console.log('SSE error, reconnecting...');
                // Story 22.11 Task 7.4: Mark terminal as stopped on error
                this.terminalStatus = 'stopped';
                if (!this._sseReconnectDelay) {
                    this._sseReconnectDelay = 1000; // Start with 1s
                } else {
                    this._sseReconnectDelay = Math.min(this._sseReconnectDelay * 2, 8000); // Max 8s
                }
                setTimeout(() => this.connectSSE(), this._sseReconnectDelay);
            };

            this.eventSource.addEventListener('output', (e) => {
                const data = JSON.parse(e.data);
                this.addOutput(data);
            });

            this.eventSource.addEventListener('status', (e) => {
                const data = JSON.parse(e.data);
                if (data.connected) {
                    this.connected = true;
                }
            });

            this.eventSource.addEventListener('heartbeat', (e) => {
                // Keep-alive received
            });

            // Story 17.4 AC8 + Story 17.9 AC2/AC3: Handle config_reloaded SSE event
            // Self-reload detection window: SSE event from our own reload should arrive within this time
            const SELF_RELOAD_WINDOW_MS = 2000;
            this.eventSource.addEventListener('config_reloaded', (e) => {
                // Story 17.9 AC3: Skip notification if this is a self-reload (within detection window)
                if (this._selfReloadTimestamp && (Date.now() - this._selfReloadTimestamp) < SELF_RELOAD_WINDOW_MS) {
                    return;
                }

                // Story 17.9 AC2: External reload detected - show toast notification
                this.showToast('Configuration was reloaded externally.');

                // Set staleData flag if settings panel is open
                if (this.settingsView.open) {
                    this.settingsView.staleData = true;
                }
            });

            // Story 22.9: Handle workflow_status SSE event (phase transitions)
            this.eventSource.addEventListener('workflow_status', (e) => {
                this._handleDashboardEvent(e, 'workflow_status');
            });

            // Story 22.9: Handle story_status SSE event (story status changes)
            this.eventSource.addEventListener('story_status', (e) => {
                this._handleDashboardEvent(e, 'story_status');
            });

            // Story 22.9: Handle story_transition SSE event (story start/completion)
            this.eventSource.addEventListener('story_transition', (e) => {
                this._handleDashboardEvent(e, 'story_transition');
            });

            // Story 22.10 - Task 5: Handle LOOP_PAUSED SSE event
            this.eventSource.addEventListener('LOOP_PAUSED', (e) => {
                const data = JSON.parse(e.data);
                console.log('Loop paused event:', data);
                this.isPaused = true;
                this.pauseRequested = true;
                this.showToast('Loop paused');
            });

            // Story 22.10 - Task 5: Handle LOOP_RESUMED SSE event
            this.eventSource.addEventListener('LOOP_RESUMED', (e) => {
                const data = JSON.parse(e.data);
                console.log('Loop resumed event:', data);
                this.isPaused = false;
                this.pauseRequested = false;
                this.showToast('Loop resumed');
            });
        },

        async fetchStories() {
            try {
                const res = await fetch('/api/stories');
                if (!res.ok) {
                    throw new Error(`HTTP error! status: ${res.status}`);
                }
                this.stories = await res.json();
                this.loadError = null;
                // Refresh icons after tree view updates
                this.$nextTick(() => this.refreshIcons());
            } catch (err) {
                console.error('Failed to fetch stories:', err);
                this.loadError = 'Failed to load stories';
            } finally {
                this.loading = false;
            }
        },

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

        // Story 22.9: Dashboard event handlers for SSE status updates

        _handleDashboardEvent(event, expectedType) {
            // Parse and validate event data with sequence_id ordering
            try {
                const data = JSON.parse(event.data);

                // Validate required fields
                const requiredFields = ['type', 'timestamp', 'run_id', 'sequence_id', 'data'];
                const missingFields = requiredFields.filter(f => !(f in data));
                if (missingFields.length > 0) {
                    console.warn(`Dashboard event missing required fields: ${missingFields.join(', ')}`, data);
                    return;
                }

                // Check event type matches expected
                if (data.type !== expectedType) {
                    console.warn(`Event type mismatch: expected ${expectedType}, got ${data.type}`);
                    return;
                }

                // Fix: Reset sequence state when run_id changes (new bmad-assist run)
                if (this.dashboardEventState.currentRunId !== data.run_id) {
                    console.debug(`New run detected: ${data.run_id}, resetting sequence state`);
                    this.dashboardEventState.currentRunId = data.run_id;
                    this.dashboardEventState.lastSequenceId = 0;
                    this.dashboardEventState.eventBuffer = {};
                    this.dashboardEventState.processedEvents.clear();
                }

                // Check for duplicate events
                const eventKey = `${data.type}-${data.run_id}-${data.sequence_id}`;
                if (this.dashboardEventState.processedEvents.has(eventKey)) {
                    console.debug(`Duplicate event discarded: ${eventKey}`);
                    return;
                }

                // Buffer events by sequence_id for ordered processing
                if (data.sequence_id > this.dashboardEventState.lastSequenceId + 1) {
                    // Out-of-order event - buffer it
                    console.debug(`Buffering out-of-order event: sequence_id=${data.sequence_id}, last=${this.dashboardEventState.lastSequenceId}`);
                    this.dashboardEventState.eventBuffer[data.sequence_id] = data;
                    return;
                }

                // Process this event and any buffered events in sequence
                this._processDashboardEvent(data);

                // Process any buffered events that are now in sequence
                let nextSeq = data.sequence_id + 1;
                while (this.dashboardEventState.eventBuffer[nextSeq]) {
                    this._processDashboardEvent(this.dashboardEventState.eventBuffer[nextSeq]);
                    delete this.dashboardEventState.eventBuffer[nextSeq];
                    nextSeq++;
                }

            } catch (err) {
                console.error('Failed to parse dashboard event:', err, event.data);
            }
        },

        _processDashboardEvent(data) {
            // Process a validated, in-order dashboard event
            const eventKey = `${data.type}-${data.run_id}-${data.sequence_id}`;

            // Mark as processed
            this.dashboardEventState.processedEvents.add(eventKey);
            this.dashboardEventState.lastSequenceId = data.sequence_id;

            // Clean up old processed events (keep last 1000)
            if (this.dashboardEventState.processedEvents.size > 1000) {
                const entries = Array.from(this.dashboardEventState.processedEvents);
                const toKeep = entries.slice(-1000);
                this.dashboardEventState.processedEvents = new Set(toKeep);
            }

            // Dispatch to specific handler
            switch (data.type) {
                case 'workflow_status':
                    this._handleWorkflowStatus(data);
                    break;
                case 'story_status':
                    this._handleStoryStatus(data);
                    break;
                case 'story_transition':
                    this._handleStoryTransition(data);
                    break;
                default:
                    console.warn(`Unknown dashboard event type: ${data.type}`);
            }
        },

        _handleWorkflowStatus(data) {
            // Update reactive state for phase transitions
            console.debug('Workflow status:', data.data);

            // Find and update the story in the stories tree
            this._updateStoryPhase(data.data);
        },

        _handleStoryStatus(data) {
            // Update story status badge
            console.debug('Story status:', data.data);

            // Find and update the story status in the stories tree
            this._updateStoryStatus(data.data);
        },

        _handleStoryTransition(data) {
            // Handle story start/completion with highlighting
            console.debug('Story transition:', data.data);

            // Update the stories tree
            this._updateStoryTransition(data.data);
        },

        _updateStoryPhase(phaseData) {
            // Update the current phase for a story in the stories tree
            if (!this.stories.epics) return;

            const storyId = phaseData.current_story;
            const [epicNum, storyNum] = storyId.split('.').map(n => parseInt(n, 10));

            // Find the epic
            const epic = this.stories.epics.find(e => e.id === epicNum);
            if (!epic) return;

            // Find the story
            const story = epic.stories.find(s => s.id === storyNum);
            if (!story) return;

            // Update current phase status
            if (story.phases) {
                story.phases.forEach(phase => {
                    if (phase.name === phaseData.current_phase) {
                        phase.status = phaseData.phase_status;
                    }
                });
            }
        },

        _updateStoryStatus(statusData) {
            // Update the status badge for a story in the stories tree
            if (!this.stories.epics) return;

            const epic = this.stories.epics.find(e => e.id === statusData.epic_num);
            if (!epic) return;

            const story = epic.stories.find(s => s.id === statusData.story_num);
            if (!story) return;

            // Update story status
            story.status = statusData.status;
        },

        _updateStoryTransition(transitionData) {
            // Handle story transitions with highlighting
            if (!this.stories.epics) return;

            const epic = this.stories.epics.find(e => e.id === transitionData.epic_num);
            if (!epic) return;

            const story = epic.stories.find(s => s.id === transitionData.story_num);
            if (!story) return;

            // Update story status based on action
            if (transitionData.action === 'started') {
                story.status = 'in-progress';
                // Auto-expand the epic and story for visibility
                if (!this.expandedEpics.includes(epic.id)) {
                    this.expandedEpics.push(epic.id);
                }
                const storyKey = `${epic.id}-${story.id}`;
                if (!this.expandedStories.includes(storyKey)) {
                    this.expandedStories.push(storyKey);
                }
            } else if (transitionData.action === 'completed') {
                story.status = 'done';
            }
        },

        get filteredOutput() {
            if (this.activeTab === 'All') {
                return this.output;
            }
            const provider = this.activeTab.toLowerCase();
            return this.output.filter(line => line.provider === provider);
        },

        getTabCount(tab) {
            if (tab === 'All') return this.output.length;
            // Tab names are PascalCase, providerCounts keys are lowercase
            return this.providerCounts[tab.toLowerCase()] || 0;
        },

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

        getProviderColor(provider) {
            const colors = {
                opus: 'provider-opus',
                gemini: 'provider-gemini',
                glm: 'provider-glm',
                claude: 'provider-claude'
            };
            return colors[provider] || 'provider-bmad';
        },

        getStatusColor(status) {
            const colors = {
                done: 'bg-accent',
                'in-progress': 'bg-primary',
                review: 'bg-bp-warning',
                'ready-for-dev': 'bg-chart-3',
                backlog: 'bg-border'
            };
            return colors[status] || 'bg-border';
        },

        getStatusTextColor(status) {
            // Text colors for icons (uses stroke via currentColor)
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
        },

        getStatusIcon(status) {
            // Returns Lucide icon name for story status
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
        },

        getEpicStatusIcon(status) {
            // Returns Lucide icon name for epic status
            const icons = {
                done: 'folder-check',
                'in-progress': 'folder-open',
                deferred: 'pause-circle',
                draft: 'folder',
                backlog: 'folder'
            };
            return icons[status] || 'folder';
        },

        getPhaseIcon(status) {
            // Returns Lucide icon name for phase status
            const icons = {
                completed: 'check-circle',
                'in-progress': 'play-circle',
                pending: 'circle-dashed'
            };
            return icons[status] || 'circle-dashed';
        },

        getPhaseTextColor(status) {
            // Text colors for phase icons
            const colors = {
                completed: 'text-accent',
                'in-progress': 'text-primary',
                pending: 'text-muted-foreground'
            };
            return colors[status] || 'text-muted-foreground';
        },

        getActionIcon(emoji) {
            // Maps context menu emoji icons to Lucide icon names
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
        },

        toggleEpic(epicId) {
            const idx = this.expandedEpics.indexOf(epicId);
            if (idx === -1) {
                this.expandedEpics.push(epicId);
            } else {
                this.expandedEpics.splice(idx, 1);
            }
            // Re-render Lucide icons after state change
            this.$nextTick(() => this.refreshIcons());
        },

        toggleStory(storyKey) {
            const idx = this.expandedStories.indexOf(storyKey);
            if (idx === -1) {
                this.expandedStories.push(storyKey);
            } else {
                this.expandedStories.splice(idx, 1);
            }
            // Re-render Lucide icons after state change
            this.$nextTick(() => this.refreshIcons());
        },

        // Selection function (Story 16.5)
        selectItem(type, epic, story = null, phase = null) {
            this.selectedItem = { type, epic, story, phase };
            // Re-render Lucide icons in Detail Panel after selection change
            this.$nextTick(() => this.refreshIcons());
        },

        // Reset dashboard to initial state (logo click)
        resetDashboard() {
            // Clear selection
            this.selectedItem = { type: null, epic: null, story: null, phase: null };
            // Collapse all tree nodes
            this.expandedEpics = [];
            this.expandedStories = [];
            // Reset tab to All
            this.activeTab = 'All';
            // Enable auto-scroll
            this.autoScroll = true;
            // Scroll terminal to bottom
            this.$nextTick(() => {
                this.scrollToBottom();
                this.refreshIcons();
            });
        },

        // Epic progress helper (Story 16.5)
        getEpicProgress(epic) {
            if (!epic || !epic.stories) return '0/0 (0%)';
            const done = epic.stories.filter(s => s.status === 'done').length;
            const total = epic.stories.length;
            const pct = total > 0 ? Math.round((done / total) * 100) : 0;
            return `${done}/${total} (${pct}%)`;
        },

        showContextMenu(event, type, item, epic = null, story = null, source = 'rightclick') {
            // Calculate initial position based on source
            let x, y;
            if (source === 'kebab') {
                // Position 4px below the kebab button
                const button = event.currentTarget;
                const rect = button.getBoundingClientRect();
                x = rect.left;
                y = rect.bottom + 4;
            } else {
                // Position at cursor for right-click
                x = event.clientX;
                y = event.clientY;
            }

            this.contextMenu.x = x + 20;  // Shift right for better visibility
            this.contextMenu.y = y;
            this.contextMenu.type = type;
            this.contextMenu.item = item;
            this.contextMenu.epic = epic;
            this.contextMenu.story = story;
            this.contextMenu.actions = this.getContextActions(type, item);
            this.contextMenu.ready = false;  // Start invisible for flicker-free positioning
            this.contextMenu.show = true;

            // Adjust position after render to ensure menu stays in viewport
            this.$nextTick(() => {
                const adjusted = this.positionContextMenu(this.contextMenu.x, this.contextMenu.y);
                this.contextMenu.x = adjusted.x;
                this.contextMenu.y = adjusted.y;
                this.contextMenu.ready = true;  // Reveal menu after positioning
                // Refresh Lucide icons in context menu
                this.refreshIcons();
                // Focus menu for keyboard support
                if (this.$refs.contextMenuEl) {
                    this.$refs.contextMenuEl.focus();
                }
            });
        },

        positionContextMenu(x, y) {
            const menu = this.$refs.contextMenuEl;
            if (!menu) return { x, y };

            const rect = menu.getBoundingClientRect();
            const padding = 8;

            // Adjust horizontal position if menu would render off right edge
            if (x + rect.width > window.innerWidth - padding) {
                x = Math.max(padding, window.innerWidth - rect.width - padding);
            }

            // Adjust vertical position if menu would render off bottom edge
            if (y + rect.height > window.innerHeight - padding) {
                y = Math.max(padding, window.innerHeight - rect.height - padding);
            }

            return { x, y };
        },

        getContextActions(type, item) {
            if (type === 'epic') {
                // View metrics is disabled if epic is not done (no metrics yet)
                const hasMetrics = item?.status === 'done';
                return [
                    { icon: '📄', label: 'View details', action: 'view-epic', testId: 'action-view-epic' },
                    { icon: '📊', label: 'View metrics', action: 'view-metrics', testId: 'action-view-metrics', disabled: !hasMetrics },
                    { icon: '▶️', label: 'Start next story', action: 'start-next', testId: 'action-start-next' }
                ];
            }

            if (type === 'story') {
                return this.getStoryActions(item);
            }

            if (type === 'phase') {
                return this.getPhaseActions(item);
            }

            return [];
        },

        getStoryActions(story) {
            const status = story?.status || 'backlog';

            // Status-based action mapping per AC 3, 4, 6
            switch (status) {
                case 'backlog':
                    return [
                        { icon: '📄', label: 'View in epic', action: 'view-story', testId: 'action-view-story' }
                    ];

                case 'ready-for-dev':
                    return [
                        { icon: '▶️', label: 'Run dev-story', action: 'run-dev-story', testId: 'action-run-dev-story', primary: true },
                        { icon: '📋', label: 'View prompt', action: 'view-prompt', testId: 'action-view-prompt' },
                        { icon: '📝', label: 'Open story file', action: 'open-file', testId: 'action-open-file' }
                    ];

                case 'in-progress':
                    return [
                        { icon: '📋', label: 'View prompt', action: 'view-prompt', testId: 'action-view-prompt' },
                        { icon: '📝', label: 'Open story file', action: 'open-file', testId: 'action-open-file' }
                    ];

                case 'review':
                    return [
                        { icon: '📋', label: 'View prompt', action: 'view-prompt', testId: 'action-view-prompt' },
                        { icon: '📝', label: 'Open story file', action: 'open-file', testId: 'action-open-file' },
                        { icon: '👀', label: 'View review', action: 'view-review', testId: 'action-view-review' }
                    ];

                case 'done':
                    return [
                        { icon: '📋', label: 'View prompt', action: 'view-prompt', testId: 'action-view-prompt' },
                        { icon: '👀', label: 'View review', action: 'view-review', testId: 'action-view-review' },
                        { icon: '🔄', label: 'Re-run', action: 're-run', testId: 'action-re-run', danger: true }
                    ];

                default:
                    return [
                        { icon: '📄', label: 'View in epic', action: 'view-story', testId: 'action-view-story' }
                    ];
            }
        },

        getPhaseActions(phase) {
            const phaseName = phase?.name || '';
            const phaseStatus = phase?.status || 'pending';
            const actions = [];

            // Base action: View prompt (only available when phase is completed)
            if (phaseStatus === 'completed') {
                actions.push({ icon: '📋', label: 'View prompt', action: 'view-prompt', testId: 'action-view-prompt' });
            }

            // Phase-specific actions per wireframe 3b/3c (exact string matching for safety)
            if (phaseName === 'create-story') {
                // View story file only when create-story is completed
                if (phaseStatus === 'completed') {
                    actions.push({ icon: '📄', label: 'View story file', action: 'view-story-file', testId: 'action-view-story-file' });
                }
            } else if (phaseName === 'validate' || phaseName === 'validate (multi-llm)') {
                actions.push({ icon: '📊', label: 'View validation reports', action: 'view-validation-reports', testId: 'action-view-validation-reports' });
                actions.push({ icon: '📝', label: 'View synthesis', action: 'view-synthesis', testId: 'action-view-synthesis' });
            } else if (phaseName === 'dev-story') {
                actions.push({ icon: '📄', label: 'View story output', action: 'view-story-output', testId: 'action-view-story-output' });
            } else if (phaseName === 'code-review' || phaseName === 'code-review (multi-llm)') {
                actions.push({ icon: '📊', label: 'View review reports', action: 'view-review-reports', testId: 'action-view-review-reports' });
                actions.push({ icon: '📝', label: 'View synthesis', action: 'view-synthesis', testId: 'action-view-synthesis' });
            } else if (phaseName === 'atdd') {
                actions.push({ icon: '✅', label: 'View ATDD checklist', action: 'view-atdd-checklist', testId: 'action-view-atdd-checklist' });
            }

            // Common actions for all phases (separator before destructive section per wireframe 3b)
            actions.push({ icon: '🔄', label: 'Re-run this phase', action: 're-run-phase', testId: 'action-re-run-phase', danger: true });
            actions.push({ icon: '⏭️', label: 'Skip to next phase', action: 'skip-phase', testId: 'action-skip-phase', danger: true });

            return actions;
        },

        async executeAction(action) {
            this.contextMenu.show = false;
            this.contextMenu.ready = false;

            const { type, item, epic, story } = this.contextMenu;

            switch (action.action) {
                // Epic actions
                case 'view-epic':
                    await this.viewEpicDetails(item?.id);
                    break;
                case 'view-metrics':
                    console.log('View epic metrics:', item?.id);
                    break;
                case 'start-next':
                    await this.startNextStory(item);
                    break;

                // Story actions
                case 'run-dev-story':
                    await this.runWorkflow('dev-story', epic?.id, item.id);
                    break;
                case 're-run':
                    // Re-run completed story (dangerous)
                    await this.runWorkflow('dev-story', epic?.id, item.id);
                    break;
                case 'view-prompt':
                    await this.viewPrompt(epic?.id, story?.id || item?.id, item?.name || 'dev-story');
                    break;
                case 'open-file':
                    // Copy story file path to clipboard
                    if (item?.file_path) {
                        this.openFile(item.file_path);
                    } else {
                        // Construct path from story info
                        const storyPath = `_bmad-output/implementation-artifacts/stories/${epic?.id}-${item?.id}-*.md`;
                        this.openFile(storyPath);
                    }
                    break;
                case 'view-review':
                    await this.viewReports(epic?.id, story?.id || item?.id);
                    break;
                case 'view-story':
                    await this.viewStoryInEpic(epic?.id, item?.id);
                    break;

                // Phase actions
                case 'view-story-file':
                    // View the story file from create-story phase
                    console.log('View story file for phase:', item?.name);
                    break;
                case 'view-validation-reports':
                    await this.viewReports(epic?.id, story?.id);
                    break;
                case 'view-synthesis':
                    console.log('View synthesis report:', epic?.id, story?.id, item?.name);
                    break;
                case 'view-story-output':
                    console.log('View story output:', epic?.id, story?.id);
                    break;
                case 'view-review-reports':
                    await this.viewReports(epic?.id, story?.id);
                    break;
                case 'view-atdd-checklist':
                    console.log('View ATDD checklist:', epic?.id, story?.id);
                    break;
                case 're-run-phase':
                    await this.runWorkflow(item.name, epic?.id, story?.id);
                    break;
                case 'skip-phase':
                    console.warn('Skip phase API not yet implemented - deferred to future backend story');
                    this.showToast('Skip phase not yet implemented');
                    break;

                default:
                    console.log('Unhandled action:', action.action, item);
            }
        },

        async viewPrompt(epic, story, phase) {
            try {
                const res = await fetch(`/api/prompt/${epic}/${story}/${phase}`);
                if (res.ok) {
                    const text = await res.text();
                    // AC 4.2-4.4: Set modal state and show
                    this.contentModal.title = `Template: ${phase}`;
                    this.contentModal.content = text;
                    this.contentModal.type = 'xml';
                    this.contentModal.show = true;
                } else if (res.status === 404) {
                    // AC 4.5: Show toast on 404
                    const data = await res.json();
                    this.showToast(data.error || `Template not found for phase: ${phase}`);
                } else {
                    throw new Error(`HTTP ${res.status}`);
                }
            } catch (err) {
                // AC 4.6: Show toast on network error
                console.error('Failed to fetch prompt:', err);
                this.showToast('Failed to fetch template');
            }
        },

        async viewReports(epic, story) {
            try {
                const res = await fetch(`/api/validation/${epic}/${story}`);
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}`);
                }
                const data = await res.json();
                // AC 6.2: Populate reportModal state
                this.reportModal.epic = epic;
                this.reportModal.story = story;
                this.reportModal.reports = data.reports || [];
                this.reportModal.synthesis = data.synthesis || null;
                this.reportModal.show = true;
            } catch (err) {
                console.error('Failed to fetch reports:', err);
                this.showToast('Failed to fetch validation reports');
            }
        },

        // AC 6.3: Load report content and display in content modal
        async loadReportContent(report) {
            try {
                const res = await fetch(`/api/report/content?path=${encodeURIComponent(report.path)}`);
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.error || `HTTP ${res.status}`);
                }
                const content = await res.text();
                // AC 6.4: Display in contentModal with provider attribution
                const title = report.provider ? `Report: ${report.provider}` : 'Synthesis Report';
                this.contentModal.title = title;
                this.contentModal.content = content;
                this.contentModal.type = 'markdown';
                this.contentModal.show = true;
            } catch (err) {
                console.error('Failed to load report content:', err);
                this.showToast(`Failed to load report: ${err.message}`);
            }
        },

        // View epic details in modal
        async viewEpicDetails(epicId) {
            try {
                const res = await fetch(`/api/epics/${epicId}`);
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.error || `HTTP ${res.status}`);
                }
                const data = await res.json();
                // Display epic content in contentModal
                this.contentModal.title = `Epic ${data.id}: ${data.title}`;
                this.contentModal.content = data.content;
                this.contentModal.type = 'markdown';
                this.contentModal.show = true;
            } catch (err) {
                console.error('Failed to fetch epic details:', err);
                this.showToast('Failed to load epic details');
            }
        },

        // View story content from epic file
        async viewStoryInEpic(epicId, storyId) {
            try {
                const res = await fetch(`/api/epics/${epicId}/stories/${storyId}`);
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.error || `HTTP ${res.status}`);
                }
                const data = await res.json();
                // Display story content in contentModal with markdown rendering
                this.contentModal.title = `Story ${data.epic_id}.${data.id}: ${data.title}`;
                this.contentModal.content = data.content;
                this.contentModal.type = 'markdown';
                this.contentModal.show = true;
            } catch (err) {
                console.error('Failed to fetch story from epic:', err);
                this.showToast('Failed to load story from epic');
            }
        },

        // Start next story in epic (first story not done, first pending phase)
        async startNextStory(epic) {
            if (!epic || !epic.stories) {
                this.showToast('No stories found in epic');
                return;
            }

            // Find first story that's not done
            const nextStory = epic.stories.find(s => s.status !== 'done');

            if (!nextStory) {
                this.showToast('All stories in epic are done');
                return;
            }

            // Find first pending phase in this story
            const nextPhase = nextStory.phases?.find(p => p.status === 'pending');

            if (!nextPhase) {
                this.showToast(`Story ${epic.id}.${nextStory.id} has no pending phases`);
                return;
            }

            // Map phase name to workflow name
            const phaseToWorkflow = {
                'create-story': 'create-story',
                'validate': 'validate',
                'validation-synthesis': 'validate-synthesis',
                'dev-story': 'dev-story',
                'code-review': 'code-review',
                'review-synthesis': 'review-synthesis',
            };

            const workflow = phaseToWorkflow[nextPhase.name];
            if (!workflow) {
                this.showToast(`Unknown workflow for phase: ${nextPhase.name}`);
                return;
            }

            console.log(`Starting ${workflow} for story ${epic.id}.${nextStory.id}`);
            await this.runWorkflow(workflow, epic.id, nextStory.id);
        },

        // Story 16.9 AC 7.2: Toast helper (wraps existing toast state)
        showToast(message, duration = 3000) {
            this.toast = { message, visible: true };
            if (this._toastTimeout) clearTimeout(this._toastTimeout);
            this._toastTimeout = setTimeout(() => { this.toast.visible = false; }, duration);
        },

        // Story 16.9 AC 7.3: Copy to clipboard helper
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

        async runWorkflow(workflow, epicNum, storyNum) {
            // Start the bmad-assist loop - it reads sprint-status.yaml to find current position
            if (this.loopRunning) {
                this.showToast('Loop is already running');
                return;
            }

            try {
                const res = await fetch('/api/loop/start', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'started') {
                    this.showToast('Starting bmad-assist run loop...');
                } else {
                    this.showToast(data.message || 'Failed to start loop');
                }
            } catch (err) {
                console.error('Failed to start loop:', err);
                this.showToast('Failed to start loop');
            }
        },

        // Focus trap for modal (cycles Tab focus within modal boundaries)
        // refName: Optional ref name (defaults to 'busyModalContent' for backwards compatibility)
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

        scrollToBottom() {
            const terminal = this.$refs.terminal;
            if (terminal) {
                terminal.scrollTop = terminal.scrollHeight;
                this.autoScroll = true;
            }
        },

        // Terminal font size controls (Ctrl+scroll, Ctrl+/-)
        adjustTerminalFontSize(delta) {
            const newSize = this.terminalFontSize + delta;
            if (newSize >= this.terminalFontSizeMin && newSize <= this.terminalFontSizeMax) {
                this.terminalFontSize = newSize;
                localStorage.setItem('bmad-terminal-font-size', newSize);
            }
        },

        handleTerminalWheel(e) {
            if (e.ctrlKey) {
                e.preventDefault();
                // Scroll up = zoom in, scroll down = zoom out
                this.adjustTerminalFontSize(e.deltaY < 0 ? 1 : -1);
            }
        },

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

        async startLoop() {
            try {
                const response = await fetch('/api/loop/start', { method: 'POST' });
                const data = await response.json();
                console.log('Start loop response:', data);
                if (data.status === 'started') {
                    this.loopRunning = true;
                    // Story 22.11 Task 7.4: Update terminal status on start
                    this.terminalStatus = 'running';
                }
            } catch (error) {
                console.error('Failed to start loop:', error);
            }
        },

        async pauseLoop() {
            if (this.pauseRequested) {
                this.showToast('Pause already requested');
                return;
            }
            try {
                const response = await fetch('/api/loop/pause', { method: 'POST' });
                const data = await response.json();
                console.log('Pause loop response:', data);
                if (data.status === 'pause_requested') {
                    this.pauseRequested = true;
                    this.showToast('Pause requested - will stop after current workflow completes');
                } else if (data.status === 'already_paused') {
                    this.pauseRequested = true;
                }
            } catch (error) {
                console.error('Failed to pause loop:', error);
                this.showToast('Failed to pause loop');
            }
        },

        // Story 22.10 - Task 4: Resume functionality
        async resumeLoop() {
            if (!this.isPaused) {
                this.showToast('Loop is not paused');
                return;
            }
            try {
                const response = await fetch('/api/loop/resume', { method: 'POST' });
                const data = await response.json();
                console.log('Resume loop response:', data);
                if (data.status === 'resumed') {
                    this.pauseRequested = false;
                    this.showToast('Resuming loop...');
                } else if (data.status === 'not_paused') {
                    this.isPaused = false;
                    this.pauseRequested = false;
                    this.showToast('Loop was not paused');
                } else if (data.status === 'not_running') {
                    this.showToast('Loop is not running');
                }
            } catch (error) {
                console.error('Failed to resume loop:', error);
                this.showToast('Failed to resume loop');
            }
        },

        async stopLoop() {
            try {
                const response = await fetch('/api/loop/stop', { method: 'POST' });
                const data = await response.json();
                console.log('Stop loop response:', data);
                if (data.status === 'stopped') {
                    this.loopRunning = false;
                    this.pauseRequested = false;
                    this.isPaused = false;  // Story 22.10: Clear paused state on stop
                    // Story 22.11 Task 7.4: Update terminal status on stop
                    this.terminalStatus = 'stopped';
                    this.showToast('Loop stopped');
                }
            } catch (error) {
                console.error('Failed to stop loop:', error);
                this.showToast('Failed to stop loop');
            }
        },

        async checkLoopStatus() {
            try {
                const response = await fetch('/api/loop/status');
                const data = await response.json();
                this.loopRunning = data.running;
                // Story 22.10: Update paused state from status endpoint
                if (data.status === 'paused') {
                    this.isPaused = true;
                    this.pauseRequested = true;
                } else if (data.status === 'running') {
                    this.isPaused = false;
                }
            } catch (error) {
                console.error('Failed to check loop status:', error);
            }
        },

        // ==========================================
        // Settings Panel Methods (Story 17.4)
        // ==========================================

        /**
         * Open settings panel and load config data
         * Story 17.11 AC6: Fetch Playwright status if testing tab is active
         */
        openSettings() {
            this.settingsView.open = true;
            this.settingsView.loading = true;
            this.settingsView.error = null;
            this.settingsView.staleData = false;

            Promise.all([
                this.fetchSchema(),
                this.fetchConfig()
            ]).finally(() => {
                this.settingsView.loading = false;
                // Story 17.11 AC6: Fetch Playwright status if testing tab is active
                if (this.settingsView.activeTab === 'testing') {
                    this.fetchPlaywrightStatus();
                }
                this.$nextTick(() => {
                    this.refreshIcons();
                    // Focus close button on open (AC1)
                    if (this.$refs.settingsCloseBtn) {
                        this.$refs.settingsCloseBtn.focus();
                    }
                });
            });
        },

        /**
         * Close settings panel with unsaved changes warning
         */
        closeSettings() {
            if (this.settingsView.hasChanges) {
                if (!confirm('You have unsaved changes. Discard and close?')) {
                    return;
                }
            }
            this.settingsView.open = false;
            this.settingsView.staleData = false;
            this.pendingUpdates = [];
            this.validationErrors = {};
            this.settingsView.hasChanges = false;
            // Return focus to Settings button (AC1)
            this.$nextTick(() => {
                if (this.$refs.settingsBtn) {
                    this.$refs.settingsBtn.focus();
                }
            });
        },

        /**
         * Toggle scope between global and project
         */
        toggleScope(newScope) {
            if (newScope === this.settingsView.scope) return;

            if (this.settingsView.hasChanges) {
                if (!confirm('You have unsaved changes. Switching scope will discard them. Continue?')) {
                    return;
                }
            }

            this.settingsView.scope = newScope;
            this.pendingUpdates = [];
            this.validationErrors = {};
            this.settingsView.hasChanges = false;
            this.settingsView.staleData = false;
            this.settingsView.loading = true;
            this.settingsView.error = null;

            this.fetchConfig().finally(() => {
                this.settingsView.loading = false;
                this.$nextTick(() => this.refreshIcons());
            });
        },

        /**
         * Switch active settings tab
         * Story 17.11 AC6: Fetch Playwright status when switching to testing tab
         */
        setSettingsTab(tab) {
            this.settingsView.activeTab = tab;
            // Fetch Playwright status when switching to testing tab
            if (tab === 'testing') {
                this.fetchPlaywrightStatus();
            }
            this.$nextTick(() => this.refreshIcons());
        },

        /**
         * Fetch config schema (once, cached)
         */
        async fetchSchema() {
            // Skip if already cached
            if (this.configSchema) return;

            try {
                const res = await fetch('/api/config/schema');
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}`);
                }
                this.configSchema = await res.json();
            } catch (err) {
                console.error('Failed to fetch config schema:', err);
                // Schema fetch failure is non-critical, just log it
            }
        },

        /**
         * Fetch config data based on current scope (AC2)
         * Story 17.8: Also fetch global config when in project scope for "Reset to global" functionality
         */
        async fetchConfig() {
            try {
                this.settingsView.error = null;
                const scope = this.settingsView.scope;

                if (scope === 'project') {
                    // Story 17.8 AC7: Fetch both project and global configs in parallel
                    // Global config needed for "Reset to global" functionality
                    const [projectRes, globalRes] = await Promise.all([
                        fetch('/api/config/project'),
                        fetch('/api/config/global')
                    ]);
                    if (!projectRes.ok) {
                        throw new Error(`HTTP ${projectRes.status}`);
                    }
                    if (!globalRes.ok) {
                        throw new Error(`HTTP ${globalRes.status}`);
                    }
                    this.configData = await projectRes.json();
                    this.globalConfigData = await globalRes.json();
                } else {
                    // Global scope - only need global config
                    const res = await fetch('/api/config/global');
                    if (!res.ok) {
                        throw new Error(`HTTP ${res.status}`);
                    }
                    this.configData = await res.json();
                    this.globalConfigData = {};  // Not needed in global scope
                }
            } catch (err) {
                console.error('Failed to fetch config:', err);
                this.settingsView.error = 'Failed to load configuration';
            }
        },

        /**
         * Retry fetching config after error
         */
        retryFetchConfig() {
            this.settingsView.loading = true;
            this.settingsView.error = null;
            Promise.all([
                this.fetchSchema(),
                this.fetchConfig()
            ]).finally(() => {
                this.settingsView.loading = false;
                this.$nextTick(() => this.refreshIcons());
            });
        },

        /**
         * Reload config data (for stale data warning)
         */
        reloadConfigData() {
            if (this.settingsView.hasChanges) {
                if (!confirm('Reloading will discard your unsaved changes.')) {
                    return;
                }
            }
            this.pendingUpdates = [];
            this.validationErrors = {};
            this.settingsView.hasChanges = false;
            this.settingsView.staleData = false;
            this.settingsView.loading = true;
            this.fetchConfig().finally(() => {
                this.settingsView.loading = false;
                this.$nextTick(() => this.refreshIcons());
            });
        },

        /**
         * Apply config changes: save then reload
         * Handles 428 Precondition Required for RISKY fields (AC5)
         */
        async applyConfig() {
            if (!this.settingsView.hasChanges || this.settingsView.applying) {
                return;
            }

            this.settingsView.applying = true;

            try {
                // Step 1: Save changes to appropriate scope
                const scope = this.settingsView.scope;
                const endpoint = scope === 'global' ? '/api/config/global' : '/api/config/project';

                const saveRes = await fetch(endpoint, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ updates: this.pendingUpdates })
                });

                // Handle 428 Precondition Required (RISKY fields) - Story 17.6 AC5
                if (saveRes.status === 428) {
                    const data = await saveRes.json().catch(() => ({}));
                    const riskyFields = data.risky_fields || [];
                    console.log('RISKY fields requiring confirmation:', riskyFields);

                    // Show confirmation dialog
                    const confirmed = confirm(
                        `The following settings require confirmation:\n\n` +
                        `• ${riskyFields.join('\n• ')}\n\n` +
                        `Modifying these could affect workflow behavior. Continue?`
                    );

                    if (!confirmed) {
                        // User cancelled - keep pendingUpdates, reset applying state
                        this.settingsView.applying = false;
                        return;
                    }

                    // Retry with confirmed: true
                    const retryRes = await fetch(endpoint, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ updates: this.pendingUpdates, confirmed: true })
                    });

                    if (retryRes.status === 428) {
                        // Unexpected second 428
                        this.showToast('Unexpected error - please try again');
                        this.settingsView.applying = false;
                        return;
                    }

                    if (!retryRes.ok) {
                        const errData = await retryRes.json().catch(() => ({}));
                        throw new Error(errData.error || `Save failed after confirmation: HTTP ${retryRes.status}`);
                    }
                } else if (saveRes.status === 422) {
                    // Story 17.10 AC1/AC2: Handle Pydantic validation errors
                    const data = await saveRes.json().catch(() => ({}));
                    this.parseValidationErrors(data);
                    // Show toast with error count
                    const errorCount = Object.keys(this.validationErrors).length;
                    const errorWord = errorCount === 1 ? 'error' : 'errors';
                    this.showToast(`Validation failed: ${errorCount} field ${errorWord}`);
                    this.settingsView.applying = false;
                    return;
                } else if (!saveRes.ok) {
                    const errData = await saveRes.json().catch(() => ({}));
                    throw new Error(errData.message || errData.error || `Save failed: HTTP ${saveRes.status}`);
                }

                // Step 2: Reload config singleton
                // Story 17.9 AC3: Set timestamp immediately before reload to minimize race window
                this._selfReloadTimestamp = Date.now();
                const reloadRes = await fetch('/api/config/reload', {
                    method: 'POST'
                });

                if (!reloadRes.ok) {
                    // Config saved but reload failed - still show success but warn
                    this.showToast('Configuration saved but reload failed. Restart may be required.');
                } else {
                    this.showToast('Config reloaded.');
                }

                // Clear pending changes and validation errors
                this.pendingUpdates = [];
                this.validationErrors = {};
                this.settingsView.hasChanges = false;
                this.settingsView.staleData = false;

                // Refresh config data
                await this.fetchConfig();

            } catch (err) {
                console.error('Failed to apply config:', err);
                // Story 17.10 AC3: Differentiate error types for better user feedback
                let errorMessage;
                if (err.name === 'TypeError' && err.message.includes('fetch')) {
                    // Network error (no connectivity, DNS failure, etc.)
                    errorMessage = 'Network error. Check your connection and try again.';
                } else if (err.name === 'AbortError') {
                    // Request was aborted (timeout)
                    errorMessage = 'Request timed out. Server may be busy.';
                } else if (err.message.includes('500')) {
                    // Server error
                    errorMessage = 'Server error. Please try again later.';
                } else {
                    // Other errors (validation, config, etc.)
                    errorMessage = err.message || 'Failed to save configuration';
                }
                this.showToast(errorMessage);
            } finally {
                this.settingsView.applying = false;
            }
        },

        /**
         * Handle Escape key to close settings
         */
        handleSettingsEscape(event) {
            if (this.settingsView.open && event.key === 'Escape') {
                // Don't close if a modal is open
                if (this.contentModal.show || this.reportModal.show) {
                    return;
                }
                event.preventDefault();
                this.closeSettings();
            }
        },

        // ==========================================
        // Experiments View Methods (Story 19.1)
        // ==========================================

        /**
         * Open experiments panel and fetch runs
         */
        openExperiments() {
            // Close settings if open
            if (this.settingsView.open) {
                this.closeSettings();
            }
            this.experimentsView.open = true;
            this.experimentsView.activeTab = 'runs';
            this.fetchExperimentRuns();
        },

        /**
         * Close experiments panel
         */
        closeExperiments() {
            this.experimentsView.open = false;
            this.experimentsView.selected = [];
            this.fixturesView.selectedFixture = null;
        },

        /**
         * Switch experiments panel tab (Story 19.3)
         * @param {string} tab - Tab to switch to: 'runs' or 'fixtures'
         */
        switchExperimentsTab(tab) {
            this.experimentsView.activeTab = tab;
            if (tab === 'fixtures') {
                this.fetchFixtures();
            } else if (tab === 'runs') {
                this.fetchExperimentRuns();
            } else if (tab === 'templates') {
                this.fetchTemplates();
            }
        },

        /**
         * Fetch experiment runs from API with current filters/sort/pagination
         */
        async fetchExperimentRuns() {
            this.experimentsView.loading = true;
            this.experimentsView.error = null;

            try {
                const params = new URLSearchParams();
                const filters = this.experimentsView.filters;
                const sort = this.experimentsView.sort;
                const pagination = this.experimentsView.pagination;

                // Add filters
                if (filters.status) params.append('status', filters.status);
                if (filters.fixture) params.append('fixture', filters.fixture);
                if (filters.config) params.append('config', filters.config);
                if (filters.patch_set) params.append('patch_set', filters.patch_set);
                if (filters.loop) params.append('loop', filters.loop);
                if (filters.start_date) params.append('start_date', filters.start_date);
                if (filters.end_date) params.append('end_date', filters.end_date);

                // Add sorting
                params.append('sort_by', sort.by);
                params.append('sort_order', sort.order);

                // Add pagination
                params.append('offset', pagination.offset.toString());
                params.append('limit', pagination.limit.toString());

                const response = await fetch(`/api/experiments/runs?${params.toString()}`);
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.message || error.error || 'Failed to fetch experiments');
                }

                const data = await response.json();
                this.experimentsView.runs = data.runs;
                this.experimentsView.pagination = data.pagination;
            } catch (err) {
                console.error('Failed to fetch experiment runs:', err);
                this.experimentsView.error = err.message || 'Failed to fetch experiments';
            } finally {
                this.experimentsView.loading = false;
                this.$nextTick(() => this.refreshIcons());
            }
        },

        /**
         * Apply filters and refresh runs
         */
        applyExperimentFilters() {
            this.experimentsView.pagination.offset = 0;  // Reset to first page
            this.fetchExperimentRuns();
        },

        /**
         * Clear all filters
         */
        clearExperimentFilters() {
            this.experimentsView.filters = {
                status: '',
                fixture: '',
                config: '',
                patch_set: '',
                loop: '',
                start_date: '',
                end_date: ''
            };
            this.applyExperimentFilters();
        },

        /**
         * Sort by field
         * @param {string} field - Sort field name
         */
        sortExperimentsBy(field) {
            if (this.experimentsView.sort.by === field) {
                // Toggle order
                this.experimentsView.sort.order = this.experimentsView.sort.order === 'desc' ? 'asc' : 'desc';
            } else {
                this.experimentsView.sort.by = field;
                this.experimentsView.sort.order = 'desc';  // Default to desc for new sort
            }
            this.fetchExperimentRuns();
        },

        /**
         * Navigate to page
         * @param {number} offset - Page offset
         */
        goToExperimentPage(offset) {
            this.experimentsView.pagination.offset = offset;
            this.fetchExperimentRuns();
        },

        /**
         * Toggle run selection for comparison
         * @param {string} runId - Run ID to toggle
         */
        toggleRunSelection(runId) {
            const idx = this.experimentsView.selected.indexOf(runId);
            if (idx > -1) {
                this.experimentsView.selected.splice(idx, 1);
            } else {
                this.experimentsView.selected.push(runId);
            }
        },

        /**
         * Check if run is selected
         * @param {string} runId - Run ID to check
         * @returns {boolean}
         */
        isRunSelected(runId) {
            return this.experimentsView.selected.includes(runId);
        },

        // --- Experiment Details (Story 19.2) ---

        /**
         * Open experiment details panel for a specific run
         * @param {string} runId - Run ID to view
         */
        openExperimentDetails(runId) {
            this.experimentDetails.open = true;
            this.experimentDetails.runId = runId;
            this.experimentDetails.data = null;
            this.experimentDetails.error = null;
            this.fetchExperimentDetails(runId);
        },

        /**
         * Close experiment details panel
         */
        closeExperimentDetails() {
            this.experimentDetails.open = false;
            this.experimentDetails.runId = null;
            this.experimentDetails.data = null;
            this.experimentDetails.error = null;
        },

        /**
         * Fetch experiment details from API
         * @param {string} runId - Run ID to fetch
         */
        async fetchExperimentDetails(runId) {
            this.experimentDetails.loading = true;
            this.experimentDetails.error = null;

            try {
                const response = await fetch(`/api/experiments/runs/${encodeURIComponent(runId)}`);
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.message || error.error || 'Failed to fetch run details');
                }

                const data = await response.json();
                this.experimentDetails.data = data;
            } catch (err) {
                console.error('Failed to fetch experiment details:', err);
                this.experimentDetails.error = err.message || 'Failed to fetch run details';
            } finally {
                this.experimentDetails.loading = false;
                this.$nextTick(() => this.refreshIcons());
            }
        },

        /**
         * Refresh experiment details
         */
        refreshExperimentDetails() {
            if (this.experimentDetails.runId) {
                this.fetchExperimentDetails(this.experimentDetails.runId);
            }
        },

        /**
         * Get phase status badge class
         * @param {string} status - Phase status
         * @returns {string}
         */
        getPhaseStatusClass(status) {
            switch (status) {
                case 'completed': return 'badge-success';
                case 'failed': return 'badge-destructive';
                case 'skipped': return 'badge-secondary';
                default: return 'badge-outline';
            }
        },

        /**
         * Format duration for display

         * @param {number|null} seconds - Duration in seconds
         * @returns {string}
         */
        formatDuration(seconds) {
            if (seconds === null || seconds === undefined) return '-';
            const totalSecs = Math.floor(seconds);
            const hours = Math.floor(totalSecs / 3600);
            const minutes = Math.floor((totalSecs % 3600) / 60);
            const secs = totalSecs % 60;

            if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
            if (minutes > 0) return `${minutes}m ${secs}s`;
            return `${secs}s`;
        },

        /**
         * Format datetime for display
         * @param {string} isoDate - ISO date string
         * @returns {string}
         */
        formatDateTime(isoDate) {
            if (!isoDate) return '-';
            const date = new Date(isoDate);
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        },

        /**
         * Get status badge class
         * @param {string} status - Experiment status
         * @returns {string}
         */
        getExperimentStatusClass(status) {
            switch (status) {
                case 'completed': return 'badge-success';
                case 'running': return 'badge-warning';
                case 'failed': return 'badge-destructive';
                case 'cancelled': return 'badge-secondary';
                default: return 'badge-secondary';
            }
        },

        /**
         * Get sort indicator icon
         * @param {string} field - Field to check
         * @returns {string}
         */
        getSortIcon(field) {
            if (this.experimentsView.sort.by !== field) return 'chevrons-up-down';
            return this.experimentsView.sort.order === 'asc' ? 'chevron-up' : 'chevron-down';
        },

        // ==========================================
        // Fixtures Methods (Story 19.3)
        // ==========================================

        /**
         * Fetch fixtures list from API
         */
        async fetchFixtures() {
            this.fixturesView.loading = true;
            this.fixturesView.error = null;

            try {
                const filters = this.fixturesView.filters;
                const sort = this.fixturesView.sort;

                const params = new URLSearchParams();
                if (filters.difficulty) params.set('difficulty', filters.difficulty);
                if (filters.tags) params.set('tags', filters.tags);
                params.set('sort_by', sort.by);
                params.set('sort_order', sort.order);

                const response = await fetch(`/api/experiments/fixtures?${params.toString()}`);
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to fetch fixtures');
                }

                this.fixturesView.fixtures = data.fixtures;
                this.fixturesView.total = data.total;
            } catch (err) {
                this.fixturesView.error = err.message || 'Failed to fetch fixtures';
            } finally {
                this.fixturesView.loading = false;
            }
        },

        /**
         * Apply fixture filters
         */
        applyFixtureFilters() {
            this.fetchFixtures();
        },

        /**
         * Clear fixture filters
         */
        clearFixtureFilters() {
            this.fixturesView.filters = {
                difficulty: '',
                tags: ''
            };
            this.fetchFixtures();
        },

        /**
         * Sort fixtures by field
         * @param {string} field - Field to sort by
         */
        sortFixturesBy(field) {
            if (this.fixturesView.sort.by === field) {
                this.fixturesView.sort.order = this.fixturesView.sort.order === 'desc' ? 'asc' : 'desc';
            } else {
                this.fixturesView.sort.by = field;
                this.fixturesView.sort.order = 'asc';  // Default to asc for new sort
            }
            this.fetchFixtures();
        },

        /**
         * Get fixture sort indicator icon
         * @param {string} field - Field to check
         * @returns {string}
         */
        getFixtureSortIcon(field) {
            if (this.fixturesView.sort.by !== field) return 'chevrons-up-down';
            return this.fixturesView.sort.order === 'asc' ? 'chevron-up' : 'chevron-down';
        },

        /**
         * Open fixture details modal
         * @param {string} fixtureId - Fixture ID to view
         */
        async openFixtureDetails(fixtureId) {
            try {
                const response = await fetch(`/api/experiments/fixtures/${encodeURIComponent(fixtureId)}`);
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to fetch fixture details');
                }
                this.fixturesView.selectedFixture = data;
            } catch (err) {
                console.error('Failed to fetch fixture details:', err);
                // Still show what we have from the list
                const fixture = this.fixturesView.fixtures.find(f => f.id === fixtureId);
                if (fixture) {
                    this.fixturesView.selectedFixture = fixture;
                }
            }
        },

        /**
         * Close fixture details modal
         */
        closeFixtureDetails() {
            this.fixturesView.selectedFixture = null;
        },

        /**
         * Get difficulty badge class
         * @param {string} difficulty - Difficulty level
         * @returns {string}
         */
        getDifficultyClass(difficulty) {
            switch (difficulty) {
                case 'trivial': return 'badge-success';
                case 'simple': return 'badge-success';
                case 'medium': return 'badge-warning';
                case 'complex': return 'badge-destructive';
                case 'expert': return 'badge-destructive';
                default: return 'badge-secondary';
            }
        },

        /**
         * Format date for display
         * @param {string} dateStr - ISO date string
         * @returns {string}
         */
        formatFixtureDate(dateStr) {
            if (!dateStr) return 'Never';
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        },

        // ==========================================
        // Templates Methods (Story 19.5)
        // ==========================================

        /**
         * Fetch configs list from API
         */
        async fetchConfigs() {
            this.templatesView.loading = true;
            this.templatesView.error = null;

            try {
                const sort = this.templatesView.sort;
                const params = new URLSearchParams();
                params.set('sort_by', sort.by);
                params.set('sort_order', sort.order);

                const response = await fetch(`/api/experiments/configs?${params.toString()}`);
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to fetch configs');
                }

                this.templatesView.configs = data.configs;
                this.templatesView.configsTotal = data.total;
            } catch (err) {
                this.templatesView.error = err.message || 'Failed to fetch configs';
            } finally {
                this.templatesView.loading = false;
            }
        },

        /**
         * Fetch loops list from API
         */
        async fetchLoops() {
            this.templatesView.loading = true;
            this.templatesView.error = null;

            try {
                const sort = this.templatesView.sort;
                const params = new URLSearchParams();
                params.set('sort_by', sort.by);
                params.set('sort_order', sort.order);

                const response = await fetch(`/api/experiments/loops?${params.toString()}`);
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to fetch loops');
                }

                this.templatesView.loops = data.loops;
                this.templatesView.loopsTotal = data.total;
            } catch (err) {
                this.templatesView.error = err.message || 'Failed to fetch loops';
            } finally {
                this.templatesView.loading = false;
            }
        },

        /**
         * Fetch patch-sets list from API
         */
        async fetchPatchSets() {
            this.templatesView.loading = true;
            this.templatesView.error = null;

            try {
                const sort = this.templatesView.sort;
                const params = new URLSearchParams();
                params.set('sort_by', sort.by);
                params.set('sort_order', sort.order);

                const response = await fetch(`/api/experiments/patch-sets?${params.toString()}`);
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to fetch patch-sets');
                }

                this.templatesView.patchSets = data.patch_sets;
                this.templatesView.patchSetsTotal = data.total;
            } catch (err) {
                this.templatesView.error = err.message || 'Failed to fetch patch-sets';
            } finally {
                this.templatesView.loading = false;
            }
        },

        /**
         * Fetch templates based on active sub-tab
         */
        fetchTemplates() {
            switch (this.templatesView.activeSubTab) {
                case 'configs':
                    this.fetchConfigs();
                    break;
                case 'loops':
                    this.fetchLoops();
                    break;
                case 'patch-sets':
                    this.fetchPatchSets();
                    break;
            }
        },

        /**
         * Switch templates sub-tab
         * @param {string} tab - Sub-tab name
         */
        switchTemplatesSubTab(tab) {
            this.templatesView.activeSubTab = tab;
            this.fetchTemplates();
        },

        /**
         * Sort templates by field
         * @param {string} field - Field to sort by
         */
        sortTemplatesBy(field) {
            if (this.templatesView.sort.by === field) {
                this.templatesView.sort.order = this.templatesView.sort.order === 'desc' ? 'asc' : 'desc';
            } else {
                this.templatesView.sort.by = field;
                this.templatesView.sort.order = 'asc';
            }
            this.fetchTemplates();
        },

        /**
         * Get template sort indicator icon
         * @param {string} field - Field to check
         * @returns {string}
         */
        getTemplateSortIcon(field) {
            if (this.templatesView.sort.by !== field) return 'chevrons-up-down';
            return this.templatesView.sort.order === 'asc' ? 'chevron-up' : 'chevron-down';
        },

        /**
         * Open config details modal
         * @param {string} configName - Config name to view
         */
        async openConfigDetails(configName) {
            try {
                const response = await fetch(`/api/experiments/configs/${encodeURIComponent(configName)}`);
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to fetch config details');
                }
                this.templatesView.selectedTemplate = { type: 'config', ...data };
            } catch (err) {
                console.error('Failed to fetch config details:', err);
            }
        },

        /**
         * Open loop details modal
         * @param {string} loopName - Loop name to view
         */
        async openLoopDetails(loopName) {
            try {
                const response = await fetch(`/api/experiments/loops/${encodeURIComponent(loopName)}`);
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to fetch loop details');
                }
                this.templatesView.selectedTemplate = { type: 'loop', ...data };
            } catch (err) {
                console.error('Failed to fetch loop details:', err);
            }
        },

        /**
         * Open patch-set details modal
         * @param {string} patchSetName - Patch-set name to view
         */
        async openPatchSetDetails(patchSetName) {
            try {
                const response = await fetch(`/api/experiments/patch-sets/${encodeURIComponent(patchSetName)}`);
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to fetch patch-set details');
                }
                this.templatesView.selectedTemplate = { type: 'patch-set', ...data };
            } catch (err) {
                console.error('Failed to fetch patch-set details:', err);
            }
        },

        /**
         * Close template details modal
         */
        closeTemplateDetails() {
            this.templatesView.selectedTemplate = null;
        },

        /**
         * Format date for template display
         * @param {string} dateStr - ISO date string
         * @returns {string}
         */
        formatTemplateDate(dateStr) {
            if (!dateStr) return 'Never';
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        },

        /**
         * Get total count for current template type
         * @returns {number}
         */
        getTemplatesTotal() {
            switch (this.templatesView.activeSubTab) {
                case 'configs': return this.templatesView.configsTotal;
                case 'loops': return this.templatesView.loopsTotal;
                case 'patch-sets': return this.templatesView.patchSetsTotal;
                default: return 0;
            }
        },

        // ==========================================
        // Comparison Methods (Story 19.4)
        // ==========================================

        /**
         * Fetch comparison data for selected runs
         * @param {string[]} runIds - Array of run IDs to compare
         */
        async fetchComparison(runIds) {
            this.comparisonView.loading = true;
            this.comparisonView.error = null;
            this.comparisonView.runIds = runIds;
            this.comparisonView.report = null;

            try {
                const response = await fetch(`/api/experiments/compare?runs=${runIds.join(',')}`);
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.message || data.error || 'Failed to fetch comparison');
                }
                this.comparisonView.report = await response.json();
                this.comparisonView.open = true;
            } catch (err) {
                console.error('Failed to fetch comparison:', err);
                this.comparisonView.error = err.message || 'Failed to fetch comparison';
            } finally {
                this.comparisonView.loading = false;
                this.$nextTick(() => this.refreshIcons());
            }
        },

        /**
         * Close comparison view
         */
        closeComparison() {
            this.comparisonView.open = false;
            this.comparisonView.report = null;
            this.comparisonView.error = null;
            this.comparisonView.runIds = [];
        },

        /**
         * Export comparison as Markdown
         */
        async exportComparison() {
            const runIds = this.comparisonView.runIds;
            if (runIds.length < 2) return;

            this.comparisonView.exporting = true;

            try {
                const response = await fetch(`/api/experiments/compare/export?runs=${runIds.join(',')}`);
                if (!response.ok) {
                    const data = await response.json().catch(() => ({}));
                    throw new Error(data.message || data.error || 'Export failed');
                }

                // Trigger download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                // Get filename from Content-Disposition header or generate default
                const disposition = response.headers.get('Content-Disposition');
                if (disposition) {
                    const match = disposition.match(/filename="(.+)"/);
                    if (match) a.download = match[1];
                }
                if (!a.download) {
                    const date = new Date().toISOString().split('T')[0];
                    a.download = `comparison-${date}.md`;
                }
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                this.showToast('Comparison exported');
            } catch (err) {
                console.error('Export failed:', err);
                this.showToast(`Export failed: ${err.message}`);
            } finally {
                this.comparisonView.exporting = false;
            }
        },

        /**
         * Compare selected runs (triggered from experiments list)
         */
        compareSelectedRuns() {
            const selected = this.experimentsView.selected;
            if (selected.length < 2) {
                this.showToast('Select at least 2 runs to compare');
                return;
            }
            if (selected.length > 10) {
                this.showToast('Maximum 10 runs can be compared');
                return;
            }
            this.fetchComparison(selected);
        },

        /**
         * Get human-readable metric display name
         * @param {string} metricName - Internal metric name
         * @returns {string}
         */
        getMetricDisplayName(metricName) {
            const names = {
                total_cost: 'Total Cost',
                total_tokens: 'Total Tokens',
                total_duration_seconds: 'Duration',
                avg_tokens_per_phase: 'Avg Tokens/Phase',
                avg_cost_per_phase: 'Avg Cost/Phase',
                stories_completed: 'Stories Completed',
                stories_failed: 'Stories Failed',
                success_rate: 'Success Rate',
            };
            return names[metricName] || metricName;
        },

        /**
         * Format metric value based on type
         * @param {string} metricName - Metric name
         * @param {number|null} value - Value to format
         * @returns {string}
         */
        formatMetricValue(metricName, value) {
            if (value === null || value === undefined) return 'N/A';

            switch (metricName) {
                case 'total_cost':
                case 'avg_cost_per_phase':
                    return '$' + value.toFixed(2);
                case 'total_tokens':
                case 'avg_tokens_per_phase':
                    return value.toLocaleString();
                case 'total_duration_seconds': {
                    const totalSecs = Math.floor(value);
                    const hours = Math.floor(totalSecs / 3600);
                    const mins = Math.floor((totalSecs % 3600) / 60);
                    const secs = totalSecs % 60;
                    if (hours > 0) {
                        return `${hours}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
                    }
                    return `${mins}:${String(secs).padStart(2, '0')}`;
                }
                case 'success_rate':
                    return value.toFixed(1) + '%';
                case 'stories_completed':
                case 'stories_failed':
                    return String(Math.floor(value));
                default:
                    return String(value);
            }
        },

        /**
         * Format delta percentage
         * @param {number|null} delta - Delta value
         * @returns {string}
         */
        formatDelta(delta) {
            if (delta === null || delta === undefined) return 'N/A';
            const rounded = Math.round(delta * 10) / 10;
            if (rounded === 0) return '0.0%';
            const sign = rounded > 0 ? '+' : '';
            return sign + rounded.toFixed(1) + '%';
        },

        /**
         * Get CSS class for delta value (coloring)
         * @param {object} metric - Metric comparison object
         * @returns {string}
         */
        getDeltaClass(metric) {
            const runIds = this.comparisonView.report?.run_ids || [];
            if (runIds.length < 2) return 'text-muted-foreground';

            const delta = metric.deltas[runIds[1]];
            if (delta === null || delta === undefined || delta === 0) return 'text-muted-foreground';

            // For lower_is_better metrics, negative delta is good
            // For higher_is_better metrics, positive delta is good
            const isImprovement = metric.lower_is_better ? delta < 0 : delta > 0;
            return isImprovement ? 'text-green-600' : 'text-red-600';
        },

        /**
         * Get cost value for a run from metrics
         * @param {string} runId - Run ID
         * @returns {number|null}
         */
        getCostValue(runId) {
            const metric = this.comparisonView.report?.metrics?.find(m => m.metric_name === 'total_cost');
            return metric?.values[runId] ?? null;
        },

        /**
         * Get bar width percentage for cost visualization
         * @param {string} runId - Run ID
         * @returns {number}
         */
        getCostBarWidth(runId) {
            const metric = this.comparisonView.report?.metrics?.find(m => m.metric_name === 'total_cost');
            if (!metric) return 0;

            const values = Object.values(metric.values).filter(v => v !== null);
            if (values.length === 0) return 0;

            const maxValue = Math.max(...values);
            const value = metric.values[runId];
            if (value === null || maxValue === 0) return 0;

            // Apply minimum 5% width for visibility
            const rawWidth = (value / maxValue) * 100;
            return Math.max(rawWidth, 5);
        },

        /**
         * Format cost value for display
         * @param {number|null} value - Cost value
         * @returns {string}
         */
        formatCost(value) {
            if (value === null || value === undefined) return 'N/A';
            return '$' + value.toFixed(2);
        },

        /**
         * Check if all cost values are null or zero
         * @returns {boolean}
         */
        hasNoCostData() {
            const metric = this.comparisonView.report?.metrics?.find(m => m.metric_name === 'total_cost');
            if (!metric) return true;
            const values = Object.values(metric.values);
            return values.every(v => v === null || v === 0);
        },

        /**
         * Get axis display name
         * @param {string} axis - Axis name
         * @returns {string}
         */
        getAxisDisplayName(axis) {
            const names = {
                fixture: 'Fixture',
                config: 'Config',
                patch_set: 'Patch-Set',
                loop: 'Loop',
            };
            return names[axis] || axis;
        },

        // ==========================================
        // Run Trigger Methods (Story 19.6)
        // ==========================================

        /**
         * Open the run trigger modal and load available options
         */
        async openRunTriggerModal() {
            this.runTrigger.modalOpen = true;
            this.runTrigger.error = null;

            // Load options if not already loaded
            if (!this.runTrigger.optionsLoaded) {
                await this.loadRunTriggerOptions();
            }
        },

        /**
         * Close the run trigger modal
         */
        closeRunTriggerModal() {
            this.runTrigger.modalOpen = false;
            this.runTrigger.error = null;
        },

        /**
         * Load available fixtures, configs, loops, and patch-sets for the run trigger form
         */
        async loadRunTriggerOptions() {
            try {
                // Fetch all template types in parallel
                const [fixturesRes, configsRes, loopsRes, patchSetsRes] = await Promise.all([
                    fetch('/api/experiments/fixtures'),
                    fetch('/api/experiments/configs'),
                    fetch('/api/experiments/loops'),
                    fetch('/api/experiments/patch-sets'),
                ]);

                if (!fixturesRes.ok || !configsRes.ok || !loopsRes.ok || !patchSetsRes.ok) {
                    throw new Error('Failed to load template options');
                }

                const [fixtures, configs, loops, patchSets] = await Promise.all([
                    fixturesRes.json(),
                    configsRes.json(),
                    loopsRes.json(),
                    patchSetsRes.json(),
                ]);

                this.runTrigger.fixtures = fixtures.fixtures || [];
                this.runTrigger.configs = configs.configs || [];
                this.runTrigger.loops = loops.loops || [];
                this.runTrigger.patchSets = patchSets.patch_sets || [];
                this.runTrigger.optionsLoaded = true;

                // Set defaults if available
                if (this.runTrigger.fixtures.length > 0 && !this.runTrigger.fixture) {
                    this.runTrigger.fixture = this.runTrigger.fixtures[0].name;
                }
                if (this.runTrigger.configs.length > 0 && !this.runTrigger.config) {
                    this.runTrigger.config = this.runTrigger.configs[0].name;
                }
                if (this.runTrigger.loops.length > 0 && !this.runTrigger.loop) {
                    this.runTrigger.loop = this.runTrigger.loops[0].name;
                }
                if (this.runTrigger.patchSets.length > 0 && !this.runTrigger.patchSet) {
                    this.runTrigger.patchSet = this.runTrigger.patchSets[0].name;
                }
            } catch (err) {
                console.error('Failed to load run trigger options:', err);
                this.runTrigger.error = err.message || 'Failed to load options';
            }
        },

        /**
         * Submit the run trigger form to start a new experiment
         */
        async submitRunTrigger() {
            // Validate form
            if (!this.runTrigger.fixture || !this.runTrigger.config ||
                !this.runTrigger.loop || !this.runTrigger.patchSet) {
                this.runTrigger.error = 'All fields are required';
                return;
            }

            this.runTrigger.loading = true;
            this.runTrigger.error = null;

            try {
                const response = await fetch('/api/experiments/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        fixture: this.runTrigger.fixture,
                        config: this.runTrigger.config,
                        patch_set: this.runTrigger.patchSet,
                        loop: this.runTrigger.loop,
                    }),
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to start experiment');
                }

                // Success - close modal and start tracking progress
                this.closeRunTriggerModal();
                this.showToast(`Experiment ${data.run_id} started`);

                // Set up active experiment tracking
                this.activeExperiment.runId = data.run_id;
                this.activeExperiment.status = data.status;
                this.activeExperiment.percent = 0;
                this.activeExperiment.storiesCompleted = 0;
                this.activeExperiment.storiesTotal = 0;

                // Connect to SSE for progress updates
                this.connectExperimentSSE(data.run_id);

            } catch (err) {
                console.error('Failed to start experiment:', err);
                this.runTrigger.error = err.message || 'Failed to start experiment';
            } finally {
                this.runTrigger.loading = false;
            }
        },

        /**
         * Connect to SSE endpoint for experiment progress updates
         * @param {string} runId - Run ID to track
         */
        connectExperimentSSE(runId) {
            // Close existing connection if any
            if (this.activeExperiment.eventSource) {
                this.activeExperiment.eventSource.close();
            }

            const eventSource = new EventSource(`/api/experiments/run/${runId}/status`);

            eventSource.addEventListener('experiment_status', (event) => {
                const data = JSON.parse(event.data);
                if (data.run_id === this.activeExperiment.runId) {
                    this.activeExperiment.status = data.status;
                    this.activeExperiment.phase = data.phase;
                    this.activeExperiment.story = data.story;
                    this.activeExperiment.position = data.position;

                    // Check if terminal status
                    if (['completed', 'failed', 'cancelled'].includes(data.status)) {
                        this.disconnectExperimentSSE();
                        // Refresh experiment runs list if panel is open
                        if (this.experimentsView.open && this.experimentsView.activeTab === 'runs') {
                            this.fetchExperimentRuns();
                        }
                    }
                }
            });

            eventSource.addEventListener('experiment_progress', (event) => {
                const data = JSON.parse(event.data);
                if (data.run_id === this.activeExperiment.runId) {
                    this.activeExperiment.percent = data.percent;
                    this.activeExperiment.storiesCompleted = data.stories_completed;
                    this.activeExperiment.storiesTotal = data.stories_total;
                }
            });

            eventSource.onerror = () => {
                console.error('Experiment SSE connection error');
                // Don't clear state immediately - wait for reconnect or terminal status
            };

            this.activeExperiment.eventSource = eventSource;
        },

        /**
         * Disconnect from experiment SSE and clear active state
         */
        disconnectExperimentSSE() {
            if (this.activeExperiment.eventSource) {
                this.activeExperiment.eventSource.close();
                this.activeExperiment.eventSource = null;
            }
        },

        /**
         * Cancel the currently running experiment
         */
        async cancelExperiment() {
            const runId = this.activeExperiment.runId;
            if (!runId) return;

            try {
                const response = await fetch(`/api/experiments/run/${runId}/cancel`, {
                    method: 'POST',
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.message || data.error || 'Failed to cancel experiment');
                }

                this.showToast(`Experiment ${runId} cancelled`);
                this.activeExperiment.status = 'cancelled';
                this.disconnectExperimentSSE();

            } catch (err) {
                console.error('Failed to cancel experiment:', err);
                this.showToast('Failed to cancel experiment');
            }
        },

        /**
         * Clear active experiment tracking (dismiss progress UI)
         */
        clearActiveExperiment() {
            this.disconnectExperimentSSE();
            this.activeExperiment.runId = null;
            this.activeExperiment.status = null;
            this.activeExperiment.phase = null;
            this.activeExperiment.story = null;
            this.activeExperiment.position = null;
            this.activeExperiment.percent = 0;
            this.activeExperiment.storiesCompleted = 0;
            this.activeExperiment.storiesTotal = 0;
        },

        /**
         * Check if there's an active experiment that's still running
         * @returns {boolean}
         */
        hasActiveExperiment() {
            return this.activeExperiment.runId !== null &&
                   !['completed', 'failed', 'cancelled'].includes(this.activeExperiment.status);
        },

        /**
         * Get status badge class for active experiment
         * @returns {string}
         */
        getExperimentStatusClass() {
            switch (this.activeExperiment.status) {
                case 'queued':
                    return 'badge-secondary';
                case 'running':
                    return 'badge-primary';
                case 'completed':
                    return 'badge-success';
                case 'failed':
                    return 'badge-destructive';
                case 'cancelled':
                    return 'badge-secondary';
                default:
                    return 'badge-secondary';
            }
        },

        // ==========================================
        // Settings Helper Methods (Story 17.5)
        // ==========================================

        /**
         * Safe nested property access for config data
         * @param {object} obj - Object to access
         * @param {string} path - Dot-separated path (e.g., 'testarch.playwright.browsers')
         * @returns {any} Value at path or undefined
         */
        getNestedValue(obj, path) {
            return path.split('.').reduce((o, k) => o?.[k], obj);
        },

        /**
         * Get field value (pending or from config)
         * @param {string} path - Config path (e.g., 'testarch.playwright.browsers')
         * @returns {any} Pending value if exists, otherwise config value
         */
        getFieldValue(path) {
            const pending = this.pendingUpdates.find(u => u.path === path);
            if (pending !== undefined) return pending.value;
            return this.getNestedValue(this.configData, path + '.value');
        },

        /**
         * Get field provenance source
         * @param {string} path - Config path
         * @returns {string} Source: 'default', 'global', or 'project'
         */
        getFieldSource(path) {
            return this.getNestedValue(this.configData, path + '.source') || 'default';
        },

        /**
         * Array equality helper for browser selection comparison
         * @param {array} a - First array
         * @param {array} b - Second array
         * @returns {boolean} True if arrays contain same elements (order-independent)
         */
        arraysEqual(a, b) {
            if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false;
            const sortedA = [...a].sort();
            const sortedB = [...b].sort();
            return sortedA.every((val, i) => val === sortedB[i]);
        },

        /**
         * Add or update pending change with reversion detection
         * @param {string} path - Config path
         * @param {any} value - New value
         */
        addPendingUpdate(path, value) {
            const originalValue = this.getNestedValue(this.configData, path + '.value');
            const isEqual = Array.isArray(value)
                ? this.arraysEqual(value, originalValue)
                : value === originalValue;

            const idx = this.pendingUpdates.findIndex(u => u.path === path);

            if (isEqual) {
                // Value reverted to original - remove from pending
                if (idx >= 0) this.pendingUpdates.splice(idx, 1);
            } else {
                // Value changed - add/update pending
                if (idx >= 0) {
                    this.pendingUpdates[idx].value = value;
                } else {
                    this.pendingUpdates.push({ path, value });
                }
            }
            this.settingsView.hasChanges = this.pendingUpdates.length > 0;
        },

        /**
         * Check if Apply should be disabled due to validation errors
         * @returns {boolean} True if any validation errors exist
         */
        hasValidationErrors() {
            return Object.keys(this.validationErrors).length > 0;
        },

        /**
         * Validate and update a numeric field
         * @param {string} path - Config path
         * @param {string|number} value - Input value
         * @param {number} min - Minimum allowed value
         * @param {number} max - Maximum allowed value
         */
        validateAndUpdateNumber(path, value, min, max) {
            // Handle empty input - clear error and don't add to pending
            if (value === '' || value === null || value === undefined) {
                delete this.validationErrors[path];
                return;
            }

            const num = parseInt(value, 10);

            // Handle non-numeric input
            if (isNaN(num)) {
                this.validationErrors[path] = 'Must be a valid number';
                return;
            }

            // Store validation error in validationErrors object
            if (num < min || num > max) {
                this.validationErrors[path] = `Must be between ${min.toLocaleString()} and ${max.toLocaleString()}`;
            } else {
                delete this.validationErrors[path];
                this.addPendingUpdate(path, num);
            }
        },

        /**
         * Toggle a browser in the browsers array
         * @param {string} browser - Browser name ('chromium', 'firefox', 'webkit')
         */
        toggleBrowser(browser) {
            const path = 'testarch.playwright.browsers';
            const current = this.getFieldValue(path) || [];
            const browsers = Array.isArray(current) ? [...current] : [];
            const idx = browsers.indexOf(browser);
            if (idx >= 0) {
                browsers.splice(idx, 1);
            } else {
                browsers.push(browser);
            }
            this.addPendingUpdate(path, browsers);
        },

        /**
         * Check if a browser is selected
         * @param {string} browser - Browser name
         * @returns {boolean} True if browser is in the browsers array
         */
        isBrowserSelected(browser) {
            const browsers = this.getFieldValue('testarch.playwright.browsers') || ['chromium'];
            return Array.isArray(browsers) && browsers.includes(browser);
        },

        /**
         * Check if playwright config exists in configData
         * @returns {boolean} True if testarch.playwright exists
         */
        hasPlaywrightConfig() {
            return this.getNestedValue(this.configData, 'testarch.playwright') != null;
        },

        /**
         * Check if benchmarking config exists in configData
         * @returns {boolean} True if benchmarking exists
         */
        hasBenchmarkingConfig() {
            return this.getNestedValue(this.configData, 'benchmarking') != null;
        },

        // ==========================================
        // Providers Settings Helper Methods (Story 17.7)
        // ==========================================

        /**
         * Check if providers config exists in configData
         * @returns {boolean} True if providers.master exists
         */
        hasProvidersConfig() {
            return this.getNestedValue(this.configData, 'providers.master') != null;
        },

        /**
         * Get master provider field value using established getFieldValue() helper
         * @param {string} field - Field name (e.g., 'provider', 'model', 'model_name')
         * @returns {any} Pending value if exists, otherwise config value
         */
        getMasterField(field) {
            return this.getFieldValue(`providers.master.${field}`);
        },

        /**
         * Get master provider field source using established getFieldSource() helper
         * @param {string} field - Field name
         * @returns {string} Source: 'default', 'global', or 'project'
         */
        getMasterFieldSource(field) {
            return this.getFieldSource(`providers.master.${field}`);
        },

        /**
         * Get multi validators array (handles null/undefined/empty gracefully)
         * The API returns multi as {"value": [...], "source": "..."} so we access .value
         * @returns {Array} Array of raw multi validator objects (no provenance wrapper per field)
         */
        getMultiValidators() {
            const multiWrapper = this.getNestedValue(this.configData, 'providers.multi');
            // Multi is wrapped: {"value": [...], "source": "..."}
            const items = multiWrapper?.value;
            return Array.isArray(items) ? items : [];
        },

        /**
         * Get provenance source for the entire multi validators array
         * @returns {string} Source: 'default', 'global', or 'project'
         */
        getMultiValidatorsSource() {
            const multiWrapper = this.getNestedValue(this.configData, 'providers.multi');
            return multiWrapper?.source || 'default';
        },

        /**
         * Get multi validator display name: model_name if set, else model, else 'Unknown'
         * Note: Multi validators are raw objects (not wrapped in provenance per field)
         * @param {object} validator - Validator object (raw, e.g., {provider: "claude", model: "sonnet", ...})
         * @returns {string} Display name for the validator
         */
        getMultiDisplayName(validator) {
            // Raw validator objects, not wrapped in provenance per field
            // Use explicit null/undefined/empty-string check to distinguish unset from cleared
            const modelName = validator?.model_name;
            if (modelName !== null && modelName !== undefined && modelName !== '') {
                return modelName;
            }
            return validator?.model || 'Unknown';
        },

        /**
         * Validate dropdown/text field (required non-empty)
         * Consolidated method for both benchmarking and provider fields
         * @param {string} path - Config path
         * @param {string} value - Input value
         */
        validateDropdownField(path, value) {
            const trimmed = value?.trim() || '';
            if (!trimmed) {
                // Map paths to exact AC-required labels
                const labelMap = {
                    'benchmarking.extraction_provider': 'Provider',
                    'benchmarking.extraction_model': 'Model',
                    'providers.master.provider': 'Provider',
                    'providers.master.model': 'Model'
                };
                const fieldName = labelMap[path] || path.split('.').pop().replace(/_/g, ' ');
                const label = fieldName.charAt(0).toUpperCase() + fieldName.slice(1);
                this.validationErrors[path] = `${label} is required`;
            } else {
                delete this.validationErrors[path];
            }
        },

        // ==========================================
        // Inheritance Indicator Methods (Story 17.8)
        // ==========================================

        /**
         * Hardcoded default values for config fields (fallback when schema doesn't include defaults)
         * Story 17.8 AC6: Complete list of all config paths with reset buttons
         */
        CONFIG_DEFAULTS: {
            // Testing tab (4 fields)
            'testarch.playwright.browsers': ['chromium'],
            'testarch.playwright.headless': true,
            'testarch.playwright.timeout': 30000,
            'testarch.playwright.workers': 1,
            // Benchmarking tab (3 fields)
            'benchmarking.enabled': true,
            'benchmarking.extraction_provider': 'claude',
            'benchmarking.extraction_model': 'haiku',
            // Providers tab - Master (3 fields)
            'providers.master.provider': 'claude',
            'providers.master.model': 'opus',
            'providers.master.model_name': null  // null is valid default (optional field)
        },

        /**
         * Get default value for a config path from schema or hardcoded fallback
         * Story 17.8 AC6
         * @param {string} path - Config path (e.g., 'testarch.playwright.timeout')
         * @returns {any} Default value or undefined if not found
         */
        getDefaultValue(path) {
            // Try schema first
            if (this.configSchema) {
                const parts = path.split('.');
                let schema = this.configSchema;
                for (const part of parts) {
                    schema = schema?.properties?.[part];
                    if (!schema) break;
                }
                if (schema?.default !== undefined) {
                    return schema.default;
                }
            }
            // Fallback to hardcoded defaults
            if (this.CONFIG_DEFAULTS[path] !== undefined) {
                return this.CONFIG_DEFAULTS[path];
            }
            // No default available - log warning
            console.warn('No default value found for:', path);
            return undefined;
        },

        /**
         * Get global value for a config path (for "Reset to global" in project scope)
         * Story 17.8 AC7
         * @param {string} path - Config path
         * @returns {any} Global config value or undefined
         */
        getGlobalValue(path) {
            return this.getNestedValue(this.globalConfigData, path + '.value');
        },

        /**
         * Check if field can be reset to default (has non-default value AND default is known)
         * Story 17.8 AC2
         * @param {string} path - Config path
         * @returns {boolean} True if reset to default is available
         */
        canResetToDefault(path) {
            const source = this.getFieldSource(path);
            const defaultVal = this.getDefaultValue(path);
            // Can reset if source is not 'default' and we know what the default is
            return source !== 'default' && defaultVal !== undefined;
        },

        /**
         * Check if field can be reset to global (project scope with project override)
         * Story 17.8 AC3
         * @param {string} path - Config path
         * @returns {boolean} True if reset to global is available
         */
        canResetToGlobal(path) {
            // Only available in project scope when the field has a project-level override
            return this.settingsView.scope === 'project' &&
                   this.getFieldSource(path) === 'project';
        },

        /**
         * Check if field has a project-level override (for visual indicator)
         * Story 17.8 AC1
         * @param {string} path - Config path
         * @returns {boolean} True if field has project override in project scope
         */
        hasProjectOverride(path) {
            return this.settingsView.scope === 'project' &&
                   this.getFieldSource(path) === 'project';
        },

        /**
         * Format a value for display in confirmation dialogs
         * @param {any} val - Value to format
         * @returns {string} Formatted display string
         */
        formatValueForDisplay(val) {
            if (val === null || val === undefined) {
                return 'none';
            }
            if (Array.isArray(val)) {
                return val.length > 0 ? val.join(', ') : 'empty';
            }
            if (typeof val === 'boolean') {
                return val ? 'enabled' : 'disabled';
            }
            return String(val);
        },

        /**
         * Reset field to default value
         * Story 17.8 AC2
         * @param {string} path - Config path
         * @param {string} fieldName - Human-readable field name for confirmation dialog
         */
        resetToDefault(path, fieldName) {
            const defaultVal = this.getDefaultValue(path);
            if (defaultVal === undefined) {
                console.error('Cannot reset - no default value for:', path);
                return;
            }

            const displayVal = this.formatValueForDisplay(defaultVal);
            if (!confirm(`Reset ${fieldName} to default value (${displayVal})?`)) {
                return;
            }

            // null signals "delete this field from config" to backend
            // This causes the field to inherit from the next level (global or Pydantic default)
            this.addPendingUpdate(path, null);
        },

        /**
         * Reset field to global value (removes project override)
         * Story 17.8 AC3
         * @param {string} path - Config path
         * @param {string} fieldName - Human-readable field name for confirmation dialog
         */
        resetToGlobal(path, fieldName) {
            const globalVal = this.getGlobalValue(path);
            const defaultVal = this.getDefaultValue(path);
            const targetVal = globalVal !== undefined ? globalVal : defaultVal;
            const displayVal = this.formatValueForDisplay(targetVal);

            const targetSource = globalVal !== undefined ? 'global' : 'default';
            if (!confirm(`Reset ${fieldName} to ${targetSource} value (${displayVal})?`)) {
                return;
            }

            // null signals "delete this field from project config"
            // Field will then inherit from global (or default if no global)
            this.addPendingUpdate(path, null);
        },

        // ==========================================
        // Validation Error Handling Methods (Story 17.10)
        // ==========================================

        /**
         * Parse validation errors from 422 response into field-level errors
         * Story 17.10 AC1/AC2: Converts backend validation error format to per-field display format
         *
         * Backend format:
         * {
         *   "error": "validation_failed",
         *   "details": [
         *     {"loc": ["testarch", "playwright", "timeout"], "msg": "Input should be...", "type": "..."}
         *   ]
         * }
         *
         * Output format (stored in this.validationErrors):
         * {
         *   "testarch.playwright.timeout": "Input should be..."
         * }
         *
         * @param {object} responseData - Parsed JSON from 422 response
         */
        parseValidationErrors(responseData) {
            // Clear any existing validation errors
            this.validationErrors = {};

            const details = responseData?.details;
            if (!Array.isArray(details) || details.length === 0) {
                return;
            }

            for (const err of details) {
                // Convert loc array to dot-notation path
                // e.g., ["testarch", "playwright", "timeout"] -> "testarch.playwright.timeout"
                const loc = err.loc;
                if (!Array.isArray(loc) || loc.length === 0) {
                    continue;
                }
                const path = loc.map(String).join('.');
                const msg = err.msg || 'Validation error';

                // Store in validationErrors keyed by path
                this.validationErrors[path] = msg;
            }
        },

        /**
         * Clear all validation errors (used when successfully saving or resetting form)
         * Story 17.10 AC2
         */
        clearValidationErrors() {
            this.validationErrors = {};
        },

        /**
         * Get validation error message for a specific field path
         * Story 17.10 AC2: Returns error message if field has validation error
         * @param {string} path - Config path (e.g., 'testarch.playwright.timeout')
         * @returns {string|null} Error message or null if no error
         */
        getValidationError(path) {
            return this.validationErrors[path] || null;
        },

        /**
         * Check if a specific field has a validation error
         * Story 17.10 AC2: For conditional styling of input fields
         * @param {string} path - Config path
         * @returns {boolean} True if field has validation error
         */
        hasFieldError(path) {
            return !!this.validationErrors[path];
        },

        // ==========================================
        // Backup Management Methods (Story 17.10)
        // ==========================================

        /**
         * Toggle backups section expansion
         * Story 17.10 AC4/AC7: Collapsible section for backups
         */
        toggleBackupsSection() {
            this.backupsView.expanded = !this.backupsView.expanded;
            if (this.backupsView.expanded) {
                // Fetch backups when expanding
                this.fetchBackups();
            }
        },

        /**
         * Fetch backups for both global and project scopes
         * Story 17.10 AC4: Loads backup list from API
         */
        async fetchBackups() {
            this.backupsView.loading = true;
            try {
                // Fetch both global and project backups in parallel
                const [globalRes, projectRes] = await Promise.all([
                    fetch('/api/config/backups?scope=global'),
                    fetch('/api/config/backups?scope=project')
                ]);

                if (!globalRes.ok) {
                    throw new Error(`Failed to fetch global backups: HTTP ${globalRes.status}`);
                }
                if (!projectRes.ok) {
                    throw new Error(`Failed to fetch project backups: HTTP ${projectRes.status}`);
                }

                const globalData = await globalRes.json();
                const projectData = await projectRes.json();

                this.backupsView.globalBackups = globalData.backups || [];
                this.backupsView.projectBackups = projectData.backups || [];
            } catch (err) {
                console.error('Failed to fetch backups:', err);
                this.showToast('Failed to load backups');
            } finally {
                this.backupsView.loading = false;
            }
        },

        /**
         * Format backup timestamp for display
         * @param {string} isoTimestamp - ISO timestamp string
         * @returns {string} Formatted date/time string
         */
        formatBackupTime(isoTimestamp) {
            if (!isoTimestamp || isoTimestamp === 'unknown') {
                return 'Unknown';
            }
            try {
                const date = new Date(isoTimestamp);
                return date.toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch {
                return isoTimestamp;
            }
        },

        /**
         * Restore config from backup
         * Story 17.10 AC5: Restore backup with confirmation
         * @param {string} scope - 'global' or 'project'
         * @param {number} version - Backup version (1 = newest)
         */
        async restoreBackup(scope, version) {
            // Story 17.10 AC5: Confirmation dialog with unsaved changes warning
            let message = `Restore ${scope} config from backup version ${version}?\n\n` +
                `This will replace the current ${scope} configuration and cannot be undone.`;

            // Add warning if there are pending updates
            if (this.pendingUpdates.length > 0) {
                message += `\n\n⚠️ WARNING: You have ${this.pendingUpdates.length} unsaved change(s) that will be discarded.`;
            }

            const confirmed = confirm(message);
            if (!confirmed) return;

            this.backupsView.restoring = true;
            try {
                const res = await fetch('/api/config/restore', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ scope, version })
                });

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    if (res.status === 404) {
                        throw new Error(data.message || 'Backup not found');
                    } else if (res.status === 400) {
                        throw new Error(data.message || 'Invalid backup content');
                    } else {
                        throw new Error(data.message || `Restore failed: HTTP ${res.status}`);
                    }
                }

                this.showToast(`Restored ${scope} config from backup v${version}`);

                // Refresh backups list and config data
                await Promise.all([
                    this.fetchBackups(),
                    this.fetchConfig()
                ]);

                // Clear pending changes since we just restored
                this.pendingUpdates = [];
                this.validationErrors = {};
                this.settingsView.hasChanges = false;
                this.settingsView.staleData = false;

            } catch (err) {
                console.error('Failed to restore backup:', err);
                this.showToast(`Restore failed: ${err.message}`);
            } finally {
                this.backupsView.restoring = false;
            }
        },

        /**
         * View backup content in modal
         * Story 17.10 AC6: Display backup content for inspection
         * @param {string} scope - 'global' or 'project'
         * @param {object} backup - Backup object with path, version, modified
         */
        async viewBackup(scope, backup) {
            try {
                // Story 17.10 AC6: Use dedicated backup content endpoint (supports global backups)
                const res = await fetch(`/api/config/backup/content?scope=${scope}&version=${backup.version}`);

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    throw new Error(data.error || `Failed to load backup: HTTP ${res.status}`);
                }

                const content = await res.text();

                // Display in content modal
                this.contentModal.title = `${scope.charAt(0).toUpperCase() + scope.slice(1)} Backup v${backup.version}`;
                this.contentModal.content = content;
                this.contentModal.type = 'text';  // YAML as plain text
                this.contentModal.show = true;

            } catch (err) {
                console.error('Failed to view backup:', err);
                this.showToast(`Failed to load backup: ${err.message}`);
            }
        },

        /**
         * Check if any backups exist
         * @returns {boolean} True if there are any backups
         */
        hasBackups() {
            return this.backupsView.globalBackups.length > 0 ||
                   this.backupsView.projectBackups.length > 0;
        },

        // ==========================================
        // Playwright Status Methods (Story 17.11)
        // ==========================================

        /**
         * Fetch Playwright status with 30s debounce
         * Story 17.11 AC6: Auto-fetch with caching
         */
        async fetchPlaywrightStatus() {
            // Prevent concurrent fetches
            if (this.playwrightStatus.loading) return;

            const now = Date.now();
            if (now - this.playwrightStatus.lastFetch < this.PLAYWRIGHT_STATUS_CACHE_MS) {
                return;  // Use cached data
            }
            await this.refreshPlaywrightStatus();
        },

        /**
         * Force refresh Playwright status (no debounce)
         * Story 17.11 AC5: Manual refresh button
         */
        async refreshPlaywrightStatus() {
            this.playwrightStatus.loading = true;
            this.playwrightStatus.error = null;

            try {
                const res = await fetch('/api/playwright/status');
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    throw new Error(data.error || `HTTP ${res.status}`);
                }

                const data = await res.json();
                this.playwrightStatus.data = data;
                this.playwrightStatus.lastFetch = Date.now();
            } catch (err) {
                console.error('Failed to fetch Playwright status:', err);
                this.playwrightStatus.error = err.message || 'Failed to check status';
            } finally {
                this.playwrightStatus.loading = false;
                this.$nextTick(() => this.refreshIcons());
            }
        },

        /**
         * Get status badge config for display
         * Story 17.11 AC2: Badge shows Ready/Not Installed/Missing Deps/No Browsers
         */
        getPlaywrightStatusBadge() {
            const s = this.playwrightStatus;

            if (s.loading) {
                return { text: 'Checking...', class: 'badge-secondary', icon: 'loader-2' };
            }

            if (s.error) {
                return { text: 'Error', class: 'bg-destructive/20 text-destructive', icon: 'alert-circle' };
            }

            if (!s.data) {
                return { text: 'Unknown', class: 'badge-secondary', icon: 'help-circle' };
            }

            if (s.data.ready) {
                return { text: 'Ready', class: 'bg-accent/20 text-accent', icon: 'check-circle' };
            }

            if (!s.data.package_installed) {
                return { text: 'Not Installed', class: 'bg-destructive/20 text-destructive', icon: 'x-circle' };
            }

            // Check for browsers BEFORE deps_ok (deps_ok is false when no browsers installed)
            const hasAnyBrowser = s.data.browsers.chromium || s.data.browsers.firefox || s.data.browsers.webkit;
            if (!hasAnyBrowser) {
                return { text: 'No Browsers', class: 'bg-bp-warning/20 text-bp-warning', icon: 'alert-triangle' };
            }

            if (!s.data.deps_ok) {
                return { text: 'Missing Deps', class: 'bg-bp-warning/20 text-bp-warning', icon: 'alert-triangle' };
            }

            // Fallback for any other unexpected state
            return { text: 'Unknown', class: 'badge-secondary', icon: 'help-circle' };
        },

        /**
         * Get formatted browsers list from status
         * Story 17.11 AC3: Show installed browsers
         */
        getInstalledBrowsersList() {
            const browsers = this.playwrightStatus.data?.browsers;
            if (!browsers) return '';

            const installed = [];
            if (browsers.chromium) installed.push('chromium');
            if (browsers.firefox) installed.push('firefox');
            if (browsers.webkit) installed.push('webkit');

            return installed.length > 0 ? installed.join(', ') : 'none';
        },

        /**
         * Copy install commands to clipboard
         * Story 17.11 AC4: Copy All button
         */
        async copyInstallCommands() {
            const commands = this.playwrightStatus.data?.install_commands || [];
            if (commands.length === 0) {
                this.showToast('No commands to copy');
                return;
            }

            const text = commands.join('\n');
            await this.copyToClipboard(text);
        },

        // ==========================================
        // Config Export/Import Methods (Story 17.12)
        // ==========================================

        /**
         * Export configuration as YAML download
         * Story 17.12 AC2: Export button with dropdown
         * @param {string} scope - 'merged' | 'global' | 'project'
         */
        async exportConfig(scope = 'merged') {
            this.exportView.loading = true;
            this.exportView.dropdownOpen = false;

            try {
                const res = await fetch(`/api/config/export?scope=${scope}`);

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    throw new Error(data.message || `Export failed: HTTP ${res.status}`);
                }

                // Get filename from Content-Disposition header or generate
                const disposition = res.headers.get('Content-Disposition');
                let filename = `bmad-config-${scope}.yaml`;
                if (disposition) {
                    const match = disposition.match(/filename="(.+)"/);
                    if (match) filename = match[1];
                }

                // Create download with delayed cleanup for browser compatibility
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                // Delay cleanup to ensure download completes on slower devices
                setTimeout(() => URL.revokeObjectURL(url), 5000);

                this.showToast(`Exported ${scope} config`);

            } catch (err) {
                console.error('Export failed:', err);
                this.showToast(`Export failed: ${err.message}`);
            } finally {
                this.exportView.loading = false;
            }
        },

        /**
         * Trigger file picker for import
         * Story 17.12 AC5: Import button opens file picker
         */
        openImportFilePicker() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.yaml,.yml';
            input.onchange = (e) => {
                const file = e.target.files?.[0];
                if (file) this.startImport(file);
            };
            input.click();
        },

        /**
         * Read file and request import preview
         * Story 17.12 AC5/AC6: Read file, POST preview, show modal
         */
        async startImport(file) {
            // Check file size client-side (100KB limit)
            if (file.size > 100 * 1024) {
                this.showToast('Import file too large. Maximum size: 100KB');
                return;
            }

            this.importView.loading = true;
            this.importView.filename = file.name;
            this.importView.errors = null;
            this.importView.diff = null;

            try {
                const content = await file.text();
                this.importView.content = content;  // Store for scope switching
                await this._fetchImportPreview();
            } catch (err) {
                console.error('Import failed:', err);
                this.showToast(`Import failed: ${err.message}`);
                this.importView.loading = false;
            }
        },

        /**
         * Re-fetch diff preview when scope changes (uses stored content)
         * Story 17.12 AC6: Scope selector triggers re-fetch
         */
        async refreshImportPreview() {
            if (!this.importView.content) return;
            this.importView.loading = true;
            this.importView.errors = null;
            this.importView.diff = null;
            await this._fetchImportPreview();
        },

        /**
         * Internal: Fetch import preview from backend
         * Story 17.12 AC3/AC4/AC8: Preview mode returns diff or errors
         */
        async _fetchImportPreview() {
            try {
                const res = await fetch('/api/config/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        scope: this.importView.scope,
                        content: this.importView.content,
                        confirmed: false,
                    }),
                });

                const data = await res.json();

                if (res.status === 422) {
                    // Pydantic validation errors
                    this.parseValidationErrors(data);
                    this.importView.errors = 'validation';
                    this.importView.modalOpen = true;
                } else if (res.status === 403) {
                    // DANGEROUS fields present
                    this.importView.errors = `Import contains restricted fields: ${data.dangerous_fields.join(', ')}`;
                    this.importView.modalOpen = true;
                } else if (!res.ok) {
                    throw new Error(data.message || `Import failed: HTTP ${res.status}`);
                } else {
                    // Success - show diff preview
                    this.importView.diff = data.diff;
                    this.importView.riskyFields = data.risky_fields || [];
                    this.importView.modalOpen = true;
                }
            } finally {
                this.importView.loading = false;
                this.$nextTick(() => this.refreshIcons());
            }
        },

        /**
         * Check if import has any changes to apply
         * Story 17.12 AC6: Disable Apply button when no changes
         * @returns {boolean} True if diff contains any changes
         */
        hasImportChanges() {
            const d = this.importView.diff;
            if (!d) return false;
            return Object.keys(d.added || {}).length > 0 ||
                   Object.keys(d.modified || {}).length > 0 ||
                   (d.removed || []).length > 0;
        },

        /**
         * Apply the imported configuration
         * Story 17.12 AC7: Apply import with risky field confirmation
         */
        async applyImport() {
            // Handle risky fields confirmation
            if (this.importView.riskyFields.length > 0) {
                const confirmed = confirm(
                    `The following settings require confirmation:\n\n` +
                    `• ${this.importView.riskyFields.join('\n• ')}\n\n` +
                    `Modifying these could affect workflow behavior. Continue?`
                );
                if (!confirmed) return;
            }

            this.importView.loading = true;

            try {
                const res = await fetch('/api/config/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        scope: this.importView.scope,
                        content: this.importView.content,
                        confirmed: true,
                    }),
                });

                const data = await res.json();

                if (!res.ok) {
                    throw new Error(data.message || `Apply failed: HTTP ${res.status}`);
                }

                // Success
                this.importView.modalOpen = false;
                const count = data.updated_paths?.length || 0;
                this.showToast(`Configuration imported successfully. ${count} fields updated.`);

                // Suppress duplicate toast from SSE (Story 17.9 pattern)
                this._selfReloadTimestamp = Date.now();

                // Reload config in settings panel if open
                // Note: Backend already reloads config singleton and broadcasts SSE
                if (this.settingsView.open) {
                    await this.fetchConfig();
                }

            } catch (err) {
                console.error('Apply import failed:', err);
                this.importView.errors = err.message;
            } finally {
                this.importView.loading = false;
            }
        },

        /**
         * Close import modal and reset state
         * Story 17.12 AC6: Cancel button
         */
        closeImportModal() {
            this.importView.modalOpen = false;
            this.importView.diff = null;
            this.importView.errors = null;
            this.importView.content = '';
            this.importView.filename = '';
            this.importView.riskyFields = [];
        }
    };
}
