### Code Review 1.4

### Architectural Sins
- `src/bmad_assist/core/config.py:389-392` treats a directory named `bmad-assist.yaml` as a hard error, blocking fallback to global config. Dev notes expect directories to be ignored (treated as missing) so global-only still loads; current behavior elevates a benign state to failure.

### Pythonic Crimes & Readability
- No additional readability issues observed in the touched areas.

### Performance & Scalability
- No performance-specific concerns in the config loading path beyond normal YAML parsing.

### Correctness & Safety
- `src/bmad_assist/core/config.py:438-447` allows non-existent `project_path` values to pass silently and fall back to globals. AC12 requires the path be a directory; typos will quietly skip project config instead of surfacing a ConfigError, risking incorrect config.
- `src/bmad_assist/core/config.py:395-400` (and global path errors) re-raise ConfigError without clearing the singleton. If a prior valid config was loaded, `get_config()` will keep returning stale state after a failed project/global load, violating “fail closed” expectations and making retries misleading.

### Maintainability Issues
- Story File List vs git reality: only `pyproject.toml` is modified in git, but the story claims changes to `config.py`, `__init__.py`, tests, and sprint docs. The undocumented dependency change (types-PyYAML) suggests the Dev Agent Record/File List is out of sync with actual changes.

### Suggested Fixes
- Handle project config directories as “missing” to allow global-only flow: guard `is_file()` check by returning `None` when the path exists but is a directory.
- Enforce `project_path` existence: if the resolved path does not exist, raise `ConfigError("project_path must be a directory, got missing path: …")` to satisfy AC12 and avoid silent fallback.
- Clear the config singleton on any load failure (parse or validation) for both global and project paths before re-raising, ensuring callers can’t observe stale state after an error.
- Update the story Dev Agent Record/File List to include the actual change in `pyproject.toml` (types-PyYAML) or revert if unintended.

### Final Score (1-10)
4

### Verdict: MAJOR REWORK
