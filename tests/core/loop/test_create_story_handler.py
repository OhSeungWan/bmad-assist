"""Tests for CreateStoryHandler timing tracking.

Verifies timing tracking is properly configured for create-story workflow.
"""

from pathlib import Path

import pytest

from bmad_assist.core.config import Config, MasterProviderConfig, ProviderConfig


class TestCreateStoryTimingTracking:
    """Test timing tracking for create-story workflow."""

    def test_track_timing_enabled(self) -> None:
        """CreateStoryHandler has track_timing = True."""
        from bmad_assist.core.loop.handlers.create_story import CreateStoryHandler

        config = Config(
            providers=ProviderConfig(
                master=MasterProviderConfig(provider="claude", model="opus"),
            ),
        )
        handler = CreateStoryHandler(config, Path("/tmp"))
        assert handler.track_timing is True

    def test_timing_workflow_id(self) -> None:
        """CreateStoryHandler has timing_workflow_id = 'create-story'."""
        from bmad_assist.core.loop.handlers.create_story import CreateStoryHandler

        config = Config(
            providers=ProviderConfig(
                master=MasterProviderConfig(provider="claude", model="opus"),
            ),
        )
        handler = CreateStoryHandler(config, Path("/tmp"))
        assert handler.timing_workflow_id == "create-story"

    def test_phase_name(self) -> None:
        """CreateStoryHandler has phase_name = 'create_story'."""
        from bmad_assist.core.loop.handlers.create_story import CreateStoryHandler

        config = Config(
            providers=ProviderConfig(
                master=MasterProviderConfig(provider="claude", model="opus"),
            ),
        )
        handler = CreateStoryHandler(config, Path("/tmp"))
        assert handler.phase_name == "create_story"

    def test_no_execute_override(self) -> None:
        """CreateStoryHandler does not override execute()."""
        from bmad_assist.core.loop.handlers.base import BaseHandler
        from bmad_assist.core.loop.handlers.create_story import CreateStoryHandler

        # Check that execute is inherited, not overridden
        assert CreateStoryHandler.execute is BaseHandler.execute

    def test_only_required_methods_implemented(self) -> None:
        """CreateStoryHandler only implements required methods plus timing."""
        from bmad_assist.core.loop.handlers.create_story import CreateStoryHandler

        # Get methods defined in CreateStoryHandler (not inherited)
        defined_methods = [
            name
            for name, value in CreateStoryHandler.__dict__.items()
            if callable(value) or isinstance(value, property)
        ]

        # Should have phase_name, build_context, and optional timing properties
        expected = {"phase_name", "build_context", "track_timing", "timing_workflow_id"}
        actual = {name for name in defined_methods if not name.startswith("_")}

        assert actual == expected, f"Extra methods: {actual - expected}"
