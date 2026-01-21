"""Compiler for the testarch-test-review workflow.

This module implements the WorkflowCompiler protocol for the testarch-test-review
workflow, producing standalone prompts for test quality review.

The test review workflow validates tests against best practices for maintainability,
determinism, isolation, and flakiness prevention.

Public API:
    TestarchTestReviewCompiler: Workflow compiler class implementing WorkflowCompiler protocol
"""

import logging
from pathlib import Path
from typing import Any

from bmad_assist.compiler.filtering import filter_instructions
from bmad_assist.compiler.output import generate_output
from bmad_assist.compiler.shared_utils import (
    apply_post_process,
    context_snapshot,
    find_project_context_file,
    get_stories_dir,
    load_workflow_template,
    safe_read_file,
)
from bmad_assist.compiler.types import CompiledWorkflow, CompilerContext, WorkflowIR
from bmad_assist.compiler.variable_utils import substitute_variables
from bmad_assist.core.exceptions import CompilerError

logger = logging.getLogger(__name__)

# Workflow path relative to project root
_TESTARCH_TEST_REVIEW_PATH = "_bmad/bmm/workflows/testarch/test-review"

# Maximum number of test files to include in context
_MAX_TEST_FILES = 20


class TestarchTestReviewCompiler:
    """Compiler for the testarch-test-review workflow.

    Implements the WorkflowCompiler protocol to compile the testarch-test-review
    workflow into a standalone prompt. The test review workflow validates test
    quality against best practices.

    Context embedding follows recency-bias ordering:
    1. project_context.md (general rules)
    2. story file (test context)
    3. test files (most relevant for review)

    """

    @property
    def workflow_name(self) -> str:
        """Unique workflow identifier."""
        return "testarch-test-review"

    def get_required_files(self) -> list[str]:
        """Return list of required file glob patterns.

        Returns:
            Glob patterns for files needed by testarch-test-review workflow.

        """
        return [
            "**/project_context.md",
            "**/project-context.md",
        ]

    def get_variables(self) -> dict[str, Any]:
        """Return workflow-specific variables to resolve.

        Returns:
            Variables needed for testarch-test-review compilation.

        """
        return {
            "epic_num": None,
            "story_num": None,
            "story_id": None,
            "story_file": None,
            "test_dir": None,
            "date": None,
            "project_path": None,
        }

    def get_workflow_dir(self, context: CompilerContext) -> Path:
        """Return the workflow directory for this compiler.

        Uses workflow discovery for testarch-test-review.

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
                "epic_num is required for testarch-test-review compilation.\n"
                "  Suggestion: Provide epic_num via invocation params"
            )
        if story_num is None:
            raise CompilerError(
                "story_num is required for testarch-test-review compilation.\n"
                "  Suggestion: Provide story_num via invocation params"
            )

        # Workflow directory is validated by get_workflow_dir via discovery
        workflow_dir = self.get_workflow_dir(context)
        if not workflow_dir.exists():
            raise CompilerError(
                f"Workflow directory not found: {workflow_dir}\n"
                f"  Why it's needed: Contains workflow.yaml and instructions.md\n"
                f"  How to fix: Reinstall bmad-assist or ensure BMAD is properly installed"
            )

    def compile(self, context: CompilerContext) -> CompiledWorkflow:
        """Compile testarch-test-review workflow with given context.

        Executes the full compilation pipeline:
        1. Use pre-loaded workflow_ir from context
        2. Build context files with story, project context, and test files
        3. Resolve variables including test_dir from workflow.yaml
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
                logger.debug("Using testarch-test-review workflow from %s", workflow_dir)

            # Build resolved variables
            resolved = dict(context.resolved_variables)

            epic_num = resolved.get("epic_num")
            story_num = resolved.get("story_num")

            # Compute story_id (use dash to match handler filename format)
            resolved["story_id"] = f"{epic_num}-{story_num}"
            resolved["project_path"] = str(context.project_root)

            # Find and add story file path
            story_path = self._find_story_file(context, epic_num, story_num)
            if story_path:
                resolved["story_file"] = str(story_path)

            # Resolve test_dir from workflow.yaml variables
            workflow_vars = workflow_ir.raw_config.get("variables", {})
            test_dir = workflow_vars.get("test_dir", "{project-root}/tests")
            test_dir = test_dir.replace("{project-root}", str(context.project_root))
            resolved["test_dir"] = test_dir

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Resolved %d variables", len(resolved))

            # Build context files
            context_files = self._build_context_files(context, resolved)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Built context with %d files", len(context_files))

            # Load template if defined
            template_content = load_workflow_template(workflow_ir, context)

            # Filter instructions
            filtered_instructions = filter_instructions(workflow_ir)
            filtered_instructions = substitute_variables(filtered_instructions, resolved)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Filtered instructions: %d bytes", len(filtered_instructions))

            # Build mission
            mission = self._build_mission(workflow_ir, resolved)

            # Generate output
            compiled = CompiledWorkflow(
                workflow_name=self.workflow_name,
                mission=mission,
                context="",
                variables=resolved,
                instructions=filtered_instructions,
                output_template=template_content,
                token_estimate=0,
            )

            result = generate_output(
                compiled,
                project_root=context.project_root,
                context_files=context_files,
                links_only=context.links_only,
            )

            # Apply post_process rules if patch exists
            final_xml = apply_post_process(result.xml, context)

            return CompiledWorkflow(
                workflow_name=self.workflow_name,
                mission=mission,
                context=final_xml,
                variables=resolved,
                instructions=filtered_instructions,
                output_template=template_content,
                token_estimate=result.token_estimate,
            )

    def _find_story_file(
        self,
        context: CompilerContext,
        epic_num: Any,
        story_num: Any,
    ) -> Path | None:
        """Find story file by epic and story number.

        Args:
            context: Compilation context with paths.
            epic_num: Epic number.
            story_num: Story number.

        Returns:
            Path to story file or None if not found.

        """
        stories_dir = get_stories_dir(context)
        if not stories_dir.exists():
            return None

        pattern = f"{epic_num}-{story_num}-*.md"
        matches = sorted(stories_dir.glob(pattern))

        if not matches:
            logger.debug("No story file found matching %s in %s", pattern, stories_dir)
            return None

        return matches[0]

    def _discover_test_files(
        self,
        context: CompilerContext,
        epic_num: Any,
        story_num: Any,
    ) -> list[Path]:
        """Discover test files relevant to the story.

        Uses multiple patterns to find tests:
        1. tests/**/*{epic_num}-{story_num}*.py (e.g., test_testarch-9_*.py)
        2. tests/**/*{epic_num}_{story_num}*.py (e.g., test_testarch_9_*.py)
        3. Fallback: tests/**/*.py limited to 20 most recently modified files

        Args:
            context: Compilation context with paths.
            epic_num: Epic number (e.g., "testarch", 1, 2).
            story_num: Story number (e.g., "9", 1, 2).

        Returns:
            List of Path objects for discovered test files.

        """
        tests_dir = context.project_root / "tests"
        if not tests_dir.exists():
            logger.warning("Tests directory not found: %s", tests_dir)
            return []

        # Try story-specific patterns first
        story_patterns = [
            f"**/*{epic_num}-{story_num}*.py",
            f"**/*{epic_num}_{story_num}*.py",
        ]

        for pattern in story_patterns:
            matches = list(tests_dir.glob(pattern))
            if matches:
                logger.debug("Found %d test files matching pattern %s", len(matches), pattern)
                return sorted(matches)[:_MAX_TEST_FILES]

        # Fallback: get most recently modified test files
        all_test_files = list(tests_dir.glob("**/*.py"))
        if not all_test_files:
            logger.warning("No test files found in %s (non-blocking)", tests_dir)
            return []

        # Sort by modification time (most recent first)
        all_test_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        selected = all_test_files[:_MAX_TEST_FILES]
        logger.debug("Using fallback: %d most recently modified test files", len(selected))
        return selected

    def _build_context_files(
        self,
        context: CompilerContext,
        resolved: dict[str, Any],
    ) -> dict[str, str]:
        """Build context files dict with recency-bias ordering.

        For test review workflow:
        1. project_context.md (general rules)
        2. story file (test context)
        3. test files (most relevant for review)

        Args:
            context: Compilation context with paths.
            resolved: Resolved variables.

        Returns:
            Dictionary mapping file paths to content.

        """
        files: dict[str, str] = {}
        project_root = context.project_root

        # 1. Project context (general)
        project_context_path = find_project_context_file(context)
        if project_context_path:
            content = safe_read_file(project_context_path, project_root)
            if content:
                files[str(project_context_path)] = content

        # 2. Story file (context for what tests should cover)
        story_file_path = resolved.get("story_file")
        if story_file_path:
            story_path = Path(story_file_path)
            content = safe_read_file(story_path, project_root)
            if content:
                files[str(story_path)] = content

        # 3. Test files (most relevant for review)
        epic_num = resolved.get("epic_num")
        story_num = resolved.get("story_num")
        test_files = self._discover_test_files(context, epic_num, story_num)

        for test_file in test_files:
            content = safe_read_file(test_file, project_root)
            if content:
                files[str(test_file)] = content

        return files

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
            "description",
            "Review test quality using comprehensive knowledge base and best practices validation",
        )

        story_id = resolved.get("story_id", "?")

        mission = (
            f"{base_description}\n\n"
            f"Target: Story {story_id}\n"
            f"Review tests for quality, best practices, and flakiness prevention."
        )

        return mission
