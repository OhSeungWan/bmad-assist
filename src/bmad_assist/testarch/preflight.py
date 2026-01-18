"""Preflight infrastructure checking for testarch module.

This module provides the PreflightChecker class that verifies test infrastructure
(test-design docs, framework config, CI pipeline) exists before ATDD workflows run.
Tracks completion in project state to ensure run-once behavior.

Usage:
    from bmad_assist.testarch.preflight import PreflightChecker, PreflightStatus
    from bmad_assist.testarch.config import PreflightConfig
    from pathlib import Path

    config = PreflightConfig()
    checker = PreflightChecker(config, Path("/path/to/project"))
    result = checker.check()

    if not result.all_passed:
        for warning in result.warnings:
            print(warning)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from bmad_assist.core.exceptions import PreflightError
from bmad_assist.core.state import PreflightStateEntry, State
from bmad_assist.testarch.config import PreflightConfig

__all__ = [
    "PreflightStatus",
    "PreflightResult",
    "PreflightChecker",
]

logger = logging.getLogger(__name__)


class PreflightStatus(Enum):
    """Status of a preflight infrastructure check.

    Attributes:
        FOUND: Required infrastructure was found.
        NOT_FOUND: Required infrastructure was not found.
        SKIPPED: Check was disabled in configuration.

    """

    FOUND = "found"
    NOT_FOUND = "not_found"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class PreflightResult:
    """Result of preflight infrastructure checks.

    Attributes:
        test_design: Status of test design document check.
        framework: Status of test framework config check.
        ci: Status of CI pipeline config check.
        warnings: Warning messages for NOT_FOUND checks.

    """

    test_design: PreflightStatus
    framework: PreflightStatus
    ci: PreflightStatus
    warnings: tuple[str, ...] = ()

    @property
    def all_passed(self) -> bool:
        """Check if all enabled checks passed (FOUND or SKIPPED).

        Returns:
            True if no check returned NOT_FOUND.

        """
        return all(
            status in (PreflightStatus.FOUND, PreflightStatus.SKIPPED)
            for status in (self.test_design, self.framework, self.ci)
        )


class PreflightChecker:
    """Preflight infrastructure checker for testarch module.

    Verifies test infrastructure exists before ATDD workflows run.
    Tracks completion in project state to ensure run-once behavior.

    Attributes:
        config: PreflightConfig controlling which checks are enabled.
        project_root: Path to project root directory.

    """

    # Test design document patterns (recursive glob)
    TEST_DESIGN_PATTERNS = ("**/test-design*.md", "**/testability*.md")

    # Framework config files (at project root only)
    PLAYWRIGHT_CONFIGS = ("playwright.config.ts", "playwright.config.js")
    CYPRESS_CONFIGS = (
        "cypress.config.ts",
        "cypress.config.js",
        "cypress.config.mjs",
    )

    # CI config patterns (relative to project root)
    CI_CONFIGS = (
        ".github/workflows/test.yml",
        ".github/workflows/test.yaml",
        ".github/workflows/ci.yml",
        ".github/workflows/ci.yaml",
        ".gitlab-ci.yml",
        "azure-pipelines.yml",
        ".circleci/config.yml",
    )

    def __init__(self, config: PreflightConfig, project_root: Path) -> None:
        """Initialize checker with config and project root.

        Args:
            config: PreflightConfig controlling enabled checks.
            project_root: Path to project root directory.

        Raises:
            PreflightError: If project_root doesn't exist or is not a directory.

        """
        if not project_root.exists():
            raise PreflightError(f"Project root does not exist: {project_root}")
        if not project_root.is_dir():
            raise PreflightError(f"Project root is not a directory: {project_root}")

        self.config = config
        self.project_root = project_root

    def _check_test_design(self) -> PreflightStatus:
        """Check for test design document.

        Returns:
            FOUND if test design doc exists, NOT_FOUND otherwise, SKIPPED if disabled.

        """
        if not self.config.test_design:
            return PreflightStatus.SKIPPED

        for pattern in self.TEST_DESIGN_PATTERNS:
            if list(self.project_root.glob(pattern)):
                return PreflightStatus.FOUND

        return PreflightStatus.NOT_FOUND

    def _check_framework(self) -> PreflightStatus:
        """Check for test framework configuration.

        Returns:
            FOUND if framework config exists, NOT_FOUND otherwise, SKIPPED if disabled.

        """
        if not self.config.framework:
            return PreflightStatus.SKIPPED

        for config_file in self.PLAYWRIGHT_CONFIGS + self.CYPRESS_CONFIGS:
            if (self.project_root / config_file).exists():
                return PreflightStatus.FOUND

        return PreflightStatus.NOT_FOUND

    def _check_ci(self) -> PreflightStatus:
        """Check for CI pipeline configuration.

        Returns:
            FOUND if CI config exists, NOT_FOUND otherwise, SKIPPED if disabled.

        """
        if not self.config.ci:
            return PreflightStatus.SKIPPED

        for config_path in self.CI_CONFIGS:
            if (self.project_root / config_path).exists():
                return PreflightStatus.FOUND

        return PreflightStatus.NOT_FOUND

    def _generate_warnings(
        self,
        test_design: PreflightStatus,
        framework: PreflightStatus,
        ci: PreflightStatus,
    ) -> tuple[str, ...]:
        """Generate warning messages for NOT_FOUND statuses.

        Args:
            test_design: Test design check status.
            framework: Framework check status.
            ci: CI check status.

        Returns:
            Tuple of warning messages for NOT_FOUND statuses.

        """
        warnings: list[str] = []

        if test_design == PreflightStatus.NOT_FOUND:
            msg = "Test design document not found. Consider running testarch-test-design workflow."
            logger.warning(msg)
            warnings.append(msg)

        if framework == PreflightStatus.NOT_FOUND:
            msg = "Test framework config not found. Consider running testarch-framework workflow."
            logger.warning(msg)
            warnings.append(msg)

        if ci == PreflightStatus.NOT_FOUND:
            msg = "CI pipeline config not found. Consider running testarch-ci workflow."
            logger.warning(msg)
            warnings.append(msg)

        return tuple(warnings)

    def check(self) -> PreflightResult:
        """Run all preflight checks.

        Returns:
            PreflightResult with status of each check and warnings.

        """
        test_design = self._check_test_design()
        framework = self._check_framework()
        ci = self._check_ci()

        warnings = self._generate_warnings(test_design, framework, ci)

        return PreflightResult(
            test_design=test_design,
            framework=framework,
            ci=ci,
            warnings=warnings,
        )

    @staticmethod
    def should_run(state: State) -> bool:
        """Check if preflight should run.

        Args:
            state: Current project state.

        Returns:
            True if preflight has not been run yet (state.testarch_preflight is None).

        """
        return state.testarch_preflight is None

    @staticmethod
    def mark_completed(state: State, result: PreflightResult) -> None:
        """Mark preflight as completed in state.

        Updates state.testarch_preflight with result values and
        sets state.updated_at to current UTC timestamp.

        Args:
            state: State to update.
            result: Preflight check result.

        """
        now = datetime.now(UTC).replace(tzinfo=None)
        state.testarch_preflight = PreflightStateEntry(
            completed_at=now,
            test_design=result.test_design.value,
            framework=result.framework.value,
            ci=result.ci.value,
        )
        state.updated_at = now
