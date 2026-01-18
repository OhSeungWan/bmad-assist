# Epic 6: Main Loop Orchestration

**Goal:** System executes the complete development cycle (create story → validate → develop → code review → retrospective), automatically transitioning between stories and epics.

**FRs:** FR1, FR2, FR3

## Story 6.1: Phase Enum and Workflow Definition

**As a** developer,
**I want** a clear definition of workflow phases,
**So that** the loop execution is well-structured.

**Acceptance Criteria:**

**Given** Phase enum exists in `core/loop.py`
**When** workflow is defined
**Then** phases are: CREATE_STORY, VALIDATE_CREATE_STORY, VALIDATE_SYNTHESIS, DEV_STORY, CODE_REVIEW, CODE_REVIEW_SYNTHESIS, RETROSPECTIVE
**And** phase order is enforced
**And** each phase has associated handler function

**FRs:** FR1
**Estimate:** 2 SP

---

## Story 6.2: Single Phase Execution

**As a** developer,
**I want** to execute a single workflow phase,
**So that** phases can be tested and run independently.

**Acceptance Criteria:**

**Given** current state is phase=DEV_STORY, story=2.3
**When** `execute_phase(state)` is called
**Then** appropriate handler is invoked (dev_story_handler)
**And** Master provider is called with enhanced prompt
**And** Guardian analyzes output
**And** phase result (success/anomaly) is returned

**FRs:** FR1
**Estimate:** 3 SP

---

## Story 6.3: Story Completion and Transition

**As a** developer,
**I want** automatic transition between stories within an epic,
**So that** the loop continues without manual intervention.

**Acceptance Criteria:**

**Given** story 2.3 code review synthesis completes successfully
**When** loop advances
**Then** state updates to story 2.4, phase=CREATE_STORY
**And** state is persisted atomically
**And** dashboard is updated

**Given** story 2.4 is last story in epic 2
**When** story 2.4 completes
**Then** epic 2 is marked as complete
**And** epic retrospective phase is initiated

**FRs:** FR2
**Estimate:** 2 SP

---

## Story 6.4: Epic Completion and Transition

**As a** developer,
**I want** automatic transition between epics after epic retrospective,
**So that** the loop continues to the next epic.

**Acceptance Criteria:**

**Given** after epic retrospective completes 
**When** loop advances
**Then** state updates to epic 3, story 1, phase=CREATE_STORY
**And** log indicates epic transition
**And** dashboard shows epic 2 complete

**Given** last epic retrospective of last epic completes
**When** loop advances
**Then** loop terminates with success
**And** final dashboard is generated
**And** completion summary is logged

**FRs:** FR3
**Estimate:** 2 SP

---

## Story 6.5: Main Loop Runner

**As a** developer,
**I want** a main loop runner that orchestrates all phases,
**So that** the entire workflow runs autonomously.

**Acceptance Criteria:**

**Given** bmad-assist run is invoked
**When** `run_loop()` is called
**Then** state is loaded (or fresh start)
**And** phases execute in sequence
**And** state is saved after each phase
**And** loop continues until completion or anomaly

**Given** anomaly is detected
**When** Guardian pauses loop
**Then** loop halts at current phase
**And** state is saved
**And** anomaly handler is invoked

**FRs:** FR1, FR2, FR3
**Estimate:** 5 SP

---

## Story 6.6: Loop Interruption Handling

**As a** developer,
**I want** graceful handling of loop interruptions (SIGINT, SIGTERM),
**So that** state is saved before exit.

**Acceptance Criteria:**

**Given** loop is running
**When** SIGINT (Ctrl+C) is received
**Then** current phase completes (or is cancelled cleanly)
**And** state is saved
**And** exit with code 130 (SIGINT)

**Given** loop is in middle of provider invocation
**When** SIGTERM is received
**Then** provider subprocess is terminated
**And** state is saved at last completed phase
**And** exit cleanly

**FRs:** NFR1 (crash resilience)
**Estimate:** 2 SP

---

**Epic 6 Total:** 6 stories, 16 SP

---
