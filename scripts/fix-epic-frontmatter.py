#!/usr/bin/env python3
"""Fix epic files to have proper YAML frontmatter and story headers for bmad-assist parsing."""

import re
from pathlib import Path


def extract_epic_info(content: str, filename: str) -> tuple[int, str, str]:
    """Extract epic number, title, and status from content or filename."""
    # Try to get epic number from filename first (epic-1-foo.md)
    filename_match = re.match(r"epic-(\d+)", filename)
    epic_num = int(filename_match.group(1)) if filename_match else None

    # Extract title from first heading
    title_match = re.search(r"^#\s+Epic\s+\d+:\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Unknown"

    # Extract status from **Status**: line
    status_match = re.search(r"\*\*Status\*\*:\s*(\w+)", content, re.IGNORECASE)
    status = status_match.group(1).lower() if status_match else "draft"

    return epic_num, title, status


def fix_story_headers(content: str) -> str:
    """Convert # Story X.Y: to ## Story X.Y: for parser compatibility."""
    # Pattern: single # followed by Story X.Y: (not ## or ###)
    # Replace with ## Story X.Y:
    fixed = re.sub(
        r"^#\s+(Story\s+\d+\.\d+:.*)$",
        r"## \1",
        content,
        flags=re.MULTILINE,
    )
    return fixed


def fix_epic_file(file_path: Path) -> tuple[bool, bool]:
    """Fix epic file: add frontmatter if missing, fix story headers.

    Returns: (frontmatter_fixed, headers_fixed)
    """
    content = file_path.read_text(encoding="utf-8")
    frontmatter_fixed = False
    headers_fixed = False

    # Fix frontmatter if missing
    if not content.startswith("---"):
        epic_num, title, status = extract_epic_info(content, file_path.name)

        if epic_num is None:
            print(f"  ERROR (no epic number): {file_path.name}")
            return False, False

        # Create frontmatter
        frontmatter = f"""---
epic_num: {epic_num}
title: {title}
status: {status}
---

"""
        content = frontmatter + content
        frontmatter_fixed = True

    # Fix story headers (# Story -> ## Story)
    original_content = content
    content = fix_story_headers(content)
    if content != original_content:
        headers_fixed = True

    # Write back if any changes
    if frontmatter_fixed or headers_fixed:
        file_path.write_text(content, encoding="utf-8")
        changes = []
        if frontmatter_fixed:
            changes.append("frontmatter")
        if headers_fixed:
            changes.append("headers")
        print(f"  FIXED: {file_path.name} ({', '.join(changes)})")

    return frontmatter_fixed, headers_fixed


def process_fixture(fixture_dir: Path) -> tuple[int, int]:
    """Process all epic files in a fixture directory.

    Returns: (frontmatter_fixes, header_fixes)
    """
    epics_dir = fixture_dir / "docs" / "epics"
    if not epics_dir.exists():
        print(f"No epics directory: {epics_dir}")
        return 0, 0

    frontmatter_fixes = 0
    header_fixes = 0
    for epic_file in sorted(epics_dir.glob("epic-*.md")):
        fm_fixed, hdr_fixed = fix_epic_file(epic_file)
        if fm_fixed:
            frontmatter_fixes += 1
        if hdr_fixed:
            header_fixes += 1

    return frontmatter_fixes, header_fixes


def main():
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"

    projects = [
        "auth-service",
        "component-library",
        "cli-dashboard",
        "markdown-notes",
        "test-data-gen",
        "webhook-relay",
    ]

    total_fm = 0
    total_hdr = 0
    for project in projects:
        project_dir = fixtures_dir / project
        if project_dir.exists():
            print(f"\n{project}:")
            fm, hdr = process_fixture(project_dir)
            total_fm += fm
            total_hdr += hdr
        else:
            print(f"\n{project}: NOT FOUND")

    print(f"\n\nTotal: {total_fm} frontmatter fixes, {total_hdr} header fixes")


if __name__ == "__main__":
    main()
