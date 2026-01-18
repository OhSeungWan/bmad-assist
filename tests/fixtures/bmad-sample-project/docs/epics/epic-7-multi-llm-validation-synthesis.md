# Epic 7: Multi-LLM Validation & Synthesis

**Goal:** System invokes multiple LLMs for validation, collects reports, and Master LLM synthesizes findings - delivering comprehensive code quality assurance.

**FRs:** FR11, FR12, FR13, FR14, FR15

## Story 7.1: Parallel Multi-LLM Invocation

**As a** developer,
**I want** to invoke multiple LLMs in parallel for validation,
**So that** validation is faster than sequential execution.

**Acceptance Criteria:**

**Given** config specifies 3 Multi LLMs for validation
**When** validation phase executes
**Then** all 3 providers are invoked concurrently (asyncio or threading)
**And** system waits for all to complete (or timeout)
**And** partial results are collected if some fail

**Given** one Multi LLM times out
**When** others complete successfully
**Then** timeout is logged as warning
**And** available results are used for synthesis

**FRs:** FR11
**Estimate:** 3 SP

---

## Story 7.2: Multi-LLM Output Collection

**As a** developer,
**I want** to collect outputs from Multi LLMs without file modifications,
**So that** validation is read-only and safe.

**Acceptance Criteria:**

**Given** Multi LLM is invoked
**When** invocation completes
**Then** output is captured in memory
**And** no file system writes occur from Multi
**And** output is associated with provider/model metadata

**Given** Multi LLM attempts to modify files (detected in output)
**When** output is analyzed
**Then** warning is logged
**And** output is still collected (but flagged)

**FRs:** FR12
**Estimate:** 2 SP

---

## Story 7.3: Validation Report Generation

**As a** developer,
**I want** to save Multi LLM outputs as reports with metadata,
**So that** validation history is preserved.

**Acceptance Criteria:**

**Given** Multi LLM outputs are collected
**When** reports are generated
**Then** each output is saved to `{{sprint_artifacts}}/story-validations/story-validation-{{epic_num}}-{{story_num}}-{{model}}-{{timestamp}}.md`
**And** report includes: provider, model name, timestamp, epic, story, phase, full output

**Given** multiple validation reports exist
**When** reports are listed
**Then** they can be filtered by epic/story/model

**FRs:** FR13
**Estimate:** 2 SP

---

## Story 7.4: Master Synthesis Invocation

**As a** developer,
**I want** Master LLM to synthesize reports from validators,
**So that** a unified decision is made from multiple perspectives.

**Acceptance Criteria:**

**Given** 3 validation reports are collected
**When** synthesis phase executes
**Then** Master LLM receives all reports as context
**And** synthesis prompt asks for: summary, conflicts, recommended actions
**And** Master output is the authoritative result

**Given** validators disagree on an issue
**When** Master synthesizes
**Then** conflict is highlighted in synthesis
**And** Master makes final decision

**FRs:** FR14
**Estimate:** 3 SP

---

## Story 7.5: Master File Modification Permission

**As a** developer,
**I want** only Master LLM to have file modification permission,
**So that** Multi LLMs cannot accidentally change project files.

**Acceptance Criteria:**

**Given** Master LLM is invoked
**When** Master produces file changes
**Then** changes are applied to project
**And** git operations are allowed

**Given** provider is configured as Multi role
**When** invocation occurs
**Then** working directory is read-only (or sandbox)
**And** any write attempts are blocked/logged

**FRs:** FR15
**Estimate:** 2 SP

---

## Story 7.6: Synthesis Report Saving

**As a** developer,
**I want** synthesis results saved as reports,
**So that** synthesis history is preserved.

**Acceptance Criteria:**

**Given** Master code review synthesis completes
**When** report is generated
**Then** synthesis is saved to `{{sprint_artifacts}}/code-reviews/code-review-{{epic}}-{{story}}-master-{{timestamp}}.md`
**And** report includes: synthesis output

**Given** Master story validation synthesis completes
**When** report is generated
**Then** synthesis is saved to `{{sprint_artifacts}}/story-validations/story-validation-{{epic}}-{{story}}-master-{{timestamp}}.md`
**And** report includes: synthesis output

**FRs:** FR14
**Estimate:** 1 SP

---

**Epic 7 Total:** 6 stories, 13 SP

---
