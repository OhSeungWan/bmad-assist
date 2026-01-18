"""Variable utilities for BMAD workflow compiler.

This module provides utilities for variable substitution and filtering
in compiled workflow prompts.

Key features:
- Substitutes {{var}} and {var} placeholders with resolved values
- Handles dict values with _value metadata (extracts the actual value)
- Filters garbage variables from post_process artifacts

Public API:
    substitute_variables: Replace variable placeholders in text
    filter_garbage_variables: Remove invalid variable entries
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def filter_garbage_variables(variables: dict[str, Any]) -> dict[str, Any]:
    """Filter out garbage variables that shouldn't be in final output.

    Removes variables with names that:
    - Start with '(' (e.g., "(sprint status managed programmatically)")
    - End with ')'
    - Are empty strings as keys

    These typically come from workflow YAML placeholders that weren't
    properly resolved or post_process regex replacements.

    Args:
        variables: Dict of variable names to values.

    Returns:
        Filtered dict without garbage variables.

    """
    garbage_keys = [k for k in variables if k.startswith("(") or k.endswith(")") or k == ""]

    if garbage_keys:
        logger.debug("Filtering out %d garbage variables: %s", len(garbage_keys), garbage_keys)

    return {k: v for k, v in variables.items() if k not in garbage_keys}


# Patterns for variable substitution
_DOUBLE_BRACE_PATTERN = re.compile(r"{{([a-zA-Z_][a-zA-Z0-9_-]*)}}")
_SINGLE_BRACE_PATTERN = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_-]*)}")


def substitute_variables(text: str, variables: dict[str, Any]) -> str:
    """Substitute variable placeholders in text with resolved values.

    Replaces both {{var}} and {var} patterns with their values from
    the variables dict. Unknown variables are left as-is.

    Handles special cases:
    - None values are replaced with empty string
    - Dict values with '_value' key: extracts the value (used for
      variables with metadata like token counts)

    Args:
        text: Text containing variable placeholders.
        variables: Dict mapping variable names to their resolved values.
            Values can be strings, None, or dicts with '_value' key.

    Returns:
        Text with known variables substituted, unknown ones preserved.

    """

    def replace_var(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in variables:
            value = variables[var_name]
            if value is None:
                return ""
            # Handle dict values with _value key (e.g., project_context with metadata)
            if isinstance(value, dict) and "_value" in value:
                return str(value["_value"])
            return str(value)
        return match.group(0)

    result = _DOUBLE_BRACE_PATTERN.sub(replace_var, text)
    result = _SINGLE_BRACE_PATTERN.sub(replace_var, result)
    return result
