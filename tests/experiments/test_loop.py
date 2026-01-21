"""Tests for experiments loop template system.

Tests cover:
- LoopStep model validation
- LoopTemplate model validation
- YAML loading and error handling
- LoopRegistry discovery and access
- Workflow validation warnings
- Default templates (standard, atdd, fast)
"""

import logging
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic import ValidationError

from bmad_assist.core.exceptions import ConfigError
from bmad_assist.experiments.config import NAME_PATTERN
from bmad_assist.experiments.loop import (
    KNOWN_WORKFLOWS,
    LoopRegistry,
    LoopStep,
    LoopTemplate,
    load_loop_template,
)


class TestKnownWorkflows:
    """Tests for KNOWN_WORKFLOWS constant."""

    def test_known_workflows_is_frozenset(self) -> None:
        """Test KNOWN_WORKFLOWS is a frozenset."""
        assert isinstance(KNOWN_WORKFLOWS, frozenset)

    def test_known_workflows_contains_phase_values(self) -> None:
        """Test KNOWN_WORKFLOWS contains expected Phase enum mappings."""
        expected_from_phase = {
            "create-story",
            "validate-story",
            "validate-story-synthesis",
            "atdd",
            "dev-story",
            "code-review",
            "code-review-synthesis",
            "test-review",
            "retrospective",
        }
        assert expected_from_phase.issubset(KNOWN_WORKFLOWS)

    def test_known_workflows_contains_custom_workflows(self) -> None:
        """Test KNOWN_WORKFLOWS contains custom workflows like test-design."""
        assert "test-design" in KNOWN_WORKFLOWS

    def test_known_workflows_contains_all_kebab_case(self) -> None:
        """Test KNOWN_WORKFLOWS contains all kebab-case workflows (legacy)."""
        expected_kebab = {
            "create-story",
            "validate-story",
            "validate-story-synthesis",
            "dev-story",
            "code-review",
            "code-review-synthesis",
            "test-review",
            "qa-plan-generate",
            "qa-plan-execute",
            "test-design",
        }
        # All kebab-case should be in KNOWN_WORKFLOWS
        assert expected_kebab.issubset(KNOWN_WORKFLOWS)

    def test_known_workflows_contains_all_snake_case(self) -> None:
        """Test KNOWN_WORKFLOWS contains all snake_case workflows (LoopConfig convention)."""
        expected_snake = {
            "create_story",
            "validate_story",
            "validate_story_synthesis",
            "atdd",
            "dev_story",
            "code_review",
            "code_review_synthesis",
            "test_review",
            "retrospective",
            "qa_plan_generate",
            "qa_plan_execute",
            "test_design",
        }
        # All snake_case should be in KNOWN_WORKFLOWS
        assert expected_snake.issubset(KNOWN_WORKFLOWS)


class TestNamePattern:
    """Tests for name validation pattern (reused from config)."""

    def test_valid_names(self) -> None:
        """Test valid name patterns."""
        valid_names = [
            "standard",
            "atdd",
            "fast-loop",
            "my_custom_loop",
            "_private",
            "Loop123",
        ]
        for name in valid_names:
            assert NAME_PATTERN.match(name), f"Expected '{name}' to be valid"

    def test_invalid_names(self) -> None:
        """Test invalid name patterns."""
        invalid_names = [
            "123-start",  # starts with number
            "-hyphen-start",  # starts with hyphen
            "has spaces",  # contains space
            "has.dots",  # contains dot
            "has@special",  # contains special char
            "",  # empty
        ]
        for name in invalid_names:
            assert not NAME_PATTERN.match(name), f"Expected '{name}' to be invalid"


class TestLoopStep:
    """Tests for LoopStep Pydantic model."""

    def test_valid_loop_step(self) -> None:
        """Test creating a valid LoopStep."""
        step = LoopStep(workflow="create-story", required=True)
        assert step.workflow == "create-story"
        assert step.required is True

    def test_loop_step_required_defaults_true(self) -> None:
        """Test that required defaults to True."""
        step = LoopStep(workflow="dev-story")
        assert step.required is True

    def test_loop_step_required_false(self) -> None:
        """Test setting required to False."""
        step = LoopStep(workflow="validate-story", required=False)
        assert step.required is False

    def test_empty_workflow_raises_error(self) -> None:
        """Test that empty workflow raises ValueError."""
        with pytest.raises(ValueError, match="workflow cannot be empty"):
            LoopStep(workflow="")

    def test_whitespace_workflow_raises_error(self) -> None:
        """Test that whitespace-only workflow raises ValueError."""
        with pytest.raises(ValueError, match="workflow cannot be empty"):
            LoopStep(workflow="   ")

    def test_loop_step_is_frozen(self) -> None:
        """Test that LoopStep is immutable."""
        step = LoopStep(workflow="create-story")
        with pytest.raises(ValidationError, match="frozen"):
            step.workflow = "dev-story"  # type: ignore[misc]


class TestLoopTemplate:
    """Tests for LoopTemplate Pydantic model."""

    def test_valid_minimal_template(self) -> None:
        """Test creating a minimal valid template."""
        template = LoopTemplate(
            name="test-loop",
            sequence=[LoopStep(workflow="create-story")],
        )
        assert template.name == "test-loop"
        assert template.description is None
        assert len(template.sequence) == 1
        assert template.sequence[0].workflow == "create-story"

    def test_valid_full_template(self) -> None:
        """Test creating a full template with all fields."""
        template = LoopTemplate(
            name="full-loop",
            description="Full development loop",
            sequence=[
                LoopStep(workflow="create-story"),
                LoopStep(workflow="validate-story"),
                LoopStep(workflow="dev-story"),
                LoopStep(workflow="code-review"),
            ],
        )
        assert template.name == "full-loop"
        assert template.description == "Full development loop"
        assert len(template.sequence) == 4

    def test_empty_name_raises_error(self) -> None:
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            LoopTemplate(
                name="",
                sequence=[LoopStep(workflow="create-story")],
            )

    def test_whitespace_name_raises_error(self) -> None:
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            LoopTemplate(
                name="   ",
                sequence=[LoopStep(workflow="create-story")],
            )

    def test_name_with_spaces_raises_error(self) -> None:
        """Test that name with spaces raises ValueError."""
        with pytest.raises(ValueError, match="Invalid name"):
            LoopTemplate(
                name="has spaces",
                sequence=[LoopStep(workflow="create-story")],
            )

    def test_name_with_special_chars_raises_error(self) -> None:
        """Test that name with special characters raises ValueError."""
        with pytest.raises(ValueError, match="Invalid name"):
            LoopTemplate(
                name="has@special",
                sequence=[LoopStep(workflow="create-story")],
            )

    def test_name_starting_with_number_raises_error(self) -> None:
        """Test that name starting with number raises ValueError."""
        with pytest.raises(ValueError, match="Invalid name"):
            LoopTemplate(
                name="123loop",
                sequence=[LoopStep(workflow="create-story")],
            )

    def test_name_starting_with_hyphen_raises_error(self) -> None:
        """Test that name starting with hyphen raises ValueError."""
        with pytest.raises(ValueError, match="Invalid name"):
            LoopTemplate(
                name="-loop",
                sequence=[LoopStep(workflow="create-story")],
            )

    def test_empty_sequence_raises_error(self) -> None:
        """Test that empty sequence raises validation error."""
        with pytest.raises(ValidationError, match="at least 1"):
            LoopTemplate(
                name="empty-loop",
                sequence=[],
            )

    def test_template_is_frozen(self) -> None:
        """Test that template is immutable."""
        template = LoopTemplate(
            name="test-loop",
            sequence=[LoopStep(workflow="create-story")],
        )
        with pytest.raises(ValidationError, match="frozen"):
            template.name = "new-name"  # type: ignore[misc]


class TestLoadLoopTemplate:
    """Tests for load_loop_template function."""

    def test_load_minimal_template(
        self,
        write_loop: Callable[[str, str], Path],
        valid_minimal_loop: str,
    ) -> None:
        """Test loading a minimal valid template."""
        path = write_loop(valid_minimal_loop, "test-loop.yaml")
        template = load_loop_template(path)

        assert template.name == "test-loop"
        assert template.description == "Test loop configuration"
        assert len(template.sequence) == 2
        assert template.sequence[0].workflow == "create-story"
        assert template.sequence[1].workflow == "dev-story"

    def test_load_full_template(
        self,
        write_loop: Callable[[str, str], Path],
        valid_full_loop: str,
    ) -> None:
        """Test loading a full template with all phases."""
        path = write_loop(valid_full_loop, "full-loop.yaml")
        template = load_loop_template(path)

        assert template.name == "full-loop"
        assert len(template.sequence) == 6
        workflows = [step.workflow for step in template.sequence]
        assert workflows == [
            "create-story",
            "validate-story",
            "validate-story-synthesis",
            "dev-story",
            "code-review",
            "code-review-synthesis",
        ]

    def test_load_template_with_optional_steps(
        self,
        write_loop: Callable[[str, str], Path],
        loop_with_optional_steps: str,
    ) -> None:
        """Test loading template with optional (required=false) steps."""
        path = write_loop(loop_with_optional_steps, "optional-loop.yaml")
        template = load_loop_template(path)

        assert template.name == "optional-loop"
        assert template.sequence[0].required is True
        assert template.sequence[1].required is False
        assert template.sequence[2].required is True

    def test_file_not_found_raises_error(self, tmp_path: Path) -> None:
        """Test missing file raises ConfigError."""
        path = tmp_path / "nonexistent.yaml"
        with pytest.raises(ConfigError, match="not found"):
            load_loop_template(path)

    def test_invalid_yaml_raises_error(
        self,
        write_loop: Callable[[str, str], Path],
    ) -> None:
        """Test invalid YAML raises ConfigError."""
        path = write_loop("invalid: yaml: [", "invalid.yaml")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_loop_template(path)

    def test_empty_file_raises_error(
        self,
        write_loop: Callable[[str, str], Path],
    ) -> None:
        """Test empty file raises ConfigError."""
        path = write_loop("", "empty.yaml")
        with pytest.raises(ConfigError, match="is empty"):
            load_loop_template(path)

    def test_non_mapping_raises_error(
        self,
        write_loop: Callable[[str, str], Path],
    ) -> None:
        """Test non-mapping YAML raises ConfigError."""
        path = write_loop("- just\n- a\n- list", "list.yaml")
        with pytest.raises(ConfigError, match="must contain a YAML mapping"):
            load_loop_template(path)

    def test_validation_error_raises_config_error(
        self,
        write_loop: Callable[[str, str], Path],
    ) -> None:
        """Test schema validation failure raises ConfigError."""
        content = """\
name: test
# missing sequence section
"""
        path = write_loop(content, "missing-sequence.yaml")
        with pytest.raises(ConfigError, match="validation failed"):
            load_loop_template(path)

    def test_path_is_directory_raises_error(
        self,
        loops_dir: Path,
    ) -> None:
        """Test path that is directory raises ConfigError."""
        with pytest.raises(ConfigError, match="is not a file"):
            load_loop_template(loops_dir)

    def test_unknown_workflow_logs_warning(
        self,
        write_loop: Callable[[str, str], Path],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test unknown workflow name logs warning but doesn't fail."""
        content = """\
name: test-loop
sequence:
  - workflow: unknown-workflow
    required: true
  - workflow: create-story
    required: true
"""
        path = write_loop(content, "test-loop.yaml")

        with caplog.at_level(logging.WARNING):
            template = load_loop_template(path)

        assert template.name == "test-loop"
        assert "Unknown workflow" in caplog.text
        assert "unknown-workflow" in caplog.text
        # Should list known workflows in warning
        assert "create-story" in caplog.text or "KNOWN_WORKFLOWS" in caplog.text


class TestLoopRegistry:
    """Tests for LoopRegistry class."""

    def test_discover_finds_yaml_files(
        self,
        write_loop: Callable[[str, str], Path],
        loops_dir: Path,
    ) -> None:
        """Test discovery finds all .yaml files."""
        write_loop(
            "name: loop-a\nsequence:\n  - workflow: create-story",
            "loop-a.yaml",
        )
        write_loop(
            "name: loop-b\nsequence:\n  - workflow: dev-story",
            "loop-b.yaml",
        )

        registry = LoopRegistry(loops_dir)
        names = registry.list()

        assert sorted(names) == ["loop-a", "loop-b"]

    def test_discover_skips_hidden_files(
        self,
        write_loop: Callable[[str, str], Path],
        loops_dir: Path,
    ) -> None:
        """Test discovery skips hidden files."""
        write_loop(
            "name: visible\nsequence:\n  - workflow: create-story",
            "visible.yaml",
        )
        (loops_dir / ".hidden.yaml").write_text(
            "name: hidden\nsequence:\n  - workflow: create-story"
        )

        registry = LoopRegistry(loops_dir)
        names = registry.list()

        assert names == ["visible"]

    def test_discover_skips_yml_files(
        self,
        write_loop: Callable[[str, str], Path],
        loops_dir: Path,
    ) -> None:
        """Test discovery only finds .yaml, not .yml files."""
        write_loop(
            "name: yaml-file\nsequence:\n  - workflow: create-story",
            "yaml-file.yaml",
        )
        (loops_dir / "yml-file.yml").write_text(
            "name: yml-file\nsequence:\n  - workflow: create-story"
        )

        registry = LoopRegistry(loops_dir)
        names = registry.list()

        assert names == ["yaml-file"]

    def test_discover_skips_name_mismatch(
        self,
        write_loop: Callable[[str, str], Path],
        loops_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test discovery skips files where name doesn't match filename."""
        write_loop(
            "name: correct\nsequence:\n  - workflow: create-story",
            "correct.yaml",
        )
        write_loop(
            "name: wrong-name\nsequence:\n  - workflow: create-story",
            "mismatched.yaml",
        )

        with caplog.at_level(logging.WARNING):
            registry = LoopRegistry(loops_dir)
            names = registry.list()

        assert names == ["correct"]
        assert "does not match filename stem" in caplog.text

    def test_discover_skips_malformed_yaml(
        self,
        write_loop: Callable[[str, str], Path],
        loops_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test discovery skips files with invalid YAML."""
        write_loop(
            "name: valid\nsequence:\n  - workflow: create-story",
            "valid.yaml",
        )
        write_loop("invalid: yaml: [", "invalid.yaml")

        with caplog.at_level(logging.WARNING):
            registry = LoopRegistry(loops_dir)
            names = registry.list()

        assert names == ["valid"]
        assert "invalid YAML" in caplog.text

    def test_discover_nonexistent_directory(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test discovery returns empty dict for non-existent directory."""
        nonexistent = tmp_path / "nonexistent"

        with caplog.at_level(logging.INFO):
            registry = LoopRegistry(nonexistent)
            names = registry.list()

        assert names == []
        assert "does not exist" in caplog.text

    def test_get_returns_template(
        self,
        write_loop: Callable[[str, str], Path],
        loops_dir: Path,
    ) -> None:
        """Test get() returns loaded template."""
        write_loop(
            "name: test-loop\ndescription: Test\nsequence:\n  - workflow: create-story",
            "test-loop.yaml",
        )

        registry = LoopRegistry(loops_dir)
        template = registry.get("test-loop")

        assert template.name == "test-loop"
        assert template.description == "Test"

    def test_get_not_found_raises_error(
        self,
        write_loop: Callable[[str, str], Path],
        loops_dir: Path,
    ) -> None:
        """Test get() raises ConfigError for unknown name."""
        write_loop(
            "name: existing\nsequence:\n  - workflow: create-story",
            "existing.yaml",
        )

        registry = LoopRegistry(loops_dir)

        with pytest.raises(ConfigError, match="not found") as exc_info:
            registry.get("nonexistent")

        assert "existing" in str(exc_info.value)  # Should list available

    def test_get_caches_templates(
        self,
        write_loop: Callable[[str, str], Path],
        loops_dir: Path,
    ) -> None:
        """Test get() caches loaded templates."""
        write_loop(
            "name: cached\nsequence:\n  - workflow: create-story",
            "cached.yaml",
        )

        registry = LoopRegistry(loops_dir)

        template1 = registry.get("cached")
        template2 = registry.get("cached")

        # Same instance due to caching
        assert template1 is template2

    def test_list_returns_sorted_names(
        self,
        write_loop: Callable[[str, str], Path],
        loops_dir: Path,
    ) -> None:
        """Test list() returns sorted names."""
        write_loop(
            "name: zebra\nsequence:\n  - workflow: create-story",
            "zebra.yaml",
        )
        write_loop(
            "name: alpha\nsequence:\n  - workflow: create-story",
            "alpha.yaml",
        )
        write_loop(
            "name: beta\nsequence:\n  - workflow: create-story",
            "beta.yaml",
        )

        registry = LoopRegistry(loops_dir)
        names = registry.list()

        assert names == ["alpha", "beta", "zebra"]


class TestDefaultTemplates:
    """Tests for default loop templates in experiments/loops/."""

    @pytest.fixture
    def default_loops_dir(self) -> Path:
        """Path to default loop templates."""
        # This assumes tests are run from project root
        return Path("experiments/loops")

    def test_standard_exists(self, default_loops_dir: Path) -> None:
        """Test standard.yaml exists and is valid."""
        if not default_loops_dir.exists():
            pytest.skip("Default loops not available in this environment")

        template = load_loop_template(default_loops_dir / "standard.yaml")
        assert template.name == "standard"
        assert len(template.sequence) >= 4  # At least create, validate, dev, review
        workflows = [step.workflow for step in template.sequence]
        assert "create-story" in workflows
        assert "dev-story" in workflows
        assert "code-review" in workflows

    def test_atdd_exists(self, default_loops_dir: Path) -> None:
        """Test atdd.yaml exists and is valid."""
        if not default_loops_dir.exists():
            pytest.skip("Default loops not available in this environment")

        template = load_loop_template(default_loops_dir / "atdd.yaml")
        assert template.name == "atdd"
        workflows = [step.workflow for step in template.sequence]
        assert "test-design" in workflows
        assert "create-story" in workflows
        assert "dev-story" in workflows

    def test_fast_exists(self, default_loops_dir: Path) -> None:
        """Test fast.yaml exists and is valid."""
        if not default_loops_dir.exists():
            pytest.skip("Default loops not available in this environment")

        template = load_loop_template(default_loops_dir / "fast.yaml")
        assert template.name == "fast"
        # Fast loop should skip validation
        workflows = [step.workflow for step in template.sequence]
        assert "create-story" in workflows
        assert "dev-story" in workflows
        assert "validate-story" not in workflows

    def test_all_default_templates_discoverable(self, default_loops_dir: Path) -> None:
        """Test LoopRegistry can discover all default templates."""
        if not default_loops_dir.exists():
            pytest.skip("Default loops not available in this environment")

        registry = LoopRegistry(default_loops_dir)
        names = registry.list()

        expected = ["atdd", "fast", "standard"]
        assert sorted(names) == expected

    def test_all_default_templates_have_known_workflows(self, default_loops_dir: Path) -> None:
        """Test all default templates only use known workflows."""
        if not default_loops_dir.exists():
            pytest.skip("Default loops not available in this environment")

        registry = LoopRegistry(default_loops_dir)

        for name in registry.list():
            template = registry.get(name)
            for step in template.sequence:
                assert step.workflow in KNOWN_WORKFLOWS, (
                    f"Template '{name}' uses unknown workflow: {step.workflow}"
                )

    def test_all_steps_required_by_default_in_templates(self, default_loops_dir: Path) -> None:
        """Test default templates have required=true for all steps."""
        if not default_loops_dir.exists():
            pytest.skip("Default loops not available in this environment")

        registry = LoopRegistry(default_loops_dir)

        for name in registry.list():
            template = registry.get(name)
            for step in template.sequence:
                assert step.required is True, (
                    f"Template '{name}' has non-required step: {step.workflow}"
                )
