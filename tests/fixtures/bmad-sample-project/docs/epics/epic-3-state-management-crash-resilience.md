# Epic 3: State Management & Crash Resilience

**Goal:** System maintains persistent state, survives crashes, and can resume work from last checkpoint - enabling fire-and-forget operation.

**FRs:** FR4, FR5, FR31, FR32, FR33, FR34
**NFRs:** NFR1, NFR2

## Story 3.1: State Data Model

**As a** developer,
**I want** a well-defined state data model,
**So that** all loop progress is tracked consistently.

**Acceptance Criteria:**

**Given** State dataclass exists in `core/state.py`
**When** state is instantiated
**Then** it contains: current_epic, current_story, current_phase, completed_stories, timestamps
**And** all fields have type hints
**And** default factory creates valid initial state

**FRs:** FR4, FR34
**Estimate:** 2 SP

---

## Story 3.2: Atomic State Persistence

**As a** developer,
**I want** state writes to be atomic,
**So that** crashes never leave corrupted state files.

**Acceptance Criteria:**

**Given** state needs to be saved
**When** `save_state(state)` is called
**Then** state is written to temporary file first
**And** `os.rename()` atomically replaces the target file
**And** partial writes are impossible

**Given** crash occurs during write
**When** system restarts
**Then** previous valid state is intact
**And** no `.tmp` files are left behind (cleanup on start)

**FRs:** FR31, FR33, NFR2
**Estimate:** 2 SP

---

## Story 3.3: State Restoration on Restart

**As a** developer,
**I want** to restore state from persisted file on restart,
**So that** interrupted work can resume seamlessly.

**Acceptance Criteria:**

**Given** state file exists at configured path
**When** `load_state()` is called
**Then** state is deserialized from YAML
**And** StateError is raised if file is corrupted
**And** state object is validated against schema

**Given** no state file exists
**When** `load_state()` is called
**Then** fresh initial state is returned
**And** info log indicates fresh start

**FRs:** FR32, NFR1
**Estimate:** 2 SP

---

## Story 3.4: Loop Position Tracking

**As a** developer,
**I want** to track current position in the development loop,
**So that** the system knows exactly where to resume.

**Acceptance Criteria:**

**Given** system is in phase "code-review" of story 2.3
**When** state is saved
**Then** current_epic=2, current_story=3, current_phase="code-review"
**And** timestamp of last update is recorded

**Given** story 2.3 is completed
**When** `advance_state()` is called
**Then** story 2.3 is added to completed_stories
**And** current_story advances to 2.4 (or next epic)

**FRs:** FR4, FR34
**Estimate:** 2 SP

---

## Story 3.5: Resume Interrupted Loop

**As a** developer,
**I want** to resume interrupted loop from last saved state,
**So that** crashes don't lose progress.

**Acceptance Criteria:**

**Given** crash occurred during "develop" phase of story 3.1
**When** system restarts and loads state
**Then** loop resumes from "develop" phase of story 3.1
**And** log indicates resumption point
**And** no duplicate work is performed

**Given** state indicates "validate-create-story" phase
**When** loop resumes
**Then** validation phase is re-executed (idempotent)
**And** previous partial outputs are cleaned up

**FRs:** FR5, NFR1
**Estimate:** 3 SP

---

## Story 3.6: State Location Configuration

**As a** developer,
**I want** configurable state file location,
**So that** state can be project-local or global.

**Acceptance Criteria:**

**Given** config specifies `state_path: ./bmad-state.yaml`
**When** state is saved/loaded
**Then** project-local path is used

**Given** config specifies `state_path: ~/.bmad-assist/state.yaml`
**When** state is saved/loaded
**Then** global path is used

**Given** no state_path in config
**When** state is saved/loaded
**Then** default `~/.bmad-assist/state.yaml` is used

**FRs:** FR31
**Estimate:** 1 SP

---

**Epic 3 Total:** 6 stories, 12 SP

---
