"""Pytest configuration and fixtures for bmad-assist tests."""

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def reset_paths_singleton():
    """Reset paths singleton before and after each test.

    This ensures tests don't leak path configuration between each other.
    Tests that need paths must explicitly initialize them.
    """
    from bmad_assist.core.paths import _reset_paths

    _reset_paths()
    yield
    _reset_paths()


@pytest.fixture
def init_test_paths(tmp_path):
    """Initialize paths singleton for a test with temp directory.

    Usage:
        def test_something(init_test_paths):
            # paths are now initialized with tmp_path as project root
            from bmad_assist.core.paths import get_paths
            paths = get_paths()
    """
    from bmad_assist.core.paths import init_paths

    paths = init_paths(tmp_path)
    paths.ensure_directories()
    return paths


@pytest.fixture(autouse=True)
def disable_debug_json_logger(request):
    """Globally disable DebugJsonLogger during tests.

    Prevents tests from writing to ~/.bmad-assist/debug/json/
    which would create large files (especially for tests with
    10MB output like test_output_capture.py).

    Tests that need the real logger can use:
        @pytest.mark.real_debug_logger
    """
    # Skip this fixture for tests marked with real_debug_logger
    if request.node.get_closest_marker("real_debug_logger"):
        yield None
        return

    with patch("bmad_assist.core.debug_logger.DebugJsonLogger") as mock:
        # Create a mock that does nothing
        instance = mock.return_value
        instance.enabled = False
        instance.append.return_value = None
        instance.close.return_value = None
        instance.path = None
        yield mock
