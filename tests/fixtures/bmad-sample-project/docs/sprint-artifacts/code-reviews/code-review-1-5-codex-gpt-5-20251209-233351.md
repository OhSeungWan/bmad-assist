# Code Review – Story 1.5: Credentials Security with .env

**Reviewer:** codex-gpt-5  
**Status:** Fail (issues remain)  
**Story file:** docs/sprint-artifacts/1-5-credentials-security-with-env.md  
**Git vs Story Discrepancies:** 1 (changed file not listed in story)  
**Issues Found:** 1 High, 2 Medium, 0 Low

## Git vs Story Discrepancies
- Changed but not listed in story File List: `power-prompts/python-cli/dev-story.md` (story has no File List).

## Findings
- **HIGH** – Credential masking not applied: helper `_mask_credential` exists but no logging path uses it, so secrets would be logged if values reach logs (`src/bmad_assist/core/config.py`:535-559). Violates AC7/NFR9.
- **MEDIUM** – load_env_file signals success without verifying load: returns `True` whenever `.env` exists, even if `load_dotenv` fails or loads nothing. Broken/empty file would be reported as loaded (`src/bmad_assist/core/config.py`:618-633). Weakens AC1/AC4.
- **MEDIUM** – Tests missing for .env example and gitignore coverage: `tests/core/test_config.py` has no assertions that `.env.example` exists with required keys or that `.env` is ignored by git (Tasks 9.5/9.6, AC5/AC6).

## Acceptance Criteria Coverage (sampled)
- AC1/AC4/AC11: load_env_file basic behaviors covered by tests, but success signal gap noted (see Medium finding).
- AC5/AC6: Not fully covered—no automated tests for `.env.example` presence/content or `.env` in `.gitignore`.
- AC7: Masking helper present but unused (High finding).

## Recommendations
1. Wire masking into logging paths that could include credentials (e.g., sanitize values before logging, or add log filter).
2. Have `load_env_file` return the actual result of `load_dotenv` (or False on failure) and optionally log when zero keys are loaded.
3. Add tests for `.env.example` required keys and `.env` ignore rule to `tests/core/test_config.py`.

## Testing
- Not run (per instructions).
