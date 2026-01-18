# Epic 1: Project Foundation & CLI Infrastructure

**Goal:** Developer can install and run bmad-assist with basic CLI, configuration loads correctly, project structure is ready for development.

**FRs:** FR35, FR36, FR37, FR38
**NFRs:** NFR8, NFR9

## Story 1.1: Project Initialization with pyproject.toml

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

## Story 1.2: Pydantic Configuration Models

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

## Story 1.3: Global Configuration Loading

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

## Story 1.4: Project Configuration Override

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

## Story 1.5: Credentials Security with .env

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

## Story 1.6: Typer CLI Entry Point

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

## Story 1.7: Interactive Config Generation

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
