"""QA plan existence checker.

Story: Standalone QA Plan Workflow
Checks which completed epics are missing QA plans.
"""

from __future__ import annotations

import logging
from pathlib import Path

from bmad_assist.core.config import Config
from bmad_assist.core.state import State
from bmad_assist.core.types import EpicId

logger = logging.getLogger(__name__)


def get_qa_artifacts_path(config: Config, project_path: Path) -> Path:
    """Get resolved QA artifacts path from config.

    Args:
        config: Configuration instance.
        project_path: Project root directory.

    Returns:
        Resolved Path to QA artifacts folder.

    """
    if config.qa is not None:
        path_template = config.qa.qa_artifacts_path
    else:
        path_template = "{project-root}/_bmad-output/qa-artifacts"

    # Resolve {project-root} placeholder
    resolved = path_template.replace("{project-root}", str(project_path))
    return Path(resolved)


def get_qa_plan_path(
    config: Config,
    project_path: Path,
    epic_id: EpicId,
) -> Path:
    """Get path to QA plan file for an epic.

    Args:
        config: Configuration instance.
        project_path: Project root directory.
        epic_id: Epic identifier (int or str).

    Returns:
        Path to the QA plan markdown file.

    """
    qa_artifacts = get_qa_artifacts_path(config, project_path)
    return qa_artifacts / "test-plans" / f"epic-{epic_id}-e2e-plan.md"


def get_trace_path(
    config: Config,
    project_path: Path,
    epic_id: EpicId,
) -> Path:
    """Get path to epic-level traceability file.

    For epic-level QA, we aggregate story-level traces. This returns the
    path where the aggregated epic trace should be stored.

    Args:
        config: Configuration instance.
        project_path: Project root directory.
        epic_id: Epic identifier (int or str).

    Returns:
        Path to the epic traceability markdown file.

    """
    qa_artifacts = get_qa_artifacts_path(config, project_path)
    return qa_artifacts / "traceability" / f"epic-{epic_id}-trace.md"


def check_missing_qa_plans(
    state: State,
    config: Config,
    project_path: Path,
) -> list[EpicId]:
    """Find completed epics that don't have QA plans.

    Checks all epics in state.completed_epics and returns those
    that are missing QA plan files.

    Args:
        state: Current loop state with completed_epics list.
        config: Configuration instance.
        project_path: Project root directory.

    Returns:
        List of epic IDs that are completed but missing QA plans.
        Empty list if all completed epics have QA plans.

    Example:
        >>> missing = check_missing_qa_plans(state, config, project_path)
        >>> if missing:
        ...     print(f"Epics without QA plans: {missing}")

    """
    missing: list[EpicId] = []

    for epic_id in state.completed_epics:
        qa_plan_path = get_qa_plan_path(config, project_path, epic_id)

        if not qa_plan_path.exists():
            logger.debug("Epic %s missing QA plan: %s", epic_id, qa_plan_path)
            missing.append(epic_id)
        else:
            logger.debug("Epic %s has QA plan: %s", epic_id, qa_plan_path)

    if missing:
        logger.info(
            "Found %d completed epics without QA plans: %s",
            len(missing),
            missing,
        )
    else:
        logger.debug("All completed epics have QA plans")

    return missing


def is_qa_check_enabled(config: Config) -> bool:
    """Check if QA startup check is enabled in config.

    Args:
        config: Configuration instance.

    Returns:
        True if QA check on startup is enabled (default True).

    """
    if config.qa is None:
        return True  # Default enabled
    return config.qa.check_on_startup


def is_post_retro_qa_enabled(config: Config) -> bool:
    """Check if post-retrospective QA generation is enabled.

    Args:
        config: Configuration instance.

    Returns:
        True if QA generation after retro is enabled (default True).

    """
    if config.qa is None:
        return True  # Default enabled
    return config.qa.generate_after_retro
