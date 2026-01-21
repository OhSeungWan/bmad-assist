# Changelog

All notable changes to bmad-assist are documented in this file.

## [0.4.3] - 2026-01-21

### Added
- CLI `--phase` flag to override starting phase in development loop

### Changed
- Sprint reconciler with forward-only protection and improved entry ordering
- Retrospective entries now tracked in sprint-status.yaml

## [0.4.2] - 2026-01-20

### Added
- Bundled workflow templates for standalone package distribution
- External docs support - planning artifacts can live outside project root
- Configurable loop phases via `loop:` key in bmad-assist.yaml

### Changed
- Paths singleton pattern for consistent path resolution
- Project knowledge path added to CompilerContext

### Fixed
- Patch/cache discovery in subprocess and experiment contexts
- Sprint-status sync before project completion
- ruamel.yaml now a required dependency

## [0.4.1] - 2026-01-15

### Changed
- Modularized CLI commands (patch, benchmark, sprint, experiment, qa)
- Modularized dashboard routes into package structure

### Fixed
- Test suite async isolation and E2E skip handling
- Story counting in sync and QA result parsing

## [0.4.0] - 2026-01-10

### Added
- Sprint-status auto-repair and reconciliation
- Human-readable notification formatting with story titles
- Descriptive prompt filenames (epic/story/phase identifiers)
- Auto-archive artifacts after code review synthesis

### Changed
- Unified phase naming convention across all components
- Report extraction with flexible fallbacks for Multi-LLM outputs

### Fixed
- Validator tools restricted to read-only operations
- Code review anonymization and report extraction

## [0.3.0] - 2025-12-28

### Added
- Workflow compiler with variable resolution and patch system
- Multi-LLM validation with output anonymization
- Benchmarking module for LLM performance metrics
- Code review orchestration with Multi-LLM synthesis
- Telegram and Discord notification providers
- Context menu system for story/phase actions

### Changed
- Provider pattern with BaseProvider ABC for CLI adapters
- Atomic state persistence with temp file + rename

## [0.1.1] - 2025-12-15

### Added
- Typer CLI with Pydantic configuration models
- BMAD file parsing (markdown frontmatter, epic files)
- YAML state persistence with atomic writes
- LLM providers: Claude, Codex, Gemini CLI
- Development loop with phase execution and transitions
- Multi-LLM parallel orchestration with Master synthesis

### Notes
- Initial release with core development loop functionality
