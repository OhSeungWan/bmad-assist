"""Event types and payload models for notification system.

This module defines the EventType enum for all notification events and
Pydantic models for validated, immutable event payloads.

Example:
    >>> from bmad_assist.notifications import EventType, StoryStartedPayload
    >>> payload = StoryStartedPayload(
    ...     project="my-project",
    ...     epic=15,
    ...     story="15-1",
    ...     phase="CREATE_STORY"
    ... )
    >>> is_high_priority(EventType.ERROR_OCCURRED)
    True

"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from bmad_assist.core.types import EpicId


class EventType(StrEnum):
    """Notification event types.

    Events are classified by priority:
    - HIGH: ANOMALY_DETECTED, QUEUE_BLOCKED, ERROR_OCCURRED,
            TIMEOUT_WARNING, CLI_CRASHED, CLI_RECOVERED, FATAL_ERROR
    - NORMAL: STORY_STARTED, STORY_COMPLETED, PHASE_COMPLETED,
              EPIC_COMPLETED, PROJECT_COMPLETED

    HIGH priority events indicate conditions requiring immediate attention
    and may trigger additional notification channels or escalation.

    Infrastructure events (Story 21.4):
    - TIMEOUT_WARNING: Proactive warning when CLI approaches timeout limit
    - CLI_CRASHED: CLI tool crashed (may have recovered or exceeded max retries)
    - CLI_RECOVERED: CLI tool crashed but workflow recovered after retry
    - FATAL_ERROR: bmad-assist process encountered unrecoverable error

    Completion events (Story standalone-03):
    - EPIC_COMPLETED: All stories in epic finished (includes cumulative duration)
    - PROJECT_COMPLETED: All epics finished (includes total project duration)
    """

    STORY_STARTED = "story_started"
    STORY_COMPLETED = "story_completed"
    PHASE_COMPLETED = "phase_completed"
    # Completion events (Story standalone-03 AC6/AC7)
    EPIC_COMPLETED = "epic_completed"
    PROJECT_COMPLETED = "project_completed"
    ANOMALY_DETECTED = "anomaly_detected"
    QUEUE_BLOCKED = "queue_blocked"
    ERROR_OCCURRED = "error_occurred"
    # Infrastructure events (Story 21.4)
    TIMEOUT_WARNING = "timeout_warning"
    CLI_CRASHED = "cli_crashed"
    CLI_RECOVERED = "cli_recovered"
    FATAL_ERROR = "fatal_error"


HIGH_PRIORITY_EVENTS: frozenset[EventType] = frozenset(
    {
        EventType.ANOMALY_DETECTED,
        EventType.QUEUE_BLOCKED,
        EventType.ERROR_OCCURRED,
        # Infrastructure events (Story 21.4) - all HIGH priority
        EventType.TIMEOUT_WARNING,
        EventType.CLI_CRASHED,
        EventType.CLI_RECOVERED,
        EventType.FATAL_ERROR,
    }
)


def is_high_priority(event: EventType) -> bool:
    """Check if event is high priority (requires immediate attention).

    HIGH priority events: anomaly_detected, queue_blocked, error_occurred,
    timeout_warning, cli_crashed, cli_recovered, fatal_error.

    Args:
        event: Event type to check.

    Returns:
        True if event is high priority, False otherwise.

    """
    return event in HIGH_PRIORITY_EVENTS


class EventPayload(BaseModel):
    """Base payload for all notification events.

    Frozen for immutability - prevents race conditions during async dispatch.

    Attributes:
        timestamp: UTC timestamp when event occurred (auto-generated).
        project: Project name.
        epic: Epic identifier (int or str).
        story: Story identifier, or None for epic-level events.

    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    project: str
    epic: EpicId
    story: str | None = None


class StoryStartedPayload(EventPayload):
    """Payload for STORY_STARTED event.

    Attributes:
        story: Story identifier (required for story-level events).
        phase: Current workflow phase (Phase enum .value, e.g., "CREATE_STORY").
        story_title: Human-readable story title (optional, shown on second line).

    """

    story: str  # Override to make required for story-level events
    phase: str
    story_title: str | None = None


class StoryCompletedPayload(EventPayload):
    """Payload for STORY_COMPLETED event.

    Attributes:
        story: Story identifier (required for story-level events).
        duration_ms: Total story duration in milliseconds (must be >= 0).
        outcome: Completion outcome (e.g., "success", "failed").

    """

    story: str  # Override to make required for story-level events
    duration_ms: int = Field(ge=0)
    outcome: str


class EpicCompletedPayload(EventPayload):
    """Payload for EPIC_COMPLETED event (Story standalone-03 AC6).

    Sent when all stories in an epic have completed. Includes cumulative
    timing information for the entire epic execution.

    Attributes:
        duration_ms: Total epic duration in milliseconds (must be >= 0).
        stories_completed: Number of stories completed in this epic.

    """

    duration_ms: int = Field(ge=0)
    stories_completed: int = Field(ge=0)


class ProjectCompletedPayload(EventPayload):
    """Payload for PROJECT_COMPLETED event (Story standalone-03 AC7).

    Sent when all epics in the project have completed. Includes cumulative
    timing information for the entire project execution.

    Attributes:
        duration_ms: Total project duration in milliseconds (must be >= 0).
        epics_completed: Number of epics completed in this project.
        stories_completed: Total number of stories completed across all epics.

    """

    duration_ms: int = Field(ge=0)
    epics_completed: int = Field(ge=0)
    stories_completed: int = Field(ge=0)


class PhaseCompletedPayload(EventPayload):
    """Payload for PHASE_COMPLETED event.

    Attributes:
        phase: Completed phase (Phase enum .value, e.g., "DEV_STORY").
        next_phase: Next phase if any, or None if final.
        duration_ms: Phase duration in milliseconds (must be >= 0).

    """

    phase: str
    next_phase: str | None
    duration_ms: int = Field(ge=0, default=0)


class AnomalyDetectedPayload(EventPayload):
    """Payload for ANOMALY_DETECTED event (HIGH priority).

    Attributes:
        anomaly_type: Type/category of anomaly detected.
        context: Contextual information about the anomaly.
        suggested_actions: List of suggested remediation actions.

    """

    anomaly_type: str
    context: str
    suggested_actions: list[str]


class QueueBlockedPayload(EventPayload):
    """Payload for QUEUE_BLOCKED event (HIGH priority).

    Attributes:
        reason: Description of why queue is blocked.
        waiting_tasks: Number of tasks waiting in queue (must be >= 0).

    """

    reason: str
    waiting_tasks: int = Field(ge=0)


class ErrorOccurredPayload(EventPayload):
    """Payload for ERROR_OCCURRED event (HIGH priority).

    Attributes:
        error_type: Type/class of error that occurred.
        message: Error message.
        stack_trace: Optional stack trace for debugging.

    """

    error_type: str
    message: str
    stack_trace: str | None = None


# ============================================================================
# Infrastructure Event Payloads (Story 21.4)
# ============================================================================


class TimeoutWarningPayload(EventPayload):
    """Payload for TIMEOUT_WARNING event (HIGH priority).

    Sent proactively when CLI execution approaches configured timeout limit.
    Allows user intervention before hard timeout failure.

    Attributes:
        tool_name: CLI tool approaching timeout (e.g., "claude-code").
        elapsed_ms: Milliseconds elapsed since CLI start.
        limit_ms: Configured timeout limit in milliseconds.
        remaining_ms: Milliseconds remaining until timeout.

    """

    tool_name: str
    elapsed_ms: int = Field(ge=0)
    limit_ms: int = Field(gt=0)
    remaining_ms: int = Field(ge=0)


class CLICrashedPayload(EventPayload):
    """Payload for CLI_CRASHED and CLI_RECOVERED events (HIGH priority).

    CLI_CRASHED: Tool crashed and either recovered or exceeded max retries.
    CLI_RECOVERED: Alias for crashed with recovered=True.

    Attributes:
        tool_name: CLI tool that crashed (e.g., "claude-code", "gemini").
        exit_code: Process exit code if non-signal failure (e.g., exit(1)), or None.
        signal: Unix signal that killed the process, or None if not signal-based.
        attempt: Current retry attempt number (1-based).
        max_attempts: Maximum configured retry attempts.
        recovered: True if workflow resumed after crash, False if max retries exceeded.

    """

    tool_name: str
    exit_code: int | None = None
    signal: int | None = None
    attempt: int = Field(ge=1)
    max_attempts: int = Field(ge=1)
    recovered: bool


class FatalErrorPayload(EventPayload):
    """Payload for FATAL_ERROR event (HIGH priority).

    Sent when bmad-assist encounters an unrecoverable error and is terminating.

    Attributes:
        exception_type: Exception class name (e.g., "KeyError", "StateError").
        message: Error message (may be truncated to 500 chars).
        location: Source location as "filename:lineno" (e.g., "state.py:142").

    """

    exception_type: str
    message: str = Field(max_length=500)
    location: str


# ============================================================================
# Signal Name Helper (Story 21.4)
# ============================================================================

# Signal number to name mapping (POSIX signals)
SIGNAL_NAMES: dict[int, str] = {
    1: "SIGHUP",
    2: "SIGINT",
    3: "SIGQUIT",
    6: "SIGABRT",
    9: "SIGKILL",
    11: "SIGSEGV",
    13: "SIGPIPE",
    14: "SIGALRM",
    15: "SIGTERM",
}


def get_signal_name(signal: int | None) -> str | None:
    """Get human-readable signal name from signal number.

    Args:
        signal: Unix signal number (e.g., 9 for SIGKILL), or None.

    Returns:
        Signal name (e.g., "SIGKILL"), or None if unknown or None input.

    Examples:
        >>> get_signal_name(9)
        'SIGKILL'
        >>> get_signal_name(15)
        'SIGTERM'
        >>> get_signal_name(99)
        None
        >>> get_signal_name(None)
        None

    """
    if signal is None:
        return None
    return SIGNAL_NAMES.get(signal)


# ============================================================================
# Payload Models Registry
# ============================================================================

PAYLOAD_MODELS: dict[EventType, type[EventPayload]] = {
    # Existing events (6)
    EventType.STORY_STARTED: StoryStartedPayload,
    EventType.STORY_COMPLETED: StoryCompletedPayload,
    EventType.PHASE_COMPLETED: PhaseCompletedPayload,
    EventType.ANOMALY_DETECTED: AnomalyDetectedPayload,
    EventType.QUEUE_BLOCKED: QueueBlockedPayload,
    EventType.ERROR_OCCURRED: ErrorOccurredPayload,
    # Completion events (Story standalone-03 AC6/AC7)
    EventType.EPIC_COMPLETED: EpicCompletedPayload,
    EventType.PROJECT_COMPLETED: ProjectCompletedPayload,
    # Infrastructure events (4) - Story 21.4
    EventType.TIMEOUT_WARNING: TimeoutWarningPayload,
    EventType.CLI_CRASHED: CLICrashedPayload,
    EventType.CLI_RECOVERED: CLICrashedPayload,  # Same payload, different event
    EventType.FATAL_ERROR: FatalErrorPayload,
}
