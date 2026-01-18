"""Tests for NotificationProvider ABC.

Tests cover:
- ABC cannot be instantiated (AC1)
- Concrete implementation pattern (AC1, AC4)
- Error handling contract (AC4)
"""

import logging

import pytest

from bmad_assist.notifications import (
    EventPayload,
    EventType,
    NotificationProvider,
    StoryStartedPayload,
)


class TestNotificationProviderABC:
    """Test AC1: NotificationProvider ABC."""

    def test_cannot_instantiate_abc(self) -> None:
        """Test NotificationProvider cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            NotificationProvider()  # type: ignore[abstract]
        assert "abstract" in str(exc_info.value).lower()

    def test_abc_has_provider_name_property(self) -> None:
        """Test NotificationProvider has abstract provider_name property."""
        assert hasattr(NotificationProvider, "provider_name")

    def test_abc_has_send_method(self) -> None:
        """Test NotificationProvider has abstract send method."""
        assert hasattr(NotificationProvider, "send")


class MockSuccessProvider(NotificationProvider):
    """Mock provider that always succeeds."""

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "mock-success"

    async def send(self, event: EventType, payload: EventPayload) -> bool:
        """Send notification (always succeeds)."""
        return True


class MockFailureProvider(NotificationProvider):
    """Mock provider that always fails (returns False)."""

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "mock-failure"

    async def send(self, event: EventType, payload: EventPayload) -> bool:
        """Send notification (always fails, simulates internal error handling)."""
        return False


class MockErrorHandlingProvider(NotificationProvider):
    """Mock provider that demonstrates proper error handling."""

    def __init__(self) -> None:
        """Initialize mock provider with configurable failure mode."""
        self._should_fail = False
        self._logger = logging.getLogger(__name__)

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "mock-error-handling"

    def set_should_fail(self, fail: bool) -> None:
        """Configure provider to fail on next send."""
        self._should_fail = fail

    async def send(self, event: EventType, payload: EventPayload) -> bool:
        """Send notification with proper error handling contract."""
        try:
            if self._should_fail:
                raise ConnectionError("Simulated network failure")
            return True
        except Exception as e:
            self._logger.error(
                "Notification failed: event=%s, provider=%s, error=%s",
                event,
                self.provider_name,
                str(e),
            )
            return False


class TestConcreteProviderPattern:
    """Test AC1, AC4: Concrete implementation pattern."""

    def test_concrete_provider_can_be_instantiated(self) -> None:
        """Test concrete provider can be instantiated."""
        provider = MockSuccessProvider()
        assert provider.provider_name == "mock-success"

    async def test_success_provider_returns_true(self) -> None:
        """Test successful send returns True."""
        provider = MockSuccessProvider()
        payload = StoryStartedPayload(project="test", epic=1, story="1-1", phase="CREATE_STORY")
        result = await provider.send(EventType.STORY_STARTED, payload)
        assert result is True

    async def test_failure_provider_returns_false(self) -> None:
        """Test failed send returns False (never raises)."""
        provider = MockFailureProvider()
        payload = StoryStartedPayload(project="test", epic=1, story="1-1", phase="CREATE_STORY")
        result = await provider.send(EventType.STORY_STARTED, payload)
        assert result is False


class TestErrorHandlingContract:
    """Test AC4: Provider error handling contract."""

    async def test_error_handling_returns_false_on_exception(self) -> None:
        """Test provider returns False on internal exception."""
        provider = MockErrorHandlingProvider()
        provider.set_should_fail(True)
        payload = StoryStartedPayload(project="test", epic=1, story="1-1", phase="CREATE_STORY")
        # Should NOT raise, should return False
        result = await provider.send(EventType.STORY_STARTED, payload)
        assert result is False

    async def test_error_handling_logs_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test provider logs error on failure."""
        provider = MockErrorHandlingProvider()
        provider.set_should_fail(True)
        payload = StoryStartedPayload(project="test", epic=1, story="1-1", phase="CREATE_STORY")

        with caplog.at_level(logging.ERROR):
            await provider.send(EventType.STORY_STARTED, payload)

        assert "Notification failed" in caplog.text
        assert "mock-error-handling" in caplog.text
        assert "network failure" in caplog.text.lower()

    async def test_successful_send_does_not_log_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test successful send does not log errors."""
        provider = MockErrorHandlingProvider()
        provider.set_should_fail(False)
        payload = StoryStartedPayload(project="test", epic=1, story="1-1", phase="CREATE_STORY")

        with caplog.at_level(logging.ERROR):
            result = await provider.send(EventType.STORY_STARTED, payload)

        assert result is True
        assert "Notification failed" not in caplog.text
