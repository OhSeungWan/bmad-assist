/**
 * Shiki Syntax Highlighter Utility (ESM Module)
 *
 * Provides VSCode-style syntax highlighting for code blocks using Shiki.
 * Uses dynamic ESM imports from esm.sh CDN - no local vendoring required.
 *
 * Story 23.3 - Shiki Local Integration (base implementation)
 * Story 23.4 - Shiki Caching & Lazy Load (lazy loading, caching, pre-warming)
 * Version: shiki@3.21.0 (pinned 2026-01-18)
 *
 * Usage:
 *   await window.shikiHighlighter.initShiki();
 *   const html = await window.shikiHighlighter.highlightCode('const x = 1;', 'javascript');
 *   await window.shikiHighlighter.highlightCodeBlocks(containerElement);
 */

// Constants
const SHIKI_VERSION = '3.21.0';
const SHIKI_CDN_BASE = `https://esm.sh/shiki@${SHIKI_VERSION}`;
const LOCALSTORAGE_LOADED_LANGS_KEY = 'shiki:loaded-languages';
const LOCALSTORAGE_THEME_KEY = 'shiki:theme-preference';
const DEFAULT_THEME = 'dark-plus';
const MAX_PREWARM_LANGUAGES = 5;

// Starter languages loaded at init time
const STARTER_LANGUAGES = [
    'javascript',
    'typescript',
    'python',
    'yaml',
    'json',
    'xml',
    'markdown',
    'css',
    'bash',
    'shell'
];

// Extended language aliases (Story 23.4 - Task 5)
const langAliases = {
    // Existing (Story 23.3)
    'sh': 'bash',
    'zsh': 'bash',
    'js': 'javascript',
    'ts': 'typescript',
    'py': 'python',
    'yml': 'yaml',
    'md': 'markdown',

    // New additions (Story 23.4)
    'rb': 'ruby',
    'rs': 'rust',
    'cpp': 'cpp',
    'c++': 'cpp',
    'cs': 'csharp',
    'c#': 'csharp',
    'kt': 'kotlin',
    'kts': 'kotlin',
    'dockerfile': 'docker',
    'makefile': 'make',
    'tf': 'terraform',
    'hcl': 'terraform',
    'gql': 'graphql',
    'sol': 'solidity',
    'hs': 'haskell',
    'ex': 'elixir',
    'exs': 'elixir',
    'erl': 'erlang',
    'clj': 'clojure',
    'ps1': 'powershell',
    'psm1': 'powershell'
};

// Singleton highlighter instance
let _highlighter = null;

// Track initialization state
window._shikiReady = false;

// Track pending language load promises to prevent duplicate requests (AC6)
const _pendingLoads = new Map();

/**
 * Get escapeHtml from utils.js (centralized, Story 23.3 - DRY fix).
 * Falls back to inline implementation if utils.js not loaded yet.
 *
 * @param {string} text - Raw text to escape
 * @returns {string} HTML-escaped text
 */
function escapeHtml(text) {
    // Use centralized version from utils.js if available
    if (window.dashboardUtils && window.dashboardUtils.escapeHtml) {
        return window.dashboardUtils.escapeHtml(text);
    }
    // Fallback for module load order (ESM loads async)
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ==========================================
// localStorage Helpers (Story 23.4 - Task 2, 3)
// ==========================================

/**
 * Get loaded languages from localStorage cache.
 * @returns {string[]} Array of language names, empty array on error
 */
function _getLoadedLanguagesCache() {
    try {
        const data = localStorage.getItem(LOCALSTORAGE_LOADED_LANGS_KEY);
        if (!data) return [];
        const parsed = JSON.parse(data);
        return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
        // SecurityError (localStorage disabled) or parse error - ignore silently
        return [];
    }
}

/**
 * Save loaded languages to localStorage cache.
 * @param {string[]} langs - Array of language names to cache
 */
function _saveLoadedLanguages(langs) {
    try {
        localStorage.setItem(LOCALSTORAGE_LOADED_LANGS_KEY, JSON.stringify(langs));
    } catch (err) {
        if (err.name === 'QuotaExceededError') {
            console.warn('localStorage quota exceeded, clearing shiki cache');
            try {
                localStorage.removeItem(LOCALSTORAGE_LOADED_LANGS_KEY);
                localStorage.setItem(LOCALSTORAGE_LOADED_LANGS_KEY, JSON.stringify(langs));
            } catch (retryErr) {
                console.warn('Failed to save languages even after cache clear');
            }
        }
        // SecurityError: localStorage disabled - ignore silently
    }
}

/**
 * Add a language to the localStorage cache.
 * Maintains MRU (Most Recently Used) order - moves existing languages to front.
 * @param {string} lang - Language name to add
 */
function _addToLanguageCache(lang) {
    let cached = _getLoadedLanguagesCache();
    // Remove existing entry to move to front (proper MRU ordering)
    cached = cached.filter(l => l !== lang);
    // Add to front (most recently used first)
    cached.unshift(lang);
    // Keep only last 50 languages
    if (cached.length > 50) cached.pop();
    _saveLoadedLanguages(cached);
}

/**
 * Get theme preference from localStorage.
 * @returns {string} Theme name (default: 'dark-plus')
 */
function getThemePreference() {
    try {
        return localStorage.getItem(LOCALSTORAGE_THEME_KEY) || DEFAULT_THEME;
    } catch (err) {
        return DEFAULT_THEME;
    }
}

/**
 * Set theme preference in localStorage.
 * @param {string} theme - Theme name to save
 */
function setThemePreference(theme) {
    try {
        localStorage.setItem(LOCALSTORAGE_THEME_KEY, theme);
    } catch (err) {
        // Ignore localStorage errors
    }
}

// ==========================================
// Language Loading (Story 23.4 - Task 1)
// ==========================================

/**
 * Load a language grammar if not already loaded.
 * Implements request deduplication - concurrent requests for same language share one fetch.
 *
 * @param {string} lang - Language identifier
 * @returns {Promise<boolean>} True if language is now available, false on error
 */
async function loadLanguageIfNeeded(lang) {
    if (!_highlighter) return false;

    // Check if already loaded
    const loadedLangs = _highlighter.getLoadedLanguages();
    if (loadedLangs.includes(lang)) {
        return true;
    }

    // Return cached promise if already loading (prevents duplicate requests - AC6)
    if (_pendingLoads.has(lang)) {
        return _pendingLoads.get(lang);
    }

    // Create and cache load promise
    const loadPromise = (async () => {
        const startTime = performance.now();
        try {
            // Dynamic import from CDN
            await _highlighter.loadLanguage(
                import(`${SHIKI_CDN_BASE}/langs/${lang}.mjs`)
            );
            const duration = performance.now() - startTime;
            console.log(`Loaded language: ${lang} (${duration.toFixed(0)}ms)`);

            // Cache the successfully loaded language
            _addToLanguageCache(lang);

            return true;
        } catch (err) {
            console.warn(`Failed to load language "${lang}":`, err);
            return false;
        } finally {
            // Clean up pending promise
            _pendingLoads.delete(lang);
        }
    })();

    _pendingLoads.set(lang, loadPromise);
    return loadPromise;
}

/**
 * Pre-warm frequently used languages from cache.
 * Runs in background using requestIdleCallback/setTimeout.
 * @private
 */
function _prewarmCachedLanguages() {
    const cached = _getLoadedLanguagesCache();
    if (cached.length === 0) return;

    // Only pre-warm top N most recent languages
    const toPrewarm = cached.slice(0, MAX_PREWARM_LANGUAGES);

    // Use requestIdleCallback if available, otherwise setTimeout
    const scheduleIdle = window.requestIdleCallback || ((fn) => setTimeout(fn, 0));

    scheduleIdle(async () => {
        // Filter out already loaded languages
        const loadedLangs = _highlighter?.getLoadedLanguages() || [];
        const needsLoading = toPrewarm.filter(lang => !loadedLangs.includes(lang));

        if (needsLoading.length === 0) return;

        console.log(`Pre-warming languages from cache: ${needsLoading.join(', ')}`);

        // Load all in parallel, don't block on failures
        const results = await Promise.allSettled(
            needsLoading.map(lang => loadLanguageIfNeeded(lang))
        );

        const loaded = results.filter(r => r.status === 'fulfilled' && r.value).length;
        console.log(`Pre-warmed ${loaded}/${needsLoading.length} languages`);
    });
}

// ==========================================
// Main API
// ==========================================

/**
 * Initialize Shiki highlighter singleton.
 * Loads Shiki from CDN and creates highlighter with dark-plus theme.
 *
 * @returns {Promise<Object|null>} Highlighter instance or null if failed
 */
async function initShiki() {
    // Return cached instance if already initialized
    if (_highlighter) {
        return _highlighter;
    }

    try {
        // Dynamic import from esm.sh CDN (pinned version)
        const { createHighlighter } = await import(`${SHIKI_CDN_BASE}`);

        // Get theme from localStorage or use default
        const theme = getThemePreference();

        _highlighter = await createHighlighter({
            themes: [theme],
            langs: STARTER_LANGUAGES
        });

        window._shikiReady = true;
        console.log('Shiki highlighter initialized successfully');

        // Pre-warm frequently used languages from cache (Story 23.4 - Task 4)
        _prewarmCachedLanguages();

        return _highlighter;
    } catch (err) {
        console.warn('Shiki initialization failed:', err);
        window._shikiReady = false;
        return null;
    }
}

/**
 * Highlight code with Shiki.
 * Returns highlighted HTML or escaped plain text if Shiki unavailable.
 * Loads language grammar on-demand if not in starter set (Story 23.4).
 *
 * @param {string} code - Source code to highlight
 * @param {string} lang - Language identifier (e.g., 'javascript', 'python')
 * @param {Object} options - Optional parameters
 * @param {Function} options.onLoadingStart - Callback when language load starts
 * @param {Function} options.onLoadingEnd - Callback when language load ends
 * @returns {Promise<string>} Highlighted HTML string
 */
async function highlightCode(code, lang, options = {}) {
    // Normalize language identifier
    const normalizedLang = (lang || 'text').toLowerCase().trim();

    // Map common aliases
    const resolvedLang = langAliases[normalizedLang] || normalizedLang;

    // Fallback if Shiki not ready
    if (!window._shikiReady || !_highlighter) {
        return `<pre class="shiki-fallback"><code>${escapeHtml(code)}</code></pre>`;
    }

    try {
        // Check if language is already loaded
        let loadedLangs = _highlighter.getLoadedLanguages();
        let langSupported = loadedLangs.includes(resolvedLang);

        // If not loaded, try to load it on-demand (Story 23.4 - AC1)
        if (!langSupported) {
            // Signal loading state
            if (options.onLoadingStart) options.onLoadingStart();

            const loaded = await loadLanguageIfNeeded(resolvedLang);

            if (options.onLoadingEnd) options.onLoadingEnd();

            if (loaded) {
                langSupported = true;
            } else {
                // Language not available - return unsupported styling
                return `<pre class="shiki shiki-unsupported"><code>${escapeHtml(code)}</code></pre>`;
            }
        }

        // Get theme from localStorage
        const theme = getThemePreference();

        // Highlight with Shiki
        const html = _highlighter.codeToHtml(code, {
            lang: resolvedLang,
            theme: theme
        });

        return html;
    } catch (err) {
        console.warn(`Shiki highlight failed for language "${resolvedLang}":`, err);
        return `<pre class="shiki-fallback"><code>${escapeHtml(code)}</code></pre>`;
    }
}

/**
 * Highlight all code blocks within a container element.
 * Finds all <pre><code> elements and applies Shiki highlighting.
 *
 * @param {HTMLElement} container - Container element to search for code blocks
 * @returns {Promise<void>}
 */
async function highlightCodeBlocks(container) {
    if (!container) return;

    // Skip if Shiki not ready
    if (!window._shikiReady || !_highlighter) {
        console.warn('Shiki not ready, skipping code block highlighting');
        return;
    }

    // Find all code blocks
    const codeBlocks = container.querySelectorAll('pre > code');

    for (const codeEl of codeBlocks) {
        // Skip already highlighted blocks
        if (codeEl.closest('.shiki')) continue;

        // Get language from class (e.g., "language-python")
        const langClass = Array.from(codeEl.classList).find(c => c.startsWith('language-'));
        const lang = langClass ? langClass.replace('language-', '') : 'text';

        // Get code content
        const code = codeEl.textContent || '';

        // Get parent pre element
        const preEl = codeEl.parentElement;
        if (!preEl) continue;

        try {
            // Add loading state class (Story 23.4 - AC7)
            preEl.classList.add('shiki-loading');

            // Generate highlighted HTML
            const html = await highlightCode(code, lang);

            // Remove loading state
            preEl.classList.remove('shiki-loading');

            // Create temp container to parse HTML
            const temp = document.createElement('div');
            temp.innerHTML = html;

            // Replace original pre element with highlighted version
            const newPre = temp.firstElementChild;
            if (newPre) {
                preEl.parentElement?.replaceChild(newPre, preEl);
            }
        } catch (err) {
            console.warn('Failed to highlight code block:', err);
            preEl.classList.remove('shiki-loading');
            preEl.classList.add('shiki-fallback');
        }
    }
}

/**
 * Check if a language is currently loaded.
 * @param {string} lang - Language identifier
 * @returns {boolean} True if language is loaded
 */
function isLanguageLoaded(lang) {
    if (!_highlighter) return false;
    const normalizedLang = (lang || '').toLowerCase().trim();
    const resolvedLang = langAliases[normalizedLang] || normalizedLang;
    return _highlighter.getLoadedLanguages().includes(resolvedLang);
}

/**
 * Get list of currently loaded languages.
 * @returns {string[]} Array of loaded language identifiers
 */
function getLoadedLanguages() {
    if (!_highlighter) return [];
    return _highlighter.getLoadedLanguages();
}

// Export API as window global for use by non-module scripts
window.shikiHighlighter = {
    initShiki,
    highlightCode,
    highlightCodeBlocks,
    loadLanguageIfNeeded,
    isLanguageLoaded,
    getLoadedLanguages,
    getThemePreference,
    setThemePreference
};

// Auto-initialize on module load (lazy - only creates the promise, doesn't block)
initShiki().catch(err => {
    console.warn('Shiki auto-initialization failed:', err);
});
