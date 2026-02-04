"""Prompt formatting for workflow patches.

This module handles formatting prompts for LLM to apply transforms
to workflow content. Transforms are simple instruction strings.

Also includes post-processing for deterministic cleanups that don't
need LLM (removing redundant file references, etc.).
"""

import logging
import re
import xml.etree.ElementTree as ET

from bmad_assist.compiler.patching.config import get_patcher_config
from bmad_assist.compiler.patching.types import PostProcessRule

logger = logging.getLogger(__name__)


# Pattern to match < that should be escaped (not part of XML tags)
# Matches < followed by: digit, space, =, or other comparison context
_UNESCAPED_LT_PATTERN = re.compile(r"<(\d|[=\s])")


def fix_xml_entities(content: str) -> str:
    """Fix unescaped < characters in XML text content.

    LLMs sometimes convert &lt; back to < when transforming XML.
    This function attempts to fix such cases by escaping < characters
    that appear in text content (not as part of XML tags).

    Heuristic: < followed by digit, space, or = is likely text content
    that should be escaped. < followed by letter or / is likely a tag.

    Args:
        content: XML content that may have unescaped < in text.

    Returns:
        Content with problematic < characters escaped to &lt;

    """
    # First check if XML is already valid
    try:
        # Wrap in root element for parsing (content may have multiple roots)
        ET.fromstring(f"<root>{content}</root>")
        return content  # Already valid, no fix needed
    except ET.ParseError:
        pass  # Need to fix

    # Fix < characters that appear to be in text content
    # Pattern: < followed by digit, space, or = (comparison operators)
    fixed = _UNESCAPED_LT_PATTERN.sub(r"&lt;\1", content)

    # Verify fix worked
    try:
        ET.fromstring(f"<root>{fixed}</root>")
        logger.info("Fixed unescaped < characters in XML content")
        return fixed
    except ET.ParseError as e:
        # Fix didn't work, return original and let caller handle error
        logger.warning("Could not auto-fix XML content: %s", e)
        return content


# Map of flag names to re module constants
_FLAG_MAP = {
    "IGNORECASE": re.IGNORECASE,
    "I": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "M": re.MULTILINE,
    "DOTALL": re.DOTALL,
    "S": re.DOTALL,
}


def _parse_flags(flags_str: str) -> int:
    """Parse flags string into re module flags.

    Args:
        flags_str: Space or comma separated flag names (e.g., "MULTILINE IGNORECASE").

    Returns:
        Combined re flags integer.

    """
    if not flags_str:
        return 0

    combined = 0
    for flag_name in re.split(r"[,\s]+", flags_str.upper()):
        flag_name = flag_name.strip()
        if flag_name and flag_name in _FLAG_MAP:
            combined |= _FLAG_MAP[flag_name]
    return combined


def post_process_compiled(
    content: str,
    rules: list[PostProcessRule] | None = None,
) -> str:
    """Apply deterministic post-processing to compiled workflow.

    Applies regex-based replacements defined in patch config to remove
    redundant file references and other cleanup. Rules are defined in
    the patch YAML post_process section.

    Args:
        content: LLM-transformed workflow content.
        rules: List of PostProcessRule from patch config. If None, no processing.

    Returns:
        Post-processed content with rules applied.

    """
    if rules is None:
        return content

    for rule in rules:
        try:
            flags = _parse_flags(rule.flags)
            pattern = re.compile(rule.pattern, flags)
            content = pattern.sub(rule.replacement, content)
        except re.error as e:
            logger.warning(
                "Invalid post_process regex pattern '%s': %s",
                rule.pattern,
                e,
            )
            continue

    # Clean up multiple blank lines that may result from removals
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content


def format_transform_prompt(
    instructions: list[str],
    workflow_content: str,
) -> str:
    """Format all transform instructions into a single prompt for LLM.

    Args:
        instructions: List of natural language transform instructions.
        workflow_content: The source workflow content to transform.

    Returns:
        Formatted prompt string with all instructions.

    """
    config = get_patcher_config()
    parts = []

    # System context from config
    parts.append("<task-context>")
    parts.append(config.system_prompt.strip())
    parts.append("</task-context>")
    parts.append("")

    # Source document
    parts.append("<source-document>")
    parts.append(workflow_content)
    parts.append("</source-document>")
    parts.append("")

    # Instructions
    parts.append("<instructions>")
    parts.append("Apply these changes IN ORDER:")
    parts.append("")

    for i, instruction in enumerate(instructions, 1):
        parts.append(f"{i}. {instruction}")

    parts.append("")
    parts.append("</instructions>")
    parts.append("")

    # Output format from config
    parts.append("<output-format>")
    parts.append(config.output_format.strip())
    parts.append("</output-format>")

    return "\n".join(parts)
