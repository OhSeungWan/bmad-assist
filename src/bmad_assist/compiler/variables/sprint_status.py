"""Sprint status resolution for BMAD workflow variables.

This module handles sprint-status.yaml resolution:
- Finding sprint-status.yaml in docs/ or docs/sprint-artifacts/
- Extracting story titles from sprint-status.yaml

Dependencies flow: sprint_status.py imports from shared_utils (outside variables/).
"""

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from bmad_assist.compiler.shared_utils import get_sprint_status_path
from bmad_assist.compiler.types import CompilerContext
from bmad_assist.core.exceptions import VariableError

logger = logging.getLogger(__name__)

__all__ = [
    "_resolve_sprint_status",
    "_extract_story_title",
]


def _resolve_sprint_status(
    resolved: dict[str, Any],
    context: CompilerContext,
) -> dict[str, Any]:
    """Resolve sprint_status variable to sprint-status.yaml path.

    Searches for sprint-status.yaml in two locations:
    - docs/sprint-status.yaml
    - docs/sprint-artifacts/sprint-status.yaml

    Rules:
    - If neither exists: set sprint_status to "none"
    - If both exist: raise VariableError (ambiguous)
    - If one exists: use that path

    Args:
        resolved: Dict of resolved variables.
        context: Compiler context with project_root.

    Returns:
        Dict with sprint_status resolved.

    Raises:
        VariableError: If sprint-status.yaml exists in both locations.

    """
    # Check new paths location first
    new_path = get_sprint_status_path(context)
    # Legacy fallback locations
    docs_path = context.project_root / "docs" / "sprint-status.yaml"
    legacy_artifacts_path = (
        context.project_root / "docs" / "sprint-artifacts" / "sprint-status.yaml"
    )

    # Deduplicate paths by resolving to absolute paths
    # (new_path may overlap with legacy_artifacts_path when paths singleton not initialized)
    seen_paths: set[str] = set()
    locations: list[tuple[Path, bool]] = []

    for p in [new_path, docs_path, legacy_artifacts_path]:
        resolved_str = str(p.resolve())
        if resolved_str not in seen_paths:
            seen_paths.add(resolved_str)
            locations.append((p, p.exists()))

    existing = [(p, e) for p, e in locations if e]

    if len(existing) > 1:
        raise VariableError(
            "Ambiguous sprint-status.yaml location\n"
            f"  Found in multiple locations: {[str(p) for p, _ in existing]}\n"
            "  Why it's a problem: Cannot determine which sprint-status.yaml to use\n"
            "  How to fix: Keep sprint-status.yaml in only one location",
            variable_name="sprint_status",
            sources_checked=[str(p) for p, _ in locations],
            suggestion="Keep sprint-status.yaml in only one location",
        )

    if existing:
        # Use the first (and only) existing path
        found_path = existing[0][0]
        resolved["sprint_status"] = str(found_path)
        logger.debug("Resolved sprint_status: %s", found_path)
    else:
        resolved["sprint_status"] = "none"
        logger.debug("No sprint-status.yaml found, set sprint_status to 'none'")

    return resolved


def _extract_story_title(
    sprint_status_path: Path,
    epic_num: int,
    story_num: int,
) -> str | None:
    """Extract story title from sprint-status.yaml.

    Looks for key matching pattern: {epic_num}-{story_num}-{title}
    in the development_status section.

    Args:
        sprint_status_path: Path to sprint-status.yaml.
        epic_num: Epic number to match.
        story_num: Story number to match.

    Returns:
        Extracted story title (kebab-case) or None if not found.

    """
    if not sprint_status_path.exists():
        logger.debug("Sprint status file not found: %s", sprint_status_path)
        return None

    try:
        content = sprint_status_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        if not isinstance(data, dict):
            logger.debug("Sprint status file is not a dict")
            return None

        development_status = data.get("development_status", {})
        if not isinstance(development_status, dict):
            logger.debug("development_status is not a dict")
            return None

        # Pattern: epic_num-story_num-title
        pattern = re.compile(rf"^{epic_num}-{story_num}-(.+)$")

        for key in development_status:
            match = pattern.match(str(key))
            if match:
                title = match.group(1)
                logger.debug("Extracted story_title from sprint-status: %s", title)
                return title

        logger.debug("No matching story key found for %s-%s", epic_num, story_num)
        return None

    except (OSError, yaml.YAMLError) as e:
        logger.debug("Error reading sprint-status.yaml: %s", e)
        return None
