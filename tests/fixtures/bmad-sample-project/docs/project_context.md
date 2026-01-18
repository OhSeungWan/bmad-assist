---
project_name: 'bmad-assist'
user_name: 'Pawel'
date: '2025-12-08'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'security_rules', 'anti_patterns']
status: 'complete'
rule_count: 28
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

```
Python 3.11+
├── typer              # CLI framework (built on Click)
├── pydantic           # Config validation (v2)
├── pyyaml             # YAML parsing
├── python-frontmatter # Markdown with frontmatter
├── jinja2             # Templates (power-prompts, dashboard)
└── rich               # CLI output (logging, progress)
```

**Project Structure:** src layout with `pyproject.toml`

---

## Critical Implementation Rules

### Python Rules

- **Type hints required** on all functions (args + return)
- **Pydantic models** for all config/data structures (not dataclasses)
- **Google-style docstrings** for public functions only
- **No bare `except:`** - always catch specific exceptions from `core/exceptions.py`
- **Use `pathlib.Path`** instead of string paths where possible
- **f-strings preferred** over .format() or %
- **All imports** at top of file, grouped: stdlib → third-party → local

### CLI Framework Rules

- **Typer commands** in `cli.py` only - no business logic
- **Rich console** for all user-facing output (not print())
- **subprocess.run()** with explicit `timeout=` parameter always
- **capture_output=True** for all subprocess calls
- **Never shell=True** in subprocess (security)

### Config Access Pattern

```python
# CORRECT - use singleton
from bmad_assist.core.config import get_config
config = get_config()

# WRONG - never load config in functions
config = load_config("path")  # ❌
```

### Atomic Write Pattern

```python
# CORRECT - atomic write
import os
temp_path = f"{target_path}.tmp"
with open(temp_path, 'w') as f:
    f.write(content)
os.rename(temp_path, target_path)

# WRONG - direct write
with open(target_path, 'w') as f:  # ❌
    f.write(content)
```

---

## Security Rules

- **Credentials ONLY in .env** - never in code, config files, or logs
- **provider-configs/*.json** - behavioral settings only, NO secrets
- **chmod 600** for .env file
- **Never log** subprocess stdout if it might contain secrets
- **CLI tools read env vars directly** - bmad-assist never handles API keys

---

## Provider Architecture Rules

- **All providers inherit `BaseProvider` ABC** from `providers/base.py`
- **Multi-LLM cannot modify files** - only Master has write permission
- **Guardian runs on EVERY output** - Master and Multi alike
- **Provider configs** use naming: `{role}-{provider}-{model}.json`

---

## Module Organization

- Each module folder has `__init__.py` exporting public API
- Use `__all__` to explicitly define exports
- Private functions/classes prefixed with `_`

---

## Anti-Patterns to Avoid

❌ Loading config in every function (use `get_config()` singleton)
❌ Mixing naming conventions (strict PEP8: snake_case functions, PascalCase classes)
❌ Business logic in `cli.py` (delegate to `core/loop.py`)
❌ Direct file writes without atomic pattern
❌ Catching bare exceptions (`except:` or `except Exception:`)
❌ Using `print()` instead of Rich console
❌ subprocess without timeout parameter
❌ shell=True in subprocess calls

---

## Testing Rules

- Tests mirror src structure: `tests/core/`, `tests/providers/`, etc.
- Test files named `test_*.py`
- Use pytest fixtures in `conftest.py`
- Mock external CLI calls (subprocess) in unit tests

---

## Reference Documents

- **Architecture:** `docs/architecture.md` - all architectural decisions
- **PRD:** `docs/prd.md` - functional and non-functional requirements

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Refer to `docs/architecture.md` for detailed patterns and examples

**For Humans:**
- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2025-12-08
