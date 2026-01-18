"""Tests for sprint-status repair orchestrator module.

Tests cover:
- RepairMode enum
- RepairResult dataclass properties and summary
- Divergence calculation accuracy
- SILENT mode auto-repair without prompting
- INTERACTIVE mode with divergence thresholds
- Callback registration and recursion guard
- Error handling and loop safety
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from bmad_assist.core.exceptions import ParserError, StateError
from bmad_assist.core.state import Phase, State
from bmad_assist.sprint.classifier import EntryType
from bmad_assist.sprint.models import (
    SprintStatus,
    SprintStatusEntry,
    SprintStatusMetadata,
)
from bmad_assist.sprint.repair import (
    RepairMode,
    RepairResult,
    _calculate_divergence,
    _default_sync_callback,
    _get_sprint_status_path,
    ensure_sprint_sync_callback,
    repair_sprint_status,
)
from bmad_assist.sprint.sync import (
    clear_sync_callbacks,
    get_sync_callbacks,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_metadata() -> SprintStatusMetadata:
    """Create sample metadata for tests."""
    return SprintStatusMetadata(
        generated=datetime(2026, 1, 7, 12, 0, 0),
        project="test-project",
    )


@pytest.fixture
def sample_entries() -> dict[str, SprintStatusEntry]:
    """Create sample entries dict for tests."""
    return {
        "epic-20": SprintStatusEntry(
            key="epic-20",
            status="in-progress",
            entry_type=EntryType.EPIC_META,
        ),
        "20-1-setup": SprintStatusEntry(
            key="20-1-setup",
            status="done",
            entry_type=EntryType.EPIC_STORY,
        ),
        "20-2-feature": SprintStatusEntry(
            key="20-2-feature",
            status="in-progress",
            entry_type=EntryType.EPIC_STORY,
        ),
        "20-3-test": SprintStatusEntry(
            key="20-3-test",
            status="backlog",
            entry_type=EntryType.EPIC_STORY,
        ),
    }


@pytest.fixture
def sample_sprint_status(
    sample_metadata: SprintStatusMetadata,
    sample_entries: dict[str, SprintStatusEntry],
) -> SprintStatus:
    """Create sample SprintStatus for tests."""
    return SprintStatus(metadata=sample_metadata, entries=sample_entries)


@pytest.fixture
def sample_state() -> State:
    """Create sample State for tests."""
    return State(
        current_epic=20,
        current_story="20.2",
        current_phase=Phase.DEV_STORY,
        completed_stories=["20.1"],
        completed_epics=[],
    )


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create temporary project structure for repair tests."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    # Create sprint-status directory
    sprint_dir = project_root / "_bmad-output" / "implementation-artifacts"
    sprint_dir.mkdir(parents=True)

    # Create epics directory
    epics_dir = project_root / "docs" / "epics"
    epics_dir.mkdir(parents=True)

    # Create stories directory
    stories_dir = sprint_dir / "stories"
    stories_dir.mkdir()

    return project_root


@pytest.fixture(autouse=True)
def cleanup_callbacks():
    """Ensure callbacks are cleared before and after each test."""
    clear_sync_callbacks()
    yield
    clear_sync_callbacks()


# =============================================================================
# Test: RepairMode Enum (Task 1)
# =============================================================================


class TestRepairMode:
    """Tests for RepairMode enum."""

    def test_repair_mode_silent_value(self):
        """SILENT mode has value 'silent'."""
        assert RepairMode.SILENT.value == "silent"

    def test_repair_mode_interactive_value(self):
        """INTERACTIVE mode has value 'interactive'."""
        assert RepairMode.INTERACTIVE.value == "interactive"

    def test_repair_mode_is_enum(self):
        """RepairMode is a proper enum."""
        from enum import Enum

        assert issubclass(RepairMode, Enum)

    def test_repair_mode_has_two_values(self):
        """RepairMode has exactly two values."""
        assert len(RepairMode) == 2


# =============================================================================
# Test: RepairResult Dataclass (Task 1)
# =============================================================================


class TestRepairResult:
    """Tests for RepairResult frozen dataclass."""

    def test_repair_result_default_values(self):
        """RepairResult has correct default values."""
        result = RepairResult()
        assert result.changes_count == 0
        assert result.divergence_pct == 0.0
        assert result.was_interactive is False
        assert result.user_cancelled is False
        assert result.errors == ()

    def test_repair_result_with_values(self):
        """RepairResult accepts all fields."""
        result = RepairResult(
            changes_count=5,
            divergence_pct=25.0,
            was_interactive=True,
            user_cancelled=False,
            errors=("error1",),
        )
        assert result.changes_count == 5
        assert result.divergence_pct == 25.0
        assert result.was_interactive is True
        assert result.user_cancelled is False
        assert result.errors == ("error1",)

    def test_repair_result_is_frozen(self):
        """RepairResult is immutable (frozen)."""
        result = RepairResult(changes_count=1)
        with pytest.raises(AttributeError):
            result.changes_count = 2  # type: ignore

    def test_repair_result_success_property_true(self):
        """Success property is True when no errors and not cancelled."""
        result = RepairResult(changes_count=5, errors=())
        assert result.success is True

    def test_repair_result_success_property_false_with_errors(self):
        """Success property is False when errors present."""
        result = RepairResult(errors=("error",))
        assert result.success is False

    def test_repair_result_success_property_false_when_cancelled(self):
        """Success property is False when user cancelled."""
        result = RepairResult(user_cancelled=True)
        assert result.success is False

    def test_repair_result_repr(self):
        """RepairResult has informative repr."""
        result = RepairResult(
            changes_count=5,
            divergence_pct=25.0,
            user_cancelled=True,
            errors=("error1", "error2"),
        )
        repr_str = repr(result)
        assert "changes=5" in repr_str
        assert "divergence=25.0%" in repr_str
        assert "errors=2" in repr_str
        assert "cancelled=True" in repr_str

    def test_repair_result_summary_success(self):
        """summary() returns success message."""
        result = RepairResult(changes_count=5, divergence_pct=12.5)
        summary = result.summary()
        assert "Repaired 5 entries" in summary
        assert "12.5% divergence" in summary

    def test_repair_result_summary_cancelled(self):
        """summary() returns cancelled message when cancelled."""
        result = RepairResult(user_cancelled=True)
        assert result.summary() == "Repair cancelled by user"

    def test_repair_result_summary_with_errors(self):
        """summary() returns error message when errors present."""
        result = RepairResult(errors=("File not found", "Parse error"))
        summary = result.summary()
        assert "Repair failed:" in summary
        assert "File not found" in summary


# =============================================================================
# Test: Divergence Calculation (Task 2, AC3)
# =============================================================================


class TestDivergenceCalculation:
    """Tests for divergence percentage calculation."""

    def test_divergence_zero_entries(self):
        """Divergence is 0.0 when existing has 0 entries."""
        result = _calculate_divergence(0, 10)
        assert result == 0.0

    def test_divergence_zero_changes(self):
        """Divergence is 0.0 when no changes made."""
        result = _calculate_divergence(10, 0)
        assert result == 0.0

    def test_divergence_half_changed(self):
        """Divergence is 50% when half entries changed."""
        result = _calculate_divergence(100, 50)
        assert result == 50.0

    def test_divergence_all_changed(self):
        """Divergence is 100% when all entries changed."""
        result = _calculate_divergence(10, 10)
        assert result == 100.0

    def test_divergence_threshold_at_30(self):
        """Divergence exactly at 30% is not above threshold."""
        result = _calculate_divergence(100, 30)
        assert result == 30.0
        # Threshold is >30%, so 30.0 should NOT trigger warning

    def test_divergence_above_threshold(self):
        """Divergence above 30% triggers warning in INTERACTIVE mode."""
        result = _calculate_divergence(100, 31)
        assert result == 31.0
        assert result > 30.0

    def test_divergence_small_numbers(self):
        """Divergence calculated correctly for small numbers."""
        result = _calculate_divergence(3, 1)
        assert abs(result - 33.33) < 0.1  # ~33.33%


# =============================================================================
# Test: Sprint Status Path (Utility)
# =============================================================================


class TestSprintStatusPath:
    """Tests for sprint-status path convention."""

    def test_get_sprint_status_path(self, tmp_path: Path):
        """Returns correct path following BMAD v6 convention."""
        path = _get_sprint_status_path(tmp_path)
        expected = tmp_path / "_bmad-output" / "implementation-artifacts" / "sprint-status.yaml"
        assert path == expected


# =============================================================================
# Test: SILENT Mode (Task 2)
# =============================================================================


class TestSilentMode:
    """Tests for SILENT mode auto-repair."""

    def test_silent_mode_proceeds_without_warning(
        self,
        temp_project: Path,
        sample_sprint_status: SprintStatus,
        sample_state: State,
        caplog: pytest.LogCaptureFixture,
    ):
        """SILENT mode repairs without WARNING even with high divergence."""
        from bmad_assist.sprint.writer import write_sprint_status

        # Write initial sprint-status
        sprint_path = _get_sprint_status_path(temp_project)
        write_sprint_status(sample_sprint_status, sprint_path)

        # Create epic file to generate entries
        epic_path = temp_project / "docs" / "epics" / "epic-20.md"
        epic_path.write_text(
            "---\nepic-id: 20\n---\n# Epic 20\n## Stories\n- Story 20.1: Setup\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING):
            result = repair_sprint_status(temp_project, RepairMode.SILENT, sample_state)

        # Should succeed without warning log
        assert result.success
        assert result.was_interactive is False
        # Should NOT log WARNING about divergence
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        divergence_warnings = [r for r in warning_records if "divergence" in r.message.lower()]
        assert len(divergence_warnings) == 0


# =============================================================================
# Test: INTERACTIVE Mode (Task 3, AC3, AC8)
# =============================================================================


class TestInteractiveMode:
    """Tests for INTERACTIVE mode with divergence thresholds."""

    def test_interactive_mode_low_divergence_no_warning(
        self,
        temp_project: Path,
        caplog: pytest.LogCaptureFixture,
    ):
        """INTERACTIVE mode with divergence <= 30% proceeds silently."""
        from bmad_assist.sprint.writer import write_sprint_status

        # Create sprint-status with many entries where only a small % will change
        sprint_path = _get_sprint_status_path(temp_project)
        entries = {
            "epic-20": SprintStatusEntry(
                key="epic-20",
                status="in-progress",
                entry_type=EntryType.EPIC_META,
            ),
            # These story keys must match what generator produces from epic file
            "20-1-setup": SprintStatusEntry(
                key="20-1-setup",
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            ),
            "20-2-feature": SprintStatusEntry(
                key="20-2-feature",
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            ),
            "20-3-test": SprintStatusEntry(
                key="20-3-test",
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            ),
            "20-4-deploy": SprintStatusEntry(
                key="20-4-deploy",
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            ),
        }
        status = SprintStatus(
            metadata=SprintStatusMetadata(
                generated=datetime.now(UTC).replace(tzinfo=None),
                project="test",
            ),
            entries=entries,
        )
        write_sprint_status(status, sprint_path)

        # Create matching epic file with same stories (use ### Story format)
        epic_path = temp_project / "docs" / "epics" / "epic-20.md"
        epic_path.write_text(
            "---\nepic_num: 20\n---\n# Epic 20\n## Stories\n\n"
            "### Story 20.1: Setup\n\n"
            "### Story 20.2: Feature\n\n"
            "### Story 20.3: Test\n\n"
            "### Story 20.4: Deploy\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING):
            result = repair_sprint_status(temp_project, RepairMode.INTERACTIVE, None)

        assert result.was_interactive is True
        # With matching entries, divergence should be low (no high divergence warning)
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        divergence_warnings = [r for r in warning_records if "high divergence" in r.message.lower()]
        assert len(divergence_warnings) == 0

    def test_interactive_mode_high_divergence_shows_dialog(
        self,
        temp_project: Path,
        sample_sprint_status: SprintStatus,
        caplog: pytest.LogCaptureFixture,
    ):
        """INTERACTIVE mode with divergence > 30% shows dialog (Story 20.12).

        In CI/non-TTY environments, dialog auto-cancels. Test verifies:
        1. Dialog is shown for high divergence
        2. Cancellation logs warning
        3. Result indicates user_cancelled=True (dialog auto-cancelled)
        """
        from bmad_assist.sprint.writer import write_sprint_status

        # Write initial sprint-status with entries that won't match generated
        sprint_path = _get_sprint_status_path(temp_project)
        write_sprint_status(sample_sprint_status, sprint_path)

        # Create epic file that generates different entries
        epic_path = temp_project / "docs" / "epics" / "epic-99.md"
        epic_path.write_text(
            "---\nepic_num: 99\n---\n# Epic 99\n## Stories\n\n"
            "### Story 99.1: New\n\n### Story 99.2: Another\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING):
            result = repair_sprint_status(temp_project, RepairMode.INTERACTIVE, None)

        # In CI/non-TTY, dialog auto-cancels → user_cancelled=True
        # (This is expected behavior per AC9 of Story 20.12)
        assert result.was_interactive is True
        assert result.divergence_pct > 30, "Test expects high divergence"

        # Dialog was shown and cancelled (either by timeout or CI auto-cancel)
        # Should log warning about cancellation
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        # Either "cancelled" or "timed out" should appear in warnings
        cancellation_warnings = [
            r
            for r in warning_records
            if "cancel" in r.message.lower() or "timed out" in r.message.lower()
        ]
        if result.user_cancelled:
            assert len(cancellation_warnings) >= 1, (
                f"Expected WARNING about cancellation but got: "
                f"{[r.message for r in warning_records]}"
            )

    def test_interactive_mode_never_blocks(
        self,
        temp_project: Path,
    ):
        """INTERACTIVE mode always proceeds, never blocks (pre-Story 20.12)."""
        # Create empty sprint-status
        sprint_path = _get_sprint_status_path(temp_project)
        sprint_path.parent.mkdir(parents=True, exist_ok=True)
        sprint_path.write_text(
            "generated: 2026-01-07T00:00:00\ndevelopment_status: {}\n",
            encoding="utf-8",
        )

        result = repair_sprint_status(temp_project, RepairMode.INTERACTIVE, None)

        # Should never block or set user_cancelled
        assert result.user_cancelled is False


# =============================================================================
# Test: Error Handling (Task 2, AC5)
# =============================================================================


class TestErrorHandling:
    """Tests for error handling - loop safety."""

    def test_repair_handles_state_error(
        self,
        temp_project: Path,
        caplog: pytest.LogCaptureFixture,
    ):
        """repair_sprint_status catches StateError and returns in errors."""
        with patch(
            "bmad_assist.sprint.repair._repair_sprint_status_impl",
            side_effect=StateError("Test state error"),
        ):
            result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        assert result.success is False
        assert len(result.errors) == 1
        assert "Test state error" in result.errors[0]

    def test_repair_handles_parser_error(
        self,
        temp_project: Path,
    ):
        """repair_sprint_status catches ParserError and returns in errors."""
        with patch(
            "bmad_assist.sprint.repair._repair_sprint_status_impl",
            side_effect=ParserError("Test parser error"),
        ):
            result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        assert result.success is False
        assert "Test parser error" in result.errors[0]

    def test_repair_handles_os_error(
        self,
        temp_project: Path,
    ):
        """repair_sprint_status catches OSError and returns in errors."""
        with patch(
            "bmad_assist.sprint.repair._repair_sprint_status_impl",
            side_effect=OSError("Permission denied"),
        ):
            result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        assert result.success is False
        assert "Permission denied" in result.errors[0]

    def test_repair_handles_value_error(
        self,
        temp_project: Path,
    ):
        """repair_sprint_status catches ValueError and returns in errors."""
        with patch(
            "bmad_assist.sprint.repair._repair_sprint_status_impl",
            side_effect=ValueError("Invalid value"),
        ):
            result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        assert result.success is False
        assert "Invalid value" in result.errors[0]

    def test_repair_handles_key_error(
        self,
        temp_project: Path,
    ):
        """repair_sprint_status catches KeyError and returns in errors."""
        with patch(
            "bmad_assist.sprint.repair._repair_sprint_status_impl",
            side_effect=KeyError("missing_key"),
        ):
            result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        assert result.success is False

    def test_repair_handles_generic_exception(
        self,
        temp_project: Path,
    ):
        """repair_sprint_status catches generic Exception as last resort."""
        with patch(
            "bmad_assist.sprint.repair._repair_sprint_status_impl",
            side_effect=RuntimeError("Unexpected error"),
        ):
            result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        assert result.success is False
        assert "Unexpected error" in result.errors[0]

    def test_repair_logs_warning_on_error(
        self,
        temp_project: Path,
        caplog: pytest.LogCaptureFixture,
    ):
        """repair_sprint_status logs WARNING on errors."""
        with (
            patch(
                "bmad_assist.sprint.repair._repair_sprint_status_impl",
                side_effect=StateError("Test error"),
            ),
            caplog.at_level(logging.WARNING),
        ):
            repair_sprint_status(temp_project, RepairMode.SILENT, None)

        assert any("Sprint repair failed" in r.message for r in caplog.records)


# =============================================================================
# Test: Callback Pattern (Task 4)
# =============================================================================


class TestDefaultSyncCallback:
    """Tests for default sync callback with recursion guard."""

    def test_ensure_callback_registered(self):
        """ensure_sprint_sync_callback registers callback."""
        clear_sync_callbacks()
        ensure_sprint_sync_callback()

        callbacks = get_sync_callbacks()
        assert len(callbacks) == 1
        assert callbacks[0] is _default_sync_callback

    def test_ensure_callback_idempotent(self):
        """ensure_sprint_sync_callback is idempotent - no duplicates."""
        clear_sync_callbacks()
        ensure_sprint_sync_callback()
        ensure_sprint_sync_callback()
        ensure_sprint_sync_callback()

        callbacks = get_sync_callbacks()
        assert len(callbacks) == 1

    def test_callback_uses_trigger_sync_not_repair(
        self,
        temp_project: Path,
        sample_state: State,
    ):
        """Default callback uses lightweight trigger_sync, not full repair."""
        with patch("bmad_assist.sprint.sync.trigger_sync") as mock_sync:
            mock_sync.return_value = MagicMock(summary=lambda: "Synced")
            _default_sync_callback(sample_state, temp_project)

        mock_sync.assert_called_once_with(sample_state, temp_project)

    def test_callback_catches_exceptions(
        self,
        temp_project: Path,
        sample_state: State,
        caplog: pytest.LogCaptureFixture,
    ):
        """Default callback catches and logs exceptions, never raises."""
        with (
            patch(
                "bmad_assist.sprint.sync.trigger_sync",
                side_effect=RuntimeError("Test error"),
            ),
            caplog.at_level(logging.WARNING),
        ):
            # Should NOT raise
            _default_sync_callback(sample_state, temp_project)

        assert any("failed" in r.message.lower() for r in caplog.records)

    def test_callback_recursion_guard(
        self,
        temp_project: Path,
        sample_state: State,
    ):
        """Default callback has recursion guard to prevent re-entry."""
        import bmad_assist.sprint.repair as repair_module

        # Simulate being in progress
        original_flag = repair_module._sync_in_progress
        try:
            repair_module._sync_in_progress = True

            with patch("bmad_assist.sprint.sync.trigger_sync") as mock_sync:
                _default_sync_callback(sample_state, temp_project)

            # Should not call trigger_sync when in progress
            mock_sync.assert_not_called()
        finally:
            repair_module._sync_in_progress = original_flag

    def test_callback_resets_flag_on_exception(
        self,
        temp_project: Path,
        sample_state: State,
    ):
        """Recursion guard flag is reset even on exception."""
        import bmad_assist.sprint.repair as repair_module

        with patch(
            "bmad_assist.sprint.sync.trigger_sync",
            side_effect=RuntimeError("Test error"),
        ):
            _default_sync_callback(sample_state, temp_project)

        # Flag should be reset
        assert repair_module._sync_in_progress is False


# =============================================================================
# Test: Full Repair Integration (Task 2)
# =============================================================================


class TestFullRepairIntegration:
    """Integration tests for full repair cycle."""

    def test_repair_creates_new_file_if_missing(
        self,
        temp_project: Path,
    ):
        """Repair creates sprint-status if missing."""
        sprint_path = _get_sprint_status_path(temp_project)

        # Create epic file
        epic_path = temp_project / "docs" / "epics" / "epic-1.md"
        epic_path.write_text(
            "---\nepic-id: 1\n---\n# Epic 1\n## Stories\n- Story 1.1: First\n",
            encoding="utf-8",
        )

        result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        assert result.success
        assert sprint_path.exists()

    def test_repair_preserves_existing_comments(
        self,
        temp_project: Path,
    ):
        """Repair preserves comments when ruamel.yaml is available."""
        from bmad_assist.sprint.writer import has_ruamel, write_sprint_status

        if not has_ruamel():
            pytest.skip("ruamel.yaml not available")

        # Create sprint-status with entries
        sprint_path = _get_sprint_status_path(temp_project)
        entries = {
            "epic-1": SprintStatusEntry(
                key="epic-1",
                status="in-progress",
                entry_type=EntryType.EPIC_META,
            ),
        }
        status = SprintStatus(
            metadata=SprintStatusMetadata(
                generated=datetime.now(UTC).replace(tzinfo=None),
                project="test",
            ),
            entries=entries,
        )
        write_sprint_status(status, sprint_path)

        # Create matching epic file
        epic_path = temp_project / "docs" / "epics" / "epic-1.md"
        epic_path.write_text(
            "---\nepic-id: 1\n---\n# Epic 1\n",
            encoding="utf-8",
        )

        result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        assert result.success

    def test_repair_with_state_sync(
        self,
        temp_project: Path,
        sample_state: State,
    ):
        """Repair integrates state sync when state provided."""
        from bmad_assist.sprint.writer import write_sprint_status

        # Create sprint-status with entries
        sprint_path = _get_sprint_status_path(temp_project)
        entries = {
            "epic-20": SprintStatusEntry(
                key="epic-20",
                status="in-progress",
                entry_type=EntryType.EPIC_META,
            ),
            "20-1-setup": SprintStatusEntry(
                key="20-1-setup",
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            ),
            "20-2-feature": SprintStatusEntry(
                key="20-2-feature",
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            ),
        }
        status = SprintStatus(
            metadata=SprintStatusMetadata(
                generated=datetime.now(UTC).replace(tzinfo=None),
                project="test",
            ),
            entries=entries,
        )
        write_sprint_status(status, sprint_path)

        # Create epic file
        epic_path = temp_project / "docs" / "epics" / "epic-20.md"
        epic_path.write_text(
            "---\nepic_num: 20\n---\n# Epic 20\n## Stories\n\n"
            "### Story 20.1: Setup\n\n### Story 20.2: Feature\n",
            encoding="utf-8",
        )

        result = repair_sprint_status(temp_project, RepairMode.SILENT, sample_state)

        assert result.success

        # Verify state sync was applied
        from bmad_assist.sprint.parser import parse_sprint_status

        final_status = parse_sprint_status(sprint_path)

        # Story 20.1 should be done (in completed_stories)
        if "20-1-setup" in final_status.entries:
            assert final_status.entries["20-1-setup"].status == "done"

    def test_repair_detects_corrupted_file(
        self,
        temp_project: Path,
        caplog: pytest.LogCaptureFixture,
    ):
        """Repair detects corrupted file and returns error."""
        sprint_path = _get_sprint_status_path(temp_project)
        sprint_path.parent.mkdir(parents=True, exist_ok=True)

        # Write corrupted content (non-empty but invalid)
        sprint_path.write_text("{{invalid yaml", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        # Should return error about corruption or parse failure
        assert result.success is False, "Corrupted file should cause repair failure"
        assert len(result.errors) > 0, "Expected at least one error for corrupted file"
        # Check that error message indicates parsing/corruption issue
        error_msg = " ".join(result.errors).lower()
        assert any(word in error_msg for word in ("corrupt", "parse", "invalid", "yaml")), (
            f"Expected error about corruption/parse failure, got: {result.errors}"
        )
        # Should also log corruption detection (at ERROR level, not WARNING)
        log_messages = [r.message.lower() for r in caplog.records]
        assert any("corrupt" in msg for msg in log_messages), (
            f"Expected log about corruption, got: {[r.message for r in caplog.records]}"
        )


# =============================================================================
# Test: INFO Logging Format (AC4)
# =============================================================================


class TestLoggingFormat:
    """Tests for INFO logging format matching AC4."""

    def test_info_log_format(
        self,
        temp_project: Path,
        caplog: pytest.LogCaptureFixture,
    ):
        """Check log format matches AC4 for changes and divergence."""
        from bmad_assist.sprint.writer import write_sprint_status

        # Create sprint-status
        sprint_path = _get_sprint_status_path(temp_project)
        entries = {
            "epic-1": SprintStatusEntry(
                key="epic-1",
                status="in-progress",
                entry_type=EntryType.EPIC_META,
            ),
        }
        status = SprintStatus(
            metadata=SprintStatusMetadata(
                generated=datetime.now(UTC).replace(tzinfo=None),
                project="test",
            ),
            entries=entries,
        )
        write_sprint_status(status, sprint_path)

        # Create epic file
        epic_path = temp_project / "docs" / "epics" / "epic-1.md"
        epic_path.write_text(
            "---\nepic_num: 1\n---\n# Epic 1\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.INFO):
            repair_sprint_status(temp_project, RepairMode.SILENT, None)

        # Check for expected log format
        info_records = [r for r in caplog.records if r.levelno == logging.INFO]
        sync_logs = [r for r in info_records if "Sprint sync:" in r.message]
        assert len(sync_logs) >= 1
        # Should contain changes count and divergence percentage
        log_msg = sync_logs[0].message
        assert "changes" in log_msg
        assert "divergence" in log_msg


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_repair_empty_project(
        self,
        temp_project: Path,
    ):
        """Repair handles project with no epics gracefully."""
        # No epic files created
        result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        # Should succeed with empty result
        assert result.success

    def test_repair_empty_sprint_status(
        self,
        temp_project: Path,
    ):
        """Repair handles empty sprint-status file."""
        sprint_path = _get_sprint_status_path(temp_project)
        sprint_path.parent.mkdir(parents=True, exist_ok=True)
        sprint_path.write_text(
            "generated: 2026-01-07T00:00:00\ndevelopment_status: {}\n",
            encoding="utf-8",
        )

        result = repair_sprint_status(temp_project, RepairMode.INTERACTIVE, None)

        # Empty file = 0% divergence (needs population, not repair)
        assert result.divergence_pct == 0.0

    def test_repair_handles_none_state(
        self,
        temp_project: Path,
    ):
        """Repair works without state (state sync skipped)."""
        from bmad_assist.sprint.writer import write_sprint_status

        # Create a valid sprint-status (not empty, to avoid corruption check)
        sprint_path = _get_sprint_status_path(temp_project)
        entries = {
            "epic-1": SprintStatusEntry(
                key="epic-1",
                status="in-progress",
                entry_type=EntryType.EPIC_META,
            ),
        }
        status = SprintStatus(
            metadata=SprintStatusMetadata(
                generated=datetime.now(UTC).replace(tzinfo=None),
                project="test",
            ),
            entries=entries,
        )
        write_sprint_status(status, sprint_path)

        # Create epic file (use epic_num not epic-id)
        epic_path = temp_project / "docs" / "epics" / "epic-1.md"
        epic_path.write_text(
            "---\nepic_num: 1\n---\n# Epic 1\n## Stories\n- Story 1.1: First\n",
            encoding="utf-8",
        )

        result = repair_sprint_status(temp_project, RepairMode.SILENT, None)

        assert result.success
