"""QA_PLAN_GENERATE phase handler.

Generates E2E test plans for completed epics using the qa/generator module.

This handler wraps the standalone generate_qa_plan() function which:
- Loads epic context (epic file, stories, trace, UX elements)
- Calls LLM with embedded prompt to generate test plan
- Saves plan to _bmad-output/implementation-artifacts/qa-plans/

Unlike BaseHandler, this doesn't use prompt templates - it calls the
qa/generator.py function directly with config and project_path.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from bmad_assist.core.loop.handlers.base import BaseHandler
from bmad_assist.core.loop.types import PhaseResult
from bmad_assist.core.state import State
from bmad_assist.qa.generator import QAPlanResult, generate_qa_plan

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class QaPlanGenerateHandler(BaseHandler):
    """Handler for QA_PLAN_GENERATE phase.

    Generates E2E test plans for completed epics.
    Wraps the standalone generate_qa_plan() function from qa/generator.py.

    This phase runs after RETROSPECTIVE completes for an epic.
    """

    @property
    def phase_name(self) -> str:
        """Return the phase name."""
        return "qa_plan_generate"

    def build_context(self, state: State) -> dict[str, Any]:
        """Build context for qa-plan-generate.

        Not used for this handler - generate_qa_plan() takes
        config and project_path directly, not a rendered prompt.

        Args:
            state: Current loop state.

        Returns:
            Empty dict (not used).

        """
        return {}

    def execute(self, state: State) -> PhaseResult:
        """Execute QA plan generation.

        Overrides BaseHandler.execute() to call generate_qa_plan() directly
        instead of rendering prompts and invoking providers.

        Args:
            state: Current loop state with epic information.

        Returns:
            PhaseResult with success status and QA plan path in outputs.

        """
        # Guard: epic must be set
        if state.current_epic is None:
            return PhaseResult.fail("Cannot generate QA plan: no current epic set")

        epic_id = state.current_epic

        logger.info("Generating QA plan for epic %s...", epic_id)

        try:
            # Call generate_qa_plan() from qa/generator module
            # This function handles:
            # - Checking if plan already exists (skip if so)
            # - Loading epic context
            # - Invoking LLM with embedded prompt
            # - Saving plan to qa-plans/ directory
            result: QAPlanResult = generate_qa_plan(
                config=self.config,
                project_path=self.project_path,
                epic_id=epic_id,
                force=False,  # Don't regenerate if exists
            )

            # Handle result
            if not result.success:
                error_msg = result.error or "Unknown error"
                logger.error("QA plan generation failed for epic %s: %s", epic_id, error_msg)
                return PhaseResult.fail(f"QA plan generation failed: {error_msg}")

            # Build outputs with QA plan path
            outputs = {
                "epic_id": epic_id,
                "qa_plan_path": str(result.qa_plan_path) if result.qa_plan_path else None,
                "skipped": result.skipped,
            }

            if result.trace_path:
                outputs["trace_path"] = str(result.trace_path)

            if result.skipped:
                logger.info(
                    "QA plan already exists for epic %s, skipped: %s",
                    epic_id,
                    result.qa_plan_path,
                )
            else:
                logger.info(
                    "QA plan generated for epic %s: %s",
                    epic_id,
                    result.qa_plan_path,
                )

            return PhaseResult.ok(outputs)

        except Exception as e:
            logger.error(
                "QA plan generation failed for epic %s: %s",
                epic_id,
                e,
                exc_info=True,
            )
            return PhaseResult.fail(f"QA plan generation error: {e}")
