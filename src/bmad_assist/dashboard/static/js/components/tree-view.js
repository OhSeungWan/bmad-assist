/**
 * Tree-view component for epic/story navigation
 * Handles sidebar tree structure, selection, and story fetching
 */

window.treeViewComponent = function() {
    return {
        // State
        stories: {},
        expandedEpics: [],
        expandedStories: [],
        selectedItem: {
            type: null,      // 'epic' | 'story' | 'phase'
            epic: null,      // Epic object
            story: null,     // Story object (if type is 'story' or 'phase')
            phase: null      // Phase object (if type is 'phase')
        },
        loading: true,
        loadError: null,

        // Fetch stories from API
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

        // Toggle epic expansion
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

        // Toggle story expansion
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

        // Select item for detail panel (Story 16.5)
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

        // Get story status (for tree display)
        getStoryStatus(story) {
            return story?.status || 'backlog';
        },

        // Normalize SSE phase names (UPPER_SNAKE_CASE) to snake_case for matching phase.id
        _normalizePhaseIdFromSSE(ssePhase) {
            return ssePhase ? ssePhase.toLowerCase() : '';
        },

        // Update story phase from SSE event
        _updateStoryPhase(phaseData) {
            // Update the current phase for a story in the stories tree
            if (!this.stories.epics) return;

            // Story 22.9: Access nested data field from SSE event structure
            // Event structure: {type, timestamp, run_id, sequence_id, data: {current_story, ...}}
            const eventData = phaseData.data || phaseData;
            const storyId = eventData.current_story;
            if (!storyId) return;

            const parts = storyId.split('.');
            if (parts.length !== 2) return;

            // Don't parseInt the epic part - it can be a string (e.g. "testarch")
            const epicId = parts[0];
            const storyNum = parseInt(parts[1], 10);

            // Find the epic (handle both numeric and string comparison)
            const epic = this.stories.epics.find(e => String(e.id) === String(epicId));
            if (!epic) return;

            // Find the story (handle both numeric and string comparison)
            const story = epic.stories.find(s => String(s.id) === String(storyNum));
            if (!story) return;

            // Normalize SSE phase name (CREATE_STORY → create_story) to match phase.id
            const normalizedPhaseId = this._normalizePhaseIdFromSSE(eventData.current_phase);

            // Update phase status - mark previous phases as completed
            if (story.phases) {
                let foundCurrentPhase = false;
                story.phases.forEach(phase => {
                    if (phase.id === normalizedPhaseId) {
                        phase.status = eventData.phase_status;
                        foundCurrentPhase = true;
                    } else if (!foundCurrentPhase && eventData.phase_status === 'in-progress') {
                        // Mark previous phases as completed when current phase is in-progress
                        phase.status = 'completed';
                    }
                });
            }

            // Re-render Lucide icons after phase update
            this.$nextTick(() => this.refreshIcons());
        },

        // Update story status from SSE event
        _updateStoryStatus(statusData) {
            // Update the status badge for a story in the stories tree
            if (!this.stories.epics) return;

            // Story 22.9: Access nested data field from SSE event structure
            const eventData = statusData.data || statusData;

            // Handle both numeric and string epic IDs
            const epic = this.stories.epics.find(e => String(e.id) === String(eventData.epic_num));
            if (!epic) return;

            const story = epic.stories.find(s => String(s.id) === String(eventData.story_num));
            if (!story) return;

            // Update story status
            story.status = eventData.status;

            // Re-render Lucide icons after status update
            this.$nextTick(() => this.refreshIcons());
        },

        // Handle story transition from SSE event
        _updateStoryTransition(transitionData) {
            // Handle story transitions with highlighting
            if (!this.stories.epics) return;

            // Story 22.9: Access nested data field from SSE event structure
            const eventData = transitionData.data || transitionData;

            // Handle both numeric and string epic IDs
            const epic = this.stories.epics.find(e => String(e.id) === String(eventData.epic_num));
            if (!epic) return;

            const story = epic.stories.find(s => String(s.id) === String(eventData.story_num));
            if (!story) return;

            // Update story status based on action
            if (eventData.action === 'started') {
                story.status = 'in-progress';
                // Auto-expand the epic and story for visibility
                if (!this.expandedEpics.includes(epic.id)) {
                    this.expandedEpics.push(epic.id);
                }
                const storyKey = `${epic.id}-${story.id}`;
                if (!this.expandedStories.includes(storyKey)) {
                    this.expandedStories.push(storyKey);
                }
            } else if (eventData.action === 'completed') {
                story.status = 'done';
            }

            // Re-render Lucide icons after transition
            this.$nextTick(() => this.refreshIcons());
        },

        // View epic details in modal
        async viewEpicDetails(epicId) {
            try {
                // Show loading toast (consistent with viewStoryModal pattern)
                this.showToast('Loading epic...');

                const res = await fetch(`/api/epics/${epicId}`);

                // Handle 404 specifically for better UX
                if (res.status === 404) {
                    this.showToast(`Epic ${epicId} not found`);
                    return;
                }

                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}`);
                }

                const data = await res.json();

                // Story 24.6: Initialize browser state for Raw/Rendered toggle
                this.contentModal.browser = window.contentBrowserComponent().createBrowserState();

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

        // View epic benchmark metrics in modal (Story 24.7)
        async viewEpicMetrics(epicId) {
            // Show loading state BEFORE fetch (Task 2.2)
            this.metricsModal.epicId = epicId;
            this.metricsModal.loading = true;
            this.metricsModal.show = true;
            try {
                const res = await fetch(`/api/epics/${epicId}/metrics`);
                if (!res.ok) {
                    if (res.status === 404) {
                        // AC6: Toast message when no metrics found
                        this.showToast('Metrics not available for this epic');
                        this.metricsModal.show = false;
                        this.metricsModal.loading = false;
                        return;
                    }
                    const data = await res.json();
                    throw new Error(data.error || `HTTP ${res.status}`);
                }
                const data = await res.json();
                // Story 24.7: Open dedicated metrics modal with visualization
                this.openEpicMetrics(epicId, data);
            } catch (err) {
                console.error('Failed to fetch epic metrics:', err);
                this.showToast('Failed to load epic metrics');
                this.metricsModal.show = false;
            } finally {
                this.metricsModal.loading = false;
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
            // Map phase.id (snake_case) to workflow names (kebab-case)
            const phaseToWorkflow = {
                'create_story': 'create-story',
                'validate_story': 'validate-story',
                'validate_story_synthesis': 'validate-story-synthesis',
                'dev_story': 'dev-story',
                'code_review': 'code-review',
                'code_review_synthesis': 'code-review-synthesis',
            };

            const workflow = phaseToWorkflow[nextPhase.id];
            if (!workflow) {
                this.showToast(`Unknown workflow for phase: ${nextPhase.name}`);
                return;
            }

            console.log(`Starting ${workflow} for story ${epic.id}.${nextStory.id}`);
            await this.runWorkflow(workflow, epic.id, nextStory.id);
        }
    };
};
