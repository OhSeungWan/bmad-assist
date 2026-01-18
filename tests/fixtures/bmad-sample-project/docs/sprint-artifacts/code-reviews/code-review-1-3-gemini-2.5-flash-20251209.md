### Code Review 1.3

### Architectural Sins
- **Test Logic Leaking into Production**: The `_reset_config()` function exists solely for testing purposes but is present in the production module. This breaks the boundary between application logic and test harness.
- **Global Mutable State**: While the Singleton pattern is requested, the implementation uses a module-level `_config` variable that is effectively a global variable. This makes the system fragile to state ordering issues, as evidenced by the need for `_reset_config` in tests.

### Pythonic Crimes & Readability
- **Pydantic Hack**: Usage of `object.__setattr__(self, "state_path", ...)` inside `expand_state_path` to bypass `frozen=True` immutability is ugly and brittle. If the model needs to mutate during validation, it shouldn't be frozen, or should use a proper `AfterValidator` that returns a new instance.
- **Type Hint Lying**: `load_global_config(path: Path | None = None)` claims to only accept `Path` or `None`. However, the implementation `Path(path)` explicitly supports strings, and `test_path_type_conversion` explicitly tests passing a string. The type hint should be `path: str | Path | None` if this behavior is intended and tested.

### Performance & Scalability
- **Memory Inefficiency**: `path.read_text()` reads the entire file into memory. While currently capped at 1MB, this pattern encourages bad habits.

### Correctness & Safety
- **CRITICAL SECURITY (TOCTOU)**: The file size check in `_load_yaml_file` introduces a **Time-Of-Check Time-Of-Use** vulnerability.
    - Code checks `path.stat().st_size` (Time of Check).
    - Code calls `path.read_text()` (Time of Use).
    - An attacker (or race condition) can swap the file with a massive one between these two calls, causing the application to read an arbitrarily large file into memory, leading to an OOM Denial of Service.
- **XDG Violation**: Hardcoding `~/.bmad-assist` violates the XDG Base Directory specification standard on Linux (`~/.config/bmad-assist`). The application behaves like a rude guest in the user's home directory.

### Maintainability Issues
- **Hardcoded Paths**: `GLOBAL_CONFIG_PATH` is hardcoded to a specific hidden directory pattern rather than being configurable via environment variables (e.g., `BMAD_CONFIG_DIR`).

### Suggested Fixes
**Fix TOCTOU and Memory Issue:**
Refactor `_load_yaml_file` to read the stream with a limit, rather than stat-then-read.

```python
def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file with safety checks."""
    try:
        # Secure read with size limit
        with path.open("r", encoding="utf-8") as f:
            content = f.read(MAX_CONFIG_SIZE + 1) # Read 1 byte more to detect overflow
            
        if len(content) > MAX_CONFIG_SIZE:
             raise ConfigError(
                f"Config file {path} is too large. "
                f"Maximum allowed size is {MAX_CONFIG_SIZE} bytes (1MB)."
            )

        return yaml.safe_load(content) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}") from e
    except OSError as e:
        raise ConfigError(f"Cannot read config file {path}: {e}") from e
```

**Fix Type Hint:**
Update signature to `def load_global_config(path: str | Path | None = None) -> Config:` to match implementation and tests.

### Final Score (1-10)
7

### Verdict: APPROVE
(Conditional on fixing the Security TOCTOU issue. The XDG violation is a design choice but should be reconsidered in future.)
