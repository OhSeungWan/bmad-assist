"""Tests for guardian module.

Story 6.5: Main Loop Runner - Guardian functionality
- get_next_phase()
- guardian_check_anomaly()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass


class TestGetNextPhase:
    """AC7: get_next_phase() returns next phase in PHASE_ORDER."""

    def test_get_next_phase_returns_next_for_create_story(self) -> None:
        """AC7: CREATE_STORY -> VALIDATE_STORY."""
        from bmad_assist.core.loop import Phase, get_next_phase

        result = get_next_phase(Phase.CREATE_STORY)
        assert result == Phase.VALIDATE_STORY

    def test_get_next_phase_returns_next_for_dev_story(self) -> None:
        """AC7: DEV_STORY -> CODE_REVIEW."""
        from bmad_assist.core.loop import Phase, get_next_phase

        result = get_next_phase(Phase.DEV_STORY)
        assert result == Phase.CODE_REVIEW

    def test_get_next_phase_returns_next_for_code_review_synthesis(self) -> None:
        """AC7: CODE_REVIEW_SYNTHESIS -> TEST_REVIEW (with testarch) or RETROSPECTIVE (without)."""
        from unittest.mock import patch

        from bmad_assist.core.loop import Phase, get_next_phase

        # Without testarch: skip TEST_REVIEW
        result = get_next_phase(Phase.CODE_REVIEW_SYNTHESIS)
        assert result == Phase.RETROSPECTIVE

        # With testarch enabled: TEST_REVIEW is next
        with patch("bmad_assist.core.loop.guardian._is_testarch_enabled", return_value=True):
            result = get_next_phase(Phase.CODE_REVIEW_SYNTHESIS)
            assert result == Phase.TEST_REVIEW

    def test_get_next_phase_returns_none_for_retrospective(self) -> None:
        """AC7: RETROSPECTIVE returns None (last phase)."""
        from bmad_assist.core.loop import Phase, get_next_phase

        result = get_next_phase(Phase.RETROSPECTIVE)
        assert result is None

    def test_get_next_phase_all_phases_in_sequence(self, monkeypatch) -> None:
        """AC7: All phases advance correctly in PHASE_ORDER (with QA + testarch enabled)."""
        from unittest.mock import patch

        from bmad_assist.core.loop import PHASE_ORDER, Phase, get_next_phase

        # Enable QA phases for full PHASE_ORDER test
        monkeypatch.setenv("BMAD_QA_ENABLED", "1")

        # Enable testarch for ATDD and TEST_REVIEW phases
        with patch("bmad_assist.core.loop.guardian._is_testarch_enabled", return_value=True):
            for i, phase in enumerate(PHASE_ORDER[:-1]):  # Skip last (QA_PLAN_EXECUTE)
                expected = PHASE_ORDER[i + 1]
                assert get_next_phase(phase) == expected, f"Failed for {phase}"

    def test_get_next_phase_without_qa_stops_at_retrospective(self) -> None:
        """RETROSPECTIVE is last phase when QA is disabled (default)."""
        from bmad_assist.core.loop import Phase, get_next_phase

        # QA is disabled by default
        result = get_next_phase(Phase.RETROSPECTIVE)
        assert result is None

    def test_get_next_phase_skips_testarch_when_disabled(self) -> None:
        """ATDD and TEST_REVIEW are skipped when testarch is disabled."""
        from bmad_assist.core.loop import Phase, get_next_phase

        # Testarch is disabled by default (config.testarch is None)
        # VALIDATE_STORY_SYNTHESIS -> should skip ATDD -> DEV_STORY
        result = get_next_phase(Phase.VALIDATE_STORY_SYNTHESIS)
        assert result == Phase.DEV_STORY

        # CODE_REVIEW_SYNTHESIS -> should skip TEST_REVIEW -> RETROSPECTIVE
        result = get_next_phase(Phase.CODE_REVIEW_SYNTHESIS)
        assert result == Phase.RETROSPECTIVE


class TestGuardianCheckAnomaly:
    """AC5: guardian_check_anomaly() placeholder returns GuardianDecision.CONTINUE."""

    def test_guardian_halts_on_failure(self) -> None:
        """AC5: Guardian returns HALT on phase failure to prevent infinite loops."""
        from bmad_assist.core.loop import (
            GuardianDecision,
            PhaseResult,
            guardian_check_anomaly,
        )
        from bmad_assist.core.state import Phase, State

        result = PhaseResult.fail("Some error")
        state = State(current_phase=Phase.DEV_STORY, current_story="1.1")

        decision = guardian_check_anomaly(result, state)

        assert decision == GuardianDecision.HALT

    def test_guardian_continues_on_success(self) -> None:
        """AC5: Guardian returns CONTINUE on phase success."""
        from bmad_assist.core.loop import (
            GuardianDecision,
            PhaseResult,
            guardian_check_anomaly,
        )
        from bmad_assist.core.state import Phase, State

        result = PhaseResult.ok()
        state = State(current_phase=Phase.CREATE_STORY, current_story="1.1")

        decision = guardian_check_anomaly(result, state)

        assert decision == GuardianDecision.CONTINUE

    def test_guardian_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """AC5: Placeholder logs warning with phase, story, and error info."""
        from bmad_assist.core.loop import PhaseResult, guardian_check_anomaly
        from bmad_assist.core.state import Phase, State

        result = PhaseResult.fail("Test error message")
        state = State(current_phase=Phase.CODE_REVIEW, current_story="2.3")

        with caplog.at_level(logging.WARNING):
            guardian_check_anomaly(result, state)

        assert "CODE_REVIEW" in caplog.text
        assert "2.3" in caplog.text
        assert "Test error message" in caplog.text

    def test_guardian_handles_none_phase(self) -> None:
        """AC5: Guardian handles None current_phase gracefully (still halts on failure)."""
        from bmad_assist.core.loop import (
            GuardianDecision,
            PhaseResult,
            guardian_check_anomaly,
        )
        from bmad_assist.core.state import State

        result = PhaseResult.fail("Error")
        state = State(current_phase=None, current_story="1.1")

        decision = guardian_check_anomaly(result, state)

        # Should still halt on failure even with None phase
        assert decision == GuardianDecision.HALT
