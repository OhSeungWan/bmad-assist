"""Tests for Review Browser Validator Mapping (Story 24.8).

This file tests the frontend implementation that maps validator IDs (a, b, c)
to actual model names in the report list modal:
- getReportDisplayName() method in modals.js
- Report list HTML uses getReportDisplayName(report) instead of report.provider
- viewReports() awaits mapping load before showing modal
"""
from pathlib import Path

import pytest


@pytest.fixture
def modals_js_content() -> str:
    """Read modals.js content."""
    modals_path = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/static-src/js/components/modals.js"
    )
    return modals_path.read_text(encoding="utf-8")


@pytest.fixture
def context_menu_js_content() -> str:
    """Read context-menu.js content."""
    context_menu_path = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/static-src/js/components/context-menu.js"
    )
    return context_menu_path.read_text(encoding="utf-8")


@pytest.fixture
def tail_html_content() -> str:
    """Read 11-tail.html content."""
    tail_path = (
        Path(__file__).parent.parent.parent
        / "src/bmad_assist/dashboard/static-src/11-tail.html"
    )
    return tail_path.read_text(encoding="utf-8")


# ==========================================
# Tests for getReportDisplayName() - Task 1
# ==========================================


class TestGetReportDisplayNameMethod:
    """Tests for getReportDisplayName() method in modals.js (AC3, AC4)."""

    def test_method_exists(self, modals_js_content: str) -> None:
        """Verify getReportDisplayName method exists."""
        assert "getReportDisplayName(report)" in modals_js_content

    def test_has_story_reference(self, modals_js_content: str) -> None:
        """Verify method has Story 24.8 reference."""
        # Check for AC3 reference in method documentation
        assert "Story 24.8 AC3" in modals_js_content

    def test_handles_missing_report(self, modals_js_content: str) -> None:
        """Verify method handles null/undefined report (AC4)."""
        # Should check if report exists before accessing properties
        assert "!report || !report.provider" in modals_js_content

    def test_returns_fallback_for_missing_provider(self, modals_js_content: str) -> None:
        """Verify method returns fallback when provider is missing (AC4)."""
        assert "report?.name || 'Unknown'" in modals_js_content

    def test_checks_mapping_loaded_flag(self, modals_js_content: str) -> None:
        """Verify method checks _reportValidatorMappingLoaded before using mapping (AC4)."""
        # Check that method uses the loaded flag
        assert "!this._reportValidatorMappingLoaded" in modals_js_content
        assert "return report.provider" in modals_js_content

    def test_converts_letter_to_uppercase(self, modals_js_content: str) -> None:
        """Verify method converts provider letter to uppercase for lookup."""
        assert "report.provider.toUpperCase()" in modals_js_content

    def test_builds_validator_key(self, modals_js_content: str) -> None:
        """Verify method builds 'Validator X' key format for lookup."""
        assert "`Validator ${letter}`" in modals_js_content

    def test_looks_up_in_mapping(self, modals_js_content: str) -> None:
        """Verify method looks up key in _reportValidatorMapping."""
        assert "this._reportValidatorMapping[key]" in modals_js_content

    def test_logs_warning_for_missing_mapping(self, modals_js_content: str) -> None:
        """Verify method logs warning when letter not found in mapping (AC4 debugging)."""
        assert "console.warn" in modals_js_content
        assert "No mapping found for validator" in modals_js_content

    def test_returns_mapped_or_fallback(self, modals_js_content: str) -> None:
        """Verify method returns mapped name or falls back to original letter."""
        assert "return mapped || report.provider" in modals_js_content


# ==========================================
# Tests for Report List HTML - Task 1
# ==========================================


class TestReportListHTML:
    """Tests for report list HTML using getReportDisplayName (AC3)."""

    def test_validation_reports_use_display_name(self, tail_html_content: str) -> None:
        """Verify validation report items use getReportDisplayName(report)."""
        # Check that validation reports use the new method
        assert 'data-testid="validation-report-item"' in tail_html_content
        # The x-text should use getReportDisplayName, not report.provider
        assert (
            'x-text="getReportDisplayName(report)"' in tail_html_content
        ), "Validation report items should use getReportDisplayName(report)"

    def test_code_review_reports_use_display_name(self, tail_html_content: str) -> None:
        """Verify code review report items use getReportDisplayName(report)."""
        # Check that code review reports use the new method
        assert 'data-testid="code-review-report-item"' in tail_html_content
        # The x-text should use getReportDisplayName, not report.provider
        assert (
            'x-text="getReportDisplayName(report)"' in tail_html_content
        ), "Code review report items should use getReportDisplayName(report)"

    def test_validation_section_has_story_comment(self, tail_html_content: str) -> None:
        """Verify validation section has Story 24.8 comment."""
        assert "Story 24.8" in tail_html_content

    def test_not_using_old_provider_pattern(self, tail_html_content: str) -> None:
        """Verify old pattern (report.provider || report.name) is not used in report items."""
        # The old pattern should NOT be in report item buttons anymore
        # Note: It may still be used elsewhere, so we check specifically in the report modal context
        content_after_report_modal = tail_html_content.split('data-testid="report-modal"')[1]
        content_before_close = content_after_report_modal.split('data-testid="close-report-modal"')[
            0
        ]
        # Old pattern should not appear in the report list section
        assert (
            'x-text="report.provider || report.name"' not in content_before_close
        ), "Old pattern should be replaced with getReportDisplayName(report)"


# ==========================================
# Tests for viewReports() Await - Task 2
# ==========================================


class TestViewReportsAwait:
    """Tests for viewReports() awaiting mapping load (AC5)."""

    def test_view_reports_is_async(self, context_menu_js_content: str) -> None:
        """Verify viewReports is an async function."""
        assert "async viewReports(epic, story)" in context_menu_js_content

    def test_view_reports_has_story_reference(self, context_menu_js_content: str) -> None:
        """Verify viewReports has Story 24.8 AC5 reference."""
        assert "Story 24.8 AC5" in context_menu_js_content

    def test_awaits_mapping_load(self, context_menu_js_content: str) -> None:
        """Verify viewReports awaits loadReportValidatorMapping (AC5)."""
        # Should use await before the mapping load
        assert "await this.loadReportValidatorMapping(epic, story)" in context_menu_js_content

    def test_modal_show_after_await(self, context_menu_js_content: str) -> None:
        """Verify reportModal.show = true comes AFTER the await."""
        # Find the viewReports function
        view_reports_start = context_menu_js_content.find("async viewReports(epic, story)")
        view_reports_end = context_menu_js_content.find("async viewStoryModal", view_reports_start)
        view_reports_content = context_menu_js_content[view_reports_start:view_reports_end]

        # Find positions within the function
        await_pos = view_reports_content.find("await this.loadReportValidatorMapping")
        modal_show_pos = view_reports_content.find("this.reportModal.show = true")

        assert await_pos < modal_show_pos, (
            f"reportModal.show should come AFTER await, "
            f"but positions are await={await_pos} vs show={modal_show_pos}"
        )

    def test_has_graceful_degradation_comment(self, context_menu_js_content: str) -> None:
        """Verify code comments explain graceful degradation behavior."""
        assert "Graceful degradation" in context_menu_js_content


# ==========================================
# Tests for Fallback Behavior - AC4
# ==========================================


class TestGracefulFallback:
    """Tests for graceful fallback behavior (AC4)."""

    def test_modals_has_mapping_state(self, modals_js_content: str) -> None:
        """Verify modals.js has mapping state variables."""
        assert "_reportValidatorMapping: {}" in modals_js_content
        assert "_reportValidatorMappingLoaded: false" in modals_js_content

    def test_load_mapping_sets_loaded_flag(self, modals_js_content: str) -> None:
        """Verify loadReportValidatorMapping sets _reportValidatorMappingLoaded = true."""
        assert "_reportValidatorMappingLoaded = true" in modals_js_content

    def test_load_mapping_resets_state_first(self, modals_js_content: str) -> None:
        """Verify loadReportValidatorMapping resets state at the start."""
        # Should reset both mapping and loaded flag at start
        assert "this._reportValidatorMapping = {}" in modals_js_content
        assert "this._reportValidatorMappingLoaded = false" in modals_js_content


# ==========================================
# Integration Tests
# ==========================================


class TestIntegration:
    """Integration tests for the complete mapping flow."""

    def test_existing_mapping_infrastructure_exists(self, modals_js_content: str) -> None:
        """Verify existing Story 23.8 infrastructure is present."""
        assert "loadReportValidatorMapping" in modals_js_content
        assert "replaceValidatorIdsInContent" in modals_js_content

    def test_replace_validator_ids_uses_mapping(self, modals_js_content: str) -> None:
        """Verify replaceValidatorIdsInContent uses the mapping."""
        assert "this._reportValidatorMapping" in modals_js_content

    def test_context_menu_calls_load_mapping(self, context_menu_js_content: str) -> None:
        """Verify context-menu.js calls loadReportValidatorMapping."""
        assert "loadReportValidatorMapping" in context_menu_js_content

    def test_synthesis_reports_still_get_mapped(self, context_menu_js_content: str) -> None:
        """Verify synthesis reports still apply validator ID replacement (Story 23.8)."""
        assert "isSynthesisReport" in context_menu_js_content
        assert "replaceValidatorIdsInContent" in context_menu_js_content


class TestDocumentation:
    """Tests for code documentation."""

    def test_get_report_display_name_documented(self, modals_js_content: str) -> None:
        """Verify getReportDisplayName has JSDoc documentation."""
        # Check for documentation before the method
        method_start = modals_js_content.find("getReportDisplayName(report)")
        doc_before = modals_js_content[method_start - 500 : method_start]
        assert "/**" in doc_before
        assert "@param" in doc_before
        assert "@returns" in doc_before

    def test_view_reports_documents_ac5(self, context_menu_js_content: str) -> None:
        """Verify viewReports documents the AC5 await behavior."""
        view_reports_start = context_menu_js_content.find("async viewReports")
        doc_before = context_menu_js_content[view_reports_start - 200 : view_reports_start]
        assert "Await mapping" in doc_before or "AC5" in doc_before or "mapping" in doc_before


class TestBuiltOutput:
    """Tests for built static/index.html."""

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

    def test_get_report_display_name_in_built_output(self, built_index_content: str) -> None:
        """Verify getReportDisplayName is in built index.html."""
        assert "getReportDisplayName(report)" in built_index_content

    def test_validation_report_uses_display_name_in_built(self, built_index_content: str) -> None:
        """Verify built output uses getReportDisplayName for validation reports."""
        assert 'x-text="getReportDisplayName(report)"' in built_index_content
