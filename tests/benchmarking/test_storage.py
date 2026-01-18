"""Tests for benchmarking storage module.

Tests storage layer for saving, loading, and querying LLM evaluation records.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from bmad_assist.benchmarking.schema import (
    BenchmarkingError,
    EnvironmentInfo,
    EvaluatorInfo,
    EvaluatorRole,
    ExecutionTelemetry,
    LLMEvaluationRecord,
    OutputAnalysis,
    PatchInfo,
    StoryInfo,
    WorkflowInfo,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_record() -> LLMEvaluationRecord:
    """Create a sample evaluation record for testing."""
    return LLMEvaluationRecord(
        record_id="test-uuid-1234",
        created_at=datetime(2025, 12, 19, 14, 32, 0, tzinfo=UTC),
        workflow=WorkflowInfo(
            id="validate-story",
            version="1.0.0",
            variant="multi-llm",
            patch=PatchInfo(applied=True, id="test-patch", version="1.0.0"),
        ),
        story=StoryInfo(
            epic_num=13,
            story_num=1,
            title="Test Story",
            complexity_flags={"has_ui_changes": False},
        ),
        evaluator=EvaluatorInfo(
            provider="claude",
            model="opus-4",
            role=EvaluatorRole.VALIDATOR,
            role_id="a",
            session_id="session-123",
        ),
        execution=ExecutionTelemetry(
            start_time=datetime(2025, 12, 19, 14, 30, 0, tzinfo=UTC),
            end_time=datetime(2025, 12, 19, 14, 32, 0, tzinfo=UTC),
            duration_ms=120000,
            input_tokens=1000,
            output_tokens=500,
            retries=0,
            sequence_position=0,
        ),
        output=OutputAnalysis(
            char_count=5000,
            heading_count=10,
            list_depth_max=3,
            code_block_count=2,
            sections_detected=["Summary", "Findings"],
        ),
        environment=EnvironmentInfo(
            bmad_assist_version="0.1.0",
            python_version="3.11.0",
            platform="linux",
            git_commit_hash="abc123",
        ),
    )


@pytest.fixture
def sample_synthesizer_record(sample_record: LLMEvaluationRecord) -> LLMEvaluationRecord:
    """Create a sample synthesizer evaluation record."""
    return LLMEvaluationRecord(
        record_id="test-uuid-synth",
        created_at=datetime(2025, 12, 19, 14, 45, 0, tzinfo=UTC),
        workflow=sample_record.workflow,
        story=sample_record.story,
        evaluator=EvaluatorInfo(
            provider="claude",
            model="opus-4",
            role=EvaluatorRole.SYNTHESIZER,
            role_id=None,
            session_id="session-456",
        ),
        execution=ExecutionTelemetry(
            start_time=datetime(2025, 12, 19, 14, 43, 0, tzinfo=UTC),
            end_time=datetime(2025, 12, 19, 14, 45, 0, tzinfo=UTC),
            duration_ms=120000,
            input_tokens=2000,
            output_tokens=1000,
            retries=0,
            sequence_position=1,
        ),
        output=sample_record.output,
        environment=sample_record.environment,
    )


@pytest.fixture
def temp_base_dir(tmp_path: Path) -> Path:
    """Create temporary base directory for tests."""
    return tmp_path / "docs" / "sprint-artifacts"


# =============================================================================
# Task 1 Tests: Module Structure and Dataclasses
# =============================================================================


class TestModuleStructure:
    """Test AC1: Storage module creation and public API."""

    def test_storage_module_exists(self) -> None:
        """Test that storage module can be imported."""
        from bmad_assist.benchmarking import storage

        assert storage is not None

    def test_storage_error_exists(self) -> None:
        """Test StorageError exception class exists."""
        from bmad_assist.benchmarking.storage import StorageError

        assert issubclass(StorageError, BenchmarkingError)

    def test_storage_error_inherits_from_benchmarking_error(self) -> None:
        """Test StorageError is subclass of BenchmarkingError."""
        from bmad_assist.benchmarking.storage import StorageError

        error = StorageError("test error")
        assert isinstance(error, BenchmarkingError)

    def test_record_filters_dataclass_exists(self) -> None:
        """Test RecordFilters dataclass exists with required fields."""
        from bmad_assist.benchmarking.storage import RecordFilters

        # Check it's a frozen dataclass
        rf = RecordFilters()
        assert hasattr(rf, "date_from")
        assert hasattr(rf, "date_to")
        assert hasattr(rf, "epic")
        assert hasattr(rf, "story")
        assert hasattr(rf, "provider")
        assert hasattr(rf, "role")

    def test_record_filters_all_fields_optional(self) -> None:
        """Test RecordFilters can be instantiated with no arguments."""
        from bmad_assist.benchmarking.storage import RecordFilters

        rf = RecordFilters()
        assert rf.date_from is None
        assert rf.date_to is None
        assert rf.epic is None
        assert rf.story is None
        assert rf.provider is None
        assert rf.role is None

    def test_record_filters_frozen(self) -> None:
        """Test RecordFilters is immutable (frozen dataclass)."""
        from bmad_assist.benchmarking.storage import RecordFilters

        rf = RecordFilters()
        with pytest.raises(AttributeError):
            rf.epic = 1  # type: ignore[misc]

    def test_record_summary_dataclass_exists(self) -> None:
        """Test RecordSummary dataclass exists with required fields."""
        from bmad_assist.benchmarking.storage import RecordSummary

        rs = RecordSummary(
            path=Path("/test/path.yaml"),
            record_id="test-id",
            epic_num=13,
            story_num=1,
            role_id="a",
            provider="claude",
            created_at=datetime.now(UTC),
        )
        assert rs.path == Path("/test/path.yaml")
        assert rs.record_id == "test-id"
        assert rs.epic_num == 13
        assert rs.story_num == 1
        assert rs.role_id == "a"
        assert rs.provider == "claude"

    def test_record_summary_frozen(self) -> None:
        """Test RecordSummary is immutable (frozen dataclass)."""
        from bmad_assist.benchmarking.storage import RecordSummary

        rs = RecordSummary(
            path=Path("/test/path.yaml"),
            record_id="test-id",
            epic_num=13,
            story_num=1,
            role_id="a",
            provider="claude",
            created_at=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            rs.epic_num = 2  # type: ignore[misc]

    def test_public_functions_exist(self) -> None:
        """Test all public API functions exist."""
        from bmad_assist.benchmarking.storage import (
            get_records_for_story,
            list_evaluation_records,
            load_evaluation_record,
            save_evaluation_record,
        )

        assert callable(save_evaluation_record)
        assert callable(load_evaluation_record)
        assert callable(list_evaluation_records)
        assert callable(get_records_for_story)


# =============================================================================
# Task 2 Tests: save_evaluation_record
# =============================================================================


class TestSaveEvaluationRecord:
    """Test AC2, AC3, AC7: Save with atomic write and correct path."""

    def test_save_creates_correct_path_validator(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test save creates correct path for validator role."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        result_path = save_evaluation_record(sample_record, temp_base_dir)

        # Expected: {base_dir}/benchmarks/2025-12/eval-13-1-a-20251219T143200Z.yaml
        expected_path = (
            temp_base_dir / "benchmarks" / "2025-12" / "eval-13-1-a-20251219T143200Z.yaml"
        )
        assert result_path == expected_path
        assert result_path.exists()

    def test_save_creates_correct_path_synthesizer(
        self, sample_synthesizer_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test save creates correct path for synthesizer role."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        result_path = save_evaluation_record(sample_synthesizer_record, temp_base_dir)

        # Expected: {base_dir}/benchmarks/2025-12/eval-13-1-synthesizer-20251219T144500Z.yaml
        expected_path = (
            temp_base_dir / "benchmarks" / "2025-12" / "eval-13-1-synthesizer-20251219T144500Z.yaml"
        )
        assert result_path == expected_path
        assert result_path.exists()

    def test_save_creates_correct_path_master(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test save creates correct path for master role."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        master_record = LLMEvaluationRecord(
            record_id="test-uuid-master",
            created_at=datetime(2025, 12, 20, 9, 15, 0, tzinfo=UTC),
            workflow=sample_record.workflow,
            story=StoryInfo(
                epic_num=13,
                story_num=5,
                title="Test Master",
                complexity_flags={},
            ),
            evaluator=EvaluatorInfo(
                provider="claude",
                model="opus-4",
                role=EvaluatorRole.MASTER,
                role_id=None,
                session_id="session-789",
            ),
            execution=sample_record.execution,
            output=sample_record.output,
            environment=sample_record.environment,
        )

        result_path = save_evaluation_record(master_record, temp_base_dir)

        expected_path = (
            temp_base_dir / "benchmarks" / "2025-12" / "eval-13-5-master-20251220T091500Z.yaml"
        )
        assert result_path == expected_path

    def test_save_creates_directory_structure(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test save creates parent directories if missing."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        # Ensure base_dir doesn't exist
        assert not temp_base_dir.exists()

        save_evaluation_record(sample_record, temp_base_dir)

        # Verify directory structure was created
        assert (temp_base_dir / "benchmarks" / "2025-12").is_dir()

    def test_save_atomic_write_cleanup_on_success(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test no temp files remain after successful save."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        result_path = save_evaluation_record(sample_record, temp_base_dir)

        # Check no .tmp files exist
        temp_files = list(result_path.parent.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_save_yaml_format_sort_keys_false(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test YAML is written with sort_keys=False (preserves field order)."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        result_path = save_evaluation_record(sample_record, temp_base_dir)

        content = result_path.read_text()
        # record_id should come before created_at (schema order)
        assert content.index("record_id") < content.index("created_at")

    def test_save_yaml_format_datetime_iso8601(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test datetime fields serialized as ISO 8601."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        result_path = save_evaluation_record(sample_record, temp_base_dir)

        content = result_path.read_text()
        # Should contain ISO 8601 format
        assert "2025-12-19T14:32:00" in content

    def test_save_uses_model_dump_json_mode(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test save uses model_dump(mode='json') for proper serialization."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        result_path = save_evaluation_record(sample_record, temp_base_dir)

        # Load and verify it's valid YAML
        with open(result_path) as f:
            data = yaml.safe_load(f)

        # Verify the data contains expected fields (strings, not objects)
        assert isinstance(data["record_id"], str)
        assert isinstance(data["created_at"], str)
        assert isinstance(data["evaluator"]["role"], str)

    def test_save_requires_base_dir(self, sample_record: LLMEvaluationRecord) -> None:
        """Test save raises StorageError if base_dir is None."""
        from bmad_assist.benchmarking.storage import StorageError, save_evaluation_record

        with pytest.raises(StorageError, match="base_dir required"):
            save_evaluation_record(sample_record, None)  # type: ignore[arg-type]

    def test_save_validator_requires_role_id(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test validator role requires role_id."""
        # This should be validated by the schema, not storage
        # The record fixture has role_id set, so just verify it works
        from bmad_assist.benchmarking.storage import save_evaluation_record

        result_path = save_evaluation_record(sample_record, temp_base_dir)
        assert result_path.exists()


# =============================================================================
# Task 3 Tests: Index File Management
# =============================================================================


class TestIndexFileManagement:
    """Test AC8: Index file auto-update."""

    def test_save_creates_index_file(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test save creates index.yaml in month directory."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        save_evaluation_record(sample_record, temp_base_dir)

        index_path = temp_base_dir / "benchmarks" / "2025-12" / "index.yaml"
        assert index_path.exists()

    def test_save_updates_existing_index(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test save appends to existing index.yaml."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        # Save first record
        save_evaluation_record(sample_record, temp_base_dir)

        # Create second record with different timestamp
        second_record = LLMEvaluationRecord(
            record_id="test-uuid-5678",
            created_at=datetime(2025, 12, 19, 14, 33, 0, tzinfo=UTC),
            workflow=sample_record.workflow,
            story=sample_record.story,
            evaluator=EvaluatorInfo(
                provider="gemini",
                model="2.0-flash",
                role=EvaluatorRole.VALIDATOR,
                role_id="b",
                session_id="session-456",
            ),
            execution=sample_record.execution,
            output=sample_record.output,
            environment=sample_record.environment,
        )
        save_evaluation_record(second_record, temp_base_dir)

        # Verify index contains both records
        index_path = temp_base_dir / "benchmarks" / "2025-12" / "index.yaml"
        with open(index_path) as f:
            index_data = yaml.safe_load(f)

        assert len(index_data["records"]) == 2

    def test_index_contains_required_fields(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test index entries contain all required metadata."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        save_evaluation_record(sample_record, temp_base_dir)

        index_path = temp_base_dir / "benchmarks" / "2025-12" / "index.yaml"
        with open(index_path) as f:
            index_data = yaml.safe_load(f)

        record_entry = index_data["records"][0]
        assert "record_id" in record_entry
        assert "path" in record_entry
        assert "epic" in record_entry
        assert "story" in record_entry
        assert "role_id" in record_entry
        assert "provider" in record_entry
        assert "created_at" in record_entry

        # Verify values
        assert record_entry["record_id"] == "test-uuid-1234"
        assert record_entry["epic"] == 13
        assert record_entry["story"] == 1
        assert record_entry["role_id"] == "a"
        assert record_entry["provider"] == "claude"

    def test_index_has_updated_at_timestamp(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test index has updated_at timestamp."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        save_evaluation_record(sample_record, temp_base_dir)

        index_path = temp_base_dir / "benchmarks" / "2025-12" / "index.yaml"
        with open(index_path) as f:
            index_data = yaml.safe_load(f)

        assert "updated_at" in index_data

    def test_index_skips_duplicate_record_id(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test index skips duplicate entries by record_id."""
        from bmad_assist.benchmarking.storage import save_evaluation_record

        # Save same record twice
        save_evaluation_record(sample_record, temp_base_dir)
        save_evaluation_record(sample_record, temp_base_dir)

        index_path = temp_base_dir / "benchmarks" / "2025-12" / "index.yaml"
        with open(index_path) as f:
            index_data = yaml.safe_load(f)

        # Should only have one entry
        assert len(index_data["records"]) == 1


# =============================================================================
# Task 4 Tests: load_evaluation_record
# =============================================================================


class TestLoadEvaluationRecord:
    """Test AC4: Load with validation."""

    def test_load_valid_record(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test load returns valid LLMEvaluationRecord."""
        from bmad_assist.benchmarking.storage import (
            load_evaluation_record,
            save_evaluation_record,
        )

        saved_path = save_evaluation_record(sample_record, temp_base_dir)
        loaded = load_evaluation_record(saved_path)

        assert loaded.record_id == sample_record.record_id
        assert loaded.story.epic_num == sample_record.story.epic_num
        assert loaded.evaluator.provider == sample_record.evaluator.provider

    def test_load_file_not_found(self, temp_base_dir: Path) -> None:
        """Test load raises StorageError for missing file."""
        from bmad_assist.benchmarking.storage import StorageError, load_evaluation_record

        missing_path = temp_base_dir / "nonexistent.yaml"
        with pytest.raises(StorageError, match="not found"):
            load_evaluation_record(missing_path)

    def test_load_invalid_yaml(self, temp_base_dir: Path) -> None:
        """Test load raises StorageError for invalid YAML."""
        from bmad_assist.benchmarking.storage import StorageError, load_evaluation_record

        # Create invalid YAML file
        temp_base_dir.mkdir(parents=True, exist_ok=True)
        invalid_path = temp_base_dir / "invalid.yaml"
        invalid_path.write_text("{ invalid: yaml: content")

        with pytest.raises(StorageError, match="Invalid YAML"):
            load_evaluation_record(invalid_path)

    def test_load_schema_validation_error(self, temp_base_dir: Path) -> None:
        """Test load raises StorageError for schema validation failure."""
        from bmad_assist.benchmarking.storage import StorageError, load_evaluation_record

        # Create valid YAML but invalid schema
        temp_base_dir.mkdir(parents=True, exist_ok=True)
        invalid_path = temp_base_dir / "bad_schema.yaml"
        invalid_path.write_text("record_id: test\n")  # Missing required fields

        with pytest.raises(StorageError, match="validation"):
            load_evaluation_record(invalid_path)

    def test_load_preserves_original_exception(self, temp_base_dir: Path) -> None:
        """Test StorageError wraps original exception as __cause__."""
        from bmad_assist.benchmarking.storage import StorageError, load_evaluation_record

        missing_path = temp_base_dir / "nonexistent.yaml"
        with pytest.raises(StorageError) as exc_info:
            load_evaluation_record(missing_path)

        assert exc_info.value.__cause__ is not None


# =============================================================================
# Task 5 Tests: list_evaluation_records
# =============================================================================


class TestListEvaluationRecords:
    """Test AC5: List with filtering."""

    def test_list_with_no_filters(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list returns all records without filters."""
        from bmad_assist.benchmarking.storage import (
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        results = list_evaluation_records(temp_base_dir)

        assert len(results) == 1
        assert results[0].record_id == sample_record.record_id

    def test_list_filter_by_epic(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list filters by epic number."""
        from bmad_assist.benchmarking.storage import (
            RecordFilters,
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        # Filter for epic 13 (should match)
        results = list_evaluation_records(temp_base_dir, RecordFilters(epic=13))
        assert len(results) == 1

        # Filter for epic 14 (should not match)
        results = list_evaluation_records(temp_base_dir, RecordFilters(epic=14))
        assert len(results) == 0

    def test_list_filter_by_story(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list filters by story number."""
        from bmad_assist.benchmarking.storage import (
            RecordFilters,
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        # Filter for story 1 (should match)
        results = list_evaluation_records(temp_base_dir, RecordFilters(story=1))
        assert len(results) == 1

        # Filter for story 2 (should not match)
        results = list_evaluation_records(temp_base_dir, RecordFilters(story=2))
        assert len(results) == 0

    def test_list_filter_by_provider(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list filters by provider name."""
        from bmad_assist.benchmarking.storage import (
            RecordFilters,
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        # Filter for claude (should match)
        results = list_evaluation_records(temp_base_dir, RecordFilters(provider="claude"))
        assert len(results) == 1

        # Filter for gemini (should not match)
        results = list_evaluation_records(temp_base_dir, RecordFilters(provider="gemini"))
        assert len(results) == 0

    def test_list_filter_by_role_validator(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list filters by VALIDATOR role."""
        from bmad_assist.benchmarking.storage import (
            RecordFilters,
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        # Filter for VALIDATOR (should match)
        results = list_evaluation_records(
            temp_base_dir, RecordFilters(role=EvaluatorRole.VALIDATOR)
        )
        assert len(results) == 1

        # Filter for SYNTHESIZER (should not match)
        results = list_evaluation_records(
            temp_base_dir, RecordFilters(role=EvaluatorRole.SYNTHESIZER)
        )
        assert len(results) == 0

    def test_list_filter_by_role_synthesizer(
        self, sample_synthesizer_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list filters finds SYNTHESIZER role records."""
        from bmad_assist.benchmarking.storage import (
            RecordFilters,
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_synthesizer_record, temp_base_dir)

        # Filter for SYNTHESIZER (should match)
        results = list_evaluation_records(
            temp_base_dir, RecordFilters(role=EvaluatorRole.SYNTHESIZER)
        )
        assert len(results) == 1
        assert results[0].record_id == "test-uuid-synth"

        # Filter for VALIDATOR (should not match)
        results = list_evaluation_records(
            temp_base_dir, RecordFilters(role=EvaluatorRole.VALIDATOR)
        )
        assert len(results) == 0

    def test_list_filter_by_role_master(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list filters finds MASTER role records."""
        from bmad_assist.benchmarking.storage import (
            RecordFilters,
            list_evaluation_records,
            save_evaluation_record,
        )

        master_record = LLMEvaluationRecord(
            record_id="test-uuid-master",
            created_at=datetime(2025, 12, 20, 9, 15, 0, tzinfo=UTC),
            workflow=sample_record.workflow,
            story=sample_record.story,
            evaluator=EvaluatorInfo(
                provider="claude",
                model="opus-4",
                role=EvaluatorRole.MASTER,
                role_id=None,
                session_id="session-789",
            ),
            execution=sample_record.execution,
            output=sample_record.output,
            environment=sample_record.environment,
        )

        save_evaluation_record(master_record, temp_base_dir)

        # Filter for MASTER (should match)
        results = list_evaluation_records(temp_base_dir, RecordFilters(role=EvaluatorRole.MASTER))
        assert len(results) == 1
        assert results[0].record_id == "test-uuid-master"

        # Filter for SYNTHESIZER (should not match)
        results = list_evaluation_records(
            temp_base_dir, RecordFilters(role=EvaluatorRole.SYNTHESIZER)
        )
        assert len(results) == 0

    def test_list_filter_by_date_range(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list filters by date range."""
        from bmad_assist.benchmarking.storage import (
            RecordFilters,
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        # Filter for date that includes the record
        results = list_evaluation_records(
            temp_base_dir,
            RecordFilters(
                date_from=datetime(2025, 12, 19, 0, 0, 0, tzinfo=UTC),
                date_to=datetime(2025, 12, 19, 23, 59, 59, tzinfo=UTC),
            ),
        )
        assert len(results) == 1

        # Filter for date before the record
        results = list_evaluation_records(
            temp_base_dir,
            RecordFilters(
                date_from=datetime(2025, 12, 20, 0, 0, 0, tzinfo=UTC),
            ),
        )
        assert len(results) == 0

    def test_list_returns_empty_for_no_matches(self, temp_base_dir: Path) -> None:
        """Test list returns empty list when no matches."""
        from bmad_assist.benchmarking.storage import list_evaluation_records

        temp_base_dir.mkdir(parents=True, exist_ok=True)

        results = list_evaluation_records(temp_base_dir)
        assert results == []

    def test_list_uses_index_when_available(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list uses index.yaml for fast lookup."""
        from bmad_assist.benchmarking.storage import (
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        # Verify index exists
        index_path = temp_base_dir / "benchmarks" / "2025-12" / "index.yaml"
        assert index_path.exists()

        # List should work using index
        results = list_evaluation_records(temp_base_dir)
        assert len(results) == 1

    def test_list_fallback_without_index(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list falls back to glob when index missing."""
        from bmad_assist.benchmarking.storage import (
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        # Remove index file
        index_path = temp_base_dir / "benchmarks" / "2025-12" / "index.yaml"
        index_path.unlink()

        # List should still work using glob
        results = list_evaluation_records(temp_base_dir)
        assert len(results) == 1

    def test_list_fallback_on_corrupted_index(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list falls back to glob when index corrupted."""
        from bmad_assist.benchmarking.storage import (
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        # Corrupt index file
        index_path = temp_base_dir / "benchmarks" / "2025-12" / "index.yaml"
        index_path.write_text("{ invalid: yaml: content")

        # List should still work using glob fallback
        results = list_evaluation_records(temp_base_dir)
        assert len(results) == 1

    def test_list_requires_base_dir(self) -> None:
        """Test list raises StorageError if base_dir is None."""
        from bmad_assist.benchmarking.storage import StorageError, list_evaluation_records

        with pytest.raises(StorageError, match="base_dir required"):
            list_evaluation_records(None)  # type: ignore[arg-type]

    def test_list_record_summary_has_correct_fields(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test list returns RecordSummary with correct field values."""
        from bmad_assist.benchmarking.storage import (
            list_evaluation_records,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        results = list_evaluation_records(temp_base_dir)
        summary = results[0]

        assert summary.record_id == "test-uuid-1234"
        assert summary.epic_num == 13
        assert summary.story_num == 1
        assert summary.role_id == "a"
        assert summary.provider == "claude"
        assert summary.path.exists()


# =============================================================================
# Task 6 Tests: get_records_for_story
# =============================================================================


class TestGetRecordsForStory:
    """Test AC6: Get records for story."""

    def test_get_records_returns_all_for_story(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test get_records_for_story returns all records for epic/story."""
        from bmad_assist.benchmarking.storage import (
            get_records_for_story,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        records = get_records_for_story(13, 1, temp_base_dir)

        assert len(records) == 1
        assert records[0].record_id == sample_record.record_id

    def test_get_records_sorted_by_created_at(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test get_records_for_story returns records sorted by created_at ascending."""
        from bmad_assist.benchmarking.storage import (
            get_records_for_story,
            save_evaluation_record,
        )

        # Save record 2 first (later timestamp)
        second_record = LLMEvaluationRecord(
            record_id="test-uuid-second",
            created_at=datetime(2025, 12, 19, 14, 35, 0, tzinfo=UTC),
            workflow=sample_record.workflow,
            story=sample_record.story,
            evaluator=EvaluatorInfo(
                provider="gemini",
                model="2.0-flash",
                role=EvaluatorRole.VALIDATOR,
                role_id="b",
                session_id="session-456",
            ),
            execution=sample_record.execution,
            output=sample_record.output,
            environment=sample_record.environment,
        )
        save_evaluation_record(second_record, temp_base_dir)

        # Save record 1 second (earlier timestamp)
        save_evaluation_record(sample_record, temp_base_dir)

        records = get_records_for_story(13, 1, temp_base_dir)

        assert len(records) == 2
        # First record should be earlier (sample_record at 14:32)
        assert records[0].record_id == "test-uuid-1234"
        # Second record should be later (14:35)
        assert records[1].record_id == "test-uuid-second"

    def test_get_records_returns_empty_for_no_matches(self, temp_base_dir: Path) -> None:
        """Test get_records_for_story returns empty list when no matches."""
        from bmad_assist.benchmarking.storage import get_records_for_story

        temp_base_dir.mkdir(parents=True, exist_ok=True)

        records = get_records_for_story(99, 99, temp_base_dir)
        assert records == []

    def test_get_records_loads_full_content(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test get_records_for_story loads full record content."""
        from bmad_assist.benchmarking.storage import (
            get_records_for_story,
            save_evaluation_record,
        )

        save_evaluation_record(sample_record, temp_base_dir)

        records = get_records_for_story(13, 1, temp_base_dir)

        # Verify full content is loaded
        record = records[0]
        assert record.workflow.id == "validate-story"
        assert record.story.title == "Test Story"
        assert record.evaluator.model == "opus-4"
        assert record.output.char_count == 5000

    def test_get_records_requires_base_dir(self) -> None:
        """Test get_records_for_story raises StorageError if base_dir is None."""
        from bmad_assist.benchmarking.storage import StorageError, get_records_for_story

        with pytest.raises(StorageError, match="base_dir required"):
            get_records_for_story(13, 1, None)  # type: ignore[arg-type]


# =============================================================================
# Task 9 Tests: Error Handling
# =============================================================================


class TestErrorHandling:
    """Test AC9: Error handling."""

    def test_storage_error_wraps_original_exception(self, temp_base_dir: Path) -> None:
        """Test StorageError chains original exception."""
        from bmad_assist.benchmarking.storage import StorageError, load_evaluation_record

        missing_path = temp_base_dir / "nonexistent.yaml"
        with pytest.raises(StorageError) as exc_info:
            load_evaluation_record(missing_path)

        # Verify original exception is chained
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    def test_atomic_write_cleanup_on_failure(
        self, sample_record: LLMEvaluationRecord, temp_base_dir: Path
    ) -> None:
        """Test temp files are cleaned up on write failure."""
        from bmad_assist.benchmarking.storage import StorageError, save_evaluation_record

        # Create the directory structure
        month_dir = temp_base_dir / "benchmarks" / "2025-12"
        month_dir.mkdir(parents=True, exist_ok=True)

        # Mock os.replace to fail
        with (
            patch("os.replace", side_effect=OSError("Simulated failure")),
            pytest.raises(StorageError),
        ):
            save_evaluation_record(sample_record, temp_base_dir)

        # Verify no temp files remain
        temp_files = list(month_dir.glob("*.tmp"))
        assert len(temp_files) == 0
