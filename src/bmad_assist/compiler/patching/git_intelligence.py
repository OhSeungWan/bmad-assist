"""Git intelligence extraction for compile-time embedding.

This module provides functionality to extract git information at compile time
and embed it in the workflow prompt. This prevents LLM from running expensive
git archaeology at runtime.

Key functions:
    is_git_repo: Check if a directory is a git repository
    run_git_command: Execute a git command with variable substitution
    extract_git_intelligence: Run all configured commands and format output
"""

import logging
import re
import subprocess
from pathlib import Path

from bmad_assist.compiler.patching.types import GitIntelligence

logger = logging.getLogger(__name__)

# Timeout for git commands (seconds)
GIT_COMMAND_TIMEOUT = 10

# Max output length per command (characters)
MAX_OUTPUT_LENGTH = 2000


def is_git_repo(path: Path) -> bool:
    """Check if a directory is a git repository ROOT.

    This function checks if `path` is itself the root of a git repository,
    NOT just a subdirectory within one. This is important when the project
    directory is a subdirectory of another git repository (e.g., test fixtures
    inside the main bmad-assist repo).

    Args:
        path: Directory to check.

    Returns:
        True if path is a git repository root, False otherwise.

    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=GIT_COMMAND_TIMEOUT,
        )
        if result.returncode != 0:
            return False

        # Compare the git root with the provided path
        # Both must resolve to the same directory
        git_root = Path(result.stdout.strip()).resolve()
        target_path = path.resolve()

        return git_root == target_path
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _substitute_variables(command: str, variables: dict[str, str | int | None]) -> str:
    """Substitute {{variable}} placeholders in command string.

    Args:
        command: Command string with optional {{variable}} placeholders.
        variables: Dictionary of variable names to values.

    Returns:
        Command string with variables substituted.

    """
    result = command
    for name, value in variables.items():
        # Handle both {{name}} and {{ name }} formats
        pattern = r"\{\{\s*" + re.escape(str(name)) + r"\s*\}\}"
        result = re.sub(pattern, str(value), result)
    return result


def run_git_command(
    command: str,
    cwd: Path,
    variables: dict[str, str | int | None] | None = None,
) -> str:
    """Execute a git command and return output.

    Args:
        command: Git command to execute (e.g., "git log --oneline -5").
        cwd: Working directory for the command.
        variables: Optional variables for substitution in command.

    Returns:
        Command output (stdout), truncated if too long.
        On error, returns error message.

    """
    # Substitute variables
    if variables:
        command = _substitute_variables(command, variables)

    logger.debug("Running git command: %s (cwd=%s)", command, cwd)

    try:
        result = subprocess.run(
            command,
            shell=True,  # Need shell for pipes, grep etc.
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=GIT_COMMAND_TIMEOUT,
        )

        output = result.stdout.strip()

        # Truncate if too long
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + "\n... (truncated)"

        if result.returncode != 0 and result.stderr:
            # Include stderr if command failed
            return f"(command failed: {result.stderr.strip()})"

        return output or "(no output)"

    except subprocess.TimeoutExpired:
        logger.warning("Git command timed out: %s", command)
        return "(command timed out)"
    except OSError as e:
        logger.warning("Git command failed: %s - %s", command, e)
        return f"(command error: {e})"


def extract_git_intelligence(
    config: GitIntelligence,
    project_root: Path,
    variables: dict[str, str | int | None] | None = None,
) -> str:
    """Extract git intelligence and format as embedded content.

    Checks if git is initialized, runs configured commands, and formats
    the output for embedding in the workflow prompt.

    Args:
        config: Git intelligence configuration from patch.
        project_root: Project root directory (for git commands).
        variables: Optional variables for command substitution.

    Returns:
        Formatted string to embed in workflow, wrapped in embed_marker tags.

    """
    if not config.enabled:
        logger.debug("Git intelligence disabled")
        return ""

    marker = config.embed_marker
    parts = [f"<{marker}>"]

    # Check if git is initialized
    if not is_git_repo(project_root):
        logger.info("Project is not a git repository: %s", project_root)
        parts.append(config.no_git_message)
        parts.append(f"</{marker}>")
        return "\n".join(parts)

    # Run each configured command
    parts.append(
        "Git intelligence extracted at compile time. "
        "Do NOT run additional git commands - use this embedded data instead."
    )
    parts.append("")

    for git_cmd in config.commands:
        output = run_git_command(git_cmd.command, project_root, variables)
        parts.append(f"### {git_cmd.name}")
        parts.append("```")
        parts.append(output)
        parts.append("```")
        parts.append("")

    parts.append(f"</{marker}>")

    return "\n".join(parts)
