### Code Review 2.3

### Architectural Sins
- **Architectural Misalignment: Mutable `ProjectState` (Medium)**
  - The `ProjectState` dataclass is intended to represent "immutable semantics" as described in the story's "Dev Notes", yet it is not declared as `frozen=True`. This allows for accidental mutation of the project state after creation, which directly contradicts the design intent and can introduce subtle bugs. Immutable data structures are crucial for state management in complex systems to ensure predictability and facilitate debugging.
  - **Location:** `src/bmad_assist/bmad/reconciler.py`, line 21 (`@dataclass class ProjectState:`)

### Pythonic Crimes & Readability
- **Redundant Status Normalization (Low)**
  - The `_normalize_status` function is called multiple times (`completed_stories` list comprehension, `_determine_current_position`). While functional, it indicates that story statuses are not consistently normalized at their point of ingestion or within the `EpicStory` object itself. This adds minor overhead and verbosity. It would be cleaner to normalize status once, perhaps within the `EpicStory` parser or as a property of `EpicStory`.
  - **Location:** `src/bmad_assist/bmad/reconciler.py`, lines 219, 222
- **Ambiguous `EpicStory` Mutability (Low)**
  - Helper functions like `_apply_default_status` and `_apply_sprint_statuses` create *new* `EpicStory` instances when modifying status. If `EpicStory` is intended to be immutable, then `ProjectState` should be `frozen=True` and this approach is correct. However, if `EpicStory` is mutable (which `dataclass` is by default), directly updating the `status` attribute would be more efficient and less verbose. This inconsistency suggests a lack of explicit design decision regarding object mutability.
  - **Location:** `src/bmad_assist/bmad/reconciler.py`, lines 102, 179
- **Broad Glob Pattern in `_discover_epic_files` (Low)**
  - The `*epic*.md` glob pattern is overly permissive, requiring a subsequent filter for "retrospective". While the filter works, a more precise initial globbing (e.g., `epic-*.md` and `epics.md`) would reduce the number of files processed and improve clarity.
  - **Location:** `src/bmad_assist/bmad/reconciler.py`, line 58
- **Missing Type Hint for `yaml.safe_load` Result (Low)**
  - In `_load_sprint_status`, the result of `yaml.safe_load(f)` is assigned to `data` without an explicit type hint. While the subsequent `isinstance(dev_status, dict)` check is good, a more precise type annotation for `data` would improve static analysis and readability.
  - **Location:** `src/bmad_assist/bmad/reconciler.py`, line 147

### Performance & Scalability
- **Minor Iteration Overheads (Low)**
  - The `read_project_state` function performs several sequential iterations and list comprehensions over `all_stories` (e.g., for default status, sprint status, completed stories, current position). For a project with thousands of stories, these repeated passes, especially when creating new `EpicStory` objects in some helpers, could introduce minor inefficiencies. A single pass to process and normalize all story attributes might be slightly more performant for very large datasets, though likely negligible for typical BMAD project sizes.

### Correctness & Safety
- **Implicit Invariant Enforcement (High)**
  - AC15 mandates that "If current_epic is None, then current_story MUST be None" and "If current_story is not None, then current_epic MUST match story's epic." The code comment in `read_project_state` states, "These invariants are naturally satisfied by _determine_current_position." Relying on "natural satisfaction" is a critical safety hazard. Invariants should be explicitly asserted, ideally via Pydantic validators on `ProjectState` or an `__post_init__` method, to guarantee their enforcement regardless of future code changes in helper functions. Without explicit enforcement, these invariants are fragile.
  - **Location:** `src/bmad_assist/bmad/reconciler.py`, line 231
- **Silent Skip of Malformed Sprint Status Entries (Low)**
  - In `_load_sprint_status`, when iterating through `dev_status.items()`, if a `status` value is not a string (`isinstance(status, str)`), it is silently skipped. While this prevents errors, a warning log would be beneficial to alert the user or developer about malformed entries in `sprint-status.yaml` that are being ignored.
  - **Location:** `src/bmad_assist/bmad/reconciler.py`, line 161

### Maintainability Issues
- **God Function `read_project_state` (Medium)**
  - The `read_project_state` function, while using helper functions, acts as a central orchestrator for many distinct responsibilities. It is quite long (over 50 lines of code) and could benefit from further decomposition. Refactoring it into a class with well-defined methods for each logical step (e.g., `_load_epics`, `_process_stories`, `_determine_position`) would enhance readability, testability, and maintainability.
  - **Location:** `src/bmad_assist/bmad/reconciler.py`, lines 196-239
- **Magic Strings for Story Statuses (Low)**
  - Story statuses like "done", "review", "backlog" are used as magic strings throughout the codebase. Introducing an `Enum` (e.g., `StoryStatus(Enum)`) would improve type safety, reduce the likelihood of typos, and make status comparisons more robust and readable. This is a best practice for managing a fixed set of string values.
  - **Location:** Multiple occurrences in `src/bmad_assist/bmad/reconciler.py` and `tests/bmad/test_reconciler.py`
- **Documentation Discrepancy: Git vs. Story File List (Medium)**
  - The `Dev Agent Record -> File List` in the story lists files created/modified (`reconciler.py`, `test_reconciler.py`, `__init__.py`, `sprint-status.yaml`, `2-3-project-state-reader.md`). However, the current `git status` shows no uncommitted changes for `reconciler.py`, `test_reconciler.py`, `__init__.py`. Conversely, `git status` reveals changes to `docs/prd-pl.md` and `power-prompts/python-cli/code-review-multi.md` that are *not* documented in the story's file list. This significant discrepancy indicates that the story's documentation for "Files modified" does not accurately reflect the current working tree, or that uncommitted changes unrelated to the story are present. This impacts the transparency and accuracy of the story record and implies poor discipline in updating the `File List` at the time of the review request. This also makes it harder for a reviewer to trust the provided `File List` as the authoritative source for the changes under review.

### Suggested Fixes
```diff
--- a/src/bmad_assist/bmad/reconciler.py
+++ b/src/bmad_assist/bmad/reconciler.py
@@ -20,7 +20,7 @@
 
 
 @dataclass
-class ProjectState:
+class ProjectState(frozen=True): # Enforce immutability
     """Complete project state from BMAD files.
 
     Attributes:
@@ -40,6 +40,17 @@
     current_story: str | None
     bmad_path: str
 
+    def __post_init__(self) -> None:
+        """Enforce ProjectState field invariants (AC15)."""
+        if self.current_epic is None and self.current_story is not None:
+            raise ValueError("current_story cannot be set if current_epic is None.")
+        if self.current_epic is not None and self.current_story is None:
+            # This scenario is valid if there's an epic with non-done stories,
+            # but no specific story can be identified as "current" (e.g., empty epic)
+            pass
+        # More comprehensive checks could be added here, e.g., if current_story's epic matches current_epic
+
+
 
 def _discover_epic_files(bmad_path: Path) -> list[Path]:
     """Discover epic files in BMAD directory.
@@ -57,7 +68,7 @@
     epic_files = list(bmad_path.glob("*epic*.md"))
 
     # Filter out retrospectives and other non-epic files
-    epic_files = [f for f in epic_files if "retrospective" not in f.name.lower() and f.is_file()]
+    epic_files = [f for f in epic_files if "retrospective" not in f.name.lower() and f.stem != "epics" and f.is_file()]
 
     return sorted(epic_files)
 
@@ -107,6 +118,17 @@
     return status.lower().strip()
 
 
+# Add an Enum for consistent story statuses
+from enum import Enum
+
+class StoryStatus(str, Enum):
+    DONE = "done"
+    REVIEW = "review"
+    IN_PROGRESS = "in-progress"
+    READY_FOR_DEV = "ready-for-dev"
+    DRAFTED = "drafted"
+    BACKLOG = "backlog"
+
 def _apply_default_status(stories: list[EpicStory]) -> list[EpicStory]:
     """Apply default 'backlog' status to stories without explicit status.
 
@@ -124,7 +146,7 @@
                     number=story.number,
                     title=story.title,
                     estimate=story.estimate,
-                    status="backlog",
+                    status=StoryStatus.BACKLOG.value, # Use Enum
                     dependencies=story.dependencies,
                     completed_criteria=story.completed_criteria,
                     total_criteria=story.total_criteria,
@@ -148,7 +170,7 @@
 
     """
     for story in stories:
-        status = _normalize_status(story.status)
+        status = StoryStatus(_normalize_status(story.status)) # Ensure consistent Enum conversion
         if status != "done":
             epic_num = int(story.number.split(".")[0])
             return (epic_num, story.number)
@@ -210,6 +232,7 @@
                 for key, status in dev_status.items():
                     story_num = _parse_sprint_status_key(key)
                     if story_num is not None and isinstance(status, str):
+                        # Consider normalizing status here as well
                         result[story_num] = status
 
                 return result
@@ -242,7 +265,7 @@
                     number=story.number,
                     title=story.title,
                     estimate=story.estimate,
-                    status=sprint_statuses[story.number],
+                    status=StoryStatus(_normalize_status(sprint_statuses[story.number])).value, # Normalize and use Enum
                     dependencies=story.dependencies,
                     completed_criteria=story.completed_criteria,
                     total_criteria=story.total_criteria,
@@ -310,10 +333,7 @@
         sprint_statuses = _load_sprint_status(bmad_path)
         if sprint_statuses:
             all_stories = _apply_sprint_statuses(all_stories, sprint_statuses)
-
-    # Step 6: Compile completed stories (AC3)
-    completed_stories = [s.number for s in all_stories if _normalize_status(s.status) == "done"]
-
-    # Step 7: Determine current position (AC4, AC5)
-    current_epic, current_story = _determine_current_position(all_stories)
-
-    # AC15: Enforce field invariants
-    # If current_epic is None, current_story must be None
-    # If current_story is set, current_epic must match
-    # These invariants are naturally satisfied by _determine_current_position
-
-    return ProjectState(
-        epics=epics,
-        all_stories=all_stories,
-        completed_stories=completed_stories,
-        current_epic=current_epic,
-        current_story=current_story,
-        bmad_path=str(bmad_path),
-    )
+    
+    # Step 6: Determine current position (AC4, AC5) and compile completed stories (AC3) in a single pass
+    completed_stories: list[str] = []
+    current_epic: int | None = None
+    current_story: str | None = None
+
+    for story in all_stories:
+        normalized_status = StoryStatus(_normalize_status(story.status))
+        if normalized_status == StoryStatus.DONE:
+            completed_stories.append(story.number)
+        elif current_epic is None: # Found first non-done story
+            current_epic = int(story.number.split(".")[0])
+            current_story = story.number
+
+    return ProjectState(epics=epics, all_stories=all_stories, completed_stories=completed_stories, current_epic=current_epic, current_story=current_story, bmad_path=str(bmad_path))
```

```diff
--- a/tests/bmad/test_reconciler.py
+++ b/tests/bmad/test_reconciler.py
@@ -10,7 +10,7 @@
 from pathlib import Path
 
 import pytest
-
+from enum import Enum
 from bmad_assist.bmad.reconciler import (
     ProjectState,
     _apply_default_status,
@@ -194,7 +194,7 @@
 
         result = read_project_state(tmp_path)
 
-        assert result.current_epic is None
+        assert result.current_epic is None # Test AC15: current_epic None implies current_story None
 
 
 class TestCurrentStoryDetermination:
@@ -624,6 +624,19 @@
         assert epic is None
         assert story is None
 
+    def test_determine_current_position_with_enum_statuses(self) -> None:
+        """Test _determine_current_position works with Enum statuses."""
+        stories = [
+            EpicStory(number="1.1", title="A", status=StoryStatus.DONE.value),
+            EpicStory(number="1.2", title="B", status=StoryStatus.IN_PROGRESS.value),
+        ]
+
+        epic, story = _determine_current_position(stories)
+
+        assert epic == 1
+        assert story == "1.2"
+
+
 class TestPathHandling:
     """Test path handling edge cases."""
 
@@ -737,3 +750,17 @@
 
         numbers = [s.number for s in result.all_stories]
         assert numbers == ["1.1", "1.2", "2.1", "2.2"]
+
+# Added to test the new enum
+class StoryStatus(str, Enum):
+    DONE = "done"
+    REVIEW = "review"
+    IN_PROGRESS = "in-progress"
+    READY_FOR_DEV = "ready-for-dev"
+    DRAFTED = "drafted"
+    BACKLOG = "backlog"
+
+    def test_projectstate_raises_error_on_invalid_invariant(self) -> None:
+        """Test ProjectState __post_init__ raises ValueError for invalid invariants."""
+        with pytest.raises(ValueError, match="current_story cannot be set if current_epic is None"):
+            ProjectState(epics=[], all_stories=[], completed_stories=[], current_epic=None, current_story="1.1", bmad_path="/tmp")
```