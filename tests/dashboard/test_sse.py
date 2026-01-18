"""Tests for SSE broadcasting - Story 16.3: SSE Output Streaming.

Tests verify SSE implementation for real-time dashboard updates:
- AC1: SSE endpoint with proper headers and initial status event
- AC2: Output broadcast with {line, provider, timestamp}
- AC3: Queue broadcast passing dict through
- AC4: Heartbeat after 30s idle
- AC5: Connection cleanup on disconnect
- AC6: Multiple concurrent connections

RED Phase: All tests should verify existing implementation correctness.
"""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from bmad_assist.dashboard.server import DashboardServer
from bmad_assist.dashboard.sse import EventType, SSEBroadcaster, SSEMessage

# =============================================================================
# Task 1: Test SSEMessage formatting (AC: 1, 2)
# =============================================================================


class TestSSEMessageFormat:
    """Tests for SSEMessage.format() method."""

    def test_format_produces_valid_sse_protocol(self) -> None:
        """Test that produces valid SSE protocol with event, data, double newline."""
        # GIVEN: SSEMessage
        msg = SSEMessage(
            event="output",
            data={"line": "test", "provider": "opus", "timestamp": 1.0},
        )

        # WHEN: Format
        formatted = msg.format()

        # THEN: Valid SSE format
        assert "event: output" in formatted
        assert "data:" in formatted
        assert formatted.endswith("\n\n")  # Double newline terminates

    def test_format_includes_id_when_provided(self) -> None:
        """Test that includes id line."""
        # GIVEN: SSEMessage with id
        msg = SSEMessage(event="output", data={"line": "test"}, id="123")

        # WHEN: Format
        formatted = msg.format()

        # THEN: Contains id
        assert "id: 123" in formatted

    def test_format_includes_retry_when_provided(self) -> None:
        """Test that includes retry line."""
        # GIVEN: SSEMessage with retry
        msg = SSEMessage(event="status", data={"connected": True}, retry=3000)

        # WHEN: Format
        formatted = msg.format()

        # THEN: Contains retry
        assert "retry: 3000" in formatted

    def test_format_json_encodes_dict_data(self) -> None:
        """Test that data is JSON-encoded."""
        # GIVEN: SSEMessage with dict
        msg = SSEMessage(event="output", data={"key": "value", "num": 42})

        # WHEN: Format
        formatted = msg.format()

        # THEN: JSON encoded
        assert '"key": "value"' in formatted or '"key":"value"' in formatted
        assert '"num": 42' in formatted or '"num":42' in formatted

    def test_format_json_encodes_list_data(self) -> None:
        """Test that data is JSON-encoded."""
        # GIVEN: SSEMessage with list
        msg = SSEMessage(event="queue", data=[{"id": 1}, {"id": 2}])

        # WHEN: Format
        formatted = msg.format()

        # THEN: JSON encoded
        assert '"id": 1' in formatted or '"id":1' in formatted

    def test_format_multiline_json_uses_multiple_data_lines(self) -> None:
        """Test that each line gets separate data: prefix (SSE protocol)."""
        # GIVEN: Large dict that will span multiple lines when formatted
        # Note: Our implementation uses json.dumps which is compact by default
        # This test verifies behavior if newlines are in data
        msg = SSEMessage(event="output", data={"line": "line1\nline2"})

        # WHEN: Format
        formatted = msg.format()

        # THEN: Contains data prefix
        assert "data:" in formatted

    def test_event_type_enum_values(self) -> None:
        """Test that matches expected strings."""
        # THEN: Enum values correct
        assert EventType.OUTPUT.value == "output"
        assert EventType.STATUS.value == "status"
        assert EventType.HEARTBEAT.value == "heartbeat"

    def test_format_field_order(self) -> None:
        """Test that fields appear in SSE-compliant order: id, retry, event, data."""
        # GIVEN: SSEMessage with all fields
        msg = SSEMessage(event="status", data={"connected": True}, id="1", retry=3000)

        # WHEN: Format
        formatted = msg.format()

        # THEN: Order is id, retry, event, data
        id_pos = formatted.find("id:")
        retry_pos = formatted.find("retry:")
        event_pos = formatted.find("event:")
        data_pos = formatted.find("data:")

        assert id_pos < retry_pos < event_pos < data_pos


# =============================================================================
# Task 2: Test SSEBroadcaster subscription (AC: 1, 4)
# =============================================================================


class TestSSEBroadcasterSubscribe:
    """Tests for SSEBroadcaster.subscribe() method."""

    @pytest.mark.asyncio
    async def test_subscribe_yields_initial_status_event(self) -> None:
        """Test that first message is status event with {connected: true, timestamp}."""
        # GIVEN: Broadcaster with long heartbeat (prevent timeout)
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # WHEN: Subscribe and get first message
        async def consume_one():
            async for msg in broadcaster.subscribe():
                return msg

        task = asyncio.create_task(consume_one())
        first_msg = await asyncio.wait_for(task, timeout=1.0)

        # THEN: Status event with connected true
        assert "event: status" in first_msg
        assert '"connected": true' in first_msg or '"connected":true' in first_msg

    @pytest.mark.asyncio
    async def test_subscribe_initial_event_has_timestamp(self) -> None:
        """Test that initial status event has timestamp field."""
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # WHEN: Subscribe and get first message
        async def consume_one():
            async for msg in broadcaster.subscribe():
                return msg

        task = asyncio.create_task(consume_one())
        first_msg = await asyncio.wait_for(task, timeout=1.0)

        # THEN: Has timestamp
        assert "timestamp" in first_msg

    @pytest.mark.asyncio
    async def test_subscribe_initial_event_has_retry(self) -> None:
        """Test that initial status event has retry directive (3000ms)."""
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # WHEN: Subscribe and get first message
        async def consume_one():
            async for msg in broadcaster.subscribe():
                return msg

        task = asyncio.create_task(consume_one())
        first_msg = await asyncio.wait_for(task, timeout=1.0)

        # THEN: Has retry
        assert "retry: 3000" in first_msg

    @pytest.mark.asyncio
    async def test_heartbeat_sent_after_timeout(self) -> None:
        """Test that heartbeat event is sent."""
        # GIVEN: Broadcaster with very short heartbeat
        broadcaster = SSEBroadcaster(heartbeat_interval=0.1)

        # WHEN: Wait for heartbeat
        messages = []

        async def consume_two():
            count = 0
            async for msg in broadcaster.subscribe():
                messages.append(msg)
                count += 1
                if count >= 2:  # Initial + heartbeat
                    break

        await asyncio.wait_for(consume_two(), timeout=2.0)

        # THEN: Second message is heartbeat
        assert len(messages) == 2
        assert "event: heartbeat" in messages[1]

    @pytest.mark.asyncio
    async def test_heartbeat_format(self) -> None:
        """Test that contains {timestamp: float}."""
        # GIVEN: Broadcaster with short heartbeat
        broadcaster = SSEBroadcaster(heartbeat_interval=0.1)

        # WHEN: Get heartbeat message
        messages = []

        async def consume_two():
            count = 0
            async for msg in broadcaster.subscribe():
                messages.append(msg)
                count += 1
                if count >= 2:
                    break

        await asyncio.wait_for(consume_two(), timeout=2.0)

        # THEN: Heartbeat has timestamp
        heartbeat = messages[1]
        assert "timestamp" in heartbeat

    @pytest.mark.asyncio
    async def test_connection_added_to_queues_on_subscribe(self) -> None:
        """Test that connection_count increases."""
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # WHEN: Subscribe
        async def subscribe_and_check():
            async for _ in broadcaster.subscribe():
                # Check count while subscribed
                assert broadcaster.connection_count == 1
                break

        await asyncio.wait_for(subscribe_and_check(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_connection_removed_from_queues_in_finally(self) -> None:
        """Test that connection_count decreases."""
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # WHEN: Subscribe and exit
        async def subscribe_and_exit():
            async for _ in broadcaster.subscribe():
                break  # Exit after first message

        await asyncio.wait_for(subscribe_and_exit(), timeout=1.0)

        # THEN: Connection cleaned up
        # Give a moment for cleanup
        await asyncio.sleep(0.01)
        assert broadcaster.connection_count == 0


# =============================================================================
# Task 3: Test broadcast delivery (AC: 2, 3, 6)
# =============================================================================


class TestSSEBroadcasterBroadcast:
    """Tests for SSEBroadcaster broadcast methods."""

    @pytest.mark.asyncio
    async def test_broadcast_output_creates_correct_event_structure(self) -> None:
        """Test that output event is sent with {line, provider, timestamp}."""
        # GIVEN: Broadcaster with subscriber
        broadcaster = SSEBroadcaster(heartbeat_interval=60)
        received = []

        async def consumer():
            count = 0
            async for msg in broadcaster.subscribe():
                received.append(msg)
                count += 1
                if count >= 2:  # Initial + broadcast
                    break

        # Start consumer
        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)  # Let it subscribe

        # WHEN: Broadcast output
        count = await broadcaster.broadcast_output("test line", "opus")

        await asyncio.wait_for(task, timeout=1.0)

        # THEN: Output event received
        assert count == 1
        output_msg = received[1]
        assert "event: output" in output_msg
        assert '"line": "test line"' in output_msg or '"line":"test line"' in output_msg
        assert '"provider": "opus"' in output_msg or '"provider":"opus"' in output_msg
        assert "timestamp" in output_msg

    @pytest.mark.asyncio
    async def test_broadcast_output_timestamp_is_unix_epoch(self) -> None:
        """Test that timestamp is Unix epoch float (time."""
        # GIVEN: Broadcaster with subscriber
        broadcaster = SSEBroadcaster(heartbeat_interval=60)
        received = []
        before_time = time.time()

        async def consumer():
            count = 0
            async for msg in broadcaster.subscribe():
                received.append(msg)
                count += 1
                if count >= 2:
                    break

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        # WHEN: Broadcast output
        await broadcaster.broadcast_output("test", "opus")
        after_time = time.time()

        await asyncio.wait_for(task, timeout=1.0)

        # THEN: Timestamp is in valid range
        output_msg = received[1]
        # Extract timestamp from JSON
        data_start = output_msg.find("data: ") + 6
        data_end = output_msg.find("\n", data_start)
        data_json = output_msg[data_start:data_end]
        data = json.loads(data_json)

        assert before_time <= data["timestamp"] <= after_time

    @pytest.mark.asyncio
    async def test_broadcast_output_provider_null(self) -> None:
        """Test that provider serializes as JSON null."""
        # GIVEN: Broadcaster with subscriber
        broadcaster = SSEBroadcaster(heartbeat_interval=60)
        received = []

        async def consumer():
            count = 0
            async for msg in broadcaster.subscribe():
                received.append(msg)
                count += 1
                if count >= 2:
                    break

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        # WHEN: Broadcast with None provider
        await broadcaster.broadcast_output("test line", None)

        await asyncio.wait_for(task, timeout=1.0)

        # THEN: Provider is null
        output_msg = received[1]
        assert '"provider": null' in output_msg or '"provider":null' in output_msg

    @pytest.mark.asyncio
    async def test_broadcast_delivers_to_multiple_subscribers(self) -> None:
        """Test that all subscribers receive the message."""
        # GIVEN: Broadcaster with 3 subscribers
        broadcaster = SSEBroadcaster(heartbeat_interval=60)
        received_counts = []

        async def consumer(consumer_id: int):
            count = 0
            async for _msg in broadcaster.subscribe():
                count += 1
                if count >= 2:  # Initial + broadcast
                    received_counts.append(consumer_id)
                    break

        # Start 3 consumers
        tasks = [asyncio.create_task(consumer(i)) for i in range(3)]
        await asyncio.sleep(0.1)  # Let all subscribe

        # WHEN: Broadcast
        sent_count = await broadcaster.broadcast_output("test", "opus")

        await asyncio.wait_for(asyncio.gather(*tasks), timeout=2.0)

        # THEN: All 3 received
        assert sent_count == 3
        assert len(received_counts) == 3

    @pytest.mark.asyncio
    async def test_message_counter_increments_per_broadcast(self) -> None:
        """Test that message IDs increment."""
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)
        received = []

        async def consumer():
            count = 0
            async for msg in broadcaster.subscribe():
                received.append(msg)
                count += 1
                if count >= 4:  # Initial + 3 broadcasts
                    break

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)

        # WHEN: Multiple broadcasts
        await broadcaster.broadcast_output("line 1", "opus")
        await broadcaster.broadcast_output("line 2", "opus")
        await broadcaster.broadcast_output("line 3", "opus")

        await asyncio.wait_for(task, timeout=2.0)

        # THEN: IDs increment
        # Extract IDs from messages 1-3 (skip initial status)
        ids = []
        for msg in received[1:]:
            if "id: " in msg:
                id_line = [line for line in msg.split("\n") if line.startswith("id: ")][0]
                ids.append(int(id_line.split(": ")[1]))

        assert ids == [1, 2, 3]


# =============================================================================
# Task 4: Test connection lifecycle (AC: 5, 6)
# =============================================================================


class TestConnectionLifecycle:
    """Tests for connection lifecycle management."""

    @pytest.mark.asyncio
    async def test_connection_count_accuracy_zero_clients(self) -> None:
        """Test that returns 0."""
        # GIVEN: Fresh broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # THEN: Count is 0
        assert broadcaster.connection_count == 0

    @pytest.mark.asyncio
    async def test_connection_count_accuracy_one_client(self) -> None:
        """Test that returns 1."""
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # WHEN: One subscriber
        async def check_count():
            async for _ in broadcaster.subscribe():
                assert broadcaster.connection_count == 1
                break

        await asyncio.wait_for(check_count(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_connection_count_accuracy_five_clients(self) -> None:
        """Test that returns 5."""
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)
        all_connected = asyncio.Event()

        async def subscriber(sub_id: int):
            async for _ in broadcaster.subscribe():
                if broadcaster.connection_count >= 5:
                    all_connected.set()
                await asyncio.sleep(0.1)  # Stay connected briefly
                break

        # WHEN: 5 subscribers connect
        tasks = [asyncio.create_task(subscriber(i)) for i in range(5)]
        await asyncio.wait_for(all_connected.wait(), timeout=2.0)

        # THEN: Count is 5
        assert broadcaster.connection_count == 5

        # Cleanup
        for t in tasks:
            t.cancel()

    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect_no_race_conditions(self) -> None:
        """Test that no race conditions occur and final count is 0."""
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        async def rapid_subscriber():
            async for _ in broadcaster.subscribe():
                break  # Disconnect immediately

        # WHEN: Rapid connect/disconnect
        tasks = [asyncio.create_task(rapid_subscriber()) for _ in range(10)]
        await asyncio.gather(*tasks)

        # Give time for all cleanup
        await asyncio.sleep(0.1)

        # THEN: All cleaned up
        assert broadcaster.connection_count == 0

    @pytest.mark.asyncio
    async def test_queue_full_logs_warning_does_not_raise(self) -> None:
        """Test that warning is logged, no exception raised."""
        # This tests the QueueFull exception handling
        # We need to create a scenario where queue fills up

        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # Create a subscriber that doesn't consume
        queue = asyncio.Queue(maxsize=1)  # Very small queue
        async with broadcaster._lock:
            broadcaster._queues.add(queue)

        # Fill the queue
        queue.put_nowait(SSEMessage(event="test", data={}))

        # WHEN: Broadcast (queue is full)
        with patch("bmad_assist.dashboard.sse.logger") as mock_logger:
            await broadcaster.broadcast_output("test", None)

        # THEN: Warning logged, no exception
        mock_logger.warning.assert_called_once()
        assert "queue full" in mock_logger.warning.call_args[0][0].lower()

        # Cleanup
        async with broadcaster._lock:
            broadcaster._queues.discard(queue)

    @pytest.mark.asyncio
    async def test_shutdown_sends_none_to_all_queues(self) -> None:
        """Test that none is sent to all queues (shutdown signal)."""
        # GIVEN: Broadcaster with subscriber
        broadcaster = SSEBroadcaster(heartbeat_interval=60)
        shutdown_received = asyncio.Event()

        async def subscriber():
            async for _msg in broadcaster.subscribe():
                # If we get None (shutdown), the loop exits
                pass
            shutdown_received.set()

        asyncio.create_task(subscriber())
        await asyncio.sleep(0.05)

        # WHEN: Shutdown
        await broadcaster.shutdown()

        # THEN: Subscriber exits
        await asyncio.wait_for(shutdown_received.wait(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_shutdown_clears_queues_set(self) -> None:
        """Test that _queues set is cleared."""
        # GIVEN: Broadcaster with subscriber that stays connected
        broadcaster = SSEBroadcaster(heartbeat_interval=60)
        connected = asyncio.Event()

        async def subscriber():
            async for _msg in broadcaster.subscribe():
                connected.set()
                # Don't break - stay connected until shutdown sends None

        task = asyncio.create_task(subscriber())
        # Wait for subscriber to be connected
        await asyncio.wait_for(connected.wait(), timeout=1.0)

        # Verify at least one connection
        assert broadcaster.connection_count >= 1

        # WHEN: Shutdown
        await broadcaster.shutdown()
        await asyncio.wait_for(task, timeout=1.0)  # Wait for clean exit

        # THEN: Queues cleared
        assert broadcaster.connection_count == 0


# =============================================================================
# Task 5: SSE Endpoint Integration Tests (AC: 1)
# =============================================================================


class TestSSEEndpoint:
    """Integration tests for /sse/output endpoint.

    Note: SSE streams are long-running by design. These tests verify route
    registration and response structure by inspecting the sse_output function
    and routes, rather than consuming the actual stream which causes timeouts
    in ASGI test transport.
    """

    def test_sse_route_registered(self, tmp_path: Path) -> None:
        """Test that /sse/output route is registered."""
        # GIVEN: Server
        server = DashboardServer(project_root=tmp_path)
        app = server.create_app()

        # THEN: Route is registered
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/sse/output" in routes

    def test_sse_output_function_returns_streaming_response(self, tmp_path: Path) -> None:
        """Test that it returns StreamingResponse with correct media_type."""
        # Verify the route function structure
        from inspect import getsource

        from bmad_assist.dashboard.routes.sse import sse_output

        source = getsource(sse_output)

        # THEN: Uses StreamingResponse with text/event-stream
        assert "StreamingResponse" in source
        assert 'media_type="text/event-stream"' in source
        assert '"Cache-Control": "no-cache"' in source
        assert '"Connection": "keep-alive"' in source
        assert '"X-Accel-Buffering": "no"' in source

    @pytest.mark.asyncio
    async def test_sse_broadcaster_integration_with_server(self, tmp_path: Path) -> None:
        """Test that sse_broadcaster is initialized and accessible."""
        # GIVEN: Server
        server = DashboardServer(project_root=tmp_path)

        # THEN: SSE broadcaster is available
        assert server.sse_broadcaster is not None
        assert isinstance(server.sse_broadcaster, SSEBroadcaster)

    @pytest.mark.asyncio
    async def test_sse_broadcaster_accessible_via_app_state(self, tmp_path: Path) -> None:
        """Test that server (with sse_broadcaster) is available."""
        # GIVEN: Server and app
        server = DashboardServer(project_root=tmp_path)
        app = server.create_app()

        # THEN: Server accessible via app state
        assert hasattr(app.state, "server")
        assert app.state.server.sse_broadcaster is not None


# =============================================================================
# Story 16.10: SSE Integration Tests - Additional Cases
# =============================================================================


class TestSSEReconnection1610:
    """Tests for SSE reconnection scenarios (Story 16.10 Task 3.6)."""

    @pytest.mark.asyncio
    async def test_reconnection_gets_fresh_status_event(self) -> None:
        """Test that new connection after disconnect gets fresh status event.

        Subtask 3.6: Reconnection gets fresh status event.
        """
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # First connection
        async def first_connection():
            async for msg in broadcaster.subscribe():
                return msg

        first_msg = await asyncio.wait_for(first_connection(), timeout=1.0)
        assert "event: status" in first_msg

        # Give time for cleanup
        await asyncio.sleep(0.01)
        assert broadcaster.connection_count == 0

        # WHEN: Reconnect
        async def second_connection():
            async for msg in broadcaster.subscribe():
                return msg

        second_msg = await asyncio.wait_for(second_connection(), timeout=1.0)

        # THEN: Second connection also gets status event
        assert "event: status" in second_msg
        assert '"connected": true' in second_msg or '"connected":true' in second_msg

    @pytest.mark.asyncio
    async def test_reconnection_after_broadcast(self) -> None:
        """Test that reconnecting client gets status, not missed broadcasts.

        New connections should NOT receive messages sent before they connected.
        """
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # Send some broadcasts with no subscribers
        await broadcaster.broadcast_output("line 1", "opus")
        await broadcaster.broadcast_output("line 2", "opus")

        # WHEN: New client connects
        async def new_connection():
            messages = []
            async for msg in broadcaster.subscribe():
                messages.append(msg)
                if len(messages) >= 1:
                    break
            return messages

        messages = await asyncio.wait_for(new_connection(), timeout=1.0)

        # THEN: First message is status, not the missed broadcasts
        assert len(messages) == 1
        assert "event: status" in messages[0]
        # Old broadcasts are NOT received
        assert "line 1" not in messages[0]
        assert "line 2" not in messages[0]


class TestSSEFullLifecycle1610:
    """Tests for full SSE lifecycle (Story 16.10 Task 3.1)."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_connect_receive_disconnect_cleanup(self) -> None:
        """Test complete lifecycle: connect → receive status → disconnect → cleanup.

        Subtask 3.1: Full lifecycle test.
        """
        # GIVEN: Broadcaster
        broadcaster = SSEBroadcaster(heartbeat_interval=60)

        # Verify initial state
        assert broadcaster.connection_count == 0

        # WHEN: Connect
        received_messages = []
        connection_task = None

        async def subscriber():
            async for msg in broadcaster.subscribe():
                received_messages.append(msg)
                if len(received_messages) >= 2:
                    break  # Disconnect

        connection_task = asyncio.create_task(subscriber())
        await asyncio.sleep(0.05)  # Wait for subscription

        # THEN: Connected, received status
        assert broadcaster.connection_count == 1
        assert len(received_messages) >= 1
        assert "event: status" in received_messages[0]

        # Send a broadcast
        await broadcaster.broadcast_output("test", None)
        await asyncio.wait_for(connection_task, timeout=1.0)

        # After disconnect, count should be 0
        await asyncio.sleep(0.05)  # Give time for cleanup
        assert broadcaster.connection_count == 0
