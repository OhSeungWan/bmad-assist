"""Path resolution for BMAD workflow variables.

This module handles path-related variable resolution:
- {project-root} placeholder resolution
- {installed_path} placeholder resolution
- External config loading with security validation

Dependencies flow: paths.py has no dependencies on other variables/ modules.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from bmad_assist.compiler.types import CompilerContext, WorkflowIR
from bmad_assist.core.exceptions import VariableError

logger = logging.getLogger(__name__)

__all__ = [
    "_resolve_path_placeholders",
    "_validate_config_path",
    "_load_external_config",
]


def _resolve_path_placeholders(
    value: str,
    context: CompilerContext,
    workflow_ir: WorkflowIR,
) -> str:
    """Resolve path placeholders in a string value.

    Handles:
    - {project-root} → context.project_root
    - {installed_path} → parent directory of workflow_ir.config_path

    Args:
        value: String potentially containing path placeholders.
        context: Compiler context with project_root.
        workflow_ir: Workflow IR with config_path.

    Returns:
        String with path placeholders resolved.

    """
    result = value

    # Resolve {project-root}
    if "{project-root}" in result:
        result = result.replace("{project-root}", str(context.project_root))

    # Resolve {installed_path}
    if "{installed_path}" in result:
        installed_path = workflow_ir.config_path.parent
        result = result.replace("{installed_path}", str(installed_path))

    return result


def _validate_config_path(config_path: Path, project_root: Path) -> None:
    """Validate config path is within project root (security).

    Uses Path.is_relative_to() for safe containment check.
    This prevents path traversal attacks like /project/root2 passing
    when project_root is /project/root (which startswith would allow).

    Args:
        config_path: Path to validate.
        project_root: Project root directory.

    Raises:
        VariableError: If path traversal detected.

    """
    try:
        resolved_path = config_path.resolve()
        resolved_root = project_root.resolve()

        # Check for path traversal patterns in the original path
        original_str = str(config_path)
        if ".." in original_str:
            raise VariableError(
                f"Path security violation: {config_path}\n"
                f"  Project root: {project_root}\n"
                f"  Reason: Path traversal detected (..)\n"
                f"  Suggestion: Use paths within the project directory",
                variable_name="config_source",
                sources_checked=["security validation"],
                suggestion="Use paths within the project directory",
            )

        # Use is_relative_to() for safe containment check (Python 3.9+)
        # This correctly rejects /project/root2 when root is /project/root
        if not resolved_path.is_relative_to(resolved_root):
            raise VariableError(
                f"Path security violation: {config_path}\n"
                f"  Project root: {project_root}\n"
                f"  Reason: Path outside project boundary\n"
                f"  Suggestion: Use paths within the project directory",
                variable_name="config_source",
                sources_checked=["security validation"],
                suggestion="Use paths within the project directory",
            )
    except ValueError:
        # is_relative_to() raises ValueError on Windows when paths are on different drives
        raise VariableError(
            f"Path security violation: {config_path}\n"
            f"  Project root: {project_root}\n"
            f"  Reason: Path outside project boundary (different drive)\n"
            f"  Suggestion: Use paths within the project directory",
            variable_name="config_source",
            sources_checked=["security validation"],
            suggestion="Use paths within the project directory",
        ) from None
    except OSError as e:
        raise VariableError(
            f"Cannot validate config source path: {config_path}\n"
            f"  Error: {e}\n"
            f"  Suggestion: Check path permissions and format",
            variable_name="config_source",
            suggestion="Check path permissions and format",
        ) from e


def _load_external_config(config_path: Path) -> dict[str, Any]:
    """Load external YAML config file.

    Args:
        config_path: Path to YAML config file.

    Returns:
        Parsed config as dictionary.

    Raises:
        VariableError: If file cannot be read or parsed.

    """
    try:
        content = config_path.read_text(encoding="utf-8")
    except OSError as e:
        raise VariableError(
            f"Cannot read config file: {config_path}\n"
            f"  Error: {e}\n"
            f"  Suggestion: Check file permissions and path",
            variable_name="config_source",
            suggestion="Check file permissions and path",
        ) from e

    try:
        result = yaml.safe_load(content)
        if result is None:
            return {}
        if not isinstance(result, dict):
            raise VariableError(
                f"Invalid config file: {config_path}\n"
                f"  Root element must be a mapping (dict), got {type(result).__name__}\n"
                f"  Suggestion: Ensure config file is key: value format",
                variable_name="config_source",
                suggestion="Ensure config file is key: value format",
            )
        return result
    except yaml.YAMLError as e:
        raise VariableError(
            f"Invalid YAML in config file: {config_path}\n"
            f"  Error: {e}\n"
            f"  Suggestion: Check YAML syntax",
            variable_name="config_source",
            suggestion="Check YAML syntax",
        ) from e
