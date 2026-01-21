/**
 * Experiments component for experiment management
 * Handles experiments listing, details, fixtures, templates, comparison, and run triggering
 */

window.experimentsComponent = function() {
    return {
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

        // ==========================================
        // Experiment Details (Story 19.2)
        // ==========================================

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
         * Get status badge class for active experiment (overload for active experiment)
         * @returns {string}
         */
        getActiveExperimentStatusClass() {
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
        }
    };
};
