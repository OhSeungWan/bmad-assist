"""File discovery and inclusion for BMAD workflow compiler.

This module provides file discovery via glob patterns, content loading,
and section extraction for compiled workflows.

Public API:
    discover_files: Discover files based on input_file_patterns
    load_file_contents: Load discovered file contents into context
    extract_section: Extract a section from markdown by header
    LoadStrategy: Enum for file loading strategies
"""

from __future__ import annotations

import glob
import logging
import re
from enum import Enum
from pathlib import Path
from typing import Any

from bmad_assist.bmad.sharding import get_sort_key
from bmad_assist.bmad.sharding.index_parser import parse_index_references
from bmad_assist.bmad.sharding.sorting import DocType
from bmad_assist.compiler.types import CompilerContext
from bmad_assist.core.exceptions import AmbiguousFileError, CompilerError

logger = logging.getLogger(__name__)


class LoadStrategy(str, Enum):
    """File loading strategy for discovered files.

    Attributes:
        FULL_LOAD: Load all matching files.
        SELECTIVE_LOAD: Error on multiple matches - user must specify.
        INDEX_GUIDED: Parse index.md to determine relevant files.

    """

    FULL_LOAD = "FULL_LOAD"
    SELECTIVE_LOAD = "SELECTIVE_LOAD"
    INDEX_GUIDED = "INDEX_GUIDED"


def discover_files(
    context: CompilerContext,
) -> dict[str, list[Path]]:
    """Discover files based on input_file_patterns in workflow config.

    Uses glob patterns from workflow.yaml to find matching files.
    Supports sharded directories (checked first) and whole files.
    Results are stored in context.discovered_files.

    Args:
        context: Compiler context with workflow_ir containing raw_config.

    Returns:
        Dictionary mapping pattern names to lists of discovered file paths.

    Raises:
        CompilerError: If workflow_ir not set, invalid glob pattern, or
            required file missing.
        AmbiguousFileError: If SELECTIVE_LOAD finds multiple matches.

    """
    if context.workflow_ir is None:
        raise CompilerError(
            "Cannot discover files: workflow_ir not set in context\n"
            "  Why it's needed: File discovery requires parsed workflow config\n"
            "  How to fix: Call parse_workflow() before discover_files()"
        )

    raw_config = context.workflow_ir.raw_config
    patterns_config = raw_config.get("input_file_patterns", {})

    if not patterns_config:
        logger.debug("No input_file_patterns defined, skipping discovery")
        context.discovered_files = {}
        return {}

    discovered: dict[str, list[Path]] = {}

    for pattern_name, pattern_config in patterns_config.items():
        files = _discover_pattern(
            pattern_name=pattern_name,
            pattern_config=pattern_config,
            context=context,
        )
        discovered[pattern_name] = files
        logger.debug("Discovered %d files for pattern '%s'", len(files), pattern_name)

    # Validate required files
    _validate_required_files(patterns_config, discovered)

    context.discovered_files = discovered
    return discovered


def _discover_pattern(
    pattern_name: str,
    pattern_config: dict[str, Any],
    context: CompilerContext,
) -> list[Path]:
    """Discover files for a single pattern configuration.

    Args:
        pattern_name: Name of the pattern (e.g., 'prd', 'epics').
        pattern_config: Pattern configuration dict with 'whole', 'sharded', etc.
        context: Compiler context for path validation.

    Returns:
        List of discovered file paths.

    Raises:
        CompilerError: If glob pattern is invalid.
        AmbiguousFileError: If SELECTIVE_LOAD finds multiple matches.

    """
    sharded_pattern = pattern_config.get("sharded")
    whole_pattern = pattern_config.get("whole")
    strategy_str = pattern_config.get("load_strategy", "FULL_LOAD")

    try:
        strategy = LoadStrategy(strategy_str)
    except ValueError:
        logger.warning(
            "Unknown load_strategy '%s' for pattern '%s', using FULL_LOAD",
            strategy_str,
            pattern_name,
        )
        strategy = LoadStrategy.FULL_LOAD

    files: list[Path] = []

    # Try sharded pattern first
    if sharded_pattern:
        sharded_files = _glob_files(sharded_pattern, pattern_name, context.project_root)
        # "sharded exists" = directory has at least one .md file
        if sharded_files:
            files = sharded_files
            logger.debug(
                "Using sharded files for '%s': %d files found",
                pattern_name,
                len(files),
            )

    # Fall back to whole pattern if no sharded files
    if not files and whole_pattern:
        files = _glob_files(whole_pattern, pattern_name, context.project_root)
        if files:
            logger.debug(
                "Using whole file for '%s': %d files found",
                pattern_name,
                len(files),
            )

    # Apply load strategy
    files = _apply_load_strategy(
        files=files,
        strategy=strategy,
        pattern_name=pattern_name,
        pattern_config=pattern_config,
        context=context,
    )

    return files


def _glob_files(
    pattern: str,
    pattern_name: str,
    project_root: Path,
) -> list[Path]:
    """Execute glob pattern and filter results.

    Args:
        pattern: Glob pattern string.
        pattern_name: Name of pattern for error messages.
        project_root: Project root for path validation.

    Returns:
        List of valid file paths within project_root.

    Raises:
        CompilerError: If glob pattern syntax is invalid.

    """
    try:
        # Use glob.glob with recursive support
        matches = glob.glob(pattern, recursive=True)
    except re.error as e:
        raise CompilerError(
            f"Invalid glob pattern for '{pattern_name}': {pattern}\n"
            f"  Error: {e}\n"
            f"  Suggestion: Check glob pattern syntax (wildcards, brackets, escaping)"
        ) from e
    except Exception as e:
        raise CompilerError(
            f"Error executing glob pattern for '{pattern_name}': {pattern}\n"
            f"  Error: {e}\n"
            f"  Suggestion: Check pattern syntax and file system permissions"
        ) from e

    files: list[Path] = []
    visited: set[Path] = set()

    for match in matches:
        path = Path(match)

        # Skip if not a file
        if not path.is_file():
            continue

        # Resolve symlinks and check for loops
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError) as e:
            logger.debug("Skipping path with resolution error: %s - %s", path, e)
            continue

        # Check for symlink loop (visited set)
        if resolved in visited:
            logger.debug("Skipping symlink loop: %s", path)
            continue
        visited.add(resolved)

        # Security: validate path is within project_root
        try:
            if not resolved.is_relative_to(project_root.resolve()):
                logger.warning("Skipping file outside project root: %s", path)
                continue
        except (OSError, ValueError):
            logger.warning("Skipping file with invalid path: %s", path)
            continue

        files.append(path)

    return files


def _apply_load_strategy(
    files: list[Path],
    strategy: LoadStrategy,
    pattern_name: str,
    pattern_config: dict[str, Any],
    context: CompilerContext,
) -> list[Path]:
    """Apply load strategy to discovered files.

    Args:
        files: List of discovered files.
        strategy: Loading strategy to apply.
        pattern_name: Name of pattern for error messages.
        pattern_config: Pattern configuration for workflow_context.
        context: Compiler context.

    Returns:
        Filtered list of files based on strategy.

    Raises:
        AmbiguousFileError: If SELECTIVE_LOAD finds multiple matches.

    """
    if not files:
        return []

    if strategy == LoadStrategy.FULL_LOAD:
        # Return all files, sorted
        return _sort_files(files, pattern_name)

    elif strategy == LoadStrategy.SELECTIVE_LOAD:
        if len(files) > 1:
            # Sort files for deterministic error messages (NFR11)
            sorted_files = sorted(files, key=lambda f: str(f))
            # Format candidates list (max 10 shown per AC4)
            max_shown = 10
            total = len(sorted_files)
            shown_files = sorted_files[:max_shown]
            candidates_text = "\n    - ".join(str(f) for f in shown_files)
            if total > max_shown:
                candidates_text += f"\n    ... and {total - max_shown} more"

            raise AmbiguousFileError(
                f"Multiple files match pattern '{pattern_name}' with SELECTIVE_LOAD strategy\n"
                f"  Candidates (showing first {min(max_shown, total)} of {total}):\n"
                f"    - {candidates_text}\n"
                f"  Suggestion: Change load_strategy to FULL_LOAD in workflow.yaml, "
                f"or narrow the glob pattern",
                pattern_name=pattern_name,
                candidates=sorted_files,
                suggestion="Change load_strategy to FULL_LOAD in workflow.yaml, "
                "or narrow the glob pattern",
            )
        return files

    elif strategy == LoadStrategy.INDEX_GUIDED:
        return _apply_index_guided(
            files=files,
            pattern_name=pattern_name,
            context=context,
        )

    return files


def _apply_index_guided(
    files: list[Path],
    pattern_name: str,
    context: CompilerContext,
) -> list[Path]:
    """Apply INDEX_GUIDED strategy using index.md.

    Args:
        files: List of discovered files (should include index.md).
        pattern_name: Name of pattern.
        context: Compiler context for workflow_context.

    Returns:
        List of relevant files based on index.md and workflow context.

    """
    # Find index.md among files
    index_file: Path | None = None
    for f in files:
        if f.name == "index.md":
            index_file = f
            break

    if not index_file:
        # No index.md - return all files sorted
        logger.debug("No index.md found for INDEX_GUIDED, returning all files")
        return _sort_files(files, pattern_name)

    # Parse index.md for references and their descriptions
    # parse_index_references returns list of filenames
    references = parse_index_references(index_file)

    # Get workflow context for relevance matching
    workflow_context = ""
    if context.workflow_ir:
        workflow_context = context.workflow_ir.raw_config.get("workflow_context", "")

    # Build map of filename to file path
    file_map: dict[str, Path] = {f.name: f for f in files}

    # Always include index.md first
    result: list[Path] = [index_file]

    # Read index.md content to extract descriptions for relevance matching
    try:
        index_content = index_file.read_text(encoding="utf-8").lower()
    except OSError:
        index_content = ""

    if workflow_context:
        # Filter by relevance based on workflow_context
        context_lower = workflow_context.lower()

        for ref in references:
            if ref in file_map:
                # Check if reference line in index mentions context
                # Simple heuristic: check if context term appears near the link
                ref_lower = ref.lower().replace("-", " ").replace("_", " ")

                # Check both filename and surrounding text in index
                is_match = context_lower in ref_lower or context_lower in index_content
                if is_match and file_map[ref] not in result:
                    result.append(file_map[ref])
    else:
        # No workflow_context - include all indexed files
        for ref in references:
            if ref in file_map and file_map[ref] not in result:
                result.append(file_map[ref])

    return result


def _sort_files(files: list[Path], pattern_name: str) -> list[Path]:
    """Sort files according to pattern-specific rules.

    Args:
        files: List of files to sort.
        pattern_name: Pattern name for determining sort strategy.

    Returns:
        Sorted list of files.

    """
    # Determine doc type for sorting
    doc_type: DocType
    pattern_lower = pattern_name.lower()
    if "epic" in pattern_lower:
        doc_type = "epics"
    elif "arch" in pattern_lower:
        doc_type = "architecture"
    elif "ux" in pattern_lower:
        doc_type = "ux"
    else:
        doc_type = "prd"  # Default alphabetic with index first

    return sorted(files, key=lambda f: get_sort_key(doc_type, f.name))


def _validate_required_files(
    patterns_config: dict[str, Any],
    discovered: dict[str, list[Path]],
) -> None:
    """Validate that required files were discovered.

    Args:
        patterns_config: Pattern configurations with 'required' flags.
        discovered: Discovered files by pattern name.

    Raises:
        CompilerError: If required file is missing.

    """
    for pattern_name, config in patterns_config.items():
        required = config.get("required", False)
        if required and not discovered.get(pattern_name):
            whole = config.get("whole", "")
            sharded = config.get("sharded", "")
            raise CompilerError(
                f"Required file not found for pattern '{pattern_name}'\n"
                f"  Patterns tried:\n"
                f"    - whole: {whole or '(not configured)'}\n"
                f"    - sharded: {sharded or '(not configured)'}\n"
                f"  Why it's needed: This file is marked as required by the workflow\n"
                f"  How to fix: Create the file or update input_file_patterns"
            )


def load_file_contents(
    context: CompilerContext,
    patterns: list[str] | None = None,
) -> dict[str, str]:
    """Load content from discovered files into context.

    Loads files from context.discovered_files and stores concatenated
    content in context.file_contents.

    Args:
        context: Compiler context with discovered_files.
        patterns: Optional list of pattern names to load.
            If None, loads all discovered patterns.

    Returns:
        Dictionary mapping pattern names to file contents.

    Raises:
        CompilerError: If file read fails with permission error.

    """
    if patterns is None:
        patterns = list(context.discovered_files.keys())

    result: dict[str, str] = {}

    for pattern_name in patterns:
        files = context.discovered_files.get(pattern_name, [])

        if not files:
            result[pattern_name] = ""
            continue

        # Sort files for consistent ordering (index.md first)
        sorted_files = _sort_files(files, pattern_name)

        content_parts: list[str] = []
        for file_path in sorted_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                content_parts.append(content)
            except UnicodeDecodeError:
                logger.debug("Skipping binary file: %s", file_path)
                # Binary file - skip, don't append
                continue
            except PermissionError as e:
                raise CompilerError(
                    f"Permission denied reading file: {file_path}\n"
                    f"  Error: {e}\n"
                    f"  Suggestion: Check file permissions or run with appropriate access rights"
                ) from e
            except OSError as e:
                logger.warning("Error reading file '%s': %s", file_path, e)

        result[pattern_name] = "\n\n".join(content_parts)

    context.file_contents.update(result)
    return result


def extract_section(
    file_path: Path,
    section_id: str,
) -> str:
    """Extract a section from markdown file by header match.

    Finds a header containing the section_id and extracts content
    until the next header of same or higher level.

    Args:
        file_path: Path to markdown file.
        section_id: Section identifier to match (e.g., "story-10.4", "epic-10").
            Supports normalized matching: -, ., _ treated as word separators.

    Returns:
        Extracted section content including header.

    Raises:
        CompilerError: If section not found or file read error.

    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as e:
        raise CompilerError(
            f"Cannot read file: {file_path}\n"
            f"  Error: {e}\n"
            f"  Suggestion: Check file path and permissions"
        ) from e

    lines = content.split("\n")

    # Normalize section_id for matching: treat -, ., _ as word separators
    normalized_id = re.sub(r"[-._]", " ", section_id.lower())

    start_idx: int | None = None
    start_level = 0

    for i, line in enumerate(lines):
        # Header MUST start with # (not just contain it)
        if not line.startswith("#"):
            continue

        # Count # chars at start
        match = re.match(r"^(#+)", line)
        if not match:
            continue

        level = len(match.group(1))
        header_text = line.lstrip("#").strip().lower()

        # Normalize header text same way
        normalized_header = re.sub(r"[-._]", " ", header_text)

        # Check if header matches section_id with word boundary
        # Word boundary check: prevent "10.4" matching "10.40"
        pattern = r"\b" + re.escape(normalized_id) + r"\b"
        if re.search(pattern, normalized_header):
            start_idx = i
            start_level = level
            break

    if start_idx is None:
        raise CompilerError(
            f"Section not found in {file_path}: '{section_id}'\n"
            f"  Why it's needed: Workflow requires specific section content\n"
            f"  Suggestion: Add a header containing '{section_id}' to the file"
        )

    # Find end of section: next header of same or higher level (<=)
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        if line.startswith("#"):
            match = re.match(r"^(#+)", line)
            if match:
                level = len(match.group(1))
                if level <= start_level:
                    end_idx = i
                    break

    return "\n".join(lines[start_idx:end_idx])


def find_closest_file(
    base_dir: Path,
    pattern: str,
    exclude_dirs: list[str] | None = None,
) -> Path | None:
    """Find file matching pattern closest to base directory.

    Searches recursively from base_dir, excludes specified directories,
    and returns the file with the shortest path (closest to base_dir).

    Args:
        base_dir: Directory to start searching from.
        pattern: Glob pattern to match (e.g., "**/project_context.md").
        exclude_dirs: Directory names to exclude (e.g., ["archive"]).
            Matches any path component, case-insensitive.

    Returns:
        Path to the closest matching file, or None if not found.

    """
    if exclude_dirs is None:
        exclude_dirs = []

    exclude_lower = [d.lower() for d in exclude_dirs]

    # Build full pattern from base_dir
    full_pattern = str(base_dir / pattern)

    try:
        matches = glob.glob(full_pattern, recursive=True)
    except (re.error, Exception) as e:
        logger.warning("Error in glob pattern '%s': %s", pattern, e)
        return None

    valid_files: list[Path] = []

    for match in matches:
        path = Path(match)

        # Skip if not a file
        if not path.is_file():
            continue

        # Check if any path component is in exclude list
        path_parts_lower = [p.lower() for p in path.parts]
        if any(excl in path_parts_lower for excl in exclude_lower):
            logger.debug("Excluding file in excluded dir: %s", path)
            continue

        valid_files.append(path)

    if not valid_files:
        logger.debug("No files found matching '%s' in %s", pattern, base_dir)
        return None

    # Sort by path depth (number of parts) - closest to base_dir first
    # Then alphabetically for determinism
    valid_files.sort(key=lambda p: (len(p.parts), str(p)))

    closest = valid_files[0]
    logger.debug(
        "Found %d files matching '%s', using closest: %s",
        len(valid_files),
        pattern,
        closest,
    )
    return closest
