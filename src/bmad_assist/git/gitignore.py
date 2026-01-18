"""Gitignore setup utilities for bmad-assist projects.

Ensures proper .gitignore patterns are in place to prevent committing
auto-generated cache and metadata files that cause false positives in code reviews.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Patterns that bmad-assist requires in .gitignore
# These are auto-generated files that should NEVER be committed
REQUIRED_PATTERNS: tuple[str, ...] = (
    "# bmad-assist artifacts (auto-generated, never commit)",
    ".bmad-assist/cache/",
    "*.meta.yaml",
    "*.tpl.xml",
)

# Header comment to identify bmad-assist section
SECTION_HEADER = "# bmad-assist artifacts"


def check_gitignore(project_root: Path) -> tuple[bool, list[str]]:
    """Check if .gitignore has required bmad-assist patterns.

    Args:
        project_root: Path to project root directory.

    Returns:
        Tuple of (all_patterns_present, missing_patterns).

    """
    gitignore_path = project_root / ".gitignore"

    if not gitignore_path.exists():
        # No .gitignore - all patterns are missing
        return False, list(REQUIRED_PATTERNS[1:])  # Skip comment line

    content = gitignore_path.read_text(encoding="utf-8")
    lines = {line.strip() for line in content.split("\n")}

    missing = []
    for pattern in REQUIRED_PATTERNS:
        if pattern.startswith("#"):
            continue  # Skip comments in check
        if pattern not in lines:
            missing.append(pattern)

    return len(missing) == 0, missing


def setup_gitignore(project_root: Path, dry_run: bool = False) -> tuple[bool, str]:
    """Add required bmad-assist patterns to .gitignore.

    Creates .gitignore if it doesn't exist. Appends patterns if they're missing.
    Idempotent - safe to run multiple times.

    Args:
        project_root: Path to project root directory.
        dry_run: If True, don't modify files, just report what would be done.

    Returns:
        Tuple of (changes_made, message describing action taken).

    """
    gitignore_path = project_root / ".gitignore"
    all_present, missing = check_gitignore(project_root)

    if all_present:
        return False, "All bmad-assist patterns already in .gitignore"

    # Build the section to add
    section_lines = list(REQUIRED_PATTERNS)
    section = "\n" + "\n".join(section_lines) + "\n"

    if dry_run:
        if not gitignore_path.exists():
            return True, "Would create .gitignore with bmad-assist patterns"
        return True, f"Would add to .gitignore: {', '.join(missing)}"

    # Create or append to .gitignore
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        # Check if section header already exists (partial setup)
        if SECTION_HEADER in content:
            # Section exists but incomplete - don't duplicate, warn user
            logger.warning(
                "bmad-assist section exists in .gitignore but is incomplete. "
                "Please manually add: %s",
                ", ".join(missing),
            )
            return False, f"Partial setup detected. Missing: {', '.join(missing)}"

        # Append section
        if not content.endswith("\n"):
            content += "\n"
        content += section
        gitignore_path.write_text(content, encoding="utf-8")
        logger.info("Added bmad-assist patterns to .gitignore")
        return True, f"Added to .gitignore: {', '.join(missing)}"

    else:
        # Create new .gitignore
        gitignore_path.write_text(section.lstrip("\n"), encoding="utf-8")
        logger.info("Created .gitignore with bmad-assist patterns")
        return True, "Created .gitignore with bmad-assist patterns"


def ensure_gitignore(project_root: Path) -> None:
    """Ensure .gitignore has required patterns, setup silently if missing.

    This is meant to be called automatically during bmad-assist operations
    to ensure the project is properly configured. Logs but doesn't fail.

    Args:
        project_root: Path to project root directory.

    """
    all_present, missing = check_gitignore(project_root)

    if all_present:
        return

    # Auto-setup
    changed, message = setup_gitignore(project_root)
    if changed:
        logger.info("Auto-configured .gitignore: %s", message)
