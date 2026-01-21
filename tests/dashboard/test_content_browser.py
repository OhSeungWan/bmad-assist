"""Tests for content-browser.js shared component (Story 24.1).

This file tests the shared browser infrastructure for dashboard content browsers:
- Path utilities (shortenPath, isExternalPath, formatPathWithExternal, detectProjectRoot)
- Component API (createBrowserState, toggleView, copyRawContent)
- Global exports (window.contentBrowserUtils, window.contentBrowserComponent)
"""
from pathlib import Path

import pytest


@pytest.fixture
def component_content() -> str:
    """Read content-browser.js content."""
    component_path = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/static-src/js/components/content-browser.js"
    )
    return component_path.read_text(encoding="utf-8")


class TestComponentStructure:
    """Tests for content-browser.js component structure (Story 24.1 AC6)."""

    def test_exports_content_browser_utils(self, component_content: str) -> None:
        """Verify window.contentBrowserUtils is exported."""
        assert "window.contentBrowserUtils = {" in component_content

    def test_exports_content_browser_component(self, component_content: str) -> None:
        """Verify window.contentBrowserComponent is exported."""
        assert "window.contentBrowserComponent = function()" in component_content

    def test_utils_exports_shorten_path(self, component_content: str) -> None:
        """Verify shortenPath is exported in utils."""
        assert "shortenPath," in component_content or "shortenPath" in component_content

    def test_utils_exports_is_external_path(self, component_content: str) -> None:
        """Verify isExternalPath is exported in utils."""
        assert "isExternalPath," in component_content or "isExternalPath" in component_content

    def test_utils_exports_format_path_with_external(self, component_content: str) -> None:
        """Verify formatPathWithExternal is exported in utils."""
        assert "formatPathWithExternal," in component_content or "formatPathWithExternal" in component_content

    def test_utils_exports_detect_project_root(self, component_content: str) -> None:
        """Verify detectProjectRoot is exported in utils."""
        assert "detectProjectRoot" in component_content


class TestPathShortening:
    """Tests for shortenPath function (Story 24.1 AC3)."""

    def test_function_exists(self, component_content: str) -> None:
        """Verify shortenPath function exists."""
        assert "function shortenPath(fullPath, projectRoot)" in component_content

    def test_handles_empty_path(self, component_content: str) -> None:
        """Verify function handles empty path."""
        assert "if (!fullPath) return ''" in component_content

    def test_checks_directory_boundary(self, component_content: str) -> None:
        """Verify function checks directory boundary correctly."""
        # Should check both equality and starts-with for proper boundary detection
        assert "fullPath === projectRoot" in component_content
        assert "fullPath.startsWith(projectRoot + '/')" in component_content

    def test_uses_project_markers(self, component_content: str) -> None:
        """Verify function uses project markers as fallback."""
        assert "'/docs/'" in component_content
        assert "'/src/'" in component_content
        assert "'/_bmad-output/'" in component_content
        assert "'/tests/'" in component_content


class TestExternalPathDetection:
    """Tests for isExternalPath and formatPathWithExternal (Story 24.1 AC4)."""

    def test_is_external_path_function_exists(self, component_content: str) -> None:
        """Verify isExternalPath function exists."""
        assert "function isExternalPath(fullPath, projectRoot)" in component_content

    def test_is_external_checks_null(self, component_content: str) -> None:
        """Verify isExternalPath handles null/empty inputs."""
        assert "if (!fullPath || !projectRoot) return false" in component_content

    def test_is_external_checks_directory_boundary(self, component_content: str) -> None:
        """Verify isExternalPath checks directory boundary."""
        assert "fullPath.startsWith(projectRoot + '/')" in component_content

    def test_format_path_with_external_exists(self, component_content: str) -> None:
        """Verify formatPathWithExternal function exists."""
        assert "function formatPathWithExternal(fullPath, projectRoot)" in component_content

    def test_format_path_returns_object(self, component_content: str) -> None:
        """Verify formatPathWithExternal returns proper structure."""
        assert "displayPath" in component_content
        assert "isExternal" in component_content
        assert "externalBase" in component_content

    def test_format_path_extracts_base_directory(self, component_content: str) -> None:
        """Verify formatPathWithExternal extracts base directory for tooltip."""
        assert "lastIndexOf('/')" in component_content
        assert "externalBase" in component_content


class TestProjectRootDetection:
    """Tests for detectProjectRoot function (Story 24.1)."""

    def test_function_exists(self, component_content: str) -> None:
        """Verify detectProjectRoot function exists."""
        assert "function detectProjectRoot(variables)" in component_content

    def test_handles_empty_variables(self, component_content: str) -> None:
        """Verify function handles empty variables array."""
        assert "if (!variables || variables.length === 0) return null" in component_content

    def test_checks_file_suffix(self, component_content: str) -> None:
        """Verify function checks for *_file variable names."""
        assert "endsWith('_file')" in component_content

    def test_checks_known_path_vars(self, component_content: str) -> None:
        """Verify function checks known path variable names."""
        assert "'output_folder'" in component_content
        assert "'implementation_artifacts'" in component_content
        assert "'planning_artifacts'" in component_content
        assert "'project_knowledge'" in component_content
        assert "'story_dir'" in component_content


class TestBrowserState:
    """Tests for createBrowserState method (Story 24.1 AC1)."""

    def test_create_browser_state_exists(self, component_content: str) -> None:
        """Verify createBrowserState method exists."""
        assert "createBrowserState()" in component_content

    def test_defaults_to_rendered_view(self, component_content: str) -> None:
        """Verify default view is 'rendered' (AC1)."""
        assert "view: 'rendered'" in component_content

    def test_includes_project_root(self, component_content: str) -> None:
        """Verify state includes projectRoot."""
        assert "projectRoot: null" in component_content


class TestToggleView:
    """Tests for toggleView method (Story 24.1 AC1)."""

    def test_toggle_view_exists(self, component_content: str) -> None:
        """Verify toggleView method exists."""
        assert "toggleView(browser)" in component_content

    def test_toggle_switches_state(self, component_content: str) -> None:
        """Verify toggleView switches between rendered and raw."""
        assert "browser.view === 'rendered' ? 'raw' : 'rendered'" in component_content


class TestCopyRawContent:
    """Tests for copyRawContent method (Story 24.1 AC2)."""

    def test_copy_raw_content_exists(self, component_content: str) -> None:
        """Verify copyRawContent method exists."""
        assert "copyRawContent(content, toastCallback)" in component_content

    def test_checks_clipboard_availability(self, component_content: str) -> None:
        """Verify method checks for clipboard API."""
        assert "navigator.clipboard" in component_content
        assert "Clipboard not available" in component_content

    def test_shows_success_toast(self, component_content: str) -> None:
        """Verify method shows success toast."""
        assert "Copied to clipboard!" in component_content

    def test_handles_clipboard_error(self, component_content: str) -> None:
        """Verify method handles clipboard errors gracefully."""
        assert "Failed to copy" in component_content

    def test_uses_toast_callback(self, component_content: str) -> None:
        """Verify method uses callback for toast messages."""
        assert "toastCallback?." in component_content


class TestDocumentation:
    """Tests for component documentation."""

    def test_has_story_reference(self, component_content: str) -> None:
        """Verify component has Story 24.1 reference."""
        assert "Story 24.1" in component_content

    def test_documents_utils_api(self, component_content: str) -> None:
        """Verify utils API is documented."""
        assert "window.contentBrowserUtils" in component_content

    def test_documents_component_api(self, component_content: str) -> None:
        """Verify component API is documented."""
        assert "window.contentBrowserComponent" in component_content


class TestAlpineIntegration:
    """Tests for Alpine.js integration in alpine-init.js (Story 24.1 AC6)."""

    @pytest.fixture
    def alpine_init_content(self) -> str:
        """Read alpine-init.js content."""
        init_path = (
            Path(__file__).parent.parent.parent
            / "src/bmad_assist/dashboard/static-src/js/alpine-init.js"
        )
        return init_path.read_text(encoding="utf-8")

    def test_content_browser_component_loaded(self, alpine_init_content: str) -> None:
        """Verify contentBrowserComponent is loaded in alpine-init.js."""
        assert "window.contentBrowserComponent" in alpine_init_content

    def test_content_browser_spread_in_dashboard(self, alpine_init_content: str) -> None:
        """Verify contentBrowser is spread into dashboard object."""
        assert "...contentBrowser," in alpine_init_content


class TestScriptLoading:
    """Tests for script loading order in 11-tail.html."""

    @pytest.fixture
    def tail_html_content(self) -> str:
        """Read 11-tail.html content."""
        tail_path = (
            Path(__file__).parent.parent.parent
            / "src/bmad_assist/dashboard/static-src/11-tail.html"
        )
        return tail_path.read_text(encoding="utf-8")

    def test_content_browser_script_included(self, tail_html_content: str) -> None:
        """Verify content-browser.js script is included."""
        assert 'src="/js/components/content-browser.js"' in tail_html_content

    def test_content_browser_loads_before_alpine_init(self, tail_html_content: str) -> None:
        """Verify content-browser.js loads before alpine-init.js.

        content-browser.js must load before alpine-init.js because:
        1. alpine-init.js references window.contentBrowserComponent
        2. The comment says 'Component scripts (load before alpine-init.js orchestrator)'
        """
        # Find script tag positions (not just filename mentions)
        content_browser_script = tail_html_content.find('src="/js/components/content-browser.js"')
        alpine_init_script = tail_html_content.find('src="/js/alpine-init.js"')
        assert content_browser_script < alpine_init_script, (
            f"content-browser.js must load before alpine-init.js, "
            f"but positions are {content_browser_script} vs {alpine_init_script}"
        )

    def test_content_browser_loads_after_prompt_browser(self, tail_html_content: str) -> None:
        """Verify content-browser.js loads after prompt-browser.js (dependency order)."""
        prompt_browser_pos = tail_html_content.find("prompt-browser.js")
        content_browser_pos = tail_html_content.find("content-browser.js")
        assert prompt_browser_pos < content_browser_pos


class TestBuiltOutput:
    """Tests for built static/index.html."""

    @pytest.fixture
    def built_index_content(self) -> str:
        """Read built index.html content."""
        index_path = (
            Path(__file__).parent.parent.parent
            / "src/bmad_assist/dashboard/static/index.html"
        )
        return index_path.read_text(encoding="utf-8")

    def test_content_browser_in_built_output(self, built_index_content: str) -> None:
        """Verify content-browser.js is in built index.html."""
        assert 'src="/js/components/content-browser.js"' in built_index_content
