"""Tests for ContextBuilder module.

Tests cover:
- AC1: Module structure and API (fluent builder, method chaining)
- AC2: Error handling and graceful degradation (recency-bias ordering, optional/required files)
- Integration with CompilerContext
"""

import logging
from pathlib import Path

import pytest

from bmad_assist.compiler.context import (
    PRIORITY_BACKGROUND,
    PRIORITY_EPIC,
    PRIORITY_PLANNING,
    PRIORITY_STORIES,
    PRIORITY_VALIDATIONS,
    ContextBuilder,
)
from bmad_assist.compiler.types import CompilerContext
from bmad_assist.core.exceptions import ContextError


class TestContextBuilderFluentAPI:
    """Test AC1: Fluent API pattern (method chaining)."""

    def test_each_method_returns_self(self, tmp_path: Path) -> None:
        """Each add_* method returns self for chaining."""
        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
            resolved_variables={"epic_num": 1, "story_num": 1},
        )
        builder = ContextBuilder(context)

        # Each method should return the builder instance
        result = builder.add_project_context(required=False)
        assert result is builder

        result = builder.add_planning_docs(required=False)
        assert result is builder

        result = builder.add_previous_stories(count=3)
        assert result is builder

        result = builder.add_epic_files(epic_num=1)
        assert result is builder

        result = builder.add_validations(story_key="1-1-test")
        assert result is builder

    def test_chaining_works(self, tmp_path: Path) -> None:
        """Methods can be chained in a single expression."""
        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
            resolved_variables={"epic_num": 1, "story_num": 1},
        )

        # Should not raise - all optional
        result = (
            ContextBuilder(context)
            .add_project_context(required=False)
            .add_planning_docs(required=False)
            .add_previous_stories(count=3)
            .add_epic_files(epic_num=1)
            .build()
        )

        assert isinstance(result, dict)

    def test_empty_builder_returns_empty_dict(self, tmp_path: Path) -> None:
        """Empty builder returns empty dict without error."""
        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )
        builder = ContextBuilder(context)

        result = builder.build()

        assert result == {}
        assert isinstance(result, dict)


class TestContextBuilderRecencyBiasOrdering:
    """Test AC2: Recency-bias ordering with priority constants."""

    def test_priority_constants_defined(self) -> None:
        """Priority constants are defined with correct values."""
        assert PRIORITY_BACKGROUND == 10
        assert PRIORITY_PLANNING == 20
        assert PRIORITY_STORIES == 30
        assert PRIORITY_VALIDATIONS == 40
        assert PRIORITY_EPIC == 50

    def test_priority_ordering_preserved(self, tmp_path: Path) -> None:
        """Files are ordered by priority (background first, epic last)."""
        # Create files in different categories
        # Note: get_stories_dir() falls back to output_folder/sprint-artifacts
        # Note: planning docs go in planning-artifacts/ subdirectory
        (tmp_path / "project_context.md").write_text("# Context")
        planning_dir = tmp_path / "planning-artifacts"
        planning_dir.mkdir()
        (planning_dir / "prd.md").write_text("# PRD")
        (tmp_path / "sprint-artifacts").mkdir()
        (tmp_path / "sprint-artifacts" / "1-1-first.md").write_text("# Story 1")
        (tmp_path / "epics").mkdir()
        (tmp_path / "epics" / "epic-1-main.md").write_text("# Epic 1")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
            resolved_variables={"epic_num": 1, "story_num": 2},
        )

        result = (
            ContextBuilder(context)
            .add_project_context()
            .add_planning_docs(prd=True, architecture=False, ux=False)
            .add_previous_stories(count=3)
            .add_epic_files(epic_num=1)
            .build()
        )

        # Get the keys in order
        keys = list(result.keys())

        # Verify order: project_context -> prd -> stories -> epic
        assert len(keys) == 4
        assert "project_context.md" in keys[0]
        assert "prd.md" in keys[1]
        assert "1-1-first.md" in keys[2]
        assert "epic-1-main.md" in keys[3]

    def test_stories_chronological_order(self, tmp_path: Path) -> None:
        """Previous stories are added in chronological order (oldest first)."""
        # Create stories directory and files (uses sprint-artifacts fallback)
        stories_dir = tmp_path / "sprint-artifacts"
        stories_dir.mkdir()
        (stories_dir / "5-1-first.md").write_text("# Story 5.1")
        (stories_dir / "5-2-second.md").write_text("# Story 5.2")
        (stories_dir / "5-3-third.md").write_text("# Story 5.3")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
            resolved_variables={"epic_num": 5, "story_num": 4},
        )

        result = ContextBuilder(context).add_previous_stories(count=3).build()

        keys = list(result.keys())
        # Should be oldest first: 5.1, 5.2, 5.3
        assert len(keys) == 3
        assert "5-1-first.md" in keys[0]
        assert "5-2-second.md" in keys[1]
        assert "5-3-third.md" in keys[2]


class TestContextBuilderErrorHandling:
    """Test AC2: Error handling and graceful degradation."""

    def test_missing_required_project_context_raises(self, tmp_path: Path) -> None:
        """Missing required project_context.md raises ContextError."""
        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )
        builder = ContextBuilder(context)

        with pytest.raises(ContextError) as exc_info:
            builder.add_project_context(required=True)

        assert "project_context.md" in str(exc_info.value)
        assert "Required context file" in str(exc_info.value)

    def test_missing_optional_project_context_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Missing optional project_context.md logs warning, doesn't raise."""
        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )
        builder = ContextBuilder(context)

        with caplog.at_level(logging.WARNING):
            result = builder.add_project_context(required=False).build()

        assert result == {}
        assert "project_context.md not found" in caplog.text

    def test_missing_required_planning_doc_raises(self, tmp_path: Path) -> None:
        """Missing required planning doc raises ContextError."""
        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )
        builder = ContextBuilder(context)

        with pytest.raises(ContextError) as exc_info:
            builder.add_planning_docs(prd=True, required=True)

        assert "prd" in str(exc_info.value).lower()

    def test_missing_optional_planning_doc_continues(self, tmp_path: Path) -> None:
        """Missing optional planning docs don't raise, just skip."""
        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = (
            ContextBuilder(context)
            .add_planning_docs(prd=True, architecture=True, ux=True, required=False)
            .build()
        )

        assert result == {}

    def test_context_error_inherits_from_compiler_error(self) -> None:
        """ContextError inherits from CompilerError."""
        from bmad_assist.core.exceptions import CompilerError

        assert issubclass(ContextError, CompilerError)


class TestContextBuilderDuplicates:
    """Test idempotency and duplicate handling."""

    def test_duplicate_calls_are_idempotent(self, tmp_path: Path) -> None:
        """Calling same add method multiple times doesn't add duplicates."""
        (tmp_path / "project_context.md").write_text("# Context")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = (
            ContextBuilder(context)
            .add_project_context()
            .add_project_context()  # Duplicate call
            .add_project_context()  # Another duplicate
            .build()
        )

        # Should only have one entry
        assert len(result) == 1


class TestContextBuilderAddProjectContext:
    """Test add_project_context() method."""

    def test_loads_project_context_from_output_folder(self, tmp_path: Path) -> None:
        """Finds project_context.md in output_folder."""
        (tmp_path / "project_context.md").write_text("# Project Context\nRules here")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = ContextBuilder(context).add_project_context().build()

        assert len(result) == 1
        assert "# Project Context" in list(result.values())[0]

    def test_supports_project_dash_context_naming(self, tmp_path: Path) -> None:
        """Finds project-context.md (dash instead of underscore)."""
        (tmp_path / "project-context.md").write_text("# Dash Context")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = ContextBuilder(context).add_project_context().build()

        assert len(result) == 1
        assert "# Dash Context" in list(result.values())[0]


class TestContextBuilderAddPlanningDocs:
    """Test add_planning_docs() method."""

    def test_loads_prd_architecture_ux(self, tmp_path: Path) -> None:
        """Loads all three planning documents when present."""
        # Files go in planning-artifacts/ subdirectory (fallback location)
        planning_dir = tmp_path / "planning-artifacts"
        planning_dir.mkdir()
        (planning_dir / "prd.md").write_text("# PRD")
        (planning_dir / "architecture.md").write_text("# Architecture")
        (planning_dir / "ux.md").write_text("# UX Design")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = (
            ContextBuilder(context).add_planning_docs(prd=True, architecture=True, ux=True).build()
        )

        assert len(result) == 3
        contents = list(result.values())
        assert any("# PRD" in c for c in contents)
        assert any("# Architecture" in c for c in contents)
        assert any("# UX Design" in c for c in contents)

    def test_selective_planning_docs(self, tmp_path: Path) -> None:
        """Can selectively include/exclude planning docs."""
        # Files go in planning-artifacts/ subdirectory (fallback location)
        planning_dir = tmp_path / "planning-artifacts"
        planning_dir.mkdir()
        (planning_dir / "prd.md").write_text("# PRD")
        (planning_dir / "architecture.md").write_text("# Architecture")
        (planning_dir / "ux.md").write_text("# UX Design")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = (
            ContextBuilder(context)
            .add_planning_docs(prd=True, architecture=False, ux=False)
            .build()
        )

        assert len(result) == 1
        assert "# PRD" in list(result.values())[0]


class TestContextBuilderAddPreviousStories:
    """Test add_previous_stories() method."""

    def test_finds_previous_stories_in_same_epic(self, tmp_path: Path) -> None:
        """Finds stories from same epic before current story number."""
        stories_dir = tmp_path / "sprint-artifacts"
        stories_dir.mkdir()
        (stories_dir / "3-1-first.md").write_text("# Story 3.1")
        (stories_dir / "3-2-second.md").write_text("# Story 3.2")
        (stories_dir / "3-3-third.md").write_text("# Story 3.3")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
            resolved_variables={"epic_num": 3, "story_num": 4},
        )

        result = ContextBuilder(context).add_previous_stories(count=3).build()

        assert len(result) == 3

    def test_respects_count_limit(self, tmp_path: Path) -> None:
        """Only returns up to count stories."""
        stories_dir = tmp_path / "sprint-artifacts"
        stories_dir.mkdir()
        for i in range(1, 6):
            (stories_dir / f"1-{i}-story.md").write_text(f"# Story 1.{i}")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
            resolved_variables={"epic_num": 1, "story_num": 6},
        )

        result = ContextBuilder(context).add_previous_stories(count=2).build()

        # Only 2 most recent (4 and 5)
        assert len(result) == 2
        keys = list(result.keys())
        assert "1-4-story.md" in keys[0]
        assert "1-5-story.md" in keys[1]

    def test_no_stories_for_first_story(self, tmp_path: Path) -> None:
        """Story 1 has no previous stories."""
        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
            resolved_variables={"epic_num": 1, "story_num": 1},
        )

        result = ContextBuilder(context).add_previous_stories(count=3).build()

        assert result == {}


class TestContextBuilderAddEpicFiles:
    """Test add_epic_files() method."""

    def test_loads_sharded_epic_with_selective_load(self, tmp_path: Path) -> None:
        """For sharded epics, loads index.md + specific epic file only."""
        epics_dir = tmp_path / "epics"
        epics_dir.mkdir()
        (epics_dir / "index.md").write_text("# Index")
        (epics_dir / "summary.md").write_text("# Summary")
        (epics_dir / "epic-1-main.md").write_text("# Epic 1")
        (epics_dir / "epic-2-other.md").write_text("# Epic 2")
        (epics_dir / "epic-3-third.md").write_text("# Epic 3")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = ContextBuilder(context).add_epic_files(epic_num=2).build()

        # Should have: index.md + epic-2 (no other support files)
        assert len(result) == 2
        keys = list(result.keys())
        assert any("index.md" in k for k in keys)
        assert any("epic-2-other.md" in k for k in keys)
        # Verify no other support files or other epics
        assert not any("summary.md" in k for k in keys)
        assert not any("epic-1" in k for k in keys)
        assert not any("epic-3" in k for k in keys)

    def test_loads_single_epic_file(self, tmp_path: Path) -> None:
        """Loads single epic file when not sharded."""
        (tmp_path / "epic-5-solo.md").write_text("# Epic 5")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = ContextBuilder(context).add_epic_files(epic_num=5).build()

        assert len(result) == 1
        assert "# Epic 5" in list(result.values())[0]

    def test_supports_string_epic_num(self, tmp_path: Path) -> None:
        """Supports string epic identifiers like 'testarch'."""
        epics_dir = tmp_path / "epics"
        epics_dir.mkdir()
        (epics_dir / "epic-testarch-main.md").write_text("# Testarch Epic")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = ContextBuilder(context).add_epic_files(epic_num="testarch").build()

        assert len(result) == 1
        assert "# Testarch Epic" in list(result.values())[0]


class TestContextBuilderAddValidations:
    """Test add_validations() method."""

    def test_finds_validation_files(self, tmp_path: Path) -> None:
        """Finds validation files matching story key."""
        # Validations live in output_folder/sprint-artifacts/story-validations (fallback)
        # Pattern: validation-{story_key}-{role_id}-{timestamp}.md where role_id is single char
        (tmp_path / "sprint-artifacts").mkdir()
        validations_dir = tmp_path / "sprint-artifacts" / "story-validations"
        validations_dir.mkdir()
        (validations_dir / "validation-1-2-test-a-20260105.md").write_text("# Val A")
        (validations_dir / "validation-1-2-test-b-20260105.md").write_text("# Val B")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = ContextBuilder(context).add_validations(story_key="1-2-test").build()

        assert len(result) == 2

    def test_filters_by_session_id(self, tmp_path: Path) -> None:
        """Can filter validations by session_id."""
        # Pattern: validation-{story_key}-{role_id}-{session_id}*.md where role_id is single char
        (tmp_path / "sprint-artifacts").mkdir()
        validations_dir = tmp_path / "sprint-artifacts" / "story-validations"
        validations_dir.mkdir()
        (validations_dir / "validation-1-1-foo-a-session1.md").write_text("# S1")
        (validations_dir / "validation-1-1-foo-b-session1.md").write_text("# S1")
        (validations_dir / "validation-1-1-foo-a-session2.md").write_text("# S2")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = (
            ContextBuilder(context)
            .add_validations(
                story_key="1-1-foo",
                session_id="session1",
            )
            .build()
        )

        assert len(result) == 2


class TestContextBuilderBuild:
    """Test build() method."""

    def test_returns_ordered_dict(self, tmp_path: Path) -> None:
        """build() returns dict with insertion order preserved."""
        (tmp_path / "project_context.md").write_text("# Context")
        # Planning docs go in planning-artifacts/ subdirectory
        planning_dir = tmp_path / "planning-artifacts"
        planning_dir.mkdir()
        (planning_dir / "prd.md").write_text("# PRD")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = (
            ContextBuilder(context)
            .add_project_context()
            .add_planning_docs(prd=True, architecture=False, ux=False)
            .build()
        )

        # Dict maintains insertion order in Python 3.7+
        keys = list(result.keys())
        assert len(keys) == 2
        # project_context (priority 10) before prd (priority 20)
        assert "project_context.md" in keys[0]
        assert "prd.md" in keys[1]

    def test_keys_are_absolute_paths(self, tmp_path: Path) -> None:
        """Keys in result dict are absolute path strings."""
        (tmp_path / "project_context.md").write_text("# Context")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        result = ContextBuilder(context).add_project_context().build()

        key = list(result.keys())[0]
        # Should be absolute path
        assert Path(key).is_absolute()

    def test_deterministic_ordering(self, tmp_path: Path) -> None:
        """Same inputs produce same output order (NFR11)."""
        (tmp_path / "project_context.md").write_text("# Context")
        (tmp_path / "prd.md").write_text("# PRD")
        (tmp_path / "architecture.md").write_text("# Arch")

        context = CompilerContext(
            project_root=tmp_path,
            output_folder=tmp_path,
        )

        # Build multiple times
        results = []
        for _ in range(3):
            result = ContextBuilder(context).add_project_context().add_planning_docs().build()
            results.append(list(result.keys()))

        # All should be identical
        assert results[0] == results[1] == results[2]
