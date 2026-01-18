### Ruthless Story Validation 1.4
Story reviewed: `docs/sprint-artifacts/1-4-project-configuration-override.md` (status: ready-for-dev, 3 SP).

### INVEST Violations
- (6) Independent: strongly coupled to Story 1.3/1.2 implementation (_load_yaml_file, load_global_config, ConfigError, singleton), so value is gated on prior stories being correct.
- (7) Testable: no explicit criteria for failure modes (invalid/oversized/permission-denied project config), making negative-path validation ambiguous and leaving gaps against the stated 95% coverage goal.

### Acceptance Criteria Issues
- Missing AC for malformed or oversized `bmad-assist.yaml` (project config); expected ConfigError path not specified, so behavior on YAML errors or >1MB files is undefined.
- ACs omit unreadable project config (permissions, directories) handling, risking silent fallback to global and hiding misconfiguration.
- No AC for type conflicts during deep merge (e.g., dict vs scalar/list mismatches), so outcome is undefined and can corrupt config.
- AC10 expects singleton updated but no rollback path if project load fails after global load, risking partial state in singleton.

### Hidden Risks & Dependencies
- Depends on existing `_load_yaml_file` semantics (size limit, UTF-8, empty-file handling); divergence for project config would break consistency and NFR reliability.
- Deep merge with list replacement can drop global `providers.multi` unintentionally if project file contains empty list or partial key; needs guardrails.
- Path resolution AC6 ignores `~` expansion or environment overrides, which may violate architecture path-handling patterns.
- Relies on previous story 1.3 code structure in `src/bmad_assist/core/config.py`; refactors there could break this story without safeguards.

### Estimation Reality-Check
3 SP seems low given new merge logic, dual-file loading paths, error handling parity with global config, and extensive tests (edge cases + 95% coverage). Closer to 4–5 SP.

### Technical Alignment
- Story aligns with architecture.md on config hierarchy (global + project) and Pydantic validation, but it omits explicit reuse of `_load_yaml_file`/ConfigError patterns for project config and lacks guidance on preserving frozen models/singleton reset on failure—risk of divergence from established config module patterns.

### Final Score (1-10)
6

### Verdict: MAJOR REWORK
