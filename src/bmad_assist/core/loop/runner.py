"""Main loop runner orchestration.

Story 6.5: run_loop() and _run_loop_body() implementation.
Story 15.4: Event notification dispatch integration.
Story 20.10: Sprint-status sync and repair integration.

"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from bmad_assist.core.config import Config
from bmad_assist.core.exceptions import StateError

# Story 22.9: Dashboard SSE event emission
from bmad_assist.core.loop.dashboard_events import (
    emit_story_transition,
    emit_workflow_status,
    generate_run_id,
    parse_story_id,
    story_id_from_parts,
)
from bmad_assist.core.loop.dispatch import execute_phase, init_handlers
from bmad_assist.core.loop.epic_transitions import handle_epic_completion
from bmad_assist.core.loop.guardian import get_next_phase, guardian_check_anomaly
from bmad_assist.core.loop.signals import (
    _get_interrupt_exit_reason,
    register_signal_handlers,
    reset_shutdown,
    shutdown_requested,
    unregister_signal_handlers,
)
from bmad_assist.core.loop.story_transitions import handle_story_completion
from bmad_assist.core.loop.types import GuardianDecision, LoopExitReason
from bmad_assist.core.state import (
    Phase,
    State,
    get_epic_duration_ms,
    get_phase_duration_ms,
    get_project_duration_ms,
    get_state_path,
    get_story_duration_ms,
    load_state,
    save_state,
    start_epic_timing,
    start_phase_timing,
    start_project_timing,
    start_story_timing,
)
from bmad_assist.core.types import EpicId

logger = logging.getLogger(__name__)


__all__ = [
    "run_loop",
]


# Type alias for state parameter
LoopState = State


# =============================================================================
# Epic Story Count Helper - Story standalone-03 Synthesis Fix
# =============================================================================


def _count_epic_stories(state: LoopState) -> int:
    """Count completed stories belonging to the current epic only.

    Stories in completed_stories have format like "1.1", "2.5", "testarch.3".
    This function filters to count only those matching current_epic.

    Args:
        state: Current loop state with completed_stories and current_epic.

    Returns:
        Count of stories completed in the current epic (0 if none).

    """
    if not state.completed_stories or state.current_epic is None:
        return 0

    epic_prefix = f"{state.current_epic}."
    return sum(1 for story in state.completed_stories if story.startswith(epic_prefix))


# =============================================================================
# Story Title Helper
# =============================================================================


def _get_story_title(project_path: Path, story_id: str) -> str | None:
    """Get human-readable story title from sprint-status or story key.

    Tries to extract story title from:
    1. Sprint-status entries (e.g., "2-1-css-design-tokens" -> "CSS Design Tokens")
    2. Story key slug (fallback)

    Args:
        project_path: Project root path.
        story_id: Story identifier (e.g., "2.1").

    Returns:
        Story title if found, None otherwise.

    """
    try:
        from bmad_assist.sprint.parser import parse_sprint_status

        # Load sprint-status to find story entry with title
        sprint_path = project_path / "_bmad-output" / "implementation-artifacts" / "sprint-status.yaml"
        if not sprint_path.exists():
            return None

        sprint_data = parse_sprint_status(sprint_path)

        # Find entry matching this story ID (e.g., "2.1" matches "2-1-css-design-tokens")
        # Story ID format: "X.Y" -> key prefix "X-Y-"
        story_parts = story_id.split(".")
        if len(story_parts) == 2:
            key_prefix = f"{story_parts[0]}-{story_parts[1]}-"
            for entry in sprint_data.entries.values():
                if entry.key.startswith(key_prefix):
                    # Extract title from key: "2-1-css-design-tokens" -> "css design tokens" -> "CSS Design Tokens"
                    title_slug = entry.key[len(key_prefix) :]
                    if title_slug:
                        # Convert slug to title: kebab-case -> Title Case
                        return title_slug.replace("-", " ").title()
    except Exception:
        pass

    return None


# =============================================================================
# Notification Dispatch Helper - Story 15.4
# =============================================================================


def _dispatch_event(
    event_type: str,
    project_path: Path,
    state: LoopState,
    **extra_fields: str | int | None,
) -> None:
    """Fire-and-forget dispatch of notification events.

    Runs dispatch in a new event loop to not block the main loop.
    All errors are caught and logged - never raises.

    Args:
        event_type: Event type name (e.g., "story_started", "phase_completed").
        project_path: Project root path for project name.
        state: Current loop state for epic/story info.
        **extra_fields: Additional fields for payload (phase, duration_ms, etc.).

    """
    try:
        from bmad_assist.notifications.dispatcher import get_dispatcher  # noqa: I001
        from bmad_assist.notifications.events import (  # noqa: I001
            EpicCompletedPayload,
            ErrorOccurredPayload,
            EventPayload,
            EventType,
            PhaseCompletedPayload,
            ProjectCompletedPayload,
            QueueBlockedPayload,
            StoryCompletedPayload,
            StoryStartedPayload,
        )

        dispatcher = get_dispatcher()
        if dispatcher is None:
            return

        # Build payload based on event type
        project = project_path.name
        # Default epic/story to safe values if None
        epic = state.current_epic if state.current_epic is not None else 0
        story = state.current_story if state.current_story is not None else "unknown"

        payload: EventPayload
        event: EventType

        if event_type == "story_started":
            event = EventType.STORY_STARTED
            phase_str = extra_fields.get("phase")
            story_title = extra_fields.get("story_title")
            payload = StoryStartedPayload(
                project=project,
                epic=epic,
                story=story,
                phase=str(phase_str) if phase_str else "",
                story_title=str(story_title) if story_title else None,
            )
        elif event_type == "story_completed":
            event = EventType.STORY_COMPLETED
            duration = extra_fields.get("duration_ms")
            outcome = extra_fields.get("outcome")
            payload = StoryCompletedPayload(
                project=project,
                epic=epic,
                story=story,
                duration_ms=int(duration) if duration else 0,
                outcome=str(outcome) if outcome else "success",
            )
        elif event_type == "phase_completed":
            event = EventType.PHASE_COMPLETED
            phase_val = extra_fields.get("phase")
            next_phase = extra_fields.get("next_phase")
            duration = extra_fields.get("duration_ms")
            payload = PhaseCompletedPayload(
                project=project,
                epic=epic,
                story=story,
                phase=str(phase_val) if phase_val else "",
                next_phase=str(next_phase) if next_phase else None,
                duration_ms=int(duration) if duration else 0,
            )
        elif event_type == "error_occurred":
            event = EventType.ERROR_OCCURRED
            error_type_val = extra_fields.get("error_type")
            message_val = extra_fields.get("message")
            stack_val = extra_fields.get("stack_trace")
            payload = ErrorOccurredPayload(
                project=project,
                epic=epic,
                story=story,
                error_type=str(error_type_val) if error_type_val else "unknown",
                message=str(message_val) if message_val else "",
                stack_trace=str(stack_val) if stack_val else None,
            )
        elif event_type == "queue_blocked":
            event = EventType.QUEUE_BLOCKED
            reason_val = extra_fields.get("reason")
            waiting_val = extra_fields.get("waiting_tasks")
            payload = QueueBlockedPayload(
                project=project,
                epic=epic,
                story=story,
                reason=str(reason_val) if reason_val else "guardian_halt",
                waiting_tasks=int(waiting_val) if waiting_val else 0,
            )
        # Story standalone-03 AC6: Epic completion event
        elif event_type == "epic_completed":
            event = EventType.EPIC_COMPLETED
            duration = extra_fields.get("duration_ms")
            stories_completed = extra_fields.get("stories_completed")
            payload = EpicCompletedPayload(
                project=project,
                epic=epic,
                duration_ms=int(duration) if duration else 0,
                stories_completed=int(stories_completed) if stories_completed else 0,
            )
        # Story standalone-03 AC7: Project completion event
        elif event_type == "project_completed":
            event = EventType.PROJECT_COMPLETED
            duration = extra_fields.get("duration_ms")
            epics_completed = extra_fields.get("epics_completed")
            stories_completed = extra_fields.get("stories_completed")
            payload = ProjectCompletedPayload(
                project=project,
                epic=epic,
                duration_ms=int(duration) if duration else 0,
                epics_completed=int(epics_completed) if epics_completed else 0,
                stories_completed=int(stories_completed) if stories_completed else 0,
            )
        else:
            logger.debug("Unknown event type for dispatch: %s", event_type)
            return

        # Run dispatch with nested event loop safety (AC3 requirement)
        # Check if we're inside an already-running event loop (test environments)
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - create task (fire-and-forget)
            loop.create_task(dispatcher.dispatch(event, payload))
        except RuntimeError:
            # No running loop - safe to use asyncio.run()
            asyncio.run(dispatcher.dispatch(event, payload))

    except Exception as e:
        logger.debug("Notification dispatch error (ignored): %s", str(e))


# =============================================================================
# Resume Validation Against Sprint-Status - Bug fix for stale state on resume
# =============================================================================


def _validate_resume_against_sprint(
    state: LoopState,
    project_path: Path,
    epic_list: list[EpicId],
    epic_stories_loader: Callable[[EpicId], list[str]],
    state_path: Path,
) -> tuple[LoopState, bool]:
    """Validate and advance state based on sprint-status on resume.

    Checks sprint-status.yaml to see if current story/epic is already done.
    If so, advances state to the next incomplete story/epic.

    This fixes the bug where:
    - Loop was interrupted after completing work
    - sprint-status.yaml reflects the completed work
    - But state.yaml is stale and points to the completed position
    - On resume, loop would re-execute completed work

    Args:
        state: Current state from state.yaml.
        project_path: Project root directory.
        epic_list: Ordered list of epic IDs.
        epic_stories_loader: Function to get stories for an epic.
        state_path: Path to state file for persistence.

    Returns:
        Tuple of (updated_state, is_project_complete).
        - updated_state: May be same as input if no changes needed.
        - is_project_complete: True if all epics are done.

    """
    try:
        from bmad_assist.sprint.resume_validation import validate_resume_state
    except ImportError:
        logger.debug("Sprint resume validation module not available")
        return state, False

    try:
        result = validate_resume_state(state, project_path, epic_list, epic_stories_loader)

        if result.project_complete:
            # All epics done - save state if changed and signal completion
            logger.info("Resume validation: project is complete")
            if result.advanced:
                save_state(result.state, state_path)
            return result.state, True

        if result.advanced:
            logger.info("Resume validation: %s", result.summary())
            # Persist the advanced state
            save_state(result.state, state_path)
            # Trigger sprint sync to update sprint-status with new state
            _invoke_sprint_sync(result.state, project_path)
            return result.state, False

        logger.debug("Resume validation: no changes needed")
        return state, False

    except Exception as e:
        # Resume validation is defensive - never crash the loop
        logger.warning("Resume validation failed (continuing): %s", e)
        return state, False


# =============================================================================
# Sprint Sync Integration - Story 20.10
# =============================================================================


def _invoke_sprint_sync(state: LoopState, project_path: Path) -> None:
    """Invoke sprint sync callbacks after state save.

    Fire-and-forget invocation of registered sync callbacks. All errors are
    caught and logged at WARNING level, never propagating to the caller.

    Args:
        state: Current State instance.
        project_path: Project root directory.

    """
    try:
        from bmad_assist.sprint.sync import invoke_sync_callbacks

        invoke_sync_callbacks(state, project_path)
    except ImportError:
        logger.debug("Sprint module not available for sync")
    except Exception as e:
        logger.warning("Sprint sync failed (ignored): %s", e)


def _ensure_sprint_sync_callback() -> None:
    """Ensure default sprint sync callback is registered at loop startup.

    Idempotent registration - safe to call multiple times. Uses lazy import
    with ImportError guard for sprint module availability.

    """
    try:
        from bmad_assist.sprint.repair import ensure_sprint_sync_callback

        ensure_sprint_sync_callback()
    except ImportError:
        logger.debug("Sprint module not available for callback registration")
    except Exception as e:
        logger.warning("Sprint callback registration failed (ignored): %s", e)


def _trigger_interactive_repair(project_path: Path, state: LoopState) -> None:
    """Trigger interactive repair on loop initialization.

    Catches all exceptions including ImportError - NEVER crashes the loop.
    Called only on fresh start to perform full artifact-based repair.

    Args:
        project_path: Project root directory.
        state: Current State instance.

    """
    try:
        from bmad_assist.sprint.repair import RepairMode, repair_sprint_status
    except ImportError:
        logger.debug("Sprint module not available for repair")
        return

    try:
        result = repair_sprint_status(project_path, RepairMode.INTERACTIVE, state)
        if result.user_cancelled:
            logger.warning("Sprint repair cancelled, continuing without repair")
        elif result.errors:
            logger.warning("Sprint repair encountered errors: %s", result.errors)
        else:
            logger.info("Sprint repair complete: %s", result.summary())
    except Exception as e:
        logger.warning("Sprint repair failed (ignored): %s", e)


def _run_archive_artifacts(project_path: Path) -> None:
    """Run archive-artifacts.sh to archive multi-LLM validation and review reports.

    Archives non-master/non-synthesis .md files from:
    - _bmad-output/implementation-artifacts/code-reviews/
    - _bmad-output/implementation-artifacts/story-validations/

    Called after CODE_REVIEW_SYNTHESIS to clean up multi-reviewer artifacts.
    Script is idempotent - safe to call multiple times.

    Args:
        project_path: Project root directory.

    """
    script_path = project_path / "scripts" / "archive-artifacts.sh"

    if not script_path.exists():
        logger.debug("archive-artifacts.sh not found at %s, skipping", script_path)
        return

    try:
        result = subprocess.run(
            [str(script_path), "-s"],  # -s for silent mode
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("Archived multi-LLM artifacts after code review synthesis")
        else:
            logger.warning(
                "archive-artifacts.sh failed (returncode=%d): %s",
                result.returncode,
                result.stderr,
            )
    except subprocess.TimeoutExpired:
        logger.warning("archive-artifacts.sh timed out after 30s")
    except Exception as e:
        logger.warning("archive-artifacts.sh execution failed: %s", e)


# =============================================================================
# Lock File Context Manager - Dashboard Process Detection
# =============================================================================


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is running.

    Uses os.kill(pid, 0) which sends a null signal (doesn't kill the process,
    only checks existence). Returns True if process exists, False if PID not found.

    Story 22.3: PID validation for stale lock detection.

    Args:
        pid: Process ID to check.

    Returns:
        True if process is running, False if PID is not found (stale lock).

    """
    try:
        os.kill(pid, 0)  # Signal 0 doesn't kill, just checks existence
        return True
    except ProcessLookupError:
        # PID definitely not found - stale lock
        return False
    except PermissionError:
        # Process exists but belongs to another user - treat as alive
        # This prevents overwriting valid locks from other users
        return True
    except OSError:
        # Other OS errors (e.g., invalid PID) - treat as not found
        return False


def _read_lock_file(lock_path: Path) -> tuple[int | None, str | None]:
    """Read PID and timestamp from lock file.

    Story 22.3: Parse lock file for PID validation.

    Args:
        lock_path: Path to running.lock file.

    Returns:
        Tuple of (pid, timestamp) or (None, None) if file is invalid.

    """
    try:
        content = lock_path.read_text().strip().split("\n")
        if len(content) >= 2:
            pid = int(content[0].strip())
            timestamp = content[1].strip()
            return pid, timestamp
    except (ValueError, IndexError, OSError):
        pass
    return None, None


@contextmanager
def _running_lock(project_path: Path):
    """Context manager for .bmad-assist/running.lock file.

    Creates lock file with PID and timestamp on enter, removes on exit.
    Dashboard checks this file to detect if run is active.

    Story 22.2: Also initializes run-scoped prompts directory for organized
    prompt tracking during the run.

    Story 22.3: Implements PID validation for stale lock detection and
    concurrent run prevention.

    Args:
        project_path: Project root directory.

    Yields:
        Path to lock file.

    Raises:
        StateError: If another bmad-assist run is already active.

    """
    from bmad_assist.core.io import get_timestamp, init_run_prompts_dir

    lock_dir = project_path / ".bmad-assist"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "running.lock"

    # Story 22.3: Check for existing lock file and validate PID
    if lock_path.exists():
        existing_pid, lock_timestamp = _read_lock_file(lock_path)
        if existing_pid is not None:
            if _is_pid_alive(existing_pid):
                # Active lock - abort to prevent concurrent runs
                raise StateError(
                    f"Another bmad-assist run is already active (PID {existing_pid}). "
                    f"If this is incorrect, remove the stale lock file: {lock_path}"
                )
            else:
                # Stale lock - remove and continue with warning
                logger.warning(
                    f"Removed stale lock file from dead process {existing_pid} "
                    f"(locked at {lock_timestamp})"
                )
                try:
                    lock_path.unlink()
                except OSError as e:
                    logger.warning(f"Failed to remove stale lock file: {e}")

    # Generate run timestamp for run-scoped prompts directory
    run_timestamp = get_timestamp()

    # Initialize run-scoped prompts directory (Story 22.2)
    init_run_prompts_dir(project_path, run_timestamp)

    # Story 22.10: Clean up stale pause flag on startup (AC #7)
    from bmad_assist.core.loop.pause import cleanup_stale_pause_flags

    cleanup_stale_pause_flags(project_path)

    # Write lock file with PID and timestamp
    lock_content = f"{os.getpid()}\n{datetime.now(UTC).isoformat()}\n"
    lock_path.write_text(lock_content)

    try:
        yield lock_path
    finally:
        # Story 22.3: Always remove lock file on exit
        # Use contextlib.suppress for robustness if file was externally deleted
        import contextlib

        with contextlib.suppress(FileNotFoundError):
            lock_path.unlink()


# =============================================================================
# run_loop - Story 6.5
# =============================================================================


def run_loop(
    config: Config,
    project_path: Path,
    epic_list: list[EpicId],
    epic_stories_loader: Callable[[EpicId], list[str]],
) -> LoopExitReason:
    """Execute the main BMAD development loop.

    Main orchestrator that ties together all phase execution, story transitions,
    and epic transitions. Implements the "fire-and-forget" design where the loop
    runs autonomously until project completion, guardian halt, or signal interrupt.

    The loop:
    - Loads or creates state on startup
    - Executes phases in sequence using execute_phase() from Story 6.2
    - Handles story completion using handle_story_completion() from Story 6.3
    - Handles epic completion using handle_epic_completion() from Story 6.4
    - Saves state after each phase
    - Checks for shutdown signals after each save_state()
    - Continues until project completion, anomaly detection, or signal interrupt

    Args:
        config: Pydantic Config model with state_path, provider settings.
        project_path: Path to project root directory.
        epic_list: Sorted list of epic numbers (e.g., [1, 2, 3, 6]).
            Typically generated via glob docs/epics/epic-*.md → extract numbers → sort.
        epic_stories_loader: Callable that returns story IDs for given epic.
            Takes epic number (int), returns list of story IDs (list[str]).

    Returns:
        LoopExitReason indicating how the loop exited:
        - COMPLETED: Project finished successfully
        - INTERRUPTED_SIGINT: Interrupted by Ctrl+C (SIGINT)
        - INTERRUPTED_SIGTERM: Interrupted by kill signal (SIGTERM)
        - GUARDIAN_HALT: Halted by Guardian for user intervention

    Raises:
        StateError: If epic_list is empty.
        StateError: If first epic has no stories.
        StateError: If state file exists but is corrupted (propagated from load_state).

    Example:
        >>> epic_list = [1, 2, 3]
        >>> loader = lambda epic: [f"{epic}.1", f"{epic}.2", f"{epic}.3"]
        >>> result = run_loop(config, project_path, epic_list, loader)
        >>> result
        <LoopExitReason.COMPLETED: 'completed'>

    Note:
        - Guardian integration is placeholder only (Epic 8)
        - Dashboard update is log placeholder only (Epic 9)
        - Signal handlers (SIGINT/SIGTERM) are registered for graceful shutdown (Story 6.6)
        - NEVER calls sys.exit() - returns LoopExitReason for CLI to handle

    """
    # AC1: Validate epic_list not empty
    if not epic_list:
        raise StateError("No epics found in project")

    # Story 6.6: Clear shutdown state from any previous invocation and register handlers
    reset_shutdown()
    register_signal_handlers()

    # Initialize phase handlers with config and project path
    init_handlers(config, project_path)

    # Story 20.10: Register sprint sync callback at loop startup
    _ensure_sprint_sync_callback()

    # Dashboard: Create lock file for process detection
    with _running_lock(project_path):
        try:
            return _run_loop_body(config, project_path, epic_list, epic_stories_loader)
        finally:
            # Story 6.6: Always restore previous signal handlers on exit
            unregister_signal_handlers()


def _run_loop_body(
    config: Config,
    project_path: Path,
    epic_list: list[EpicId],
    epic_stories_loader: Callable[[EpicId], list[str]],
) -> LoopExitReason:
    """Execute the main loop body with signal handling active.

    This function contains the actual loop logic. It is called by run_loop()
    within a try/finally block that ensures signal handlers are properly
    restored on exit.

    Args:
        config: Pydantic Config model with state_path, provider settings.
        project_path: Path to project root directory.
        epic_list: Sorted list of epic numbers (validated non-empty by run_loop).
        epic_stories_loader: Callable that returns story IDs for given epic.

    Returns:
        LoopExitReason indicating how the loop exited.

    """
    # Resolve state_path - stored in project directory
    state_path = get_state_path(config, project_root=project_path)

    # Story 22.9: Initialize dashboard event tracking
    run_id = generate_run_id()
    sequence_id = 0

    # AC1: Load state or create fresh
    try:
        state = load_state(state_path)
        logger.info(
            "Loaded state: epic=%s story=%s phase=%s",
            state.current_epic,
            state.current_story,
            state.current_phase.name if state.current_phase else "None",
        )
    except StateError:
        # Invalid state file - let exception propagate per AC1
        raise

    # Check if this is a fresh start (ALL position fields are None)
    # Code Review Fix: Use AND logic - only fresh start if ALL fields are None
    # Partial state (some None, some set) indicates corruption and should error
    is_fresh_start = (
        state.current_epic is None and state.current_story is None and state.current_phase is None
    )

    # Code Review Fix: Validate partial state as corruption
    if not is_fresh_start and any(
        [
            state.current_epic is None,
            state.current_story is None,
            state.current_phase is None,
        ]
    ):
        raise StateError(
            f"State file has partial data: epic={state.current_epic}, "
            f"story={state.current_story}, phase={state.current_phase}. "
            "Expected all or none to be None"
        )

    if is_fresh_start:
        # AC1: Create fresh state with first epic, first story, CREATE_STORY phase
        # epic_list is already sorted per contract - no need to sort again
        first_epic = epic_list[0]

        # Code Review Fix: Wrap epic_stories_loader in try-except
        try:
            first_epic_stories = epic_stories_loader(first_epic)
        except Exception as e:
            raise StateError(f"Failed to load stories for epic {first_epic}: {e}") from e

        # AC1: Validate first epic has stories
        if not first_epic_stories:
            raise StateError(f"No stories found in epic {first_epic}")

        first_story = first_epic_stories[0]

        # Ensure we're on the correct branch for this epic
        # Import here to avoid circular dependency
        from bmad_assist.git.branch import ensure_epic_branch, is_git_enabled

        if is_git_enabled():
            ensure_epic_branch(first_epic, project_path)

        # Get naive UTC timestamp (project convention)
        now = datetime.now(UTC).replace(tzinfo=None)

        state = state.model_copy(
            update={
                "current_epic": first_epic,
                "current_story": first_story,
                "current_phase": Phase.CREATE_STORY,
                "started_at": now,
                "updated_at": now,
            }
        )

        # Story standalone-03 AC6/AC7: Start timing for project, epic, and story
        start_project_timing(state)
        start_epic_timing(state)
        start_story_timing(state)

        logger.info(
            "Fresh start: epic=%s story=%s phase=%s",
            first_epic,
            first_story,
            Phase.CREATE_STORY.name,
        )

        # AC1: Persist initial state BEFORE first phase execution
        save_state(state, state_path)

        # Story 20.10: Trigger interactive repair on fresh start
        # Note: repair_sprint_status already includes state sync, so no separate
        # _invoke_sprint_sync call is needed here (avoids redundant I/O)
        _trigger_interactive_repair(project_path, state)

        # Story 15.4: Dispatch story_started event
        story_title = _get_story_title(project_path, first_story)
        _dispatch_event(
            "story_started",
            project_path,
            state,
            phase=Phase.CREATE_STORY.name,
            story_title=story_title,
        )

        # Story 22.9: Emit dashboard story_transition and workflow_status events
        sequence_id += 1
        epic_num = int(state.current_epic) if state.current_epic else 1
        story_num = int(first_story.split(".")[-1])
        story_title = (
            first_story.split(".")[-1].replace("-", " ") if "." in first_story else first_story
        )
        story_id = story_id_from_parts(epic_num, story_num, story_title)
        emit_story_transition(
            run_id=run_id,
            sequence_id=sequence_id,
            action="started",
            epic_num=epic_num,
            story_num=story_num,
            story_id=story_id,
            story_title=story_title,
        )
        emit_workflow_status(
            run_id=run_id,
            sequence_id=sequence_id,
            epic_num=epic_num,
            story_id=first_story,
            phase=Phase.CREATE_STORY.name,
            phase_status="in-progress",
        )

    # ALWAYS validate state against sprint-status on loop start
    # This catches cases where:
    # - sprint-status shows work is done but state.yaml is stale (resume case)
    # - project has existing sprint-status from previous runs (fresh start on existing project)
    # This must run AFTER fresh start initialization so we have a valid state
    state, is_project_complete = _validate_resume_against_sprint(
        state, project_path, epic_list, epic_stories_loader, state_path
    )
    if is_project_complete:
        logger.info("Project complete! All epics finished (detected on startup)")
        return LoopExitReason.COMPLETED

    # Handle resume case
    if not is_fresh_start:
        # Ensure timing context exists (resuming from crash where timing may be missing)
        timing_updated = False
        if state.phase_started_at is None:
            logger.info("Resuming: initializing phase timing")
            start_phase_timing(state)
            timing_updated = True
        if state.story_started_at is None:
            logger.info("Resuming: initializing story timing")
            start_story_timing(state)
            timing_updated = True
        if state.epic_started_at is None:
            logger.info("Resuming: initializing epic timing")
            start_epic_timing(state)
            timing_updated = True
        if state.project_started_at is None:
            logger.info("Resuming: initializing project timing")
            start_project_timing(state)
            timing_updated = True
        if timing_updated:
            save_state(state, state_path)

        # Ensure we're on the correct branch for the current epic
        # (Fresh start is handled inside is_fresh_start block)
        from bmad_assist.git.branch import ensure_epic_branch, is_git_enabled

        if is_git_enabled() and state.current_epic is not None:
            ensure_epic_branch(state.current_epic, project_path)

    # SECURITY WARNING:
    # Never log full config objects, API keys, or fields that may contain secrets.
    # Only log non-sensitive scalar values (provider names, model names, paths).
    logger.debug("Config providers.master.provider: %s", config.providers.master.provider)
    logger.debug("Config providers.master.model: %s", config.providers.master.model)
    logger.debug("Project path: %s", project_path)

    # Main loop - runs until project complete or guardian halt
    while True:
        # Story standalone-03 AC1: Reset phase timing BEFORE each phase execution
        # This ensures accurate duration reporting in notifications
        start_phase_timing(state)
        save_state(state, state_path)

        # AC2: Execute current phase
        result = execute_phase(state)

        # Code Review Fix: Log phase completion with duration for observability
        logger.info(
            "Phase %s completed: success=%s duration=%dms error=%s",
            state.current_phase.name if state.current_phase else "None",
            result.success,
            result.outputs.get("duration_ms", 0),
            result.error if not result.success else "none",
        )

        # AC5: Handle phase failures
        if not result.success:
            logger.warning(
                "Phase %s failed for story %s: %s",
                state.current_phase.name if state.current_phase else "None",
                state.current_story,
                result.error,
            )

            # Story 15.4: Dispatch error_occurred event
            _dispatch_event(
                "error_occurred",
                project_path,
                state,
                error_type="phase_failure",
                message=result.error or "Unknown error",
            )

            if state.current_phase == Phase.RETROSPECTIVE:
                # AC5: RETROSPECTIVE failure - log warning, proceed to next epic
                logger.warning(
                    "RETROSPECTIVE phase failed for epic %s. Error: %s. "
                    "Logging warning and proceeding to next epic.",
                    state.current_epic,
                    result.error,
                )
                # Ensure state is saved with current (failed) retrospective
                save_state(state, state_path)
                # Story 20.10: Invoke sync callbacks after retrospective failure save
                _invoke_sprint_sync(state, project_path)

                # Now, attempt to advance to the next epic as if retrospective succeeded
                # This ensures the loop continues if there are more epics
                # Calculate epic timing before handle_epic_completion modifies state
                epic_duration_ms = get_epic_duration_ms(state)
                epic_stories_count = _count_epic_stories(state)

                new_state, is_project_complete = handle_epic_completion(
                    state, epic_list, epic_stories_loader, state_path
                )

                # Story standalone-03 AC6: Dispatch epic_completed event (even on failure)
                _dispatch_event(
                    "epic_completed",
                    project_path,
                    state,
                    duration_ms=epic_duration_ms,
                    stories_completed=epic_stories_count,
                )

                if is_project_complete:
                    # Story standalone-03 AC7: Dispatch project_completed event
                    project_duration_ms = get_project_duration_ms(state)
                    total_stories = len(state.completed_stories) if state.completed_stories else 0
                    _dispatch_event(
                        "project_completed",
                        project_path,
                        state,
                        duration_ms=project_duration_ms,
                        epics_completed=len(epic_list),
                        stories_completed=total_stories,
                    )
                    logger.info(
                        "Project complete after RETROSPECTIVE failure. All %d epics finished.",
                        len(epic_list),
                    )
                    return LoopExitReason.COMPLETED
                else:
                    state = new_state
                    # Story standalone-03 AC6: Start timing for the new epic
                    start_epic_timing(state)
                    start_story_timing(state)
                    logger.info(
                        "Advanced to next epic %s (story %s) after RETROSPECTIVE failure.",
                        state.current_epic,
                        state.current_story,
                    )
                    continue

            # AC5: Save state FIRST (before guardian call) to preserve position
            save_state(state, state_path)
            # Story 20.10: Invoke sync callbacks after failure path save
            _invoke_sprint_sync(state, project_path)

            # AC5: Guardian check for anomaly
            guardian_decision = guardian_check_anomaly(result, state)

            # Code Review Fix: Use GuardianDecision enum instead of magic string
            if guardian_decision == GuardianDecision.HALT:
                # AC5: Guardian "halt" - stop loop for user intervention
                logger.info("Loop halted by guardian for user intervention")

                # Story 15.4: Dispatch queue_blocked event
                _dispatch_event(
                    "queue_blocked",
                    project_path,
                    state,
                    reason="guardian_halt",
                    waiting_tasks=0,
                )

                # Code Review Fix: Remove duplicate save - state already saved above
                return LoopExitReason.GUARDIAN_HALT

            # Story 6.6: Check for shutdown after failure path save_state
            if shutdown_requested():
                logger.info("Loop interrupted by signal, state saved")
                return _get_interrupt_exit_reason()

            # AC5: MVP guardian ALWAYS returns "continue" - proceed to next phase
            # Note: In MVP, failures don't block loop (acknowledged risk - NFR4 deferred to Epic 8)
            # Code Review Fix: Skip AC6 save below - already saved above before guardian
            continue

        # AC6: Save state after each phase completion (SUCCESS PATH ONLY)
        # NOTE: This saves on EVERY successful iteration for maximum crash resilience (NFR1).
        # Performance cost: ~N atomic writes per story (N = phases executed).
        # Optimization deferred until profiling shows I/O is bottleneck.

        # Save state BEFORE advancing - current_phase is the phase that just completed
        save_state(state, state_path)

        # Story 20.10: Invoke sync callbacks after success path save
        _invoke_sprint_sync(state, project_path)

        # Story 22.10 - Task 3: Check for pause flag at safe interrupt point (after state persist)
        from bmad_assist.core.loop.dashboard_events import emit_loop_paused, emit_loop_resumed
        from bmad_assist.core.loop.pause import (
            check_pause_flag,
            validate_state_for_pause,
            wait_for_resume,
        )

        if check_pause_flag(project_path):
            logger.info(
                "Pause detected - entering wait loop (phase %s completed)",
                state.current_phase.name if state.current_phase else "None",
            )

            # Validate state before pause (AC #3, #6)
            if not validate_state_for_pause(state_path):
                logger.error("State validation failed - unsafe to pause, continuing loop")
                # Continue loop instead of pausing with corrupted state
            else:
                # State is valid - emit paused event before entering wait loop
                sequence_id += 1
                emit_loop_paused(
                    run_id=run_id,
                    sequence_id=sequence_id,
                    current_phase=state.current_phase.name if state.current_phase else None,
                )

                # Wait for resume (pause.flag cleared) or stop request
                # shutdown_requested() is checked inside wait_for_resume (Story 22.10)
                resumed = wait_for_resume(project_path, stop_event=None, pause_timeout_minutes=60)

                if not resumed:
                    # Stop requested while paused or timeout
                    logger.info("Terminating loop after stop while paused")
                    return (
                        _get_interrupt_exit_reason()
                        if shutdown_requested()
                        else LoopExitReason.COMPLETED
                    )

                # Resumed - emit resumed event and continue loop
                sequence_id += 1
                emit_loop_resumed(run_id=run_id, sequence_id=sequence_id)
                logger.info("Resumed from pause - continuing to next phase")

        # Story 15.4: Dispatch phase_completed event with actual duration
        phase_duration = get_phase_duration_ms(state)
        _dispatch_event(
            "phase_completed",
            project_path,
            state,
            phase=state.current_phase.name if state.current_phase else "unknown",
            duration_ms=phase_duration,
        )

        # Git auto-commit for the COMPLETED phase (before advancing)
        # Only commits if phase is in COMMIT_PHASES (CREATE_STORY, DEV_STORY, CODE_REVIEW_SYNTHESIS)
        # Validation phases are NOT in COMMIT_PHASES, so their reports are not committed.
        # Lazy import to avoid circular dependency
        from bmad_assist.git import auto_commit_phase

        auto_commit_phase(
            phase=state.current_phase,
            story_id=state.current_story,
            project_path=project_path,
        )

        # Determine what to do next based on current phase
        current_phase = state.current_phase

        # AC3: CODE_REVIEW_SYNTHESIS success → handle story completion
        # CRITICAL: This check MUST happen before get_next_phase() because story completion
        # determines whether we advance to RETROSPECTIVE (epic complete) or next story.
        if current_phase == Phase.CODE_REVIEW_SYNTHESIS and result.success:
            # Archive multi-LLM artifacts (idempotent - safe if LLM already ran it)
            _run_archive_artifacts(project_path)

            # Get stories for current epic
            if state.current_epic is None:
                raise StateError("Logic error: current_epic is None at CODE_REVIEW_SYNTHESIS")

            # Code Review Fix: Wrap epic_stories_loader in try-except
            try:
                epic_stories = epic_stories_loader(state.current_epic)
            except Exception as e:
                raise StateError(
                    f"Failed to load stories for epic {state.current_epic}: {e}"
                ) from e

            # Story 15.4: Dispatch story_completed event with TOTAL story duration
            story_duration = get_story_duration_ms(state)
            _dispatch_event(
                "story_completed",
                project_path,
                state,
                duration_ms=story_duration,
                outcome="success",
            )

            new_state, is_epic_complete = handle_story_completion(state, epic_stories, state_path)

            if is_epic_complete:
                # AC3: Last story in epic - run_loop sets phase to RETROSPECTIVE
                state = new_state.model_copy(update={"current_phase": Phase.RETROSPECTIVE})
                save_state(state, state_path)
                # Story 20.10: Invoke sync callbacks after RETROSPECTIVE transition save
                _invoke_sprint_sync(state, project_path)
                logger.info(
                    "Epic %s stories complete, starting retrospective",
                    state.current_epic,
                )

                # Story 6.6: Check for shutdown after RETROSPECTIVE transition save_state
                if shutdown_requested():
                    logger.info("Loop interrupted by signal, state saved")
                    return _get_interrupt_exit_reason()
            else:
                # AC3: Not last story - advance to next story
                state = new_state
                # Start timing for the new story
                start_story_timing(state)
                # Story 20.10: Sync after story completion (non-last in epic)
                _invoke_sprint_sync(state, project_path)
                logger.info(
                    "Advanced to story %s at phase %s",
                    state.current_story,
                    state.current_phase.name if state.current_phase else "None",
                )

                # Story 15.4: Dispatch story_started for new story
                story_title = _get_story_title(project_path, state.current_story or "")
                _dispatch_event(
                    "story_started",
                    project_path,
                    state,
                    phase=state.current_phase.name if state.current_phase else "CREATE_STORY",
                    story_title=story_title,
                )

                # Story 22.9: Emit dashboard story_transition and workflow_status events
                sequence_id += 1
                if state.current_epic is not None and state.current_story is not None:
                    story_id_str = str(state.current_story)
                    # Parse story_id using helper function
                    try:
                        epic_num, story_num = parse_story_id(story_id_str)
                    except ValueError:
                        # Fallback for standalone stories or non-standard IDs
                        # Use current_epic directly as EpicId (supports string epics)
                        epic_num = state.current_epic if state.current_epic is not None else 1
                        story_num = 1

                    # Get story title from story file or use default
                    # For now, use a slugified version of story_id as title
                    story_title = story_id_str.replace(".", "-").replace("_", "-").lower()

                    # Generate full story_id (epic-story-title format)
                    full_story_id = story_id_from_parts(epic_num, story_num, story_title)
                    emit_story_transition(
                        run_id=run_id,
                        sequence_id=sequence_id,
                        action="started",
                        epic_num=epic_num,
                        story_num=story_num,
                        story_id=full_story_id,
                        story_title=story_title,
                    )
                    emit_workflow_status(
                        run_id=run_id,
                        sequence_id=sequence_id,
                        epic_num=epic_num,
                        story_id=story_id_str,
                        phase=state.current_phase.name if state.current_phase else "CREATE_STORY",
                        phase_status="in-progress",
                    )

            continue

        # AC4: QA_PLAN_EXECUTE success → handle epic completion
        # Note: This is the FINAL phase of an epic (after RETROSPECTIVE → QA_PLAN_GENERATE → QA_PLAN_EXECUTE)
        if current_phase == Phase.QA_PLAN_EXECUTE and result.success:
            # Calculate epic timing before handle_epic_completion modifies state
            epic_duration_ms = get_epic_duration_ms(state)
            epic_stories_count = _count_epic_stories(state)

            new_state, is_project_complete = handle_epic_completion(
                state, epic_list, epic_stories_loader, state_path
            )

            # Story standalone-03 AC6: Dispatch epic_completed event
            _dispatch_event(
                "epic_completed",
                project_path,
                state,
                duration_ms=epic_duration_ms,
                stories_completed=epic_stories_count,
            )

            if is_project_complete:
                # Story standalone-03 AC7: Dispatch project_completed event
                project_duration_ms = get_project_duration_ms(state)
                total_stories = len(state.completed_stories) if state.completed_stories else 0
                _dispatch_event(
                    "project_completed",
                    project_path,
                    state,
                    duration_ms=project_duration_ms,
                    epics_completed=len(epic_list),
                    stories_completed=total_stories,
                )
                # AC4: Last epic - project complete, terminate gracefully
                logger.info(
                    "Project complete! All %d epics finished.",
                    len(epic_list),
                )
                return LoopExitReason.COMPLETED

            # AC4: Not last epic - advance to next epic
            state = new_state

            # Ensure we're on the correct branch for the new epic
            from bmad_assist.git.branch import ensure_epic_branch, is_git_enabled

            if is_git_enabled() and state.current_epic is not None:
                ensure_epic_branch(state.current_epic, project_path)

            # Story standalone-03 AC6: Start timing for the new epic
            start_epic_timing(state)
            start_story_timing(state)
            # Story 20.10: Sync after epic completion (non-last in project)
            _invoke_sprint_sync(state, project_path)
            logger.info(
                "Advanced to epic %s, story %s",
                state.current_epic,
                state.current_story,
            )

            # Story 15.4: Dispatch story_started for new epic's first story
            story_title = _get_story_title(project_path, state.current_story or "")
            _dispatch_event(
                "story_started",
                project_path,
                state,
                phase=state.current_phase.name if state.current_phase else "CREATE_STORY",
                story_title=story_title,
            )

            continue

        # Code Review Fix: Honor PhaseResult.next_phase override from handlers
        if result.next_phase is not None:
            now = datetime.now(UTC).replace(tzinfo=None)
            state = state.model_copy(
                update={
                    "current_phase": result.next_phase,
                    "updated_at": now,
                }
            )
            logger.info("Phase override: jumping to %s", result.next_phase.name)
            continue

        # AC7: Normal phase advancement via get_next_phase()
        # Note: When QA is disabled (--qa flag not set), RETROSPECTIVE is the last phase
        # and get_next_phase() returns None. In this case, handle epic completion.

        # Defensive check: current_phase could still be None if all prior
        # conditions failed (e.g., phase not in special cases). Verify before use.
        if current_phase is None:
            raise StateError("Logic error: current_phase is None in main loop")

        next_phase = get_next_phase(current_phase)
        if next_phase is None:
            # RETROSPECTIVE is last phase when QA disabled - handle epic completion
            if current_phase == Phase.RETROSPECTIVE and result.success:
                logger.info(
                    "RETROSPECTIVE complete for epic %s (QA phases disabled)",
                    state.current_epic,
                )
                # Calculate epic timing before handle_epic_completion modifies state
                epic_duration_ms = get_epic_duration_ms(state)
                completed_epic = state.current_epic
                epic_stories_count = _count_epic_stories(state)

                new_state, is_project_complete = handle_epic_completion(
                    state, epic_list, epic_stories_loader, state_path
                )

                # Story standalone-03 AC6: Dispatch epic_completed event
                _dispatch_event(
                    "epic_completed",
                    project_path,
                    state,  # Use original state with completed epic
                    duration_ms=epic_duration_ms,
                    stories_completed=epic_stories_count,
                )

                if is_project_complete:
                    # Story standalone-03 AC7: Dispatch project_completed event
                    project_duration_ms = get_project_duration_ms(state)
                    total_stories = len(state.completed_stories) if state.completed_stories else 0
                    _dispatch_event(
                        "project_completed",
                        project_path,
                        state,
                        duration_ms=project_duration_ms,
                        epics_completed=len(epic_list) if epic_list else 1,
                        stories_completed=total_stories,
                    )
                    logger.info(
                        "Project complete! All %d epics finished.",
                        len(epic_list) if epic_list else 1,
                    )
                    return LoopExitReason.COMPLETED

                # Not last epic - advance to next epic
                state = new_state

                # Ensure we're on the correct branch for the new epic
                from bmad_assist.git.branch import ensure_epic_branch, is_git_enabled

                if is_git_enabled() and state.current_epic is not None:
                    ensure_epic_branch(state.current_epic, project_path)

                # Story standalone-03 AC6: Start timing for the new epic
                start_epic_timing(state)
                start_story_timing(state)
                # Sync after epic completion
                _invoke_sprint_sync(state, project_path)
                logger.info(
                    "Advanced to epic %s, story %s",
                    state.current_epic,
                    state.current_story,
                )

                # Dispatch story_started for new epic's first story
                story_title = _get_story_title(project_path, state.current_story or "")
                _dispatch_event(
                    "story_started",
                    project_path,
                    state,
                    phase=state.current_phase.name if state.current_phase else "CREATE_STORY",
                    story_title=story_title,
                )

                continue

            # Other phases returning None is unexpected - raise error
            raise StateError(f"Cannot advance past {current_phase.name}")

        # Code Review Fix: Include updated_at in phase advancement
        now = datetime.now(UTC).replace(tzinfo=None)
        state = state.model_copy(
            update={
                "current_phase": next_phase,
                "updated_at": now,
            }
        )
        logger.debug(
            "Advanced to phase %s",
            next_phase.name,
        )

        # Story 22.9: Emit dashboard workflow_status event on phase transition
        sequence_id += 1
        if state.current_epic is not None and state.current_story is not None:
            emit_workflow_status(
                run_id=run_id,
                sequence_id=sequence_id,
                epic_num=state.current_epic,
                story_id=str(state.current_story),
                phase=next_phase.name,
                phase_status="in-progress",
            )
