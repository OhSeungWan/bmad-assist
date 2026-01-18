"""Core type definitions for bmad-assist.

This module provides type aliases and utilities for common types used
across the codebase, particularly for identifiers that can be either
numeric or string-based.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

# Epic ID can be int (1, 2, 3) or str ("testarch", "0a", "standalone")
# Used for: current_epic, epic_num, completed_epics, etc.
EpicId: TypeAlias = int | str

# Security level for config fields (Epic 17)
# - safe: Behavioral settings with no security implications
# - risky: Settings that could break workflows if misconfigured
# - dangerous: Settings that could expose secrets (excluded from schema)
SecurityLevel: TypeAlias = Literal["safe", "risky", "dangerous"]

# UI widget type for config fields (Epic 17)
# - checkbox_group: for list[str] with predefined options
# - toggle: for boolean fields
# - number: for int/float with optional min/max
# - dropdown: for Literal/enum types
# - text: default for str fields
# - readonly: display only, no edit capability
WidgetType: TypeAlias = Literal[
    "checkbox_group", "toggle", "number", "dropdown", "text", "readonly"
]


def normalize_epic_id(epic_id: EpicId) -> str:
    """Normalize epic ID to string for comparison and storage.

    Args:
        epic_id: Epic identifier (int or str).

    Returns:
        String representation of the epic ID.

    Examples:
        >>> normalize_epic_id(3)
        '3'
        >>> normalize_epic_id("testarch")
        'testarch'

    """
    return str(epic_id)


def parse_epic_id(value: str) -> EpicId:
    """Parse epic ID from string, returning int if numeric.

    Args:
        value: String representation of epic ID.

    Returns:
        Integer if value is numeric, otherwise the original string.

    Examples:
        >>> parse_epic_id("3")
        3
        >>> parse_epic_id("testarch")
        'testarch'
        >>> parse_epic_id("0a")
        '0a'

    """
    try:
        return int(value)
    except ValueError:
        return value


def epic_id_for_filename(epic_id: EpicId) -> str:
    """Convert epic ID to safe filename component.

    Args:
        epic_id: Epic identifier.

    Returns:
        String safe for use in filenames.

    Examples:
        >>> epic_id_for_filename(3)
        '3'
        >>> epic_id_for_filename("testarch")
        'testarch'

    """
    return str(epic_id)


def is_numeric_epic(epic_id: EpicId) -> bool:
    """Check if epic ID is numeric.

    Args:
        epic_id: Epic identifier.

    Returns:
        True if epic_id is an integer, False otherwise.

    Examples:
        >>> is_numeric_epic(3)
        True
        >>> is_numeric_epic("testarch")
        False

    """
    return isinstance(epic_id, int)


def compare_epic_ids(a: EpicId, b: EpicId) -> int:
    """Compare two epic IDs for sorting.

    Numeric IDs come before string IDs.
    Within each category, natural ordering is used.

    Args:
        a: First epic ID.
        b: Second epic ID.

    Returns:
        -1 if a < b, 0 if a == b, 1 if a > b.

    Examples:
        >>> compare_epic_ids(1, 2)
        -1
        >>> compare_epic_ids("testarch", "power-prompts")
        1
        >>> compare_epic_ids(1, "testarch")
        -1

    """
    # Numeric IDs come first
    a_numeric = isinstance(a, int)
    b_numeric = isinstance(b, int)

    if a_numeric and not b_numeric:
        return -1
    if not a_numeric and b_numeric:
        return 1

    # Both same type - compare directly with proper narrowing
    if isinstance(a, int) and isinstance(b, int):
        # Both are int - direct comparison
        if a < b:
            return -1
        if a > b:
            return 1
    elif isinstance(a, str) and isinstance(b, str):
        # Both are str - direct comparison
        if a < b:
            return -1
        if a > b:
            return 1
    return 0


def epic_sort_key(epic_id: EpicId) -> tuple[int, int | str]:
    """Generate sort key for epic ID.

    Numeric IDs sort first (by value), then string IDs (alphabetically).

    Args:
        epic_id: Epic identifier.

    Returns:
        Tuple for sorting: (type_order, value).

    Examples:
        >>> sorted([3, "testarch", 1, "alpha"], key=epic_sort_key)
        [1, 3, 'alpha', 'testarch']

    """
    if isinstance(epic_id, int):
        return (0, epic_id)
    return (1, epic_id)
