# Epic 5: Power-Prompts Engine

**Goal:** System can load and inject context-aware prompts with dynamic variables, enhancing BMAD workflow invocations with project-specific quality standards.

**FRs:** FR22, FR23, FR24, FR25

## Story 5.1: Power-Prompt Data Model

**As a** developer,
**I want** a structured model for power-prompt sets,
**So that** prompts are organized and validated.

**Acceptance Criteria:**

**Given** PowerPromptSet model exists
**When** YAML prompt set is loaded
**Then** it contains: name, tech_stack, phases (dict of phase→prompt)
**And** each phase prompt is a string with optional Jinja2 variables
**And** validation ensures required phases exist

**FRs:** FR22
**Estimate:** 2 SP

---

## Story 5.2: Power-Prompt Set Loading

**As a** developer,
**I want** to load power-prompt sets from YAML files,
**So that** different tech stacks have customized prompts.

**Acceptance Criteria:**

**Given** `power-prompts/react-frontend.yaml` exists
**When** `load_prompt_set("react-frontend")` is called
**Then** YAML is parsed into PowerPromptSet model
**And** file not found raises ConfigError with clear message

**Given** multiple prompt sets exist
**When** sets are loaded
**Then** each set is available by name in memory

**FRs:** FR22
**Estimate:** 2 SP

---

## Story 5.3: Tech Stack Selection

**As a** developer,
**I want** to select power-prompt set based on project tech stack,
**So that** prompts match the project's technology.

**Acceptance Criteria:**

**Given** project config specifies `power_prompt_set: react-frontend`
**When** prompt engine initializes
**Then** react-frontend set is loaded and active

**Given** project config doesn't specify power_prompt_set
**When** prompt engine initializes
**Then** default set is used (or none if not configured)

**FRs:** FR23
**Estimate:** 1 SP

---

## Story 5.4: Dynamic Variable Injection

**As a** developer,
**I want** to inject dynamic variables into power-prompts,
**So that** prompts contain current context (epic, story, paths).

**Acceptance Criteria:**

**Given** prompt contains `{{epic_num}}`, `{{story_num}}`, `{{sprint_artifacts}}`, `{{model}}`, `{{timestamp}}`
**When** `render_prompt(phase, context)` is called
**Then** Jinja2 renders variables with actual values
**And** undefined variables raise clear error

**Given** context has epic_num=2, story_num=3
**When** prompt "Working on story {{epic_num}}.{{story_num}}" is rendered
**Then** output is "Working on story 2.3"

**FRs:** FR24
**Estimate:** 2 SP

---

## Story 5.5: BMAD Workflow Enhancement

**As a** developer,
**I want** to append power-prompts to BMAD workflow invocations,
**So that** LLM receives enhanced, context-aware instructions.

**Acceptance Criteria:**

**Given** phase is "code-review" and power-prompt set has code-review prompt
**When** `enhance_prompt(base_prompt, phase)` is called
**Then** power-prompt is appended to base prompt
**And** separator clearly distinguishes base from enhancement

**Given** phase has no power-prompt defined
**When** `enhance_prompt()` is called
**Then** base prompt is returned unchanged
**And** no error is raised

**FRs:** FR25
**Estimate:** 2 SP

---

## Story 5.6: Default Power-Prompt Sets

**As a** developer,
**I want** two default power-prompt sets (React frontend, Python backend),
**So that** MVP has working prompt enhancements.

**Acceptance Criteria:**

**Given** bmad-assist is installed
**When** power-prompts directory is checked
**Then** `react-frontend.yaml` and `python-backend.yaml` exist
**And** each contains prompts for: create-story, validate-story, dev-story, code-review
**And** prompts include quality standards specific to tech stack

**FRs:** FR22 (MVP requirement)
**Estimate:** 3 SP

---

**Epic 5 Total:** 6 stories, 12 SP

---
