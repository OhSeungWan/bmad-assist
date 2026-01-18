"""RETROSPECTIVE phase handler.

Runs epic retrospective after the last story completes.
Integrates with testarch trace handler when enabled.

Bug Fix: Retrospective Report Persistence
- Extracts report from LLM output using markers
- Saves report to retrospectives directory

"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bmad_assist.core.loop.handlers.base import BaseHandler
from bmad_assist.core.loop.types import PhaseResult
from bmad_assist.core.paths import get_paths
from bmad_assist.core.state import State
from bmad_assist.retrospective import extract_retrospective_report, save_retrospective_report

if TYPE_CHECKING:
    from bmad_assist.core.config import Config

logger = logging.getLogger(__name__)


class RetrospectiveHandler(BaseHandler):
    """Handler for RETROSPECTIVE phase.

    Invokes Master LLM to conduct epic retrospective.
    When testarch is configured, runs trace handler first to generate
    traceability matrices and quality gate decisions.

    """

    def __init__(self, config: Config, project_path: Path) -> None:
        """Initialize handler with trace result storage.

        Args:
            config: Application configuration.
            project_path: Path to project root.

        """
        super().__init__(config, project_path)
        self._trace_result: PhaseResult | None = None

    @property
    def phase_name(self) -> str:
        """Returns the name of the phase."""
        return "retrospective"

    def build_context(self, state: State) -> dict[str, Any]:
        """Build context for retrospective prompt template.

        Includes trace results if available (gate decision, trace file path).

        Args:
            state: Current loop state.

        Returns:
            Context dict with common variables plus trace results if available.

        """
        context = self._build_common_context(state)

        # Include trace results in context (AC #7)
        if self._trace_result and self._trace_result.success:
            outputs = self._trace_result.outputs
            if not outputs.get("skipped"):
                context["trace_gate_decision"] = outputs.get("gate_decision")
                context["trace_file"] = outputs.get("trace_file")
                context["trace_response"] = outputs.get("response")

        return context

    def _run_trace_if_enabled(self, state: State) -> PhaseResult | None:
        """Run trace handler if testarch configured.

        Non-blocking: handles both exceptions and PhaseResult.fail().
        Uses lazy import to avoid core→testarch coupling.

        Args:
            state: Current loop state.

        Returns:
            PhaseResult from trace handler if successful, None otherwise.

        """
        try:
            # Lazy import to avoid core→testarch coupling
            from bmad_assist.testarch.handlers import TraceHandler

            handler = TraceHandler(self.config, self.project_path)
            result = handler.run(state)

            # Handle PhaseResult.fail() - non-blocking
            if not result.success:
                logger.warning(
                    "Trace failed (continuing retrospective): %s",
                    result.error or "unknown error",
                )
                return None

            return result

        except ImportError:
            # testarch module not installed - skip silently
            logger.debug("Trace skipped: testarch module not available")
            return None
        except Exception as e:
            # Any other error - log warning, continue retrospective
            logger.warning("Trace failed (continuing retrospective): %s", e)
            return None

    def execute(self, state: State) -> PhaseResult:
        """Execute the retrospective handler.

        First runs trace handler (non-blocking), then proceeds with
        the retrospective workflow. After successful execution, extracts
        and saves the retrospective report.

        Trace results are passed to the retrospective context via build_context().

        Note: Trace execution time is not included in timing tracking.
        This is intentional - trace is a pre-step, not part of the
        retrospective workflow itself.

        Args:
            state: Current loop state.

        Returns:
            PhaseResult from retrospective execution, with report_file in outputs.

        """
        # Run trace before retrospective (non-blocking)
        # Store result for build_context() to include in prompt (AC #7)
        self._trace_result = self._run_trace_if_enabled(state)

        # Log trace results
        if self._trace_result and self._trace_result.success:
            outputs = self._trace_result.outputs
            if not outputs.get("skipped"):
                logger.info(
                    "Trace completed: gate_decision=%s, trace_file=%s",
                    outputs.get("gate_decision"),
                    outputs.get("trace_file"),
                )

        # Run parent's execute() for actual retrospective
        # build_context() will include trace results in prompt
        result = super().execute(state)

        # Extract and save retrospective report if successful
        if result.success and state.current_epic is not None:
            self._save_retrospective_report(result, state)

        return result

    def _save_retrospective_report(self, result: PhaseResult, state: State) -> None:
        """Extract and save retrospective report from LLM output.

        Bug Fix: Retrospective Report Persistence (AC #3)

        Args:
            result: Successful PhaseResult with response in outputs.
            state: Current loop state with epic information.

        """
        try:
            raw_output = result.outputs.get("response", "")
            if not raw_output:
                logger.warning("No response in retrospective result, skipping save")
                return

            # Extract report using markers or fallback heuristics
            report_content = extract_retrospective_report(raw_output)

            # Get retrospectives directory from project paths
            paths = get_paths()
            retrospectives_dir = paths.retrospectives_dir

            # Save report
            # Note: state.current_epic is guaranteed non-None by the caller's guard
            assert state.current_epic is not None  # Type narrowing for mypy
            timestamp = datetime.now(UTC)
            report_path = save_retrospective_report(
                content=report_content,
                epic_id=state.current_epic,
                retrospectives_dir=retrospectives_dir,
                timestamp=timestamp,
            )

            # Add report path to result outputs
            # Note: PhaseResult is frozen=True, but outputs dict is intentionally
            # mutable to allow handlers to enrich results without recreating the
            # entire dataclass. This is a deliberate design choice - see types.py.
            result.outputs["report_file"] = str(report_path)

            logger.info("Retrospective report saved: %s", report_path)

        except Exception as e:
            # Non-blocking: log error but don't fail the retrospective
            # AC #5: graceful degradation
            logger.error(
                "Failed to save retrospective report for epic %s: %s",
                state.current_epic,
                e,
                exc_info=True,  # Include traceback for debugging
            )
