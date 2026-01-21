"""Compiler for the dev-story workflow.

This module implements the WorkflowCompiler protocol for the dev-story
workflow, producing standalone prompts for story implementation with
all necessary context embedded.

Public API:
    DevStoryCompiler: Workflow compiler class implementing WorkflowCompiler protocol
    DEFAULT_SOURCE_FILES_TOKEN_BUDGET: Token budget for source files from File List
"""

import logging
import re
from pathlib import Path
from typing import Any

from bmad_assist.compiler.filtering import filter_instructions
from bmad_assist.compiler.output import generate_output
from bmad_assist.compiler.shared_utils import (
    apply_post_process,
    context_snapshot,
    estimate_tokens,
    find_epic_file,
    find_file_in_output_folder,
    find_file_in_planning_dir,
    find_project_context_file,
    find_sprint_status_file,
    resolve_story_file,
    safe_read_file,
)
from bmad_assist.compiler.types import CompiledWorkflow, CompilerContext, WorkflowIR
from bmad_assist.compiler.variable_utils import substitute_variables
from bmad_assist.compiler.variables import resolve_variables
from bmad_assist.core.exceptions import CompilerError

logger = logging.getLogger(__name__)

# Workflow path relative to project root
_WORKFLOW_RELATIVE_PATH = "_bmad/bmm/workflows/4-implementation/dev-story"

# Default token budget for source files from File List (AC3)
DEFAULT_SOURCE_FILES_TOKEN_BUDGET = 20000


# Pattern for File List section header
_FILE_LIST_HEADER = re.compile(r"^#{2,3}\s*File\s+List\s*$", re.MULTILINE | re.IGNORECASE)

# Pattern for file paths in markdown lists (supports backticks and plain paths)
# Note: longer extensions must come before shorter ones (tsx before ts, etc.)
_FILE_PATH_PATTERN = re.compile(
    r"^\s*[-*]\s*`?([^`\s]+\."
    r"(py|tsx|ts|jsx|js|yaml|yml|json|md|sql|sh|go|rs|java|kt|swift|rb|php|cpp|hpp|c|h))`?",
    re.MULTILINE,
)


def _extract_file_paths_from_story(story_content: str) -> list[str]:
    """Extract file paths from File List section in story content.

    Parses the "## File List" or "### File List" section and extracts
    file paths from markdown list items like:
    - `src/module/file.py` - Description
    - src/other/file.ts

    Args:
        story_content: Full story file content.

    Returns:
        List of file paths found in the File List section.

    """
    header_match = _FILE_LIST_HEADER.search(story_content)
    if not header_match:
        return []

    section_start = header_match.end()
    next_section = re.search(r"^#{2,3}\s+\w", story_content[section_start:], re.MULTILINE)
    if next_section:
        section_content = story_content[section_start : section_start + next_section.start()]
    else:
        section_content = story_content[section_start:]

    paths: list[str] = []
    for match in _FILE_PATH_PATTERN.finditer(section_content):
        path = match.group(1).strip()
        if path and not path.startswith("#"):
            paths.append(path)

    return paths


class DevStoryCompiler:
    """Compiler for the dev-story workflow.

    Implements the WorkflowCompiler protocol to compile the dev-story
    workflow into a standalone prompt. The dev-story workflow is an
    action-workflow (no template output), focused on implementing
    stories with all necessary context embedded.

    Context embedding follows recency-bias ordering:
    1. project_context.md (general)
    2. prd.md (full, no filtering)
    3. ux.md (optional)
    4. architecture.md (technical)
    5. epic file (current epic)
    6. source files from File List (with token budget)
    7. story file (LAST - closest to instructions)

    """

    @property
    def workflow_name(self) -> str:
        """Unique workflow identifier."""
        return "dev-story"

    def get_required_files(self) -> list[str]:
        """Return list of required file glob patterns.

        Returns:
            Glob patterns for files needed by dev-story workflow.

        """
        return [
            "**/project_context.md",
            "**/project-context.md",
            "**/architecture*.md",
            "**/prd*.md",
            "**/ux*.md",
            "**/sprint-status.yaml",
            "**/epic*.md",
        ]

    def get_variables(self) -> dict[str, Any]:
        """Return workflow-specific variables to resolve.

        Returns:
            Variables needed for dev-story compilation.

        """
        return {
            "epic_num": None,
            "story_num": None,
            "story_key": None,
            "story_id": None,
            "story_file": None,
            "story_title": None,
            "date": None,
        }

    def get_workflow_dir(self, context: CompilerContext) -> Path:
        """Return the workflow directory for this compiler.

        Args:
            context: The compilation context with project paths.

        Returns:
            Path to the workflow directory containing workflow.yaml.

        Raises:
            CompilerError: If workflow directory not found.

        """
        from bmad_assist.compiler.workflow_discovery import (
            discover_workflow_dir,
            get_workflow_not_found_message,
        )

        workflow_dir = discover_workflow_dir(self.workflow_name, context.project_root)
        if workflow_dir is None:
            raise CompilerError(
                get_workflow_not_found_message(self.workflow_name, context.project_root)
            )
        return workflow_dir

    def validate_context(self, context: CompilerContext) -> None:
        """Validate context before compilation.

        Args:
            context: The compilation context to validate.

        Raises:
            CompilerError: If required context is missing.

        """
        if context.project_root is None:
            raise CompilerError("project_root is required in context")
        if context.output_folder is None:
            raise CompilerError("output_folder is required in context")

        epic_num = context.resolved_variables.get("epic_num")
        story_num = context.resolved_variables.get("story_num")

        if epic_num is None:
            raise CompilerError(
                "epic_num is required for dev-story compilation.\n"
                "  Suggestion: Provide epic_num via invocation params or ensure "
                "sprint-status.yaml has a ready-for-dev story"
            )
        if story_num is None:
            raise CompilerError(
                "story_num is required for dev-story compilation.\n"
                "  Suggestion: Provide story_num via invocation params or ensure "
                "sprint-status.yaml has a ready-for-dev story"
            )

        # Workflow directory is validated by get_workflow_dir via discovery
        workflow_dir = self.get_workflow_dir(context)
        if not workflow_dir.exists():
            raise CompilerError(
                f"Workflow directory not found: {workflow_dir}\n"
                f"  Why it's needed: Contains workflow.yaml and instructions.xml\n"
                f"  How to fix: Reinstall bmad-assist or ensure BMAD is properly installed"
            )

        story_path, _, _ = resolve_story_file(context, epic_num, story_num)
        if story_path is None:
            raise CompilerError(
                f"Story file not found for {epic_num}-{story_num}-*.md\n"
                f"  Expected pattern: docs/sprint-artifacts/{epic_num}-{story_num}-*.md\n"
                f"  Suggestion: Run 'create-story' workflow first to create the story"
            )

    def compile(self, context: CompilerContext) -> CompiledWorkflow:
        """Compile dev-story workflow with given context.

        Executes the full compilation pipeline:
        1. Use pre-loaded workflow_ir from context
        2. Resolve variables with sprint-status lookup
        3. Build context files with recency-bias ordering (story LAST)
        4. Filter instructions
        5. Generate XML output

        Args:
            context: The compilation context with:
                - workflow_ir: Pre-loaded WorkflowIR
                - patch_path: Path to patch file (for post_process)

        Returns:
            CompiledWorkflow ready for output.

        Raises:
            CompilerError: If compilation fails at any stage.

        """
        workflow_ir = context.workflow_ir
        if workflow_ir is None:
            raise CompilerError(
                "workflow_ir not set in context. This is a bug - core.py should have loaded it."
            )

        workflow_dir = self.get_workflow_dir(context)

        with context_snapshot(context):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Using workflow from %s", workflow_dir)

            invocation_params = {
                k: v
                for k, v in context.resolved_variables.items()
                if k in ("epic_num", "story_num", "story_title", "date")
            }

            sprint_status_path = find_sprint_status_file(context)

            epic_num = invocation_params.get("epic_num")
            epics_path = find_epic_file(context, epic_num) if epic_num else None

            resolved = resolve_variables(context, invocation_params, sprint_status_path, epics_path)

            story_path, story_key, _ = resolve_story_file(
                context,
                resolved.get("epic_num"),
                resolved.get("story_num"),
            )
            if story_path:
                resolved["story_file"] = str(story_path)
            if story_key:
                resolved["story_key"] = story_key

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Resolved %d variables", len(resolved))

            context_files = self._build_context_files(context, resolved)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Built context with %d files", len(context_files))

            filtered_instructions = filter_instructions(workflow_ir)
            filtered_instructions = substitute_variables(filtered_instructions, resolved)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Filtered instructions: %d bytes", len(filtered_instructions))

            mission = self._build_mission(workflow_ir, resolved)

            compiled = CompiledWorkflow(
                workflow_name=self.workflow_name,
                mission=mission,
                context="",
                variables=resolved,
                instructions=filtered_instructions,
                output_template="",  # action-workflow, no template
                token_estimate=0,
            )

            result = generate_output(
                compiled,
                project_root=context.project_root,
                context_files=context_files,
                links_only=context.links_only,
            )

            final_xml = apply_post_process(result.xml, context)

            return CompiledWorkflow(
                workflow_name=self.workflow_name,
                mission=mission,
                context=final_xml,
                variables=resolved,
                instructions=filtered_instructions,
                output_template="",
                token_estimate=result.token_estimate,
            )

    def _build_context_files(
        self,
        context: CompilerContext,
        resolved: dict[str, Any],
    ) -> dict[str, str]:
        """Build context files dict with recency-bias ordering.

        Files are ordered from general (early) to specific (late):
        1. project_context.md (general)
        2. prd.md (full, no filtering)
        3. ux.md (if exists)
        4. architecture.md (technical)
        5. epic file (current epic)
        6. source files from File List (with token budget)
        7. story file (LAST - closest to instructions)

        Args:
            context: Compilation context with paths.
            resolved: Resolved variables containing epic_num and story_num.

        Returns:
            Dictionary mapping file paths to content, ordered by recency-bias.

        """
        files: dict[str, str] = {}
        project_root = context.project_root

        # 1. Project context (general)
        project_context_path = find_project_context_file(context)
        if project_context_path:
            content = safe_read_file(project_context_path, project_root)
            if content:
                files[str(project_context_path)] = content

        # 2. PRD (full, no epic-specific filtering) - search in planning_artifacts (docs/)
        prd_path = find_file_in_planning_dir(context, "*prd*.md")
        if prd_path:
            content = safe_read_file(prd_path, project_root)
            if content:
                files[str(prd_path)] = content

        # 3. UX (optional) - search in planning_artifacts (docs/)
        ux_path = find_file_in_planning_dir(context, "*ux*.md")
        if ux_path:
            content = safe_read_file(ux_path, project_root)
            if content:
                files[str(ux_path)] = content

        # 4. Architecture (technical) - search in planning_artifacts (docs/)
        arch_path = find_file_in_planning_dir(context, "*architecture*.md")
        if arch_path:
            content = safe_read_file(arch_path, project_root)
            if content:
                files[str(arch_path)] = content

        # 5. Epic file (current epic)
        epic_num = resolved.get("epic_num")
        if epic_num:
            epic_path = find_epic_file(context, epic_num)
            if epic_path:
                content = safe_read_file(epic_path, project_root)
                if content:
                    files[str(epic_path)] = content

        # 5.5 ATDD checklist (if exists) - provides failing tests from ATDD phase
        story_id = resolved.get("story_id")
        if story_id:
            atdd_pattern = f"*atdd-checklist*{story_id}*.md"
            atdd_path = find_file_in_output_folder(context, atdd_pattern)
            if atdd_path:
                content = safe_read_file(atdd_path, project_root)
                if content:
                    files[str(atdd_path)] = content
                    logger.debug("Embedded ATDD checklist: %s", atdd_path)

        # 6. Source files from story's File List (with token budget)
        story_path_str = resolved.get("story_file")
        if story_path_str:
            story_path = Path(story_path_str)
            source_files = self._collect_source_files_from_story(
                story_path, context, token_budget=DEFAULT_SOURCE_FILES_TOKEN_BUDGET
            )
            files.update(source_files)

        # 7. Story file (LAST - closest to instructions per recency-bias)
        if story_path_str:
            story_path = Path(story_path_str)
            content = safe_read_file(story_path, project_root)
            if content:
                files[str(story_path)] = content

        return files

    def _collect_source_files_from_story(
        self,
        story_path: Path,
        context: CompilerContext,
        token_budget: int = DEFAULT_SOURCE_FILES_TOKEN_BUDGET,
    ) -> dict[str, str]:
        """Collect source files from story's File List with token budget.

        Reads File List section from story, extracts file paths, filters
        out docs/ files, and includes source file contents up to token budget.

        Args:
            story_path: Path to story file.
            context: Compilation context with project root.
            token_budget: Maximum tokens for source files.

        Returns:
            Dictionary mapping file paths to content (possibly truncated).

        """
        try:
            story_content = story_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("Could not read story %s for source file extraction: %s", story_path, e)
            return {}

        file_paths = _extract_file_paths_from_story(story_content)
        if not file_paths:
            logger.debug("No file paths in File List for %s", story_path.name)
            return {}

        output_folder_resolved = context.output_folder.resolve()
        project_root_resolved = context.project_root.resolve()
        result: dict[str, str] = {}
        tokens_used = 0

        for rel_path in file_paths:
            abs_path = (context.project_root / rel_path).resolve()

            try:
                if not abs_path.is_relative_to(project_root_resolved):
                    logger.debug("Skipping path outside project: %s", rel_path)
                    continue
            except ValueError:
                continue

            # Use is_relative_to for proper path containment check
            # (avoids false positives with startswith on similar prefixes like docs2/)
            try:
                if abs_path.is_relative_to(output_folder_resolved):
                    logger.debug("Skipping docs file: %s", rel_path)
                    continue
            except ValueError:
                pass  # Not relative to output folder, which is fine

            if not abs_path.exists():
                logger.debug("Skipping missing file: %s", rel_path)
                continue

            try:
                content = abs_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                logger.debug("Could not read source file %s: %s", rel_path, e)
                continue

            file_tokens = estimate_tokens(content)

            if tokens_used + file_tokens <= token_budget:
                result[str(abs_path)] = content
                tokens_used += file_tokens
                logger.debug(
                    "Added source file %s (~%d tokens, total: %d)",
                    rel_path,
                    file_tokens,
                    tokens_used,
                )
            elif tokens_used < token_budget:
                remaining_tokens = token_budget - tokens_used
                remaining_chars = remaining_tokens * 4

                truncated = content[:remaining_chars]
                last_newline = truncated.rfind("\n")
                if last_newline > 0:
                    truncated = truncated[:last_newline]
                    line_count = truncated.count("\n") + 1
                else:
                    line_count = 1

                truncated += f"\n\n[... TRUNCATED at line {line_count} due to token budget ...]"
                result[str(abs_path)] = truncated
                tokens_used = token_budget

                logger.debug(
                    "Truncated source file %s at line %d (budget reached)", rel_path, line_count
                )
                break
            else:
                logger.debug(
                    "Skipping source file %s - token budget exhausted (%d/%d)",
                    rel_path,
                    tokens_used,
                    token_budget,
                )
                break

        if result:
            logger.info(
                "Collected %d source files from File List (~%d tokens)", len(result), tokens_used
            )

        return result

    def _build_mission(
        self,
        workflow_ir: WorkflowIR,
        resolved: dict[str, Any],
    ) -> str:
        """Build mission description for compiled workflow.

        Args:
            workflow_ir: Workflow IR with description.
            resolved: Resolved variables.

        Returns:
            Mission description string.

        """
        base_description = workflow_ir.raw_config.get(
            "description", "Execute a story by implementing tasks/subtasks, writing tests"
        )

        epic_num = resolved.get("epic_num", "?")
        story_num = resolved.get("story_num", "?")
        story_title = resolved.get("story_title", "")

        if story_title:
            mission = (
                f"{base_description}\n\n"
                f"Target: Story {epic_num}.{story_num} - {story_title}\n"
                f"Implement all tasks and subtasks following TDD methodology."
            )
        else:
            mission = (
                f"{base_description}\n\n"
                f"Target: Story {epic_num}.{story_num}\n"
                f"Implement all tasks and subtasks following TDD methodology."
            )

        return mission
