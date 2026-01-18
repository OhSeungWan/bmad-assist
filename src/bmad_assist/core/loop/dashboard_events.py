"""Dashboard event broadcasting for main loop.

Story 22.9: SSE sidebar tree updates.
Story 22.10: Pause/resume events.

This module provides functions for emitting dashboard events from the main loop
via stdout markers. The dashboard server parses these markers and broadcasts
SSE events to connected clients.

IPC Protocol:
- Main loop (subprocess) prints DASHBOARD_EVENT:{json_payload} to stdout
- Dashboard server parses stdout for DASHBOARD_EVENT markers
- Validated events are broadcast via SSE broadcaster

Events:
- workflow_status: Phase transitions
- story_status: Story status changes
- story_transition: Story start/completion
- LOOP_PAUSED: Pause entered (Story 22.10)
- LOOP_RESUMED: Pause exited (Story 22.10)
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import UTC, datetime
from typing import Literal

from bmad_assist.core.types import EpicId

logger = logging.getLogger(__name__)

# Dashboard event marker prefix
DASHBOARD_EVENT_MARKER = "DASHBOARD_EVENT:"

# =============================================================================
# Event Emission Functions (Main Loop / Subprocess)
# =============================================================================


def _emit_dashboard_event(event_data: dict[str, object]) -> None:
    """Emit a dashboard event via stdout marker.

    This function prints a DASHBOARD_EVENT marker to stdout with JSON payload.
    The dashboard server parses stdout for these markers and broadcasts via SSE.

    Events are only emitted when BMAD_DASHBOARD_MODE=1 environment variable is set.
    This prevents noise in CLI output when running without the dashboard.

    Args:
        event_data: Event data dictionary (will be JSON serialized).

    """
    # Only emit events when running as dashboard subprocess
    if os.environ.get("BMAD_DASHBOARD_MODE") != "1":
        return

    try:
        json_payload = json.dumps(event_data)
        print(f"{DASHBOARD_EVENT_MARKER}{json_payload}")
        sys.stdout.flush()  # Ensure immediate output
    except Exception as e:
        logger.debug("Failed to emit dashboard event (ignored): %s", e)


def emit_workflow_status(
    run_id: str,
    sequence_id: int,
    epic_num: EpicId,
    story_id: str,
    phase: str,
    phase_status: Literal["pending", "in-progress", "completed", "failed"],
) -> None:
    """Emit workflow_status event on phase transitions.

    AC1: SSE event emitted when main loop transitions between phases with
    current_phase, current_story, sequence_id, timestamp, run_id fields.

    Args:
        run_id: Run identifier.
        sequence_id: Monotonic sequence number.
        epic_num: Current epic number (supports string epics like "testarch").
        story_id: Current story ID (e.g., "22.9").
        phase: Current phase name (e.g., "DEV_STORY").
        phase_status: Phase status.

    Example output:
        DASHBOARD_EVENT:{"type":"workflow_status","timestamp":"2026-01-15T08:00:00Z",...}

    """
    event_data = {
        "type": "workflow_status",
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "sequence_id": sequence_id,
        "data": {
            "current_epic": epic_num,
            "current_story": story_id,
            "current_phase": phase,
            "phase_status": phase_status,
        },
    }
    _emit_dashboard_event(event_data)


def emit_story_status(
    run_id: str,
    sequence_id: int,
    epic_num: EpicId,
    story_num: int,
    story_id: str,
    status: Literal["backlog", "ready-for-dev", "in-progress", "review", "done"],
    previous_status: (
        Literal["backlog", "ready-for-dev", "in-progress", "review", "done"] | None
    ) = None,
) -> None:
    """Emit story_status event on story status changes.

    AC2: SSE event emitted when story status changes with story_id, epic_num,
    story_num, status, sequence_id, timestamp, run_id fields.

    Args:
        run_id: Run identifier.
        sequence_id: Monotonic sequence number.
        epic_num: Epic number (supports string epics like "testarch").
        story_num: Story number.
        story_id: Full story ID (e.g., "22-9-sse-sidebar-tree-updates").
        status: New story status.
        previous_status: Previous story status (optional).

    """
    event_data = {
        "type": "story_status",
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "sequence_id": sequence_id,
        "data": {
            "epic_num": epic_num,
            "story_num": story_num,
            "story_id": story_id,
            "status": status,
            "previous_status": previous_status,
        },
    }
    _emit_dashboard_event(event_data)


def emit_story_transition(
    run_id: str,
    sequence_id: int,
    action: Literal["started", "completed"],
    epic_num: EpicId,
    story_num: int,
    story_id: str,
    story_title: str,
) -> None:
    """Emit story_transition event on story start/completion.

    AC3: SSE event emitted when new story starts or current story completes
    with epic_num, story_num, story_id, story_title, action, sequence_id,
    timestamp, run_id fields.

    Args:
        run_id: Run identifier.
        sequence_id: Monotonic sequence number.
        action: Either "started" or "completed".
        epic_num: Epic number (supports string epics like "testarch").
        story_num: Story number.
        story_id: Full story ID (e.g., "22-9-sse-sidebar-tree-updates").
        story_title: Story title (slug).

    """
    event_data = {
        "type": "story_transition",
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "sequence_id": sequence_id,
        "data": {
            "action": action,
            "epic_num": epic_num,
            "story_num": story_num,
            "story_id": story_id,
            "story_title": story_title,
        },
    }
    _emit_dashboard_event(event_data)


# =============================================================================
# Run ID Generation
# =============================================================================


def generate_run_id() -> str:
    """Generate a unique run_id.

    Format: run-YYYYMMDD-HHMMSS-{uuid8}

    Returns:
        Run ID string.

    """
    import uuid

    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    uuid_suffix = str(uuid.uuid4())[:8]
    return f"run-{timestamp}-{uuid_suffix}"


# =============================================================================
# Story ID Parsing Helpers
# =============================================================================


def parse_story_id(story_id: str) -> tuple[int, int]:
    """Parse story ID into epic_num and story_num.

    Args:
        story_id: Story ID in format "epic.story" (e.g., "22.9").

    Returns:
        Tuple of (epic_num, story_num).

    Raises:
        ValueError: If story_id format is invalid.

    Examples:
        >>> parse_story_id("22.9")
        (22, 9)
        >>> parse_story_id("1.10")
        (1, 10)

    """
    parts = story_id.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid story_id format: {story_id} (expected 'epic.story')")

    try:
        epic_num = int(parts[0])
        story_num = int(parts[1])
        return epic_num, story_num
    except ValueError as e:
        raise ValueError(f"Invalid story_id format: {story_id} (numeric parts required)") from e


def story_id_from_parts(epic_num: int, story_num: int, title: str) -> str:
    """Generate story_id from epic_num, story_num, and title.

    Args:
        epic_num: Epic number.
        story_num: Story number.
        title: Story title (will be slugified).

    Returns:
        Story ID in format "epic-story-title-slug".

    Examples:
        >>> story_id_from_parts(22, 9, "SSE Sidebar Tree Updates")
        '22-9-sse-sidebar-tree-updates'

    """
    # Slugify title: lowercase, replace spaces/hyphens with single hyphen
    slug = title.lower().strip()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r"[\s_]+", "-", slug)
    # Remove non-alphanumeric characters (except hyphens)
    slug = re.sub(r"[^a-z0-9-]+", "", slug)
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    return f"{epic_num}-{story_num}-{slug}"


# =============================================================================
# Story 22.10: Pause/Resume events
# =============================================================================


def emit_loop_paused(
    run_id: str,
    sequence_id: int,
    current_phase: str | None,
) -> None:
    """Emit LOOP_PAUSED event when main loop enters pause wait loop (Story 22.10).

    This event signals to the dashboard that the loop is now paused and waiting
    for resume. The frontend will display the "Paused" status and show the
    Resume button.

    Args:
        run_id: Run identifier.
        sequence_id: Monotonic sequence number.
        current_phase: Current phase name (e.g., "DEV_STORY") when paused.

    Example output:
        DASHBOARD_EVENT:{"type":"LOOP_PAUSED","timestamp":"2026-01-15T08:00:00Z",...}

    """
    event_data = {
        "type": "LOOP_PAUSED",
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "sequence_id": sequence_id,
        "data": {
            "current_phase": current_phase,
        },
    }
    _emit_dashboard_event(event_data)


def emit_loop_resumed(
    run_id: str,
    sequence_id: int,
) -> None:
    """Emit LOOP_RESUMED event when main loop exits pause wait loop (Story 22.10).

    This event signals to the dashboard that the loop has resumed from pause.
    The frontend will hide the "Paused" status and Resume button, and show the
    Pause button again.

    Args:
        run_id: Run identifier.
        sequence_id: Monotonic sequence number.

    Example output:
        DASHBOARD_EVENT:{"type":"LOOP_RESUMED","timestamp":"2026-01-15T08:00:00Z",...}

    """
    event_data = {
        "type": "LOOP_RESUMED",
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "sequence_id": sequence_id,
        "data": {},
    }
    _emit_dashboard_event(event_data)


# =============================================================================
# Re-export for convenience
# =============================================================================


__all__ = [
    # Marker constant
    "DASHBOARD_EVENT_MARKER",
    # Run ID generation
    "generate_run_id",
    # Story ID parsing
    "parse_story_id",
    "story_id_from_parts",
    # Event emission
    "emit_workflow_status",
    "emit_story_status",
    "emit_story_transition",
    # Story 22.10: Pause/resume events
    "emit_loop_paused",
    "emit_loop_resumed",
]
