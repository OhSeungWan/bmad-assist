"""Validation engine for workflow patch output.

This module handles validating compiled workflow output against
must_contain and must_not_contain rules, and checking success thresholds.

Functions:
    is_regex: Check if a pattern is in /pattern/ format
    parse_regex: Parse /pattern/ into compiled regex
    validate_output: Validate content against validation rules
    check_threshold: Check if success rate meets 75% threshold
"""

import re

from bmad_assist.compiler.patching.types import TransformResult, Validation

# Threshold for successful compilation (75%)
SUCCESS_THRESHOLD_PERCENT = 75


def is_regex(pattern: str) -> bool:
    """Check if a pattern is in /pattern/ regex format.

    Regex patterns are detected by surrounding slashes: /pattern/

    Args:
        pattern: The pattern string to check.

    Returns:
        True if pattern is in regex format, False otherwise.

    """
    if len(pattern) < 2:
        return False
    return pattern.startswith("/") and pattern.endswith("/")


def parse_regex(pattern: str) -> re.Pattern[str]:
    """Parse a /pattern/ format string into a compiled regex.

    Extracts the pattern from between slashes and compiles it
    with MULTILINE flag (^ and $ match line boundaries).

    Args:
        pattern: Pattern string in /pattern/ format.

    Returns:
        Compiled regex pattern.

    Raises:
        re.error: If the regex is invalid.

    """
    # Extract pattern between slashes
    inner_pattern = pattern[1:-1]

    # Unescape any escaped slashes
    inner_pattern = inner_pattern.replace(r"\/", "/")

    # Compile with MULTILINE flag
    return re.compile(inner_pattern, re.MULTILINE)


def validate_output(content: str, validation: Validation | None) -> list[str]:
    """Validate content against validation rules.

    Checks must_contain (all must match) and must_not_contain (none may match).

    Args:
        content: The compiled workflow content to validate.
        validation: Validation rules to apply, or None for no validation.

    Returns:
        List of error messages. Empty list means validation passed.

    """
    # Guard against None validation
    if validation is None:
        return []

    errors: list[str] = []

    # Check must_contain rules
    for rule in validation.must_contain:
        if is_regex(rule):
            try:
                pattern = parse_regex(rule)
                if not pattern.search(content):
                    errors.append(f"must_contain regex {rule} not found in output")
            except re.error as e:
                errors.append(f"Invalid regex in must_contain {rule}: {e}")
        else:
            # Substring match (case-sensitive)
            if rule not in content:
                errors.append(f"must_contain substring '{rule}' not found in output")

    # Check must_not_contain rules
    for rule in validation.must_not_contain:
        if is_regex(rule):
            try:
                pattern = parse_regex(rule)
                if pattern.search(content):
                    errors.append(f"must_not_contain regex {rule} found in output")
            except re.error as e:
                errors.append(f"Invalid regex in must_not_contain {rule}: {e}")
        else:
            # Substring match (case-sensitive)
            if rule in content:
                errors.append(f"must_not_contain substring '{rule}' found in output")

    return errors


def check_threshold(results: list[TransformResult]) -> bool:
    """Check if transform success rate meets 75% threshold.

    Uses floor division for percentage calculation.

    Args:
        results: List of transform results.

    Returns:
        True if success rate >= 75%, False otherwise.

    """
    if not results:
        # No transforms = consider it a pass (nothing to fail)
        return True

    successful = sum(1 for r in results if r.success)
    total = len(results)

    # Use floor division for percentage (per AC5)
    success_rate = (successful * 100) // total

    return success_rate >= SUCCESS_THRESHOLD_PERCENT
