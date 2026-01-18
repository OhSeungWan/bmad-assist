# Code Review – Story 1.1: Project Initialization with pyproject.toml

**Story:** docs/sprint-artifacts/1-1-project-initialization-with-pyproject-toml.md
**Status:** in-progress (issues remain)
**Git vs Story Discrepancies:** 0
**Issues Found:** 2 High, 2 Medium, 0 Low

## Acceptance Criteria Validation
- **AC1 (pyproject metadata):** Implemented (PEP 621-compliant metadata present, values match spec)
- **AC2 (dev install works):** Not validated (no evidence of `uv pip install -e .[dev]`, `uv pip check`, or import test runs)
- **AC3 (CLI entry point help):** Missing (top-level `bmad-assist --help` does not show `--project/--config`; only visible under `run --help`)
- **AC4 (dependencies specified):** Missing (dependency is `typer>=0.9.0`, AC requires `typer[all]>=0.9.0` to include Rich extras)
- **AC5 (src layout, mypy, ruff):** Partially validated (structure/tests present; no evidence of running `mypy` or `ruff` from story tasks)

## Findings
### 🔴 High
1) Dependency mismatch vs AC4 (`pyproject.toml`): `typer>=0.9.0` is missing the `[all]` extra required by AC4; Rich extras not guaranteed.
2) AC3 not met (CLI help): `bmad-assist --help` does not include `--project/--config` options required by AC3 because Typer shows them only under `run --help`.

### 🟡 Medium
3) Test expectation mismatch (`tests/test_cli.py`): `TestNoArgsIsHelp` expects exit code 2, but current CLI with `no_args_is_help=True` exits 0, so test would fail; behavior/assertion are inconsistent.
4) Task verification evidence missing (Tasks 4.x / AC2/AC5): Story marks install/check/mypy/ruff as done, but repo has no artifacts or logs showing these commands were executed; cannot confirm those tasks.

## Task Audit
- Tasks marked [x] for install/validation (4.2–4.7) lack evidence of execution → treat as not verified.

## Recommended Actions
- Update dependencies to `typer[all]>=0.9.0` to satisfy AC4 and include Rich extras.
- Adjust CLI to surface `--project/--config` in top-level help (e.g., move options to callback or customize help) to satisfy AC3.
- Align `TestNoArgsIsHelp` with actual behavior (either expect exit 0 and assert help text, or change CLI behavior to exit 2); keep behavior/test consistent.
- Re-run and document install/check steps: `uv pip install -e .[dev]`, `uv pip check`, `python -c "import bmad_assist"`, `mypy src/`, `ruff check src/`, `pytest`.

## Status & Next Steps
- **New Status:** in-progress (High/Medium issues remain)
- **Issues Fixed:** 0
- **Action Items Created:** 0
