### Code Review 1.8

**Story:** Test Suite Refactoring - split monolithic test_config.py (3003l) into modules & extract fixtures.

**Changes:** test_config.py deleted. New: conftest.py (23l), test_config_models.py (325l), test_config_loading.py (276l), test_config_project.py (363l), test_config_env.py (393l), + edge_cases/merge/errors/singleton (135-464l all &lt;500). test_cli.py (871l) untouched (OOS). generator.py (698l) pre-exist.

**Verification:** pytest tests/: 294 PASS (0.67s core). Coverage OK. wc-l OK new files. mypy 41 err (mostly src stubs). ruff 11 fixable.

### Architectural Sins
- None. Modular split aligns with architecture (tests mirror src/core/). Fixtures shared properly.

### Pythonic Crimes & Readability
- I001 unsorted imports: test_config_generator.py:14, test_config_models.py:14, test_loop.py:105 etc. (`ruff format .`)
- E501 long lines: test_config_loading_edge_cases.py:211,327.
- F841 unused `config_path`: test_config_generator.py:351.
- SIM300 Yoda: test_config_loading.py:33 (`assert GLOBAL_CONFIG_PATH == ...` → `assert ... == GLOBAL_CONFIG_PATH`).

### Performance & Scalability
- None. Refactor neutral (tests ±10% time OK).

### Correctness & Safety
- mypy: import-untyped (src lacks py.typed/stubs), unused `# type: ignore` (test_config_models_singleton.py:71,78,...), "override" untyped (test_config_deep_merge.py:143).
- No runtime issues (294 PASS).

### Maintainability Issues
- **Process:** Tasks all [ ] (no [x]), Dev Record/File List=TBD, status ready-for-dev mimo done.
- Extra changes: power-prompts/*.md (5), .gitignore, sprint-status.yaml (undocumented).
- Untracked bmad-backup.tar.gz (cleanup?).
- No independent file tests (`pytest tests/core/test_config_models.py` etc.).

### Suggested Fixes
```
# Lint all
ruff check --fix tests/

# mypy: add types/stubs src, remove unused ignores
# e.g. tests/core/test_config_deep_merge.py:143 override: dict[str, Any] = ...

# Story update (edit):
- Mark Tasks [x]
- File List: tests/core/{conftest,test_config_*}.py (deleted test_config.py)
- Dev Record: "Split into 10 modules, extracted fixtures, 294 PASS"

git add tests/core/; git rm bmad-backup.tar.gz?; git commit -m "feat(tests): complete 1.8 refactor"
```

### Final Score (1-10)
8

### Verdict: APPROVE
(Run fixes, update story → done)