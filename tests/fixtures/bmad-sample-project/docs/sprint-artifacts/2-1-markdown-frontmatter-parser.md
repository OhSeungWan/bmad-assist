# Story 2.1: Markdown Frontmatter Parser

**Status:** Ready for Review
**Story Points:** 2

---

## Story

**As a** developer,
**I want** to parse BMAD markdown files with YAML frontmatter,
**So that** I can extract metadata without using an LLM.

### Business Context

Epic 2 begins BMAD File Integration - the system's ability to understand project documentation (PRD, architecture, epics, stories) without invoking LLMs. This is foundational for:
- FR27: Reading current project state from BMAD files
- FR28: Detecting discrepancies between internal state and BMAD files
- FR30: Extracting story list and status from epic files

The markdown frontmatter parser is the lowest-level building block that all subsequent BMAD parsing depends on.

### Success Criteria

- BMAD markdown files with YAML frontmatter parse correctly
- Frontmatter is returned as a dictionary
- Markdown content is returned separately
- Invalid frontmatter raises clear ParserError
- Files without frontmatter are handled gracefully
- No LLM calls - pure deterministic parsing

---

## Acceptance Criteria

### AC1: Parse valid frontmatter
```gherkin
Given a markdown file with YAML frontmatter exists:
  """
  ---
  title: PRD Document
  status: complete
  date: 2025-12-08
  ---

  # Content here
  """
When parse_bmad_file(path) is called
Then frontmatter dict contains {"title": "PRD Document", "status": "complete", "date": "2025-12-08"}
And content string equals "\n# Content here\n"
```

### AC2: Parse file without frontmatter
```gherkin
Given a markdown file without frontmatter:
  """
  # Just Content

  Some markdown text.
  """
When parse_bmad_file(path) is called
Then frontmatter dict is empty {}
And content string equals "# Just Content\n\nSome markdown text.\n"
```

### AC3: Handle malformed frontmatter
```gherkin
Given a markdown file with invalid YAML frontmatter:
  """
  ---
  invalid: [unclosed bracket
  ---
  """
When parse_bmad_file(path) is called
Then ParserError is raised
And error message contains file path
And error message indicates YAML parsing failed
```

### AC4: Handle missing file
```gherkin
Given no file exists at /path/to/missing.md
When parse_bmad_file("/path/to/missing.md") is called
Then FileNotFoundError is raised
And error message contains the file path
```

### AC5: Handle complex frontmatter types
```gherkin
Given a markdown file with complex YAML frontmatter:
  """
  ---
  stepsCompleted: [1, 2, 3, 4]
  inputDocuments:
    - docs/prd.md
    - docs/architecture.md
  metadata:
    author: Pawel
    validated: true
  ---
  """
When parse_bmad_file(path) is called
Then frontmatter["stepsCompleted"] equals [1, 2, 3, 4]
And frontmatter["inputDocuments"] equals ["docs/prd.md", "docs/architecture.md"]
And frontmatter["metadata"]["author"] equals "Pawel"
And frontmatter["metadata"]["validated"] equals True
```

### AC6: Handle empty frontmatter
```gherkin
Given a markdown file with empty frontmatter:
  """
  ---
  ---

  # Content
  """
When parse_bmad_file(path) is called
Then frontmatter dict is empty {}
And content string equals "\n# Content\n"
```

### AC7: Return type consistency
```gherkin
Given parse_bmad_file returns a result
When result is inspected
Then result is a BmadDocument dataclass with:
  - frontmatter: dict[str, Any]
  - content: str
  - path: str (original file path)
```

### AC8: Handle `---` delimiters in content
```gherkin
Given a markdown file with --- delimiters in content:
  """
  ---
  title: Architecture Doc
  ---

  ## Code Example

  ```yaml
  ---
  config: value
  ---
  ```

  ---

  More content after horizontal rule.
  """
When parse_bmad_file(path) is called
Then frontmatter contains only {"title": "Architecture Doc"}
And content preserves all --- delimiters in code blocks and text
```

---

## Tasks / Subtasks

- [x] Task 1: Create module structure
  - [x] 1.1 Create `src/bmad_assist/bmad/` directory
  - [x] 1.2 Create `src/bmad_assist/bmad/__init__.py`
  - [x] 1.3 Create `src/bmad_assist/bmad/parser.py`
  - [x] 1.4 Add `ParserError` to `core/exceptions.py`

- [x] Task 2: Implement BmadDocument dataclass
  - [x] 2.1 Define BmadDocument in `bmad/parser.py`
  - [x] 2.2 Fields: frontmatter (dict), content (str), path (str)
  - [x] 2.3 Add type hints and docstring

- [x] Task 3: Implement parse_bmad_file function
  - [x] 3.1 Read file contents (handle FileNotFoundError)
  - [x] 3.2 Detect frontmatter delimiters (---)
  - [x] 3.3 Extract and parse YAML frontmatter (handle yaml.YAMLError)
  - [x] 3.4 Return BmadDocument instance
  - [x] 3.5 Handle files without frontmatter
  - [x] 3.6 Handle empty frontmatter

- [x] Task 4: Write tests
  - [x] 4.1 Create `tests/bmad/` directory
  - [x] 4.2 Create `tests/bmad/__init__.py`
  - [x] 4.3 Create `tests/bmad/test_parser.py`
  - [x] 4.4 Test AC1: Valid frontmatter parsing
  - [x] 4.5 Test AC2: File without frontmatter
  - [x] 4.6 Test AC3: Malformed YAML frontmatter
  - [x] 4.7 Test AC4: Missing file
  - [x] 4.8 Test AC5: Complex frontmatter types (lists, nested dicts)
  - [x] 4.9 Test AC6: Empty frontmatter
  - [x] 4.10 Test AC7: Return type validation (BmadDocument dataclass)
  - [x] 4.11 Test AC8: Content with `---` delimiters (code blocks, horizontal rules)

- [x] Task 5: Validation
  - [x] 5.1 `pytest tests/bmad/` - all tests pass (46 tests)
  - [x] 5.2 `pytest --cov=src/bmad_assist/bmad` - coverage 100%
  - [x] 5.3 `mypy src/bmad_assist/bmad/` - no type errors
  - [x] 5.4 `ruff check src/bmad_assist/bmad/` - no linting errors

---

## Dev Notes

### Architecture Compliance

**From architecture.md:**
- Module location: `src/bmad_assist/bmad/parser.py`
- Exception: `ParserError` inherits from `BmadAssistError`
- Pattern: Google-style docstrings, type hints on all functions
- Naming: snake_case functions, PascalCase classes

**Module Organization Pattern:**
```python
# bmad/__init__.py
from .parser import BmadDocument, parse_bmad_file

__all__ = ["BmadDocument", "parse_bmad_file"]
```

### Library Requirements

**Use python-frontmatter (already in pyproject.toml):**
```python
import frontmatter

# This library handles:
# - Frontmatter detection (--- delimiters)
# - YAML parsing
# - Content separation
```

**Why python-frontmatter:**
- Already specified in architecture as core dependency
- Battle-tested for markdown frontmatter parsing
- Handles edge cases (empty frontmatter, no frontmatter)
- Returns Post object with .metadata and .content

### Implementation Strategy

**Option A (Recommended): Use python-frontmatter directly**
```python
import frontmatter
from pathlib import Path
from dataclasses import dataclass
from typing import Any

@dataclass
class BmadDocument:
    """Parsed BMAD document with frontmatter and content."""
    frontmatter: dict[str, Any]
    content: str
    path: str

def parse_bmad_file(path: str | Path) -> BmadDocument:
    """Parse a BMAD markdown file with YAML frontmatter."""
    path = Path(path)

    try:
        post = frontmatter.load(path)
    except FileNotFoundError:
        raise  # Let it propagate
    except Exception as e:
        raise ParserError(f"Failed to parse {path}: {e}") from e

    return BmadDocument(
        frontmatter=dict(post.metadata),
        content=post.content,
        path=str(path)
    )
```

**Edge Case Handling:**
- File not found: Let `FileNotFoundError` propagate (natural Python behavior)
- Invalid YAML: Wrap in `ParserError` with file path context
- No frontmatter: `frontmatter` library returns empty metadata dict
- Empty frontmatter: Same as no frontmatter (empty dict)

### Error Message Format

Follow exception patterns from Epic 1:
```python
class ParserError(BmadAssistError):
    """BMAD file parsing error.

    Raised when:
    - YAML frontmatter is malformed
    - File encoding issues occur
    - Unexpected parsing failures
    """
    pass
```

**Error message pattern:**
```
ParserError: Failed to parse {path}: {original_error}
```

Example messages:
- `ParserError: Failed to parse /path/to/file.md: expected '<document start>', but found '<scalar>'`
- `ParserError: Failed to parse /path/to/file.md: 'utf-8' codec can't decode byte...`

### Test Structure

```
tests/
├── bmad/
│   ├── __init__.py
│   ├── conftest.py      # Fixtures for sample BMAD files
│   └── test_parser.py   # All AC tests
```

**Sample Test Fixture:**
```python
@pytest.fixture
def sample_bmad_file(tmp_path: Path) -> Path:
    """Create a sample BMAD file with frontmatter."""
    content = """---
title: Test Document
status: draft
---

# Test Content

Some markdown text.
"""
    path = tmp_path / "test.md"
    path.write_text(content)
    return path
```

### Previous Story Patterns (from Story 1.8)

**Test File Guidelines:**
- Target < 500 lines per file
- Use fixtures from conftest.py for sample data
- Each AC should have dedicated test class or clear grouping
- Use parametrized tests for multiple scenarios

**Fixture Extraction Rules (from Story 1.8 notes):**
- Extract to conftest.py IF used in 2+ test files
- Keep in test file IF tightly coupled to specific tests

### Real BMAD File Examples

From this project's docs/:

**docs/prd.md frontmatter:**
```yaml
---
stepsCompleted: [1, 2, 3, 4, 7, 8, 9, 10, 11]
inputDocuments: []
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 0
workflowType: 'prd'
lastStep: 11
project_name: 'bmad-assist'
user_name: 'Pawel'
date: '2025-12-08'
---
```

**docs/architecture.md frontmatter:**
```yaml
---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - docs/prd.md
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2025-12-08'
project_name: 'bmad-assist'
user_name: 'Pawel'
date: '2025-12-08'
---
```

Use these real examples in tests to ensure compatibility with actual BMAD files.

---

## Technical Requirements

### Dependencies

**Already in pyproject.toml:**
- `python-frontmatter` - markdown frontmatter parsing
- `pyyaml` - YAML parsing (used by python-frontmatter)

### File Encoding

- **Default encoding:** UTF-8 (python-frontmatter default)
- **Non-UTF-8 files:** Will raise ParserError with encoding context
- **No explicit encoding parameter:** Keep interface simple; BMAD files are always UTF-8

### File Structure After Implementation

```
src/bmad_assist/
├── bmad/
│   ├── __init__.py        # Export BmadDocument, parse_bmad_file
│   └── parser.py          # BmadDocument dataclass, parse_bmad_file function
├── core/
│   ├── exceptions.py      # Add ParserError
│   └── ...
└── ...

tests/
├── bmad/
│   ├── __init__.py
│   ├── conftest.py        # Sample BMAD file fixtures
│   └── test_parser.py     # AC1-AC7 tests
└── ...
```

### Type Hints Required

```python
from typing import Any
from pathlib import Path

def parse_bmad_file(path: str | Path) -> BmadDocument:
    ...
```

### Validation Commands

```bash
# Run all bmad tests
pytest tests/bmad/ -v

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
| 65b617d | docs(story-1.8): translate story file to English | Story files in English |
| 024c0ef | feat(tests): complete Story 1.8 test suite refactoring | Test structure patterns |
| ca502d8 | docs(story-1.8): complete Multi-LLM validation synthesis | Multi-LLM review workflow |
| 6e38af6 | docs(retro): complete Epic 1 retrospective | Retrospective format |
| 254907e | chore(prompts): simplify action_required sections | Power-prompts patterns |

### Established Patterns from Epic 1

**Commit Message Format:**
- `feat(module): description` for new features
- `fix(module): description` for bug fixes
- `docs(story-X.Y): description` for documentation
- `chore(scope): description` for maintenance

**Test Patterns:**
- Tests in `tests/{module}/` mirroring `src/bmad_assist/{module}/`
- conftest.py with shared fixtures
- Parametrized tests for multiple scenarios
- Coverage >= 95% required

**Code Patterns:**
- Type hints on all functions
- Google-style docstrings
- Custom exceptions inherit from BmadAssistError
- Module exports via `__all__` in `__init__.py`

---

## Architecture Compliance

### Stack Requirements
- **Language:** Python 3.11+
- **Dependencies:** python-frontmatter, pyyaml (both already in pyproject.toml)

### Structure Requirements
- **Location:** `src/bmad_assist/bmad/parser.py`
- **Tests:** `tests/bmad/test_parser.py`
- **Exception:** `core/exceptions.py` → ParserError

### Pattern Requirements
- BaseProvider ABC (not applicable to this story)
- Config singleton (not applicable to this story)
- Atomic writes (not applicable to this story)
- Custom exceptions: ParserError inherits from BmadAssistError

### Testing Requirements
- pytest for testing framework
- pytest-cov for coverage (>= 95%)
- mypy for type checking
- ruff for linting

---

## Testing Requirements

### Unit Tests

**Test Classes:**
- `TestParseValidFrontmatter` - AC1, AC5, AC6
- `TestParseNoFrontmatter` - AC2
- `TestParseMalformedFrontmatter` - AC3
- `TestParseMissingFile` - AC4
- `TestBmadDocumentDataclass` - AC7
- `TestContentWithDelimiters` - AC8

### Edge Cases to Cover

1. **Frontmatter variations:**
   - Valid YAML with various types (strings, ints, lists, dicts, booleans)
   - Empty frontmatter (`---\n---`)
   - No frontmatter at all
   - Frontmatter with Unicode characters
   - Frontmatter with dates (YAML date parsing)

2. **Content variations:**
   - Empty content (only frontmatter)
   - Large content (multi-page document)
   - Content with `---` in code blocks (AC8 - should not confuse parser)
   - Content with `---` horizontal rules (AC8 - should preserve in content)
   - YAML code blocks with frontmatter-like syntax

3. **Error scenarios:**
   - Malformed YAML (unclosed brackets, invalid syntax)
   - File not found
   - File with binary content (should fail gracefully)
   - File with invalid encoding

### Mocking Strategy

- Use `tmp_path` fixture for creating test files (no mocking needed)
- Real file I/O for integration-like tests
- `python-frontmatter` library not mocked (testing integration)

---

## Verification Checklist

- [ ] `src/bmad_assist/bmad/__init__.py` exports BmadDocument, parse_bmad_file
- [ ] `src/bmad_assist/bmad/parser.py` contains BmadDocument dataclass and parse_bmad_file function
- [ ] `src/bmad_assist/core/exceptions.py` contains ParserError
- [ ] `tests/bmad/test_parser.py` covers all 8 acceptance criteria (AC1-AC8)
- [ ] `pytest tests/bmad/` - all tests pass
- [ ] `pytest tests/bmad/ --cov=src/bmad_assist/bmad` - coverage >= 95%
- [ ] `mypy src/bmad_assist/bmad/` - no type errors
- [ ] `ruff check src/bmad_assist/bmad/` - no linting errors
- [ ] Real BMAD files from docs/ parse correctly
- [ ] Files with `---` in content (code blocks, horizontal rules) parse correctly

---

## References

- [Source: docs/architecture.md#Project-Structure] - Module organization
- [Source: docs/architecture.md#Implementation-Patterns] - Naming conventions, error handling
- [Source: docs/epics.md#Story-2.1] - Original story requirements
- [Source: docs/prd.md#FR26] - System can parse BMAD files without using LLM
- [Source: docs/prd.md#NFR6] - System must parse BMAD files in markdown and YAML formats
- [Source: Story 1.8] - Test structure patterns, fixture extraction rules

---

## Dev Agent Record

### Context Reference
- Story ID: 2.1
- Story Key: 2-1-markdown-frontmatter-parser
- Epic: 2 - BMAD File Integration
- Previous Story: 1.8 (done) - Test Suite Refactoring

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

No debug issues encountered. Implementation followed the recommended approach using `python-frontmatter` library.

### Completion Notes List

- Used `python-frontmatter` library as recommended in Dev Notes - handles all frontmatter edge cases robustly
- Added `ParserError` to `core/exceptions.py` inheriting from `BmadAssistError`
- Created `BmadDocument` dataclass with `frontmatter`, `content`, and `path` fields
- Implemented `parse_bmad_file` function with proper error handling:
  - `FileNotFoundError` propagates naturally (no wrapping)
  - All other exceptions wrapped in `ParserError` with file path context
- Added `type: ignore[import-untyped]` comment for `python-frontmatter` import since library lacks type stubs
- Comprehensive test suite: 46 tests covering all 8 acceptance criteria
- Real BMAD files from `docs/` parse correctly (verified prd.md and architecture.md)
- Test coverage: 100% on bmad module

### File List

**New files:**
- `src/bmad_assist/bmad/__init__.py` - Module exports (BmadDocument, parse_bmad_file)
- `src/bmad_assist/bmad/parser.py` - BmadDocument dataclass and parse_bmad_file function
- `tests/bmad/__init__.py` - Test module marker
- `tests/bmad/conftest.py` - Test fixtures for sample BMAD files
- `tests/bmad/test_parser.py` - 46 tests covering AC1-AC8

**Modified files:**
- `src/bmad_assist/core/exceptions.py` - Added ParserError class
- `docs/sprint-artifacts/sprint-status.yaml` - Status updated to in-progress → review
- `docs/sprint-artifacts/2-1-markdown-frontmatter-parser.md` - This file

### Change Log

- 2025-12-10: Implemented Story 2.1 - Markdown Frontmatter Parser (all tasks complete, 100% coverage)
