### Code Review 2.3

#### Architectural Sins
- **Boundary Breach:** `_load_sprint_status` hardcodes paths (`sprint-artifacts/sprint-status.yaml`), violates architecture.md's config-driven paths. Should use `get_config().sprint_artifacts` singleton. src/bmad_assist/bmad/reconciler.py:216
- **SOLID Violation (SRP):** `read_project_state` orchestrates discovery/parsing/status/position - 100+ lines, mixes concerns. Split into composable funcs per AC. src/bmad_assist/bmad/reconciler.py:294
- **Dependency Inversion Missing:** Ties to `yaml.safe_load` directly; inject loader for testability/mocking.

#### Pythonic Crimes & Readability
- **Broad Except:** `except Exception as e` in epic parsing swallows IOErrors, ValueErrors - only catch `ParserError`. Violates \"catch specific exceptions\". src/bmad_assist/bmad/reconciler.py:50
- **Magic Strings:** \"retrospective\", \"done\" hardcoded repeatedly - define STATUS_DONE = \"done\", RETRO_KEYWORDS = [\"retrospective\"]. src/bmad_assist/bmad/reconciler.py:59,73
- **Mutable Dataclass:** ProjectState lists mutable post-init; use `frozen=True` or field(default_factory=list) for immutability. src/bmad_assist/bmad/reconciler.py:21

#### Performance & Scalability
- **No Glob Limits:** `glob(\"*epic*.md\")` scans entire dir - vulnerable to 10k+ files DoS. Add `max_files=50` param, raise if exceeded.
- **O(n^2) Potential:** `_flatten_stories` uses set for dedupe but iterates all; fine now (&lt;100 stories) but scales poorly.
- **YAML No Limits:** `yaml.safe_load` no size limit - huge file DoS. Add `MAX_YAML_SIZE=1MB` check.

#### Correctness & Safety
- **Unicode Status Normalize:** `.lower().strip()` assumes ASCII statuses; fails on \"DoNé\" (accent). Use `status.lower().strip()` with unicode normalization.
- **Sprint Key Parse Fragile:** `_parse_sprint_status_key` assumes \"X-Y-slug\", fails on \"2-10-long-story\" (parts[1]=\"10\" ok, but slug with \"-\" breaks). Use regex `r'^(\\d+)-(\\d+).*'`.
- **No Invariant Checks:** AC15 invariants asserted in tests only - add `@dataclass(frozen=True)` or post_init validator.

#### Maintainability Issues
- **Test Brittleness:** `test_parse_real_docs_folder` skips if no docs/ - integration test should fixture real data or mock.
- **No Metrics Logging:** No timing/logs for parse duration, epic count - hard to debug prod issues.
- **Undocumented Defaults:** `use_sprint_status=False` buried in docstring - expose as config.

#### Suggested Fixes
For reconciler.py:295-350 (main func &lt;350 lines):
```diff
def read_project_state(
     bmad_path: str | Path,
-    use_sprint_status: bool = False,
+    use_sprint_status: bool = get_config().use_sprint_status,  # Config-driven
 ) -&gt; ProjectState:
+    MAX_EPICS = get_config().max_epics or 50
     epic_files = _discover_epic_files(bmad_path)
+    if len(epic_files) &gt; MAX_EPICS:
+        raise ValueError(f&quot;Too many epic files: {len(epic_files)} &gt; {MAX_EPICS}&quot;)
 
     epics: list[EpicDocument] = []
     for epic_file in epic_files:
-        try:
-            epic_doc = parse_epic_file(epic_file)
+        try:
+            epic_doc = parse_epic_file(epic_file)  # Specific ParserError only
             epics.append(epic_doc)
         except ParserError as e:  # Narrow catch
             logger.warning(&quot;Failed to parse epic file %s: %s&quot;, epic_file, e)
+        except OSError as e:
+            logger.error(&quot;IO error on epic file %s: %s&quot;, epic_file, e)
             continue
```

#### Final Score (1-10)
7

#### Verdict: MAJOR REWORK