# Epic 8: Anomaly Guardian

**Goal:** System detects unusual LLM outputs, pauses when needed, allows user intervention, and saves resolutions for future learning - enabling intelligent fallback.

**FRs:** FR16, FR17, FR18, FR19, FR20, FR21
**NFRs:** NFR4

## Story 8.1: Guardian Detector Core

**As a** developer,
**I want** Guardian to analyze LLM outputs for anomalies,
**So that** unusual behavior is detected automatically.

**Acceptance Criteria:**

**Given** LLM output is received
**When** `analyze_output(output, context)` is called
**Then** Guardian (fast/cheap LLM) analyzes for anomalies
**And** analysis checks: infinite loops, wrong language, off-topic, errors
**And** result is: CONTINUE or ANOMALY with type and confidence

**Given** output contains repeated patterns (potential loop)
**When** Guardian analyzes
**Then** anomaly type "infinite-loop" is detected

**FRs:** FR16, NFR4
**Estimate:** 3 SP

---

## Story 8.2: Loop Pause on Anomaly

**As a** developer,
**I want** Guardian to pause main loop when anomaly is detected,
**So that** problematic situations don't propagate.

**Acceptance Criteria:**

**Given** Guardian returns ANOMALY
**When** phase execution receives result
**Then** main loop is paused immediately
**And** current state is saved
**And** anomaly handler is invoked

**Given** Guardian returns CONTINUE
**When** phase execution receives result
**Then** loop continues to next phase
**And** no interruption occurs

**FRs:** FR17
**Estimate:** 2 SP

---

## Story 8.3: Anomaly Context Persistence

**As a** developer,
**I want** Guardian to save anomaly context to markdown file,
**So that** all anomaly details are preserved for review.

**Acceptance Criteria:**

**Given** anomaly is detected
**When** context is saved
**Then** markdown file is created at `anomalies/{timestamp}-{epic}-{story}-{type}.md`
**And** file contains: full LLM output, provider, model, epic, story, phase, timestamp, anomaly type, Guardian reasoning

**Given** anomaly file is created
**When** file is opened
**Then** all context is human-readable
**And** LLM can use file as future context

**FRs:** FR18
**Estimate:** 2 SP

---

## Story 8.4: User Anomaly Response Interface

**As a** developer,
**I want** to provide prompt response to resolve anomaly,
**So that** I can guide the system past unusual situations.

**Acceptance Criteria:**

**Given** anomaly is detected and loop is paused
**When** user runs `bmad-assist resolve --anomaly {timestamp}`
**Then** anomaly details are displayed
**And** user can input resolution prompt
**And** resolution is passed to system

**Given** user provides resolution "ignore output, continue"
**When** resolution is processed
**Then** loop resumes from appropriate point
**And** resolution is logged

**FRs:** FR19
**Estimate:** 3 SP

---

## Story 8.5: Anomaly Resolution Metadata

**As a** developer,
**I want** to save user's anomaly resolution with metadata,
**So that** resolutions become training data for Guardian.

**Acceptance Criteria:**

**Given** user provides resolution
**When** resolution is saved
**Then** anomaly file is updated with: user response, resolution timestamp, outcome
**And** resolution is linked to original anomaly
**And** metadata enables future pattern matching

**Given** similar anomaly occurs later
**When** Guardian has access to past resolutions
**Then** past resolutions inform analysis (future learning)

**FRs:** FR20
**Estimate:** 2 SP

---

## Story 8.6: Loop Resume After Resolution

**As a** developer,
**I want** to resume main loop after anomaly resolution,
**So that** work continues without manual restart.

**Acceptance Criteria:**

**Given** anomaly is resolved
**When** `resume_loop()` is called
**Then** loop resumes from saved state
**And** resolution action is applied (skip output, retry, etc.)
**And** normal execution continues

**Given** resolution is "retry phase"
**When** loop resumes
**Then** current phase is re-executed
**And** new output is analyzed by Guardian

**FRs:** FR21
**Estimate:** 2 SP

---

## Story 8.7: Infinite Loop Detection

**As a** developer,
**I want** Guardian to detect and handle infinite loops in LLM output,
**So that** the system doesn't get stuck.

**Acceptance Criteria:**

**Given** LLM output contains >3 repetitions of same pattern
**When** Guardian analyzes
**Then** "infinite-loop" anomaly is detected
**And** loop is paused
**And** specific pattern is identified in anomaly report

**Given** LLM keeps producing similar outputs across invocations
**When** pattern is detected
**Then** "stuck-loop" anomaly is raised
**And** history of attempts is included

**FRs:** NFR4
**Estimate:** 2 SP

---

**Epic 8 Total:** 7 stories, 16 SP

---
