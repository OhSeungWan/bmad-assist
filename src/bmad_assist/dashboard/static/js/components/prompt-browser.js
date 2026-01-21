/**
 * Prompt Browser component for viewing compiled BMAD prompts
 * Provides hierarchical XML viewing with collapsible sections
 *
 * Story 23.5 - Prompt Browser Core
 * Story 23.6 - CDATA & Content Detection
 * Story 23.7 - Variables Panel
 * Story 23.8 - Validator Identity Mapping
 */

window.promptBrowserComponent = function() {
    return {
        // Prompt browser state
        promptBrowser: {
            show: false,
            title: '',
            content: '',    // Raw XML string
            parsed: null,   // Parsed structure
            loading: false,
            parseError: null
        },

        // Variables panel view state (Story 23.7)
        variablesView: 'rendered',  // 'rendered' | 'raw'

        // Track expanded sections (collapsed by default for files)
        _expandedSections: new Set(),

        // Track pending Shiki highlight timeouts for cleanup (Story 23.6)
        _pendingPromptBrowserHighlights: [],

        // Story 23.8: Validator identity mapping state
        _validatorMapping: {},      // {"Validator A": "glm-4.7", ...}
        _validatorMappingLoaded: false,
        _validatorMappingEpic: null,
        _validatorMappingStory: null,

        /**
         * Parse compiled-workflow XML structure.
         * Extracts: mission, context (with files), variables, file-index, instructions, output-template
         *
         * @param {string} xmlContent - Raw XML content
         * @returns {object|null} Parsed structure or null on error
         */
        parsePromptXml(xmlContent) {
            if (!xmlContent) return null;

            const parser = new DOMParser();
            const doc = parser.parseFromString(xmlContent, 'text/xml');

            // Check for parse errors (parsererror element indicates malformed XML)
            const parseError = doc.querySelector('parsererror');
            if (parseError) {
                const errorMsg = parseError.textContent || 'Unknown XML parsing error';
                console.warn('XML parse error:', errorMsg);
                this.promptBrowser.parseError = errorMsg;
                return null;
            }

            // Get root element
            const root = doc.querySelector('compiled-workflow');
            if (!root) {
                this.promptBrowser.parseError = 'Invalid prompt structure: missing compiled-workflow root';
                return null;
            }

            try {
                const mission = this._extractSection(root, 'mission');
                const instructions = this._extractSection(root, 'instructions');
                const output = this._extractSection(root, 'output-template');

                // Extract variables with raw XML, project root, and categorized data (Story 23.7)
                const variablesData = this._extractVariables(root);

                return {
                    mission,
                    missionContentType: this.detectContentType(mission),
                    context: this._extractContext(root),
                    variables: variablesData.variables,
                    rawVariablesXml: variablesData.rawXml,
                    projectRoot: variablesData.projectRoot,
                    categorizedVariables: variablesData.categorized,
                    fileIndex: this._extractFileIndex(root),
                    instructions,
                    instructionsContentType: this.detectContentType(instructions),
                    output,
                    outputContentType: this.detectContentType(output)
                };
            } catch (err) {
                console.error('Failed to parse prompt structure:', err);
                this.promptBrowser.parseError = `Parse error: ${err.message}`;
                return null;
            }
        },

        /**
         * Extract text content from a section element.
         * @private
         */
        _extractSection(root, tagName) {
            const el = root.querySelector(tagName);
            if (!el) return '';
            // textContent auto-unwraps CDATA
            return el.textContent || '';
        },

        /**
         * Extract context section with file elements.
         * Detects CDATA markers and content type for each file (Story 23.6).
         * @private
         */
        _extractContext(root) {
            const contextEl = root.querySelector('context');
            if (!contextEl) return { files: [], rawContent: '' };

            const files = [];
            const fileEls = contextEl.querySelectorAll('file');

            for (const fileEl of fileEls) {
                const id = fileEl.getAttribute('id') || '';
                const path = fileEl.getAttribute('path') || '';

                // CRITICAL: Check CDATA from innerHTML BEFORE textContent extraction (Story 23.6 AC1)
                // DOMParser auto-unwraps CDATA in textContent, so we need innerHTML for detection
                const rawHtml = fileEl.innerHTML || '';
                const hasCdata = /<!\[CDATA\[/.test(rawHtml) || /\]\]><!\[CDATA\[/.test(rawHtml);

                const content = fileEl.textContent || '';  // CDATA auto-unwrapped here

                // Cache content type during extraction (Story 23.6 AC2, AC3)
                const contentType = this.detectContentType(content);

                files.push({ id, path, content, hasCdata, contentType });
            }

            // If no file elements, use raw content
            if (files.length === 0) {
                return { files: [], rawContent: contextEl.textContent || '' };
            }

            return { files, rawContent: '' };
        },

        /**
         * Extract variables section (Story 23.7: stores raw XML for toggle view).
         * @private
         * @returns {{ variables: Array, rawXml: string|null, projectRoot: string|null, categorized: object }}
         */
        _extractVariables(root) {
            const varsEl = root.querySelector('variables');
            if (!varsEl) return { variables: [], rawXml: null, projectRoot: null, categorized: {} };

            // Store original XML for raw view (preserves formatting/comments)
            const rawXml = varsEl.outerHTML;

            const variables = [];
            const varEls = varsEl.querySelectorAll('var');

            for (const varEl of varEls) {
                const name = varEl.getAttribute('name') || '';
                const fileId = varEl.getAttribute('file_id') || null;
                const value = varEl.textContent || '';

                variables.push({ name, value, fileId });
            }

            // Detect project root and categorize (Story 23.7)
            const projectRoot = this._detectProjectRoot(variables);
            const categorized = this._categorizeVariables(variables, projectRoot);

            return { variables, rawXml, projectRoot, categorized };
        },

        /**
         * Extract file-index section.
         * @private
         */
        _extractFileIndex(root) {
            const indexEl = root.querySelector('file-index');
            if (!indexEl) return [];

            const entries = [];
            const entryEls = indexEl.querySelectorAll('entry');

            for (const entryEl of entryEls) {
                const id = entryEl.getAttribute('id') || '';
                const path = entryEl.getAttribute('path') || '';
                entries.push({ id, path });
            }

            return entries;
        },

        /**
         * Toggle section expanded/collapsed state.
         * @param {string} sectionId - Unique section identifier
         */
        toggleSection(sectionId) {
            if (this._expandedSections.has(sectionId)) {
                this._expandedSections.delete(sectionId);
            } else {
                this._expandedSections.add(sectionId);
            }
            // Refresh Lucide icons after toggle for chevron update
            this.$nextTick(() => this.refreshIcons());
        },

        /**
         * Check if section is expanded.
         * @param {string} sectionId - Section identifier
         * @returns {boolean} True if expanded
         */
        isExpanded(sectionId) {
            return this._expandedSections.has(sectionId);
        },

        /**
         * Get chevron icon name for section header.
         * Returns static 'chevron-right' - CSS handles rotation on expand.
         * @param {string} sectionId - Section identifier (unused, kept for API compat)
         * @returns {string} Lucide icon name
         */
        getChevronIcon(sectionId) {
            // Always return chevron-right; CSS rotates 90deg when expanded
            return 'chevron-right';
        },

        /**
         * Estimate token count for content (~4 chars per token).
         * @param {string} content - Content to estimate
         * @returns {string} Formatted token count (e.g., "~1.2k tokens")
         */
        estimateTokens(content) {
            if (!content) return '';
            const tokens = Math.ceil(content.length / 4);
            if (tokens >= 1000) {
                return `~${(tokens / 1000).toFixed(1)}k tokens`;
            }
            return `~${tokens} tokens`;
        },

        /**
         * Open the prompt browser modal.
         * @param {string} title - Modal title
         * @param {string} content - Raw XML content
         */
        openPromptBrowser(title, content) {
            // Set loading state
            this.promptBrowser.loading = true;
            this.promptBrowser.show = true;
            this.promptBrowser.title = title;
            this.promptBrowser.content = content;
            this.promptBrowser.parsed = null;
            this.promptBrowser.parseError = null;

            // Reset variables view to rendered for consistent fresh state (Story 23.7)
            this.variablesView = 'rendered';

            // Clear expanded sections for fresh view
            this._expandedSections.clear();

            // Story 24.4: Set default expanded sections (Mission and Instructions start expanded)
            this._expandedSections.add('mission');
            this._expandedSections.add('instructions');

            // Use performance markers for timing (AC4)
            performance.mark('prompt-browser-render-start');
            performance.mark('prompt-browser-parse-start');

            // Parse in next tick to allow loading UI to render
            this.$nextTick(() => {
                const parsed = this.parsePromptXml(content);
                this.promptBrowser.parsed = parsed;
                this.promptBrowser.loading = false;

                performance.mark('prompt-browser-parse-end');
                performance.measure('prompt-browser-parse', 'prompt-browser-parse-start', 'prompt-browser-parse-end');

                const parseMeasure = performance.getEntriesByName('prompt-browser-parse')[0];

                // Story 23.8: Initialize validator mapping after parsing
                this._initValidatorMapping();

                // Measure render time after DOM update
                this.$nextTick(() => {
                    performance.mark('prompt-browser-render-end');
                    performance.measure('prompt-browser-render', 'prompt-browser-render-start', 'prompt-browser-render-end');

                    const renderMeasure = performance.getEntriesByName('prompt-browser-render')[0];
                    console.log(`Prompt Browser: parse=${parseMeasure?.duration?.toFixed(0) || '?'}ms render=${renderMeasure?.duration?.toFixed(0) || '?'}ms`);

                    // Clean up performance entries
                    performance.clearMarks('prompt-browser-parse-start');
                    performance.clearMarks('prompt-browser-parse-end');
                    performance.clearMarks('prompt-browser-render-start');
                    performance.clearMarks('prompt-browser-render-end');
                    performance.clearMeasures('prompt-browser-parse');
                    performance.clearMeasures('prompt-browser-render');

                    // Refresh icons for chevrons
                    this.refreshIcons();
                });
            });
        },

        /**
         * Close prompt browser and reset state.
         */
        closePromptBrowser() {
            this.promptBrowser.show = false;
            this.promptBrowser.parsed = null;
            this.promptBrowser.parseError = null;
            this.promptBrowser.loading = false;
            this._expandedSections.clear();
            // Cancel pending Shiki highlights (Story 23.6)
            this._cancelPendingPromptBrowserHighlights();
            // Story 23.8: Reset validator mapping state
            this._validatorMapping = {};
            this._validatorMappingLoaded = false;
            this._validatorMappingEpic = null;
            this._validatorMappingStory = null;
        },

        /**
         * Get file extension from path for syntax highlighting.
         * @param {string} path - File path
         * @returns {string} Language identifier
         */
        getFileLanguage(path) {
            if (!path) return 'text';

            const ext = path.split('.').pop()?.toLowerCase() || '';
            const langMap = {
                'md': 'markdown',
                'py': 'python',
                'js': 'javascript',
                'ts': 'typescript',
                'tsx': 'typescript',
                'jsx': 'javascript',
                'yaml': 'yaml',
                'yml': 'yaml',
                'json': 'json',
                'xml': 'xml',
                'html': 'html',
                'css': 'css',
                'sh': 'bash',
                'bash': 'bash',
                'go': 'go',
                'rs': 'rust',
                'java': 'java',
                'kt': 'kotlin',
                'swift': 'swift',
                'rb': 'ruby',
                'php': 'php',
                'c': 'c',
                'cpp': 'cpp',
                'h': 'c',
                'hpp': 'cpp',
                'sql': 'sql'
            };

            return langMap[ext] || 'text';
        },

        /**
         * Get short filename from path.
         * @param {string} path - Full file path
         * @returns {string} Filename only
         */
        getFilename(path) {
            if (!path) return 'unknown';
            return path.split('/').pop() || path;
        },

        /**
         * Escape HTML for safe display (uses centralized util).
         * @param {string} text - Text to escape
         * @returns {string} Escaped HTML
         */
        escapeHtml(text) {
            if (window.dashboardUtils && window.dashboardUtils.escapeHtml) {
                return window.dashboardUtils.escapeHtml(text);
            }
            // Fallback
            if (!text) return '';
            return text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        },

        /**
         * Apply Shiki syntax highlighting to a file section when expanded.
         * Uses lazy loading - only highlights when section is opened.
         *
         * @param {string} sectionId - Section ID to highlight
         * @param {string} content - Code content
         * @param {string} lang - Language identifier
         */
        async highlightFileContent(sectionId, content, lang) {
            // Skip if Shiki not ready
            if (!window._shikiReady || !window.shikiHighlighter) {
                return;
            }

            const container = document.querySelector(`[data-section-id="${sectionId}"] .file-content-code`);
            if (!container) return;

            // Skip if content is rendered markdown (don't replace with Shiki highlight)
            if (container.querySelector('.markdown-content')) return;

            // Skip if already highlighted
            if (container.querySelector('.shiki:not(.shiki-loading)')) return;

            try {
                const html = await window.shikiHighlighter.highlightCode(content, lang);

                // Verify section is still expanded before updating DOM
                if (!this.isExpanded(sectionId)) return;

                // Parse and replace
                const temp = document.createElement('div');
                temp.innerHTML = html;
                const highlighted = temp.firstElementChild;

                if (highlighted) {
                    // Remove shiki class to avoid duplicate styles
                    container.innerHTML = '';
                    container.appendChild(highlighted);
                }
            } catch (err) {
                console.warn('Failed to highlight file content:', err);
            }
        },

        /**
         * Handle section toggle with lazy highlighting.
         * @param {string} sectionId - Section identifier
         * @param {string} content - File content
         * @param {string} lang - Language identifier
         */
        toggleFileSection(sectionId, content, lang) {
            this.toggleSection(sectionId);

            // If expanding, queue highlighting
            if (this.isExpanded(sectionId)) {
                this.$nextTick(() => {
                    this.highlightFileContent(sectionId, content, lang);
                });
            }
        },

        // ==========================================
        // Story 23.6 - Content Detection & Rendering
        // ==========================================

        /**
         * Detect content type for intelligent rendering (Story 23.6 AC2, AC3, AC5).
         * @param {string} content - Raw content to analyze
         * @returns {'markdown' | 'xml' | 'text'} Content type
         */
        detectContentType(content) {
            if (!content || content.length < 50) return 'text';

            const trimmed = content.trim();

            // Markdown indicators
            const hasHeader = /^#{1,6}\s/m.test(trimmed);
            const hasUnorderedList = /^[-*]\s/m.test(content);
            const hasOrderedList = /^\d+\.\s/m.test(content);
            const hasCodeBlock = /```[\w]*\n/.test(content);
            const hasBold = /\*\*[^*]+\*\*/.test(content);
            // Simplified italic detection without lookbehind (Safari < 16.4 compat)
            const hasItalic = /(?:^|[^*])\*[^*]+\*(?:[^*]|$)/.test(content);

            const mdIndicators = [hasHeader, hasUnorderedList, hasOrderedList, hasCodeBlock, hasBold, hasItalic]
                .filter(Boolean).length;

            // Strong markdown signal: header alone is definitive, or multiple indicators
            if (hasHeader || mdIndicators >= 2) return 'markdown';

            // XML detection
            const startsWithTag = /^<[a-zA-Z]/.test(trimmed);
            const hasBalancedTags = /<[a-zA-Z][^>]*>[\s\S]*<\/[a-zA-Z]+>/.test(content);

            if (startsWithTag && hasBalancedTags && mdIndicators === 0) return 'xml';

            // Ambiguous - default to text
            return 'text';
        },

        /**
         * Render Markdown content with full markdown parsing and Shiki highlighting (Story 23.6 AC2).
         * Uses marked.js for markdown parsing with custom renderer for code blocks.
         *
         * @param {string} content - Raw markdown content
         * @param {string} sectionId - Section ID for element tracking
         * @returns {string} HTML with rendered markdown and highlighted code blocks
         */
        renderMarkdownContent(content, sectionId) {
            if (!content) return '';

            const escapeHtml = window.dashboardUtils?.escapeHtml || this.escapeHtml.bind(this);
            const self = this;
            let blockCount = 0;

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
                            const blockId = `pb-md-${sectionId}-${blockCount++}-${Date.now()}`;

                            // Queue async highlighting
                            self._queuePromptBrowserHighlight(blockId, code, language);

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
         * Render XML content with Shiki syntax highlighting (Story 23.6 AC3, AC4).
         * Returns SYNCHRONOUS HTML with placeholder for async highlighting.
         *
         * @param {string} content - Raw XML content
         * @param {string} sectionId - Section ID for element tracking
         * @returns {string} HTML with XML syntax coloring
         */
        renderXmlContent(content, sectionId) {
            if (!content) return '';

            const escapeHtml = window.dashboardUtils?.escapeHtml || this.escapeHtml.bind(this);

            if (!window._shikiReady || !window.shikiHighlighter) {
                return `<pre class="shiki shiki-fallback"><code>${escapeHtml(content)}</code></pre>`;
            }

            // Create unique block ID for async update
            const blockId = `pb-xml-${sectionId}-${Date.now()}`;

            // Queue async highlighting
            this._queueXmlHighlight(blockId, content);

            // Return synchronous placeholder
            return `<pre class="shiki shiki-loading" data-block-id="${blockId}"><code>${escapeHtml(content)}</code></pre>`;
        },

        /**
         * Queue async Shiki highlighting (shared implementation).
         * Consolidates _queuePromptBrowserHighlight and _queueXmlHighlight.
         * @private
         * @param {string} blockId - DOM element block ID
         * @param {string} content - Code content to highlight
         * @param {string} lang - Language for Shiki
         */
        _queueHighlight(blockId, content, lang) {
            const timeoutId = setTimeout(async () => {
                // Remove from tracking array
                const idx = this._pendingPromptBrowserHighlights.indexOf(timeoutId);
                if (idx > -1) this._pendingPromptBrowserHighlights.splice(idx, 1);

                // Skip if modal was closed
                if (!this.promptBrowser.show) return;

                const block = document.querySelector(`[data-block-id="${blockId}"]`);
                if (!block) return;

                try {
                    const html = await window.shikiHighlighter.highlightCode(content, lang);
                    const temp = document.createElement('div');
                    temp.innerHTML = html;
                    const newBlock = temp.firstElementChild;

                    if (newBlock && block.parentElement) {
                        newBlock.setAttribute('data-block-id', blockId);
                        if (lang !== 'xml') newBlock.setAttribute('data-lang', lang);
                        block.parentElement.replaceChild(newBlock, block);
                    }
                } catch (err) {
                    console.warn(`${lang} highlighting failed:`, err);
                    block.classList.remove('shiki-loading');
                    block.classList.add('shiki-fallback');
                }
            }, 0);

            this._pendingPromptBrowserHighlights.push(timeoutId);
        },

        /**
         * Queue async Shiki highlighting for a code block in Prompt Browser.
         * @private
         */
        _queuePromptBrowserHighlight(blockId, code, lang) {
            this._queueHighlight(blockId, code, lang);
        },

        /**
         * Queue async XML highlighting for Shiki (Story 23.6).
         * @private
         */
        _queueXmlHighlight(blockId, content) {
            this._queueHighlight(blockId, content, 'xml');
        },

        /**
         * Cancel all pending Prompt Browser highlights (call on modal close).
         * @private
         */
        _cancelPendingPromptBrowserHighlights() {
            for (const timeoutId of this._pendingPromptBrowserHighlights) {
                clearTimeout(timeoutId);
            }
            this._pendingPromptBrowserHighlights = [];
        },

        // ==========================================
        // Story 23.7 - Variables Panel
        // ==========================================

        /**
         * Toggle variables view between rendered and raw XML (Story 23.7 AC1).
         */
        toggleVariablesView() {
            this.variablesView = this.variablesView === 'rendered' ? 'raw' : 'rendered';
        },

        /**
         * Detect project root from file path variables (Story 23.7 AC2, AC3).
         * Finds common prefix among absolute paths or uses project markers as fallback.
         *
         * Story 24.1: Delegates to shared contentBrowserUtils.
         *
         * @param {Array} variables - Array of {name, value} objects
         * @returns {string|null} Project root path or null
         */
        _detectProjectRoot(variables) {
            // Delegate to shared utility (Story 24.1)
            return window.contentBrowserUtils.detectProjectRoot(variables);
        },

        /**
         * Shorten an absolute path relative to project root (Story 23.7 AC2, AC3).
         *
         * Story 24.1: Delegates to shared contentBrowserUtils.
         *
         * @param {string} fullPath - Full absolute path
         * @param {string|null} projectRoot - Detected project root
         * @returns {string} Shortened path (relative) or original path
         */
        shortenPath(fullPath, projectRoot) {
            // Delegate to shared utility (Story 24.1)
            return window.contentBrowserUtils.shortenPath(fullPath, projectRoot);
        },

        /**
         * Categorize variables by BMAD workflow categories (Story 23.7 AC2).
         * Categories: Story Context, Input Files, Output Paths, Project Settings, Other
         *
         * @param {Array} variables - Array of {name, value, fileId} objects
         * @param {string|null} projectRoot - Detected project root for path shortening
         * @returns {object} Object with category names as keys, arrays of vars as values
         */
        _categorizeVariables(variables, projectRoot) {
            const categories = {
                'Story Context': [],
                'Input Files': [],
                'Output Paths': [],
                'Project Settings': [],
                'Other': []
            };

            // Define patterns for each category (applied in priority order)
            const storyContextNames = ['epic_num', 'story_num', 'story_key', 'story_id', 'story_title', 'story_dir'];
            const projectSettingsNames = ['project_name', 'user_name', 'author', 'date', 'timestamp', 'communication_language', 'document_output_language', 'user_skill_level', 'name', 'description'];
            const outputPathNames = ['output_folder', 'default_output_file', 'implementation_artifacts', 'planning_artifacts', 'project_knowledge'];

            for (const v of variables) {
                // Apply shortened path to value for display
                const shortenedValue = this.shortenPath(v.value, projectRoot);
                const displayVar = {
                    ...v,
                    displayValue: shortenedValue,
                    fullValue: v.value  // Keep original for tooltip
                };

                // Check patterns in priority order
                if (storyContextNames.includes(v.name)) {
                    categories['Story Context'].push(displayVar);
                } else if (v.name.endsWith('_file')) {
                    categories['Input Files'].push(displayVar);
                } else if (v.name.endsWith('_artifacts') || outputPathNames.includes(v.name)) {
                    categories['Output Paths'].push(displayVar);
                } else if (projectSettingsNames.includes(v.name)) {
                    categories['Project Settings'].push(displayVar);
                } else if (v.name === 'project_context') {
                    // project_context is an input file reference
                    categories['Input Files'].push(displayVar);
                } else {
                    categories['Other'].push(displayVar);
                }
            }

            return categories;
        },

        /**
         * Get category order for rendering (Story 23.7 AC2).
         * Returns array of category names that have variables.
         *
         * @returns {Array<string>} Ordered category names with content
         */
        getVariableCategoryOrder() {
            const order = ['Story Context', 'Input Files', 'Output Paths', 'Project Settings', 'Other'];
            const categorized = this.promptBrowser.parsed?.categorizedVariables || {};

            return order.filter(cat => categorized[cat] && categorized[cat].length > 0);
        },

        /**
         * Get variables for a specific category (Story 23.7 AC2).
         *
         * @param {string} categoryName - Category name
         * @returns {Array} Variables in that category
         */
        getVariablesForCategory(categoryName) {
            const categorized = this.promptBrowser.parsed?.categorizedVariables || {};
            return categorized[categoryName] || [];
        },

        /**
         * Get raw XML for variables section (Story 23.7 AC4).
         * Uses stored raw XML if available, otherwise reconstructs from parsed data.
         *
         * @returns {string} Raw XML string
         */
        getVariablesRawXml() {
            // Prefer stored raw XML (preserves original formatting)
            if (this.promptBrowser.parsed?.rawVariablesXml) {
                return this.promptBrowser.parsed.rawVariablesXml;
            }

            // Fallback: reconstruct from parsed data
            const vars = this.promptBrowser.parsed?.variables || [];
            if (vars.length === 0) return '<variables></variables>';

            const escapeXml = (str) => {
                if (!str) return '';
                return str
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&apos;');
            };

            let xml = '<variables>\n';
            for (const v of vars) {
                const fileIdAttr = v.fileId ? ` file_id="${escapeXml(v.fileId)}"` : '';
                xml += `<var name="${escapeXml(v.name)}"${fileIdAttr}>${escapeXml(v.value)}</var>\n`;
            }
            xml += '</variables>';
            return xml;
        },

        /**
         * Check if a variable value is a path that was shortened (Story 23.7 AC3).
         *
         * @param {object} variable - Variable object with displayValue and fullValue
         * @returns {boolean} True if path was shortened
         */
        isPathShortened(variable) {
            return variable.displayValue !== variable.fullValue &&
                   variable.fullValue &&
                   variable.fullValue.startsWith('/');
        },

        // ==========================================
        // Story 23.8 - Validator Identity Mapping
        // ==========================================

        /**
         * Load validator mapping from API for current epic/story (Story 23.8 AC3, AC5).
         * Fetches both validation and code-review mappings and merges them.
         *
         * @param {string} epic - Epic number
         * @param {string} story - Story number
         */
        async loadValidatorMapping(epic, story) {
            // Skip if already loaded for this epic/story
            if (this._validatorMappingLoaded &&
                this._validatorMappingEpic === epic &&
                this._validatorMappingStory === story) {
                return;
            }

            this._validatorMapping = {};
            this._validatorMappingLoaded = false;
            this._validatorMappingEpic = epic;
            this._validatorMappingStory = story;

            // Try loading both validation and code-review mappings
            const types = ['validation', 'code-review'];
            for (const type of types) {
                try {
                    const response = await fetch(`/api/mapping/${type}/${epic}/${story}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.validators) {
                            // Merge into mapping (later types override earlier)
                            Object.assign(this._validatorMapping, data.validators);
                        }
                    }
                } catch (err) {
                    console.warn(`Failed to load ${type} mapping:`, err);
                    // Graceful fallback - keep original identifiers (AC4)
                }
            }

            this._validatorMappingLoaded = true;
        },

        /**
         * Replace validator IDs with actual model names in text (Story 23.8 AC1, AC2).
         * Handles both [Validator X]/[Reviewer X] formats (file paths) and prose text.
         *
         * @param {string} text - Text containing validator IDs
         * @returns {string} Text with model names
         */
        replaceValidatorIds(text) {
            if (!text || !this._validatorMappingLoaded) return text;

            const mapping = this._validatorMapping;
            if (!mapping || Object.keys(mapping).length === 0) return text;

            let result = text;

            // Replace [Validator X] and [Reviewer X] format (file paths)
            result = result.replace(/\[(Validator|Reviewer)\s+([A-Z])\]/gi, (match, type, letter) => {
                const key = `Validator ${letter.toUpperCase()}`;
                return mapping[key] ? `[${mapping[key]}]` : match;
            });

            // Replace "Validator X" and "Reviewer X" format (prose text in reports)
            // Use word boundary to avoid partial matches
            // Supports: Validator A, Reviewer B, Validators C, Reviewers D (singular/plural)
            result = result.replace(/\b(Validator|Reviewer)s?\s+([A-Z])\b/gi, (match, type, letter) => {
                const key = `Validator ${letter.toUpperCase()}`;
                return mapping[key] || match;
            });

            return result;
        },

        /**
         * Get display-ready file path with validator IDs replaced (Story 23.8 AC2).
         * Wraps getFilename() with validator ID replacement.
         *
         * @param {string} path - Full file path
         * @returns {string} Filename with model names
         */
        getFilenameWithMapping(path) {
            const filename = this.getFilename(path);
            return this.replaceValidatorIds(filename);
        },

        /**
         * Get display-ready full path with validator IDs replaced (Story 23.8 AC2).
         *
         * @param {string} path - Full file path
         * @returns {string} Path with model names
         */
        getPathWithMapping(path) {
            return this.replaceValidatorIds(path);
        },

        /**
         * Extract epic and story from prompt browser title (Story 23.8).
         * Title format: "Epic X Story Y - Phase Name" or similar
         *
         * @returns {{ epic: string, story: string } | null}
         */
        _extractEpicStoryFromTitle() {
            const title = this.promptBrowser.title || '';

            // Try pattern: "Epic X Story Y"
            const match = title.match(/Epic\s+(\d+)\s+Story\s+(\d+)/i);
            if (match) {
                return { epic: match[1], story: match[2] };
            }

            // Try pattern from variables if available
            const vars = this.promptBrowser.parsed?.variables || [];
            const epicVar = vars.find(v => v.name === 'epic_num');
            const storyVar = vars.find(v => v.name === 'story_num');

            if (epicVar && storyVar) {
                return { epic: epicVar.value, story: storyVar.value };
            }

            return null;
        },

        /**
         * Initialize validator mapping after parsing (Story 23.8).
         * Called from openPromptBrowser after XML parsing completes.
         */
        _initValidatorMapping() {
            const epicStory = this._extractEpicStoryFromTitle();
            if (epicStory) {
                // Fire and forget - mapping loads async
                this.loadValidatorMapping(epicStory.epic, epicStory.story);
            }
        }
    };
};
