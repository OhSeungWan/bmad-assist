/**
 * Context menu component for epic/story/phase actions
 * Handles right-click and kebab menu interactions
 */

window.contextMenuComponent = function() {
    return {
        // Context menu state
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

        /**
         * Show context menu at position
         * @param {Event} event - Mouse event
         * @param {string} type - 'epic' | 'story' | 'phase'
         * @param {object} item - The item being clicked
         * @param {object} epic - Parent epic (for story/phase)
         * @param {object} story - Parent story (for phase)
         * @param {string} source - 'rightclick' | 'kebab'
         */
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

        /**
         * Adjust context menu position to keep within viewport
         * @param {number} x - Initial x position
         * @param {number} y - Initial y position
         * @returns {object} Adjusted {x, y} position
         */
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

        /**
         * Get available actions for context menu item
         * @param {string} type - Item type
         * @param {object} item - Item object
         * @returns {array} Array of action objects
         */
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

        /**
         * Get actions for story based on status
         * @param {object} story - Story object
         * @returns {array} Array of action objects
         */
        getStoryActions(story) {
            const status = story?.status || 'backlog';

            // Story 24.5: "View Story" is always first action for all statuses (AC 1)
            // Status-based action mapping per AC 3, 4, 6
            switch (status) {
                case 'backlog':
                    return [
                        { icon: '📄', label: 'View Story', action: 'view-story-modal', testId: 'action-view-story-modal' },
                        { icon: '📄', label: 'View in epic', action: 'view-story', testId: 'action-view-story' }
                    ];

                case 'ready-for-dev':
                    // Story 24.10: Removed 'View prompt' - prompts are phase-specific, not story-level
                    return [
                        { icon: '📄', label: 'View Story', action: 'view-story-modal', testId: 'action-view-story-modal' },
                        { icon: '▶️', label: 'Run dev-story', action: 'run-dev-story', testId: 'action-run-dev-story', primary: true },
                        { icon: '📝', label: 'Open story file', action: 'open-file', testId: 'action-open-file' }
                    ];

                case 'in-progress':
                    // Story 24.10: Removed 'View prompt' - prompts are phase-specific, not story-level
                    return [
                        { icon: '📄', label: 'View Story', action: 'view-story-modal', testId: 'action-view-story-modal' },
                        { icon: '📝', label: 'Open story file', action: 'open-file', testId: 'action-open-file' }
                    ];

                case 'review':
                    // Story 24.10: Removed 'View prompt' - prompts are phase-specific, not story-level
                    return [
                        { icon: '📄', label: 'View Story', action: 'view-story-modal', testId: 'action-view-story-modal' },
                        { icon: '📝', label: 'Open story file', action: 'open-file', testId: 'action-open-file' },
                        { icon: '👀', label: 'View review', action: 'view-review', testId: 'action-view-review' }
                    ];

                case 'done':
                    // Story 24.10: Removed 'View prompt' - prompts are phase-specific, not story-level
                    return [
                        { icon: '📄', label: 'View Story', action: 'view-story-modal', testId: 'action-view-story-modal' },
                        { icon: '👀', label: 'View review', action: 'view-review', testId: 'action-view-review' },
                        { icon: '🔄', label: 'Re-run', action: 're-run', testId: 'action-re-run', danger: true }
                    ];

                default:
                    return [
                        { icon: '📄', label: 'View Story', action: 'view-story-modal', testId: 'action-view-story-modal' },
                        { icon: '📄', label: 'View in epic', action: 'view-story', testId: 'action-view-story' }
                    ];
            }
        },

        /**
         * Get actions for phase
         * @param {object} phase - Phase object
         * @returns {array} Array of action objects
         */
        getPhaseActions(phase) {
            // Story 24.2: Use phase.id (snake_case) not phase.name (display name) for matching
            // Phase objects have: id (e.g., "create_story"), name (e.g., "Create Story")
            const phaseId = phase?.id || '';
            const phaseStatus = phase?.status || 'pending';
            const actions = [];

            // Story 24.2 AC2: View prompt available for all phases regardless of status
            // API returns 404 if prompt file doesn't exist, handled gracefully with toast
            actions.push({ icon: '📋', label: 'View prompt', action: 'view-prompt', testId: 'action-view-prompt' });

            // Phase-specific actions per wireframe 3b/3c (use phase.id snake_case for matching)
            if (phaseId === 'create_story') {
                // View story file only when create_story is completed
                if (phaseStatus === 'completed') {
                    actions.push({ icon: '📄', label: 'View story file', action: 'view-story-file', testId: 'action-view-story-file' });
                }
            } else if (phaseId === 'validate_story' || phaseId === 'validate_story_synthesis') {
                actions.push({ icon: '📊', label: 'View validation reports', action: 'view-validation-reports', testId: 'action-view-validation-reports' });
                actions.push({ icon: '📝', label: 'View synthesis', action: 'view-synthesis', testId: 'action-view-synthesis' });
            } else if (phaseId === 'dev_story') {
                actions.push({ icon: '📄', label: 'View story output', action: 'view-story-output', testId: 'action-view-story-output' });
            } else if (phaseId === 'code_review' || phaseId === 'code_review_synthesis') {
                actions.push({ icon: '📊', label: 'View review reports', action: 'view-review-reports', testId: 'action-view-review-reports' });
                actions.push({ icon: '📝', label: 'View synthesis', action: 'view-synthesis', testId: 'action-view-synthesis' });
            } else if (phaseId === 'atdd') {
                actions.push({ icon: '✅', label: 'View ATDD checklist', action: 'view-atdd-checklist', testId: 'action-view-atdd-checklist' });
            }

            // Common actions for all phases (separator before destructive section per wireframe 3b)
            actions.push({ icon: '🔄', label: 'Re-run this phase', action: 're-run-phase', testId: 'action-re-run-phase', danger: true });
            actions.push({ icon: '⏭️', label: 'Skip to next phase', action: 'skip-phase', testId: 'action-skip-phase', danger: true });

            return actions;
        },

        /**
         * Execute context menu action
         * @param {object} action - Action object with action property
         */
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
                    await this.viewEpicMetrics(item?.id);
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
                    // Story 24.10: Only phase-level View Prompt remains
                    // Fallback to 'dev_story' if phase ID is missing (defensive)
                    const phaseId = item?.id || 'dev_story';
                    if (!item?.id) {
                        console.warn('Phase ID undefined, falling back to dev_story');
                    }
                    await this.viewPrompt(epic?.id, story?.id, phaseId);
                    break;
                case 'open-file':
                    // Copy story file path to clipboard
                    if (item?.file_path) {
                        this.openFile(item.file_path);
                    } else {
                        // Construct path from story info (stories are in implementation-artifacts directly)
                        const storyPath = `_bmad-output/implementation-artifacts/${epic?.id}-${item?.id}-*.md`;
                        this.openFile(storyPath);
                    }
                    break;
                case 'view-review':
                    await this.viewReports(epic?.id, story?.id || item?.id);
                    break;
                case 'view-story':
                    await this.viewStoryInEpic(epic?.id, item?.id);
                    break;
                case 'view-story-modal':
                    // Story 24.5: View story file content in modal
                    await this.viewStoryModal(epic?.id, item?.id);
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
                    // Story 24.2: Use phase ID (snake_case) not display name
                    const rerunPhaseId = item?.id;
                    if (!rerunPhaseId) {
                        console.warn('Phase ID undefined for re-run, aborting');
                        this.showToast('Cannot re-run: phase ID missing');
                        break;
                    }
                    await this.runWorkflow(rerunPhaseId, epic?.id, story?.id);
                    break;
                case 'skip-phase':
                    console.warn('Skip phase API not yet implemented - deferred to future backend story');
                    this.showToast('Skip phase not yet implemented');
                    break;

                default:
                    console.log('Unhandled action:', action.action, item);
            }
        },

        /**
         * View compiled prompt
         * Opens in Prompt Browser for structured hierarchical view (Story 23.5)
         *
         * @param {number} epic - Epic ID
         * @param {number} story - Story ID
         * @param {string} phase - Phase ID (snake_case, e.g., "create_story")
         */
        async viewPrompt(epic, story, phase) {
            // Story 24.10 synthesis: Validate required parameters
            if (!epic || !story || !phase) {
                console.error('Missing required parameters for viewPrompt', { epic, story, phase });
                this.showToast('Unable to load prompt: missing context');
                return;
            }
            try {
                const res = await fetch(`/api/prompt/${epic}/${story}/${phase}`);
                if (res.ok) {
                    const text = await res.text();
                    // Story 23.5: Route to Prompt Browser for structured view
                    // Story 24.2 AC3: Use "Prompt" terminology consistently
                    this.openPromptBrowser(`Prompt: ${phase} [${epic}.${story}]`, text);
                } else if (res.status === 404) {
                    // Story 24.2 AC3: Show toast with "Prompt" terminology
                    const data = await res.json();
                    this.showToast(data.error || `Prompt not found for phase: ${phase}`);
                } else {
                    throw new Error(`HTTP ${res.status}`);
                }
            } catch (err) {
                // Story 24.2 AC3: Use "Prompt" terminology in error messages
                console.error('Failed to fetch prompt:', err);
                this.showToast('Failed to fetch prompt');
            }
        },

        /**
         * View validation/code-review reports
         * Story 24.8 AC5: Await mapping load before showing modal
         * @param {number} epic - Epic ID
         * @param {number} story - Story ID
         */
        async viewReports(epic, story) {
            try {
                const res = await fetch(`/api/reviews/${epic}/${story}`);
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}`);
                }
                const data = await res.json();
                // Populate reportModal with both validation and code-review sections
                this.reportModal.epic = epic;
                this.reportModal.story = story;
                this.reportModal.validation = data.validation || { reports: [], synthesis: null };
                this.reportModal.code_review = data.code_review || { reports: [], synthesis: null };

                // Story 24.8 AC5: Await mapping load BEFORE showing modal
                // This ensures consistent display from initial render (model names, not letters)
                // Graceful degradation: if mapping fails, modal still opens with original letters
                if (this.loadReportValidatorMapping) {
                    await this.loadReportValidatorMapping(epic, story);
                }

                this.reportModal.show = true;
            } catch (err) {
                console.error('Failed to fetch reviews:', err);
                this.showToast('Failed to fetch review reports');
            }
        },

        /**
         * View story file content in modal
         * Story 24.5: Fetches story content from implementation-artifacts
         * and displays in modal with Raw/Rendered toggle support.
         *
         * @param {string} epicId - Epic identifier
         * @param {string} storyId - Story number
         */
        async viewStoryModal(epicId, storyId) {
            try {
                // AC 2: Show loading toast before fetch
                this.showToast('Loading story...');

                // Fetch story content from backend
                const res = await fetch(`/api/story/${epicId}/${storyId}/content`);

                if (res.status === 404) {
                    // AC 5: Show toast and do NOT open modal on 404
                    this.showToast(`Story file not found for ${epicId}.${storyId}`);
                    return;
                }

                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}`);
                }

                const data = await res.json();

                // AC 3: Initialize browser state for Raw/Rendered toggle
                // Uses Story 24.1 shared infrastructure
                this.contentModal.browser = window.contentBrowserComponent().createBrowserState();

                // AC 2: Set modal title with story info
                this.contentModal.title = `Story ${epicId}.${storyId}: ${data.title}`;
                this.contentModal.content = data.content;
                this.contentModal.type = 'markdown';

                // Fetch-first pattern: Only show modal after fetch succeeds
                this.contentModal.show = true;

            } catch (err) {
                // AC 5: Show toast on error, do NOT open modal
                console.error('Failed to load story content:', err);
                this.showToast('Failed to load story');
            }
        },

        /**
         * Load individual report content
         * Story 24.9: Adds browser state for Raw/Rendered toggle support
         * @param {object} report - Report object with path and provider
         */
        async loadReportContent(report) {
            // Story 24.9: Loading feedback for UX consistency with viewStoryModal/viewEpicDetails
            this.showToast('Loading report...');

            try {
                const res = await fetch(`/api/report/content?path=${encodeURIComponent(report.path)}`);
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.error || `HTTP ${res.status}`);
                }
                let content = await res.text();

                // Story 23.8: Apply validator ID mapping for synthesis reports
                if (this.isSynthesisReport && this.isSynthesisReport(report.path)) {
                    if (this.replaceValidatorIdsInContent) {
                        content = this.replaceValidatorIdsInContent(content);
                    }
                }

                // AC 6.4: Display in contentModal with provider attribution
                // Story 24.8: Use mapped model name for consistency with report list
                const displayName = this.getReportDisplayName ? this.getReportDisplayName(report) : report.provider;
                const storyRef = `[${this.reportModal.epic}.${this.reportModal.story}]`;
                const title = displayName ? `Report: ${displayName} ${storyRef}` : `Synthesis Report ${storyRef}`;
                this.contentModal.title = title;
                this.contentModal.content = content;
                this.contentModal.type = 'markdown';

                // Story 24.9: Initialize browser state for Raw/Rendered toggle
                // Must be set BEFORE contentModal.show = true for consistent initial render
                // Defensive check: if content-browser.js failed to load, browser controls will be unavailable
                if (window.contentBrowserComponent) {
                    this.contentModal.browser = window.contentBrowserComponent().createBrowserState();
                } else {
                    this.contentModal.browser = null;
                    console.warn('contentBrowserComponent not loaded - Raw/Rendered toggle unavailable');
                }

                this.contentModal.show = true;
            } catch (err) {
                console.error('Failed to load report content:', err);
                this.showToast(`Failed to load report: ${err.message || 'Network error'}`);
                // Note: Modal does NOT open on error - show=true is never reached
            }
        }
    };
};
