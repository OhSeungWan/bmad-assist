"""Index.md parsing for sharded documentation.

This module provides functions to parse index.md files in sharded
documentation directories to extract file references and loading order.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Pattern to extract markdown links: [text](./filename.md) or [text](filename.md)
# Excludes external URLs (http://, https://, //)
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((?!https?://|//)\.?/?([^)]+\.md)\)")


def parse_index_references(index_path: Path) -> list[str]:
    """Parse index.md to extract referenced file names in order.

    Extracts markdown links from index.md to determine the intended
    loading order of sharded documentation files.

    Args:
        index_path: Path to index.md file.

    Returns:
        List of referenced filenames in order of appearance.
        Does not include index.md itself.

    Examples:
        >>> parse_index_references(Path("docs/epics/index.md"))
        ['epic-2-integration.md', 'epic-1-foundation.md']

    Notes:
        - Only .md file links are extracted
        - Links can be relative (./file.md) or bare (file.md)
        - Duplicate references are preserved (caller handles)
        - Non-existent files are included (caller validates)

    """
    try:
        content = index_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Failed to read index.md at %s: %s", index_path, e)
        return []

    references: list[str] = []
    for match in MARKDOWN_LINK_PATTERN.finditer(content):
        filename = match.group(2)
        # Normalize: remove leading ./
        if filename.startswith("./"):
            filename = filename[2:]
        # Skip subdirectory paths (security - only same directory)
        if "/" in filename:
            logger.debug("Skipping subdirectory reference in index.md: %s", filename)
            continue
        # Don't include index.md itself if referenced
        if filename != "index.md":
            references.append(filename)

    logger.debug(
        "Parsed %d file references from %s: %s",
        len(references),
        index_path,
        references,
    )
    return references
