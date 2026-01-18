"""Guardian phase progression and anomaly detection.

Story 6.5: Main loop runner helpers - get_next_phase, guardian_check_anomaly.

"""

import logging
import os

from bmad_assist.core.loop.types import GuardianDecision, PhaseResult
from bmad_assist.core.state import PHASE_ORDER, Phase, State

logger = logging.getLogger(__name__)


def _is_qa_enabled() -> bool:
    """Check if QA phases are enabled via --qa flag."""
    return os.environ.get("BMAD_QA_ENABLED") == "1"


def _is_testarch_enabled() -> bool:
    """Check if testarch phases (ATDD, TEST_REVIEW) are enabled.

    Testarch is enabled if config.testarch is not None.
    Uses get_config() singleton to check configuration.
    """
    try:
        from bmad_assist.core.config import get_config

        config = get_config()
        return config.testarch is not None
    except Exception:
        # Config not loaded yet or other error - default to disabled
        return False


# Testarch phases that should be skipped when testarch is disabled
TESTARCH_PHASES: frozenset[Phase] = frozenset({Phase.ATDD, Phase.TEST_REVIEW})


__all__ = [
    "get_next_phase",
    "guardian_check_anomaly",
]


# =============================================================================
# Story 6.5: Main Loop Runner Helpers
# =============================================================================


def get_next_phase(current_phase: Phase) -> Phase | None:
    """Get next phase in PHASE_ORDER sequence.

    Pure function that calculates the next phase without modifying state.
    - Testarch phases (ATDD, TEST_REVIEW) are skipped if config.testarch is None
    - QA phases (QA_PLAN_GENERATE, QA_PLAN_EXECUTE) are skipped unless
      the --qa flag is enabled (BMAD_QA_ENABLED=1)

    Args:
        current_phase: Current phase to advance from.

    Returns:
        Next phase in sequence, or None if current_phase is the last
        applicable phase or not found in PHASE_ORDER.

    Example:
        >>> get_next_phase(Phase.CREATE_STORY)
        <Phase.VALIDATE_STORY: 'validate_story'>
        >>> get_next_phase(Phase.RETROSPECTIVE)  # with --qa flag
        <Phase.QA_PLAN_GENERATE: 'qa_plan_generate'>
        >>> get_next_phase(Phase.RETROSPECTIVE)  # without --qa flag
        None
        >>> get_next_phase(Phase.QA_PLAN_EXECUTE)
        None

    """
    qa_enabled = _is_qa_enabled()
    testarch_enabled = _is_testarch_enabled()

    # Without --qa, RETROSPECTIVE is the last phase (skip QA phases)
    if not qa_enabled and current_phase == Phase.RETROSPECTIVE:
        logger.debug("QA phases disabled, RETROSPECTIVE is last phase")
        return None

    try:
        idx = PHASE_ORDER.index(current_phase)

        # Find next applicable phase (skip disabled phases)
        while idx + 1 < len(PHASE_ORDER):
            candidate = PHASE_ORDER[idx + 1]

            # Skip testarch phases if testarch is disabled
            if not testarch_enabled and candidate in TESTARCH_PHASES:
                logger.debug("Skipping %s (testarch disabled)", candidate.name)
                idx += 1
                continue

            return candidate

        return None  # No more phases
    except ValueError:
        return None  # Invalid phase


def guardian_check_anomaly(result: PhaseResult, state: State) -> GuardianDecision:
    """Check Guardian for anomaly detection (placeholder).

    MVP implementation that halts on phase failure to prevent infinite loops.
    Full Guardian implementation with anomaly detection, user intervention,
    and configurable retry policies will be added in Epic 8.

    Args:
        result: PhaseResult from execute_phase() (contains success flag, error, duration).
        state: Current State object (contains epic, story, phase position).

    Returns:
        GuardianDecision.CONTINUE - proceed to next phase (on success)
        GuardianDecision.HALT - stop loop for user intervention (on failure)

    Note:
        Full implementation in Epic 8. MVP halts on failure to prevent
        infinite retry loops when handlers are not yet implemented.

    """
    # MVP: Halt on failure to prevent infinite loops with placeholder handlers
    if not result.success:
        decision = GuardianDecision.HALT
        logger.warning(
            "Guardian: phase=%s story=%s FAILED - halting for user intervention. Error: %s",
            state.current_phase.name if state.current_phase else "None",
            state.current_story,
            result.error,
        )
    else:
        decision = GuardianDecision.CONTINUE
        logger.debug(
            "Guardian: phase=%s story=%s SUCCESS - continuing",
            state.current_phase.name if state.current_phase else "None",
            state.current_story,
        )
    return decision
