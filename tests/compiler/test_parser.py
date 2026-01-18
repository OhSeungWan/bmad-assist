"""Tests for compiler parser module.

Tests cover:
- YAML configuration parsing (valid, malformed, empty)
- XML instructions parsing (valid, malformed)
- Unified workflow parsing
- Template path extraction
- Placeholder preservation
- Edge cases (Unicode, empty files, missing files)
- Error handling with context (line numbers, suggestions)
"""

from pathlib import Path

import pytest

from bmad_assist.compiler import WorkflowIR, parse_workflow
from bmad_assist.compiler.parser import (
    parse_workflow_config,
    parse_workflow_instructions,
)
from bmad_assist.core.exceptions import ParserError

# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "compiler"
VALID_WORKFLOW_DIR = FIXTURES_DIR / "valid_workflow"
MALFORMED_YAML_DIR = FIXTURES_DIR / "malformed_yaml"
MALFORMED_XML_DIR = FIXTURES_DIR / "malformed_xml"
NO_TEMPLATE_DIR = FIXTURES_DIR / "no_template"
EMPTY_YAML_DIR = FIXTURES_DIR / "empty_yaml"
UNICODE_DIR = FIXTURES_DIR / "unicode_content"


class TestParseWorkflowConfig:
    """Test parse_workflow_config function."""

    def test_parse_valid_yaml(self) -> None:
        """parse_workflow_config returns dict from valid YAML."""
        config = parse_workflow_config(VALID_WORKFLOW_DIR / "workflow.yaml")
        assert isinstance(config, dict)
        assert config["name"] == "test-workflow"
        assert "description" in config

    def test_preserves_placeholders(self) -> None:
        """Variable placeholders are preserved as-is (not resolved)."""
        config = parse_workflow_config(VALID_WORKFLOW_DIR / "workflow.yaml")
        # {config_source}: references should be raw strings
        assert config["output_folder"] == "{config_source}:output_folder"
        assert config["user_name"] == "{config_source}:user_name"
        # {project-root} should be preserved
        assert "{project-root}" in config["config_source"]
        # {installed_path} should be preserved
        assert "{installed_path}" in config["instructions"]

    def test_malformed_yaml_raises_parser_error(self) -> None:
        """ParserError raised with line info for malformed YAML."""
        with pytest.raises(ParserError) as exc_info:
            parse_workflow_config(MALFORMED_YAML_DIR / "workflow.yaml")

        error_msg = str(exc_info.value)
        assert "workflow.yaml" in error_msg
        assert "line" in error_msg.lower()  # Line number included

    def test_malformed_yaml_includes_suggestion(self) -> None:
        """ParserError includes fix suggestion for YAML errors."""
        with pytest.raises(ParserError) as exc_info:
            parse_workflow_config(MALFORMED_YAML_DIR / "workflow.yaml")

        error_msg = str(exc_info.value)
        assert "suggestion" in error_msg.lower()

    def test_empty_yaml_returns_empty_dict(self) -> None:
        """Empty YAML file returns empty dict (AC6)."""
        config = parse_workflow_config(EMPTY_YAML_DIR / "workflow.yaml")
        assert config == {}

    def test_missing_file_raises_parser_error(self) -> None:
        """ParserError raised when config file doesn't exist."""
        with pytest.raises(ParserError) as exc_info:
            parse_workflow_config(FIXTURES_DIR / "nonexistent" / "workflow.yaml")

        assert "not found" in str(exc_info.value).lower()

    def test_unicode_preserved(self) -> None:
        """Unicode characters in YAML are preserved correctly (AC6)."""
        config = parse_workflow_config(UNICODE_DIR / "workflow.yaml")
        assert config["user_name"] == "Paweł"
        assert config["greeting"] == "日本語テスト"
        assert config["german"] == "Schöne Grüße"


class TestParseWorkflowInstructions:
    """Test parse_workflow_instructions function."""

    def test_parse_valid_xml(self) -> None:
        """parse_workflow_instructions returns XML string from valid file."""
        xml_content = parse_workflow_instructions(VALID_WORKFLOW_DIR / "instructions.xml")
        assert isinstance(xml_content, str)
        assert "<workflow>" in xml_content
        assert "<step" in xml_content

    def test_returns_raw_string(self) -> None:
        """XML is returned as raw string, not parsed tree."""
        xml_content = parse_workflow_instructions(VALID_WORKFLOW_DIR / "instructions.xml")
        # Should contain original XML text including whitespace
        assert "Perform first action" in xml_content
        assert "template-output" in xml_content

    def test_malformed_xml_raises_parser_error(self) -> None:
        """ParserError raised with context for malformed XML."""
        with pytest.raises(ParserError) as exc_info:
            parse_workflow_instructions(MALFORMED_XML_DIR / "instructions.xml")

        error_msg = str(exc_info.value)
        assert "instructions.xml" in error_msg

    def test_malformed_xml_includes_suggestion(self) -> None:
        """ParserError includes fix suggestion for XML errors."""
        with pytest.raises(ParserError) as exc_info:
            parse_workflow_instructions(MALFORMED_XML_DIR / "instructions.xml")

        error_msg = str(exc_info.value)
        assert "suggestion" in error_msg.lower()

    def test_missing_file_raises_parser_error(self) -> None:
        """ParserError raised when instructions file doesn't exist."""
        with pytest.raises(ParserError) as exc_info:
            parse_workflow_instructions(FIXTURES_DIR / "nonexistent" / "instructions.xml")

        assert "not found" in str(exc_info.value).lower()

    def test_unicode_preserved(self) -> None:
        """Unicode characters in XML are preserved correctly (AC6)."""
        xml_content = parse_workflow_instructions(UNICODE_DIR / "instructions.xml")
        assert "日本語" in xml_content
        assert "Schöne Grüße" in xml_content
        assert "ąęćłńóśźż" in xml_content

    def test_nested_elements_preserved(self) -> None:
        """Nested XML elements are preserved in raw string (AC6)."""
        xml_content = parse_workflow_instructions(VALID_WORKFLOW_DIR / "instructions.xml")
        # Verify nested structure is preserved
        assert "<check if=" in xml_content
        assert "</check>" in xml_content


class TestParseWorkflow:
    """Test unified parse_workflow function."""

    def test_returns_workflow_ir(self) -> None:
        """parse_workflow returns complete WorkflowIR."""
        ir = parse_workflow(VALID_WORKFLOW_DIR)

        assert isinstance(ir, WorkflowIR)
        assert ir.config_path == (VALID_WORKFLOW_DIR / "workflow.yaml").resolve()
        assert ir.instructions_path == (VALID_WORKFLOW_DIR / "instructions.xml").resolve()
        assert isinstance(ir.raw_config, dict)
        assert isinstance(ir.raw_instructions, str)

    def test_workflow_name_from_config(self) -> None:
        """Workflow name extracted from config 'name' key."""
        ir = parse_workflow(VALID_WORKFLOW_DIR)
        assert ir.name == "test-workflow"

    def test_workflow_name_fallback_to_directory(self) -> None:
        """Workflow name falls back to directory name if 'name' key absent."""
        ir = parse_workflow(EMPTY_YAML_DIR)
        # Empty YAML has no 'name' key, should use directory name
        assert ir.name == "empty_yaml"

    def test_template_path_string(self) -> None:
        """WorkflowIR includes template_path when template specified as string."""
        ir = parse_workflow(VALID_WORKFLOW_DIR)
        assert ir.template_path is not None
        assert ir.template_path == "{installed_path}/template.md"

    def test_template_path_false(self) -> None:
        """WorkflowIR has None template_path when template: false."""
        ir = parse_workflow(NO_TEMPLATE_DIR)
        assert ir.template_path is None

    def test_template_path_absent(self) -> None:
        """WorkflowIR has None template_path when template key absent."""
        ir = parse_workflow(EMPTY_YAML_DIR)
        assert ir.template_path is None

    def test_missing_workflow_yaml(self) -> None:
        """ParserError raised when workflow.yaml missing (AC6)."""
        with pytest.raises(ParserError) as exc_info:
            parse_workflow(FIXTURES_DIR / "nonexistent")
        assert "workflow.yaml" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    def test_missing_instructions_xml(self, tmp_path: Path) -> None:
        """ParserError raised when instructions file missing (AC6)."""
        # Create directory with only workflow.yaml
        (tmp_path / "workflow.yaml").write_text("name: test\n")

        with pytest.raises(ParserError) as exc_info:
            parse_workflow(tmp_path)
        assert "instructions.xml" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    def test_placeholders_preserved_in_config(self) -> None:
        """Placeholders in raw_config are preserved (not resolved)."""
        ir = parse_workflow(VALID_WORKFLOW_DIR)
        assert ir.raw_config["output_folder"] == "{config_source}:output_folder"
        assert "{project-root}" in ir.raw_config["config_source"]

    def test_raw_instructions_contains_xml(self) -> None:
        """raw_instructions contains validated XML string."""
        ir = parse_workflow(VALID_WORKFLOW_DIR)
        assert "<workflow>" in ir.raw_instructions
        assert "<step" in ir.raw_instructions
        assert "</workflow>" in ir.raw_instructions

    def test_workflow_ir_is_frozen(self) -> None:
        """WorkflowIR is immutable (frozen dataclass)."""
        ir = parse_workflow(VALID_WORKFLOW_DIR)
        with pytest.raises(AttributeError):
            ir.name = "modified"  # type: ignore[misc]

    def test_deterministic_parsing(self) -> None:
        """Same input produces identical output (NFR11)."""
        ir1 = parse_workflow(VALID_WORKFLOW_DIR)
        ir2 = parse_workflow(VALID_WORKFLOW_DIR)

        assert ir1.name == ir2.name
        assert ir1.config_path == ir2.config_path
        assert ir1.instructions_path == ir2.instructions_path
        assert ir1.template_path == ir2.template_path
        assert ir1.raw_config == ir2.raw_config
        assert ir1.raw_instructions == ir2.raw_instructions


class TestParseWorkflowEdgeCases:
    """Test edge cases for workflow parsing (AC6)."""

    def test_xml_without_step_elements(self, tmp_path: Path) -> None:
        """XML without <step> elements returns valid raw string."""
        (tmp_path / "workflow.yaml").write_text("name: minimal\n")
        (tmp_path / "instructions.xml").write_text(
            "<workflow><critical>No steps here</critical></workflow>"
        )

        ir = parse_workflow(tmp_path)
        assert "No steps here" in ir.raw_instructions
        assert "<step" not in ir.raw_instructions

    def test_whitespace_only_yaml(self, tmp_path: Path) -> None:
        """YAML with only whitespace returns empty dict."""
        (tmp_path / "workflow.yaml").write_text("   \n\n   \t\n")
        (tmp_path / "instructions.xml").write_text("<workflow></workflow>")

        ir = parse_workflow(tmp_path)
        assert ir.raw_config == {}
        # Name should fall back to directory name
        assert ir.name == tmp_path.name

    def test_large_xml_file(self, tmp_path: Path) -> None:
        """Files up to 1MB parsed without issues (AC6)."""
        (tmp_path / "workflow.yaml").write_text("name: large-xml\n")

        # Create ~100KB XML (well under 1MB but demonstrates capability)
        steps = "\n".join(
            f'  <step n="{i}" goal="Step {i}"><action>Action {i}</action></step>'
            for i in range(1000)
        )
        large_xml = f"<workflow>\n{steps}\n</workflow>"
        (tmp_path / "instructions.xml").write_text(large_xml)

        ir = parse_workflow(tmp_path)
        assert "Step 999" in ir.raw_instructions
        assert ir.name == "large-xml"

    def test_instructions_key_without_placeholder(self, tmp_path: Path) -> None:
        """Instructions key with explicit path (no placeholder) is resolved."""
        (tmp_path / "workflow.yaml").write_text(
            "name: explicit-instructions\ninstructions: my-instructions.xml\n"
        )
        (tmp_path / "my-instructions.xml").write_text("<workflow></workflow>")

        ir = parse_workflow(tmp_path)
        assert ir.instructions_path == (tmp_path / "my-instructions.xml").resolve()


class TestSecurityValidation:
    """Test security validations in parser."""

    def test_yaml_root_list_raises_error(self, tmp_path: Path) -> None:
        """YAML with list root raises ParserError (not dict)."""
        (tmp_path / "workflow.yaml").write_text("- item1\n- item2\n")

        with pytest.raises(ParserError) as exc_info:
            parse_workflow_config(tmp_path / "workflow.yaml")
        assert "mapping" in str(exc_info.value).lower() or "dict" in str(exc_info.value).lower()

    def test_yaml_root_scalar_raises_error(self, tmp_path: Path) -> None:
        """YAML with scalar root raises ParserError (not dict)."""
        (tmp_path / "workflow.yaml").write_text("just a string\n")

        with pytest.raises(ParserError) as exc_info:
            parse_workflow_config(tmp_path / "workflow.yaml")
        assert "mapping" in str(exc_info.value).lower() or "dict" in str(exc_info.value).lower()

    def test_yaml_name_null_uses_directory_fallback(self, tmp_path: Path) -> None:
        """Name falls back to directory when YAML has name: null."""
        workflow_dir = tmp_path / "my-workflow"
        workflow_dir.mkdir()
        (workflow_dir / "workflow.yaml").write_text("name: null\n")
        (workflow_dir / "instructions.xml").write_text("<workflow></workflow>")

        ir = parse_workflow(workflow_dir)
        assert ir.name == "my-workflow"

    def test_yaml_name_wrong_type_uses_directory_fallback(self, tmp_path: Path) -> None:
        """Name falls back to directory when YAML has name: 123."""
        workflow_dir = tmp_path / "numeric-name"
        workflow_dir.mkdir()
        (workflow_dir / "workflow.yaml").write_text("name: 123\n")
        (workflow_dir / "instructions.xml").write_text("<workflow></workflow>")

        ir = parse_workflow(workflow_dir)
        assert ir.name == "numeric-name"

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Path traversal in instructions path is blocked."""
        (tmp_path / "workflow.yaml").write_text('instructions: "../../../etc/passwd"\n')
        (tmp_path / "instructions.xml").write_text("<workflow></workflow>")

        with pytest.raises(ParserError) as exc_info:
            parse_workflow(tmp_path)
        assert "path traversal" in str(exc_info.value).lower()

    def test_absolute_instructions_path_blocked(self, tmp_path: Path) -> None:
        """Absolute path in instructions is blocked."""
        (tmp_path / "workflow.yaml").write_text('instructions: "/etc/passwd"\n')
        (tmp_path / "instructions.xml").write_text("<workflow></workflow>")

        with pytest.raises(ParserError) as exc_info:
            parse_workflow(tmp_path)
        assert "path traversal" in str(exc_info.value).lower()

    def test_xml_doctype_blocked(self, tmp_path: Path) -> None:
        """XML with DOCTYPE declaration is blocked (XML bomb protection)."""
        (tmp_path / "workflow.yaml").write_text("name: test\n")
        (tmp_path / "instructions.xml").write_text(
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE lolz [<!ENTITY lol "lol">]>\n'
            "<workflow>&lol;</workflow>"
        )

        with pytest.raises(ParserError) as exc_info:
            parse_workflow(tmp_path)
        assert "DOCTYPE" in str(exc_info.value) or "ENTITY" in str(exc_info.value)

    def test_xml_entity_blocked(self, tmp_path: Path) -> None:
        """XML with ENTITY declaration is blocked."""
        (tmp_path / "workflow.yaml").write_text("name: test\n")
        (tmp_path / "instructions.xml").write_text('<!ENTITY test "value">\n<workflow></workflow>')

        with pytest.raises(ParserError) as exc_info:
            parse_workflow(tmp_path)
        assert "ENTITY" in str(exc_info.value)


class TestModuleExports:
    """Test that parser functions are properly exported."""

    def test_parse_workflow_importable_from_compiler(self) -> None:
        """parse_workflow is importable from compiler module."""
        from bmad_assist.compiler import parse_workflow as imported_parse

        assert imported_parse is parse_workflow

    def test_parser_error_importable_from_compiler(self) -> None:
        """ParserError is importable from compiler module."""
        from bmad_assist.compiler import ParserError as ImportedError
        from bmad_assist.core.exceptions import ParserError as CoreError

        assert ImportedError is CoreError

    def test_compiler_all_includes_parse_workflow(self) -> None:
        """parse_workflow is in compiler.__all__."""
        from bmad_assist import compiler

        assert "parse_workflow" in compiler.__all__

    def test_compiler_all_includes_parser_error(self) -> None:
        """ParserError is in compiler.__all__."""
        from bmad_assist import compiler

        assert "ParserError" in compiler.__all__
