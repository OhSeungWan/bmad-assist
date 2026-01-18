# Requirements Inventory

## Functional Requirements

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

## Non-Functional Requirements

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

## Additional Requirements from Architecture

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
