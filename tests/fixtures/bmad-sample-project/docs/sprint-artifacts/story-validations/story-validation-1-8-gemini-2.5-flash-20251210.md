### Ruthless Story Validation 1.8

### INVEST Violations
- **Negotiable (Severity: 4):** AC5 is marked "opcjonalnie" (optional). Acceptance Criteria define the Definition of Done. They cannot be optional. This makes the scope ambiguous.
- **Independent (Severity: 2):** The story is tightly coupled to the exact current state of `test_config.py`. Any parallel development on config (e.g. bug fixes) will cause massive merge conflicts.

### Acceptance Criteria Issues
- **Ambiguous:** AC5 "Ocenić czy 871 linii wymaga rozbicia" (Assess if 871 lines need splitting) is subjective. A testable criterion would be "test_cli.py is < 500 lines" or "Structure remains unchanged".
- **Missing:** ACs do not include updating `docs/architecture.md`. The architecture document explicitly maps `tests/core/test_config.py`. Deleting this file without updating documentation breaks the "Single Source of Truth" principle.
- **Untestable:** AC3 "czas wykonania nie wzrósł znacząco (±10%)". In a local development environment (shared resources, background processes), a 10% variance is noise. This will lead to false failures.

### Hidden Risks & Dependencies
- **Documentation Drift:** The story changes the fundamental project structure defined in `architecture.md` but lists no task to update it.
- **Import Hell:** `test_config.py` likely contains shared helpers (non-fixture) or localized classes used across the 3000 lines. Splitting this requires careful analysis of imports to avoid circular dependencies or code duplication.
- **Git History:** Simple file deletion/creation destroys `git blame` history. The plan should ideally use `git mv` or similar strategies where possible to preserve history for at least one of the resulting files.

### Estimation Reality-Check
- **Estimate: 2 SP.** Realistic. The task is mechanical (cut & paste), though verifying imports and fixtures will take the majority of the time. The complexity lies in dependency management, not logic.

### Technical Alignment
- **Violation:** `docs/architecture.md` (Test Organization) explicitly lists `test_config.py` as a core component. The story contradicts the architecture document without a corresponding update task.
- **Alignment:** The move to `conftest.py` for shared fixtures is strongly aligned with pytest best practices and the project's goal of clean code.

### Final Score (7/10)
### Verdict: READY
*Condition: AC5 must be decided (keep or remove, not optional) and a task to update `architecture.md` must be added during implementation.*