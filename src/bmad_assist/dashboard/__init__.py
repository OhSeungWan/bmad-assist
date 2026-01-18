"""Dashboard module for bmad-assist.

This module provides a web-based control panel for bmad-assist with:
- Real-time visibility into the BMAD development loop via SSE
- Tree-based navigation of epics/stories/phases
- Context menu actions for workflow execution

Public API:
    DashboardServer: Main HTTP server class
    start_server: Convenience function to start dashboard
    set_output_hook: Register callback for output capture
    get_output_hook: Get current output callback
    register_output_bridge: Set up sync-to-async bridge
    unregister_output_bridge: Clear sync-to-async bridge
    sync_broadcast: Thread-safe broadcast from any thread
    detect_provider_from_line: Fallback provider detection
"""

import asyncio
import re
from typing import Protocol

from bmad_assist.dashboard.server import DashboardServer, start_server
from bmad_assist.dashboard.sse import SSEBroadcaster

# =============================================================================
# Output Callback Protocol and Hook
# =============================================================================


class OutputCallback(Protocol):
    """Protocol for output capture callbacks.

    Called by write_progress() to notify listeners of new output lines.
    """

    def __call__(self, line: str, provider: str | None) -> None:
        """Handle output line.

        Args:
            line: Output line text.
            provider: Provider name or None for generic output.

        """
        ...


# Module-level output hook (None = no hook registered)
_output_hook: OutputCallback | None = None


def set_output_hook(callback: OutputCallback | None) -> None:
    """Register callback for output capture.

    Args:
        callback: Callback function or None to clear.

    """
    global _output_hook
    _output_hook = callback


def get_output_hook() -> OutputCallback | None:
    """Get current output callback.

    Returns:
        Current callback or None if not set.

    """
    return _output_hook


# =============================================================================
# Sync-to-Async Bridge for SSE Broadcasting
# =============================================================================

# Store event loop and broadcaster references for cross-thread access
_event_loop: asyncio.AbstractEventLoop | None = None
_broadcaster: SSEBroadcaster | None = None


def register_output_bridge(loop: asyncio.AbstractEventLoop, broadcaster: SSEBroadcaster) -> None:
    """Register event loop and broadcaster for output bridging.

    Called during server startup to enable sync_broadcast() from worker threads.

    Args:
        loop: Server's event loop.
        broadcaster: SSE broadcaster instance.

    """
    global _event_loop, _broadcaster
    _event_loop = loop
    _broadcaster = broadcaster


def unregister_output_bridge() -> None:
    """Clear event loop and broadcaster references.

    Called during server shutdown.
    """
    global _event_loop, _broadcaster
    _event_loop = None
    _broadcaster = None


def sync_broadcast(line: str, provider: str | None) -> None:
    """Thread-safe broadcast from any thread to server's event loop.

    Fire-and-forget: schedules broadcast_output() in the server's event loop
    without waiting for result. Safe to call from worker threads.

    Args:
        line: Output line text.
        provider: Provider name or None.

    """
    if _broadcaster is None or _event_loop is None:
        return
    if not _event_loop.is_running():
        return
    # Fire-and-forget: schedule in server's event loop from ANY thread
    asyncio.run_coroutine_threadsafe(
        _broadcaster.broadcast_output(line, provider),
        _event_loop,
    )


# =============================================================================
# Provider Detection from Line Content
# =============================================================================

# ANSI escape code pattern for stripping
_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def detect_provider_from_line(line: str) -> str | None:
    """Detect provider from output line content.

    Fallback detection when thread-local context is unavailable.
    Strips ANSI codes before pattern matching.

    Args:
        line: Output line (may contain ANSI escape codes).

    Returns:
        Provider name ("gemini", "glm") or None for generic output.

    """
    # Strip ANSI escape codes
    clean_line = _ANSI_ESCAPE_RE.sub("", line).lower()

    # Check for provider-specific patterns
    if "gemini" in clean_line:
        return "gemini"
    if "glm" in clean_line or "zhipu" in clean_line:
        return "glm"

    return None


__all__ = [
    "DashboardServer",
    "start_server",
    # Output capture API
    "OutputCallback",
    "set_output_hook",
    "get_output_hook",
    "register_output_bridge",
    "unregister_output_bridge",
    "sync_broadcast",
    "detect_provider_from_line",
]
