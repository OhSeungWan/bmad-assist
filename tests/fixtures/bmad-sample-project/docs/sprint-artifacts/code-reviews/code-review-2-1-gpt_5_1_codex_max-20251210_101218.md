### Code Review 2.1

### Architectural Sins
- MEDIUM – `BmadDocument` is implemented as a plain dataclass (`src/bmad_assist/bmad/parser.py:16-29`), but project standards call for Pydantic models for data structures (docs/project-context.md). That bypasses built-in validation and consistency rules expected elsewhere in the codebase.

### Pythonic Crimes & Readability
- None observed beyond the architectural mismatch above; naming and docstrings align with PEP 8/Google style.

### Performance & Scalability
- No performance risks identified in this small parsing helper; work is I/O bound on a single file.

### Correctness & Safety
- HIGH – `dict(post.metadata)` is executed without validating that the parsed frontmatter is a mapping (`parser.py:67`). Valid YAML can legally produce a list or scalar frontmatter; in that case this line raises a raw `TypeError` instead of the documented `ParserError`, breaking the AC3 contract and leaking unexpected exceptions to callers.
- MEDIUM – The catch-all `except Exception` wraps every failure (including `PermissionError`/`IsADirectoryError`) into `ParserError` (`parser.py:59-64`), collapsing important OS errors into a generic parse failure and making troubleshooting harder. Only YAML/frontmatter parsing failures should be wrapped; filesystem errors should propagate like `FileNotFoundError` does.

### Maintainability Issues
- MEDIUM – Git reality diverges from the story’s File List: untracked files `bmad-backup.tar.gz`, `docs/sprint-artifacts/code-reviews/code-review-2-1-grok_4_1_fast_reasoning-20251210_130500.md`, and `docs/sprint-artifacts/code-reviews/code-review-2-1-sonnet_4_5-20251210_113000.md` exist but are not documented in the story, leaving review/backup artifacts unmanaged and undocumented.

### Suggested Fixes
- Validate frontmatter type before casting: if `post.metadata` is not a `Mapping`, raise `ParserError(f"Invalid frontmatter in {path}: expected mapping, got {type(post.metadata).__name__}")` so non-mapping YAML surfaces as a controlled parse error.
- Narrow exception handling to YAML/frontmatter parsing errors (`yaml.YAMLError`, `frontmatter.FrontmatterError`) and let other I/O errors propagate just like `FileNotFoundError` to preserve accurate failure modes.
- Replace `BmadDocument` with a small Pydantic model (or at minimum add validation hooks) to align with the project’s “Pydantic for data structures” rule and gain automatic type enforcement.
- Document or remove the untracked backup/review artifacts so the story’s file list matches git reality.

### Final Score (1-10)
4

### Verdict: MAJOR REWORK
