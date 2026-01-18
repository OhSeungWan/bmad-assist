"""QA_PLAN_EXECUTE phase handler.

Executes E2E tests from generated QA plans using the qa/executor module.

This handler wraps the standalone execute_qa_plan() function which:
- Checks if QA plan exists
- Parses plan to count tests
- Chooses execution mode (single run vs batch)
- Executes tests and returns results

Unlike BaseHandler, this doesn't use prompt templates - it calls the
qa/executor.py function directly with config and project_path.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from bmad_assist.core.loop.handlers.base import BaseHandler
from bmad_assist.core.loop.types import PhaseResult
from bmad_assist.core.state import State
from bmad_assist.qa.executor import DEFAULT_BATCH_SIZE, QAExecuteResult, execute_qa_plan

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class QaPlanExecuteHandler(BaseHandler):
    """Handler for QA_PLAN_EXECUTE phase.

    Executes E2E tests for completed epics using generated QA plans.
    Wraps the standalone execute_qa_plan() function from qa/executor.py.

    This phase runs after QA_PLAN_GENERATE completes.
    """

    @property
    def phase_name(self) -> str:
        """Return the phase name."""
        return "qa_plan_execute"

    def build_context(self, state: State) -> dict[str, Any]:
        """Build context for qa-plan-execute.

        Not used for this handler - execute_qa_plan() takes
        config and project_path directly, not a rendered prompt.

        Args:
            state: Current loop state.

        Returns:
            Empty dict (not used).

        """
        return {}

    def execute(self, state: State) -> PhaseResult:
        """Execute QA plan execution.

        Overrides BaseHandler.execute() to call execute_qa_plan() directly
        instead of rendering prompts and invoking providers.

        Args:
            state: Current loop state with epic information.

        Returns:
            PhaseResult with success status and test execution summary.

        """
        # Guard: epic must be set
        if state.current_epic is None:
            return PhaseResult.fail("Cannot execute QA plan: no current epic set")

        epic_id = state.current_epic

        logger.info("Executing QA plan for epic %s...", epic_id)

        try:
            # Call execute_qa_plan() from qa/executor module
            # This function handles:
            # - Checking if QA plan exists
            # - Parsing plan to count tests
            # - Choosing execution mode (single run vs batch)
            # - Executing tests and returning results
            # Get category from state (default "A" for safety)
            # "A" = CLI/bash tests only (safe, no Playwright)
            # "all" = A + B (includes Playwright UI tests)
            category = getattr(state, "qa_category", "A")

            result: QAExecuteResult = execute_qa_plan(
                config=self.config,
                project_path=self.project_path,
                epic_id=epic_id,
                category=category,
                batch_size=DEFAULT_BATCH_SIZE,
                batch_mode=None,  # Auto-select based on test count
            )

            # Handle execution failure
            if not result.success:
                error_msg = result.error or "Unknown error"
                logger.error("QA execution failed for epic %s: %s", epic_id, error_msg)
                return PhaseResult.fail(f"QA execution failed: {error_msg}")

            # Build outputs with execution summary
            outputs = {
                "epic_id": epic_id,
                "tests_run": result.tests_run,
                "tests_passed": result.tests_passed,
                "tests_failed": result.tests_failed,
                "pass_rate": result.pass_rate,
                "batch_mode": result.batch_mode,
            }

            if result.results_path:
                outputs["results_path"] = str(result.results_path)

            if result.summary_path:
                outputs["summary_path"] = str(result.summary_path)

            if result.batch_mode:
                outputs["batches_completed"] = result.batches_completed

            # Log summary
            logger.info(
                "QA execution complete for epic %s: %d/%d passed (%.1f%%)%s",
                epic_id,
                result.tests_passed,
                result.tests_run,
                result.pass_rate,
                f" [batch mode: {result.batches_completed} batches]" if result.batch_mode else "",
            )

            return PhaseResult.ok(outputs)

        except Exception as e:
            logger.error(
                "QA execution failed for epic %s: %s",
                epic_id,
                e,
                exc_info=True,
            )
            return PhaseResult.fail(f"QA execution error: {e}")
