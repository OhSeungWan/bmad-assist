# Epic 4: CLI Provider Integration

**Goal:** System can invoke external LLM CLI tools (Claude Code, Codex, Gemini CLI), capture outputs, and handle errors - the foundation for all LLM operations.

**FRs:** FR6, FR7, FR8, FR9, FR10
**NFRs:** NFR3, NFR5, NFR7

## Story 4.1: BaseProvider Abstract Class

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

## Story 4.2: Claude Code Provider

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

## Story 4.3: Provider Timeout Handling

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

## Story 4.4: Exit Code Detection

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

## Story 4.5: Stdout/Stderr Capture

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

## Story 4.6: Provider Configuration Loading

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

## Story 4.7: Codex Provider

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

## Story 4.8: Gemini CLI Provider

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

## Story 4.9: Provider Registry

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
