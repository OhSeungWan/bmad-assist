"""Tests for notification events and payload models.

Tests cover:
- EventType enum values (AC2)
- is_high_priority() helper function (AC2)
- Pydantic payload models validation (AC3)
- Payload immutability (AC3)
- PAYLOAD_MODELS completeness (AC3)
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from bmad_assist.notifications import (
    HIGH_PRIORITY_EVENTS,
    PAYLOAD_MODELS,
    SIGNAL_NAMES,
    AnomalyDetectedPayload,
    CLICrashedPayload,
    ErrorOccurredPayload,
    EventPayload,
    EventType,
    FatalErrorPayload,
    PhaseCompletedPayload,
    QueueBlockedPayload,
    StoryCompletedPayload,
    StoryStartedPayload,
    TimeoutWarningPayload,
    get_signal_name,
    is_high_priority,
)


class TestEventTypeEnum:
    """Test AC2: EventType enum values."""

    def test_has_all_twelve_event_types(self) -> None:
        """Test EventType enum contains exactly 12 members (6 original + 4 infrastructure + 2 completion)."""
        assert len(EventType) == 12

    def test_story_started_value(self) -> None:
        """Test STORY_STARTED has correct snake_case value."""
        assert EventType.STORY_STARTED == "story_started"
        assert EventType.STORY_STARTED.value == "story_started"

    def test_story_completed_value(self) -> None:
        """Test STORY_COMPLETED has correct snake_case value."""
        assert EventType.STORY_COMPLETED == "story_completed"
        assert EventType.STORY_COMPLETED.value == "story_completed"

    def test_phase_completed_value(self) -> None:
        """Test PHASE_COMPLETED has correct snake_case value."""
        assert EventType.PHASE_COMPLETED == "phase_completed"
        assert EventType.PHASE_COMPLETED.value == "phase_completed"

    def test_anomaly_detected_value(self) -> None:
        """Test ANOMALY_DETECTED has correct snake_case value."""
        assert EventType.ANOMALY_DETECTED == "anomaly_detected"
        assert EventType.ANOMALY_DETECTED.value == "anomaly_detected"

    def test_queue_blocked_value(self) -> None:
        """Test QUEUE_BLOCKED has correct snake_case value."""
        assert EventType.QUEUE_BLOCKED == "queue_blocked"
        assert EventType.QUEUE_BLOCKED.value == "queue_blocked"

    def test_error_occurred_value(self) -> None:
        """Test ERROR_OCCURRED has correct snake_case value."""
        assert EventType.ERROR_OCCURRED == "error_occurred"
        assert EventType.ERROR_OCCURRED.value == "error_occurred"

    def test_event_type_is_str_enum(self) -> None:
        """Test EventType values are strings (StrEnum)."""
        for event in EventType:
            assert isinstance(event, str)
            assert isinstance(event.value, str)


class TestHighPriorityEvents:
    """Test AC2: HIGH_PRIORITY_EVENTS constant and is_high_priority() helper."""

    def test_high_priority_events_is_frozenset(self) -> None:
        """Test HIGH_PRIORITY_EVENTS is a frozenset."""
        assert isinstance(HIGH_PRIORITY_EVENTS, frozenset)

    def test_high_priority_events_contains_seven_events(self) -> None:
        """Test HIGH_PRIORITY_EVENTS contains exactly 7 events (3 original + 4 infrastructure)."""
        assert len(HIGH_PRIORITY_EVENTS) == 7

    def test_anomaly_detected_is_high_priority(self) -> None:
        """Test ANOMALY_DETECTED is in HIGH_PRIORITY_EVENTS."""
        assert EventType.ANOMALY_DETECTED in HIGH_PRIORITY_EVENTS
        assert is_high_priority(EventType.ANOMALY_DETECTED) is True

    def test_queue_blocked_is_high_priority(self) -> None:
        """Test QUEUE_BLOCKED is in HIGH_PRIORITY_EVENTS."""
        assert EventType.QUEUE_BLOCKED in HIGH_PRIORITY_EVENTS
        assert is_high_priority(EventType.QUEUE_BLOCKED) is True

    def test_error_occurred_is_high_priority(self) -> None:
        """Test ERROR_OCCURRED is in HIGH_PRIORITY_EVENTS."""
        assert EventType.ERROR_OCCURRED in HIGH_PRIORITY_EVENTS
        assert is_high_priority(EventType.ERROR_OCCURRED) is True

    def test_story_started_is_not_high_priority(self) -> None:
        """Test STORY_STARTED is not high priority."""
        assert EventType.STORY_STARTED not in HIGH_PRIORITY_EVENTS
        assert is_high_priority(EventType.STORY_STARTED) is False

    def test_story_completed_is_not_high_priority(self) -> None:
        """Test STORY_COMPLETED is not high priority."""
        assert EventType.STORY_COMPLETED not in HIGH_PRIORITY_EVENTS
        assert is_high_priority(EventType.STORY_COMPLETED) is False

    def test_phase_completed_is_not_high_priority(self) -> None:
        """Test PHASE_COMPLETED is not high priority."""
        assert EventType.PHASE_COMPLETED not in HIGH_PRIORITY_EVENTS
        assert is_high_priority(EventType.PHASE_COMPLETED) is False


class TestEventPayload:
    """Test AC3: Base EventPayload model."""

    def test_create_with_required_fields(self) -> None:
        """Test EventPayload creation with required fields."""
        payload = EventPayload(project="test-project", epic=15)
        assert payload.project == "test-project"
        assert payload.epic == 15
        assert payload.story is None
        assert isinstance(payload.timestamp, datetime)

    def test_create_with_all_fields(self) -> None:
        """Test EventPayload creation with all fields."""
        timestamp = datetime.now(UTC)
        payload = EventPayload(
            project="test-project",
            epic="testarch",
            story="testarch-1",
            timestamp=timestamp,
        )
        assert payload.project == "test-project"
        assert payload.epic == "testarch"
        assert payload.story == "testarch-1"
        assert payload.timestamp == timestamp

    def test_timestamp_auto_generated_in_utc(self) -> None:
        """Test timestamp is auto-generated in UTC."""
        before = datetime.now(UTC)
        payload = EventPayload(project="test", epic=1)
        after = datetime.now(UTC)
        assert before <= payload.timestamp <= after
        assert payload.timestamp.tzinfo is not None

    def test_epic_id_accepts_int(self) -> None:
        """Test epic field accepts integer."""
        payload = EventPayload(project="test", epic=15)
        assert payload.epic == 15

    def test_epic_id_accepts_string(self) -> None:
        """Test epic field accepts string (module IDs like 'testarch')."""
        payload = EventPayload(project="test", epic="testarch")
        assert payload.epic == "testarch"

    def test_validation_missing_project(self) -> None:
        """Test validation fails when project is missing."""
        with pytest.raises(ValidationError) as exc_info:
            EventPayload(epic=1)  # type: ignore[call-arg]
        assert "project" in str(exc_info.value)

    def test_validation_missing_epic(self) -> None:
        """Test validation fails when epic is missing."""
        with pytest.raises(ValidationError) as exc_info:
            EventPayload(project="test")  # type: ignore[call-arg]
        assert "epic" in str(exc_info.value)


class TestPayloadImmutability:
    """Test AC3: Payload immutability (frozen=True)."""

    def test_event_payload_is_immutable(self) -> None:
        """Test EventPayload cannot be modified after creation."""
        payload = EventPayload(project="test", epic=1)
        with pytest.raises(ValidationError):
            payload.project = "modified"  # type: ignore[misc]

    def test_story_started_payload_is_immutable(self) -> None:
        """Test StoryStartedPayload cannot be modified."""
        payload = StoryStartedPayload(project="test", epic=1, story="1-1", phase="CREATE_STORY")
        with pytest.raises(ValidationError):
            payload.phase = "DEV_STORY"  # type: ignore[misc]

    def test_story_completed_payload_is_immutable(self) -> None:
        """Test StoryCompletedPayload cannot be modified."""
        payload = StoryCompletedPayload(
            project="test", epic=1, story="1-1", duration_ms=1000, outcome="success"
        )
        with pytest.raises(ValidationError):
            payload.outcome = "failed"  # type: ignore[misc]

    def test_anomaly_detected_payload_is_immutable(self) -> None:
        """Test AnomalyDetectedPayload cannot be modified."""
        payload = AnomalyDetectedPayload(
            project="test",
            epic=1,
            anomaly_type="drift",
            context="Test context",
            suggested_actions=["action1"],
        )
        with pytest.raises(ValidationError):
            payload.context = "modified"  # type: ignore[misc]


class TestStoryStartedPayload:
    """Test AC3: StoryStartedPayload model."""

    def test_create_with_valid_data(self) -> None:
        """Test StoryStartedPayload creation with valid data."""
        payload = StoryStartedPayload(
            project="bmad-assist",
            epic=15,
            story="15-1",
            phase="CREATE_STORY",
        )
        assert payload.project == "bmad-assist"
        assert payload.epic == 15
        assert payload.story == "15-1"
        assert payload.phase == "CREATE_STORY"

    def test_validation_missing_phase(self) -> None:
        """Test validation fails when phase is missing."""
        with pytest.raises(ValidationError) as exc_info:
            StoryStartedPayload(project="test", epic=1, story="1-1")  # type: ignore[call-arg]
        assert "phase" in str(exc_info.value)

    def test_story_required_not_optional(self) -> None:
        """Test story field is required (overrides base class optional)."""
        with pytest.raises(ValidationError) as exc_info:
            StoryStartedPayload(project="test", epic=1, phase="CREATE_STORY")  # type: ignore[call-arg]
        assert "story" in str(exc_info.value)


class TestStoryCompletedPayload:
    """Test AC3: StoryCompletedPayload model."""

    def test_create_with_valid_data(self) -> None:
        """Test StoryCompletedPayload creation with valid data."""
        payload = StoryCompletedPayload(
            project="bmad-assist",
            epic=15,
            story="15-1",
            duration_ms=120000,
            outcome="success",
        )
        assert payload.duration_ms == 120000
        assert payload.outcome == "success"

    def test_duration_ms_accepts_zero(self) -> None:
        """Test duration_ms accepts zero (edge case for instant completion)."""
        payload = StoryCompletedPayload(
            project="test", epic=1, story="1-1", duration_ms=0, outcome="success"
        )
        assert payload.duration_ms == 0

    def test_duration_ms_rejects_negative(self) -> None:
        """Test duration_ms rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            StoryCompletedPayload(
                project="test", epic=1, story="1-1", duration_ms=-100, outcome="success"
            )
        assert "duration_ms" in str(exc_info.value)

    def test_validation_missing_duration_ms(self) -> None:
        """Test validation fails when duration_ms is missing."""
        with pytest.raises(ValidationError) as exc_info:
            StoryCompletedPayload(  # type: ignore[call-arg]
                project="test", epic=1, story="1-1", outcome="success"
            )
        assert "duration_ms" in str(exc_info.value)

    def test_validation_missing_outcome(self) -> None:
        """Test validation fails when outcome is missing."""
        with pytest.raises(ValidationError) as exc_info:
            StoryCompletedPayload(  # type: ignore[call-arg]
                project="test", epic=1, story="1-1", duration_ms=1000
            )
        assert "outcome" in str(exc_info.value)

    def test_story_required_not_optional(self) -> None:
        """Test story field is required (overrides base class optional)."""
        with pytest.raises(ValidationError) as exc_info:
            StoryCompletedPayload(  # type: ignore[call-arg]
                project="test", epic=1, duration_ms=1000, outcome="success"
            )
        assert "story" in str(exc_info.value)


class TestPhaseCompletedPayload:
    """Test AC3: PhaseCompletedPayload model."""

    def test_create_with_next_phase(self) -> None:
        """Test PhaseCompletedPayload with next_phase specified."""
        payload = PhaseCompletedPayload(
            project="test",
            epic=1,
            story="1-1",
            phase="CREATE_STORY",
            next_phase="VALIDATE_STORY",
        )
        assert payload.phase == "CREATE_STORY"
        assert payload.next_phase == "VALIDATE_STORY"

    def test_create_with_no_next_phase(self) -> None:
        """Test PhaseCompletedPayload when no next phase (final phase)."""
        payload = PhaseCompletedPayload(
            project="test",
            epic=1,
            story="1-1",
            phase="RETROSPECTIVE",
            next_phase=None,
        )
        assert payload.phase == "RETROSPECTIVE"
        assert payload.next_phase is None


class TestAnomalyDetectedPayload:
    """Test AC3: AnomalyDetectedPayload model."""

    def test_create_with_valid_data(self) -> None:
        """Test AnomalyDetectedPayload creation with valid data."""
        payload = AnomalyDetectedPayload(
            project="test",
            epic=1,
            anomaly_type="quality_drift",
            context="Validation score dropped below threshold",
            suggested_actions=["Review story", "Check prompts"],
        )
        assert payload.anomaly_type == "quality_drift"
        assert payload.context == "Validation score dropped below threshold"
        assert payload.suggested_actions == ["Review story", "Check prompts"]

    def test_suggested_actions_can_be_empty(self) -> None:
        """Test suggested_actions can be empty list."""
        payload = AnomalyDetectedPayload(
            project="test",
            epic=1,
            anomaly_type="unknown",
            context="Unexpected condition",
            suggested_actions=[],
        )
        assert payload.suggested_actions == []


class TestQueueBlockedPayload:
    """Test AC3: QueueBlockedPayload model."""

    def test_create_with_valid_data(self) -> None:
        """Test QueueBlockedPayload creation with valid data."""
        payload = QueueBlockedPayload(
            project="test",
            epic=1,
            reason="User input required",
            waiting_tasks=3,
        )
        assert payload.reason == "User input required"
        assert payload.waiting_tasks == 3

    def test_waiting_tasks_accepts_zero(self) -> None:
        """Test waiting_tasks accepts zero (edge case for empty queue)."""
        payload = QueueBlockedPayload(project="test", epic=1, reason="Blocked", waiting_tasks=0)
        assert payload.waiting_tasks == 0

    def test_waiting_tasks_rejects_negative(self) -> None:
        """Test waiting_tasks rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            QueueBlockedPayload(project="test", epic=1, reason="Blocked", waiting_tasks=-5)
        assert "waiting_tasks" in str(exc_info.value)


class TestErrorOccurredPayload:
    """Test AC3: ErrorOccurredPayload model."""

    def test_create_with_stack_trace(self) -> None:
        """Test ErrorOccurredPayload with stack trace."""
        payload = ErrorOccurredPayload(
            project="test",
            epic=1,
            error_type="ProviderError",
            message="Connection timeout",
            stack_trace="Traceback (most recent call last):\n  ...",
        )
        assert payload.error_type == "ProviderError"
        assert payload.message == "Connection timeout"
        assert payload.stack_trace is not None

    def test_create_without_stack_trace(self) -> None:
        """Test ErrorOccurredPayload without stack trace."""
        payload = ErrorOccurredPayload(
            project="test",
            epic=1,
            error_type="ValidationError",
            message="Invalid input",
        )
        assert payload.stack_trace is None


class TestPayloadModelsMapping:
    """Test AC3: PAYLOAD_MODELS mapping completeness."""

    def test_payload_models_has_entry_for_every_event_type(self) -> None:
        """Test PAYLOAD_MODELS contains entry for every EventType."""
        for event_type in EventType:
            assert event_type in PAYLOAD_MODELS, f"Missing: {event_type}"

    def test_payload_models_count_matches_event_type_count(self) -> None:
        """Test PAYLOAD_MODELS has same count as EventType members."""
        assert len(PAYLOAD_MODELS) == len(EventType)

    def test_story_started_mapping(self) -> None:
        """Test STORY_STARTED maps to StoryStartedPayload."""
        assert PAYLOAD_MODELS[EventType.STORY_STARTED] is StoryStartedPayload

    def test_story_completed_mapping(self) -> None:
        """Test STORY_COMPLETED maps to StoryCompletedPayload."""
        assert PAYLOAD_MODELS[EventType.STORY_COMPLETED] is StoryCompletedPayload

    def test_phase_completed_mapping(self) -> None:
        """Test PHASE_COMPLETED maps to PhaseCompletedPayload."""
        assert PAYLOAD_MODELS[EventType.PHASE_COMPLETED] is PhaseCompletedPayload

    def test_anomaly_detected_mapping(self) -> None:
        """Test ANOMALY_DETECTED maps to AnomalyDetectedPayload."""
        assert PAYLOAD_MODELS[EventType.ANOMALY_DETECTED] is AnomalyDetectedPayload

    def test_queue_blocked_mapping(self) -> None:
        """Test QUEUE_BLOCKED maps to QueueBlockedPayload."""
        assert PAYLOAD_MODELS[EventType.QUEUE_BLOCKED] is QueueBlockedPayload

    def test_error_occurred_mapping(self) -> None:
        """Test ERROR_OCCURRED maps to ErrorOccurredPayload."""
        assert PAYLOAD_MODELS[EventType.ERROR_OCCURRED] is ErrorOccurredPayload

    def test_all_payload_types_are_subclasses_of_event_payload(self) -> None:
        """Test all payload types in PAYLOAD_MODELS inherit from EventPayload."""
        for _event_type, payload_cls in PAYLOAD_MODELS.items():
            assert issubclass(payload_cls, EventPayload), (
                f"{payload_cls} not subclass of EventPayload"
            )


# ============================================================================
# Infrastructure Event Tests (Story 21.4)
# ============================================================================


class TestInfrastructureEventTypes:
    """Test Story 21.4 AC1: New EventType enum values."""

    def test_timeout_warning_value(self) -> None:
        """Test TIMEOUT_WARNING has correct snake_case value."""
        assert EventType.TIMEOUT_WARNING == "timeout_warning"
        assert EventType.TIMEOUT_WARNING.value == "timeout_warning"

    def test_cli_crashed_value(self) -> None:
        """Test CLI_CRASHED has correct snake_case value."""
        assert EventType.CLI_CRASHED == "cli_crashed"
        assert EventType.CLI_CRASHED.value == "cli_crashed"

    def test_cli_recovered_value(self) -> None:
        """Test CLI_RECOVERED has correct snake_case value."""
        assert EventType.CLI_RECOVERED == "cli_recovered"
        assert EventType.CLI_RECOVERED.value == "cli_recovered"

    def test_fatal_error_value(self) -> None:
        """Test FATAL_ERROR has correct snake_case value."""
        assert EventType.FATAL_ERROR == "fatal_error"
        assert EventType.FATAL_ERROR.value == "fatal_error"

    def test_timeout_warning_is_high_priority(self) -> None:
        """Test TIMEOUT_WARNING is in HIGH_PRIORITY_EVENTS."""
        assert EventType.TIMEOUT_WARNING in HIGH_PRIORITY_EVENTS
        assert is_high_priority(EventType.TIMEOUT_WARNING) is True

    def test_cli_crashed_is_high_priority(self) -> None:
        """Test CLI_CRASHED is in HIGH_PRIORITY_EVENTS."""
        assert EventType.CLI_CRASHED in HIGH_PRIORITY_EVENTS
        assert is_high_priority(EventType.CLI_CRASHED) is True

    def test_cli_recovered_is_high_priority(self) -> None:
        """Test CLI_RECOVERED is in HIGH_PRIORITY_EVENTS."""
        assert EventType.CLI_RECOVERED in HIGH_PRIORITY_EVENTS
        assert is_high_priority(EventType.CLI_RECOVERED) is True

    def test_fatal_error_is_high_priority(self) -> None:
        """Test FATAL_ERROR is in HIGH_PRIORITY_EVENTS."""
        assert EventType.FATAL_ERROR in HIGH_PRIORITY_EVENTS
        assert is_high_priority(EventType.FATAL_ERROR) is True


class TestTimeoutWarningPayload:
    """Test Story 21.4 AC2: TimeoutWarningPayload model."""

    def test_create_with_valid_data(self) -> None:
        """Test TimeoutWarningPayload creation with valid data."""
        payload = TimeoutWarningPayload(
            project="bmad-assist",
            epic=21,
            story="21-4",
            tool_name="claude-code",
            elapsed_ms=3000000,
            limit_ms=3600000,
            remaining_ms=600000,
        )
        assert payload.tool_name == "claude-code"
        assert payload.elapsed_ms == 3000000
        assert payload.limit_ms == 3600000
        assert payload.remaining_ms == 600000

    def test_elapsed_ms_accepts_zero(self) -> None:
        """Test elapsed_ms accepts zero (just started)."""
        payload = TimeoutWarningPayload(
            project="test",
            epic=1,
            tool_name="gemini",
            elapsed_ms=0,
            limit_ms=1000,
            remaining_ms=1000,
        )
        assert payload.elapsed_ms == 0

    def test_elapsed_ms_rejects_negative(self) -> None:
        """Test elapsed_ms rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            TimeoutWarningPayload(
                project="test",
                epic=1,
                tool_name="gemini",
                elapsed_ms=-1,
                limit_ms=1000,
                remaining_ms=1000,
            )
        assert "elapsed_ms" in str(exc_info.value)

    def test_limit_ms_rejects_zero(self) -> None:
        """Test limit_ms rejects zero (must be > 0)."""
        with pytest.raises(ValidationError) as exc_info:
            TimeoutWarningPayload(
                project="test",
                epic=1,
                tool_name="gemini",
                elapsed_ms=0,
                limit_ms=0,
                remaining_ms=0,
            )
        assert "limit_ms" in str(exc_info.value)

    def test_limit_ms_rejects_negative(self) -> None:
        """Test limit_ms rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            TimeoutWarningPayload(
                project="test",
                epic=1,
                tool_name="gemini",
                elapsed_ms=0,
                limit_ms=-1,
                remaining_ms=0,
            )
        assert "limit_ms" in str(exc_info.value)

    def test_remaining_ms_accepts_zero(self) -> None:
        """Test remaining_ms accepts zero (at timeout)."""
        payload = TimeoutWarningPayload(
            project="test",
            epic=1,
            tool_name="gemini",
            elapsed_ms=1000,
            limit_ms=1000,
            remaining_ms=0,
        )
        assert payload.remaining_ms == 0

    def test_remaining_ms_rejects_negative(self) -> None:
        """Test remaining_ms rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            TimeoutWarningPayload(
                project="test",
                epic=1,
                tool_name="gemini",
                elapsed_ms=1000,
                limit_ms=1000,
                remaining_ms=-1,
            )
        assert "remaining_ms" in str(exc_info.value)

    def test_payload_is_immutable(self) -> None:
        """Test TimeoutWarningPayload cannot be modified."""
        payload = TimeoutWarningPayload(
            project="test",
            epic=1,
            tool_name="gemini",
            elapsed_ms=1000,
            limit_ms=2000,
            remaining_ms=1000,
        )
        with pytest.raises(ValidationError):
            payload.tool_name = "claude"  # type: ignore[misc]


class TestCLICrashedPayload:
    """Test Story 21.4 AC3: CLICrashedPayload model."""

    def test_create_with_signal(self) -> None:
        """Test CLICrashedPayload creation with signal."""
        payload = CLICrashedPayload(
            project="bmad-assist",
            epic=21,
            story="21-4",
            tool_name="claude-code",
            signal=9,
            attempt=2,
            max_attempts=3,
            recovered=False,
        )
        assert payload.tool_name == "claude-code"
        assert payload.signal == 9
        assert payload.exit_code is None
        assert payload.attempt == 2
        assert payload.max_attempts == 3
        assert payload.recovered is False

    def test_create_with_exit_code(self) -> None:
        """Test CLICrashedPayload creation with exit_code."""
        payload = CLICrashedPayload(
            project="test",
            epic=1,
            tool_name="codex",
            exit_code=1,
            attempt=1,
            max_attempts=3,
            recovered=True,
        )
        assert payload.exit_code == 1
        assert payload.signal is None
        assert payload.recovered is True

    def test_create_with_neither_signal_nor_exit_code(self) -> None:
        """Test CLICrashedPayload creation with unknown failure."""
        payload = CLICrashedPayload(
            project="test",
            epic=1,
            tool_name="gemini",
            attempt=3,
            max_attempts=3,
            recovered=False,
        )
        assert payload.exit_code is None
        assert payload.signal is None

    def test_attempt_rejects_zero(self) -> None:
        """Test attempt rejects zero (must be >= 1)."""
        with pytest.raises(ValidationError) as exc_info:
            CLICrashedPayload(
                project="test",
                epic=1,
                tool_name="gemini",
                attempt=0,
                max_attempts=3,
                recovered=False,
            )
        assert "attempt" in str(exc_info.value)

    def test_attempt_rejects_negative(self) -> None:
        """Test attempt rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            CLICrashedPayload(
                project="test",
                epic=1,
                tool_name="gemini",
                attempt=-1,
                max_attempts=3,
                recovered=False,
            )
        assert "attempt" in str(exc_info.value)

    def test_max_attempts_rejects_zero(self) -> None:
        """Test max_attempts rejects zero (must be >= 1)."""
        with pytest.raises(ValidationError) as exc_info:
            CLICrashedPayload(
                project="test",
                epic=1,
                tool_name="gemini",
                attempt=1,
                max_attempts=0,
                recovered=False,
            )
        assert "max_attempts" in str(exc_info.value)

    def test_max_attempts_rejects_negative(self) -> None:
        """Test max_attempts rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            CLICrashedPayload(
                project="test",
                epic=1,
                tool_name="gemini",
                attempt=1,
                max_attempts=-1,
                recovered=False,
            )
        assert "max_attempts" in str(exc_info.value)

    def test_payload_is_immutable(self) -> None:
        """Test CLICrashedPayload cannot be modified."""
        payload = CLICrashedPayload(
            project="test",
            epic=1,
            tool_name="gemini",
            attempt=1,
            max_attempts=3,
            recovered=False,
        )
        with pytest.raises(ValidationError):
            payload.recovered = True  # type: ignore[misc]


class TestFatalErrorPayload:
    """Test Story 21.4 AC4: FatalErrorPayload model."""

    def test_create_with_valid_data(self) -> None:
        """Test FatalErrorPayload creation with valid data."""
        payload = FatalErrorPayload(
            project="bmad-assist",
            epic=21,
            story="21-4",
            exception_type="KeyError",
            message="'current_story' not found",
            location="state.py:142",
        )
        assert payload.exception_type == "KeyError"
        assert payload.message == "'current_story' not found"
        assert payload.location == "state.py:142"

    def test_message_accepts_max_length(self) -> None:
        """Test message accepts messages up to 500 characters."""
        payload = FatalErrorPayload(
            project="test",
            epic=1,
            exception_type="RuntimeError",
            message="x" * 500,
            location="test.py:1",
        )
        assert len(payload.message) == 500

    def test_message_rejects_over_max_length(self) -> None:
        """Test message rejects messages over 500 characters."""
        with pytest.raises(ValidationError) as exc_info:
            FatalErrorPayload(
                project="test",
                epic=1,
                exception_type="RuntimeError",
                message="x" * 501,
                location="test.py:1",
            )
        assert "message" in str(exc_info.value)

    def test_payload_is_immutable(self) -> None:
        """Test FatalErrorPayload cannot be modified."""
        payload = FatalErrorPayload(
            project="test",
            epic=1,
            exception_type="KeyError",
            message="test",
            location="test.py:1",
        )
        with pytest.raises(ValidationError):
            payload.exception_type = "ValueError"  # type: ignore[misc]


class TestSignalNameHelper:
    """Test Story 21.4 AC8: Signal name helper."""

    def test_get_signal_name_sigkill(self) -> None:
        """Test get_signal_name returns SIGKILL for signal 9."""
        assert get_signal_name(9) == "SIGKILL"

    def test_get_signal_name_sigterm(self) -> None:
        """Test get_signal_name returns SIGTERM for signal 15."""
        assert get_signal_name(15) == "SIGTERM"

    def test_get_signal_name_sigsegv(self) -> None:
        """Test get_signal_name returns SIGSEGV for signal 11."""
        assert get_signal_name(11) == "SIGSEGV"

    def test_get_signal_name_sigabrt(self) -> None:
        """Test get_signal_name returns SIGABRT for signal 6."""
        assert get_signal_name(6) == "SIGABRT"

    def test_get_signal_name_sigint(self) -> None:
        """Test get_signal_name returns SIGINT for signal 2."""
        assert get_signal_name(2) == "SIGINT"

    def test_get_signal_name_sighup(self) -> None:
        """Test get_signal_name returns SIGHUP for signal 1."""
        assert get_signal_name(1) == "SIGHUP"

    def test_get_signal_name_unknown_signal(self) -> None:
        """Test get_signal_name returns None for unknown signal."""
        assert get_signal_name(99) is None

    def test_get_signal_name_none_input(self) -> None:
        """Test get_signal_name returns None for None input."""
        assert get_signal_name(None) is None

    def test_signal_names_constant_contains_common_signals(self) -> None:
        """Test SIGNAL_NAMES contains common POSIX signals."""
        expected_signals = {1, 2, 3, 6, 9, 11, 13, 14, 15}
        assert expected_signals == set(SIGNAL_NAMES.keys())


class TestInfrastructurePayloadModelsMapping:
    """Test Story 21.4 AC5: PAYLOAD_MODELS includes infrastructure events."""

    def test_timeout_warning_mapping(self) -> None:
        """Test TIMEOUT_WARNING maps to TimeoutWarningPayload."""
        assert PAYLOAD_MODELS[EventType.TIMEOUT_WARNING] is TimeoutWarningPayload

    def test_cli_crashed_mapping(self) -> None:
        """Test CLI_CRASHED maps to CLICrashedPayload."""
        assert PAYLOAD_MODELS[EventType.CLI_CRASHED] is CLICrashedPayload

    def test_cli_recovered_mapping(self) -> None:
        """Test CLI_RECOVERED maps to CLICrashedPayload (same payload type)."""
        assert PAYLOAD_MODELS[EventType.CLI_RECOVERED] is CLICrashedPayload

    def test_fatal_error_mapping(self) -> None:
        """Test FATAL_ERROR maps to FatalErrorPayload."""
        assert PAYLOAD_MODELS[EventType.FATAL_ERROR] is FatalErrorPayload

    def test_payload_models_has_all_twelve_event_types(self) -> None:
        """Test PAYLOAD_MODELS contains all 12 event types."""
        assert len(PAYLOAD_MODELS) == 12
        for event_type in EventType:
            assert event_type in PAYLOAD_MODELS, f"Missing: {event_type}"
