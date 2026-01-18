# Ruthless Story Validation 1.3

**Story:** 1.3 - Global Configuration Loading
**Validator:** Multi-LLM (Sonnet 4.5)
**Date:** 2025-12-09
**Validation Mode:** Adversarial Review

---

## INVEST Violations

### 1. **Ambiguous Default Behavior Decision (Severity: 8/10)**

**Violation:** Story explicitly defers critical architectural decision to implementation phase.

**Evidence (Line 162):**
> "IMPORTANT: Ask user which approach they prefer during implementation."

**Why This Is A Problem:**
- Story is marked `ready-for-dev` but contains a critical fork in the road
- Two mutually exclusive approaches (Option A: raise error vs Option B: return default)
- Implementation cannot start without this decision
- Each option has different test requirements and API contracts

**Impact:**
- Story is NOT actually ready for development
- Developer must stop mid-implementation to ask clarifying questions
- Test cases provided (lines 450-465) contradict each other based on which option is chosen
- Sprint velocity will be interrupted

**Fix Required:**
- Choose ONE approach before marking ready-for-dev
- Update AC4 to reflect chosen approach
- Update test cases to match decision
- Remove "ask user" instruction from dev notes

---

### 2. **"Independent" (Severity: 3/10)**

**Minor Issue:** Story has tight dependency on Story 1.2 implementation details.

**Evidence:**
- Requires `_reset_config()` fixture from Story 1.2 (line 297, line 530)
- Assumes specific validator patterns (`model_validator(mode="after")`)
- Depends on frozen model implementation details

**Mitigation:** Dependency is documented and acceptable for incremental story, but reduces true independence.

---

### 3. **"Negotiable" (Severity: 2/10)**

**Minor Issue:** Implementation approach is highly prescriptive.

**Evidence:**
- Specific function signatures provided (lines 195-208)
- Exact YAML loading pattern prescribed (lines 166-190)
- Helper function naming pre-decided (`_load_yaml_file`)

**Assessment:** Acceptable for junior developer onboarding, but reduces negotiability. Senior developer might prefer different implementation patterns.

---

## Acceptance Criteria Issues

### AC1: **Incomplete Integration Test**

**Issue:** AC1 doesn't verify singleton population.

**Current AC1:**
```gherkin
Given a global config file exists at `~/.bmad-assist/config.yaml`
When `load_global_config()` is called
Then the file is read and parsed as YAML
And the parsed dict is validated against Pydantic models
And the Config instance is stored in the module-level singleton
```

**Problem:** "Stored in singleton" is stated but not testably verified. The AC doesn't include a "When get_config() is called / Then returns same instance" step.

**Fix:** AC6 partially covers this, but AC1 should be self-contained for the primary happy path.

---

### AC2: **Vague "Default Values" Verification**

**Issue:** AC2 lists expected defaults but doesn't specify HOW defaults are applied.

**Current AC2 (line 44):**
> "Then optional fields use default values from Story 1.2"

**Ambiguity:**
- Are defaults applied by Pydantic model defaults?
- Are defaults applied by loading a default dict?
- Are defaults applied by merging logic?

**Why It Matters:** Story 1.2 already handles defaults via Pydantic. This story should clarify if it's relying on Story 1.2's defaults or adding additional defaulting logic.

**Actual Answer (from code inspection):** Story 1.2's Pydantic models handle defaults, so this AC is redundant. But the AC doesn't make this clear.

---

### AC3: **Missing OSError Test Case**

**Issue:** AC3 only covers YAMLError, but code pattern (line 189) also handles OSError.

**Dev Notes Code (lines 186-189):**
```python
except yaml.YAMLError as e:
    raise ConfigError(f"Invalid YAML in {path}: {e}") from e
except OSError as e:
    raise ConfigError(f"Cannot read config file {path}: {e}") from e
```

**AC3 Current Scope:**
```gherkin
Given a global config file exists with invalid YAML syntax
When `load_global_config()` is called
Then ConfigError is raised
```

**Missing:** No AC for "file exists but is unreadable" (permissions, encoding issues, etc.)

**Impact:** Test coverage gap for OSError path.

---

### AC4: **Critical Contradiction with Test Cases**

**SHOWSTOPPER:** AC4 contradicts test case on line 450.

**AC4 (line 64):**
```gherkin
Given no global config file exists at `~/.bmad-assist/config.yaml`
When `load_global_config()` is called
Then default configuration is used (minimal valid config)
And info log indicates "No global config found, using defaults"
```

**Test Case (line 450-456):**
```python
def test_missing_file_raises_config_error(self, tmp_path: Path) -> None:
    """Missing config file raises ConfigError (if Option A chosen)."""
    nonexistent = tmp_path / "does_not_exist.yaml"
    with pytest.raises(ConfigError) as exc_info:
        load_global_config(path=nonexistent)
```

**Contradiction Analysis:**
- AC4 says "default configuration is used" (Option B)
- Test case says "raises ConfigError" (Option A)
- Comment "if Option A chosen" indicates indecision

**Root Cause:** The deferred decision (lines 141-162) creates this contradiction.

**Sprint-Killer Impact:** Developer cannot write tests without knowing which behavior is correct.

---

### AC5: **Testability Concern**

**Minor Issue:** AC5 tests path expansion, but this is already tested in Story 1.2.

**Redundancy Check:**
- Story 1.2 has path expansion via `model_validator` (line 292)
- Story 1.2 code review verified tilde expansion (line 315)

**Question:** Is AC5 testing Story 1.3's file loading preserves Story 1.2's expansion, or is it redundantly testing Story 1.2 behavior?

**Assessment:** AC5 is acceptable as an integration test, but rationale should be explicit.

---

### AC6: **Good - No Issues**

AC6 correctly tests singleton integration after file load. This is well-defined and testable.

---

## Hidden Risks & Dependencies

### Risk 1: **YAML Bomb / Malicious Config (Severity: 7/10)**

**Threat:** Story uses `yaml.safe_load()` (line 544) which is correct, but doesn't address resource exhaustion attacks.

**Scenario:**
```yaml
# Billion laughs attack
a: &a ["lol","lol","lol","lol","lol","lol","lol","lol","lol"]
b: &b [*a,*a,*a,*a,*a,*a,*a,*a,*a]
c: &c [*b,*b,*b,*b,*b,*b,*b,*b,*b]
# ... continues
```

**Mitigation Missing:**
- No file size check before loading
- No timeout on YAML parsing
- No memory limit

**Impact:** User-provided config file could DoS the tool.

**Fix:** Add max file size check (e.g., 1MB limit for config files).

---

### Risk 2: **Symlink Attack (Severity: 5/10)**

**Threat:** `~/.bmad-assist/config.yaml` could be a symlink to `/etc/passwd` or other sensitive file.

**Current Code (line 566):**
```python
content = path.read_text(encoding="utf-8")
```

**Mitigation Missing:** No check if path is a symlink or regular file.

**Impact:**
- Tool could read arbitrary files on system
- YAML parsing would fail, but file content might leak via error message

**Fix:** Add `path.is_file()` check or resolve symlinks explicitly.

---

### Risk 3: **Unicode Encoding Issues (Severity: 4/10)**

**Issue:** Story specifies `encoding="utf-8"` (line 182) but doesn't test non-ASCII content.

**Missing Test Case:**
```yaml
# Config with Polish characters
user_name: Paweł
project_name: bmad-助手
```

**Risk:** Encoding errors on Windows or systems with different locale settings.

**Mitigation:** Test case with non-ASCII YAML content should be added.

---

### Risk 4: **Story 1.4 Integration Assumption (Severity: 6/10)**

**Dependency Leak:** Story 1.3 makes assumptions about Story 1.4's merge logic.

**Evidence (lines 248-253):**
> "Story 1.4 will add project config by:
> 1. Loading global config via `load_global_config()`
> 2. Loading project config from `./bmad-assist.yaml`
> 3. Deep merging project over global"

**Problem:** Story 1.3's API design assumes Story 1.4 will exist. If Story 1.4 changes approach (e.g., uses overlay pattern instead of merge), Story 1.3 might need refactoring.

**Risk Mitigation:** Story 1.3's API should be merge-agnostic. Current design is acceptable but fragile.

---

### Risk 5: **Default Config Must Be Valid (Severity: 9/10 if Option B chosen)**

**Critical Issue:** If Option B (return default config) is chosen, the default must include a valid `providers.master`.

**Dev Notes (lines 154-158):**
```python
DEFAULT_CONFIG = {
    "providers": {
        "master": {"provider": "claude", "model": "opus_4_5"}
    }
}
```

**Problems:**
1. **Hardcoded provider:** What if user doesn't have Claude access?
2. **No API key:** Default config won't work without `.env` setup
3. **Model version drift:** "opus_4_5" might not exist when tool is used

**Impact:** If Option B is chosen, the tool will fail on first run despite "default config".

**Fix:** If Option B is chosen, default config should be a placeholder that forces user to create real config, defeating the purpose of a default.

**Conclusion:** This is strong evidence for choosing Option A (raise error) instead.

---

## Estimation Reality-Check

**Stated Estimate:** 2 story points

**Actual Complexity Analysis:**

### Work Items:
1. **Add YAML loading function** (Task 1) - 4 subtasks
2. **Implement `load_global_config()`** (Task 2) - 5 subtasks
3. **Handle default configuration** (Task 3) - 3 subtasks ← **BLOCKED by undecided approach**
4. **Update module exports** (Task 4) - 2 subtasks
5. **Write comprehensive tests** (Task 5) - 8 subtasks

**Total Subtasks:** 22

**Complexity Factors:**
- ✅ **Low Complexity:** YAML loading is straightforward
- ✅ **Low Complexity:** Path expansion already handled by Story 1.2
- ✅ **Low Complexity:** Singleton integration already tested
- ⚠️ **Medium Complexity:** Error handling for multiple failure modes (YAML, OSError, validation)
- ❌ **High Complexity:** Architectural decision deferred to implementation

**Adjusted Estimate:** **3 story points** (if decision is made upfront)

**Rationale for +1 point:**
- 8 new test cases (lines 378-522) is substantial for a "2 point" story
- Security considerations (symlinks, encoding, file size) not addressed in estimate
- Integration testing with Story 1.2's existing tests requires careful fixture management

**If decision remains deferred:** **4-5 story points** due to mid-sprint interruption.

---

## Technical Alignment

### ✅ **Architecture.md Compliance - Excellent**

**Verified Alignments:**

1. **Module Location (line 130):** `src/bmad_assist/core/config.py` ✅
2. **Exception Handling (line 132):** Uses `ConfigError` from `core/exceptions.py` ✅
3. **Config Access (line 133):** Singleton via `get_config()` ✅
4. **Naming (line 134):** PEP8 snake_case ✅
5. **Type Hints (line 135):** Required on all functions ✅
6. **Docstrings (line 136):** Google-style ✅
7. **Logging Pattern (line 280):** `logger = logging.getLogger(__name__)` ✅
8. **Test Organization (line 356):** `tests/core/test_config.py` ✅

### ✅ **Technology Stack (architecture.md lines 126-135)**

| Technology | Architecture Requirement | Story Implementation | Status |
|------------|--------------------------|----------------------|--------|
| PyYAML | Already in pyproject.toml | Used via `yaml.safe_load()` | ✅ |
| Pydantic v2 | Story 1.2's validation | Reused via `load_config(dict)` | ✅ |
| pathlib.Path | File operations | `Path.home() / ".bmad-assist"` | ✅ |
| Python 3.11+ | Type hints required | Union syntax `str \| Path \| None` | ✅ |

### ⚠️ **Minor Deviation: Logging**

**Architecture Requirement (line 152):**
> "rich logging for consistent pretty output"

**Story Implementation (line 66):**
> "And info log indicates 'No global config found, using defaults'"

**Issue:** Story doesn't explicitly import `rich.logging.RichHandler` in code examples.

**Severity:** Low - This is a trivial fix during implementation.

---

### ✅ **Security Alignment (NFR8, NFR9)**

**Architecture Requirements:**
- NFR8: Credential isolation (chmod 600)
- NFR9: No credentials in logs

**Story Compliance:**
- Story only handles config files (behavioral settings)
- Credentials remain in `.env` (handled by CLI tools, not bmad-assist)
- No API keys in YAML config examples ✅

---

### ✅ **Data Architecture Alignment**

**Architecture.md (line 161):**
> "Global: `~/.bmad-assist/config.yaml`"

**Story Implementation (line 97):**
```python
GLOBAL_CONFIG_PATH = Path.home() / ".bmad-assist" / "config.yaml"
```

**Perfect alignment.** ✅

---

## Final Score

### Scoring Breakdown

| Criteria | Weight | Score | Weighted |
|----------|--------|-------|----------|
| INVEST Compliance | 25% | 6/10 | 1.5 |
| Acceptance Criteria Quality | 30% | 5/10 | 1.5 |
| Risk Management | 20% | 6/10 | 1.2 |
| Estimation Accuracy | 10% | 7/10 | 0.7 |
| Technical Alignment | 15% | 9/10 | 1.35 |

**Total Weighted Score:** **6.25/10**

---

## Verdict: MAJOR REWORK

### Critical Blockers (Must Fix Before Implementation)

1. **[SHOWSTOPPER] Decide default behavior** (Option A vs Option B)
   - Update AC4 to reflect chosen approach
   - Align test cases with decision (lines 450-465)
   - Remove "ask user during implementation" instruction (line 162)
   - **Recommendation:** Choose Option A (raise ConfigError) for reasons outlined in Risk 5

2. **[HIGH] Fix AC4/test contradiction**
   - AC4 says "return default"
   - Test case says "raise error"
   - These cannot both be correct

3. **[MEDIUM] Add missing test cases**
   - OSError handling (file permissions, encoding errors)
   - File size limit (YAML bomb protection)
   - Non-ASCII content (Unicode handling)
   - Symlink behavior (security)

---

### Recommended Changes Before Marking ready-for-dev

#### Change 1: Add Security Requirements Section

```markdown
## Security Requirements

### File Validation
- Max config file size: 1MB
- Must be regular file (not symlink, unless explicitly followed)
- UTF-8 encoding required

### Test Cases
- AC7: Config file >1MB raises ConfigError
- AC8: Config with non-ASCII content loads correctly
```

#### Change 2: Resolve Default Behavior (Recommendation: Option A)

**Replace lines 141-162 with:**

```markdown
### Default Behavior: Raise Error

When no global config file exists, `load_global_config()` raises ConfigError.

**Rationale:**
1. Aligns with Story 1.7 (interactive config generation)
2. Prevents silent failures with invalid default credentials
3. Clear error message guides user to `bmad-assist init`

**Implementation:**
```python
def load_global_config(path: Path | None = None) -> Config:
    config_path = path or GLOBAL_CONFIG_PATH
    if not config_path.exists():
        raise ConfigError(
            f"Global config not found at {config_path}.\n"
            f"Run 'bmad-assist init' to create one."
        )
    # ... load and return config
```
```

#### Change 3: Update AC4

**Replace AC4 (lines 62-68) with:**

```gherkin
### AC4: ConfigError When File Missing
Given no global config file exists at `~/.bmad-assist/config.yaml`
When `load_global_config()` is called
Then ConfigError is raised
And error message includes file path
And error message suggests running 'bmad-assist init'
```

#### Change 4: Update Test Case

**Replace lines 450-465 with:**

```python
class TestMissingConfigFile:
    """Tests for AC4: ConfigError when file missing."""

    def test_missing_file_raises_config_error(self, tmp_path: Path) -> None:
        """Missing config file raises ConfigError with helpful message."""
        nonexistent = tmp_path / "does_not_exist.yaml"

        with pytest.raises(ConfigError) as exc_info:
            load_global_config(path=nonexistent)

        error_msg = str(exc_info.value).lower()
        assert "not found" in error_msg or "does not exist" in error_msg
        assert "does_not_exist.yaml" in str(exc_info.value)
        assert "init" in error_msg  # Suggests bmad-assist init
```

---

### Why Not "REJECT"?

Despite critical issues, the story has strong foundations:
- ✅ Excellent architecture alignment
- ✅ Comprehensive dev notes
- ✅ Clear task breakdown
- ✅ Strong integration with Story 1.2

**The story is 80% ready.** With the 4 critical changes above, it would be **READY**.

---

### Recommendation for Scrum Master

**Action:** Return story to Product Owner with specific rework requests.

**Timeline Impact:** +1 hour to make changes, then re-validate.

**Alternative:** If PO approves Option A verbally now, developer can proceed with that assumption and story can stay in sprint.

---

**Validation Complete.**
**Report saved to:** `docs/sprint-artifacts/story-validation-1-3-sonnet-4-5-20251209-191330.md`
