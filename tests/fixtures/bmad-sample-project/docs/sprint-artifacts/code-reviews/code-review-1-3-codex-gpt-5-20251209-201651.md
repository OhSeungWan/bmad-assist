### Code Review 1.3

### Architectural Sins
- src/bmad_assist/core/config.py:249-272 – load_global_config leaves the previous singleton intact when validation fails; after a failed load, get_config() still returns the stale config, breaking the singleton contract and masking bad configs.

### Pythonic Crimes & Readability
- src/bmad_assist/core/config.py:249 – Signature declares path: Path | None, but the docstring and usage imply string paths are supported; type hint is wrong per project standards and the Story 1.3 design note (str | Path | None).

### Performance & Scalability
- Brak istotnych uwag wydajnościowych w tej zmianie.

### Correctness & Safety
- src/bmad_assist/core/config.py:252 – Passing a tilde-containing string (e.g., "~/.bmad-assist/config.yaml") fails because Path(path) is not expanded; user-friendly default should expand ~ to meet AC usability expectations.
- tests/core/test_config.py:789-801 (“file at exactly 1MB”) never creates a ~1MB file, so it can’t catch off-by-one errors in size enforcement (lying test for AC10).

### Maintainability Issues
- Git vs story File List mismatch: sprint-status.yaml, power-prompts/*, AGENTS.md are modified but not listed in the story’s File List → documentation gap.

### Suggested Fixes
- Reset _config to None before/when wrapping ValidationError in load_global_config; ensure failed loads cannot leave stale configs reachable via get_config().
- Update load_global_config signature and annotations to path: str | Path | None, and expand user paths (expanduser()) before existence checks.
- Fix AC10 boundary test to actually write ~1_048_576-byte valid YAML and assert behavior; add a complementary “just under limit” case.
- Update the story File List to include all touched files (e.g., docs/sprint-artifacts/sprint-status.yaml, power-prompts/python-cli/code-review-*, AGENTS.md).

### Final Score (1-10)
5

### Verdict: REJECT
