"""State discrepancy detection for BMAD files.

This module provides functionality to detect discrepancies between internal
state tracked by bmad-assist and actual project state in BMAD files.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from bmad_assist.bmad.state_reader import ProjectState, _normalize_status

logger = logging.getLogger(__name__)


class StateComparable(Protocol):
    """Protocol for state objects that can be compared.

    This protocol defines the minimum interface required for state objects
    to be used with detect_discrepancies(). It enables decoupling from the
    concrete InternalState implementation (Epic 3) while allowing testing
    with mock objects.

    Attributes:
        current_epic: Current epic number, or None if all done.
        current_story: Current story number (e.g., "2.3"), or None if all done.
        completed_stories: List of completed story numbers.

    """

    current_epic: int | None
    current_story: str | None
    completed_stories: list[str]


@dataclass
class Discrepancy:
    """Represents a discrepancy between internal state and BMAD files.

    Attributes:
        type: Discrepancy type identifier (e.g., "story_status_mismatch").
        expected: Value from internal state.
        actual: Value from BMAD files.
        story_number: Affected story number, if applicable.
        file_path: Source file path, if applicable.
        description: Human-readable description of the discrepancy.

    """

    type: str
    expected: Any
    actual: Any
    story_number: str | None = None
    file_path: str | None = None
    description: str = ""

    def __str__(self) -> str:
        """Return human-readable description of the discrepancy."""
        if self.description:
            return self.description
        return f"{self.type}: expected={self.expected}, actual={self.actual}"


def _build_story_status_map(state: ProjectState) -> dict[str, tuple[str, str | None]]:
    """Build a map of story number to (status, file_path) from ProjectState.

    Args:
        state: ProjectState from BMAD files.

    Returns:
        Dict mapping story number to (status, file_path) tuple.

    """
    # Build reverse index: story_number -> epic_path in O(n) instead of O(n×m×k)
    story_to_epic: dict[str, str] = {}
    for epic in state.epics:
        for story in epic.stories:
            story_to_epic[story.number] = epic.path

    # Build status map in O(n)
    return {
        story.number: (_normalize_status(story.status), story_to_epic.get(story.number))
        for story in state.all_stories
    }


def detect_discrepancies(
    internal_state: StateComparable,
    bmad_state: ProjectState,
) -> list[Discrepancy]:
    """Detect discrepancies between internal state and BMAD files.

    Compares the internal state tracked by bmad-assist with the actual
    project state read from BMAD files, identifying any inconsistencies.

    Args:
        internal_state: Internal state from bmad-assist's state file.
            Must implement StateComparable protocol.
        bmad_state: Project state read from BMAD files via read_project_state().

    Returns:
        List of Discrepancy objects, empty if states match.
        Discrepancies are sorted by type, then story_number.

    Raises:
        TypeError: If internal_state or bmad_state is None.

    Examples:
        >>> from bmad_assist.bmad import read_project_state, detect_discrepancies
        >>> bmad_state = read_project_state("docs")
        >>> discrepancies = detect_discrepancies(internal_state, bmad_state)
        >>> for d in discrepancies:
        ...     print(d)

    """
    # Validate inputs (AC: TypeError for None)
    if internal_state is None:
        raise TypeError("internal_state must not be None")
    if bmad_state is None:
        raise TypeError("bmad_state must not be None")

    discrepancies: list[Discrepancy] = []

    # Build story status map from BMAD state for efficient lookups
    bmad_story_map = _build_story_status_map(bmad_state)
    bmad_story_numbers = set(bmad_story_map.keys())

    # Build set of internal stories (completed + current if not None)
    internal_story_numbers: set[str] = set(internal_state.completed_stories)
    if internal_state.current_story is not None:
        internal_story_numbers.add(internal_state.current_story)

    logger.info(
        "Comparing %d internal stories with %d BMAD stories",
        len(internal_story_numbers),
        len(bmad_story_numbers),
    )

    # AC8: Handle empty BMAD state
    if not bmad_state.all_stories and internal_state.completed_stories:
        discrepancies.append(
            Discrepancy(
                type="bmad_empty",
                expected=internal_state.completed_stories,
                actual=[],
                story_number=None,
                file_path=None,
                description=(
                    f"BMAD files contain no stories but internal state tracks "
                    f"{len(internal_state.completed_stories)} stories"
                ),
            )
        )
        # Sort and return early - no point comparing further
        discrepancies.sort(key=lambda d: (d.type, d.story_number or ""))
        return discrepancies

    # AC3: Compare current epic positions
    if internal_state.current_epic != bmad_state.current_epic:
        discrepancies.append(
            Discrepancy(
                type="current_epic_mismatch",
                expected=internal_state.current_epic,
                actual=bmad_state.current_epic,
                story_number=None,
                file_path=None,
                description=(
                    f"Current epic mismatch: internal={internal_state.current_epic}, "
                    f"bmad={bmad_state.current_epic}"
                ),
            )
        )

    # AC2: Compare current story positions
    if internal_state.current_story != bmad_state.current_story:
        discrepancies.append(
            Discrepancy(
                type="current_story_mismatch",
                expected=internal_state.current_story,
                actual=bmad_state.current_story,
                story_number=None,
                file_path=None,
                description=(
                    f"Current story mismatch: internal={internal_state.current_story}, "
                    f"bmad={bmad_state.current_story}"
                ),
            )
        )

    # AC4: Compare completed stories lists (order-independent)
    internal_set = set(internal_state.completed_stories)
    bmad_set = set(bmad_state.completed_stories)

    if internal_set != bmad_set:
        missing_from_internal = sorted(bmad_set - internal_set)
        missing_from_bmad = sorted(internal_set - bmad_set)

        discrepancies.append(
            Discrepancy(
                type="completed_stories_mismatch",
                expected=sorted(internal_state.completed_stories),
                actual=sorted(bmad_state.completed_stories),
                story_number=None,
                file_path=None,
                description=(
                    f"Completed stories mismatch: "
                    f"missing_from_internal={missing_from_internal}, "
                    f"missing_from_bmad={missing_from_bmad}"
                ),
            )
        )

    # AC1: Compare individual story statuses for stories in both states
    # We check stories that exist in completed list of internal state
    for story_num in internal_state.completed_stories:
        if story_num in bmad_story_map:
            bmad_status, file_path = bmad_story_map[story_num]
            # Internal says "done" (in completed_stories), check if BMAD agrees
            if bmad_status != "done":
                discrepancies.append(
                    Discrepancy(
                        type="story_status_mismatch",
                        expected="done",
                        actual=bmad_status,
                        story_number=story_num,
                        file_path=file_path,
                        description=(
                            f"Story {story_num} status mismatch: internal=done, bmad={bmad_status}"
                        ),
                    )
                )

    # Check current story status if internal has one
    if internal_state.current_story is not None:
        story_num = internal_state.current_story
        if story_num in bmad_story_map:
            bmad_status, file_path = bmad_story_map[story_num]
            # Internal says current (in-progress), BMAD says done
            if bmad_status == "done":
                discrepancies.append(
                    Discrepancy(
                        type="story_status_mismatch",
                        expected="in-progress",
                        actual="done",
                        story_number=story_num,
                        file_path=file_path,
                        description=(
                            f"Story {story_num} status mismatch: internal=in-progress, bmad=done"
                        ),
                    )
                )

    # AC10: Detect stories in internal state but not in BMAD files
    for story_num in internal_story_numbers:
        if story_num not in bmad_story_numbers:
            discrepancies.append(
                Discrepancy(
                    type="story_not_in_bmad",
                    expected=story_num,
                    actual=None,
                    story_number=story_num,
                    file_path=None,
                    description=(
                        f"Story {story_num} tracked in internal state but not found in BMAD files"
                    ),
                )
            )

    # AC11: Detect stories in BMAD files but not in internal state
    # Flag ALL stories in BMAD that aren't tracked internally, regardless of status
    for story_num in bmad_story_numbers:
        if story_num not in internal_story_numbers:
            bmad_status, file_path = bmad_story_map[story_num]
            discrepancies.append(
                Discrepancy(
                    type="story_not_in_internal",
                    expected=None,
                    actual=story_num,
                    story_number=story_num,
                    file_path=file_path,
                    description=(
                        f"Story {story_num} (status: {bmad_status}) found in BMAD files "
                        f"but not tracked in internal state"
                    ),
                )
            )

    # AC9: Sort discrepancies by type, then story_number for consistent ordering
    discrepancies.sort(key=lambda d: (d.type, d.story_number or ""))

    return discrepancies
