# Story 2.3: Project State Reader

**Status:** done
**Story Points:** 5

> **Scope Note:** This story includes optional sprint-status.yaml integration (AC10) as a practical extension beyond the core Epic 2 scope. The core functionality (AC1-AC9) fulfills FR27. Sprint-status integration is disabled by default (`use_sprint_status=False`).

---

## Quick Reference

**Module:** `src/bmad_assist/bmad/reconciler.py` (NEW file per architecture.md)
**New Exports:** `ProjectState`, `read_project_state`
**Foundation:** Build on `parse_epic_file()` from Story 2.2 and `parse_bmad_file()` from Story 2.1
**Key Patterns:** Dataclass for state, glob pattern matching for epic discovery
**Tests:** `tests/bmad/test_reconciler.py` - new test file
**Validation:** pytest (>=95% coverage), mypy (no errors), ruff (no warnings)

---

## Story

**As a** developer,
**I want** to read current project state from BMAD files,
**So that** the system understands project progress without manual input.

### Business Context

This story completes Epic 2 (BMAD File Integration) by providing the highest-level abstraction for reading project state. While Stories 2.1 and 2.2 provided low-level parsing capabilities, Story 2.3 aggregates that information into a unified `ProjectState` that represents the entire project's progress.

This is critical for:
- **FR27:** System can read current project state from BMAD files
- **FR28:** Enable discrepancy detection between internal state and BMAD files (Story 2.4 foundation)
- **FR4:** System can track current position in the loop (epic number, story number, phase)

The project state reader enables bmad-assist to:
1. Discover all epics in a BMAD project
2. Parse each epic file to extract story information
3. Compile a unified view of completed, in-progress, and backlog stories
4. Determine the current position in the development loop

This is the final piece needed before Epic 3 (State Management) can reconcile internal state with BMAD files.

### Success Criteria

- Discover and parse all BMAD epic files in a project
- Return structured ProjectState with all epics and stories
- Determine current epic/story position from story statuses
- Handle various project layouts (single epics.md vs. separate epic files)
- Build on existing parsers from Stories 2.1 and 2.2 - NO duplication
- Gracefully handle missing or malformed epic files

---

## Acceptance Criteria

### AC1: Discover epic files in project
```gherkin
Given a BMAD project with docs folder containing:
  - docs/epics.md (consolidated file)
  OR
  - docs/epic-1.md, docs/epic-2.md, etc. (separate files)
When read_project_state(bmad_path) is called
Then all epic files are discovered
And each epic file is parsed using parse_epic_file()
```

### AC2: Return ProjectState dataclass
```gherkin
Given read_project_state() completes successfully
When result is inspected
Then result is ProjectState dataclass with:
  - epics: list[EpicDocument] (parsed epic documents)
  - all_stories: list[EpicStory] (flattened list of all stories)
  - completed_stories: list[str] (story numbers with status="done")
  - current_epic: int | None (epic number of current work)
  - current_story: str | None (story number of current work, e.g., "2.3")
  - bmad_path: str (original path to BMAD docs)
```

### AC3: Compile completed stories list
```gherkin
Given epic files contain stories with various statuses:
  - Story 1.1: status="done"
  - Story 1.2: status="done"
  - Story 2.1: status="review"
  - Story 2.2: status="in-progress"
  - Story 2.3: status="backlog"
  - Story 2.4: status="ready-for-dev"
  - Story 2.5: status="drafted"
  - Story 2.6: (no status field)
When read_project_state() is called
Then completed_stories equals ["1.1", "1.2"]
And ONLY stories with status="done" are in completed_stories
And stories without status field are treated as status="backlog"
```

**Status Enumeration (complete list):**
- `done` → completed (in completed_stories)
- `review` → NOT completed
- `in-progress` → NOT completed
- `ready-for-dev` → NOT completed
- `drafted` → NOT completed
- `backlog` → NOT completed
- `(no status)` → treated as `backlog` (NOT completed)

### AC4: Determine current epic position
```gherkin
Given stories have these statuses:
  - Epic 1 stories: all "done"
  - Story 2.1: "done"
  - Story 2.2: "review"
  - Story 2.3: "backlog"
When read_project_state() is called
Then current_epic equals 2 (first epic with non-done stories)
```

### AC5: Determine current story position
```gherkin
Given stories have these statuses:
  - Story 2.1: "done"
  - Story 2.2: "review"
  - Story 2.3: "backlog"
When read_project_state() is called
Then current_story equals "2.2" (first non-done story in current epic)
```

### AC6: Handle consolidated epics.md file
```gherkin
Given project has single docs/epics.md with multiple epics
When read_project_state("docs") is called
Then single EpicDocument is returned in epics list
And all_stories contains stories from all epics
And current position is determined correctly across epics
```

### AC7: Handle separate epic files
```gherkin
Given project has separate epic files:
  - docs/epic-1.md
  - docs/epic-2.md
  - docs/epic-3.md
When read_project_state("docs") is called
Then epics list contains 3 EpicDocument objects
And all_stories is merged from all epics
And stories are ordered by epic number, then story number
```

### AC8: Handle missing epic files gracefully
```gherkin
Given BMAD path exists but contains no epic files
When read_project_state(bmad_path) is called
Then ProjectState is returned with:
  - epics: []
  - all_stories: []
  - completed_stories: []
  - current_epic: None
  - current_story: None
And no error is raised
```

### AC9: Handle invalid BMAD path
```gherkin
Given BMAD path does not exist
When read_project_state("/nonexistent/path") is called
Then FileNotFoundError is raised
And error message contains the path
```

### AC10: Handle malformed epic files gracefully
```gherkin
Given BMAD path contains:
  - docs/epic-1.md (valid)
  - docs/epic-2.md (malformed YAML frontmatter)
  - docs/epic-3.md (valid)
When read_project_state(bmad_path) is called
Then ProjectState is returned with epics [1, 3]
And warning is logged for epic-2.md
And no error is raised (graceful degradation)
```

### AC11: Handle stories without status field
```gherkin
Given epic file contains story with no status field
When read_project_state() is called
Then story is assigned status="backlog" by default
And story is NOT in completed_stories
And story is considered for current position determination
```

### AC12: Handle both consolidated and separate epic files
```gherkin
Given project has BOTH:
  - docs/epics.md (consolidated, contains Epic 1, Epic 2)
  - docs/epic-3.md (separate file)
When read_project_state("docs") is called
Then all stories from all files are merged
And duplicates are not created (unique by story number)
And stories are sorted by epic number, then story number
```

### AC13: Determine position from sprint-status.yaml if available (OPTIONAL EXTENSION)
```gherkin
Given project has sprint-status.yaml with development_status section
When read_project_state() is called with use_sprint_status=True
Then current position is determined from sprint-status.yaml statuses
And takes precedence over embedded story statuses
```
**Note:** This AC is disabled by default (`use_sprint_status=False`). It extends beyond core Epic 2 scope.

### AC14: Handle malformed sprint-status.yaml gracefully
```gherkin
Given project has sprint-status.yaml that is malformed (invalid YAML or wrong structure)
When read_project_state() is called with use_sprint_status=True
Then warning is logged for malformed file
And fallback to embedded story statuses is used
And no error is raised
```

### AC15: ProjectState field invariants
```gherkin
Given read_project_state() completes successfully
Then the following invariants hold:
  - If current_epic is None, then current_story MUST be None
  - If current_story is not None, then current_epic MUST match story's epic
  - completed_stories only contains story numbers from all_stories
  - all_stories is sorted by (epic_num, story_num)
```

---

## Tasks / Subtasks

- [x] Task 1: Create module structure (AC2)
  - [x] 1.1 Create `src/bmad_assist/bmad/reconciler.py`
  - [x] 1.2 Create ProjectState dataclass with all fields
  - [x] 1.3 Add type hints and Google-style docstrings

- [x] Task 2: Implement epic file discovery (AC1, AC6, AC7)
  - [x] 2.1 Create `_discover_epic_files()` helper function
  - [x] 2.2 Handle consolidated `epics.md` pattern (glob: `*epic*.md`)
  - [x] 2.3 Handle separate `epic-N.md` pattern (glob: `epic-*.md`)
  - [x] 2.4 Return list of discovered file paths

- [x] Task 3: Implement read_project_state function (AC2, AC3, AC4, AC5)
  - [x] 3.1 Call `_discover_epic_files()` to find epic files
  - [x] 3.2 Parse each file with `parse_epic_file()` from Story 2.2
  - [x] 3.3 Flatten all stories into `all_stories` list
  - [x] 3.4 Sort stories by epic number, then story number
  - [x] 3.5 Compile `completed_stories` (filter status="done")
  - [x] 3.6 Determine `current_epic` (first epic with non-done stories)
  - [x] 3.7 Determine `current_story` (first non-done story in current epic)
  - [x] 3.8 Return ProjectState

- [x] Task 4: Handle edge cases (AC8, AC9, AC10, AC11, AC12, AC15)
  - [x] 4.1 Handle missing BMAD path (raise FileNotFoundError)
  - [x] 4.2 Handle empty BMAD directory (return empty ProjectState)
  - [x] 4.3 Handle malformed epic files (log warning, skip file, continue - AC10)
  - [x] 4.4 Handle path as string or Path object
  - [x] 4.5 Handle stories without status field (default to "backlog" - AC11)
  - [x] 4.6 Handle both consolidated and separate epic files (merge, dedupe - AC12)
  - [x] 4.7 Enforce ProjectState field invariants (AC15)

- [x] Task 5: Implement sprint-status.yaml integration (AC13, AC14) - OPTIONAL EXTENSION
  - [x] 5.1 Create `_load_sprint_status()` helper function
  - [x] 5.2 Parse sprint-status.yaml if exists
  - [x] 5.3 Use sprint-status statuses when `use_sprint_status=True`
  - [x] 5.4 Fall back to embedded story statuses if file doesn't exist
  - [x] 5.5 Handle malformed sprint-status.yaml (log warning, fallback - AC14)
  - [x] 5.6 Validate development_status is dict, not list

- [x] Task 6: Update module exports
  - [x] 6.1 Create `bmad/reconciler.py` with exports
  - [x] 6.2 Update `bmad/__init__.py` to export ProjectState, read_project_state
  - [x] 6.3 Update `__all__` list

- [x] Task 7: Write tests
  - [x] 7.1 Create `tests/bmad/test_reconciler.py`
  - [x] 7.2 Test AC1: Epic file discovery (consolidated and separate)
  - [x] 7.3 Test AC2: ProjectState dataclass structure
  - [x] 7.4 Test AC3: Completed stories compilation with all status values
  - [x] 7.5 Test AC4: Current epic determination
  - [x] 7.6 Test AC5: Current story determination
  - [x] 7.7 Test AC6: Consolidated epics.md handling
  - [x] 7.8 Test AC7: Separate epic files handling
  - [x] 7.9 Test AC8: Missing epic files (empty project)
  - [x] 7.10 Test AC9: Invalid BMAD path
  - [x] 7.11 Test AC10: Malformed epic files (log warning, skip, continue)
  - [x] 7.12 Test AC11: Stories without status field (default to backlog)
  - [x] 7.13 Test AC12: Both consolidated and separate epic files (merge, dedupe)
  - [x] 7.14 Test AC13: Sprint-status.yaml integration (optional)
  - [x] 7.15 Test AC14: Malformed sprint-status.yaml (fallback)
  - [x] 7.16 Test AC15: ProjectState field invariants
  - [x] 7.17 Test with real `docs/` folder from this project
  - [x] 7.18 Test story ordering (by epic, then story number)

- [x] Task 8: Validation
  - [x] 8.1 `pytest tests/bmad/` - all tests pass (150 tests)
  - [x] 8.2 `pytest --cov=src/bmad_assist/bmad` - coverage 97% (>= 95%)
  - [x] 8.3 `mypy src/bmad_assist/bmad/` - no type errors
  - [x] 8.4 `ruff check src/bmad_assist/bmad/` - no linting errors

---

## Dev Notes

### Architecture Compliance

**From architecture.md:**
- Module location: `src/bmad_assist/bmad/reconciler.py` (per architecture.md mapping)
- Pattern: Build on `parse_epic_file()` - DO NOT duplicate parsing logic
- Exception: Use existing `ParserError` for parsing failures
- Naming: snake_case functions, PascalCase classes (ProjectState)

**Architecture Reference:**
```
bmad/
├── __init__.py
├── parser.py           # Stories 2.1 + 2.2 (BmadDocument, EpicStory, EpicDocument)
└── reconciler.py       # Story 2.3 (ProjectState, read_project_state)
                        # Stories 2.4 + 2.5 (discrepancy detection/correction)
```

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
from .reconciler import (
    ProjectState,
    read_project_state,
)

__all__ = [
    "BmadDocument",
    "parse_bmad_file",
    "EpicStory",
    "EpicDocument",
    "parse_epic_file",
    "ProjectState",
    "read_project_state",
]
```

### Required Imports

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from bmad_assist.bmad.parser import EpicDocument, EpicStory, parse_epic_file
from bmad_assist.core.exceptions import ParserError

logger = logging.getLogger(__name__)
```

### Implementation Strategy

**Build on Story 2.2 foundation:**
```python
def read_project_state(
    bmad_path: str | Path,
    use_sprint_status: bool = False,  # Disabled by default (optional extension beyond Epic 2 scope)
) -> ProjectState:
    """Read current project state from BMAD files.

    Discovers and parses all epic files in the BMAD project, compiling
    a unified view of project progress including completed stories and
    current position.

    Args:
        bmad_path: Path to BMAD documentation directory (e.g., "docs").
        use_sprint_status: If True, use sprint-status.yaml for story statuses.
            Disabled by default as this is an optional extension beyond core Epic 2 scope.

    Returns:
        ProjectState with all epics, stories, and current position.

    Raises:
        FileNotFoundError: If bmad_path does not exist.

    """
    bmad_path = Path(bmad_path)

    if not bmad_path.exists():
        raise FileNotFoundError(f"BMAD path does not exist: {bmad_path}")

    # Step 1: Discover epic files
    epic_files = _discover_epic_files(bmad_path)

    if not epic_files:
        return ProjectState(
            epics=[],
            all_stories=[],
            completed_stories=[],
            current_epic=None,
            current_story=None,
            bmad_path=str(bmad_path),
        )

    # Step 2: Parse each epic file
    epics = []
    for epic_file in epic_files:
        try:
            epic_doc = parse_epic_file(epic_file)
            epics.append(epic_doc)
        except Exception as e:
            logger.warning("Failed to parse epic file %s: %s", epic_file, e)
            continue

    # Step 3: Flatten and sort all stories
    all_stories = _flatten_stories(epics)

    # Step 4: Load sprint-status.yaml if available
    if use_sprint_status:
        sprint_statuses = _load_sprint_status(bmad_path)
        if sprint_statuses:
            all_stories = _apply_sprint_statuses(all_stories, sprint_statuses)

    # Step 5: Compile completed stories
    completed_stories = [s.number for s in all_stories if s.status == "done"]

    # Step 6: Determine current position
    current_epic, current_story = _determine_current_position(all_stories)

    return ProjectState(
        epics=epics,
        all_stories=all_stories,
        completed_stories=completed_stories,
        current_epic=current_epic,
        current_story=current_story,
        bmad_path=str(bmad_path),
    )
```

### Epic File Discovery Strategy

**Glob patterns to check (in order):**
1. `*epic*.md` - matches both `epics.md` and `epic-1.md`, `epic-2.md`
2. Filter out non-epic files (e.g., `epic-retrospective.md`)

```python
def _discover_epic_files(bmad_path: Path) -> list[Path]:
    """Discover epic files in BMAD directory.

    Searches for epic files using glob patterns and returns them
    sorted for consistent ordering.

    Args:
        bmad_path: Path to BMAD documentation directory.

    Returns:
        List of discovered epic file paths, sorted alphabetically.

    """
    # Find all potential epic files
    epic_files = list(bmad_path.glob("*epic*.md"))

    # Filter out retrospectives and other non-epic files
    epic_files = [
        f for f in epic_files
        if "retrospective" not in f.name.lower()
        and f.is_file()
    ]

    # Sort for consistent ordering
    return sorted(epic_files)
```

### Sprint-Status.yaml Integration

**Sprint-status.yaml format (from current project):**
```yaml
development_status:
  epic-1: in-progress
  1-1-project-initialization-with-pyproject-toml: done
  1-2-pydantic-configuration-models: review
  2-1-markdown-frontmatter-parser: review
  2-2-epic-file-parser: review
  2-3-project-state-reader: backlog
```

**Status mapping:**
- Sprint-status key format: `{epic}-{story}-{slug}` (e.g., `2-1-markdown-frontmatter-parser`)
- Story number extraction: first two numbers (e.g., `2-1` → `2.1`)

```python
def _load_sprint_status(bmad_path: Path) -> dict[str, str] | None:
    """Load story statuses from sprint-status.yaml if available.

    Args:
        bmad_path: Path to BMAD documentation directory.

    Returns:
        Dict mapping story numbers to statuses, or None if file doesn't exist.

    """
    # Check both sprint-artifacts location and docs root
    possible_paths = [
        bmad_path / "sprint-artifacts" / "sprint-status.yaml",
        bmad_path / "sprint-status.yaml",
    ]

    for status_path in possible_paths:
        if status_path.exists():
            try:
                with open(status_path) as f:
                    data = yaml.safe_load(f)
                return _parse_sprint_statuses(data.get("development_status", {}))
            except Exception as e:
                logger.warning("Failed to load sprint-status.yaml: %s", e)
                return None

    return None
```

### Story Sorting Algorithm

**Sort key: (epic_num, story_num)**
```python
def _sort_key(story: EpicStory) -> tuple[int, int]:
    """Generate sort key for story ordering."""
    parts = story.number.split(".")
    return (int(parts[0]), int(parts[1]))

all_stories = sorted(all_stories, key=_sort_key)
```

### Current Position Determination

**Algorithm:**
1. Find first story that is NOT "done"
2. Extract epic number from that story's number
3. That's the current epic and current story

```python
def _determine_current_position(
    stories: list[EpicStory],
) -> tuple[int | None, str | None]:
    """Determine current epic and story from story list.

    Returns:
        Tuple of (current_epic, current_story) or (None, None) if all done.

    """
    for story in stories:
        if story.status != "done":
            epic_num = int(story.number.split(".")[0])
            return (epic_num, story.number)

    # All stories done
    return (None, None)
```

### Error Handling

- **BMAD path not found:** Raise `FileNotFoundError` with path in message
- **No epic files found:** Return empty ProjectState (not an error)
- **Epic file parse failure:** Log warning, skip file, continue with others (AC10)
- **Story without status field:** Assign `status="backlog"` by default (AC11)
- **Both consolidated and separate epic files:** Merge all, deduplicate by story number (AC12)
- **Sprint-status.yaml missing:** Fall back to embedded story statuses (AC13)
- **Sprint-status.yaml malformed:** Log warning, fall back to embedded statuses (AC14)
- **Sprint-status development_status is not dict:** Log warning, fall back to embedded statuses

### Performance Constraints

**Expected File Sizes:**
- Typical project: 1-10 epic files
- Each epic file: <50KB
- sprint-status.yaml: <10KB

**Performance Target:**
- Parse entire project state in <500ms on standard hardware

**Memory Profile:**
- All epic documents held in memory (acceptable - total <1MB)
- Stories list typically <1000 items

---

## Technical Requirements

### Dependencies

**Already in pyproject.toml:**
- `pyyaml` - for sprint-status.yaml parsing
- No new dependencies needed

**Standard library:**
- `pathlib` - path handling
- `logging` - for warning messages
- `dataclasses` - for ProjectState

### File Structure After Implementation

```
src/bmad_assist/
├── bmad/
│   ├── __init__.py        # Updated exports
│   ├── parser.py          # Stories 2.1 + 2.2 (unchanged)
│   └── reconciler.py      # NEW: Story 2.3 (ProjectState, read_project_state)
└── ...

tests/
├── bmad/
│   ├── __init__.py
│   ├── conftest.py        # Existing + new project fixtures
│   ├── test_parser.py     # Story 2.1 tests
│   ├── test_epic_parser.py  # Story 2.2 tests
│   └── test_reconciler.py   # NEW: Story 2.3 tests
└── ...
```

### Type Hints Required

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ProjectState:
    """Complete project state from BMAD files.

    Attributes:
        epics: List of parsed EpicDocument objects.
        all_stories: Flattened list of all stories, sorted by number.
        completed_stories: List of story numbers with status "done".
        current_epic: Number of the current epic (first with non-done stories).
        current_story: Number of the current story (first non-done).
        bmad_path: Path to BMAD documentation directory.

    """
    epics: list[EpicDocument]
    all_stories: list[EpicStory]
    completed_stories: list[str]
    current_epic: int | None
    current_story: str | None
    bmad_path: str

def read_project_state(
    bmad_path: str | Path,
    use_sprint_status: bool = False,  # Disabled by default (optional extension)
) -> ProjectState:
    ...
```

### Validation Commands

```bash
# Run all bmad tests
pytest tests/bmad/ -v

# Run only reconciler tests
pytest tests/bmad/test_reconciler.py -v

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
| 979ce7a | fix(bmad): correct STATUS_PATTERN for multi-word statuses | Regex pattern fix from code review |
| 473c4dc | feat(bmad): implement epic file parser (Story 2.2) | Direct foundation - reuse parse_epic_file |
| 2435a24 | feat(bmad): implement markdown frontmatter parser (Story 2.1) | Foundation for all BMAD parsing |
| 7582704 | docs(story-2.2): complete Multi-LLM validation synthesis | Multi-LLM review workflow |
| 3ca87b6 | docs(story-2.2): create Epic File Parser story with comprehensive context | Story documentation pattern |

### Files Modified in Story 2.2 (Direct Dependency)

From commit 473c4dc:
- `src/bmad_assist/bmad/__init__.py` - Module exports (will extend)
- `src/bmad_assist/bmad/parser.py` - EpicDocument, EpicStory, parse_epic_file (will use)
- `tests/bmad/conftest.py` - Test fixtures (will extend)

**Reuse patterns:**
- Use `parse_epic_file()` directly - no duplication
- Follow same test fixture patterns in conftest.py
- Same validation commands and coverage requirements

### Established Testing Patterns

From Story 2.1 and 2.2:
- Use `tmp_path` fixture for creating test directories/files
- Test with real project files (`docs/`) for integration
- Parametrized tests for multiple scenarios
- Use `caplog` fixture for logging assertions
- Coverage >= 95% required

---

## Architecture Compliance

### Stack Requirements
- **Language:** Python 3.11+
- **Dependencies:** pyyaml (already in pyproject.toml)
- **Standard library:** pathlib, logging, dataclasses

### Structure Requirements
- **Location:** `src/bmad_assist/bmad/reconciler.py` (NEW file per architecture)
- **Tests:** `tests/bmad/test_reconciler.py` (NEW file)
- **Exception:** Use existing `ParserError` from core/exceptions.py

### Pattern Requirements
- Build on `parse_epic_file()` from Story 2.2 - NO duplication
- Custom dataclasses with type hints
- Google-style docstrings
- Module exports via `__all__` in `__init__.py`
- Logging for non-critical warnings (use `logger = logging.getLogger(__name__)`)

### Testing Requirements
- pytest for testing framework
- pytest-cov for coverage (>= 95%)
- mypy for type checking
- ruff for linting

---

## Testing Requirements

### Unit Tests

**Test Classes:**
- `TestDiscoverEpicFiles` - AC1, file discovery
- `TestProjectStateDataclass` - AC2, return type
- `TestCompletedStories` - AC3, status filtering (all status values)
- `TestCurrentEpicDetermination` - AC4
- `TestCurrentStoryDetermination` - AC5
- `TestConsolidatedEpicsHandling` - AC6
- `TestSeparateEpicFilesHandling` - AC7
- `TestEmptyProject` - AC8
- `TestInvalidBmadPath` - AC9
- `TestMalformedEpicFiles` - AC10, graceful degradation
- `TestStoriesWithoutStatus` - AC11, default to backlog
- `TestMixedEpicLayouts` - AC12, merge consolidated + separate
- `TestSprintStatusIntegration` - AC13, optional extension
- `TestMalformedSprintStatus` - AC14, fallback behavior
- `TestFieldInvariants` - AC15, dataclass constraints
- `TestRealProject` - Integration with real docs/

### Edge Cases to Cover

1. **Project layouts:**
   - Single `epics.md` file (consolidated) - AC6
   - Separate `epic-1.md`, `epic-2.md`, etc. - AC7
   - **BOTH consolidated AND separate (merge, deduplicate)** - AC12

2. **Story statuses:**
   - All done (current_epic=None, current_story=None)
   - All backlog (current is first story)
   - Mixed statuses (various combinations)
   - **No status field → treat as "backlog"** - AC11
   - All valid statuses: done, review, in-progress, ready-for-dev, drafted, backlog - AC3

3. **Sprint-status integration (AC13, AC14):**
   - File exists with valid data
   - File exists but malformed YAML → log warning, fallback
   - File doesn't exist → fall back to embedded
   - **development_status is list, not dict** → log warning, fallback
   - Status key format variations

4. **Error scenarios:**
   - BMAD path doesn't exist - AC9
   - BMAD path exists but no epic files - AC8
   - **Epic file exists but malformed → log warning, skip, continue** - AC10
   - Permission denied on file read → raise error

5. **Field invariants (AC15):**
   - current_epic=None → current_story=None
   - current_story set → current_epic must match
   - completed_stories subset of all_stories
   - all_stories sorted by (epic, story)

6. **Real project:**
   - Test with actual `docs/` from this project
   - Verify 60 stories discovered
   - Verify correct current position

### Mocking Strategy

- Use `tmp_path` fixture for test directories (no mocking needed)
- Real file I/O for tests
- No mocking of `parse_epic_file()` - test integration
- Create mock sprint-status.yaml files in test directories

---

## Verification Checklist

- [ ] `src/bmad_assist/bmad/reconciler.py` contains ProjectState, read_project_state
- [ ] `src/bmad_assist/bmad/__init__.py` exports all new symbols
- [ ] `read_project_state()` uses `parse_epic_file()` internally (no duplication)
- [ ] `tests/bmad/test_reconciler.py` covers all 15 acceptance criteria
- [ ] `pytest tests/bmad/` - all tests pass (existing + new)
- [ ] `pytest tests/bmad/ --cov=src/bmad_assist/bmad` - coverage >= 95%
- [ ] `mypy src/bmad_assist/bmad/` - no type errors
- [ ] `ruff check src/bmad_assist/bmad/` - no linting errors
- [ ] Real `docs/` folder parses correctly (60 stories, correct position)
- [ ] Stories 2.1 and 2.2 tests still pass (no regressions)
- [ ] Sprint-status.yaml integration works when enabled (`use_sprint_status=True`)
- [ ] Empty project returns valid (empty) ProjectState
- [ ] Malformed epic files are skipped with warning (AC10)
- [ ] Stories without status default to "backlog" (AC11)
- [ ] Both consolidated and separate epics merge correctly (AC12)
- [ ] Malformed sprint-status.yaml falls back gracefully (AC14)
- [ ] ProjectState field invariants hold (AC15)

---

## References

- [Source: docs/architecture.md#Project-Structure] - Module organization (bmad/reconciler.py)
- [Source: docs/architecture.md#Implementation-Patterns] - Naming conventions, error handling
- [Source: docs/epics.md#Story-2.3] - Original story requirements
- [Source: docs/prd.md#FR27] - System can read current project state from BMAD files
- [Source: docs/prd.md#FR28] - System can detect discrepancies (foundation)
- [Source: docs/prd.md#NFR6] - System must parse BMAD files in markdown and YAML formats
- [Source: docs/sprint-artifacts/2-1-markdown-frontmatter-parser.md] - Story 2.1 patterns
- [Source: docs/sprint-artifacts/2-2-epic-file-parser.md] - Story 2.2 patterns and learnings
- [Source: docs/sprint-artifacts/sprint-status.yaml] - Sprint status file format

---

## Dev Agent Record

### Context Reference
- Story ID: 2.3
- Story Key: 2-3-project-state-reader
- Epic: 2 - BMAD File Integration
- Previous Story: 2.2 (review) - Epic File Parser

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - no debug issues encountered

### Completion Notes List

✅ **Story 2.3 Implementation Complete**

**Implementation Approach:**
- Built on `parse_epic_file()` from Story 2.2 - no parsing logic duplication
- Created `reconciler.py` module with `ProjectState` dataclass and `read_project_state()` function
- Implemented 9 helper functions for clean separation of concerns
- All 15 acceptance criteria implemented and tested

**Key Implementation Decisions:**
1. Used dataclass for `ProjectState` with immutable semantics
2. Stories without explicit status default to "backlog" (AC11)
3. Deduplicate stories by number when merging consolidated + separate files (AC12)
4. Sprint-status integration disabled by default (`use_sprint_status=False`)
5. Malformed epic files are skipped with warning (graceful degradation)

**Test Coverage:**
- 67 new tests in `test_reconciler.py`
- 150 total tests in bmad/ module
- 97% code coverage

### File List

**Files created:**
- `src/bmad_assist/bmad/reconciler.py` - ProjectState dataclass and read_project_state function (398 lines)
- `tests/bmad/test_reconciler.py` - Comprehensive test suite for all 15 acceptance criteria (817 lines)

**Files modified:**
- `src/bmad_assist/bmad/__init__.py` - Added exports for ProjectState, read_project_state
- `docs/sprint-artifacts/sprint-status.yaml` - Updated status to review
- `docs/sprint-artifacts/2-3-project-state-reader.md` - Updated with completion details

### Change Log

- 2025-12-10: Story 2.3 created with comprehensive context for Project State Reader implementation
- 2025-12-10: **Master LLM Validation Synthesis** - Applied Multi-LLM review feedback:
  - Increased estimate from 3 SP to 5 SP (realistic for scope)
  - Added scope note clarifying sprint-status integration is optional extension
  - Changed `use_sprint_status` default from True to False (truly optional)
  - Added AC10: Handle malformed epic files gracefully
  - Added AC11: Handle stories without status field (default to backlog)
  - Added AC12: Handle both consolidated and separate epic files (merge, dedupe)
  - Renamed AC10 → AC13: Sprint-status.yaml integration (optional extension)
  - Added AC14: Handle malformed sprint-status.yaml gracefully
  - Added AC15: ProjectState field invariants
  - Expanded AC3 with complete status enumeration
  - Updated Tasks 4, 5, 7 with new subtasks for new ACs
  - Updated Test Classes and Edge Cases sections
  - Updated Verification Checklist with all 15 ACs
- 2025-12-10: **Implementation Complete (Claude Opus 4.5)**
  - Created reconciler.py with ProjectState, read_project_state, and 9 helper functions
  - All 15 ACs implemented: epic discovery, story aggregation, status handling, current position
  - 67 tests covering all acceptance criteria and edge cases
  - 97% code coverage, mypy clean, ruff clean
  - All 150 bmad tests pass, all 444 project tests pass
