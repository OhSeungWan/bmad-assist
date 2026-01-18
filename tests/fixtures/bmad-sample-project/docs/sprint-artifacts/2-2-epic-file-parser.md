# Story 2.2: Epic File Parser

**Status:** Ready for Review
**Story Points:** 3

---

## 📌 Quick Reference

**Module:** `src/bmad_assist/bmad/parser.py` (extend existing - NO new file)
**New Exports:** `EpicStory`, `EpicDocument`, `parse_epic_file`
**Foundation:** Build on `parse_bmad_file()` from Story 2.1 - NO duplication
**Key Patterns:** See Dev Notes for regex (STORY_HEADER_PATTERN handles `##` and `###`)
**Tests:** `tests/bmad/test_epic_parser.py` - 10 test classes for 10 ACs
**Critical Mandate:** NO code duplication from Story 2.1 - reuse existing parser
**Validation:** pytest (>=95% coverage), mypy (no errors), ruff (no warnings)

---

## Story

**As a** developer,
**I want** to extract story list and status from epic files,
**So that** the system knows which stories exist and their completion state.

### Business Context

This story builds directly on Story 2.1 (Markdown Frontmatter Parser) to provide the next layer of BMAD file understanding. While Story 2.1 gave us generic markdown+frontmatter parsing, Story 2.2 specifically interprets epic file structure to extract:

- Story identifiers (epic.story numbers)
- Story titles
- Story status (inferred from content or markers)
- Story dependencies (if present)

This is critical for:
- **FR30:** System can extract story list and status from epic files
- **FR27:** System can read current project state from BMAD files (epic files are a primary source)
- **FR28:** Enable discrepancy detection between internal state and BMAD files

The epic file parser enables bmad-assist to understand project progress without LLM calls - a fundamental requirement for autonomous operation.

### Success Criteria

- Parse BMAD epic files following the standard `## Story X.Y: Title` format
- Extract story number, title, and estimate for each story
- Return structured list of Story objects
- Handle various epic file formats (single epic file, consolidated epics.md)
- Gracefully handle missing stories or malformed sections
- Build on existing `parse_bmad_file()` from Story 2.1 - NO duplication

---

## Acceptance Criteria

### AC1: Parse standard story sections
```gherkin
Given an epic file with standard story sections:
  """
  # Epic 2: BMAD File Integration

  ## Story 2.1: Markdown Frontmatter Parser

  **As a** developer...

  **Acceptance Criteria:**
  ...

  **Estimate:** 2 SP

  ---

  ## Story 2.2: Epic File Parser

  **As a** developer...
  """
When parse_epic_file(path) is called
Then a list of Story objects is returned
And first story has number="2.1", title="Markdown Frontmatter Parser"
And second story has number="2.2", title="Epic File Parser"
```

### AC2: Extract story estimates
```gherkin
Given a story section contains "**Estimate:** 3 SP" or "**Story Points:** 3"
When parse_epic_file(path) is called
Then story.estimate equals 3
```

### AC3: Handle epic file with no stories
```gherkin
Given an epic file with only epic header (no story sections):
  """
  # Epic 5: Power-Prompts Engine

  **Goal:** System can load and inject context-aware prompts...

  **FRs:** FR22, FR23, FR24, FR25
  """
When parse_epic_file(path) is called
Then empty list is returned
And no error is raised
```

### AC4: Handle malformed story headers
```gherkin
Given an epic file with non-standard story headers:
  """
  ## Story 2.1 - Missing Colon
  ## Invalid: No Number
  ## Story: No Epic Prefix
  """
When parse_epic_file(path) is called
Then only valid story headers are parsed
And malformed headers are logged as warnings (not errors)
```

### AC5: Extract epic metadata from frontmatter
```gherkin
Given an epic file with frontmatter:
  """
  ---
  epic_num: 2
  title: BMAD File Integration
  status: in-progress
  ---

  ## Story 2.1: Markdown Frontmatter Parser
  ...
  """
When parse_epic_file(path) is called
Then epic.number equals 2
And epic.title equals "BMAD File Integration"
And epic.status equals "in-progress"
```

### AC6: Handle consolidated epics.md file
```gherkin
Given a single epics.md file with multiple epics:
  """
  # Epic 1: Project Foundation

  ## Story 1.1: Project Initialization
  ...

  # Epic 2: BMAD File Integration

  ## Story 2.1: Markdown Frontmatter Parser
  ...
  """
When parse_epic_file(path) is called
Then EpicDocument is returned with:
  - epic_num = None (multi-epic file has no single epic number)
  - title = None (multi-epic file has no single title)
  - status = None (multi-epic file has no single status)
  - stories = list containing stories from ALL epics
And each story.number reflects its source epic (e.g., "1.1", "2.1")
And stories are ordered by appearance in file
```

### AC7: Extract story dependencies
```gherkin
Given a story section contains dependencies:
  """
  ## Story 3.5: Resume Interrupted Loop

  **Dependencies:** Story 3.2 (Atomic State Persistence), Story 3.4 (Loop Position Tracking)
  """
When parse_epic_file(path) is called
Then story.dependencies equals ["3.2", "3.4"]
```

### AC8: Return type consistency
```gherkin
Given parse_epic_file returns results
When results are inspected
Then result is EpicDocument dataclass with:
  - epic_num: int | None
  - title: str | None
  - status: str | None
  - stories: list[EpicStory]
  - path: str
And each EpicStory has:
  - number: str (e.g., "2.1")
  - title: str
  - estimate: int | None
  - dependencies: list[str]
```

### AC9: Infer status from content with priority rules
```gherkin
Given an epic file with story status indicators:
  """
  ## Story 2.1: Markdown Frontmatter Parser
  **Status:** done

  ## Story 2.2: Epic File Parser
  **Status:** in-progress
  """
When parse_epic_file(path) is called
Then story[0].status equals "done"
And story[1].status equals "in-progress"

# Status priority rules (highest to lowest):
# 1. Explicit **Status:** field in story section (if present)
# 2. None (checkbox counts tracked separately in completed_criteria/total_criteria)
# Note: Checkboxes do NOT auto-infer status; they are tracked separately
```

### AC9b: Status field takes priority over checkbox counts
```gherkin
Given a story with BOTH Status field AND checkbox criteria:
  """
  ## Story 2.1: Parser
  **Status:** done

  **Acceptance Criteria:**
  - [ ] AC1: Parse frontmatter
  - [ ] AC2: Handle errors
  """
When parse_epic_file(path) is called
Then story.status equals "done" (explicit Status field wins)
And story.completed_criteria equals 0 (tracked separately)
And story.total_criteria equals 2 (tracked separately)
```

### AC10: Handle story status from acceptance criteria checkboxes
```gherkin
Given a story section with checkbox-based acceptance criteria:
  """
  ## Story 2.1: Markdown Frontmatter Parser

  **Acceptance Criteria:**
  - [x] AC1: Parse valid frontmatter
  - [x] AC2: Parse file without frontmatter
  - [ ] AC3: Handle malformed frontmatter
  """
When parse_epic_file(path) is called
Then story.completed_criteria equals 2
And story.total_criteria equals 3
```

---

## Tasks / Subtasks

- [x] Task 1: Create data models (AC8)
  - [x] 1.1 Create EpicStory dataclass in `bmad/parser.py` (number, title, estimate, dependencies, status, completed_criteria, total_criteria)
  - [x] 1.2 Create EpicDocument dataclass (epic_num, title, status, stories, path)
  - [x] 1.3 Add type hints and docstrings

- [x] Task 2: Implement parse_epic_file function (AC1, AC2, AC3, AC4, AC5)
  - [x] 2.1 Call existing `parse_bmad_file()` to get frontmatter and content
  - [x] 2.2 Extract epic metadata from frontmatter (epic_num, title, status)
  - [x] 2.3 Parse content for `## Story X.Y: Title` OR `### Story X.Y: Title` headers using regex (handle both h2 and h3)
  - [x] 2.4 Extract estimate from each story section (`**Estimate:**` or `**Story Points:**`)
  - [x] 2.5 Extract status from each story section (`**Status:**`) - explicit status only, not inferred from checkboxes
  - [x] 2.6 Handle malformed headers gracefully with logging:
    ```python
    # Logger specification (consistent with architecture.md):
    logger = logging.getLogger(__name__)  # Results in 'bmad_assist.bmad.parser'

    # Warning format for malformed headers:
    logger.warning("Skipping malformed story header: %s", malformed_text)
    ```
  - [x] 2.7 Return EpicDocument with all extracted data

- [x] Task 3: Implement dependency extraction (AC7)
  - [x] 3.1 Parse `**Dependencies:**` line for story references
  - [x] 3.2 Extract story numbers using regex (handle various formats)
  - [x] 3.3 Return list of dependency story numbers

- [x] Task 4: Implement consolidated epic file handling (AC6)
  - [x] 4.1 Detect multiple `# Epic N:` or `## Epic N:` headers in content
  - [x] 4.2 Parse each epic section separately, extracting stories from each
  - [x] 4.3 Return single EpicDocument with:
    - epic_num = None (multi-epic file has no single epic)
    - title = None
    - status = None
    - stories = combined list from all epics (ordered by appearance)
  - [x] 4.4 Each story.number still reflects source epic (e.g., "1.1", "2.1")

- [x] Task 5: Implement acceptance criteria parsing (AC10)
  - [x] 5.1 Count `- [x]` (checked) and `- [ ]` (unchecked) patterns
  - [x] 5.2 Set completed_criteria and total_criteria on EpicStory

- [x] Task 6: Update module exports
  - [x] 6.1 Add EpicStory, EpicDocument, parse_epic_file to `bmad/__init__.py`
  - [x] 6.2 Update `__all__` export list

- [x] Task 7: Write tests
  - [x] 7.1 Create `tests/bmad/test_epic_parser.py`
  - [x] 7.2 Test AC1: Standard story sections parsing (both `##` and `###` headers)
  - [x] 7.3 Test AC2: Story estimate extraction
  - [x] 7.4 Test AC3: Epic with no stories
  - [x] 7.5 Test AC4: Malformed story headers (verify warning logged using caplog fixture)
  - [x] 7.6 Test AC5: Epic metadata from frontmatter
  - [x] 7.7 Test AC6: Consolidated epics.md file (verify epic_num=None, all stories returned)
  - [x] 7.8 Test AC7: Dependency extraction (multiple formats)
  - [x] 7.9 Test AC8: Return type validation
  - [x] 7.10 Test AC9: Status inference from content
  - [x] 7.11 Test AC9b: Status priority (explicit Status field wins over checkboxes)
  - [x] 7.12 Test AC10: Acceptance criteria checkbox counting
  - [x] 7.13 Test logging: Malformed headers trigger warning with correct format (using pytest caplog)
  - [x] 7.14 Test with real `docs/epics.md` file (60 stories expected)

- [x] Task 8: Validation
  - [x] 8.1 `pytest tests/bmad/` - all tests pass (82 tests)
  - [x] 8.2 `pytest --cov=src/bmad_assist/bmad` - coverage 96% (>= 95%)
  - [x] 8.3 `mypy src/bmad_assist/bmad/` - no type errors
  - [x] 8.4 `ruff check src/bmad_assist/bmad/` - no linting errors

---

## Dev Notes

### Architecture Compliance

**From architecture.md:**
- Module location: `src/bmad_assist/bmad/parser.py` (extend existing module)
- Pattern: Build on `parse_bmad_file()` - DO NOT duplicate parsing logic
- Exception: Use existing `ParserError` for parsing failures
- Naming: snake_case functions, PascalCase classes (EpicStory, EpicDocument)

**Module Organization:**
```python
# bmad/__init__.py (updated)
from .parser import (
    BmadDocument,
    parse_bmad_file,
    EpicStory,
    EpicDocument,
    parse_epic_file,
)

__all__ = [
    "BmadDocument",
    "parse_bmad_file",
    "EpicStory",
    "EpicDocument",
    "parse_epic_file",
]
```

### Required Imports

```python
from __future__ import annotations  # Required for Python 3.11 union syntax (int | None)

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Internal imports - reuse from Story 2.1
from .parser import parse_bmad_file, BmadDocument

logger = logging.getLogger(__name__)
```

### Implementation Strategy

**Build on Story 2.1 foundation:**
```python
def parse_epic_file(path: str | Path) -> EpicDocument:
    """Parse a BMAD epic file to extract story list.

    Uses parse_bmad_file() for frontmatter/content parsing, then
    applies epic-specific parsing to extract story information.
    """
    # Step 1: Use existing parser
    doc = parse_bmad_file(path)

    # Step 2: Extract epic metadata from frontmatter
    epic_num = doc.frontmatter.get("epic_num")
    title = doc.frontmatter.get("title")
    status = doc.frontmatter.get("status")

    # Step 3: Parse story sections from content
    stories = _parse_story_sections(doc.content)

    return EpicDocument(
        epic_num=epic_num,
        title=title,
        status=status,
        stories=stories,
        path=doc.path,
    )
```

**Regex patterns for story parsing:**
```python
import re

# Pattern: ## Story 2.1: Title
STORY_HEADER_PATTERN = re.compile(
    r"^##\s+Story\s+(\d+)\.(\d+):\s+(.+)$",
    re.MULTILINE
)

# Pattern: **Estimate:** 3 SP or **Story Points:** 3
ESTIMATE_PATTERN = re.compile(
    r"\*\*(?:Estimate|Story Points):\*\*\s*(\d+)",
    re.IGNORECASE
)

# Pattern: **Status:** done
STATUS_PATTERN = re.compile(
    r"\*\*Status:\*\*\s*(\w+[\w\s-]*)",
    re.IGNORECASE
)

# Pattern: **Dependencies:** Story 3.2, Story 3.4
DEPENDENCIES_PATTERN = re.compile(
    r"\*\*Dependencies:\*\*\s*(.+?)(?:\n|$)",
    re.IGNORECASE
)

# Pattern to extract story numbers from dependencies
STORY_NUMBER_PATTERN = re.compile(r"(\d+\.\d+)")

# Pattern for checkbox criteria
CHECKBOX_CHECKED = re.compile(r"-\s*\[x\]", re.IGNORECASE)
CHECKBOX_UNCHECKED = re.compile(r"-\s*\[\s*\]")
```

### Story Section Extraction Strategy

**Split content by story headers:**
```python
def _parse_story_sections(content: str) -> list[EpicStory]:
    """Extract stories from epic content.

    Splits content by ## Story headers and parses each section.
    """
    # Find all story header positions
    matches = list(STORY_HEADER_PATTERN.finditer(content))

    stories = []
    for i, match in enumerate(matches):
        # Extract section content (from this header to next or end)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section = content[start:end]

        epic_num, story_num, title = match.groups()
        number = f"{epic_num}.{story_num}"

        # Extract details from section
        estimate = _extract_estimate(section)
        status = _extract_status(section)
        dependencies = _extract_dependencies(section)
        completed, total = _count_criteria(section)

        stories.append(EpicStory(
            number=number,
            title=title.strip(),
            estimate=estimate,
            status=status,
            dependencies=dependencies,
            completed_criteria=completed,
            total_criteria=total,
        ))

    return stories
```

### Handling Real epics.md Format

**From docs/epics.md analysis:**
```markdown
### Story 2.1: Markdown Frontmatter Parser

**As a** developer,
**I want** to parse BMAD markdown files with YAML frontmatter,
**So that** I can extract metadata without using an LLM.

**Acceptance Criteria:**

**Given** a markdown file with YAML frontmatter exists
...

**FRs:** FR26, NFR6
**Estimate:** 2 SP

---
```

Key observations:
- Uses `### Story X.Y:` (h3 not h2) in some files
- Has `**FRs:**` line (functional requirements)
- Estimate format: `**Estimate:** 2 SP`
- Stories separated by `---` horizontal rules

**Updated regex to handle h2 or h3:**
```python
STORY_HEADER_PATTERN = re.compile(
    r"^#{2,3}\s+Story\s+(\d+)\.(\d+):\s+(.+)$",
    re.MULTILINE
)
```

### Performance Constraints

**Expected File Sizes:**
- Single epic file: <50KB (typical: 10-20 stories)
- Consolidated epics.md: <500KB (typical: 60 stories, 9 epics)

**Performance Target:**
- Parse 60-story file in <100ms on standard hardware

**Memory Profile:**
- Parser loads entire file into memory (acceptable - BMAD files <1MB expected)
- Regex operations are O(n) where n = file size
- No streaming needed for target use case

### Error Handling

- **File not found:** Let `parse_bmad_file()` handle it (propagates FileNotFoundError)
- **Invalid epic format:** Return empty stories list (not an error)
- **Malformed story headers:** Log warning (use logger from module), skip that story
- **Missing estimates/status:** Set to None (optional fields)
- **Encoding issues:** Let `parse_bmad_file()` handle (assumes UTF-8)

```python
def _parse_story_sections(content: str) -> list[EpicStory]:
    # ... inside parsing loop ...
    try:
        # Parse story
    except Exception as e:
        logger.warning("Skipping malformed story header: %s", malformed_text)
        continue
```

### Patterns from Story 2.1 (for reference)

- Use `python-frontmatter` via `parse_bmad_file()` - don't reinvent
- Dataclass pattern: `@dataclass` with type hints
- Exception handling: Let FileNotFoundError propagate
- Return string paths: `path=str(path)` for consistency
- Test patterns: Use `tmp_path` fixture, real `docs/epics.md` tests, parametrized tests

---

## Technical Requirements

### Dependencies

**Already in pyproject.toml (no new dependencies needed):**
- `python-frontmatter` - used via `parse_bmad_file()`
- `pyyaml` - used by python-frontmatter

**Standard library:**
- `re` - regex for story header parsing
- `logging` - for warning messages
- `dataclasses` - for EpicStory, EpicDocument

### File Structure After Implementation

```
src/bmad_assist/
├── bmad/
│   ├── __init__.py        # Updated exports
│   └── parser.py          # Extended with EpicStory, EpicDocument, parse_epic_file
└── ...

tests/
├── bmad/
│   ├── __init__.py
│   ├── conftest.py        # Existing + new epic fixtures
│   ├── test_parser.py     # Existing Story 2.1 tests
│   └── test_epic_parser.py  # New Story 2.2 tests
└── ...
```

### Type Hints Required

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class EpicStory:
    number: str  # e.g., "2.1"
    title: str
    estimate: int | None
    status: str | None
    dependencies: list[str]
    completed_criteria: int | None
    total_criteria: int | None

@dataclass
class EpicDocument:
    epic_num: int | None
    title: str | None
    status: str | None
    stories: list[EpicStory]
    path: str

def parse_epic_file(path: str | Path) -> EpicDocument:
    ...
```

### Validation Commands

```bash
# Run all bmad tests
pytest tests/bmad/ -v

# Run only epic parser tests
pytest tests/bmad/test_epic_parser.py -v

# Coverage
pytest tests/bmad/ --cov=src/bmad_assist/bmad --cov-report=term-missing

# Type checking
mypy src/bmad_assist/bmad/

# Linting
ruff check src/bmad_assist/bmad/

# Format check
ruff format --check src/bmad_assist/bmad/
```

---

## Git Intelligence Summary

### Recent Commits (Last 5)

| Commit | Description | Relevant Pattern |
|--------|-------------|------------------|
| 2435a24 | feat(bmad): implement markdown frontmatter parser (Story 2.1) | Direct foundation for this story |
| 9621f61 | docs(story-2.1): complete Multi-LLM code review synthesis | Review workflow |
| 93aba31 | chore(prompts): update power-prompt templates | Power-prompts patterns |
| 1d0b673 | docs: update documentation and reorganize sprint artifacts | Doc organization |
| 4b22d35 | docs(story-2.1): complete Multi-LLM validation synthesis | Validation workflow |

### Files Modified in Story 2.1 (Foundation)

From commit 2435a24:
- `src/bmad_assist/bmad/__init__.py` - Module exports
- `src/bmad_assist/bmad/parser.py` - BmadDocument, parse_bmad_file
- `src/bmad_assist/core/exceptions.py` - ParserError
- `tests/bmad/conftest.py` - Test fixtures
- `tests/bmad/test_parser.py` - 46 tests

**Extend, don't duplicate:**
- Add to `parser.py`, don't create new file
- Add fixtures to existing `conftest.py`
- Create new test file `test_epic_parser.py`

---

## Architecture Compliance

### Stack Requirements
- **Language:** Python 3.11+
- **Dependencies:** None new (uses existing python-frontmatter via parse_bmad_file)
- **Standard library:** re, logging, dataclasses

### Structure Requirements
- **Location:** `src/bmad_assist/bmad/parser.py` (extend existing)
- **Tests:** `tests/bmad/test_epic_parser.py` (new file)
- **Exception:** Use existing `ParserError`

### Pattern Requirements
- Build on `parse_bmad_file()` - NO duplication
- Custom dataclasses with type hints
- Google-style docstrings
- Module exports via `__all__` in `__init__.py`
- Logging for non-critical warnings

### Testing Requirements
- pytest for testing framework
- pytest-cov for coverage (>= 95%)
- mypy for type checking
- ruff for linting

---

## Testing Requirements

### Unit Tests

**Test Classes:**
- `TestParseStandardStorySections` - AC1
- `TestExtractStoryEstimate` - AC2
- `TestParseEpicNoStories` - AC3
- `TestMalformedStoryHeaders` - AC4
- `TestExtractEpicMetadata` - AC5
- `TestConsolidatedEpicsFile` - AC6
- `TestDependencyExtraction` - AC7
- `TestReturnTypes` - AC8
- `TestStatusInference` - AC9
- `TestAcceptanceCriteriaCheckboxes` - AC10

### Edge Cases to Cover

1. **Story header variations:**
   - `## Story X.Y: Title` (h2)
   - `### Story X.Y: Title` (h3)
   - With/without trailing content
   - Numbers > 9 (e.g., Story 12.15)

2. **Estimate variations:**
   - `**Estimate:** 3 SP`
   - `**Story Points:** 3`
   - `**Estimate:** 3` (no SP suffix)
   - Missing estimate (None)

3. **Dependency variations:**
   - `**Dependencies:** Story 3.2, Story 3.4`
   - `**Dependencies:** 3.2, 3.4`
   - `**Dependencies:** Story 3.2 (title), Story 3.4`
   - No dependencies (empty list)

4. **Real files:**
   - `docs/epics.md` - consolidated file with all 9 epics
   - Parse and verify expected story count (60 stories)

### Mocking Strategy

- Use `tmp_path` fixture for test files (no mocking needed)
- Real file I/O for tests
- No mocking of `parse_bmad_file()` - test integration

---

## Verification Checklist

- [ ] `src/bmad_assist/bmad/parser.py` contains EpicStory, EpicDocument, parse_epic_file
- [ ] `src/bmad_assist/bmad/__init__.py` exports all new symbols
- [ ] `parse_epic_file()` uses `parse_bmad_file()` internally (no duplication)
- [ ] `tests/bmad/test_epic_parser.py` covers all 11 acceptance criteria (AC1-AC10 + AC9b)
- [ ] `pytest tests/bmad/` - all tests pass
- [ ] `pytest tests/bmad/ --cov=src/bmad_assist/bmad` - coverage >= 95%
- [ ] `mypy src/bmad_assist/bmad/` - no type errors
- [ ] `ruff check src/bmad_assist/bmad/` - no linting errors
- [ ] Real `docs/epics.md` parses correctly (60 stories expected)
- [ ] Story 2.1 tests still pass (no regressions)
- [ ] Multi-epic file returns epic_num=None, title=None, status=None (AC6)
- [ ] Logging tests pass (malformed headers trigger warnings with caplog)

---

## References

- [Source: docs/architecture.md#Project-Structure] - Module organization
- [Source: docs/architecture.md#Implementation-Patterns] - Naming conventions, error handling
- [Source: docs/epics.md#Story-2.2] - Original story requirements
- [Source: docs/prd.md#FR30] - System can extract story list and status from epic files
- [Source: docs/prd.md#FR27] - System can read current project state from BMAD files
- [Source: docs/prd.md#NFR6] - System must parse BMAD files in markdown and YAML formats
- [Source: docs/sprint-artifacts/2-1-markdown-frontmatter-parser.md] - Previous story patterns and learnings

---

## Dev Agent Record

### Context Reference
- Story ID: 2.2
- Story Key: 2-2-epic-file-parser
- Epic: 2 - BMAD File Integration
- Previous Story: 2.1 (review) - Markdown Frontmatter Parser

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - no debug issues encountered during implementation

### Completion Notes List

- ✅ Implemented EpicStory and EpicDocument dataclasses with full type hints
- ✅ parse_epic_file() builds on parse_bmad_file() - no code duplication
- ✅ Handles both `## Story X.Y:` (h2) and `### Story X.Y:` (h3) headers
- ✅ Handles both `# Epic N:` (h1) and `## Epic N:` (h2) epic headers for multi-epic detection
- ✅ Extracts estimates from `**Estimate:**` and `**Story Points:**` formats
- ✅ Extracts explicit status from `**Status:**` field
- ✅ Extracts dependencies from `**Dependencies:**` with various formats
- ✅ Counts checked/unchecked acceptance criteria checkboxes (case-insensitive [x]/[X])
- ✅ Multi-epic files return epic_num=None, title=None, status=None as per AC6
- ✅ Real docs/epics.md parses correctly: 60 stories extracted
- ✅ 36 new tests + 46 existing = 82 total tests passing
- ✅ 96% test coverage (exceeds 95% requirement)
- ✅ mypy: no type errors
- ✅ ruff: all checks passed
- ✅ Fixed pre-existing test (test_bmad_document_field_types) to work with PEP 563 annotations

### File List

**Files created:**
- `tests/bmad/test_epic_parser.py` - 36 tests covering AC1-AC10, AC9b, logging, and real file parsing

**Files modified:**
- `src/bmad_assist/bmad/parser.py` - Added EpicStory, EpicDocument, parse_epic_file, helper functions, and regex patterns
- `src/bmad_assist/bmad/__init__.py` - Updated exports for EpicStory, EpicDocument, parse_epic_file
- `tests/bmad/conftest.py` - Added 4 epic file fixtures (single_epic_file, consolidated_epics_file, epic_with_no_stories, epic_with_dependencies)
- `tests/bmad/test_parser.py` - Fixed test_bmad_document_field_types for PEP 563 compatibility
- `docs/sprint-artifacts/sprint-status.yaml` - Updated status to in-progress → review
- `docs/sprint-artifacts/2-2-epic-file-parser.md` - This file

### Change Log

- 2025-12-10: Story 2.2 implementation complete - Epic File Parser
  - All 8 tasks completed successfully
  - 36 new tests added, all passing
  - 96% test coverage achieved
  - Full validation passed (pytest, mypy, ruff)
  - Real docs/epics.md successfully parses 60 stories
- 2025-12-10 14:30: Master LLM validation synthesis - fixed all critical issues:
  - Added Quick Reference section for LLM scanability
  - Clarified AC6 multi-epic handling (epic_num=None, title=None, status=None)
  - Added AC9b for status priority rules (explicit Status field wins)
  - Added logging specification to Task 2.6 (logger name, message format)
  - Added missing tests (7.11, 7.13, 7.14) for status priority and logging
  - Added Required Imports section with `from __future__ import annotations`
  - Added Performance Constraints section
  - Consolidated "Previous Story Intelligence" into shorter "Patterns from Story 2.1"
  - Updated Task 4 with explicit return value specification
  - Updated Verification Checklist with 2 new items
- 2025-12-10: Story 2.2 created with comprehensive context for Epic File Parser implementation
