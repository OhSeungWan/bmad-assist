"""Tests for patch definition data models."""

import pytest
from pydantic import ValidationError

from bmad_assist.compiler.patching.types import (
    Compatibility,
    PatchConfig,
    TransformResult,
    Validation,
    WorkflowPatch,
)
from bmad_assist.core.exceptions import PatchError


class TestPatchConfig:
    """Tests for PatchConfig dataclass."""

    def test_valid_config_required_fields(self) -> None:
        """Test creating PatchConfig with required fields only."""
        config = PatchConfig(name="test-patch", version="1.0.0")
        assert config.name == "test-patch"
        assert config.version == "1.0.0"
        assert config.author is None
        assert config.description is None

    def test_valid_config_all_fields(self) -> None:
        """Test creating PatchConfig with all fields."""
        config = PatchConfig(
            name="test-patch",
            version="1.0.0",
            author="Test Author",
            description="A test patch",
        )
        assert config.name == "test-patch"
        assert config.version == "1.0.0"
        assert config.author == "Test Author"
        assert config.description == "A test patch"

    def test_empty_name_raises_error(self) -> None:
        """Test that empty name raises validation error."""
        with pytest.raises(ValidationError):
            PatchConfig(name="", version="1.0.0")

    def test_empty_version_raises_error(self) -> None:
        """Test that empty version raises validation error."""
        with pytest.raises(ValidationError):
            PatchConfig(name="test", version="")


class TestCompatibility:
    """Tests for Compatibility dataclass."""

    def test_valid_compatibility(self) -> None:
        """Test creating Compatibility with valid values."""
        compat = Compatibility(bmad_version="0.1.0", workflow="create-story")
        assert compat.bmad_version == "0.1.0"
        assert compat.workflow == "create-story"

    def test_empty_bmad_version_raises_error(self) -> None:
        """Test that empty bmad_version raises validation error."""
        with pytest.raises(ValidationError):
            Compatibility(bmad_version="", workflow="test")

    def test_empty_workflow_raises_error(self) -> None:
        """Test that empty workflow raises validation error."""
        with pytest.raises(ValidationError):
            Compatibility(bmad_version="0.1.0", workflow="")


class TestTransformResult:
    """Tests for TransformResult dataclass."""

    def test_successful_result(self) -> None:
        """Test creating a successful transform result."""
        result = TransformResult(success=True, transform_index=0)
        assert result.success is True
        assert result.transform_index == 0
        assert result.reason is None

    def test_failed_result(self) -> None:
        """Test creating a failed transform result."""
        result = TransformResult(
            success=False,
            transform_index=2,
            reason="LLM response missing workflow tag",
        )
        assert result.success is False
        assert result.transform_index == 2
        assert result.reason == "LLM response missing workflow tag"


class TestValidation:
    """Tests for Validation dataclass."""

    def test_empty_validation(self) -> None:
        """Test creating validation with empty lists."""
        validation = Validation()
        assert validation.must_contain == []
        assert validation.must_not_contain == []

    def test_validation_with_rules(self) -> None:
        """Test creating validation with rules."""
        validation = Validation(
            must_contain=["<step", "/step\\d+/"],
            must_not_contain=["<ask>", "HALT"],
        )
        assert validation.must_contain == ["<step", "/step\\d+/"]
        assert validation.must_not_contain == ["<ask>", "HALT"]


class TestWorkflowPatch:
    """Tests for WorkflowPatch dataclass."""

    def test_valid_workflow_patch(self) -> None:
        """Test creating a valid WorkflowPatch with string transforms."""
        patch = WorkflowPatch(
            config=PatchConfig(name="test", version="1.0.0"),
            compatibility=Compatibility(bmad_version="0.1.0", workflow="create-story"),
            transforms=["Remove step 1 completely"],
        )
        assert patch.config.name == "test"
        assert patch.compatibility.workflow == "create-story"
        assert len(patch.transforms) == 1
        assert patch.transforms[0] == "Remove step 1 completely"
        assert patch.validation is None

    def test_patch_with_multiple_transforms(self) -> None:
        """Test creating a patch with multiple transform instructions."""
        patch = WorkflowPatch(
            config=PatchConfig(name="test", version="1.0.0"),
            compatibility=Compatibility(bmad_version="0.1.0", workflow="test"),
            transforms=[
                "Remove all <ask> elements",
                "Simplify the instructions section",
                "Renumber steps starting from 1",
            ],
        )
        assert len(patch.transforms) == 3
        assert "Remove all" in patch.transforms[0]
        assert "Simplify" in patch.transforms[1]
        assert "Renumber" in patch.transforms[2]

    def test_patch_with_validation(self) -> None:
        """Test creating a patch with validation rules."""
        patch = WorkflowPatch(
            config=PatchConfig(name="test", version="1.0.0"),
            compatibility=Compatibility(bmad_version="0.1.0", workflow="test"),
            transforms=["Remove unused elements"],
            validation=Validation(must_contain=["<step"]),
        )
        assert patch.validation is not None
        assert patch.validation.must_contain == ["<step"]

    def test_patch_empty_transforms_raises_error(self) -> None:
        """Test that a patch with empty transforms raises validation error."""
        with pytest.raises(ValidationError):
            WorkflowPatch(
                config=PatchConfig(name="test", version="1.0.0"),
                compatibility=Compatibility(bmad_version="0.1.0", workflow="test"),
                transforms=[],
            )

    def test_patch_empty_instruction_raises_error(self) -> None:
        """Test that an empty instruction string raises validation error."""
        with pytest.raises(ValidationError):
            WorkflowPatch(
                config=PatchConfig(name="test", version="1.0.0"),
                compatibility=Compatibility(bmad_version="0.1.0", workflow="test"),
                transforms=["Valid instruction", ""],
            )


class TestPatchError:
    """Tests for PatchError exception."""

    def test_patch_error_basic(self) -> None:
        """Test basic PatchError creation."""
        error = PatchError("Test error message")
        assert str(error) == "Test error message"

    def test_patch_error_inherits_from_compiler_error(self) -> None:
        """Test that PatchError inherits from CompilerError."""
        from bmad_assist.core.exceptions import CompilerError

        error = PatchError("Test")
        assert isinstance(error, CompilerError)

    def test_patch_error_can_be_raised(self) -> None:
        """Test that PatchError can be raised and caught."""
        with pytest.raises(PatchError) as exc_info:
            raise PatchError("Invalid patch YAML")
        assert "Invalid patch YAML" in str(exc_info.value)
