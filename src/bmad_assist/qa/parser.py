"""Test plan parser for QA execution.

Parses E2E test plan markdown files to extract structured test data.
Used by batch executor to split tests into manageable chunks.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Parsed test case from test plan.

    Attributes:
        id: Test ID (e.g., E17-A01, E17-B05).
        name: Human-readable test name.
        category: Test category (A, B, or C).
        script: Bash script content for Category A tests.
        description: Test description.
        pre_conditions: Pre-conditions to check.
        expected_exit_code: Expected exit code (default 0).
        expected_output: Expected output patterns.

    """

    id: str
    name: str
    category: str
    script: str = ""
    description: str = ""
    pre_conditions: list[str] = field(default_factory=list)
    expected_exit_code: int = 0
    expected_output: list[str] = field(default_factory=list)


@dataclass
class ParsedTestPlan:
    """Parsed test plan with all test cases.

    Attributes:
        epic_id: Epic identifier.
        tests: List of parsed test cases.
        setup_script: Optional setup script to run before tests.
        category_counts: Dict mapping category to test count.

    """

    epic_id: str
    tests: list[TestCase]
    setup_script: str = ""
    category_counts: dict[str, int] = field(default_factory=dict)

    def get_tests_by_category(self, category: str) -> list[TestCase]:
        """Get tests filtered by category.

        Args:
            category: Category filter (A, B, C, or "all").

        Returns:
            List of test cases matching the category.

        """
        if category.lower() == "all":
            return [t for t in self.tests if t.category in ("A", "B")]
        return [t for t in self.tests if t.category == category.upper()]


# Regex patterns for parsing
_TEST_ID_PATTERN = re.compile(r"E(\d+)-([ABC])(\d+)")
_HEADER_PATTERN = re.compile(r"^#{3,4}\s+(E\d+-[ABC]\d+):\s*(.+)$", re.MULTILINE)
_BASH_BLOCK_PATTERN = re.compile(r"```bash\n(.*?)```", re.DOTALL)
_TYPESCRIPT_BLOCK_PATTERN = re.compile(r"```(?:typescript|ts)\n(.*?)```", re.DOTALL)
_CHECKLIST_ROW_PATTERN = re.compile(r"\|\s*(?:\[[ x]\]\s*)?(E\d+-[ABC]\d+)\s*\|\s*([^|]+)\s*\|")


def parse_test_plan(content: str, epic_id: str | int) -> ParsedTestPlan:
    """Parse test plan markdown content.

    Extracts test cases from the test plan markdown format:
    1. Master Checklist table for test inventory
    2. Detailed test sections with bash scripts

    Args:
        content: Test plan markdown content.
        epic_id: Epic identifier for context.

    Returns:
        ParsedTestPlan with extracted test cases.

    """
    tests: list[TestCase] = []
    setup_script = ""
    category_counts: dict[str, int] = {"A": 0, "B": 0, "C": 0}

    # Extract setup section if present
    setup_match = re.search(
        r"##\s*Setup.*?\n```bash\n(.*?)```",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if setup_match:
        setup_script = setup_match.group(1).strip()
        logger.debug("Found setup script: %d chars", len(setup_script))

    # First pass: extract test IDs and names from checklist
    test_inventory: dict[str, str] = {}
    for match in _CHECKLIST_ROW_PATTERN.finditer(content):
        test_id = match.group(1)
        test_name = match.group(2).strip()
        test_inventory[test_id] = test_name

    logger.debug("Found %d tests in checklist", len(test_inventory))

    # Second pass: extract detailed test sections with scripts
    # Collect all header matches first, then iterate pairwise to avoid
    # false positives from markdown-like content inside heredocs
    header_matches = list(_HEADER_PATTERN.finditer(content))

    for i, header_match in enumerate(header_matches):
        test_id = header_match.group(1)
        test_name = header_match.group(2).strip()

        # Parse test ID components
        id_match = _TEST_ID_PATTERN.match(test_id)
        if not id_match:
            logger.warning("Invalid test ID format: %s", test_id)
            continue

        category = id_match.group(2)
        category_counts[category] = category_counts.get(category, 0) + 1

        # Find section content: from end of this header to start of next header (or EOF)
        section_start = header_match.end()
        section_end = header_matches[i + 1].start() if i + 1 < len(header_matches) else len(content)
        section_content = content[section_start:section_end]

        # Extract script based on category
        # Category A: bash scripts
        # Category B: TypeScript Playwright tests
        script = ""
        if category == "A":
            script_match = _BASH_BLOCK_PATTERN.search(section_content)
            if script_match:
                script = script_match.group(1).strip()
                logger.debug("Test %s: extracted bash script (%d chars)", test_id, len(script))
        elif category == "B":
            script_match = _TYPESCRIPT_BLOCK_PATTERN.search(section_content)
            if script_match:
                script = script_match.group(1).strip()
                logger.debug("Test %s: extracted typescript (%d chars)", test_id, len(script))

        # Extract pre-conditions
        pre_conditions: list[str] = []
        pre_match = re.search(
            r"\*\*Pre-conditions?:\*\*\s*(.+?)(?=\n\n|\n\*\*|\n```|$)",
            section_content,
            re.DOTALL | re.IGNORECASE,
        )
        if pre_match:
            pre_text = pre_match.group(1).strip()
            pre_conditions = [
                p.strip().lstrip("-").strip() for p in pre_text.split("\n") if p.strip()
            ]

        # Extract expected output patterns
        expected_output: list[str] = []
        expected_match = re.search(
            r"\*\*Expected.*?:\*\*\s*(.+?)(?=\n\n|\n\*\*|\n```|$)",
            section_content,
            re.DOTALL | re.IGNORECASE,
        )
        if expected_match:
            expected_text = expected_match.group(1).strip()
            expected_output = [
                e.strip().lstrip("-").strip() for e in expected_text.split("\n") if e.strip()
            ]

        test = TestCase(
            id=test_id,
            name=test_name,
            category=category,
            script=script,
            description=section_content[:500].strip(),
            pre_conditions=pre_conditions,
            expected_exit_code=0,
            expected_output=expected_output,
        )
        tests.append(test)

    # Add tests from checklist that weren't in detailed sections
    found_ids = {t.id for t in tests}
    for test_id, test_name in test_inventory.items():
        if test_id not in found_ids:
            id_match = _TEST_ID_PATTERN.match(test_id)
            if id_match:
                category = id_match.group(2)
                category_counts[category] = category_counts.get(category, 0) + 1
                tests.append(
                    TestCase(
                        id=test_id,
                        name=test_name,
                        category=category,
                    )
                )

    # Sort tests by ID
    tests.sort(key=lambda t: (t.category, t.id))

    logger.info(
        "Parsed %d tests: A=%d, B=%d, C=%d",
        len(tests),
        category_counts.get("A", 0),
        category_counts.get("B", 0),
        category_counts.get("C", 0),
    )

    return ParsedTestPlan(
        epic_id=str(epic_id),
        tests=tests,
        setup_script=setup_script,
        category_counts=category_counts,
    )


def parse_test_plan_file(file_path: Path, epic_id: str | int) -> ParsedTestPlan:
    """Parse test plan from file.

    Args:
        file_path: Path to test plan markdown file.
        epic_id: Epic identifier.

    Returns:
        ParsedTestPlan with extracted test cases.

    Raises:
        FileNotFoundError: If test plan file doesn't exist.
        ValueError: If file is empty or unparseable.

    """
    if not file_path.exists():
        raise FileNotFoundError(f"Test plan not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"Test plan is empty: {file_path}")

    return parse_test_plan(content, epic_id)
