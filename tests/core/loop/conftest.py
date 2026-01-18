"""Pytest fixtures for bmad_assist.core.loop tests.

Shared fixtures extracted from test_loop.py as part of loop.py refactor.
"""

import pytest

from bmad_assist.core.loop.signals import reset_shutdown


@pytest.fixture(autouse=True)
def reset_shutdown_state() -> None:
    """Reset shutdown state before and after each test.

    This fixture ensures test isolation by clearing the shutdown state.
    The autouse=True makes it run automatically for all tests
    in the loop directory.
    """
    reset_shutdown()
    yield
    reset_shutdown()
