"""Compiler for the testarch-trace workflow.

This module implements the WorkflowCompiler protocol for the testarch-trace
workflow, producing standalone prompts for generating traceability matrices
and making quality gate decisions (PASS/CONCERNS/FAIL/WAIVED).

The trace workflow runs on epic completion and maps requirements to tests.

Public API:
    TestarchTraceCompiler: Workflow compiler class implementing WorkflowCompiler protocol
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
    get_epics_dir,
    get_stories_dir,
    load_workflow_template,
    safe_read_file,
)
from bmad_assist.compiler.types import CompiledWorkflow, CompilerContext, WorkflowIR
from bmad_assist.compiler.variable_utils import substitute_variables
from bmad_assist.core.exceptions import CompilerError

logger = logging.getLogger(__name__)

# Workflow path relative to project root (testarch uses different path)
_TESTARCH_TRACE_PATH = "_bmad/bmm/workflows/testarch/trace"


class TestarchTraceCompiler:
    """Compiler for the testarch-trace workflow.

    Implements the WorkflowCompiler protocol to compile the testarch-trace
    workflow into a standalone prompt. The trace workflow generates
    requirements-to-tests traceability matrices and makes quality gate
    decisions.

    Context embedding follows recency-bias ordering:
    1. project_context.md (general)
    2. epic file (specific - contains stories to trace)

    """

    @property
    def workflow_name(self) -> str:
        """Unique workflow identifier."""
        return "testarch-trace"

    def get_required_files(self) -> list[str]:
        """Return list of required file glob patterns.

        Returns:
            Glob patterns for files needed by testarch-trace workflow.

        """
        return [
            "**/project_context.md",
            "**/project-context.md",
            "**/epic*.md",
        ]

    def get_variables(self) -> dict[str, Any]:
        """Return workflow-specific variables to resolve.

        Returns:
            Variables needed for testarch-trace compilation.

        """
        return {
            "epic_num": None,
            "test_dir": None,  # From workflow.yaml variables
            "source_dir": None,  # From workflow.yaml variables
            "gate_type": None,  # story|epic|release|hotfix
            "date": None,
        }

    def get_workflow_dir(self, context: CompilerContext) -> Path:
        """Return the workflow directory for this compiler.

        Testarch workflows use a different path than standard workflows:
        _bmad/bmm/workflows/testarch/trace instead of
        .bmad/bmm/workflows/4-implementation/...

        Args:
            context: The compilation context with project paths.

        Returns:
            Path to the workflow directory containing workflow.yaml.

        """
        return context.project_root / _TESTARCH_TRACE_PATH

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

        if epic_num is None:
            raise CompilerError(
                "epic_num is required for testarch-trace compilation.\n"
                "  Suggestion: Provide epic_num via invocation params"
            )

        workflow_dir = context.project_root / _TESTARCH_TRACE_PATH
        if not workflow_dir.exists():
            raise CompilerError(
                f"Workflow directory not found: {workflow_dir}\n"
                f"  Why it's needed: Contains workflow.yaml and instructions.md\n"
                f"  How to fix: Ensure BMAD testarch workflows are installed"
            )

    def compile(self, context: CompilerContext) -> CompiledWorkflow:
        """Compile testarch-trace workflow with given context.

        Executes the full compilation pipeline:
        1. Use pre-loaded workflow_ir from context
        2. Build context files with epic and project context
        3. Resolve variables including test_dir, source_dir from workflow.yaml
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

        workflow_dir = context.project_root / _TESTARCH_TRACE_PATH

        with context_snapshot(context):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Using testarch-trace workflow from %s", workflow_dir)

            # Build resolved variables
            resolved = dict(context.resolved_variables)

            # Resolve variables from workflow.yaml
            workflow_vars = workflow_ir.raw_config.get("variables", {})

            test_dir = workflow_vars.get("test_dir", "{project-root}/tests")
            test_dir = test_dir.replace("{project-root}", str(context.project_root))
            resolved["test_dir"] = test_dir

            source_dir = workflow_vars.get("source_dir", "{project-root}/src")
            source_dir = source_dir.replace("{project-root}", str(context.project_root))
            resolved["source_dir"] = source_dir

            gate_type = workflow_vars.get("gate_type", "epic")
            resolved["gate_type"] = gate_type

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

    def _find_epic_file(
        self,
        context: CompilerContext,
        epic_num: Any,
    ) -> Path | None:
        """Find epic file by epic number.

        Args:
            context: Compilation context with paths.
            epic_num: Epic number.

        Returns:
            Path to epic file or None if not found.

        """
        epics_dir = get_epics_dir(context)
        if not epics_dir.exists():
            return None

        pattern = f"epic-{epic_num}*.md"
        matches = sorted(epics_dir.glob(pattern))

        if not matches:
            logger.debug("No epic file found matching %s in %s", pattern, epics_dir)
            return None

        return matches[0]

    def _build_context_files(
        self,
        context: CompilerContext,
        resolved: dict[str, Any],
    ) -> dict[str, str]:
        """Build context files dict with recency-bias ordering.

        For trace workflow:
        1. project_context.md (general rules)
        2. epic file (overview)
        3. all stories in epic (glob `{epic}-*-*.md`) for traceability

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

        # 2. Epic file (overview)
        epic_num = resolved.get("epic_num")
        if epic_num:
            epic_path = self._find_epic_file(context, epic_num)
            if epic_path:
                content = safe_read_file(epic_path, project_root)
                if content:
                    files[str(epic_path)] = content

            # 3. All stories in epic (AC #2: glob `{epic}-*-*.md`)
            stories_dir = get_stories_dir(context)
            if stories_dir.exists():
                pattern = f"{epic_num}-*-*.md"
                story_files = sorted(stories_dir.glob(pattern))
                for story_path in story_files:
                    content = safe_read_file(story_path, project_root)
                    if content:
                        files[str(story_path)] = content
                if story_files:
                    logger.debug(
                        "Loaded %d story files for epic %s",
                        len(story_files),
                        epic_num,
                    )

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
            "description", "Generate requirements-to-tests traceability matrix"
        )

        epic_num = resolved.get("epic_num", "?")
        gate_type = resolved.get("gate_type", "epic")

        mission = (
            f"{base_description}\n\n"
            f"Target: Epic {epic_num}\n"
            f"Gate Type: {gate_type}\n"
            f"Analyze test coverage and make quality gate decision."
        )

        return mission
