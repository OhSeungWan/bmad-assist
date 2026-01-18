"""Tests for sprint-status canonical models (Story 20.2).

Tests cover:
- SprintStatusMetadata creation and serialization
- SprintStatusEntry creation, entry_type defaults, and __repr__
- SprintStatus with multiple entry types
- get_stories_for_epic() for numeric and string epics with collision prevention
- get_epic_status() found and not found cases
- Entry ordering preservation
- to_yaml() output format
- Factory methods: empty() and from_entries()
"""

from datetime import UTC, datetime

import pytest
import yaml

from bmad_assist.sprint import (
    EntryType,
    SprintStatus,
    SprintStatusEntry,
    SprintStatusMetadata,
)


class TestSprintStatusMetadata:
    """Tests for SprintStatusMetadata model."""

    def test_metadata_with_generated_only(self) -> None:
        """Test metadata with only required field."""
        now = datetime.now(UTC).replace(tzinfo=None)
        meta = SprintStatusMetadata(generated=now)

        assert meta.generated == now
        assert meta.project is None
        assert meta.project_key is None
        assert meta.tracking_system is None
        assert meta.story_location is None

    def test_metadata_with_all_fields(self) -> None:
        """Test metadata with all fields populated."""
        now = datetime.now(UTC).replace(tzinfo=None)
        meta = SprintStatusMetadata(
            generated=now,
            project="bmad-assist",
            project_key="BMAD",
            tracking_system="BMAD",
            story_location="docs/sprint-artifacts/stories",
        )

        assert meta.generated == now
        assert meta.project == "bmad-assist"
        assert meta.project_key == "BMAD"
        assert meta.tracking_system == "BMAD"
        assert meta.story_location == "docs/sprint-artifacts/stories"

    def test_metadata_serialization(self) -> None:
        """Test metadata model_dump produces serializable dict."""
        now = datetime(2026, 1, 7, 12, 0, 0)
        meta = SprintStatusMetadata(
            generated=now,
            project="test-project",
        )

        data = meta.model_dump(mode="json")
        assert data["generated"] == "2026-01-07T12:00:00"
        assert data["project"] == "test-project"
        assert data["project_key"] is None


class TestSprintStatusEntry:
    """Tests for SprintStatusEntry model."""

    def test_entry_minimal(self) -> None:
        """Test entry with only required fields."""
        entry = SprintStatusEntry(key="12-3-auth-flow", status="done")

        assert entry.key == "12-3-auth-flow"
        assert entry.status == "done"
        assert entry.entry_type == EntryType.UNKNOWN  # Default
        assert entry.source is None
        assert entry.comment is None

    def test_entry_with_all_fields(self) -> None:
        """Test entry with all fields populated."""
        entry = SprintStatusEntry(
            key="12-3-auth-flow",
            status="done",
            entry_type=EntryType.EPIC_STORY,
            source="epic",
            comment="# Core authentication story",
        )

        assert entry.key == "12-3-auth-flow"
        assert entry.status == "done"
        assert entry.entry_type == EntryType.EPIC_STORY
        assert entry.source == "epic"
        assert entry.comment == "# Core authentication story"

    def test_entry_repr(self) -> None:
        """Test __repr__ for debugging."""
        entry = SprintStatusEntry(
            key="12-3-auth",
            status="done",
            entry_type=EntryType.EPIC_STORY,
        )

        repr_str = repr(entry)
        assert "key='12-3-auth'" in repr_str
        assert "status='done'" in repr_str
        assert "entry_type=epic_story" in repr_str

    def test_entry_serialization(self) -> None:
        """Test entry model_dump produces serializable dict."""
        entry = SprintStatusEntry(
            key="12-3-story",
            status="in-progress",
            entry_type=EntryType.EPIC_STORY,
        )

        data = entry.model_dump(mode="json")
        assert data["key"] == "12-3-story"
        assert data["status"] == "in-progress"
        assert data["entry_type"] == "epic_story"


class TestSprintStatus:
    """Tests for SprintStatus container model."""

    @pytest.fixture
    def sample_metadata(self) -> SprintStatusMetadata:
        """Create sample metadata for tests."""
        return SprintStatusMetadata(
            generated=datetime(2026, 1, 7, 12, 0, 0),
            project="bmad-assist",
        )

    @pytest.fixture
    def sample_entries(self) -> dict[str, SprintStatusEntry]:
        """Create sample entries for tests."""
        return {
            "epic-12": SprintStatusEntry(
                key="epic-12",
                status="in-progress",
                entry_type=EntryType.EPIC_META,
            ),
            "12-1-setup": SprintStatusEntry(
                key="12-1-setup",
                status="done",
                entry_type=EntryType.EPIC_STORY,
            ),
            "12-2-config": SprintStatusEntry(
                key="12-2-config",
                status="in-progress",
                entry_type=EntryType.EPIC_STORY,
            ),
            "12-3-core": SprintStatusEntry(
                key="12-3-core",
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            ),
            "testarch-1-framework": SprintStatusEntry(
                key="testarch-1-framework",
                status="done",
                entry_type=EntryType.MODULE_STORY,
            ),
            "standalone-01-refactor": SprintStatusEntry(
                key="standalone-01-refactor",
                status="done",
                entry_type=EntryType.STANDALONE,
            ),
        }

    def test_sprint_status_creation(
        self,
        sample_metadata: SprintStatusMetadata,
        sample_entries: dict[str, SprintStatusEntry],
    ) -> None:
        """Test SprintStatus creation with metadata and entries."""
        status = SprintStatus(
            metadata=sample_metadata,
            entries=sample_entries,
        )

        assert status.metadata.project == "bmad-assist"
        assert len(status.entries) == 6

    def test_entry_ordering_preserved(
        self,
        sample_metadata: SprintStatusMetadata,
    ) -> None:
        """Test that entry insertion order is preserved."""
        entries: dict[str, SprintStatusEntry] = {}
        for i, key in enumerate(["zebra-1-a", "alpha-1-b", "mike-1-c", "bravo-1-d"]):
            entries[key] = SprintStatusEntry(
                key=key,
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            )

        status = SprintStatus(metadata=sample_metadata, entries=entries)

        # Order should be preserved (zebra, alpha, mike, bravo - insertion order)
        keys = list(status.entries.keys())
        assert keys == ["zebra-1-a", "alpha-1-b", "mike-1-c", "bravo-1-d"]

    def test_get_stories_for_epic_numeric(
        self,
        sample_metadata: SprintStatusMetadata,
        sample_entries: dict[str, SprintStatusEntry],
    ) -> None:
        """Test get_stories_for_epic with numeric epic ID."""
        status = SprintStatus(metadata=sample_metadata, entries=sample_entries)

        stories = status.get_stories_for_epic(12)

        assert len(stories) == 3
        keys = [s.key for s in stories]
        assert "12-1-setup" in keys
        assert "12-2-config" in keys
        assert "12-3-core" in keys
        # Should NOT include epic-12 (EPIC_META) or standalone
        assert "epic-12" not in keys

    def test_get_stories_for_epic_string(
        self,
        sample_metadata: SprintStatusMetadata,
        sample_entries: dict[str, SprintStatusEntry],
    ) -> None:
        """Test get_stories_for_epic with string epic ID (module)."""
        status = SprintStatus(metadata=sample_metadata, entries=sample_entries)

        stories = status.get_stories_for_epic("testarch")

        assert len(stories) == 1
        assert stories[0].key == "testarch-1-framework"

    def test_get_stories_for_epic_no_collision(
        self,
        sample_metadata: SprintStatusMetadata,
    ) -> None:
        """Test that epic 1 does not match '12-3-story' (prefix collision)."""
        entries = {
            "1-1-first": SprintStatusEntry(
                key="1-1-first",
                status="done",
                entry_type=EntryType.EPIC_STORY,
            ),
            "12-3-other": SprintStatusEntry(
                key="12-3-other",
                status="done",
                entry_type=EntryType.EPIC_STORY,
            ),
            "1-2-second": SprintStatusEntry(
                key="1-2-second",
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            ),
        }
        status = SprintStatus(metadata=sample_metadata, entries=entries)

        # Epic 1 should only match 1-1 and 1-2, NOT 12-3
        stories = status.get_stories_for_epic(1)

        assert len(stories) == 2
        keys = [s.key for s in stories]
        assert "1-1-first" in keys
        assert "1-2-second" in keys
        assert "12-3-other" not in keys

    def test_get_stories_for_epic_empty(
        self,
        sample_metadata: SprintStatusMetadata,
        sample_entries: dict[str, SprintStatusEntry],
    ) -> None:
        """Test get_stories_for_epic returns empty list for unknown epic."""
        status = SprintStatus(metadata=sample_metadata, entries=sample_entries)

        stories = status.get_stories_for_epic(99)

        assert stories == []

    def test_get_epic_status_found(
        self,
        sample_metadata: SprintStatusMetadata,
        sample_entries: dict[str, SprintStatusEntry],
    ) -> None:
        """Test get_epic_status when epic entry exists."""
        status = SprintStatus(metadata=sample_metadata, entries=sample_entries)

        result = status.get_epic_status(12)

        assert result == "in-progress"

    def test_get_epic_status_not_found(
        self,
        sample_metadata: SprintStatusMetadata,
        sample_entries: dict[str, SprintStatusEntry],
    ) -> None:
        """Test get_epic_status when epic entry does not exist."""
        status = SprintStatus(metadata=sample_metadata, entries=sample_entries)

        result = status.get_epic_status(99)

        assert result is None

    def test_get_epic_status_string_epic(
        self,
        sample_metadata: SprintStatusMetadata,
    ) -> None:
        """Test get_epic_status with string epic ID."""
        entries = {
            "epic-testarch": SprintStatusEntry(
                key="epic-testarch",
                status="done",
                entry_type=EntryType.EPIC_META,
            ),
        }
        status = SprintStatus(metadata=sample_metadata, entries=entries)

        result = status.get_epic_status("testarch")

        assert result == "done"

    def test_to_yaml_basic(
        self,
        sample_metadata: SprintStatusMetadata,
    ) -> None:
        """Test to_yaml produces valid YAML output."""
        entries = {
            "12-1-setup": SprintStatusEntry(
                key="12-1-setup",
                status="done",
                entry_type=EntryType.EPIC_STORY,
            ),
            "12-2-config": SprintStatusEntry(
                key="12-2-config",
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            ),
        }
        status = SprintStatus(metadata=sample_metadata, entries=entries)

        yaml_str = status.to_yaml()

        # Verify it's valid YAML
        data = yaml.safe_load(yaml_str)
        assert "generated" in data
        assert "development_status" in data
        assert data["development_status"]["12-1-setup"] == "done"
        assert data["development_status"]["12-2-config"] == "backlog"

    def test_to_yaml_includes_optional_metadata(
        self,
    ) -> None:
        """Test to_yaml includes optional metadata fields when present."""
        meta = SprintStatusMetadata(
            generated=datetime(2026, 1, 7, 12, 0, 0),
            project="test-project",
            tracking_system="BMAD",
        )
        status = SprintStatus(metadata=meta, entries={})

        yaml_str = status.to_yaml()
        data = yaml.safe_load(yaml_str)

        assert data["project"] == "test-project"
        assert data["tracking_system"] == "BMAD"
        # project_key and story_location are None, should be excluded
        assert "project_key" not in data
        assert "story_location" not in data

    def test_to_yaml_preserves_entry_order(
        self,
        sample_metadata: SprintStatusMetadata,
    ) -> None:
        """Test to_yaml preserves entry ordering."""
        entries = {}
        keys_order = ["zebra-1-a", "alpha-1-b", "mike-1-c", "bravo-1-d"]
        for key in keys_order:
            entries[key] = SprintStatusEntry(
                key=key,
                status="backlog",
                entry_type=EntryType.EPIC_STORY,
            )
        status = SprintStatus(metadata=sample_metadata, entries=entries)

        yaml_str = status.to_yaml()
        data = yaml.safe_load(yaml_str)

        # YAML dict preserves insertion order in Python 3.7+
        result_keys = list(data["development_status"].keys())
        assert result_keys == keys_order


class TestSprintStatusFactoryMethods:
    """Tests for SprintStatus factory methods."""

    def test_empty_without_project(self) -> None:
        """Test empty() factory without project name."""
        status = SprintStatus.empty()

        assert len(status.entries) == 0
        assert status.metadata.generated is not None
        assert status.metadata.project is None

    def test_empty_with_project(self) -> None:
        """Test empty() factory with project name."""
        status = SprintStatus.empty("bmad-assist")

        assert len(status.entries) == 0
        assert status.metadata.project == "bmad-assist"

    def test_from_entries_without_metadata(self) -> None:
        """Test from_entries() without explicit metadata."""
        entries = [
            SprintStatusEntry(key="1-1-first", status="done"),
            SprintStatusEntry(key="1-2-second", status="backlog"),
        ]

        status = SprintStatus.from_entries(entries)

        assert len(status.entries) == 2
        assert status.entries["1-1-first"].status == "done"
        assert status.entries["1-2-second"].status == "backlog"
        # Default metadata should be generated
        assert status.metadata.generated is not None

    def test_from_entries_with_metadata(self) -> None:
        """Test from_entries() with explicit metadata."""
        meta = SprintStatusMetadata(
            generated=datetime(2026, 1, 7, 12, 0, 0),
            project="test-project",
        )
        entries = [
            SprintStatusEntry(key="1-1-first", status="done"),
        ]

        status = SprintStatus.from_entries(entries, metadata=meta)

        assert status.metadata.project == "test-project"
        assert len(status.entries) == 1

    def test_from_entries_preserves_order(self) -> None:
        """Test from_entries() preserves list order."""
        entries = [
            SprintStatusEntry(key="zebra-1-a", status="done"),
            SprintStatusEntry(key="alpha-1-b", status="backlog"),
            SprintStatusEntry(key="mike-1-c", status="in-progress"),
        ]

        status = SprintStatus.from_entries(entries)

        keys = list(status.entries.keys())
        assert keys == ["zebra-1-a", "alpha-1-b", "mike-1-c"]

    def test_from_entries_empty_list(self) -> None:
        """Test from_entries() with empty entry list."""
        status = SprintStatus.from_entries([])

        assert len(status.entries) == 0
        assert status.metadata.generated is not None


class TestSprintStatusEntryTypes:
    """Tests for SprintStatus with various entry types."""

    @pytest.fixture
    def mixed_entries_status(self) -> SprintStatus:
        """Create SprintStatus with all entry types."""
        meta = SprintStatusMetadata(
            generated=datetime(2026, 1, 7, 12, 0, 0),
        )
        entries = {
            "epic-12": SprintStatusEntry(
                key="epic-12",
                status="in-progress",
                entry_type=EntryType.EPIC_META,
            ),
            "12-1-story": SprintStatusEntry(
                key="12-1-story",
                status="done",
                entry_type=EntryType.EPIC_STORY,
            ),
            "testarch-1-config": SprintStatusEntry(
                key="testarch-1-config",
                status="done",
                entry_type=EntryType.MODULE_STORY,
            ),
            "standalone-01-refactor": SprintStatusEntry(
                key="standalone-01-refactor",
                status="done",
                entry_type=EntryType.STANDALONE,
            ),
            "epic-12-retrospective": SprintStatusEntry(
                key="epic-12-retrospective",
                status="done",
                entry_type=EntryType.RETROSPECTIVE,
            ),
            "custom-entry": SprintStatusEntry(
                key="custom-entry",
                status="blocked",
                entry_type=EntryType.UNKNOWN,
            ),
        }
        return SprintStatus(metadata=meta, entries=entries)

    def test_get_stories_only_includes_story_types(
        self,
        mixed_entries_status: SprintStatus,
    ) -> None:
        """Test that get_stories_for_epic only returns EPIC_STORY and MODULE_STORY."""
        # For epic 12, should only get EPIC_STORY entries, not EPIC_META, RETRO, etc.
        stories = mixed_entries_status.get_stories_for_epic(12)

        assert len(stories) == 1
        assert stories[0].key == "12-1-story"
        assert stories[0].entry_type == EntryType.EPIC_STORY

    def test_all_entry_types_preserved(
        self,
        mixed_entries_status: SprintStatus,
    ) -> None:
        """Test that all entry types are preserved in entries dict."""
        entry_types = {e.entry_type for e in mixed_entries_status.entries.values()}

        assert EntryType.EPIC_META in entry_types
        assert EntryType.EPIC_STORY in entry_types
        assert EntryType.MODULE_STORY in entry_types
        assert EntryType.STANDALONE in entry_types
        assert EntryType.RETROSPECTIVE in entry_types
        assert EntryType.UNKNOWN in entry_types
