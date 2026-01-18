"""SSE event schemas for dashboard status updates.

Story 22.9: SSE sidebar tree updates.

This module defines Pydantic schemas for SSE events that update the sidebar
tree in real-time during bmad-assist execution.

Event Types:
- workflow_status: Phase transition updates
- story_status: Story status changes
- story_transition: Story start/completion events

All events include base fields: type, timestamp (ISO 8601), run_id, sequence_id.
"""

import logging
import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Base Event Schema
# =============================================================================


class DashboardEvent(BaseModel):
    """Base schema for all dashboard SSE events.

    All events share these common fields for correlation and ordering.

    Attributes:
        type: Event type identifier.
        timestamp: ISO 8601 UTC timestamp.
        run_id: Run identifier (format: run-YYYYMMDD-HHMMSS-{uuid8}).
        sequence_id: Monotonic sequence number for ordering.

    """

    type: str
    timestamp: datetime
    run_id: str = Field(..., pattern=r"^run-\d{8}-\d{6}-[a-z0-9]{8}$")
    sequence_id: int = Field(..., ge=1)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is in UTC and has no timezone info (naive UTC)."""
        if v.tzinfo is not None:
            # Convert to naive UTC (project convention)
            return v.astimezone(UTC).replace(tzinfo=None)
        return v

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, v: str) -> str:
        """Validate run_id format."""
        pattern = r"^run-(\d{8})-(\d{6})-([a-z0-9]{8})$"
        match = re.match(pattern, v)
        if not match:
            raise ValueError(f"run_id must match format run-YYYYMMDD-HHMMSS-{{uuid8}}, got: {v}")
        return v


# =============================================================================
# Workflow Status Event (Phase Transitions)
# =============================================================================


class WorkflowStatusData(BaseModel):
    """Data payload for workflow_status event.

    Emitted when the main loop transitions between phases.

    Attributes:
        current_epic: Current epic number.
        current_story: Current story ID (e.g., "22.9").
        current_phase: Current workflow phase.
        phase_status: Status of current phase (pending, in-progress, completed, failed).

    """

    current_epic: int = Field(..., ge=1)
    current_story: str = Field(..., pattern=r"^\d+\.\d+$")
    current_phase: Literal[
        "CREATE_STORY",
        "VALIDATE_STORY",
        "DEV_STORY",
        "CODE_REVIEW",
        "CODE_REVIEW_SYNTHESIS",
        "RETROSPECTIVE",
    ]
    phase_status: Literal["pending", "in-progress", "completed", "failed"]


class WorkflowStatusEvent(DashboardEvent):
    """Event emitted on phase transitions.

    AC1: Emitted when main loop transitions between phases with current_phase,
    current_story, sequence_id, timestamp, run_id fields.

    Example:
        {
            "type": "workflow_status",
            "timestamp": "2026-01-15T08:00:00Z",
            "run_id": "run-20260115-080000-a1b2c3d4",
            "sequence_id": 1,
            "data": {
                "current_epic": 22,
                "current_story": "22.9",
                "current_phase": "DEV_STORY",
                "phase_status": "in_progress"
            }
        }

    """

    type: Literal["workflow_status"] = "workflow_status"
    data: WorkflowStatusData


# =============================================================================
# Story Status Event (Story Status Changes)
# =============================================================================


class StoryStatusData(BaseModel):
    """Data payload for story_status event.

    Emitted when a story's status changes.

    Attributes:
        epic_num: Epic number.
        story_num: Story number (just the number part).
        story_id: Full story ID (e.g., "22-9-sse-sidebar-tree-updates").
        status: New story status.
        previous_status: Previous story status (optional).

    """

    epic_num: int = Field(..., ge=1)
    story_num: int = Field(..., ge=1)
    story_id: str = Field(..., pattern=r"^\d+-\d+-[\w-]+$")
    status: Literal["backlog", "ready-for-dev", "in-progress", "review", "done"]
    previous_status: Literal["backlog", "ready-for-dev", "in-progress", "review", "done"] | None = (
        None
    )


class StoryStatusEvent(DashboardEvent):
    """Event emitted when story status changes.

    AC2: Emitted when story transitions from one status to another with story_id,
    epic_num, story_num, status, sequence_id, timestamp, run_id fields.

    Example:
        {
            "type": "story_status",
            "timestamp": "2026-01-15T08:00:00Z",
            "run_id": "run-20260115-080000-a1b2c3d4",
            "sequence_id": 2,
            "data": {
                "epic_num": 22,
                "story_num": 9,
                "story_id": "22-9-sse-sidebar-tree-updates",
                "status": "in-progress",
                "previous_status": "ready-for-dev"
            }
        }

    """

    type: Literal["story_status"] = "story_status"
    data: StoryStatusData


# =============================================================================
# Story Transition Event (Story Start/Completion)
# =============================================================================


class StoryTransitionData(BaseModel):
    """Data payload for story_transition event.

    Emitted when a new story is started or the current story completes.

    Attributes:
        action: Either "started" or "completed".
        epic_num: Epic number.
        story_num: Story number (just the number part).
        story_id: Full story ID (e.g., "22-9-sse-sidebar-tree-updates").
        story_title: Story title (slug).

    """

    action: Literal["started", "completed"]
    epic_num: int = Field(..., ge=1)
    story_num: int = Field(..., ge=1)
    story_id: str = Field(..., pattern=r"^\d+-\d+-[\w-]+$")
    story_title: str = Field(..., min_length=1)


class StoryTransitionEvent(DashboardEvent):
    """Event emitted on story transitions.

    AC3: Emitted when new story starts or current story completes with epic_num,
    story_num, story_id, story_title, action, sequence_id, timestamp, run_id fields.

    Example (started):
        {
            "type": "story_transition",
            "timestamp": "2026-01-15T08:00:00Z",
            "run_id": "run-20260115-080000-a1b2c3d4",
            "sequence_id": 3,
            "data": {
                "action": "started",
                "epic_num": 22,
                "story_num": 9,
                "story_id": "22-9-sse-sidebar-tree-updates",
                "story_title": "sse-sidebar-tree-updates"
            }
        }
    """

    type: Literal["story_transition"] = "story_transition"
    data: StoryTransitionData


# =============================================================================
# Event Factory
# =============================================================================


def create_workflow_status(
    run_id: str,
    sequence_id: int,
    epic_num: int,
    story_id: str,
    phase: str,
    phase_status: str,
) -> WorkflowStatusEvent:
    """Create a workflow_status event.

    Args:
        run_id: Run identifier.
        sequence_id: Sequence number.
        epic_num: Current epic number.
        story_id: Current story ID (e.g., "22.9").
        phase: Current phase name.
        phase_status: Phase status.

    Returns:
        WorkflowStatusEvent instance.

    """
    # Extract story_num from story_id (e.g., "22.9" -> 9)
    story_num = int(story_id.split(".")[-1])

    return WorkflowStatusEvent(
        type="workflow_status",
        timestamp=datetime.now(UTC),
        run_id=run_id,
        sequence_id=sequence_id,
        data=WorkflowStatusData(
            current_epic=epic_num,
            current_story=story_id,
            current_phase=phase,
            phase_status=phase_status,
        ),
    )


def create_story_status(
    run_id: str,
    sequence_id: int,
    epic_num: int,
    story_num: int,
    story_id: str,
    status: str,
    previous_status: str | None = None,
) -> StoryStatusEvent:
    """Create a story_status event.

    Args:
        run_id: Run identifier.
        sequence_id: Sequence number.
        epic_num: Epic number.
        story_num: Story number.
        story_id: Full story ID (e.g., "22-9-sse-sidebar-tree-updates").
        status: New story status.
        previous_status: Previous story status (optional).

    Returns:
        StoryStatusEvent instance.

    """
    return StoryStatusEvent(
        type="story_status",
        timestamp=datetime.now(UTC),
        run_id=run_id,
        sequence_id=sequence_id,
        data=StoryStatusData(
            epic_num=epic_num,
            story_num=story_num,
            story_id=story_id,
            status=status,
            previous_status=previous_status,
        ),
    )


def create_story_transition(
    run_id: str,
    sequence_id: int,
    action: str,
    epic_num: int,
    story_num: int,
    story_id: str,
    story_title: str,
) -> StoryTransitionEvent:
    """Create a story_transition event.

    Args:
        run_id: Run identifier.
        sequence_id: Sequence number.
        action: Either "started" or "completed".
        epic_num: Epic number.
        story_num: Story number.
        story_id: Full story ID (e.g., "22-9-sse-sidebar-tree-updates").
        story_title: Story title.

    Returns:
        StoryTransitionEvent instance.

    """
    return StoryTransitionEvent(
        type="story_transition",
        timestamp=datetime.now(UTC),
        run_id=run_id,
        sequence_id=sequence_id,
        data=StoryTransitionData(
            action=action,
            epic_num=epic_num,
            story_num=story_num,
            story_id=story_id,
            story_title=story_title,
        ),
    )
