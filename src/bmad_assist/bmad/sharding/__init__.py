"""Sharded documentation support for BMAD files.

This subpackage provides functionality to detect, load, and process sharded
documentation directories where large documents are split into multiple files.

Supports document types:
- epics: Sorted numerically by epic number (epic-1.md, epic-2.md, epic-10.md)
- architecture, prd, ux: Sorted alphabetically (index.md first)

Example usage:
    >>> from bmad_assist.bmad.sharding import (
    ...     resolve_doc_path,
    ...     load_sharded_epics,
    ...     load_sharded_content,
    ... )
    >>> path, is_sharded = resolve_doc_path(docs_dir, "epics")
    >>> if is_sharded:
    ...     epics = load_sharded_epics(path)

"""

from .detection import is_sharded_path, resolve_doc_path
from .loaders import load_sharded_content, load_sharded_epics
from .security import DuplicateEpicError, SecurityError, validate_sharded_path
from .sorting import get_sort_key

__all__ = [
    # detection
    "is_sharded_path",
    "resolve_doc_path",
    # loaders
    "load_sharded_content",
    "load_sharded_epics",
    # security
    "DuplicateEpicError",
    "SecurityError",
    "validate_sharded_path",
    # sorting
    "get_sort_key",
]
