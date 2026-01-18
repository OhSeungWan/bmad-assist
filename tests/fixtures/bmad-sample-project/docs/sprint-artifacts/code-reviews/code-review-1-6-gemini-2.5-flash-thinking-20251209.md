### Code Review 1.6

### Architectural Sins
- **SOLID Violation (Dependency Inversion/Coupling):** `EXIT_SUCCESS`, `EXIT_ERROR`, and `EXIT_CONFIG_ERROR` are defined in `src/bmad_assist/cli.py`. These are application-wide constants that define the contract for process termination. Defining them in the CLI layer couples the core logic (exceptions, loop) to the specific CLI implementation if they ever need to reference them. They should be moved to `src/bmad_assist/core/constants.py` or `src/bmad_assist/core/exceptions.py`.
- **Global State / Singleton Misuse (Console):** `cli.py` instantiates a global `console = Console()`. This object is not passed to `run_loop()`. When Epic 6 is implemented, `run_loop` will likely need to print output. If it instantiates its own `Console`, you risk split-brain output states or threading issues. The `Console` instance should be injected into `run_loop` or available via a core singleton (similar to Config).

### Pythonic Crimes & Readability
- **Rude Library Behavior:** `_setup_logging` calls `logging.root.handlers.clear()`. While acceptable for a top-level CLI script, `bmad_assist` is structured as a package. This aggressively nukes any existing logging setup (e.g., from test runners or if this module is ever imported by another tool). It makes `caplog` fixtures in tests fragile if `_setup_logging` is called during tests (which `run()` does).
- **Function Complexity:** The `run` function in `cli.py` is doing too much: argument validation, logging setup, config loading, error handling, and delegation. It's strictly "glue code" but logic like `if verbose and quiet: _warning(...)` is edging into business logic that belongs in a helper or validator.

### Performance & Scalability
- **None detected:** This is a lightweight CLI entry point. Performance impact is negligible.

### Correctness & Safety
- **Signal Handling Missing:** The story mentions "Signal handling (SIGINT/SIGTERM - Epic 6)" is out of scope, but a robust CLI entry point should usually have a basic `try...except KeyboardInterrupt` block to catch `Ctrl+C` and exit cleanly (code 130) instead of printing a raw Python stack trace, even in this early stage. Currently, a user pressing `Ctrl+C` during `run_loop` (even if it's just a stub) will see a traceback.

### Maintainability Issues
- **Test Coupling:** `tests/test_cli.py` imports `_error`, `_success`, `_warning` private functions (`_`) from `cli.py`. Testing private implementation details makes refactoring brittle. These tests should assert on the *output* (stdout/stderr) rather than mocking/calling internal helper functions.

### Suggested Fixes

**Move Exit Codes to Core:**
Create `src/bmad_assist/core/constants.py`:
```python
EXIT_SUCCESS: int = 0
EXIT_ERROR: int = 1
EXIT_CONFIG_ERROR: int = 2
```

**Refactor `run` to catch KeyboardInterrupt:**
```python
    except KeyboardInterrupt:
        _error("Interrupted by user")
        raise typer.Exit(code=130)
```

**Inject Console:**
Update `run_loop` signature to accept `console: Console`.

### Final Score (1-10)
8

### Verdict: APPROVE
(with suggestions for future cleanup in Epic 6)
