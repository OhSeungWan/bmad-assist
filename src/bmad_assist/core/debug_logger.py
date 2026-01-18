"""Debug JSON logger for provider communication.

Provides resilient append-only logging of raw JSON messages from provider
communication. Each message is immediately flushed to disk to survive:
- Connection interruptions
- User interrupts (Ctrl+C)
- Application crashes

Usage:
    logger = DebugJsonLogger(debug_dir)
    logger.append(json_line)  # First line with init extracts session_id
    logger.close()

    # Save prompts (when debug enabled)
    save_prompt(prompt, phase_name)

File format:
    ~/.bmad-assist/debug/json/{timestamp}-{session_id}.jsonl
    ~/.bmad-assist/debug/prompts/{timestamp}-{phase_name}.xml

Timestamp format uses compact date-time for readability and sorting:
    25.12.14-17.30 (YY.MM.DD-HH.MM)
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Default debug directories under user home
DEBUG_DIR = Path.home() / ".bmad-assist" / "debug" / "json"
PROMPTS_DIR = Path.home() / ".bmad-assist" / "debug" / "prompts"

# Maximum size for a single JSON line (1MB) - truncate larger messages
MAX_LINE_SIZE = 1024 * 1024


def save_prompt(prompt: str, phase_name: str, enabled: bool | None = None) -> Path | None:
    """Save prompt to debug/prompts directory.

    Only saves when debug logging is enabled. Creates timestamped file
    for easy correlation with JSONL session logs.

    Args:
        prompt: The full prompt text to save.
        phase_name: Phase name (e.g., 'create_story') for filename.
        enabled: Force enable/disable. If None, uses logger.isEnabledFor(DEBUG).

    Returns:
        Path to saved file if written, None otherwise.

    """
    if enabled is None:
        enabled = logger.isEnabledFor(logging.DEBUG)

    if not enabled:
        return None

    # Create timestamp matching JSONL format
    now = datetime.now().astimezone()
    timestamp = now.strftime("%y.%m.%d-%H.%M.%S")

    # Ensure directory exists
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    # Create file: {timestamp}-{phase_name}.xml
    file_path = PROMPTS_DIR / f"{timestamp}-{phase_name}.xml"

    try:
        file_path.write_text(prompt, encoding="utf-8")
        logger.debug("Saved prompt: %s (%d chars)", file_path, len(prompt))
        return file_path
    except OSError as e:
        logger.warning("Failed to save prompt: %s - %s", file_path, e)
        return None


class DebugJsonLogger:
    """Resilient append-only JSON logger for provider communication.

    Each append() call opens the file, writes, flushes, and closes immediately.
    This ensures data survives crashes, interrupts, and connection failures.

    The first append() with a valid init message extracts session_id and creates
    the file with proper naming: {timestamp}-{session_id}.jsonl

    Attributes:
        debug_dir: Directory for debug log files.
        file_path: Path to the debug log file (set after first init message).
        session_id: Provider session ID (extracted from first init message).
        enabled: Whether logging is active.
        run_timestamp: External timestamp for consistent naming across a run.

    """

    def __init__(
        self,
        debug_dir: Path | None = None,
        enabled: bool | None = None,
        run_timestamp: datetime | None = None,
    ) -> None:
        """Initialize debug logger.

        Args:
            debug_dir: Directory for debug files. Defaults to ~/.bmad-assist/debug/json
            enabled: Whether to actually write. If None, uses logger.isEnabledFor(DEBUG).
            run_timestamp: External timestamp for filename. If None, uses current time.
                Use this to ensure consistent timestamps across a validation run.

        """
        if enabled is None:
            enabled = logger.isEnabledFor(logging.DEBUG)

        self.debug_dir = debug_dir or DEBUG_DIR
        self.enabled = enabled
        self.file_path: Path | None = None
        self.session_id: str | None = None
        self._run_timestamp = run_timestamp
        self._timestamp: str | None = None
        self._line_count = 0
        self._pending_lines: list[str] = []  # Buffer until we get session_id

    def _create_file(self, session_id: str) -> None:
        """Create log file with session_id in filename.

        Args:
            session_id: Provider session identifier from init message.

        """
        self.session_id = session_id

        # Use external timestamp if provided, otherwise generate now
        ts = self._run_timestamp or datetime.now().astimezone()
        # Format: 25.12.14-17.30 (YY.MM.DD-HH.MM)
        self._timestamp = ts.strftime("%y.%m.%d-%H.%M")

        # Filename: {timestamp}-{session_id}.jsonl (date first for sorting)
        self.file_path = self.debug_dir / f"{self._timestamp}-{session_id}.jsonl"

        # Ensure directory exists
        self.debug_dir.mkdir(parents=True, exist_ok=True)

        logger.debug("Debug log created: %s", self.file_path)

        # Flush any pending lines
        for line in self._pending_lines:
            self._write_line(line)
        self._pending_lines.clear()

    def _write_line(self, json_line: str) -> None:
        """Write single line to file with immediate flush.

        Args:
            json_line: Raw JSON line to write.

        Note:
            Lines exceeding MAX_LINE_SIZE are truncated to prevent
            test artifacts or anomalous outputs from creating huge files.

        """
        if self.file_path is None:
            return

        line = json_line.rstrip("\n")

        # Truncate excessively long lines (e.g., test data with 10MB content)
        if len(line) > MAX_LINE_SIZE:
            truncated_marker = f'..."[TRUNCATED: {len(line)} chars -> {MAX_LINE_SIZE}]"'
            # Find a safe truncation point before the marker
            safe_len = MAX_LINE_SIZE - len(truncated_marker) - 10
            line = line[:safe_len] + truncated_marker
            logger.debug("Truncated debug log line: %d -> %d chars", len(json_line), len(line))

        line = line + "\n"

        try:
            # Atomic append: open → write → fsync → close
            fd = os.open(
                self.file_path,
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                0o644,
            )
            try:
                os.write(fd, line.encode("utf-8"))
                os.fsync(fd)  # Force write to disk
            finally:
                os.close(fd)

            self._line_count += 1

        except OSError as e:
            logger.warning("Failed to write debug log: %s - %s", self.file_path, e)

    def _extract_session_id(self, json_line: str) -> str | None:
        """Try to extract session_id from init message.

        Handles multiple provider formats:
        - Claude: {"type": "system", "subtype": "init", "session_id": "..."}
        - Codex: {"type": "thread.started", "thread_id": "..."}
        - Gemini: {"type": "init", "session_id": "..."}

        Args:
            json_line: Raw JSON line.

        Returns:
            Session ID if this is an init message, None otherwise.

        """
        try:
            msg = json.loads(json_line)
            msg_type = msg.get("type", "")

            # Claude format: type=system, subtype=init
            if msg_type == "system" and msg.get("subtype") == "init":
                session_id = msg.get("session_id")
                return session_id if isinstance(session_id, str) else None

            # Codex format: type=thread.started, thread_id
            if msg_type == "thread.started":
                thread_id = msg.get("thread_id")
                return thread_id if isinstance(thread_id, str) else None

            # Gemini format: type=init, session_id
            if msg_type == "init":
                session_id = msg.get("session_id")
                return session_id if isinstance(session_id, str) else None

        except (json.JSONDecodeError, AttributeError):
            pass
        return None

    def append(self, json_line: str) -> None:
        """Append JSON line to log file with immediate flush.

        First call with init message extracts session_id and creates the file.
        Each write: open → write → fsync → close (survives crashes).

        Args:
            json_line: Raw JSON line from provider stream.

        """
        if not self.enabled:
            return

        # Skip empty lines
        if not json_line or not json_line.strip():
            return

        # If we don't have session_id yet, try to extract it
        if self.session_id is None:
            session_id = self._extract_session_id(json_line)
            if session_id:
                self._create_file(session_id)
                self._write_line(json_line)
            else:
                # Buffer until we get session_id (shouldn't happen normally)
                self._pending_lines.append(json_line)
        else:
            self._write_line(json_line)

    def close(self) -> None:
        """Close logger and log summary.

        Data is already flushed after each append - this just logs summary.

        """
        if not self.enabled:
            return

        # Write any remaining buffered lines to fallback file
        if self._pending_lines and self.file_path is None:
            # No session_id received - create fallback file with unique suffix
            # Use external timestamp if provided, otherwise generate now
            # Use microseconds + PID to avoid collisions when multiple providers
            # run in parallel and all fail to extract session_id
            ts = self._run_timestamp or datetime.now().astimezone()
            timestamp = ts.strftime("%y.%m.%d-%H.%M.%S")
            unique_suffix = f"{ts.microsecond:06d}-{os.getpid()}"
            self.file_path = self.debug_dir / f"{timestamp}-unknown-{unique_suffix}.jsonl"
            self.debug_dir.mkdir(parents=True, exist_ok=True)

            for line in self._pending_lines:
                self._write_line(line)
            self._pending_lines.clear()

        if self._line_count > 0:
            logger.debug(
                "Debug log complete: %s (%d lines)",
                self.file_path,
                self._line_count,
            )

    @property
    def path(self) -> Path | None:
        """Return log file path if created, None otherwise."""
        return self.file_path

    @property
    def provider_session_id(self) -> str | None:
        """Return extracted provider session_id if available.

        This is the session_id/thread_id from the provider init message,
        useful for creating traceability links (e.g., original_ref in anonymization).
        """
        return self.session_id
