"""Tests for testarch preflight checker module.

Tests the PreflightChecker class that verifies test infrastructure exists
before ATDD workflows run, and tracks completion in project state.
"""

import logging
from datetime import datetime
from pathlib import Path

import pytest

from bmad_assist.core.exceptions import PreflightError
from bmad_assist.core.state import State
from bmad_assist.testarch.config import PreflightConfig
from bmad_assist.testarch.preflight import (
    PreflightChecker,
    PreflightResult,
    PreflightStatus,
)


class TestPreflightStatusEnum:
    """Tests for PreflightStatus enum (AC#2)."""

    def test_found_value(self) -> None:
        """Test FOUND status has correct value."""
        assert PreflightStatus.FOUND.value == "found"

    def test_not_found_value(self) -> None:
        """Test NOT_FOUND status has correct value."""
        assert PreflightStatus.NOT_FOUND.value == "not_found"

    def test_skipped_value(self) -> None:
        """Test SKIPPED status has correct value."""
        assert PreflightStatus.SKIPPED.value == "skipped"


class TestPreflightResultDataclass:
    """Tests for PreflightResult frozen dataclass (AC#2)."""

    def test_all_passed_all_found(self) -> None:
        """Test all_passed returns True when all statuses are FOUND."""
        result = PreflightResult(
            test_design=PreflightStatus.FOUND,
            framework=PreflightStatus.FOUND,
            ci=PreflightStatus.FOUND,
        )
        assert result.all_passed is True

    def test_all_passed_all_skipped(self) -> None:
        """Test all_passed returns True when all statuses are SKIPPED."""
        result = PreflightResult(
            test_design=PreflightStatus.SKIPPED,
            framework=PreflightStatus.SKIPPED,
            ci=PreflightStatus.SKIPPED,
        )
        assert result.all_passed is True

    def test_all_passed_mixed_found_skipped(self) -> None:
        """Test all_passed returns True when mix of FOUND and SKIPPED."""
        result = PreflightResult(
            test_design=PreflightStatus.FOUND,
            framework=PreflightStatus.SKIPPED,
            ci=PreflightStatus.FOUND,
        )
        assert result.all_passed is True

    def test_all_passed_one_not_found(self) -> None:
        """Test all_passed returns False when any status is NOT_FOUND."""
        result = PreflightResult(
            test_design=PreflightStatus.FOUND,
            framework=PreflightStatus.NOT_FOUND,
            ci=PreflightStatus.FOUND,
        )
        assert result.all_passed is False

    def test_all_passed_all_not_found(self) -> None:
        """Test all_passed returns False when all statuses are NOT_FOUND."""
        result = PreflightResult(
            test_design=PreflightStatus.NOT_FOUND,
            framework=PreflightStatus.NOT_FOUND,
            ci=PreflightStatus.NOT_FOUND,
        )
        assert result.all_passed is False

    def test_warnings_default_empty(self) -> None:
        """Test warnings defaults to empty tuple."""
        result = PreflightResult(
            test_design=PreflightStatus.FOUND,
            framework=PreflightStatus.FOUND,
            ci=PreflightStatus.FOUND,
        )
        assert result.warnings == ()

    def test_warnings_preserved(self) -> None:
        """Test warnings are preserved in result."""
        result = PreflightResult(
            test_design=PreflightStatus.NOT_FOUND,
            framework=PreflightStatus.FOUND,
            ci=PreflightStatus.FOUND,
            warnings=("Test design not found.",),
        )
        assert result.warnings == ("Test design not found.",)

    def test_frozen_immutable(self) -> None:
        """Test result is frozen/immutable."""
        result = PreflightResult(
            test_design=PreflightStatus.FOUND,
            framework=PreflightStatus.FOUND,
            ci=PreflightStatus.FOUND,
        )
        with pytest.raises(AttributeError):
            result.test_design = PreflightStatus.NOT_FOUND  # type: ignore[misc]


class TestCheckTestDesign:
    """Tests for test design check (AC#3)."""

    def test_check_test_design_found(self, tmp_path: Path) -> None:
        """Test FOUND when test-design doc exists."""
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "test-design-system.md").write_text("# Test Design")

        config = PreflightConfig(test_design=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.test_design == PreflightStatus.FOUND

    def test_check_test_design_found_testability(self, tmp_path: Path) -> None:
        """Test FOUND when testability doc exists."""
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "testability-review.md").write_text("# Testability")

        config = PreflightConfig(test_design=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.test_design == PreflightStatus.FOUND

    def test_check_test_design_not_found(self, tmp_path: Path) -> None:
        """Test NOT_FOUND when no test design doc exists."""
        config = PreflightConfig(test_design=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.test_design == PreflightStatus.NOT_FOUND

    def test_check_test_design_skipped(self, tmp_path: Path) -> None:
        """Test SKIPPED when check is disabled."""
        config = PreflightConfig(test_design=False)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.test_design == PreflightStatus.SKIPPED


class TestCheckFramework:
    """Tests for test framework check (AC#4)."""

    def test_check_framework_playwright_ts(self, tmp_path: Path) -> None:
        """Test FOUND when playwright.config.ts exists."""
        (tmp_path / "playwright.config.ts").write_text("export default {}")

        config = PreflightConfig(framework=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.framework == PreflightStatus.FOUND

    def test_check_framework_playwright_js(self, tmp_path: Path) -> None:
        """Test FOUND when playwright.config.js exists."""
        (tmp_path / "playwright.config.js").write_text("module.exports = {}")

        config = PreflightConfig(framework=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.framework == PreflightStatus.FOUND

    def test_check_framework_cypress_ts(self, tmp_path: Path) -> None:
        """Test FOUND when cypress.config.ts exists."""
        (tmp_path / "cypress.config.ts").write_text("export default {}")

        config = PreflightConfig(framework=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.framework == PreflightStatus.FOUND

    def test_check_framework_cypress_js(self, tmp_path: Path) -> None:
        """Test FOUND when cypress.config.js exists."""
        (tmp_path / "cypress.config.js").write_text("module.exports = {}")

        config = PreflightConfig(framework=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.framework == PreflightStatus.FOUND

    def test_check_framework_cypress_mjs(self, tmp_path: Path) -> None:
        """Test FOUND when cypress.config.mjs exists."""
        (tmp_path / "cypress.config.mjs").write_text("export default {}")

        config = PreflightConfig(framework=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.framework == PreflightStatus.FOUND

    def test_check_framework_not_found(self, tmp_path: Path) -> None:
        """Test NOT_FOUND when no framework config exists."""
        config = PreflightConfig(framework=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.framework == PreflightStatus.NOT_FOUND

    def test_check_framework_skipped(self, tmp_path: Path) -> None:
        """Test SKIPPED when check is disabled."""
        config = PreflightConfig(framework=False)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.framework == PreflightStatus.SKIPPED


class TestCheckCI:
    """Tests for CI pipeline check (AC#5)."""

    def test_check_ci_github_actions_test_yml(self, tmp_path: Path) -> None:
        """Test FOUND when .github/workflows/test.yml exists."""
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "test.yml").write_text("name: Test")

        config = PreflightConfig(ci=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.ci == PreflightStatus.FOUND

    def test_check_ci_github_actions_test_yaml(self, tmp_path: Path) -> None:
        """Test FOUND when .github/workflows/test.yaml exists."""
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "test.yaml").write_text("name: Test")

        config = PreflightConfig(ci=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.ci == PreflightStatus.FOUND

    def test_check_ci_github_actions_ci_yml(self, tmp_path: Path) -> None:
        """Test FOUND when .github/workflows/ci.yml exists."""
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI")

        config = PreflightConfig(ci=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.ci == PreflightStatus.FOUND

    def test_check_ci_github_actions_ci_yaml(self, tmp_path: Path) -> None:
        """Test FOUND when .github/workflows/ci.yaml exists."""
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yaml").write_text("name: CI")

        config = PreflightConfig(ci=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.ci == PreflightStatus.FOUND

    def test_check_ci_gitlab(self, tmp_path: Path) -> None:
        """Test FOUND when .gitlab-ci.yml exists."""
        (tmp_path / ".gitlab-ci.yml").write_text("stages: []")

        config = PreflightConfig(ci=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.ci == PreflightStatus.FOUND

    def test_check_ci_azure(self, tmp_path: Path) -> None:
        """Test FOUND when azure-pipelines.yml exists."""
        (tmp_path / "azure-pipelines.yml").write_text("trigger: []")

        config = PreflightConfig(ci=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.ci == PreflightStatus.FOUND

    def test_check_ci_circleci(self, tmp_path: Path) -> None:
        """Test FOUND when .circleci/config.yml exists."""
        circleci = tmp_path / ".circleci"
        circleci.mkdir()
        (circleci / "config.yml").write_text("version: 2.1")

        config = PreflightConfig(ci=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.ci == PreflightStatus.FOUND

    def test_check_ci_not_found(self, tmp_path: Path) -> None:
        """Test NOT_FOUND when no CI config exists."""
        config = PreflightConfig(ci=True)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.ci == PreflightStatus.NOT_FOUND

    def test_check_ci_skipped(self, tmp_path: Path) -> None:
        """Test SKIPPED when check is disabled."""
        config = PreflightConfig(ci=False)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.ci == PreflightStatus.SKIPPED


class TestWarningGeneration:
    """Tests for warning generation (AC#8)."""

    def test_warning_generation_test_design_not_found(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test warning generated when test design NOT_FOUND."""
        config = PreflightConfig(test_design=True, framework=False, ci=False)
        checker = PreflightChecker(config, tmp_path)

        with caplog.at_level(logging.WARNING):
            result = checker.check()

        assert result.test_design == PreflightStatus.NOT_FOUND
        assert len(result.warnings) == 1
        assert "Test design document not found" in result.warnings[0]
        assert "testarch-test-design workflow" in result.warnings[0]
        assert "Test design document not found" in caplog.text

    def test_warning_generation_framework_not_found(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test warning generated when framework NOT_FOUND."""
        config = PreflightConfig(test_design=False, framework=True, ci=False)
        checker = PreflightChecker(config, tmp_path)

        with caplog.at_level(logging.WARNING):
            result = checker.check()

        assert result.framework == PreflightStatus.NOT_FOUND
        assert len(result.warnings) == 1
        assert "Test framework config not found" in result.warnings[0]
        assert "testarch-framework workflow" in result.warnings[0]

    def test_warning_generation_ci_not_found(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test warning generated when CI NOT_FOUND."""
        config = PreflightConfig(test_design=False, framework=False, ci=True)
        checker = PreflightChecker(config, tmp_path)

        with caplog.at_level(logging.WARNING):
            result = checker.check()

        assert result.ci == PreflightStatus.NOT_FOUND
        assert len(result.warnings) == 1
        assert "CI pipeline config not found" in result.warnings[0]
        assert "testarch-ci workflow" in result.warnings[0]

    def test_warning_generation_multiple_not_found(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test multiple warnings generated when multiple NOT_FOUND."""
        config = PreflightConfig(test_design=True, framework=True, ci=True)
        checker = PreflightChecker(config, tmp_path)

        with caplog.at_level(logging.WARNING):
            result = checker.check()

        assert len(result.warnings) == 3
        assert result.all_passed is False

    def test_no_warnings_when_all_found(self, tmp_path: Path) -> None:
        """Test no warnings generated when all checks pass."""
        # Set up all infrastructure
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "test-design.md").write_text("# Test Design")
        (tmp_path / "playwright.config.ts").write_text("export default {}")
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "test.yml").write_text("name: Test")

        config = PreflightConfig()
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.warnings == ()
        assert result.all_passed is True


class TestShouldRun:
    """Tests for should_run logic (AC#7)."""

    def test_should_run_true_no_preflight(self) -> None:
        """Test should_run returns True when no prior preflight."""
        state = State()
        assert PreflightChecker.should_run(state) is True

    def test_should_run_false_after_completion(self) -> None:
        """Test should_run returns False after preflight completed."""
        from bmad_assist.core.state import PreflightStateEntry

        state = State(
            testarch_preflight=PreflightStateEntry(
                completed_at=datetime(2026, 1, 4, 12, 0, 0),
                test_design="found",
                framework="found",
                ci="found",
            )
        )
        assert PreflightChecker.should_run(state) is False


class TestMarkCompleted:
    """Tests for mark_completed logic (AC#7)."""

    def test_mark_completed_populates_state(self) -> None:
        """Test mark_completed populates state with result values."""
        state = State()
        result = PreflightResult(
            test_design=PreflightStatus.FOUND,
            framework=PreflightStatus.NOT_FOUND,
            ci=PreflightStatus.SKIPPED,
        )

        PreflightChecker.mark_completed(state, result)

        assert state.testarch_preflight is not None
        assert state.testarch_preflight.test_design == "found"
        assert state.testarch_preflight.framework == "not_found"
        assert state.testarch_preflight.ci == "skipped"
        assert state.testarch_preflight.completed_at is not None

    def test_mark_completed_sets_timestamp(self) -> None:
        """Test mark_completed sets completed_at timestamp."""
        from datetime import UTC

        state = State()
        result = PreflightResult(
            test_design=PreflightStatus.FOUND,
            framework=PreflightStatus.FOUND,
            ci=PreflightStatus.FOUND,
        )

        before = datetime.now(UTC).replace(tzinfo=None)
        PreflightChecker.mark_completed(state, result)
        after = datetime.now(UTC).replace(tzinfo=None)

        assert state.testarch_preflight is not None
        assert before <= state.testarch_preflight.completed_at <= after

    def test_mark_completed_updates_state_updated_at(self) -> None:
        """Test mark_completed sets state.updated_at timestamp."""
        from datetime import UTC

        state = State()
        assert state.updated_at is None  # Initially None

        result = PreflightResult(
            test_design=PreflightStatus.FOUND,
            framework=PreflightStatus.FOUND,
            ci=PreflightStatus.FOUND,
        )

        before = datetime.now(UTC).replace(tzinfo=None)
        PreflightChecker.mark_completed(state, result)
        after = datetime.now(UTC).replace(tzinfo=None)

        assert state.updated_at is not None
        assert before <= state.updated_at <= after
        # Ensure updated_at matches preflight.completed_at
        assert state.testarch_preflight is not None
        assert state.updated_at == state.testarch_preflight.completed_at


class TestEdgeCases:
    """Tests for edge cases (AC#9)."""

    def test_invalid_project_root_not_exists(self, tmp_path: Path) -> None:
        """Test PreflightError raised when project_root doesn't exist."""
        non_existent = tmp_path / "nonexistent"
        config = PreflightConfig()

        with pytest.raises(PreflightError) as exc_info:
            PreflightChecker(config, non_existent)

        assert "does not exist" in str(exc_info.value)

    def test_invalid_project_root_is_file(self, tmp_path: Path) -> None:
        """Test PreflightError raised when project_root is a file."""
        file_path = tmp_path / "somefile.txt"
        file_path.write_text("content")
        config = PreflightConfig()

        with pytest.raises(PreflightError) as exc_info:
            PreflightChecker(config, file_path)

        assert "not a directory" in str(exc_info.value)

    def test_all_checks_disabled(self, tmp_path: Path) -> None:
        """Test all SKIPPED when all checks disabled, all_passed=True, empty warnings."""
        config = PreflightConfig(test_design=False, framework=False, ci=False)
        checker = PreflightChecker(config, tmp_path)
        result = checker.check()

        assert result.test_design == PreflightStatus.SKIPPED
        assert result.framework == PreflightStatus.SKIPPED
        assert result.ci == PreflightStatus.SKIPPED
        assert result.all_passed is True
        assert result.warnings == ()


class TestAllPassedLogic:
    """Tests specifically for all_passed property (AC#10)."""

    def test_all_passed_true_scenarios(self) -> None:
        """Test all_passed is True for valid scenarios."""
        # All FOUND
        assert (
            PreflightResult(
                PreflightStatus.FOUND, PreflightStatus.FOUND, PreflightStatus.FOUND
            ).all_passed
            is True
        )

        # All SKIPPED
        assert (
            PreflightResult(
                PreflightStatus.SKIPPED, PreflightStatus.SKIPPED, PreflightStatus.SKIPPED
            ).all_passed
            is True
        )

        # Mixed FOUND/SKIPPED
        assert (
            PreflightResult(
                PreflightStatus.FOUND, PreflightStatus.SKIPPED, PreflightStatus.FOUND
            ).all_passed
            is True
        )

    def test_all_passed_false_scenarios(self) -> None:
        """Test all_passed is False when NOT_FOUND present."""
        assert (
            PreflightResult(
                PreflightStatus.NOT_FOUND, PreflightStatus.FOUND, PreflightStatus.FOUND
            ).all_passed
            is False
        )

        assert (
            PreflightResult(
                PreflightStatus.FOUND, PreflightStatus.NOT_FOUND, PreflightStatus.SKIPPED
            ).all_passed
            is False
        )

        assert (
            PreflightResult(
                PreflightStatus.NOT_FOUND, PreflightStatus.NOT_FOUND, PreflightStatus.NOT_FOUND
            ).all_passed
            is False
        )
