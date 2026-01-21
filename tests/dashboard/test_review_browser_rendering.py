"""Tests for Review Browser Markdown Rendering (Story 24.9).

This file tests the frontend implementation that enables Raw/Rendered toggle
for validation and code review reports in the contentModal:
- loadReportContent() sets browser state before showing modal
- contentModal already supports browser state from Story 24.5
- All synthesis and individual report buttons use loadReportContent()
"""
from pathlib import Path

import pytest


@pytest.fixture
def context_menu_js_content() -> str:
    """Read context-menu.js content."""
    context_menu_path = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/static-src/js/components/context-menu.js"
    )
    return context_menu_path.read_text(encoding="utf-8")


@pytest.fixture
def modals_html_content() -> str:
    """Read 10-modals.html content."""
    modals_path = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/static-src/10-modals.html"
    )
    return modals_path.read_text(encoding="utf-8")


@pytest.fixture
def tail_html_content() -> str:
    """Read 11-tail.html content."""
    tail_path = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/static-src/11-tail.html"
    )
    return tail_path.read_text(encoding="utf-8")


@pytest.fixture
def content_browser_js_content() -> str:
    """Read content-browser.js content."""
    browser_path = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/static-src/js/components/content-browser.js"
    )
    return browser_path.read_text(encoding="utf-8")


# ==========================================
# Task 1: loadReportContent sets browser state (AC 1-5)
# ==========================================


class TestLoadReportContentBrowserState:
    """Tests for loadReportContent() setting browser state (AC 1-5)."""

    def test_load_report_content_has_story_reference(
        self, context_menu_js_content: str
    ) -> None:
        """Verify loadReportContent has Story 24.9 reference."""
        assert "Story 24.9" in context_menu_js_content

    def test_load_report_content_shows_loading_toast(
        self, context_menu_js_content: str
    ) -> None:
        """Verify loadReportContent shows loading toast at start."""
        # Find loadReportContent function
        func_start = context_menu_js_content.find("async loadReportContent(report)")
        assert func_start != -1, "loadReportContent function not found"

        # Check for loading toast at start of method
        func_content = context_menu_js_content[func_start : func_start + 500]
        assert "showToast('Loading report...')" in func_content

    def test_load_report_content_sets_browser_state(
        self, context_menu_js_content: str
    ) -> None:
        """Verify loadReportContent sets contentModal.browser with defensive check."""
        # Defensive pattern: check if component loaded before calling
        assert "if (window.contentBrowserComponent)" in context_menu_js_content
        assert (
            "this.contentModal.browser = window.contentBrowserComponent().createBrowserState()"
            in context_menu_js_content
        )

    def test_browser_state_set_before_modal_show(
        self, context_menu_js_content: str
    ) -> None:
        """Verify browser state is set BEFORE contentModal.show = true."""
        # Find loadReportContent function - use the end marker (next method)
        func_start = context_menu_js_content.find("async loadReportContent(report)")
        # Function ends at the closing brace before end of file
        func_content = context_menu_js_content[func_start:]

        # Find positions within the function (limited scope)
        browser_state_pos = func_content.find("this.contentModal.browser = window")
        modal_show_pos = func_content.find("this.contentModal.show = true")

        assert browser_state_pos != -1, "Browser state initialization not found"
        assert modal_show_pos != -1, "Modal show not found"
        assert browser_state_pos < modal_show_pos, (
            f"Browser state must be set BEFORE modal show, "
            f"but positions are browser={browser_state_pos} vs show={modal_show_pos}"
        )

    def test_browser_state_comment_explains_order(
        self, context_menu_js_content: str
    ) -> None:
        """Verify code comment explains why browser state must be set first."""
        assert (
            "Must be set BEFORE contentModal.show = true" in context_menu_js_content
        )

    def test_error_handling_comment_present(
        self, context_menu_js_content: str
    ) -> None:
        """Verify comment explaining modal does not open on error."""
        assert (
            "Modal does NOT open on error - show=true is never reached"
            in context_menu_js_content
        )


# ==========================================
# Task 2: contentModal Raw/Rendered toggle support (AC 3)
# ==========================================


class TestContentModalToggleSupport:
    """Tests for contentModal Raw/Rendered toggle from Story 24.5."""

    def test_content_modal_has_view_toggle(self, modals_html_content: str) -> None:
        """Verify contentModal has view toggle buttons."""
        assert 'data-testid="view-toggle"' in modals_html_content
        assert 'data-testid="view-rendered-btn"' in modals_html_content
        assert 'data-testid="view-raw-btn"' in modals_html_content

    def test_toggle_only_shown_when_browser_set(self, modals_html_content: str) -> None:
        """Verify toggle is conditionally shown when browser state exists."""
        assert '<template x-if="contentModal.browser">' in modals_html_content

    def test_rendered_button_sets_view(self, modals_html_content: str) -> None:
        """Verify Rendered button sets view to 'rendered'."""
        assert "contentModal.browser.view = 'rendered'" in modals_html_content

    def test_raw_button_sets_view(self, modals_html_content: str) -> None:
        """Verify Raw button sets view to 'raw'."""
        assert "contentModal.browser.view = 'raw'" in modals_html_content

    def test_copy_button_uses_raw_content(self, modals_html_content: str) -> None:
        """Verify copy button copies raw content when browser state exists."""
        assert (
            "contentModal.browser ? window.contentBrowserComponent().copyRawContent"
            in modals_html_content
        )

    def test_copy_button_has_tooltip(self, modals_html_content: str) -> None:
        """Verify copy button has 'Copies raw content' tooltip when browser state set."""
        assert (
            ":title=\"contentModal.browser ? 'Copies raw content'" in modals_html_content
        )


# ==========================================
# Task 3: Synthesis buttons use loadReportContent (AC 1, 2)
# ==========================================


class TestSynthesisButtonsUseLoadReportContent:
    """Tests for synthesis report buttons using loadReportContent pattern."""

    def test_validation_synthesis_uses_load_report_content(
        self, tail_html_content: str
    ) -> None:
        """Verify validation synthesis button calls loadReportContent."""
        # Find validation synthesis button
        assert 'data-testid="validation-synthesis"' in tail_html_content
        # Check it uses loadReportContent
        assert (
            "@click=\"loadReportContent(reportModal.validation.synthesis)\""
            in tail_html_content
        )

    def test_code_review_synthesis_uses_load_report_content(
        self, tail_html_content: str
    ) -> None:
        """Verify code review synthesis button calls loadReportContent."""
        # Find code review synthesis button
        assert 'data-testid="code-review-synthesis"' in tail_html_content
        # Check it uses loadReportContent
        assert (
            "@click=\"loadReportContent(reportModal.code_review.synthesis)\""
            in tail_html_content
        )

    def test_individual_validation_reports_use_load_report_content(
        self, tail_html_content: str
    ) -> None:
        """Verify individual validation report buttons call loadReportContent."""
        assert 'data-testid="validation-report-item"' in tail_html_content
        # Check the template uses loadReportContent
        assert "@click=\"loadReportContent(report)\"" in tail_html_content

    def test_individual_code_review_reports_use_load_report_content(
        self, tail_html_content: str
    ) -> None:
        """Verify individual code review report buttons call loadReportContent."""
        assert 'data-testid="code-review-report-item"' in tail_html_content


# ==========================================
# Task 4: Content browser createBrowserState (AC 3)
# ==========================================


class TestContentBrowserState:
    """Tests for content browser createBrowserState utility."""

    def test_create_browser_state_exists(
        self, content_browser_js_content: str
    ) -> None:
        """Verify createBrowserState method exists."""
        assert "createBrowserState()" in content_browser_js_content

    def test_create_browser_state_defaults_to_rendered(
        self, content_browser_js_content: str
    ) -> None:
        """Verify createBrowserState defaults to 'rendered' view."""
        assert "view: 'rendered'" in content_browser_js_content

    def test_copy_raw_content_method_exists(
        self, content_browser_js_content: str
    ) -> None:
        """Verify copyRawContent method exists."""
        assert "copyRawContent(content, toastCallback)" in content_browser_js_content


# ==========================================
# Content rendering based on browser view (AC 1, 2)
# ==========================================


class TestContentRendering:
    """Tests for content rendering based on browser.view mode."""

    def test_browser_controlled_content_template_exists(
        self, tail_html_content: str
    ) -> None:
        """Verify browser-controlled content template exists."""
        # This is in 11-tail.html at the start
        assert (
            "<template x-if=\"contentModal.type === 'markdown' && contentModal.browser\">"
            in tail_html_content
        )

    def test_rendered_mode_uses_format_markdown(self, tail_html_content: str) -> None:
        """Verify rendered mode uses formatMarkdownContent."""
        # Check for rendered view with format markdown
        assert "contentModal.browser.view === 'rendered'" in tail_html_content
        assert 'x-html="formatMarkdownContent(contentModal.content)"' in tail_html_content

    def test_raw_mode_shows_plain_text(self, tail_html_content: str) -> None:
        """Verify raw mode shows plain text in monospace."""
        assert "contentModal.browser.view === 'raw'" in tail_html_content
        assert 'whitespace-pre-wrap font-mono' in tail_html_content


# ==========================================
# Error handling (AC 6)
# ==========================================


class TestErrorHandling:
    """Tests for error handling in loadReportContent."""

    def test_error_shows_toast(self, context_menu_js_content: str) -> None:
        """Verify errors show toast with error message and fallback."""
        # Check for error handling in catch block with network error fallback
        assert "this.showToast(`Failed to load report: ${err.message || 'Network error'}`)" in context_menu_js_content

    def test_error_logs_to_console(self, context_menu_js_content: str) -> None:
        """Verify errors are logged to console."""
        assert "console.error('Failed to load report content:', err)" in context_menu_js_content


# ==========================================
# Validator mapping integration (AC 5)
# ==========================================


class TestValidatorMappingIntegration:
    """Tests for validator mapping integration with Report Browser."""

    def test_synthesis_reports_apply_validator_mapping(
        self, context_menu_js_content: str
    ) -> None:
        """Verify synthesis reports still apply validator ID replacement."""
        assert "isSynthesisReport" in context_menu_js_content
        assert "replaceValidatorIdsInContent" in context_menu_js_content

    def test_mapping_applied_before_rendering(
        self, context_menu_js_content: str
    ) -> None:
        """Verify validator mapping is applied before content is set."""
        # Find loadReportContent function
        func_start = context_menu_js_content.find("async loadReportContent(report)")
        # Function is the last one in file, so take rest
        func_content = context_menu_js_content[func_start:]

        # replaceValidatorIdsInContent should come before contentModal.content =
        mapping_pos = func_content.find("replaceValidatorIdsInContent")
        content_set_pos = func_content.find("this.contentModal.content = content")

        assert mapping_pos != -1, "Validator mapping not found"
        assert content_set_pos != -1, "Content set not found"
        assert mapping_pos < content_set_pos, (
            "Validator mapping should be applied before setting content"
        )


# ==========================================
# Built output tests
# ==========================================


class TestBuiltOutput:
    """Tests for built output files."""

    @pytest.fixture
    def built_index_content(self) -> str:
        """Read built index.html content."""
        index_path = (
            Path(__file__).parent.parent.parent
            / "src/bmad_assist/dashboard/static/index.html"
        )
        if not index_path.exists():
            pytest.skip("Built index.html not found - run build first")
        return index_path.read_text(encoding="utf-8")

    @pytest.fixture
    def built_context_menu_js(self) -> str:
        """Read built context-menu.js content."""
        js_path = (
            Path(__file__).parent.parent.parent
            / "src/bmad_assist/dashboard/static/js/components/context-menu.js"
        )
        if not js_path.exists():
            pytest.skip("Built context-menu.js not found - run build first")
        return js_path.read_text(encoding="utf-8")

    def test_browser_state_initialization_in_built_output(
        self, built_context_menu_js: str
    ) -> None:
        """Verify browser state initialization with defensive check is in built context-menu.js."""
        assert "if (window.contentBrowserComponent)" in built_context_menu_js
        assert (
            "this.contentModal.browser = window.contentBrowserComponent().createBrowserState()"
            in built_context_menu_js
        )

    def test_loading_toast_in_built_output(self, built_context_menu_js: str) -> None:
        """Verify loading toast is in built context-menu.js."""
        assert "showToast('Loading report...')" in built_context_menu_js

    def test_view_toggle_in_built_output(self, built_index_content: str) -> None:
        """Verify view toggle is in built index.html."""
        assert 'data-testid="view-toggle"' in built_index_content
