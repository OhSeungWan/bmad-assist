"""Sorting strategies for sharded documentation files.

This module provides sort key functions for different document types:
- epics: Numeric sort by epic number (epic-1.md, epic-2.md, epic-10.md)
- architecture, prd, ux: Alphabetic sort (index.md always first)
"""

from __future__ import annotations

import re
from typing import Literal

# Valid document types for sharding
DocType = Literal["epics", "architecture", "prd", "ux"]

# Pattern to extract epic number from filename: epic-{N}.md or epic-{N}-{name}.md
EPIC_NUMBER_PATTERN = re.compile(r"epic-(\d+)")


def get_sort_key(doc_type: DocType, filename: str) -> tuple[int, int | str]:
    """Get sort key based on document type.

    For epics, sorts numerically by epic number extracted from filename.
    For other document types, sorts alphabetically with index.md first.

    Args:
        doc_type: One of 'epics', 'architecture', 'prd', 'ux'.
        filename: File name (e.g., 'epic-1-foundation.md', 'core-decisions.md').

    Returns:
        Sort key tuple where first element is priority (0 for index.md, 1 for
        matched files, 2 for unmatched), second element is the sort value.

    Examples:
        >>> get_sort_key("epics", "epic-1-foundation.md")
        (1, 1)
        >>> get_sort_key("epics", "epic-10-final.md")
        (1, 10)
        >>> get_sort_key("architecture", "index.md")
        (0, "")
        >>> get_sort_key("architecture", "core-decisions.md")
        (1, "core-decisions.md")

    """
    # index.md always comes first for all doc types
    if filename == "index.md":
        return (0, "")

    if doc_type == "epics":
        # Extract epic number: epic-1-name.md -> 1
        match = EPIC_NUMBER_PATTERN.match(filename)
        if match:
            return (1, int(match.group(1)))
        # Non-matching epic files sorted last alphabetically
        return (2, filename.lower())
    else:
        # Alphabetic sort for architecture, prd, ux
        return (1, filename.lower())
