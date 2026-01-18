"""Shared fixtures and helpers for provider tests.

This module provides mock factories for testing Popen-based providers that use
JSON streaming output (Codex with --json, Gemini with --output-format stream-json).

## Mock Process Factories

- `create_mock_process()` - Generic Popen mock with configurable stdout/stderr
- `create_codex_mock_process()` - Codex-specific mock with JSON stream format
- `create_gemini_mock_process()` - Gemini-specific mock with JSON stream format

## JSON Output Generators

- `make_codex_json_output()` - Creates Codex JSONL stream (thread.started, item.completed, etc.)
- `make_gemini_json_output()` - Creates Gemini JSONL stream (init, message, result)
- `make_claude_stream_json_output()` - Creates Claude stream-json format (system/init, assistant, result)

## Usage Example

```python
from .conftest import create_codex_mock_process

def test_codex_invoke(provider):
    with patch("bmad_assist.providers.codex.Popen") as mock_popen:
        mock_popen.return_value = create_codex_mock_process(
            response_text="Expected response",
            returncode=0,
        )
        result = provider.invoke("Hello")
        assert result.stdout == "Expected response"
```
"""

import json
from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

import pytest


def make_claude_stream_json_output(
    text: str = "Mock response", session_id: str = "test-session"
) -> str:
    """Create stream-json format output for testing.

    Args:
        text: Response text to include.
        session_id: Session ID for init message.

    Returns:
        Multi-line string with JSON stream messages.

    Note:
        The text appears ONLY in the assistant message, not in the result message,
        because the provider extracts text from assistant messages. The result
        message contains metadata only (cost, duration, turns).
    """
    lines = [
        json.dumps({"type": "system", "subtype": "init", "session_id": session_id}),
        json.dumps(
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
            }
        ),
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "total_cost_usd": 0.001,
                "duration_ms": 100,
                "num_turns": 1,
                "session_id": session_id,
            }
        ),
    ]
    return "\n".join(lines) + "\n"


def create_mock_process(
    stdout_content: str | None = None,
    stderr_content: str = "",
    returncode: int = 0,
    wait_side_effect: Exception | None = None,
    response_text: str = "Mock response",
) -> MagicMock:
    """Create a mock Popen process for testing.

    Args:
        stdout_content: Raw content for stdout. If None, generates stream-json.
        stderr_content: Content to return from stderr.readline()
        returncode: Exit code to return from wait()
        wait_side_effect: Exception to raise from wait() (e.g., TimeoutExpired)
        response_text: Text to include in stream-json output (if stdout_content is None)

    Returns:
        MagicMock configured to behave like a Popen process

    """
    mock_process = MagicMock()

    # Generate stream-json if no raw content provided
    if stdout_content is None:
        stdout_content = make_stream_json_output(response_text)

    # Create iterators for stdout/stderr line reading
    stdout_lines = stdout_content.split("\n") if stdout_content else []
    stderr_lines = stderr_content.split("\n") if stderr_content else []

    # Add newlines back except for empty strings at end
    stdout_iter = iter([line + "\n" if line else "" for line in stdout_lines])
    stderr_iter = iter([line + "\n" if line else "" for line in stderr_lines])

    mock_process.stdout.readline.side_effect = lambda: next(stdout_iter, "")
    mock_process.stderr.readline.side_effect = lambda: next(stderr_iter, "")
    mock_process.stdout.close = MagicMock()
    mock_process.stderr.close = MagicMock()

    # Mock stdin for providers that use stdin (Claude, Gemini)
    mock_process.stdin = MagicMock()

    # Track write() calls for verification
    write_args: list[str] = []

    def capture_write(arg: str) -> None:
        write_args.append(arg)

    mock_process.stdin.write = MagicMock(side_effect=capture_write)
    mock_process.stdin.write_args = write_args  # type: ignore
    mock_process.stdin.close = MagicMock()

    if wait_side_effect:
        mock_process.wait.side_effect = wait_side_effect
    else:
        mock_process.wait.return_value = returncode

    mock_process.kill = MagicMock()

    return mock_process


def make_codex_json_output(text: str = "Mock response", thread_id: str = "test-thread") -> str:
    """Create Codex --json format output for testing.

    Args:
        text: Response text to include.
        thread_id: Thread ID for init message.

    Returns:
        Multi-line string with Codex JSON stream messages.
    """
    lines = [
        json.dumps({"type": "thread.started", "thread_id": thread_id}),
        json.dumps({"type": "turn.started"}),
        json.dumps(
            {
                "type": "item.completed",
                "item": {"id": "item_1", "type": "agent_message", "text": text},
            }
        ),
        json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 50}}),
    ]
    return "\n".join(lines) + "\n"


def make_gemini_json_output(text: str = "Mock response", session_id: str = "test-session") -> str:
    """Create Gemini --output-format stream-json output for testing.

    Args:
        text: Response text to include.
        session_id: Session ID for init message.

    Returns:
        Multi-line string with Gemini JSON stream messages.
    """
    lines = [
        json.dumps({"type": "init", "session_id": session_id, "model": "gemini-2.5-flash"}),
        json.dumps({"type": "message", "role": "user", "content": "test prompt"}),
        json.dumps({"type": "message", "role": "assistant", "content": text}),
        json.dumps(
            {
                "type": "result",
                "status": "success",
                "stats": {"total_tokens": 150, "duration_ms": 1000},
            }
        ),
    ]
    return "\n".join(lines) + "\n"


# Backward compatibility alias
make_stream_json_output = make_claude_stream_json_output


@pytest.fixture
def mock_popen_success():
    """Fixture that mocks Popen for successful invocation."""
    with patch("bmad_assist.providers.claude.Popen") as mock:
        mock.return_value = create_mock_process(
            stdout_content="Mock response",
            stderr_content="",
            returncode=0,
        )
        yield mock


@pytest.fixture
def mock_popen_timeout():
    """Fixture that mocks Popen for timeout."""
    with patch("bmad_assist.providers.claude.Popen") as mock:
        mock.return_value = create_mock_process(
            wait_side_effect=TimeoutExpired(cmd=["claude"], timeout=5)
        )
        yield mock


@pytest.fixture
def mock_popen_error():
    """Fixture that mocks Popen for non-zero exit."""
    with patch("bmad_assist.providers.claude.Popen") as mock:
        mock.return_value = create_mock_process(
            stdout_content="",
            stderr_content="Error message",
            returncode=1,
        )
        yield mock


@pytest.fixture
def mock_popen_not_found():
    """Fixture that mocks Popen when CLI not found."""
    with patch("bmad_assist.providers.claude.Popen") as mock:
        mock.side_effect = FileNotFoundError("claude")
        yield mock


# =============================================================================
# Codex Provider Popen Fixtures
# =============================================================================


def create_codex_mock_process(
    stdout_content: str | None = None,
    stderr_content: str = "",
    returncode: int = 0,
    wait_side_effect: Exception | None = None,
    response_text: str = "Mock response",
) -> MagicMock:
    """Create a mock Popen process for Codex testing."""
    if stdout_content is None:
        stdout_content = make_codex_json_output(response_text)
    return create_mock_process(
        stdout_content=stdout_content,
        stderr_content=stderr_content,
        returncode=returncode,
        wait_side_effect=wait_side_effect,
    )


@pytest.fixture
def mock_codex_popen_success():
    """Fixture that mocks Popen for successful Codex invocation."""
    with patch("bmad_assist.providers.codex.Popen") as mock:
        mock.return_value = create_codex_mock_process(
            response_text="Mock Codex response",
            returncode=0,
        )
        yield mock


@pytest.fixture
def mock_codex_popen_timeout():
    """Fixture that mocks Popen for Codex timeout."""
    with patch("bmad_assist.providers.codex.Popen") as mock:
        mock.return_value = create_codex_mock_process(
            wait_side_effect=TimeoutExpired(cmd=["codex"], timeout=5)
        )
        yield mock


@pytest.fixture
def mock_codex_popen_error():
    """Fixture that mocks Popen for non-zero Codex exit."""
    with patch("bmad_assist.providers.codex.Popen") as mock:
        mock.return_value = create_codex_mock_process(
            stdout_content="",
            stderr_content="Codex error message",
            returncode=1,
        )
        yield mock


@pytest.fixture
def mock_codex_popen_not_found():
    """Fixture that mocks Popen when Codex CLI not found."""
    with patch("bmad_assist.providers.codex.Popen") as mock:
        mock.side_effect = FileNotFoundError("codex")
        yield mock


# =============================================================================
# Gemini Provider Popen Fixtures
# =============================================================================


def create_gemini_mock_process(
    stdout_content: str | None = None,
    stderr_content: str = "",
    returncode: int = 0,
    wait_side_effect: Exception | None = None,
    response_text: str = "Mock response",
) -> MagicMock:
    """Create a mock Popen process for Gemini testing."""
    if stdout_content is None:
        stdout_content = make_gemini_json_output(response_text)
    return create_mock_process(
        stdout_content=stdout_content,
        stderr_content=stderr_content,
        returncode=returncode,
        wait_side_effect=wait_side_effect,
    )


@pytest.fixture
def mock_gemini_popen_success():
    """Fixture that mocks Popen for successful Gemini invocation."""
    with patch("bmad_assist.providers.gemini.Popen") as mock:
        mock.return_value = create_gemini_mock_process(
            response_text="Mock Gemini response",
            returncode=0,
        )
        yield mock


@pytest.fixture
def mock_gemini_popen_timeout():
    """Fixture that mocks Popen for Gemini timeout."""
    with patch("bmad_assist.providers.gemini.Popen") as mock:
        mock.return_value = create_gemini_mock_process(
            wait_side_effect=TimeoutExpired(cmd=["gemini"], timeout=5)
        )
        yield mock


@pytest.fixture
def mock_gemini_popen_error():
    """Fixture that mocks Popen for non-zero Gemini exit."""
    with patch("bmad_assist.providers.gemini.Popen") as mock:
        mock.return_value = create_gemini_mock_process(
            stdout_content="",
            stderr_content="Gemini error message",
            returncode=1,
        )
        yield mock


@pytest.fixture
def mock_gemini_popen_not_found():
    """Fixture that mocks Popen when Gemini CLI not found."""
    with patch("bmad_assist.providers.gemini.Popen") as mock:
        mock.side_effect = FileNotFoundError("gemini")
        yield mock
