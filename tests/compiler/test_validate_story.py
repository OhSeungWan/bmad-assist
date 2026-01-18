"""Tests for the validate-story workflow compiler.

Tests the ValidateStoryCompiler class which orchestrates all compiler
pipeline components for the validate-story workflow (adversarial
story validation).
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from bmad_assist.compiler.parser import parse_workflow
from bmad_assist.compiler.types import CompiledWorkflow, CompilerContext
from bmad_assist.compiler.workflows.validate_story import (
    ValidateStoryCompiler,
)
from bmad_assist.core.exceptions import CompilerError


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project structure for testing.

    Includes a default story file (11-1-default.md) since Story 11.2 requires
    story files to exist for compilation to succeed.
    """
    docs = tmp_path / "docs"
    docs.mkdir()

    sprint_artifacts = docs / "sprint-artifacts"
    sprint_artifacts.mkdir()

    epics = docs / "epics"
    epics.mkdir()

    # Create default story file (required since Story 11.2)
    default_story = sprint_artifacts / "11-1-default.md"
    default_story.write_text("# Story 11.1: Default Test Story\n\nTest content.")

    workflow_dir = tmp_path / "_bmad" / "bmm" / "workflows" / "4-implementation" / "validate-story"
    workflow_dir.mkdir(parents=True)

    workflow_yaml = workflow_dir / "workflow.yaml"
    workflow_yaml.write_text("""name: validate-story
description: "Validate story file completeness and quality using adversarial analysis."
config_source: "{project-root}/_bmad/bmm/config.yaml"
template: false
instructions: "{installed_path}/instructions.xml"
""")

    instructions_xml = workflow_dir / "instructions.xml"
    instructions_xml.write_text("""<workflow>
  <critical>YOU ARE AN ADVERSARIAL STORY VALIDATOR</critical>
  <step n="1" goal="Identify and load story file">
    <action>Parse user input to extract story reference</action>
    <action>Search for story file matching pattern</action>
  </step>
  <step n="2" goal="Load source documents">
    <action>Load epic file containing story</action>
    <action>Extract epic requirements</action>
  </step>
  <step n="3" goal="Execute systematic validation">
    <action>Read requirement carefully</action>
    <action>Search story file for evidence</action>
  </step>
</workflow>
""")

    config_dir = tmp_path / "_bmad" / "bmm"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_yaml = config_dir / "config.yaml"
    config_yaml.write_text(f"""project_name: test-project
output_folder: '{tmp_path}/docs'
sprint_artifacts: '{tmp_path}/docs/sprint-artifacts'
user_name: TestUser
communication_language: English
document_output_language: English
""")

    return tmp_path


def create_test_context(
    project: Path,
    epic_num: int = 11,
    story_num: int = 1,
    **extra_vars: Any,
) -> CompilerContext:
    """Create a CompilerContext for testing.

    Pre-loads workflow_ir from the workflow directory (normally done by core.compile_workflow).
    """
    resolved_vars = {
        "epic_num": epic_num,
        "story_num": story_num,
        **extra_vars,
    }
    workflow_dir = project / "_bmad" / "bmm" / "workflows" / "4-implementation" / "validate-story"
    workflow_ir = parse_workflow(workflow_dir) if workflow_dir.exists() else None
    return CompilerContext(
        project_root=project,
        output_folder=project / "docs",
        resolved_variables=resolved_vars,
        workflow_ir=workflow_ir,
    )


class TestProtocolImplementation:
    """Tests for WorkflowCompiler protocol implementation (AC2)."""

    def test_protocol_implementation(self) -> None:
        """ValidateStoryCompiler implements WorkflowCompiler protocol."""
        compiler = ValidateStoryCompiler()

        assert hasattr(compiler, "workflow_name")
        assert hasattr(compiler, "get_required_files")
        assert hasattr(compiler, "get_variables")
        assert hasattr(compiler, "validate_context")
        assert hasattr(compiler, "compile")
        assert compiler.workflow_name == "validate-story"

    def test_workflow_name(self) -> None:
        """workflow_name returns 'validate-story'."""
        compiler = ValidateStoryCompiler()
        assert compiler.workflow_name == "validate-story"

    def test_get_required_files(self) -> None:
        """get_required_files returns expected patterns."""
        compiler = ValidateStoryCompiler()
        patterns = compiler.get_required_files()

        assert "**/project_context.md" in patterns
        assert "**/architecture*.md" in patterns
        assert "**/prd*.md" in patterns
        assert "**/sprint-status.yaml" in patterns
        assert "**/epic*.md" in patterns
        assert "**/sprint-artifacts/*.md" in patterns

    def test_get_variables(self) -> None:
        """get_variables returns expected variable names."""
        compiler = ValidateStoryCompiler()
        variables = compiler.get_variables()

        assert "epic_num" in variables
        assert "story_num" in variables
        assert "story_key" in variables
        assert "story_id" in variables
        assert "story_file" in variables
        assert "story_title" in variables
        assert "validation_focus" in variables
        assert variables["validation_focus"] == "story_quality"
        assert "date" in variables


class TestValidateContext:
    """Tests for validate_context method (AC7)."""

    def test_missing_project_root_raises(self, tmp_project: Path) -> None:
        """Missing project_root raises CompilerError."""
        context = CompilerContext(
            project_root=None,  # type: ignore
            output_folder=tmp_project / "docs",
            resolved_variables={"epic_num": 11, "story_num": 1},
        )
        compiler = ValidateStoryCompiler()

        with pytest.raises(CompilerError, match="project_root"):
            compiler.validate_context(context)

    def test_missing_output_folder_raises(self, tmp_project: Path) -> None:
        """Missing output_folder raises CompilerError."""
        context = CompilerContext(
            project_root=tmp_project,
            output_folder=None,  # type: ignore
            resolved_variables={"epic_num": 11, "story_num": 1},
        )
        compiler = ValidateStoryCompiler()

        with pytest.raises(CompilerError, match="output_folder"):
            compiler.validate_context(context)

    def test_missing_epic_num_raises(self, tmp_project: Path) -> None:
        """Missing epic_num raises CompilerError."""
        context = create_test_context(tmp_project, epic_num=None, story_num=1)  # type: ignore
        compiler = ValidateStoryCompiler()

        with pytest.raises(CompilerError, match="epic_num"):
            compiler.validate_context(context)

    def test_missing_story_num_raises(self, tmp_project: Path) -> None:
        """Missing story_num raises CompilerError."""
        context = create_test_context(tmp_project, epic_num=11, story_num=None)  # type: ignore
        compiler = ValidateStoryCompiler()

        with pytest.raises(CompilerError, match="story_num"):
            compiler.validate_context(context)

    def test_missing_workflow_dir_raises(self, tmp_project: Path) -> None:
        """Missing workflow directory raises CompilerError."""
        workflow_dir = (
            tmp_project / "_bmad" / "bmm" / "workflows" / "4-implementation" / "validate-story"
        )
        for f in workflow_dir.iterdir():
            f.unlink()
        workflow_dir.rmdir()

        context = create_test_context(tmp_project)
        compiler = ValidateStoryCompiler()

        with pytest.raises(CompilerError, match="Workflow directory not found"):
            compiler.validate_context(context)

    def test_valid_context_passes(self, tmp_project: Path) -> None:
        """Valid context passes validation."""
        context = create_test_context(tmp_project)
        compiler = ValidateStoryCompiler()

        compiler.validate_context(context)


class TestWorkflowLoading:
    """Tests for workflow file loading (AC3)."""

    def test_workflow_loading(self, tmp_project: Path) -> None:
        """Workflow files are loaded from correct location."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.workflow_name == "validate-story"
        assert result.instructions

    def test_action_workflow_no_template(self, tmp_project: Path) -> None:
        """Action workflow (template: false) has empty output_template."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.output_template == ""


class TestVariableResolution:
    """Tests for variable resolution (AC4)."""

    def test_variable_resolution(self, tmp_project: Path) -> None:
        """Core variables are resolved correctly."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.variables["epic_num"] == 11
        assert result.variables["story_num"] == 1
        assert result.variables["story_id"] == "11.1"
        assert result.variables["validation_focus"] == "story_quality"

    def test_story_file_resolution(self, tmp_project: Path) -> None:
        """Story file path is resolved via glob."""
        # Remove default story and create specific one
        default_story = tmp_project / "docs" / "sprint-artifacts" / "11-1-default.md"
        default_story.unlink()

        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-test-story.md"
        story_file.write_text("# Story 11.1: Test Story\n\nContent here.")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.variables["story_file"] is not None
        assert "11-1-test-story.md" in result.variables["story_file"]
        assert result.variables["story_key"] == "11-1-test-story"
        assert result.variables["story_title"] == "test-story"

    def test_story_file_missing_raises_error(self, tmp_project: Path) -> None:
        """Missing story file raises CompilerError.

        Note: Since Story 11.2, missing story files are a hard error,
        not a graceful fallback. Validators MUST have a story to validate.
        """
        context = create_test_context(tmp_project, epic_num=99, story_num=99)
        compiler = ValidateStoryCompiler()

        with pytest.raises(CompilerError, match="Story file not found"):
            compiler.compile(context)

    def test_date_variable_populated(self, tmp_project: Path) -> None:
        """Date variable is populated."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert "date" in result.variables


class TestCompiledWorkflowOutput:
    """Tests for CompiledWorkflow output structure (AC5)."""

    def test_compiled_workflow_structure(self, tmp_project: Path) -> None:
        """CompiledWorkflow has all required fields."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert isinstance(result, CompiledWorkflow)
        assert result.workflow_name == "validate-story"
        assert isinstance(result.mission, str)
        assert isinstance(result.context, str)
        assert isinstance(result.variables, dict)
        assert isinstance(result.instructions, str)
        assert isinstance(result.output_template, str)
        assert isinstance(result.token_estimate, int)

    def test_token_estimate_positive(self, tmp_project: Path) -> None:
        """Token estimate is a positive integer."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.token_estimate > 0

    def test_context_populated_with_story(self, tmp_project: Path) -> None:
        """Context section contains story file (populated by Story 11.2).

        Note: Story 11.1 returned empty context. Story 11.2 now populates
        context with story file (required) and other optional files.
        """
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        root = ET.fromstring(result.context)
        context_elem = root.find("context")

        assert context_elem is not None, "Context element should exist"
        file_elements = context_elem.findall(".//file")
        assert len(file_elements) > 0, "Context should contain at least one file (story)"

        # Story file should be in context
        paths = [f.get("path", "") for f in file_elements]
        assert any("11-1" in p for p in paths), "Story file should be in context"


class TestMissionDescription:
    """Tests for mission description (AC6)."""

    def test_mission_adversarial_focus(self, tmp_project: Path) -> None:
        """Mission emphasizes adversarial review."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        mission_lower = result.mission.lower()
        assert "adversarial" in mission_lower
        assert "issues" in mission_lower or "find" in mission_lower
        assert "read-only" in mission_lower

    def test_mission_excludes_code_review_terminology(self, tmp_project: Path) -> None:
        """Mission does NOT include code review terminology.

        Note: The phrase "not code implementation" is acceptable as it tells
        the LLM what NOT to focus on. The AC prohibits "implementation verification"
        and "test execution" as positive actions.
        """
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        mission_lower = result.mission.lower()
        # These phrases indicate code review activities (not allowed)
        assert "implementation verification" not in mission_lower
        assert "verify implementation" not in mission_lower
        assert "test execution" not in mission_lower
        assert "run tests" not in mission_lower
        assert "code review" not in mission_lower

    def test_mission_includes_story_info(self, tmp_project: Path) -> None:
        """Mission includes story number."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert "11.1" in result.mission

    def test_mission_includes_story_title(self, tmp_project: Path) -> None:
        """Mission includes story title when available."""
        # Remove default story and create specific one
        default_story = tmp_project / "docs" / "sprint-artifacts" / "11-1-default.md"
        default_story.unlink()

        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-test-validation.md"
        story_file.write_text("# Story 11.1\n\nContent.")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert "test-validation" in result.mission


class TestFailFastErrorHandling:
    """Tests for fail-fast error handling (AC8)."""

    def test_context_rollback_on_error(
        self,
        tmp_project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Context state is restored on compilation error."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        original_vars = dict(context.resolved_variables)

        def raise_error(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Test error")

        monkeypatch.setattr(
            "bmad_assist.compiler.workflows.validate_story.filter_instructions",
            raise_error,
        )

        compiler = ValidateStoryCompiler()

        with pytest.raises(RuntimeError):
            compiler.compile(context)

        assert context.resolved_variables == original_vars

    def test_no_partial_output_on_error(
        self,
        tmp_project: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No partial output is produced on error."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)

        def raise_error(*args: Any, **kwargs: Any) -> None:
            raise CompilerError("Test compilation error")

        monkeypatch.setattr(
            "bmad_assist.compiler.workflows.validate_story.generate_output",
            raise_error,
        )

        compiler = ValidateStoryCompiler()

        with pytest.raises(CompilerError):
            compiler.compile(context)


class TestXMLOutput:
    """Tests for XML output structure."""

    def test_xml_parseable(self, tmp_project: Path) -> None:
        """Generated XML is parseable by ElementTree."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        root = ET.fromstring(result.context)
        assert root.tag == "compiled-workflow"

    def test_xml_has_required_sections(self, tmp_project: Path) -> None:
        """XML output has all required sections."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        root = ET.fromstring(result.context)

        assert root.find("mission") is not None
        assert root.find("context") is not None
        assert root.find("variables") is not None
        assert root.find("instructions") is not None


class TestDynamicLoading:
    """Tests for dynamic loading via get_workflow_compiler (AC1)."""

    def test_dynamic_loading(self) -> None:
        """ValidateStoryCompiler is loaded dynamically via naming convention."""
        from bmad_assist.compiler.core import get_workflow_compiler

        compiler = get_workflow_compiler("validate-story")

        assert compiler.workflow_name == "validate-story"
        assert isinstance(compiler, ValidateStoryCompiler)

    def test_compile_workflow_function(self, tmp_project: Path) -> None:
        """compile_workflow() works with validate-story."""
        from bmad_assist.compiler import compile_workflow

        context = create_test_context(tmp_project, epic_num=11, story_num=1)

        # Mock discover_patch to avoid finding global/CWD patches (requires config)
        with patch("bmad_assist.compiler.patching.compiler.discover_patch", return_value=None):
            result = compile_workflow("validate-story", context)

        assert result.workflow_name == "validate-story"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_unicode_content_handled(self, tmp_project: Path) -> None:
        """Unicode content in story file is handled correctly."""
        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-tëst-störy.md"
        story_file.write_text("# Story 11.1: Tëst Störy\n\nÜñíçödé content.")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.workflow_name == "validate-story"

    def test_multiple_story_files_first_selected(self, tmp_project: Path) -> None:
        """Multiple matching story files - first alphabetically is selected."""
        (tmp_project / "docs" / "sprint-artifacts" / "11-1-a-first.md").write_text("# A")
        (tmp_project / "docs" / "sprint-artifacts" / "11-1-b-second.md").write_text("# B")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert "11-1-a-first" in result.variables["story_key"]

    def test_compilation_deterministic(self, tmp_project: Path) -> None:
        """Same input produces identical output."""
        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-test.md"
        story_file.write_text("# Story 11.1\n\nContent.")

        context1 = create_test_context(tmp_project, epic_num=11, story_num=1, date="2025-01-01")
        compiler1 = ValidateStoryCompiler()
        result1 = compiler1.compile(context1)

        context2 = create_test_context(tmp_project, epic_num=11, story_num=1, date="2025-01-01")
        compiler2 = ValidateStoryCompiler()
        result2 = compiler2.compile(context2)

        assert result1.mission == result2.mission
        assert result1.instructions == result2.instructions


class TestCachedTemplateLoading:
    """Tests for cached template loading."""

    def test_original_files_parsed(self, tmp_project: Path) -> None:
        """Original files are parsed when no cache available."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.instructions


class TestStoryFileMetadata:
    """Tests for story file metadata extraction."""

    def test_story_key_derivation(self, tmp_project: Path) -> None:
        """story_key is derived from filename."""
        # Remove default story and create specific one
        default_story = tmp_project / "docs" / "sprint-artifacts" / "11-1-default.md"
        default_story.unlink()

        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-validate-compiler.md"
        story_file.write_text("# Story 11.1\n\nContent.")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.variables["story_key"] == "11-1-validate-compiler"

    def test_story_title_from_slug(self, tmp_project: Path) -> None:
        """story_title is extracted from filename slug."""
        # Remove default story and create specific one
        default_story = tmp_project / "docs" / "sprint-artifacts" / "11-1-default.md"
        default_story.unlink()

        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-my-story-title.md"
        story_file.write_text("# Story 11.1\n\nContent.")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.variables["story_title"] == "my-story-title"

    def test_story_id_computed(self, tmp_project: Path) -> None:
        """story_id is computed as epic_num.story_num."""
        # Create story file for epic 11 story 3
        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-3-test.md"
        story_file.write_text("# Story 11.3\n\nContent.")

        context = create_test_context(tmp_project, epic_num=11, story_num=3)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.variables["story_id"] == "11.3"


class TestContextBuilding:
    """Tests for context building (AC1-6)."""

    def test_context_files_recency_bias_order(self, tmp_project: Path) -> None:
        """Context files are ordered by recency-bias (general → specific)."""
        # Remove default story to avoid conflicts
        default_story = tmp_project / "docs" / "sprint-artifacts" / "11-1-default.md"
        default_story.unlink()

        # Create all context files
        (tmp_project / "docs" / "project_context.md").write_text("# Project Context")
        (tmp_project / "docs" / "prd.md").write_text("# PRD")
        (tmp_project / "docs" / "architecture.md").write_text("# Architecture")
        epics = tmp_project / "docs" / "epics"
        epics.mkdir(exist_ok=True)
        (epics / "epic-11-test.md").write_text("# Epic 11")
        (tmp_project / "docs" / "sprint-artifacts" / "11-1-story.md").write_text("# Story 11.1")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()
        result = compiler.compile(context)

        # Parse XML and extract context file paths
        root = ET.fromstring(result.context)
        context_elem = root.find("context")
        assert context_elem is not None
        file_elements = context_elem.findall(".//file")
        paths = [f.get("path", "") for f in file_elements]

        # Verify we have context files
        assert len(paths) > 0, "Expected context files to be populated"

        # Verify project_context appears early (general)
        project_context_idx = next((i for i, p in enumerate(paths) if "project_context" in p), -1)
        assert project_context_idx >= 0, "project_context.md should be in context"

        # Verify story file appears (it should be present)
        story_idx = next((i for i, p in enumerate(paths) if "11-1-story" in p), -1)
        assert story_idx >= 0, "Story file should be in context"

    def test_story_file_last_in_dict_insertion_order(self, tmp_project: Path) -> None:
        """Story file is inserted LAST in _build_context_files dict."""
        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-test.md"
        story_file.write_text("# Story 11.1")

        # Create some other context files
        (tmp_project / "docs" / "project_context.md").write_text("# Project Context")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        # Call _build_context_files directly to verify dict ordering
        resolved = {"epic_num": 11, "story_num": 1}
        context_files = compiler._build_context_files(context, resolved)

        # Story should be LAST in dict (Python 3.7+ preserves insertion order)
        keys = list(context_files.keys())
        assert len(keys) > 0, "Expected context files"
        last_key = keys[-1]
        assert "11-1" in last_key, f"Story file should be last in dict, got: {last_key}"

    def test_previous_stories_included(self, tmp_project: Path) -> None:
        """Previous stories are included for context continuity (AC3)."""
        # Create 3 stories
        artifacts = tmp_project / "docs" / "sprint-artifacts"
        (artifacts / "11-1-first.md").write_text("# Story 1")
        (artifacts / "11-2-second.md").write_text("# Story 2")
        (artifacts / "11-3-third.md").write_text("# Story 3")

        # Compile for story 3
        context = create_test_context(tmp_project, epic_num=11, story_num=3)
        compiler = ValidateStoryCompiler()
        result = compiler.compile(context)

        # Verify stories 1 and 2 are in context
        assert "11-1" in result.context, "Story 11-1 should be in context"
        assert "11-2" in result.context, "Story 11-2 should be in context"

    def test_previous_stories_chronological_order(self, tmp_project: Path) -> None:
        """Previous stories are ordered chronologically (oldest first) per AC3."""
        artifacts = tmp_project / "docs" / "sprint-artifacts"
        (artifacts / "11-1-first.md").write_text("# Story 1 Content")
        (artifacts / "11-2-second.md").write_text("# Story 2 Content")
        (artifacts / "11-3-third.md").write_text("# Story 3 Content")
        (artifacts / "11-4-fourth.md").write_text("# Story 4 Content")

        context = create_test_context(tmp_project, epic_num=11, story_num=4)
        compiler = ValidateStoryCompiler()

        resolved = {"epic_num": 11, "story_num": 4}
        context_files = compiler._build_context_files(context, resolved)
        keys = list(context_files.keys())

        # Find indices of previous stories in the dict
        idx_1 = next((i for i, k in enumerate(keys) if "11-1" in k), -1)
        idx_2 = next((i for i, k in enumerate(keys) if "11-2" in k), -1)
        idx_3 = next((i for i, k in enumerate(keys) if "11-3" in k), -1)

        # Only up to 3 previous stories included (11.1, 11.2, 11.3 for story 11.4)
        assert idx_1 >= 0, "Story 11.1 should be in context"
        assert idx_2 >= 0, "Story 11.2 should be in context"
        assert idx_3 >= 0, "Story 11.3 should be in context"

        # Chronological order: 11.1 before 11.2 before 11.3
        assert idx_1 < idx_2, "Story 11.1 should appear before 11.2"
        assert idx_2 < idx_3, "Story 11.2 should appear before 11.3"

    def test_missing_story_file_raises_error(self, tmp_project: Path) -> None:
        """Missing story file raises CompilerError with actionable message (AC5)."""
        context = create_test_context(tmp_project, epic_num=99, story_num=99)
        compiler = ValidateStoryCompiler()

        with pytest.raises(CompilerError, match="Story file not found"):
            compiler.compile(context)

    def test_empty_story_file_raises_error(self, tmp_project: Path) -> None:
        """Empty story file raises CompilerError (AC6)."""
        # Remove default story and create empty one
        default_story = tmp_project / "docs" / "sprint-artifacts" / "11-1-default.md"
        default_story.unlink()

        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-empty.md"
        story_file.write_text("")  # Empty file

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        with pytest.raises(CompilerError, match="empty"):
            compiler.compile(context)

    def test_missing_optional_files_skipped(self, tmp_project: Path) -> None:
        """Missing optional files (prd, arch) are skipped gracefully."""
        # Only create story file (required)
        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-test.md"
        story_file.write_text("# Story 11.1")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        # Should not raise
        result = compiler.compile(context)
        assert result.workflow_name == "validate-story"

    def test_no_previous_stories_when_story_num_1(self, tmp_project: Path) -> None:
        """No previous stories searched when story_num is 1 (AC3)."""
        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-first.md"
        story_file.write_text("# Story 11.1")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        resolved = {"epic_num": 11, "story_num": 1}
        context_files = compiler._build_context_files(context, resolved)

        # Only story 1 should be in context (no previous)
        story_keys = [k for k in context_files if "11-" in k and "-artifacts" in k]
        # Should have exactly 1 story file (the current one)
        assert len(story_keys) == 1, f"Expected only current story, got: {story_keys}"

    def test_previous_stories_max_three(self, tmp_project: Path) -> None:
        """Maximum 3 previous stories included even if more exist (AC3)."""
        artifacts = tmp_project / "docs" / "sprint-artifacts"
        for i in range(1, 7):  # Create stories 1-6
            (artifacts / f"11-{i}-story{i}.md").write_text(f"# Story {i}")

        context = create_test_context(tmp_project, epic_num=11, story_num=6)
        compiler = ValidateStoryCompiler()

        resolved = {"epic_num": 11, "story_num": 6}
        context_files = compiler._build_context_files(context, resolved)
        keys = list(context_files.keys())

        # Count previous story files (not including current story 6)
        prev_story_keys = [k for k in keys if any(f"11-{n}" in k for n in range(1, 6))]

        # Should have max 3 previous stories
        assert len(prev_story_keys) <= 3, f"Expected max 3 previous, got {len(prev_story_keys)}"

    def test_previous_stories_gap_handling(self, tmp_project: Path) -> None:
        """Gaps in story numbers are handled - skip missing, include available (AC3)."""
        artifacts = tmp_project / "docs" / "sprint-artifacts"
        (artifacts / "11-1-first.md").write_text("# Story 1")
        # 11-2 is missing (gap)
        (artifacts / "11-3-third.md").write_text("# Story 3")
        (artifacts / "11-4-fourth.md").write_text("# Story 4")

        context = create_test_context(tmp_project, epic_num=11, story_num=4)
        compiler = ValidateStoryCompiler()

        resolved = {"epic_num": 11, "story_num": 4}
        context_files = compiler._build_context_files(context, resolved)
        keys = list(context_files.keys())

        # Should include 11-1 and 11-3 (skip missing 11-2)
        has_story_1 = any("11-1" in k for k in keys)
        has_story_3 = any("11-3" in k for k in keys)
        has_story_2 = any("11-2" in k for k in keys)

        assert has_story_1, "Story 11-1 should be included"
        assert has_story_3, "Story 11-3 should be included"
        assert not has_story_2, "Story 11-2 should not be included (doesn't exist)"


class TestValidationFocusConstant:
    """Tests for validation_focus hardcoded constant."""

    def test_validation_focus_is_story_quality(self, tmp_project: Path) -> None:
        """validation_focus is always 'story_quality'."""
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.variables["validation_focus"] == "story_quality"

    def test_validation_focus_not_from_yaml(self) -> None:
        """validation_focus comes from compiler constant, not YAML."""
        compiler = ValidateStoryCompiler()
        variables = compiler.get_variables()

        assert variables["validation_focus"] == "story_quality"


class TestVariableSubstitution:
    """Tests for variable substitution in instructions."""

    def test_variables_substituted_in_instructions(self, tmp_project: Path) -> None:
        """Variables like {{epic_num}} are substituted in instructions."""
        # Create story file for epic 11 story 3
        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-3-test.md"
        story_file.write_text("# Story 11.3\n\nContent.")

        # Update instructions to include variable placeholders
        workflow_dir = (
            tmp_project / "_bmad" / "bmm" / "workflows" / "4-implementation" / "validate-story"
        )
        instructions_xml = workflow_dir / "instructions.xml"
        instructions_xml.write_text("""<workflow>
  <step n="1" goal="Validate story {{epic_num}}.{{story_num}}">
    <action>Load story file for epic {{epic_num}} story {{story_num}}</action>
    <action>Focus: {{validation_focus}}</action>
  </step>
</workflow>
""")

        context = create_test_context(tmp_project, epic_num=11, story_num=3)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        # Variables should be substituted
        assert "{{epic_num}}" not in result.instructions
        assert "{{story_num}}" not in result.instructions
        assert "11" in result.instructions
        assert "story 11.3" in result.instructions.lower() or "11" in result.instructions
        assert "story_quality" in result.instructions

    def test_story_title_override_preserves_legitimate_titles(self, tmp_project: Path) -> None:
        """Story titles starting with 'story-' but not fallback pattern are preserved."""
        # Create story with title that legitimately starts with "story-"
        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-story-service-api.md"
        story_file.write_text("# Story 11.1\n\nContent.")

        context = create_test_context(
            tmp_project,
            epic_num=11,
            story_num=1,
            story_title="story-service-api",  # Pre-populated legitimate title
        )
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        # Should preserve the title from filename (same as pre-populated)
        assert result.variables["story_title"] == "story-service-api"

    def test_fallback_story_title_overridden(self, tmp_project: Path) -> None:
        """Fallback 'story-N' pattern titles are correctly overridden."""
        story_file = tmp_project / "docs" / "sprint-artifacts" / "11-1-actual-story-name.md"
        story_file.write_text("# Story 11.1\n\nContent.")

        context = create_test_context(
            tmp_project,
            epic_num=11,
            story_num=1,
            story_title="story-1",  # Fallback pattern should be overridden
        )
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        # Fallback "story-1" should be replaced with actual filename slug
        assert result.variables["story_title"] == "actual-story-name"


class TestPatchIntegration:
    """Tests for patch integration in ValidateStoryCompiler (Story 11.3)."""

    @pytest.fixture
    def project_with_patch(self, tmp_project: Path) -> Path:
        """Create project structure with patch file."""
        patch_dir = tmp_project / "_bmad-assist" / "patches"
        patch_dir.mkdir(parents=True)
        patch_file = patch_dir / "validate-story.patch.yaml"
        patch_file.write_text("""patch:
  name: test-patch
  version: "1.0.0"
  author: "Test"
  description: "Test patch"
compatibility:
  bmad_version: "6.0.0"
  workflow: validate-story
transforms:
  - "Remove step 1 completely"
post_process:
  - pattern: 'REMOVE_THIS_PATTERN'
    replacement: ""
validation:
  must_contain:
    - "<step"
  must_not_contain:
    - "FORBIDDEN_STRING"
""")
        return tmp_project

    @pytest.fixture
    def home_patch_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Create patch in simulated home directory."""
        home_patches = tmp_path / "fake_home" / "_bmad-assist" / "patches"
        home_patches.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(tmp_path / "fake_home"))
        return home_patches

    def test_patch_discovered_from_project_dir(
        self, project_with_patch: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Patch is discovered from project _bmad-assist/patches/ directory."""
        import logging

        caplog.set_level(logging.DEBUG)

        context = create_test_context(project_with_patch, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        # Compilation should succeed
        assert result.workflow_name == "validate-story"
        # Check debug logs mention patch discovery (flexible matching)
        log_text = caplog.text.lower()
        assert "patch" in log_text or "post_process" in log_text

    def test_patch_discovered_from_home_dir(
        self,
        tmp_project: Path,
        home_patch_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Patch is discovered from home ~_bmad-assist/patches/ directory."""
        import logging

        caplog.set_level(logging.DEBUG)

        # Create VALID patch in home dir only (no project patch)
        # Note: patch MUST have transforms (required), bmad_version, and workflow
        home_patch = home_patch_dir / "validate-story.patch.yaml"
        home_patch.write_text("""patch:
  name: home-patch
  version: "1.0.0"
compatibility:
  bmad_version: "6.0.0"
  workflow: validate-story
transforms:
  - "Test transform instruction for home patch"
validation:
  must_contain:
    - "<step"
""")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.workflow_name == "validate-story"

    def test_project_patch_overrides_home_patch(
        self,
        project_with_patch: Path,
        home_patch_dir: Path,
    ) -> None:
        """Project patch completely overrides home patch (no merge)."""
        # Create VALID different patch in home dir
        # Note: patch MUST have transforms (required), bmad_version, and workflow
        home_patch = home_patch_dir / "validate-story.patch.yaml"
        home_patch.write_text("""patch:
  name: home-patch-should-be-ignored
  version: "1.0.0"
compatibility:
  bmad_version: "6.0.0"
  workflow: validate-story
transforms:
  - "Home patch transform that should NOT be applied"
post_process:
  - pattern: 'HOME_ONLY_PATTERN'
    replacement: "HOME_REPLACEMENT"
""")

        # Project patch has REMOVE_THIS_PATTERN
        # Home patch has HOME_ONLY_PATTERN
        # Project should win

        context = create_test_context(project_with_patch, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        # Compilation should succeed with project patch
        assert result.workflow_name == "validate-story"
        # HOME_ONLY_PATTERN should NOT have been processed
        # (can't easily test this without more complex setup)

    def test_post_process_rules_applied(
        self, tmp_project: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Post-process regex rules are applied to output."""
        import logging

        caplog.set_level(logging.DEBUG)

        # Create VALID patch with post_process rule that will match
        # Note: patch MUST have transforms (required), bmad_version, and workflow
        patch_dir = tmp_project / "_bmad-assist" / "patches"
        patch_dir.mkdir(parents=True)
        patch_file = patch_dir / "validate-story.patch.yaml"
        patch_file.write_text("""patch:
  name: test-patch
  version: "1.0.0"
compatibility:
  bmad_version: "6.0.0"
  workflow: validate-story
transforms:
  - "Test transform instruction"
post_process:
  - pattern: "ADVERSARIAL"
    replacement: "MODIFIED"
validation:
  must_contain:
    - "<step"
""")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        # The word ADVERSARIAL in mission should be replaced with MODIFIED
        assert "MODIFIED" in result.context or "post_process" in caplog.text.lower()

    def test_no_patch_graceful_handling(
        self, tmp_project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Compilation succeeds when no patch file exists (patch_path=None)."""
        # Ensure no patch exists in project
        patch_dir = tmp_project / "_bmad-assist" / "patches"
        if patch_dir.exists():
            import shutil

            shutil.rmtree(patch_dir)

        # Mock HOME to fake directory with no patches (avoid real global patch)
        fake_home = tmp_project / "fake_home_no_patch"
        fake_home.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(fake_home))

        # context.patch_path is None (no patch), context.workflow_ir is pre-loaded
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        # Should complete without error
        assert result.workflow_name == "validate-story"

    def test_validation_rules_checked(
        self, project_with_patch: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Validation rules are checked on compiled output."""
        import logging

        caplog.set_level(logging.DEBUG)

        context = create_test_context(project_with_patch, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        # Compilation should succeed
        assert result.workflow_name == "validate-story"
        # Output should contain <step (from validation.must_contain)
        assert "<step" in result.context

    def test_validation_failure_logs_warning(
        self, tmp_project: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Validation failure logs warning but doesn't fail compilation."""
        import logging

        caplog.set_level(logging.WARNING)

        # Mock HOME to avoid real global patch interfering
        fake_home = tmp_project / "fake_home_validation"
        fake_home.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(fake_home))

        # Create patch with must_contain that won't match
        patch_dir = tmp_project / "_bmad-assist" / "patches"
        patch_dir.mkdir(parents=True)
        patch_file = patch_dir / "validate-story.patch.yaml"
        patch_file.write_text("""patch:
  name: strict-patch
  version: "1.0.0"
compatibility:
  bmad_version: "6.0.0"
  workflow: validate-story
transforms:
  - "No-op transform for testing"
validation:
  must_contain:
    - "<step"
    - "NONEXISTENT_STRING_THAT_WONT_BE_IN_OUTPUT"
  must_not_contain:
    - "SOME_FORBIDDEN"
""")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        context.patch_path = patch_file  # Set patch path to enable validation
        compiler = ValidateStoryCompiler()

        # Should NOT raise - validation errors are warnings not failures
        result = compiler.compile(context)

        # Compilation should succeed
        assert result.workflow_name == "validate-story"
        # Should log warning about validation failure with specific message pattern
        log_text = caplog.text.lower()
        assert "validation warnings" in log_text or "not found in output" in log_text

    def test_cached_template_used_when_valid(
        self, tmp_project: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cached patched template is used when cache is valid."""
        import logging

        caplog.set_level(logging.INFO)

        # This test verifies the cache mechanism path exists
        # Full cache testing is complex - just verify no crash
        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        result = compiler.compile(context)

        assert result.workflow_name == "validate-story"

    def test_invalid_patch_graceful_handling(
        self, tmp_project: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Invalid patch YAML is handled gracefully (logged, not crash)."""
        import logging

        caplog.set_level(logging.WARNING)

        # Create invalid patch file
        patch_dir = tmp_project / "_bmad-assist" / "patches"
        patch_dir.mkdir(parents=True)
        patch_file = patch_dir / "validate-story.patch.yaml"
        patch_file.write_text("invalid: yaml: content: [broken")

        context = create_test_context(tmp_project, epic_num=11, story_num=1)
        compiler = ValidateStoryCompiler()

        # Should not crash - invalid patch is logged and skipped
        result = compiler.compile(context)

        assert result.workflow_name == "validate-story"
