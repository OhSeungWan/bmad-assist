"""Provenance utilities for config route handlers.

Provides config source tracking and editor creation.
"""

from typing import Any

from starlette.requests import Request

from bmad_assist.core.config import GLOBAL_CONFIG_PATH, PROJECT_CONFIG_NAME
from bmad_assist.core.config_editor import ConfigEditor


def _validate_path_exists(path: str, schema: dict[str, Any]) -> tuple[bool, str]:
    """Check if a path exists in the schema and is a leaf field.

    Args:
        path: Dot-notation path to validate.
        schema: Schema to check against.

    Returns:
        Tuple of (is_valid: bool, error_message: str).

    """
    parts = path.split(".")
    current = schema

    for i, part in enumerate(parts):
        if not isinstance(current, dict):
            return False, f"Path '{'.'.join(parts[:i])}' is not a valid section"

        if part not in current:
            return False, f"Field not found: {path}"

        field_info = current[part]

        if not isinstance(field_info, dict):
            return False, f"Invalid schema structure at '{part}'"

        # If this is the last part, check it's a leaf field (not a section)
        if i == len(parts) - 1:
            # A leaf field has a "security" attribute or is an array type
            if "security" in field_info or field_info.get("type") == "array":
                return True, ""
            # Otherwise it's a section (nested model without security attribute)
            return False, f"Path '{path}' is a section, not a leaf field"

        # Handle arrays
        if field_info.get("type") == "array":
            current = field_info.get("items", {})
        elif "security" in field_info:
            # This is a leaf field, but we need to go deeper - invalid path
            return (
                False,
                f"'{'.'.join(parts[: i + 1])}' is a leaf field, cannot access '{parts[i + 1]}'",
            )
        else:
            # Nested object
            current = field_info

    return True, ""


def _create_config_editor(request: Request) -> ConfigEditor:
    """Create ConfigEditor instance with proper paths from request context.

    Args:
        request: Starlette request with server in app.state.

    Returns:
        Configured ConfigEditor instance.

    """
    server = request.app.state.server
    project_path = server.project_root / PROJECT_CONFIG_NAME

    editor = ConfigEditor(
        global_path=GLOBAL_CONFIG_PATH,
        project_path=project_path if project_path.exists() else None,
    )
    editor.load()
    return editor


def _add_provenance_to_raw(
    data: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    """Add provenance info to raw config data where all values are from same source.

    Args:
        data: Raw config data.
        source: Source identifier ("global" or "project").

    Returns:
        Data with values wrapped in {"value": X, "source": source}.

    """
    result: dict[str, Any] = {}

    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _add_provenance_to_raw(value, source)
        else:
            result[key] = {"value": value, "source": source}

    return result


def _strip_provenance(merged_with_provenance: dict[str, Any]) -> dict[str, Any]:
    """Remove provenance metadata from get_merged_with_provenance() output.

    Provenance format: {"key": {"value": X, "source": "default|global|project"}}
    Returns: {"key": X} - clean dict with only values.

    Recursively handles nested dicts. If a dict has exactly "value" and "source"
    keys, extract the "value". Otherwise recurse into nested structure.

    Args:
        merged_with_provenance: Config data with provenance wrappers.

    Returns:
        Clean dict with only values (no provenance metadata).

    """
    result: dict[str, Any] = {}
    for key, val in merged_with_provenance.items():
        if isinstance(val, dict):
            if "value" in val and "source" in val and len(val) == 2:
                # Provenance wrapper - extract value
                result[key] = val["value"]
            else:
                # Nested config section - recurse
                result[key] = _strip_provenance(val)
        else:
            result[key] = val
    return result
