# Ruthless Story Validation 1.4

**Story:** docs/sprint-artifacts/1-4-project-configuration-override.md
**Validator:** Multi-LLM (Sonnet 4.5)
**Date:** 2025-12-09
**Validation Mode:** Adversarial - Zero Tolerance for Ambiguity

---

## INVEST Violations

### Violation #1: Estimation Potentially Low
**Severity: 5/10**

Story is estimated at 3 SP, but complexity suggests 4-5 SP:
- 10 AC classes (same as Story 1.3, but more complex logic)
- Deep merge with recursive logic, edge cases, list replacement
- Missing ACs/tests will add ~2 more test classes
- Story 1.3 (3 SP) had simpler linear YAML loading

**Impact:** Developer might underestimate time, risk missing sprint deadline.

**Recommendation:** Re-estimate to 4 SP after adding missing ACs.

---

## Acceptance Criteria Issues

### Critical Issue #1: Missing AC for Invalid YAML in Project Config
**Severity: 9/10**

Story 1.3 has AC3 for malformed YAML in global config. Story 1.4 is **completely silent** on what happens when project config (`./bmad-assist.yaml`) has invalid YAML syntax.

**Example Scenario:**
```yaml
# Malformed ./bmad-assist.yaml
providers:
  master: [unclosed bracket
```

**Impact:**
- Developer won't know expected behavior
- Could implement inconsistent error handling vs Story 1.3
- No test coverage for this critical error path

**Recommendation:** Add AC11:
```gherkin
AC11: ConfigError for Malformed Project YAML
Given project config exists at ./bmad-assist.yaml with invalid YAML syntax
When load_config_with_project(project_path) is called
Then ConfigError is raised
And error message contains "project config" and file path
And error distinguishes between global vs project config failure
```

---

### Critical Issue #2: Missing AC for Post-Merge Validation Failure
**Severity: 7/10**

What if project config overrides with values that only fail during Pydantic validation AFTER merge?

**Example:**
- Global: `providers.master.provider: claude, model: opus_4`
- Project: `providers.master.model: invalid_xyz_model`
- Merge succeeds (syntactically valid), but Pydantic validation fails

**Current Problem:** Error message won't indicate which config file (global vs project) has the bad value.

**Impact:** User debugging will be painful - they won't know if error is in `~/.bmad-assist/config.yaml` or `./bmad-assist.yaml`.

**Recommendation:** Add AC12:
```gherkin
AC12: Clear Error Messages for Post-Merge Validation Failures
Given global config has valid master provider
And project config overrides with invalid model name
When configuration is merged and validated
Then ConfigError is raised
And error message indicates project config as source of invalid value
And error includes both file paths for debugging context
```

---

### Ambiguity Issue #3: List Replacement Scope Unclear
**Severity: 5/10**

AC7 documents list replacement for `providers.multi`:
> "providers.multi contains only [codex/o3] from project"
> "gemini/gemini_2_5_pro is NOT preserved (list replacement, not append)"

**Question:** Does this apply to ALL lists in config or just `providers.multi`?

**Future Scenario:**
```yaml
# Global config
notifications:
  channels: [email, slack]

# Project config
notifications:
  channels: [telegram]
```

**Unclear:** Are `channels` REPLACED or is this behavior specific to `providers.multi`?

**Impact:** Future config additions might break assumptions about merge behavior.

**Recommendation:** Clarify in AC7 or Dev Notes:
> "Deep merge strategy: ALL lists are replaced (not merged). This is a global rule for any list field in config, not specific to `providers.multi`."

---

### Testability Issue #4: AC7 Example Uses Only providers.multi
**Severity: 3/10**

AC7 tests list replacement, but only with `providers.multi`. To validate the general rule, need test with a DIFFERENT list field.

**Recommendation:** Add test case with another list (e.g., hypothetical `excluded_paths: [...]`) to prove behavior is consistent.

---

## Hidden Risks & Dependencies

### Critical Risk #1: No Depth Limit for Recursive Deep Merge
**Severity: 6/10**

`_deep_merge()` is recursive without depth limit:
```python
def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)  # ← Unbounded recursion
```

**Attack Vector:** Maliciously crafted or accidentally deeply nested config could cause stack overflow.

**Example:**
```yaml
# 150 levels of nesting
a:
  b:
    c:
      d:
        # ... 146 more levels
```

**Impact:**
- Denial of service via config file
- Hard-to-debug crashes (`RecursionError`)
- No protection against pathological configs

**Recommendation:** Add depth limit:
```python
def _deep_merge(
    base: dict[str, Any],
    override: dict[str, Any],
    _depth: int = 0,
    max_depth: int = 100
) -> dict[str, Any]:
    if _depth > max_depth:
        raise ConfigError(f"Config nesting exceeds maximum depth ({max_depth} levels)")

    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value, _depth + 1, max_depth)
        else:
            result[key] = value
    return result
```

---

### Risk #2: Input Mutation in Deep Merge Not Explicitly Prevented
**Severity: 4/10**

`_deep_merge()` example uses `.copy()` on base, which prevents shallow mutation. But story doesn't explicitly document:
1. **Inputs MUST NOT be modified** (immutability requirement)
2. What if `base` or `override` contain mutable nested objects?

**Example Issue:**
```python
base = {"nested": {"key": "value"}}
override = {"nested": {"key2": "value2"}}
result = _deep_merge(base, override)
# If not careful, base["nested"] could be mutated
```

**Impact:** Subtle bugs if global config dict is reused and accidentally mutated.

**Recommendation:** Add to Anti-Patterns section:
> "❌ Don't mutate input dicts in `_deep_merge()` - use `.copy()` and ensure deep immutability."

Add test:
```python
def test_override_not_modified(self) -> None:
    """Override dict is not modified by merge."""
    override = {"key": "override"}
    _deep_merge({"key": "base"}, override)
    assert override == {"key": "override"}  # Unchanged
```

---

### Risk #3: Missing Validation for project_path Type
**Severity: 7/10**

Function signature accepts `project_path: str | Path | None`, but what if user passes:
- A file path instead of directory? (`/home/user/my-project/some-file.txt`)
- A path that exists but isn't a directory?

**Current Code Pattern:**
```python
project_config_path = project_path / "bmad-assist.yaml"
```

**If project_path is a file:** Path concatenation succeeds, but reading will fail with confusing error.

**Impact:** Cryptic error message instead of clear validation error.

**Recommendation:** Add validation:
```python
def load_config_with_project(
    project_path: str | Path | None = None,
    *,
    global_config_path: str | Path | None = None,
) -> Config:
    project_dir = Path(project_path) if project_path else Path.cwd()

    if project_dir.exists() and not project_dir.is_dir():
        raise ConfigError(
            f"project_path must be a directory, got file: {project_dir}"
        )

    # ... rest of function
```

Add test:
```python
def test_project_path_is_file_raises_error(self, tmp_path: Path) -> None:
    """project_path pointing to a file raises clear error."""
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("i am a file")

    with pytest.raises(ConfigError) as exc_info:
        load_config_with_project(project_path=file_path)
    assert "directory" in str(exc_info.value).lower()
```

---

### Dependency Risk #4: Inconsistent API with Story 1.3
**Severity: 4/10**

**Story 1.3:** `load_global_config(path: str | Path | None = None)`
**Story 1.4:** `load_config_with_project(project_path, *, global_config_path)`

Note the `*` making `global_config_path` **keyword-only**.

**Inconsistency:**
- Story 1.3's `path` is positional (can call `load_global_config("/path")`)
- Story 1.4's `global_config_path` is keyword-only (must call `load_config_with_project(..., global_config_path="/path")`)

**Why is this inconsistent?** Both are testing-only parameters.

**Impact:** API users (and AI agents) will be confused by different calling conventions.

**Recommendation:** Align both functions:
- **Option A:** Make both keyword-only (add `*` to Story 1.3 - requires changing existing code)
- **Option B:** Make both positional (remove `*` from Story 1.4)

Prefer **Option B** (less breaking change).

---

## Estimation Reality-Check

**Current Estimate:** 3 SP
**Realistic Estimate:** 4-5 SP

**Complexity Analysis:**

| Factor | Story 1.3 (3 SP) | Story 1.4 (3 SP) | Difference |
|--------|------------------|------------------|------------|
| Lines of code | ~40 | ~50 | +25% |
| ACs | 10 | 10 (+2 missing) | +20% when fixed |
| Test classes | 10 | 10 (+2 missing) | +20% when fixed |
| Core logic | Linear YAML load | Recursive deep merge | More complex |
| Edge cases | File errors, validation | File errors + merge conflicts + 4 scenarios | More edge cases |

**Additional Factors:**
- Deep merge is recursive (more cognitive load)
- 4 config existence scenarios to handle (both/global/project/neither)
- List replacement vs dict merge adds complexity
- Missing ACs will add ~2-3 hours of work

**Recommendation:** Re-estimate to **4 SP** after adding missing ACs and tests.

---

## Technical Alignment

### ✅ Architecture Compliance - GOOD

**Correctly aligned with architecture.md:**
- ✅ Location: `src/bmad_assist/core/config.py` (extend existing)
- ✅ Exception: Uses `ConfigError` from Story 1.2
- ✅ Config Access: Maintains singleton via `get_config()`
- ✅ Naming: PEP8 snake_case functions
- ✅ Type Hints: Required on ALL functions
- ✅ Docstrings: Google-style for public APIs

**Correctly builds on previous stories:**
- ✅ Uses `_load_yaml_file()` from Story 1.3
- ✅ Uses `load_config()` for validation (Story 1.2)
- ✅ Uses `GLOBAL_CONFIG_PATH` constant (Story 1.3)

---

### ⚠️ Minor Architecture Issue: Parameter Style Inconsistency

**Story 1.3 pattern:**
```python
def load_global_config(path: str | Path | None = None) -> Config:
```

**Story 1.4 pattern:**
```python
def load_config_with_project(
    project_path: str | Path | None = None,
    *,
    global_config_path: str | Path | None = None,  # Keyword-only
) -> Config:
```

**Issue:** Mixing positional and keyword-only parameters across related functions.

**Impact:** Inconsistent API makes it harder for developers to remember calling conventions.

**Severity:** 4/10 (minor annoyance, not a blocker)

---

### ⚠️ Missing Performance Consideration

**Issue:** No max depth limit for recursive `_deep_merge()`.

**Architectural Concern:** Python has default recursion limit of ~1000. Deeply nested config could hit this limit with cryptic error.

**Architecture.md doesn't specify:** Performance requirements for config loading.

**Should be added:** Non-functional requirement about config complexity limits.

**Severity:** 6/10 (could cause production issues with complex configs)

---

## Testing Quality Assessment

### ✅ Good Test Coverage Structure

**Strengths:**
- ✅ Test classes organized by AC (clear mapping)
- ✅ Uses `tmp_path` fixture (best practice)
- ✅ Tests both success and failure paths
- ✅ Tests singleton integration (AC10)
- ✅ Tests immutability (`test_base_not_modified`)

---

### ❌ Critical Missing Tests

**Missing Test #1: Malformed Project YAML**
**Severity: 9/10**

Story 1.3 has `TestMalformedYaml` class for global config.
Story 1.4 has **NO equivalent** for project config.

**What's Missing:**
```python
class TestProjectConfigMalformedYaml:
    def test_invalid_project_yaml_raises_error(self, tmp_path: Path) -> None:
        """Invalid YAML in project config raises ConfigError."""
        global_config = tmp_path / "config.yaml"
        global_config.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
""")

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_config = project_dir / "bmad-assist.yaml"
        project_config.write_text("invalid: yaml: syntax:")

        with pytest.raises(ConfigError) as exc_info:
            load_config_with_project(
                project_path=project_dir,
                global_config_path=global_config,
            )
        assert "project config" in str(exc_info.value).lower()
        assert "bmad-assist.yaml" in str(exc_info.value)
```

**Impact:** Critical error path completely untested. Production bug risk: HIGH.

---

**Missing Test #2: project_path is File (not Directory)**
**Severity: 7/10**

Function expects `project_path` to be a directory, but doesn't validate.

**What's Missing:**
```python
def test_project_path_is_file_raises_error(self, tmp_path: Path) -> None:
    """project_path pointing to a file raises clear error."""
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("i am a file")

    with pytest.raises(ConfigError) as exc_info:
        load_config_with_project(project_path=file_path)
    assert "directory" in str(exc_info.value).lower()
```

**Impact:** Users get cryptic errors instead of helpful validation message.

---

**Missing Test #3: Override Dict Not Modified**
**Severity: 3/10**

Tests verify `base` dict isn't modified, but should also test `override` dict immutability.

**What's Missing:**
```python
def test_override_not_modified(self) -> None:
    """Override dict is not modified by merge."""
    override = {"key": "new_value"}
    _deep_merge({"key": "old_value"}, override)
    assert override == {"key": "new_value"}  # Unchanged
```

**Impact:** Minor - ensures function contract is complete.

---

**Missing Test #4: Post-Merge Validation Failure**
**Severity: 7/10**

What if merged config is valid YAML but fails Pydantic validation?

**What's Missing:**
```python
def test_post_merge_validation_error_mentions_project_config(
    self, tmp_path: Path
) -> None:
    """Validation error after merge indicates project config as source."""
    global_config = tmp_path / "config.yaml"
    global_config.write_text("""
providers:
  master:
    provider: claude
    model: opus_4
""")

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    project_config = project_dir / "bmad-assist.yaml"
    project_config.write_text("""
providers:
  master:
    model: invalid_model_xyz
""")

    with pytest.raises(ConfigError) as exc_info:
        load_config_with_project(
            project_path=project_dir,
            global_config_path=global_config,
        )
    # Should indicate project config as source
    assert "project" in str(exc_info.value).lower() or "bmad-assist.yaml" in str(exc_info.value)
```

**Impact:** Users won't know which config file to fix.

---

### Coverage Target

**Story claims:** >=95% coverage on new code

**Estimated actual coverage with current tests:** ~85%

**Why lower?** Missing error paths:
- Project YAML malformed
- project_path validation
- Post-merge validation failure

**Recommendation:** Add 3 missing test classes to reach 95%+.

---

## Quality and Prevention - NEEDS IMPROVEMENT

### ✅ Good: Code Reuse

**Correctly identified:**
- ✅ Uses existing `_load_yaml_file()` from Story 1.3
- ✅ Uses existing `load_config()` for validation (Story 1.2)
- ✅ Uses existing `ConfigError` exception (Story 1.2)

---

### ⚠️ Anti-Patterns Section Incomplete

**Story documents these anti-patterns:**
- ❌ Don't mix naming conventions
- ❌ Don't catch bare exceptions
- ❌ Don't access config without singleton

**Missing critical anti-patterns for THIS story:**
- ❌ **Don't mutate input dicts in deep_merge** ← Should be here!
- ❌ **Don't allow unbounded recursion** ← Should warn about depth limit!
- ❌ **Don't assume project_path is a directory** ← Should validate!

**Impact:** Developer might miss these gotchas and introduce bugs.

---

### ❌ Missing Common Mistakes Section

**Story should warn about:**

**Mistake #1: Forgetting to copy() before modifying**
```python
# BAD
def _deep_merge(base, override):
    for key, value in override.items():
        base[key] = value  # Mutates input!
    return base

# GOOD
def _deep_merge(base, override):
    result = base.copy()
    for key, value in override.items():
        result[key] = value
    return result
```

**Mistake #2: Not handling None values in merge**
```python
# What if override has None value?
override = {"key": None}
# Should None override base value or be ignored?
```

**Mistake #3: Confusing list replacement with append**
```python
# Developer might think lists are appended
# Story should emphasize: ALL lists are REPLACED
```

---

### ❌ Missing Troubleshooting Guidance

**Story provides implementation details, but NOT debugging help.**

**What's missing:**
```markdown
### Debugging Merge Conflicts

If merged config doesn't match expectations:

1. **Print raw YAML** from both files before merge
   ```python
   print("Global:", global_dict)
   print("Project:", project_dict)
   ```

2. **Print merged dict** before Pydantic validation
   ```python
   merged = _deep_merge(global_dict, project_dict)
   print("Merged:", merged)
   ```

3. **Check field type:**
   - Nested dict → merges recursively
   - List → replaces entirely
   - Scalar → project overrides global

4. **Verify field names** match exactly (YAML is case-sensitive)
```

**Impact:** Developer debugging will be slower without this guidance.

---

## LLM Optimization Issues

### Issue #1: Test Code Too Verbose (278 Lines)
**Severity: 5/10**

**Current:** Story includes 278 lines of full test code examples (lines 459-737).

**Impact:**
- Story is 866 lines total
- Test section is 32% of story length
- High token cost for LLM processing
- Harder to scan for key information

**Recommendation:** Summarize tests instead of full code:

**Before (verbose):**
```python
class TestDeepMerge:
    """Tests for _deep_merge helper function."""

    def test_scalar_override(self) -> None:
        """Override scalar values replace base values."""
        base = {"timeout": 300, "retries": 3}
        override = {"timeout": 600}
        result = _deep_merge(base, override)
        assert result["timeout"] == 600
        assert result["retries"] == 3
    # ... 20 more lines per test
```

**After (optimized):**
```markdown
### Test Cases

**TestDeepMerge** (AC2, AC7, AC8)
- `test_scalar_override`: Override replaces base values
- `test_nested_dict_merge`: Dicts merge recursively
- `test_list_replacement`: Lists replace (not append)
- `test_base_not_modified`: Immutability check

**TestProjectConfigOverride** (AC1)
- `test_project_overrides_global_scalar`
- `test_non_overridden_preserved`

*Full test code in tests/core/test_config.py*
```

**Token savings:** ~60%
**Readability:** Much improved

---

### Issue #2: Missing Quick Reference Table
**Severity: 3/10**

**Story has detailed ACs, but lacks at-a-glance summary.**

**Recommendation:** Add to top of story:

```markdown
## Quick Reference: Config Merge Behavior

| Scenario | Behavior | AC |
|----------|----------|-----|
| Both exist | Deep merge (project wins) | AC1, AC2 |
| Global only | Use global | AC4 |
| Project only | Use project | AC3 |
| Neither | ConfigError | AC5 |
| Nested dicts | Merge recursively | AC2, AC8 |
| Lists | Replace entirely | AC7 |
| Scalars | Project overrides | AC1 |
```

**Benefit:** LLM can understand all scenarios in 5 seconds instead of reading 10 ACs.

---

### Issue #3: No "Critical Decisions" Callout
**Severity: 3/10**

**Story has decisions scattered throughout. Better: consolidate at top.**

**Recommendation:**
```markdown
## ⚡ CRITICAL DECISIONS (Non-Negotiable)

These decisions are FINAL - do not ask user during implementation:

1. **Deep merge strategy:** Dicts merge recursively, lists REPLACE (not append)
2. **Error on missing both:** If neither global nor project config exists, raise ConfigError with "run bmad-assist init" hint
3. **Immutability:** `_deep_merge()` MUST NOT modify input dicts (use .copy())
4. **Singleton update:** `load_config_with_project()` updates global singleton via `load_config()`
5. **Path expansion:** state_path tilde expansion happens in Pydantic validator (Story 1.2)
```

**Benefit:** LLM sees all constraints upfront, reduces hallucination risk.

---

### Improvement #4: Implementation Flow Not Sequential
**Severity: 2/10**

**Story 1.3 had clear implementation order:**
> "First implement `_load_yaml_file()`, then `load_global_config()`, then exports, then tests."

**Story 1.4 has tasks but no explicit flow.**

**Recommendation:** Add:
```markdown
### Recommended Implementation Order

1. **Start:** Implement `_deep_merge()` helper (Task 1)
   - Write function
   - Add unit tests immediately
   - Verify base/override not modified

2. **Next:** Implement `_load_project_config()` helper (Task 3)
   - Returns None if not found (not an error)
   - Reuses `_load_yaml_file()` from Story 1.3

3. **Core:** Implement `load_config_with_project()` (Task 2)
   - Handle 4 scenarios: both/global/project/neither
   - Call `_deep_merge()` when both exist
   - Call `load_config()` with result

4. **Export:** Update `core/__init__.py` (Task 4)

5. **Test:** Write comprehensive tests (Task 5)
   - Start with happy path (AC1, AC2)
   - Then edge cases (AC3-AC10)
   - Finally error paths (malformed YAML, validation failures)

6. **Verify:** Run coverage, mypy, ruff
```

**Benefit:** Clear path reduces "where do I start?" paralysis.

---

## Final Score (1-10)

**Score: 7.5/10**

**Breakdown:**

| Criterion | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| INVEST compliance | 7/10 | 15% | 1.05 |
| AC completeness | 6/10 | 25% | 1.50 |
| Technical alignment | 8/10 | 15% | 1.20 |
| Test coverage | 6/10 | 20% | 1.20 |
| Code quality guidance | 5/10 | 10% | 0.50 |
| LLM optimization | 7/10 | 10% | 0.70 |
| Dependencies clarity | 10/10 | 5% | 0.50 |

**Total:** 7.5/10 (rounded from 6.65)

---

## Verdict: MAJOR REWORK

### Why Not "READY"?

Story has **6 critical gaps** that would cause production bugs or developer frustration:

1. ❌ **Missing AC for invalid project YAML** (severity 9/10)
2. ❌ **Missing AC for post-merge validation failure** (severity 7/10)
3. ❌ **Missing test for malformed project YAML** (severity 9/10)
4. ❌ **No depth limit on recursive merge** (severity 6/10)
5. ❌ **Missing test for project_path validation** (severity 7/10)
6. ❌ **Inconsistent API with Story 1.3** (severity 4/10)

**These MUST be fixed before development starts.**

---

### What's Excellent (Keep This!)

✅ **Dependencies section is exemplary** - best I've seen
✅ **Previous story learnings well-documented** - great context
✅ **Deep merge strategy clearly explained** with code examples
✅ **Scope boundaries crystal clear** - IN/OUT scope explicit
✅ **Dev Notes comprehensive** - architecture compliance checked

---

### Estimated Rework Time

**To reach "READY" status:**
- Add 2 missing ACs: 30 minutes
- Add 3 missing test classes: 1-2 hours
- Add depth limit to `_deep_merge()`: 30 minutes
- Align parameter style with Story 1.3: 15 minutes
- Clarify list replacement scope: 15 minutes
- Add troubleshooting guidance: 30 minutes

**Total: 3-4 hours of rework**

---

## Recommendations

### Must Fix Before Development (Priority 1)

1. **Add AC11:** ConfigError for malformed project YAML
2. **Add AC12:** Clear error for post-merge validation failure
3. **Add test class:** `TestProjectConfigMalformedYaml`
4. **Add test class:** `TestProjectPathValidation`
5. **Add depth limit:** `_deep_merge(..., _depth=0, max_depth=100)`
6. **Add validation:** Check `project_path.is_dir()` before use

### Should Improve (Priority 2)

7. **Align API:** Remove `*` from `load_config_with_project()` signature OR add to Story 1.3
8. **Clarify scope:** State "ALL lists are replaced" not just `providers.multi`
9. **Add anti-pattern:** "Don't mutate inputs in `_deep_merge()`"
10. **Add test:** `test_override_not_modified()` for immutability
11. **Re-estimate:** Change from 3 SP to 4 SP

### Nice to Have (Priority 3)

12. **Optimize:** Reduce test code verbosity (summarize instead of full code)
13. **Add:** Quick Reference table for merge scenarios
14. **Add:** Critical Decisions callout box
15. **Add:** Troubleshooting guidance for merge conflicts
16. **Add:** Implementation order flow

---

## Conclusion

Story 1.4 has **excellent structure and documentation**, but **critical gaps in error handling** make it not ready for implementation.

**The good news:** All issues are fixable in 3-4 hours. After fixes, this will be a **solid, production-ready story**.

**Primary risk:** Developer implements without missing ACs, ships code with untested error paths, users hit confusing errors in production.

**Recommendation:** Fix Priority 1 items (AC11, AC12, 3 missing tests, depth limit), THEN mark ready-for-dev.

---

**Validator:** Multi-LLM (Adversarial Mode)
**Date:** 2025-12-09
**Status:** Story requires MAJOR REWORK before development
