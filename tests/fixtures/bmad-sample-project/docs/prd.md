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

# Product Requirements Document - bmad-assist

**Author:** Pawel
**Date:** 2025-12-08

## Executive Summary

**bmad-assist** is an interactive CLI tool for Linux (WSL2) that automates the BMAD methodology development loop by orchestrating LLM vendor CLI tools (Claude Code, Codex, Gemini CLI).

The tool executes the main project loop: create story → validate story (multi-LLM) → synthesis and fixes → develop story → code review (multi-LLM) → synthesis and fixes → retrospective, repeating the cycle for subsequent stories within an epic and subsequent epics in the project.

The key feature is the Master/Multi architecture where only the main LLM (Master) has permission to modify files and the git repository, while additional LLMs (Multi) serve solely for validation and report generation. The tool collects output from Multi LLMs and saves reports with metadata (date, time, model).

The system operates in fire-and-forget mode with intelligent anomaly detection - a dedicated fast model analyzes outputs and decides whether to hand control to the user in unusual situations. It's a learning mechanism, initially without predefined anomaly examples.

**Power-prompts** constitute a system of personalized enhancements for BMAD workflow invocations. Prompt sets are selected based on the project's tech stack specifics (e.g., React frontend, Python backend) and appended to standard invocations. They contain dynamic variables (`{{sprint_artifacts}}`, `{{epic_num}}`, `{{story_num}}`, `{{model}}`, `{{timestamp}}`) and contextual quality standards tailored to the technical domain.

### What Makes This Special

**Intelligent automation with fallback (40%)** - a system that "knows when it doesn't know". Fire-and-forget without losing control when an LLM returns an unexpected result. The Guardian analyzes outputs and hands control to the user only when necessary.

**Multi-LLM validation with synthesis (25%)** - different models catch different problems. Master LLM collects reports from multiple validators, performs synthesis, and introduces fixes. A more complete picture than a single model.

**Dedicated BMAD assistant (25%)** - not a generic AI tool, but deep integration with the methodology. Understands the context of epics, stories, workflows. Parses BMAD files without using LLM, detects state discrepancies.

**Contextual power-prompts** - enhancement sets matched to the project's tech stack. Dynamic variables, aggressive quality standards, full context of previous reviews. Transform standard workflows into precise, domain-specific instructions.

**Progress visualization (10%)** - HTML dashboard with epics/stories table updated at each development stage.

## Project Classification

**Technical Type:** cli_tool
**Domain:** general (with ML/AI orchestration elements)
**Complexity:** medium
**Project Context:** Greenfield - new project
**Distribution:** Private tool, no plan for public release until maturity is achieved

CLI tool for orchestrating development processes with a plugin architecture for LLM providers. Requires a solid BMAD file parser, state tracking mechanism, power-prompt system with templates per tech stack, and integration with multiple external CLIs.

## Success Criteria

### User Success

**Breakthrough moment:** First successful fire-and-forget - launching the loop, returning to ready results without intervention.

**"Aha!" moment:** System detects an anomaly on its own and makes the correct decision about what to do with it - without involving the user. This is not just fallback, this is autonomous intelligence.

**Outcome:** Time saved - elimination of manual coordination between CLI tools and BMAD workflows.

### Business Success

**1 week:** Stable main loop with full support for all 3 CLIs (Claude Code, Codex, Gemini CLI).

**1 month:** 85% of anomalies resolved autonomously without user intervention.

**3 months:** Flexibility - goals may change with AI development.

### Technical Success

**BMAD Parser:** 100% reliability in parsing BMAD files without using LLM.

**Extensibility:** Adding a new CLI provider through a configuration file, not code changes.

**Performance:** No time requirements - loop execution time depends on external variables (models, story complexity).

### Measurable Outcomes

1. **Number of manual interventions** - main metric, goal: minimization
2. **No returns to planning phase** - code quality sufficient to not rewrite PRD/architecture
3. **% of autonomously resolved anomalies** - goal: 85% after 1 month

## Product Scope

### MVP - Minimum Viable Product (1 week)

**Main loop:**
- create story → validate story (multi-LLM) → synthesis → develop story → code review (multi-LLM) → synthesis → retrospective
- Repeating for subsequent stories in epic and subsequent epics

**CLI Providers:**
- Claude Code
- Codex
- Gemini CLI
- Plugin architecture (configuration, not code)

**Master/Multi Architecture:**
- Master LLM: full permissions (files, git)
- Multi LLM: output only → report with metadata (date, time, model)

**Anomaly Guardian:**
- Fast/cheap model analyzing outputs
- Fallback to user when problems detected
- Anomaly examples database (initially empty, learning through practice)

**State Tracking:**
- Own state file (separate from BMAD)
- BMAD file parser without LLM
- Discrepancy detection and correction

**Power-prompts:**
- 2 sets (e.g., React frontend, Python backend) - sufficient to develop interchangeability
- Dynamic variables: `{{sprint_artifacts}}`, `{{epic_num}}`, `{{story_num}}`, `{{model}}`, `{{timestamp}}`

**Visualization:**
- HTML dashboard with epics/stories table
- Update at each stage

### Growth Features (Post-MVP, 1 month)

- Autonomous anomaly resolution (goal: 85%)
- Expansion of anomaly examples database
- Additional power-prompt sets per tech stack
- Improved multi-LLM report synthesis

### Vision (Future, 3+ months)

- Adaptation to AI development - goals may change
- Potentially new CLI providers as they appear on the market
- Evolution of Anomaly Guardian toward full autonomy

## User Journeys

### Journey 1: Pawel - Fire-and-Forget Daily Workflow

Pawel is a developer who has just completed comprehensive BMAD documentation for a new project - PRD, architecture, epics, and stories are ready. Instead of manually coordinating between Claude Code, Codex, and Gemini CLI, he launches bmad-assist with the project configuration and goes to sleep.

bmad-assist works 24/7. Overnight it executes the main loop: creates a story, validates through multi-LLM, Master LLM performs synthesis and introduces fixes, then development and code review with the same multi-LLM → synthesis → fixes mechanics. After each stage, it updates the HTML dashboard.

In the morning, Pawel checks the dashboard over coffee. He sees metrics: 4 stories implemented overnight, 47 new unit tests, test coverage increased to 78%, top 10 files with the most lines (potential refactoring targets), zero anomalies. He smiles because he just saved a whole day of manual coordination.

In the evening after work, he checks again - another 3 stories done, epic 2 completed, system automatically started retrospective and moved to epic 3. Dashboard shows trend: average 5-6 stories/day. Pawel takes care of other things - paid work, projects, life - while bmad-assist does the job.

**Journey Requirements:**
- HTML dashboard with metrics (stories/day, tests, coverage, top files, anomalies)
- Main loop running autonomously 24/7
- Automatic transitions between stories and epics
- State persistence between sessions

### Journey 2: Pawel - Anomaly Detection and Resolution

It's Wednesday morning, Pawel checks the dashboard and sees a yellow flag: "Anomaly detected at 3:47 AM - code review epic 3, story 2". At the same time, he has a Telegram notification (or email) on his phone sent overnight.

He opens the anomaly details in the dashboard. The Anomaly Guardian (fast, cheap LLM) detected unusual output from Codex during code review - the model started generating code in a language not present in the project and got stuck in a loop of explanations. The Guardian stopped the loop and saved: full output from Codex, timestamp, context (epic/story/phase), and reason for the stop decision.

Pawel writes a prompt in response: "Ignore output from Codex for this code review, use only reports from Claude Code and Gemini CLI for synthesis. Continue main loop." His response is saved along with metadata - this will be training data for the Guardian.

The system resumes the loop. Pawel returns to his activities.

**One month later:** The Guardian encountered a similar anomaly (model generates code in wrong language). This time instead of stopping the loop, it sends a notification: "Detected anomaly type 'wrong-language-output' from Codex. Based on previous decisions: ignored output, continuing with remaining reports. Reason: 3/3 similar cases resolved this way."

Pawel receives the notification, nods approvingly, and doesn't need to do anything. The system has learned.

**Journey Requirements:**
- Email/Telegram notifications for anomalies
- Anomaly persistence: LLM output + user response + metadata
- Interface for writing prompts in response to anomalies
- Guardian evolution: fallback → suggestions → autonomy with notifications
- Dashboard showing anomaly history and decisions made

### Journey Requirements Summary

**Dashboard & Metrics:**
- Stories implemented / day
- Number of unit tests
- Test coverage percentage
- Top 10 files with most lines (refactoring targets)
- Anomaly list with history

**Notifications:**
- Email (SMTP auth)
- Telegram (API to be investigated)
- Notifications about anomalies and autonomous decisions

**Anomaly Persistence:**
- LLM output that triggered the anomaly
- User response (prompt)
- Metadata (timestamp, epic, story, phase, model, anomaly type)
- Format: files vs database - to be determined

**Guardian Evolution:**
1. Phase 1: Stop + fallback to user
2. Phase 2: Suggest solutions, user chooses
3. Phase 3: Autonomous decisions + notifications

## CLI Tool Specific Requirements

### Project-Type Overview

bmad-assist is a fire-and-forget CLI tool for advanced users. It doesn't require an interactive UI - configuration is done through a YAML file or a one-time questionnaire that generates the config.

### Command Structure

**Basic invocation:**
```bash
bmad-assist run --project ./my-project --config ./bmad-assist.yaml
```

**Missing configuration file:**
- CLI questionnaire generating `bmad-assist.yaml`
- Questions about: BMAD project, CLI providers, Master LLM, power-prompts, notifications

**Not planned:**
- Interactive selection menu
- Shell completion (bash/zsh)
- Multiple subcommands - single `run` command

### Configuration Schema

**Format:** YAML

**Hierarchy:** Global + Project
- Global config: `~/.bmad-assist/config.yaml`
- Project config: `./bmad-assist.yaml` (overrides global)

**Global config contains:**
- CLI providers (Claude Code, Codex, Gemini CLI) - paths, parameters
- Power-prompts - sets per tech stack
- Anomaly Guardian settings
- Notifications (SMTP, Telegram)
- Prometheus pushgateway URL

**Project config contains:**
- Paths to BMAD documentation (PRD, architecture, epics)
- CLI provider selection for this project
- Power-prompt set selection
- Project-specific overrides

### Output Formats

**Reports:**
- Code review: `.md` in `{{sprint_artifacts}}/code-reviews/code-review-{{epic_num}}-{{story_num}}-{{model}}-{{timestamp}}.md`
- Story validation: `.md` in `{{sprint_artifacts}}/story-validations/story-validation-{{epic_num}}-{{story_num}}-{{model}}-{{timestamp}}.md`
- Anomalies: `.md` with full context + metadata

**Dashboard:**
- Static HTML updated after each stage

**Metrics:**
- Prometheus pushgateway
- Docker container in tool scope (not external infrastructure)
- Metrics: stories/day, tests, coverage, anomalies, execution time

### Scripting Support

**Fire-and-forget design:**
- Launch and forget
- Exit codes for cron/systemd integration
- Stdout/stderr for basic monitoring
- Pushgateway for metrics

**Not planned:**
- Piping output to other tools
- Machine-readable JSON output (except Prometheus metrics)
- Scripting multiple instances in parallel

### Implementation Considerations

**CLI Technology:** To be determined in architecture phase (Python Click/Typer, Node Commander, Go Cobra, Rust Clap)

**Docker integration:**
- Prometheus + Pushgateway as docker-compose sidecar
- Optionally: entire bmad-assist as container

**State persistence:**
- Own state file (YAML/JSON) separate from BMAD
- BMAD file parser without LLM
- Atomic writes for crash resilience

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving MVP - solving the specific problem of manual LLM coordination in BMAD workflow.

**Resource Requirements:** Solo developer, 1 week

### MVP Feature Set (Phase 1 - 1 week)

**Core User Journey Supported:** Fire-and-forget daily workflow

**Must-Have Capabilities:**
- Main loop: create story → validate (multi-model) → develop → code review (multi-model) → retrospective
- Minimum 1 CLI provider with `--model` parameter support (different models = multi-LLM)
- Master/Multi architecture (Master modifies, Multi only reports)
- Anomaly Guardian with fallback to user
- 2 power-prompt sets (e.g., React frontend, Python backend)
- HTML dashboard with basic metrics
- BMAD file parser without LLM
- Own state file (YAML)
- Config: global + project (YAML)

**Explicitly Out of MVP:**
- Prometheus/Grafana (manually check dashboard)
- Email/Telegram notifications (manually check dashboard)
- Autonomous anomaly resolution (only fallback)
- More than 2 power-prompt sets

### Post-MVP Features (Phase 2 - 1 month)

**Growth Capabilities:**
- All 3 CLI providers (Claude Code, Codex, Gemini CLI)
- Prometheus pushgateway + docker container
- Email (SMTP) / Telegram notifications
- Guardian: solution suggestions (user chooses)
- Anomaly persistence with metadata (training data)
- Additional power-prompt sets
- 85% of anomalies resolved without user

### Vision Features (Phase 3 - 3+ months)

**Expansion Capabilities:**
- Guardian: full autonomy with "what and why" notifications
- New CLI providers (as they appear on the market)
- Adaptation to AI development
- Potentially: open source (MIT) if maturity is achieved

### Risk Mitigation Strategy

**Technical Risks:**
- *CLI providers may change API* → Plugin architecture, adapters per provider
- *BMAD parser may not cover edge cases* → Tests on real BMAD projects

**Market Risks:**
- *Not applicable* - private tool, no plan for public release

**Resource Risks:**
- *Less time than a week* → Priority: main loop + 1 CLI + fallback. Dashboard and power-prompts can be simplified.

## Functional Requirements

### Main Loop Orchestration

- FR1: System can execute the main development loop (create story → validate → develop → code review → retrospective)
- FR2: System can automatically transition between stories within an epic
- FR3: System can automatically transition between epics after retrospective
- FR4: System can track current position in the loop (epic number, story number, phase)
- FR5: System can resume interrupted loop from last saved state

### CLI Provider Integration

- FR6: System can invoke external CLI tools (Claude Code, Codex, Gemini CLI) with specified parameters
- FR7: System can pass `--model` parameter to CLI provider for model selection
- FR8: System can capture stdout/stderr from CLI invocations
- FR9: System can detect CLI invocation success/failure via exit codes
- FR10: System can add new CLI providers via configuration (plugin architecture)

### Multi-LLM Validation

- FR11: System can invoke multiple models (via `--model` parameter) for validation phases
- FR12: System can collect outputs from Multi LLM invocations without allowing file modifications
- FR13: System can save Multi LLM outputs as reports with metadata (timestamp, model, epic, story, phase)
- FR14: Master LLM can synthesize reports from multiple validation sources
- FR15: Master LLM can introduce changes to files and git repository

### Anomaly Detection (Guardian)

- FR16: Guardian can analyze LLM outputs for anomalies
- FR17: Guardian can pause main loop when anomaly is detected
- FR18: Guardian can save anomaly context (LLM output, epic, story, phase, timestamp)
- FR19: User can provide prompt response to resolve anomaly
- FR20: System can save user's anomaly resolution with metadata (for future training)
- FR21: System can resume main loop after anomaly resolution

### Power-Prompts

- FR22: System can load power-prompt sets from configuration
- FR23: System can select power-prompt set based on project tech stack
- FR24: System can inject dynamic variables into power-prompts (`{{epic_num}}`, `{{story_num}}`, `{{sprint_artifacts}}`, `{{model}}`, `{{timestamp}}`)
- FR25: System can append power-prompts to BMAD workflow invocations

### BMAD Integration

- FR26: System can parse BMAD files (PRD, architecture, epics, stories) without using LLM
- FR27: System can read current project state from BMAD files
- FR28: System can detect discrepancies between internal state and BMAD files
- FR29: System can correct state discrepancies (automatically or with user confirmation)
- FR30: System can extract story list and status from epic files

### State Management

- FR31: System can persist own state to YAML file (separate from BMAD)
- FR32: System can restore state from persisted file on restart
- FR33: System can perform atomic writes for crash resilience
- FR34: System can track completed stories, current epic, current phase

### Configuration

- FR35: System can load global configuration from `~/.bmad-assist/config.yaml`
- FR36: System can load project configuration from `./bmad-assist.yaml`
- FR37: Project config can override global config values
- FR38: System can generate config file via CLI questionnaire when config is missing

### Dashboard & Reporting

- FR39: System can generate HTML dashboard with current progress
- FR40: System can update dashboard after each phase completion
- FR41: Dashboard can display: stories completed per day, test count, coverage %, top 10 largest files
- FR42: Dashboard can display anomaly history with status
- FR43: System can generate code review reports in markdown format
- FR44: System can generate story validation reports in markdown format

## Non-Functional Requirements

### Reliability

- NFR1: System must survive unexpected shutdown (crash) and resume work from last saved state
- NFR2: State writes must be atomic (no partial writes)
- NFR3: System must properly handle CLI invocation timeouts
- NFR4: Guardian must detect and handle infinite loops in LLM output

### Integration

- NFR5: System must support CLI providers that return output via stdout/stderr
- NFR6: System must parse BMAD files in markdown and YAML formats
- NFR7: Architecture should minimize code changes when adding new CLI providers (adapter pattern), but changes are acceptable

### Security (Minimal)

- NFR8: Credentials (API keys, SMTP, Telegram) must be stored in a separate file with restricted permissions (chmod 600)
- NFR9: Credentials must not be logged or displayed in stdout
