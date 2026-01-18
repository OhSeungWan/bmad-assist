### Code Review 1.4

### Architectural Sins
- **Exception Leakage**: The `load_config` function raises `pydantic.ValidationError` directly. While `load_global_config` and `load_config_with_project` wrap this in `ConfigError`, `load_config` is exposed as a public API in the module docstring ("Usage: from bmad_assist.core import ... load_config"). This violates the project's exception hierarchy principle ("Custom exceptions inherit from BmadAssistError") by leaking a 3rd-party library exception to the caller.
- **Ambiguous Validation Strategy**: `load_config_with_project` loads raw dicts from both global and project files, merges them, and *then* validates. If the global configuration contains a schema violation (e.g., `timeout: "string"`), the error message "Invalid configuration (merged from global + project)" forces the user to guess which file is the culprit. A robust implementation should validate the global config independently first to isolate errors.

### Pythonic Crimes & Readability
- **None**: The code generally adheres to PEP 8 and uses type hints effectively.

### Performance & Scalability
- **Recursion Vulnerability**: The `_deep_merge` function uses unbounded recursion. While normal configuration files are shallow, a malicious YAML file with circular references (using anchors/aliases) could trigger a `RecursionError` and crash the application. While `MAX_CONFIG_SIZE` limits the file size, it doesn't prevent circular structures from consuming stack space.

### Correctness & Safety
- **Correct**: The implementation correctly handles list replacement (vs. merging) and path expansion.
- **Correct**: The `MAX_CONFIG_SIZE` check correctly mitigates memory exhaustion DoS attacks.
- **Correct**: AC11 and AC12 are correctly implemented with specific error handling.

### Maintainability Issues
- **None**: The code is well-structured and the comprehensive test suite (2400+ lines) makes it highly maintainable.

### Suggested Fixes

**Fix 1: Wrap ValidationError in load_config**
```python
def load_config(config_data: dict[str, Any]) -> Config:
    # ...
    try:
        _config = Config.model_validate(config_data)
        return _config
    except ValidationError as e:
        _config = None
        raise ConfigError(f"Configuration validation failed: {e}") from e
```

**Fix 2: Add recursion check to _deep_merge**
```python
def _deep_merge(base: dict[str, Any], override: dict[str, Any], _depth: int = 0) -> dict[str, Any]:
    if _depth > 20:  # Reasonable limit for config nesting
        raise ConfigError("Configuration nesting too deep (possible circular reference)")
    
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value, _depth + 1)
        else:
            result[key] = value
    return result
```

**Fix 3: Validate Global Config Independently (Optional but Recommended)**
In `load_config_with_project`, attempt to validate `global_data` (if it exists) before merging. If it fails, raise a specific error pointing to the global config file.

### Final Score (1-10)
9

### Verdict: APPROVE
The implementation is solid, well-tested, and meets all functional requirements. The identified issues are minor architectural/safety improvements rather than blockers. The explicit exception wrapping and recursion limit should be addressed in a future refactor or cleanup task but do not prevent merging.
