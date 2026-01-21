"""Tests for dashboard event emission from main loop.

Story 22.9: SSE sidebar tree updates - Task 6 (tests).

Tests for stdout marker protocol and event emission functions.
"""

import json
from datetime import datetime

import pytest

from bmad_assist.core.loop.dashboard_events import (
    DASHBOARD_EVENT_MARKER,
    emit_phase_complete,
    emit_story_status,
    emit_story_transition,
    emit_validator_progress,
    emit_workflow_status,
    generate_run_id,
    parse_story_id,
    story_id_from_parts,
)


@pytest.fixture(autouse=True)
def enable_dashboard_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable dashboard mode for all tests in this module.

    Dashboard events are only emitted when BMAD_DASHBOARD_MODE=1.
    """
    monkeypatch.setenv("BMAD_DASHBOARD_MODE", "1")


class TestEmitWorkflowStatus:
    """Tests for emit_workflow_status function."""

    def test_emit_workflow_status_prints_marker(self, capsys: pytest.fixture) -> None:
        """Test that emit_workflow_status prints DASHBOARD_EVENT marker."""
        run_id = "run-20260115-080000-a1b2c3d4"
        sequence_id = 1
        epic_num = 22
        story_id = "22.9"
        phase = "DEV_STORY"
        phase_status = "in-progress"

        emit_workflow_status(run_id, sequence_id, epic_num, story_id, phase, phase_status)

        captured = capsys.readouterr()
        assert captured.out.startswith(DASHBOARD_EVENT_MARKER)

        # Verify JSON is valid
        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        assert data["type"] == "workflow_status"
        assert data["run_id"] == run_id
        assert data["sequence_id"] == sequence_id
        assert data["data"]["current_epic"] == epic_num
        assert data["data"]["current_story"] == story_id
        assert data["data"]["current_phase"] == phase
        assert data["data"]["phase_status"] == phase_status

    def test_emit_workflow_status_includes_timestamp(self, capsys: pytest.fixture) -> None:
        """Test that event includes ISO 8601 timestamp."""
        emit_workflow_status(
            run_id="run-20260115-080000-a1b2c3d4",
            sequence_id=1,
            epic_num=22,
            story_id="22.9",
            phase="DEV_STORY",
            phase_status="in-progress",
        )

        captured = capsys.readouterr()
        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        # Verify timestamp is present and valid ISO 8601
        assert "timestamp" in data
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


class TestEmitStoryStatus:
    """Tests for emit_story_status function."""

    def test_emit_story_status_prints_marker(self, capsys: pytest.fixture) -> None:
        """Test that emit_story_status prints DASHBOARD_EVENT marker."""
        emit_story_status(
            run_id="run-20260115-080000-a1b2c3d4",
            sequence_id=2,
            epic_num=22,
            story_num=9,
            story_id="22-9-sse-sidebar-tree-updates",
            status="in-progress",
            previous_status="ready-for-dev",
        )

        captured = capsys.readouterr()
        assert captured.out.startswith(DASHBOARD_EVENT_MARKER)

        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        assert data["type"] == "story_status"
        assert data["data"]["epic_num"] == 22
        assert data["data"]["story_num"] == 9
        assert data["data"]["status"] == "in-progress"
        assert data["data"]["previous_status"] == "ready-for-dev"


class TestEmitStoryTransition:
    """Tests for emit_story_transition function."""

    def test_emit_story_transition_started(self, capsys: pytest.fixture) -> None:
        """Test emit_story_transition with action='started'."""
        emit_story_transition(
            run_id="run-20260115-080000-a1b2c3d4",
            sequence_id=3,
            action="started",
            epic_num=22,
            story_num=9,
            story_id="22-9-sse-sidebar-tree-updates",
            story_title="sse-sidebar-tree-updates",
        )

        captured = capsys.readouterr()
        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        assert data["type"] == "story_transition"
        assert data["data"]["action"] == "started"
        assert data["data"]["epic_num"] == 22
        assert data["data"]["story_num"] == 9

    def test_emit_story_transition_completed(self, capsys: pytest.fixture) -> None:
        """Test emit_story_transition with action='completed'."""
        emit_story_transition(
            run_id="run-20260115-080000-a1b2c3d4",
            sequence_id=4,
            action="completed",
            epic_num=22,
            story_num=9,
            story_id="22-9-sse-sidebar-tree-updates",
            story_title="sse-sidebar-tree-updates",
        )

        captured = capsys.readouterr()
        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        assert data["data"]["action"] == "completed"


class TestParseStoryId:
    """Tests for parse_story_id function."""

    def test_parse_story_id_valid(self) -> None:
        """Test parsing valid story IDs."""
        assert parse_story_id("22.9") == (22, 9)
        assert parse_story_id("1.1") == (1, 1)
        assert parse_story_id("100.999") == (100, 999)

    def test_parse_story_id_invalid_format(self) -> None:
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid story_id format"):
            parse_story_id("invalid")

        with pytest.raises(ValueError, match="Invalid story_id format"):
            parse_story_id("22")  # Missing story number

        with pytest.raises(ValueError, match="Invalid story_id format"):
            parse_story_id("22.9.extra")  # Too many parts

    def test_parse_story_id_invalid_numeric(self) -> None:
        """Test that non-numeric story_num raises ValueError.

        Note: epic_num can now be a string (e.g., "testarch.1"), so only
        story_num is required to be numeric.
        """
        with pytest.raises(ValueError, match="story_num must be numeric"):
            parse_story_id("abc.def")


class TestStoryIdFromParts:
    """Tests for story_id_from_parts function."""

    def test_story_id_from_parts_basic(self) -> None:
        """Test generating story_id from components."""
        result = story_id_from_parts(22, 9, "SSE Sidebar Tree Updates")
        assert result == "22-9-sse-sidebar-tree-updates"

    def test_story_id_from_parts_slugification(self) -> None:
        """Test that title is properly slugified."""
        assert story_id_from_parts(1, 1, "Test Title!") == "1-1-test-title"
        assert story_id_from_parts(1, 2, "Multiple   Spaces") == "1-2-multiple-spaces"
        assert story_id_from_parts(1, 3, "under_scores") == "1-3-under-scores"

    def test_story_id_from_parts_special_chars(self) -> None:
        """Test that special characters are removed."""
        result = story_id_from_parts(1, 1, "Title: With @ Special # Chars!")
        assert "@" not in result
        assert "#" not in result
        assert "!" not in result


class TestGenerateRunId:
    """Tests for generate_run_id function."""

    def test_generate_run_id_format(self) -> None:
        """Test that generated run_id matches required format."""
        run_id = generate_run_id()

        import re

        pattern = r"^run-(\d{8})-(\d{6})-([a-z0-9]{8})$"
        match = re.match(pattern, run_id)
        assert match is not None

    def test_generate_run_id_unique(self) -> None:
        """Test that each generated run_id is unique."""
        run_ids = [generate_run_id() for _ in range(50)]
        assert len(set(run_ids)) == 50

    def test_generate_run_id_timestamp_valid(self) -> None:
        """Test that timestamp part of run_id is valid."""
        run_id = generate_run_id()

        # Extract timestamp: run-YYYYMMDD-HHMMSS-{uuid8}
        parts = run_id.split("-")
        timestamp_str = f"{parts[1]}-{parts[2]}"

        # Verify it can be parsed as datetime
        datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S")


class TestEmitValidatorProgress:
    """Tests for emit_validator_progress function (Story 22.11)."""

    def test_emit_validator_progress_prints_marker(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that emit_validator_progress prints DASHBOARD_EVENT marker."""
        emit_validator_progress(
            run_id="run-20260115-080000-a1b2c3d4",
            sequence_id=5,
            validator_id="validator-a",
            status="completed",
            duration_ms=45000,
        )

        captured = capsys.readouterr()
        assert captured.out.startswith(DASHBOARD_EVENT_MARKER)

        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        assert data["type"] == "validator_progress"
        assert data["data"]["validator_id"] == "validator-a"
        assert data["data"]["status"] == "completed"
        assert data["data"]["duration_ms"] == 45000

    def test_emit_validator_progress_timeout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test emit_validator_progress with timeout status."""
        emit_validator_progress(
            run_id="run-20260115-080000-a1b2c3d4",
            sequence_id=6,
            validator_id="validator-b",
            status="timeout",
            duration_ms=300000,
        )

        captured = capsys.readouterr()
        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        assert data["data"]["status"] == "timeout"

    def test_emit_validator_progress_no_duration(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test emit_validator_progress without duration_ms."""
        emit_validator_progress(
            run_id="run-20260115-080000-a1b2c3d4",
            sequence_id=7,
            validator_id="validator-c",
            status="failed",
        )

        captured = capsys.readouterr()
        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        assert data["data"]["status"] == "failed"
        assert data["data"]["duration_ms"] is None


class TestEmitPhaseComplete:
    """Tests for emit_phase_complete function (Story 22.11)."""

    def test_emit_phase_complete_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test emit_phase_complete with successful phase."""
        emit_phase_complete(
            run_id="run-20260115-080000-a1b2c3d4",
            sequence_id=10,
            phase_name="VALIDATE_STORY",
            success=True,
            validator_count=6,
            failed_count=0,
        )

        captured = capsys.readouterr()
        assert captured.out.startswith(DASHBOARD_EVENT_MARKER)

        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        assert data["type"] == "phase_complete"
        assert data["data"]["phase_name"] == "VALIDATE_STORY"
        assert data["data"]["success"] is True
        assert data["data"]["validator_count"] == 6
        assert data["data"]["failed_count"] == 0

    def test_emit_phase_complete_with_failures(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test emit_phase_complete with some failed validators."""
        emit_phase_complete(
            run_id="run-20260115-080000-a1b2c3d4",
            sequence_id=11,
            phase_name="VALIDATE_STORY",
            success=False,
            validator_count=6,
            failed_count=2,
        )

        captured = capsys.readouterr()
        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        assert data["data"]["success"] is False
        assert data["data"]["failed_count"] == 2

    def test_emit_phase_complete_includes_timestamp(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that phase_complete event includes ISO 8601 timestamp."""
        emit_phase_complete(
            run_id="run-20260115-080000-a1b2c3d4",
            sequence_id=12,
            phase_name="CODE_REVIEW",
            success=True,
            validator_count=3,
            failed_count=0,
        )

        captured = capsys.readouterr()
        json_str = captured.out[len(DASHBOARD_EVENT_MARKER) :].strip()
        data = json.loads(json_str)

        # Verify timestamp is present and valid ISO 8601
        assert "timestamp" in data
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
