# Epic 2: BMAD File Integration

**Goal:** System can read and understand BMAD project files (PRD, architecture, epics, stories) without LLM, enabling accurate project state tracking.

**FRs:** FR26, FR27, FR28, FR29, FR30
**NFRs:** NFR6

## Story 2.1: Markdown Frontmatter Parser

**As a** developer,
**I want** to parse BMAD markdown files with YAML frontmatter,
**So that** I can extract metadata without using an LLM.

**Acceptance Criteria:**

**Given** a markdown file with YAML frontmatter exists
**When** `parse_bmad_file(path)` is called
**Then** frontmatter is parsed into a dictionary
**And** markdown content is available separately
**And** ParserError is raised for malformed frontmatter

**Given** a markdown file without frontmatter
**When** `parse_bmad_file(path)` is called
**Then** empty frontmatter dict is returned
**And** full content is available as markdown

**FRs:** FR26, NFR6
**Estimate:** 2 SP

---

## Story 2.2: Epic File Parser

**As a** developer,
**I want** to extract story list and status from epic files,
**So that** the system knows which stories exist and their completion state.

**Acceptance Criteria:**

**Given** an epic file with story sections (## Story X.Y)
**When** `parse_epic_file(path)` is called
**Then** list of stories is returned with: number, title, status
**And** status is inferred from frontmatter or content markers
**And** story dependencies are extracted if present

**Given** epic file with no stories
**When** `parse_epic_file(path)` is called
**Then** empty story list is returned

**FRs:** FR30
**Estimate:** 3 SP

---

## Story 2.3: Project State Reader

**As a** developer,
**I want** to read current project state from BMAD files,
**So that** the system understands project progress without manual input.

**Acceptance Criteria:**

**Given** BMAD project with multiple epic files
**When** `read_project_state(bmad_path)` is called
**Then** all epics are discovered and parsed
**And** current epic/story position is determined
**And** completed stories list is compiled
**And** result is returned as ProjectState dataclass

**FRs:** FR27
**Estimate:** 3 SP

---

## Story 2.4: State Discrepancy Detection

**As a** developer,
**I want** to detect discrepancies between internal state and BMAD files,
**So that** the system can identify and report inconsistencies.

**Acceptance Criteria:**

**Given** internal state shows story 2.3 as current
**And** BMAD files show story 2.3 as completed
**When** `detect_discrepancies()` is called
**Then** discrepancy is identified and returned
**And** discrepancy includes: type, expected, actual, file path

**Given** internal state matches BMAD files
**When** `detect_discrepancies()` is called
**Then** empty list is returned

**FRs:** FR28
**Estimate:** 2 SP

---

## Story 2.5: State Discrepancy Correction

**As a** developer,
**I want** to correct state discrepancies automatically or with confirmation,
**So that** BMAD files stay synchronized with the authoritative internal state.

**⚠️ CRITICAL:** Internal state is the source of truth. Corrections update BMAD files, NEVER internal state.

**Acceptance Criteria:**

**Given** discrepancy detected (BMAD behind internal - e.g., BMAD shows "in-progress", internal shows "done")
**When** `correct_discrepancy(auto=True)` is called
**Then** BMAD file is updated to match internal state
**And** correction is logged

**Given** discrepancy detected (BMAD ahead of internal - suspicious external edit)
**When** `correct_discrepancy(auto=False)` is called
**Then** user is prompted for confirmation
**And** BMAD file is reverted to match internal state (if confirmed)

**Given** callback returns invalid value or raises exception
**When** correction is attempted
**Then** ERROR result is returned with details

**Given** discrepancy already corrected
**When** `correct_discrepancy()` called again
**Then** NO_CHANGE_NEEDED result is returned (idempotent)

**FRs:** FR29
**Estimate:** 2 SP

---

**Epic 2 Total:** 5 stories, 12 SP

---
