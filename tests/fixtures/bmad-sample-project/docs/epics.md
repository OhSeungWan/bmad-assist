---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - docs/prd.md
  - docs/architecture.md
project_name: 'bmad-assist'
user_name: 'Pawel'
date: '2025-12-08'
total_epics: 9
total_stories: 60
total_story_points: 132
fr_coverage: '44/44 (100%)'
nfr_coverage: '9/9 (100%)'
status: 'complete'
validated: true
---

# bmad-assist - Epic Breakdown

## Executive Summary

This document provides the complete epic and story breakdown for bmad-assist, decomposing 44 functional requirements and 9 non-functional requirements into 9 user-value-focused epics with implementation-ready stories.

**Total Epics:** 9
**Total FRs:** 44 (100% coverage)
**Total NFRs:** 9 (100% coverage)

## Requirements Inventory

### Functional Requirements

| ID | Requirement |
|----|-------------|
| FR1 | System can execute the main development loop (create story → validate → develop → code review → retrospective) |
| FR2 | System can automatically transition between stories within an epic |
| FR3 | System can automatically transition between epics after retrospective |
| FR4 | System can track current position in the loop (epic number, story number, phase) |
| FR5 | System can resume interrupted loop from last saved state |
| FR6 | System can invoke external CLI tools (Claude Code, Codex, Gemini CLI) with specified parameters |
| FR7 | System can pass `--model` parameter to CLI provider for model selection |
| FR8 | System can capture stdout/stderr from CLI invocations |
| FR9 | System can detect CLI invocation success/failure via exit codes |
| FR10 | System can add new CLI providers via configuration (plugin architecture) |
| FR11 | System can invoke multiple models (via `--model` parameter) for validation phases |
| FR12 | System can collect outputs from Multi LLM invocations without allowing file modifications |
| FR13 | System can save Multi LLM outputs as reports with metadata (timestamp, model, epic, story, phase) |
| FR14 | Master LLM can synthesize reports from multiple validation sources |
| FR15 | Master LLM can introduce changes to files and git repository |
| FR16 | Guardian can analyze LLM outputs for anomalies |
| FR17 | Guardian can pause main loop when anomaly is detected |
| FR18 | Guardian can save anomaly context (LLM output, epic, story, phase, timestamp) |
| FR19 | User can provide prompt response to resolve anomaly |
| FR20 | System can save user's anomaly resolution with metadata (for future training) |
| FR21 | System can resume main loop after anomaly resolution |
| FR22 | System can load power-prompt sets from configuration |
| FR23 | System can select power-prompt set based on project tech stack |
| FR24 | System can inject dynamic variables into power-prompts (`{{epic_num}}`, `{{story_num}}`, `{{sprint_artifacts}}`, `{{model}}`, `{{timestamp}}`) |
| FR25 | System can append power-prompts to BMAD workflow invocations |
| FR26 | System can parse BMAD files (PRD, architecture, epics, stories) without using LLM |
| FR27 | System can read current project state from BMAD files |
| FR28 | System can detect discrepancies between internal state and BMAD files |
| FR29 | System can correct state discrepancies (automatically or with user confirmation) |
| FR30 | System can extract story list and status from epic files |
| FR31 | System can persist own state to YAML file (separate from BMAD) |
| FR32 | System can restore state from persisted file on restart |
| FR33 | System can perform atomic writes for crash resilience |
| FR34 | System can track completed stories, current epic, current phase |
| FR35 | System can load global configuration from `~/.bmad-assist/config.yaml` |
| FR36 | System can load project configuration from `./bmad-assist.yaml` |
| FR37 | Project config can override global config values |
| FR38 | System can generate config file via CLI questionnaire when config is missing |
| FR39 | System can generate HTML dashboard with current progress |
| FR40 | System can update dashboard after each phase completion |
| FR41 | Dashboard can display: stories completed per day, test count, coverage %, top 10 largest files |
| FR42 | Dashboard can display anomaly history with status |
| FR43 | System can generate code review reports in markdown format |
| FR44 | System can generate story validation reports in markdown format |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR1 | System must survive unexpected shutdown (crash) and resume work from last saved state |
| NFR2 | State writes must be atomic (no partial writes) |
| NFR3 | System must properly handle CLI invocation timeouts |
| NFR4 | Guardian must detect and handle infinite loops in LLM output |
| NFR5 | System must support CLI providers that return output via stdout/stderr |
| NFR6 | System must parse BMAD files in markdown and YAML formats |
| NFR7 | Architecture should minimize code changes when adding new CLI providers (adapter pattern) |
| NFR8 | Credentials must be stored in a separate file with restricted permissions (chmod 600) |
| NFR9 | Credentials must not be logged or displayed in stdout |

### Additional Requirements from Architecture

- **No starter template** - custom src layout with pyproject.toml
- **Python 3.11+** with Typer CLI framework
- **Pydantic** for config validation
- **ABC pattern** for CLI providers (BaseProvider)
- **subprocess.run()** with timeout for CLI invocation
- **Atomic writes** via temp file + os.rename()
- **Rich logging** for CLI output
- **Jinja2** for power-prompts and dashboard templates
- **Provider configs** in `provider-configs/` directory with naming `{role}-{provider}-{model}.json`
- **Credentials** in `.env` file (chmod 600)

## FR Coverage Map

| FR Range | Epic | Domain |
|----------|------|--------|
| FR1-FR3 | Epic 6 | Main Loop Orchestration |
| FR4-FR5 | Epic 3 | State Tracking & Resume |
| FR6-FR10 | Epic 4 | CLI Provider Integration |
| FR11-FR15 | Epic 7 | Multi-LLM Validation |
| FR16-FR21 | Epic 8 | Anomaly Guardian |
| FR22-FR25 | Epic 5 | Power-Prompts |
| FR26-FR30 | Epic 2 | BMAD File Parsing |
| FR31-FR34 | Epic 3 | State Persistence |
| FR35-FR38 | Epic 1 | Configuration |
| FR39-FR44 | Epic 9 | Dashboard & Reporting |

## Epic List

### Epic 1: Project Foundation & CLI Infrastructure
Developer can install and run bmad-assist with basic CLI, configuration loads correctly, project structure is ready for development.
**FRs covered:** FR35, FR36, FR37, FR38
**NFRs addressed:** NFR8, NFR9

### Epic 2: BMAD File Integration
System can read and understand BMAD project files (PRD, architecture, epics, stories) without LLM, enabling accurate project state tracking.
**FRs covered:** FR26, FR27, FR28, FR29, FR30
**NFRs addressed:** NFR6

### Epic 3: State Management & Crash Resilience
System maintains persistent state, survives crashes, and can resume work from last checkpoint - enabling fire-and-forget operation.
**FRs covered:** FR4, FR5, FR31, FR32, FR33, FR34
**NFRs addressed:** NFR1, NFR2

### Epic 4: CLI Provider Integration
System can invoke external LLM CLI tools (Claude Code, Codex, Gemini CLI), capture outputs, and handle errors - the foundation for all LLM operations.
**FRs covered:** FR6, FR7, FR8, FR9, FR10
**NFRs addressed:** NFR3, NFR5, NFR7

### Epic 5: Power-Prompts Engine
System can load and inject context-aware prompts with dynamic variables, enhancing BMAD workflow invocations with project-specific quality standards.
**FRs covered:** FR22, FR23, FR24, FR25

### Epic 6: Main Loop Orchestration
System executes the complete development cycle (create story → validate → develop → code review → retrospective), automatically transitioning between stories and epics.
**FRs covered:** FR1, FR2, FR3

### Epic 7: Multi-LLM Validation & Synthesis
System invokes multiple LLMs for validation, collects reports, and Master LLM synthesizes findings - delivering comprehensive code quality assurance.
**FRs covered:** FR11, FR12, FR13, FR14, FR15

### Epic 8: Anomaly Guardian
System detects unusual LLM outputs, pauses when needed, allows user intervention, and saves resolutions for future learning - enabling intelligent fallback.
**FRs covered:** FR16, FR17, FR18, FR19, FR20, FR21
**NFRs addressed:** NFR4

### Epic 9: Dashboard & Reporting
Developer can view progress via HTML dashboard and access detailed reports - full visibility into the development process.
**FRs covered:** FR39, FR40, FR41, FR42, FR43, FR44

---

## Epic 1: Project Foundation & CLI Infrastructure

**Goal:** Developer can install and run bmad-assist with basic CLI, configuration loads correctly, project structure is ready for development.

**FRs:** FR35, FR36, FR37, FR38
**NFRs:** NFR8, NFR9

### Story 1.1: Project Initialization with pyproject.toml

**As a** developer,
**I want** to initialize the bmad-assist project with proper Python packaging,
**So that** I can install and develop the tool using standard Python tooling.

**Acceptance Criteria:**

**Given** an empty project directory
**When** pyproject.toml is created with project metadata
**Then** the project can be installed with `pip install -e .`
**And** the CLI entry point `bmad-assist` is available in PATH
**And** all dependencies (typer, pydantic, pyyaml, python-frontmatter, jinja2, rich) are specified
**And** src layout structure is created per architecture spec

**FRs:** Architecture setup
**Estimate:** 2 SP

---

### Story 1.2: Pydantic Configuration Models

**As a** developer,
**I want** type-safe configuration models with validation,
**So that** configuration errors are caught early with clear error messages.

**Acceptance Criteria:**

**Given** a Pydantic Config model exists in `core/config.py`
**When** invalid configuration values are provided
**Then** Pydantic raises ValidationError with descriptive message
**And** all config fields have type hints and default values where appropriate
**And** nested models exist for providers, power-prompts sections

**FRs:** FR35, FR36, FR37
**Estimate:** 3 SP

---

### Story 1.3: Global Configuration Loading

**As a** developer,
**I want** to load global configuration from `~/.bmad-assist/config.yaml`,
**So that** I have default settings that apply to all projects.

**Acceptance Criteria:**

**Given** a global config file exists at `~/.bmad-assist/config.yaml`
**When** `load_config()` is called
**Then** the file is parsed and validated against Pydantic models
**And** missing optional fields use default values
**And** ConfigError is raised if file is malformed

**Given** no global config file exists
**When** `load_config()` is called
**Then** default configuration is used

**FRs:** FR35
**Estimate:** 2 SP

---

### Story 1.4: Project Configuration Override

**As a** developer,
**I want** project-level config to override global settings,
**So that** each project can have custom CLI providers and power-prompts.

**Acceptance Criteria:**

**Given** global config exists with `timeout: 300`
**And** project config exists with `timeout: 600`
**When** configuration is loaded for the project
**Then** timeout value is 600 (project overrides global)
**And** non-overridden global values are preserved
**And** deep merge is performed for nested structures

**FRs:** FR36, FR37
**Estimate:** 3 SP

---

### Story 1.5: Credentials Security with .env

**As a** developer,
**I want** API credentials stored securely in .env file,
**So that** secrets are never exposed in config files or logs.

**Acceptance Criteria:**

**Given** `.env` file exists with API keys
**When** the application starts
**Then** environment variables are loaded
**And** credentials are never written to logs
**And** `.env.example` template is provided in repository

**Given** `.env` file has incorrect permissions (not 600)
**When** the application starts
**Then** warning is logged about insecure permissions

**FRs:** NFR8, NFR9
**Estimate:** 2 SP

---

### Story 1.6: Typer CLI Entry Point

**As a** developer,
**I want** a Typer CLI with `run` command,
**So that** I can execute bmad-assist from the command line.

**Acceptance Criteria:**

**Given** bmad-assist is installed
**When** user runs `bmad-assist run --project ./my-project`
**Then** CLI parses arguments and delegates to core/loop.py
**And** `--config` option allows specifying custom config path
**And** `--help` displays usage information
**And** Rich console is used for all output

**FRs:** FR38 (partial)
**Estimate:** 2 SP

---

### Story 1.7: Interactive Config Generation

**As a** developer,
**I want** CLI questionnaire to generate config when missing,
**So that** first-time setup is guided and user-friendly.

**Acceptance Criteria:**

**Given** no project config exists at `./bmad-assist.yaml`
**When** user runs `bmad-assist run --project ./my-project`
**Then** interactive questionnaire prompts for: BMAD paths, CLI provider, Master model, power-prompt set
**And** generated config is saved to `./bmad-assist.yaml`
**And** user can skip questionnaire with `--no-interactive` flag

**FRs:** FR38
**Estimate:** 3 SP

---

**Epic 1 Total:** 7 stories, 17 SP

---

## Epic 2: BMAD File Integration

**Goal:** System can read and understand BMAD project files (PRD, architecture, epics, stories) without LLM, enabling accurate project state tracking.

**FRs:** FR26, FR27, FR28, FR29, FR30
**NFRs:** NFR6

### Story 2.1: Markdown Frontmatter Parser

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

### Story 2.2: Epic File Parser

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

### Story 2.3: Project State Reader

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

### Story 2.4: State Discrepancy Detection

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

### Story 2.5: State Discrepancy Correction

**As a** developer,
**I want** to correct state discrepancies automatically or with confirmation,
**So that** the system maintains accurate state alignment.

**Acceptance Criteria:**

**Given** discrepancy detected (internal behind BMAD)
**When** `correct_discrepancy(auto=True)` is called
**Then** internal state is updated to match BMAD
**And** correction is logged

**Given** discrepancy detected (BMAD behind internal)
**When** `correct_discrepancy(auto=False)` is called
**Then** user is prompted for confirmation
**And** action taken based on user response

**FRs:** FR29
**Estimate:** 2 SP

---

**Epic 2 Total:** 5 stories, 12 SP

---

## Epic 3: State Management & Crash Resilience

**Goal:** System maintains persistent state, survives crashes, and can resume work from last checkpoint - enabling fire-and-forget operation.

**FRs:** FR4, FR5, FR31, FR32, FR33, FR34
**NFRs:** NFR1, NFR2

### Story 3.1: State Data Model

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

### Story 3.2: Atomic State Persistence

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

### Story 3.3: State Restoration on Restart

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

### Story 3.4: Loop Position Tracking

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

### Story 3.5: Resume Interrupted Loop

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

### Story 3.6: State Location Configuration

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

## Epic 4: CLI Provider Integration

**Goal:** System can invoke external LLM CLI tools (Claude Code, Codex, Gemini CLI), capture outputs, and handle errors - the foundation for all LLM operations.

**FRs:** FR6, FR7, FR8, FR9, FR10
**NFRs:** NFR3, NFR5, NFR7

### Story 4.1: BaseProvider Abstract Class

**As a** developer,
**I want** an abstract base class defining the provider interface,
**So that** all CLI providers follow a consistent contract.

**Acceptance Criteria:**

**Given** BaseProvider ABC exists in `providers/base.py`
**When** a new provider is created
**Then** it must implement: `invoke()`, `parse_output()`, `supports_model()`
**And** abstract methods have clear docstrings
**And** type hints are defined for all parameters and returns

**FRs:** FR6, NFR7
**Estimate:** 2 SP

---

### Story 4.2: Claude Code Provider

**As a** developer,
**I want** to invoke Claude Code CLI with specified parameters,
**So that** Claude can be used as Master or Multi LLM.

**Acceptance Criteria:**

**Given** ClaudeProvider extends BaseProvider
**When** `invoke(prompt, model="opus")` is called
**Then** `claude` CLI is executed with `--model opus` parameter
**And** `--print` flag is used for non-interactive mode
**And** settings file is passed via `--settings` if configured
**And** subprocess.run() is used with timeout

**Given** Claude CLI returns output
**When** `parse_output()` is called
**Then** relevant response is extracted from stdout
**And** metadata (model, timestamp) is attached

**FRs:** FR6, FR7, FR8
**Estimate:** 3 SP

---

### Story 4.3: Provider Timeout Handling

**As a** developer,
**I want** proper timeout handling for CLI invocations,
**So that** hung processes don't block the loop forever.

**Acceptance Criteria:**

**Given** provider is invoked with timeout=300
**When** CLI doesn't respond within 300 seconds
**Then** subprocess.TimeoutExpired is raised
**And** ProviderError wraps the timeout with context
**And** partial output (if any) is captured

**Given** timeout occurs
**When** error is handled
**Then** process is terminated (not left running)
**And** timeout event is logged with provider/model info

**FRs:** NFR3
**Estimate:** 2 SP

---

### Story 4.4: Exit Code Detection

**As a** developer,
**I want** to detect CLI invocation success/failure via exit codes,
**So that** errors are properly identified and handled.

**Acceptance Criteria:**

**Given** CLI returns exit code 0
**When** invocation completes
**Then** result is treated as success
**And** output is passed to parse_output()

**Given** CLI returns non-zero exit code
**When** invocation completes
**Then** ProviderError is raised
**And** stderr content is included in error message
**And** exit code is logged

**FRs:** FR9
**Estimate:** 2 SP

---

### Story 4.5: Stdout/Stderr Capture

**As a** developer,
**I want** to capture stdout and stderr from CLI invocations,
**So that** all output is available for processing.

**Acceptance Criteria:**

**Given** CLI produces stdout and stderr
**When** invocation completes
**Then** both streams are captured separately
**And** stdout contains main response
**And** stderr contains warnings/errors
**And** encoding is handled (UTF-8)

**Given** CLI produces large output
**When** output is captured
**Then** no truncation occurs
**And** memory is handled efficiently

**FRs:** FR8, NFR5
**Estimate:** 2 SP

---

### Story 4.6: Provider Configuration Loading

**As a** developer,
**I want** to load provider settings from config files,
**So that** each provider-model combo has custom settings.

**Acceptance Criteria:**

**Given** `provider-configs/master-claude-opus_4_5.json` exists
**When** ClaudeProvider is initialized for master role
**Then** settings file path is resolved from config
**And** settings are passed to CLI via `--settings` flag
**And** model set to `opus_4_5`

**Given** settings file doesn't exist
**When** provider is initialized
**Then** warning is logged
**And** provider runs with default settings

**FRs:** FR10 (partial)
**Estimate:** 2 SP

---

### Story 4.7: Codex Provider

**As a** developer,
**I want** to invoke Codex CLI with specified parameters,
**So that** Codex can be used as Multi LLM validator.

**Acceptance Criteria:**

**Given** CodexProvider extends BaseProvider
**When** `invoke(prompt, model)` is called
**Then** `codex` CLI is executed with appropriate flags
**And** model parameter is passed correctly
**And** non-interactive mode is used

**FRs:** FR6, FR7
**Estimate:** 2 SP

---

### Story 4.8: Gemini CLI Provider

**As a** developer,
**I want** to invoke Gemini CLI with specified parameters,
**So that** Gemini can be used as Multi LLM validator.

**Acceptance Criteria:**

**Given** GeminiProvider extends BaseProvider
**When** `invoke(prompt, model)` is called
**Then** `gemini` CLI is executed with appropriate flags
**And** model parameter is passed correctly
**And** non-interactive mode is used

**FRs:** FR6, FR7
**Estimate:** 2 SP

---

### Story 4.9: Provider Registry

**As a** developer,
**I want** a registry to look up providers by name,
**So that** configuration can specify providers as strings.

**Acceptance Criteria:**

**Given** config specifies `provider: claude`
**When** provider is resolved
**Then** ClaudeProvider instance is returned
**And** unknown provider name raises ConfigError

**Given** new provider class is added
**When** registered in `providers/__init__.py`
**Then** it's available via registry lookup

**FRs:** FR10, NFR7
**Estimate:** 1 SP

---

**Epic 4 Total:** 9 stories, 18 SP

---

## Epic 5: Power-Prompts Engine

**Goal:** System can load and inject context-aware prompts with dynamic variables, enhancing BMAD workflow invocations with project-specific quality standards.

**FRs:** FR22, FR23, FR24, FR25

### Story 5.1: Power-Prompt Data Model

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

### Story 5.2: Power-Prompt Set Loading

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

### Story 5.3: Tech Stack Selection

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

### Story 5.4: Dynamic Variable Injection

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

### Story 5.5: BMAD Workflow Enhancement

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

### Story 5.6: Default Power-Prompt Sets

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

## Epic 6: Main Loop Orchestration

**Goal:** System executes the complete development cycle (create story → validate → develop → code review → retrospective), automatically transitioning between stories and epics.

**FRs:** FR1, FR2, FR3

### Story 6.1: Phase Enum and Workflow Definition

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

### Story 6.2: Single Phase Execution

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

### Story 6.3: Story Completion and Transition

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

### Story 6.4: Epic Completion and Transition

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

### Story 6.5: Main Loop Runner

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

### Story 6.6: Loop Interruption Handling

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

## Epic 7: Multi-LLM Validation & Synthesis

**Goal:** System invokes multiple LLMs for validation, collects reports, and Master LLM synthesizes findings - delivering comprehensive code quality assurance.

**FRs:** FR11, FR12, FR13, FR14, FR15

### Story 7.1: Parallel Multi-LLM Invocation

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

### Story 7.2: Multi-LLM Output Collection

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

### Story 7.3: Validation Report Generation

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

### Story 7.4: Master Synthesis Invocation

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

### Story 7.5: Master File Modification Permission

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

### Story 7.6: Synthesis Report Saving

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

## Epic 8: Anomaly Guardian

**Goal:** System detects unusual LLM outputs, pauses when needed, allows user intervention, and saves resolutions for future learning - enabling intelligent fallback.

**FRs:** FR16, FR17, FR18, FR19, FR20, FR21
**NFRs:** NFR4

### Story 8.1: Guardian Detector Core

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

### Story 8.2: Loop Pause on Anomaly

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

### Story 8.3: Anomaly Context Persistence

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

### Story 8.4: User Anomaly Response Interface

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

### Story 8.5: Anomaly Resolution Metadata

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

### Story 8.6: Loop Resume After Resolution

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

### Story 8.7: Infinite Loop Detection

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

## Epic 9: Dashboard & Reporting

**Goal:** Developer can view progress via HTML dashboard and access detailed reports - full visibility into the development process.

**FRs:** FR39, FR40, FR41, FR42, FR43, FR44

### Story 9.1: Dashboard HTML Template

**As a** developer,
**I want** a Jinja2 HTML template for the dashboard,
**So that** dashboard generation is maintainable and customizable.

**Acceptance Criteria:**

**Given** `templates/dashboard.html` exists
**When** template is loaded
**Then** it contains Jinja2 variables for: progress, metrics, anomalies
**And** pure HTML/CSS (no JavaScript frameworks)
**And** responsive layout for desktop viewing

**FRs:** FR39
**Estimate:** 2 SP

---

### Story 9.2: Dashboard Data Model

**As a** developer,
**I want** a data model for dashboard content,
**So that** dashboard generation has structured input.

**Acceptance Criteria:**

**Given** DashboardData model exists
**When** model is populated
**Then** it contains: epics_progress, stories_completed_today, test_count, coverage_percent, top_files, anomaly_list
**And** all fields have type hints
**And** model can be serialized to dict for Jinja2

**FRs:** FR41, FR42
**Estimate:** 2 SP

---

### Story 9.3: Dashboard Generation

**As a** developer,
**I want** to generate HTML dashboard from current state,
**So that** progress is visible at any time.

**Acceptance Criteria:**

**Given** current state and metrics are available
**When** `generate_dashboard()` is called
**Then** Jinja2 template is rendered with data
**And** HTML is written to configured output path
**And** dashboard is self-contained (no external dependencies)

**Given** dashboard already exists
**When** new dashboard is generated
**Then** previous dashboard is overwritten atomically

**FRs:** FR39
**Estimate:** 2 SP

---

### Story 9.4: Phase Completion Dashboard Update

**As a** developer,
**I want** dashboard updated after each phase completion,
**So that** progress is always current.

**Acceptance Criteria:**

**Given** phase completes successfully
**When** state is saved
**Then** dashboard is regenerated automatically
**And** update is logged

**Given** phase fails or anomaly occurs
**When** state is saved
**Then** dashboard still updates with current status
**And** anomaly is visible in dashboard

**FRs:** FR40
**Estimate:** 1 SP

---

### Story 9.5: Progress Metrics Display

**As a** developer,
**I want** dashboard to display key progress metrics,
**So that** I can quickly assess project status.

**Acceptance Criteria:**

**Given** dashboard is generated
**When** dashboard is viewed
**Then** it displays: stories completed per day (chart/table), total test count, coverage percentage, top 10 largest files by lines
**And** metrics are clearly labeled
**And** visual hierarchy highlights important metrics

**FRs:** FR41
**Estimate:** 3 SP

---

### Story 9.6: Anomaly History Display

**As a** developer,
**I want** dashboard to display anomaly history with status,
**So that** I can track anomalies and their resolutions.

**Acceptance Criteria:**

**Given** anomalies have occurred
**When** dashboard is viewed
**Then** anomaly list shows: timestamp, type, epic/story, status (pending/resolved)
**And** resolved anomalies show resolution summary
**And** pending anomalies are highlighted

**Given** no anomalies have occurred
**When** dashboard is viewed
**Then** "No anomalies" message is displayed

**FRs:** FR42
**Estimate:** 2 SP

---

### Story 9.7: Code Review Report Generation

**As a** developer,
**I want** code review results saved as markdown reports,
**So that** review history is preserved and searchable.

**Acceptance Criteria:**

**Given** code review phase completes
**When** report is generated
**Then** markdown file is saved to `{{sprint_artifacts}}/code-reviews/code-review-{{epic}}-{{story}}-{{model}}-{{timestamp}}.md`
**And** report includes: reviewers (models), model output

**Given** multiple code reviews exist for same story
**When** reports are listed
**Then** each review is separate file with unique timestamp

**FRs:** FR43
**Estimate:** 2 SP

---

### Story 9.8: Story Validation Report Generation

**As a** developer,
**I want** story validation results saved as markdown reports,
**So that** validation history is preserved.

**Acceptance Criteria:**

**Given** story validation phase completes
**When** report is generated
**Then** markdown file is saved to `{{sprint_artifacts}}/story-validations/story-validation-{{epic}}-{{story}}-{{model}}-{{timestamp}}.md`
**And** report includes: validators (models), model output

**FRs:** FR44
**Estimate:** 2 SP

---

**Epic 9 Total:** 8 stories, 16 SP

---

## Summary

### Epic Summary

| Epic | Title | Stories | Story Points |
|------|-------|---------|--------------|
| 1 | Project Foundation & CLI Infrastructure | 7 | 17 |
| 2 | BMAD File Integration | 5 | 12 |
| 3 | State Management & Crash Resilience | 6 | 12 |
| 4 | CLI Provider Integration | 9 | 18 |
| 5 | Power-Prompts Engine | 6 | 12 |
| 6 | Main Loop Orchestration | 6 | 16 |
| 7 | Multi-LLM Validation & Synthesis | 6 | 13 |
| 8 | Anomaly Guardian | 7 | 16 |
| 9 | Dashboard & Reporting | 8 | 16 |
| **TOTAL** | | **60** | **132** |

### Requirements Coverage Matrix

| FR | Epic | Story | Description |
|----|------|-------|-------------|
| FR1 | 6 | 6.1, 6.2, 6.5 | Main development loop execution |
| FR2 | 6 | 6.3 | Story transitions within epic |
| FR3 | 6 | 6.4 | Epic transitions after retrospective |
| FR4 | 3 | 3.1, 3.4 | Loop position tracking |
| FR5 | 3 | 3.5 | Resume interrupted loop |
| FR6 | 4 | 4.1, 4.2, 4.7, 4.8 | CLI tool invocation |
| FR7 | 4 | 4.2, 4.7, 4.8 | Model parameter passing |
| FR8 | 4 | 4.2, 4.5 | Stdout/stderr capture |
| FR9 | 4 | 4.4 | Exit code detection |
| FR10 | 4 | 4.6, 4.9 | Provider plugin architecture |
| FR11 | 7 | 7.1 | Multiple model invocation |
| FR12 | 7 | 7.2 | Multi LLM output collection |
| FR13 | 7 | 7.3 | Reports with metadata |
| FR14 | 7 | 7.4, 7.6 | Master synthesis |
| FR15 | 7 | 7.5 | Master file modification |
| FR16 | 8 | 8.1 | Anomaly analysis |
| FR17 | 8 | 8.2 | Loop pause on anomaly |
| FR18 | 8 | 8.3 | Anomaly context persistence |
| FR19 | 8 | 8.4 | User anomaly response |
| FR20 | 8 | 8.5 | Resolution metadata |
| FR21 | 8 | 8.6 | Loop resume after resolution |
| FR22 | 5 | 5.1, 5.2, 5.6 | Power-prompt loading |
| FR23 | 5 | 5.3 | Tech stack selection |
| FR24 | 5 | 5.4 | Dynamic variable injection |
| FR25 | 5 | 5.5 | Workflow enhancement |
| FR26 | 2 | 2.1 | BMAD file parsing |
| FR27 | 2 | 2.3 | Project state reading |
| FR28 | 2 | 2.4 | Discrepancy detection |
| FR29 | 2 | 2.5 | Discrepancy correction |
| FR30 | 2 | 2.2 | Story extraction from epics |
| FR31 | 3 | 3.2, 3.6 | State persistence |
| FR32 | 3 | 3.3 | State restoration |
| FR33 | 3 | 3.2 | Atomic writes |
| FR34 | 3 | 3.1, 3.4 | Progress tracking |
| FR35 | 1 | 1.2, 1.3 | Global config loading |
| FR36 | 1 | 1.2, 1.4 | Project config loading |
| FR37 | 1 | 1.2, 1.4 | Config override |
| FR38 | 1 | 1.6, 1.7 | CLI & config generation |
| FR39 | 9 | 9.1, 9.3 | Dashboard generation |
| FR40 | 9 | 9.4 | Dashboard update per phase |
| FR41 | 9 | 9.2, 9.5 | Progress metrics display |
| FR42 | 9 | 9.2, 9.6 | Anomaly history display |
| FR43 | 9 | 9.7 | Code review reports |
| FR44 | 9 | 9.8 | Story validation reports |

### NFR Coverage Matrix

| NFR | Epic | Story | Description |
|-----|------|-------|-------------|
| NFR1 | 3 | 3.3, 3.5 | Crash recovery |
| NFR2 | 3 | 3.2 | Atomic writes |
| NFR3 | 4 | 4.3 | Timeout handling |
| NFR4 | 8 | 8.1, 8.7 | Infinite loop detection |
| NFR5 | 4 | 4.5 | Stdout/stderr support |
| NFR6 | 2 | 2.1 | Markdown/YAML parsing |
| NFR7 | 4 | 4.1, 4.9 | Adapter pattern |
| NFR8 | 1 | 1.5 | Credentials security |
| NFR9 | 1 | 1.5 | No credential logging |

---

**Coverage:** 44/44 FRs (100%) | 9/9 NFRs (100%)

**Document Status:** COMPLETE - Ready for sprint planning
