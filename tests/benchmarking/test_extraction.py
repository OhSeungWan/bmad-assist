"""Tests for LLM-based metrics extraction module (Story 13.3).

Tests cover:
- ExtractionContext instantiation and defaults
- ExtractedMetrics dataclass and field mapping
- JSON parsing with valid and invalid responses
- Retry logic with mock provider
- Error handling and exception inheritance
- Schema model conversions
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bmad_assist.benchmarking.collector import LinguisticMetrics
from bmad_assist.benchmarking.extraction import (
    ExtractedMetrics,
    ExtractionContext,
    FindingsData,
    LinguisticData,
    MetricsExtractionError,
    QualityData,
    _parse_extraction_response,
    extract_metrics,
)
from bmad_assist.benchmarking.schema import (
    BenchmarkingError,
    FindingsExtracted,
    LinguisticFingerprint,
    QualitySignals,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_valid_json() -> str:
    """Sample valid JSON response from LLM."""
    return json.dumps(
        {
            "findings": {
                "total_count": 5,
                "by_severity": {"critical": 1, "major": 2, "minor": 1, "nit": 1},
                "by_category": {"security": 1, "performance": 2, "correctness": 2},
                "has_fix_count": 3,
                "has_location_count": 4,
                "has_evidence_count": 5,
            },
            "complexity_flags": {
                "has_ui_changes": False,
                "has_api_changes": True,
                "has_db_changes": False,
                "has_security_impact": True,
                "requires_migration": False,
            },
            "linguistic": {
                "formality_score": 0.85,
                "sentiment": "neutral",
            },
            "quality_signals": {
                "actionable_ratio": 0.8,
                "specificity_score": 0.75,
                "evidence_quality": 0.9,
                "internal_consistency": 0.95,
            },
            "anomalies": ["duplicate finding about API validation"],
        }
    )


@pytest.fixture
def sample_json_with_code_block(sample_valid_json: str) -> str:
    """Sample JSON wrapped in markdown code block."""
    return f"```json\n{sample_valid_json}\n```"


@pytest.fixture
def extraction_context(tmp_path: Path) -> ExtractionContext:
    """Create extraction context for testing."""
    # Create workflow directory structure
    workflow_dir = tmp_path / "_bmad/bmm/workflows/metrics-extraction"
    workflow_dir.mkdir(parents=True)

    # Create minimal instructions.xml (must include validator_output placeholder)
    instructions = """<workflow>
  <mission>Extract metrics</mission>
  <context>
    <input name="validator_output">{{validator_output}}</input>
  </context>
  <instructions>
    <step n="1" goal="Analyze">
      <action>Count findings</action>
    </step>
  </instructions>
  <output format="json">
    <critical>Output only JSON</critical>
  </output>
</workflow>"""
    (workflow_dir / "instructions.xml").write_text(instructions)

    # Create workflow.yaml with required fields for compiler
    workflow_yaml = """name: metrics-extraction
description: "Extract LLM-assessed metrics from validator output"
installed_path: "{project-root}/_bmad/bmm/workflows/metrics-extraction"
instructions: "{installed_path}/instructions.xml"
template: false
variables:
  validator_output: ""
  story_epic: 0
  story_num: 0
standalone: true
"""
    (workflow_dir / "workflow.yaml").write_text(workflow_yaml)

    # Create docs directory (required by compiler)
    (tmp_path / "docs").mkdir(exist_ok=True)

    return ExtractionContext(
        story_epic=13,
        story_num=3,
        timestamp=datetime.now(UTC),
        project_root=tmp_path,
        max_retries=3,
        timeout_seconds=60,
        provider="claude",
        model="haiku",
    )


@pytest.fixture
def sample_extracted_metrics() -> ExtractedMetrics:
    """Sample ExtractedMetrics for testing conversions."""
    return ExtractedMetrics(
        findings=FindingsData(
            total_count=5,
            by_severity={"critical": 1, "major": 2, "minor": 1, "nit": 1},
            by_category={"security": 1, "performance": 2, "correctness": 2},
            has_fix_count=3,
            has_location_count=4,
            has_evidence_count=5,
        ),
        complexity_flags={
            "has_ui_changes": False,
            "has_api_changes": True,
            "has_db_changes": False,
            "has_security_impact": True,
            "requires_migration": False,
        },
        linguistic=LinguisticData(formality_score=0.85, sentiment="neutral"),
        quality=QualityData(
            actionable_ratio=0.8,
            specificity_score=0.75,
            evidence_quality=0.9,
            internal_consistency=0.95,
        ),
        anomalies=("duplicate finding about API validation",),
        extracted_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_linguistic_metrics() -> LinguisticMetrics:
    """Sample deterministic linguistic metrics for merging."""
    return LinguisticMetrics(
        avg_sentence_length=15.5,
        vocabulary_richness=0.45,
        flesch_reading_ease=55.0,
        vague_terms_count=2,
    )


# =============================================================================
# ExtractionContext Tests
# =============================================================================


class TestExtractionContext:
    """Tests for ExtractionContext dataclass."""

    def test_required_fields(self, tmp_path: Path) -> None:
        """Test required fields are enforced."""
        ctx = ExtractionContext(
            story_epic=13,
            story_num=3,
            timestamp=datetime.now(UTC),
            project_root=tmp_path,
        )
        assert ctx.story_epic == 13
        assert ctx.story_num == 3
        assert ctx.project_root == tmp_path

    def test_default_values(self, tmp_path: Path) -> None:
        """Test default values are set correctly."""
        ctx = ExtractionContext(
            story_epic=1,
            story_num=1,
            timestamp=datetime.now(UTC),
            project_root=tmp_path,
        )
        assert ctx.max_retries == 3
        assert ctx.timeout_seconds == 120
        assert ctx.provider == "claude"
        assert ctx.model == "haiku"

    def test_custom_values(self, tmp_path: Path) -> None:
        """Test custom values override defaults."""
        ctx = ExtractionContext(
            story_epic=1,
            story_num=1,
            timestamp=datetime.now(UTC),
            project_root=tmp_path,
            max_retries=5,
            timeout_seconds=180,
            provider="gemini",
            model="flash",
        )
        assert ctx.max_retries == 5
        assert ctx.timeout_seconds == 180
        assert ctx.provider == "gemini"
        assert ctx.model == "flash"

    def test_frozen(self, tmp_path: Path) -> None:
        """Test dataclass is frozen (immutable)."""
        ctx = ExtractionContext(
            story_epic=1,
            story_num=1,
            timestamp=datetime.now(UTC),
            project_root=tmp_path,
        )
        with pytest.raises(AttributeError):
            ctx.story_epic = 2  # type: ignore[misc]


# =============================================================================
# ExtractedMetrics Tests
# =============================================================================


class TestExtractedMetrics:
    """Tests for ExtractedMetrics dataclass."""

    def test_structure(self, sample_extracted_metrics: ExtractedMetrics) -> None:
        """Test ExtractedMetrics structure."""
        assert sample_extracted_metrics.findings.total_count == 5
        assert sample_extracted_metrics.linguistic.sentiment == "neutral"
        assert sample_extracted_metrics.quality.actionable_ratio == 0.8
        assert len(sample_extracted_metrics.anomalies) == 1

    def test_frozen(self, sample_extracted_metrics: ExtractedMetrics) -> None:
        """Test dataclass is frozen (immutable)."""
        with pytest.raises(AttributeError):
            sample_extracted_metrics.findings = None  # type: ignore[misc]


# =============================================================================
# JSON Parsing Tests
# =============================================================================


class TestParseExtractionResponse:
    """Tests for _parse_extraction_response function."""

    def test_valid_json(self, sample_valid_json: str) -> None:
        """Test parsing valid JSON response."""
        result = _parse_extraction_response(sample_valid_json, datetime.now(UTC))
        assert result.findings.total_count == 5
        assert result.findings.by_severity["critical"] == 1
        assert result.findings.by_category["security"] == 1
        assert result.linguistic.formality_score == 0.85
        assert result.linguistic.sentiment == "neutral"
        assert result.quality.actionable_ratio == 0.8
        assert result.complexity_flags["has_api_changes"] is True
        assert len(result.anomalies) == 1

    def test_json_with_code_block(self, sample_json_with_code_block: str) -> None:
        """Test parsing JSON wrapped in markdown code block."""
        result = _parse_extraction_response(sample_json_with_code_block, datetime.now(UTC))
        assert result.findings.total_count == 5

    def test_json_with_whitespace(self, sample_valid_json: str) -> None:
        """Test parsing JSON with leading/trailing whitespace."""
        result = _parse_extraction_response(f"\n  {sample_valid_json}  \n", datetime.now(UTC))
        assert result.findings.total_count == 5

    def test_invalid_json_syntax(self) -> None:
        """Test error on invalid JSON syntax."""
        with pytest.raises(json.JSONDecodeError):
            _parse_extraction_response("{invalid json}", datetime.now(UTC))

    def test_missing_findings(self) -> None:
        """Test error on missing findings section."""
        data = {"complexity_flags": {}, "linguistic": {}, "quality_signals": {}}
        with pytest.raises(KeyError):
            _parse_extraction_response(json.dumps(data), datetime.now(UTC))

    def test_missing_linguistic(self) -> None:
        """Test error on missing linguistic section."""
        data = {
            "findings": {
                "total_count": 0,
                "by_severity": {},
                "by_category": {},
                "has_fix_count": 0,
                "has_location_count": 0,
                "has_evidence_count": 0,
            },
            "complexity_flags": {},
            "quality_signals": {},
        }
        with pytest.raises(KeyError):
            _parse_extraction_response(json.dumps(data), datetime.now(UTC))

    def test_formality_out_of_range_high(self) -> None:
        """Test error when formality_score > 1.0."""
        data = _make_valid_response()
        data["linguistic"]["formality_score"] = 1.5
        with pytest.raises(ValueError, match="formality_score must be 0.0-1.0"):
            _parse_extraction_response(json.dumps(data), datetime.now(UTC))

    def test_formality_out_of_range_low(self) -> None:
        """Test error when formality_score < 0.0."""
        data = _make_valid_response()
        data["linguistic"]["formality_score"] = -0.1
        with pytest.raises(ValueError, match="formality_score must be 0.0-1.0"):
            _parse_extraction_response(json.dumps(data), datetime.now(UTC))

    def test_invalid_sentiment(self) -> None:
        """Test error on invalid sentiment value."""
        data = _make_valid_response()
        data["linguistic"]["sentiment"] = "happy"
        with pytest.raises(ValueError, match="sentiment must be one of"):
            _parse_extraction_response(json.dumps(data), datetime.now(UTC))

    def test_quality_scores_out_of_range(self) -> None:
        """Test error when quality score > 1.0."""
        data = _make_valid_response()
        data["quality_signals"]["actionable_ratio"] = 1.5
        with pytest.raises(ValueError, match="actionable_ratio must be 0.0-1.0"):
            _parse_extraction_response(json.dumps(data), datetime.now(UTC))

    def test_empty_anomalies(self) -> None:
        """Test parsing with empty anomalies list."""
        data = _make_valid_response()
        data["anomalies"] = []
        result = _parse_extraction_response(json.dumps(data), datetime.now(UTC))
        assert result.anomalies == ()

    def test_missing_anomalies_defaults_empty(self) -> None:
        """Test that missing anomalies defaults to empty tuple."""
        data = _make_valid_response()
        del data["anomalies"]
        result = _parse_extraction_response(json.dumps(data), datetime.now(UTC))
        assert result.anomalies == ()

    def test_unmapped_fields_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that unmapped fields are logged as warning."""
        data = _make_valid_response()
        data["extra_field"] = "unexpected"
        with caplog.at_level("WARNING"):
            _parse_extraction_response(json.dumps(data), datetime.now(UTC))
        assert "Unmapped fields" in caplog.text
        assert "extra_field" in caplog.text

    def test_unknown_severity_keys_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that unknown severity keys are logged as warning per AC3."""
        data = _make_valid_response()
        data["findings"]["by_severity"]["unknown_severity"] = 1
        with caplog.at_level("WARNING"):
            result = _parse_extraction_response(json.dumps(data), datetime.now(UTC))
        assert "Unknown severity keys" in caplog.text
        assert "unknown_severity" in caplog.text
        # Data still parsed (not rejected)
        assert result.findings.by_severity["unknown_severity"] == 1

    def test_unknown_category_keys_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that unknown category keys are logged as warning per AC3."""
        data = _make_valid_response()
        data["findings"]["by_category"]["foo"] = 2
        with caplog.at_level("WARNING"):
            result = _parse_extraction_response(json.dumps(data), datetime.now(UTC))
        assert "Unknown category keys" in caplog.text
        assert "foo" in caplog.text
        # Data still parsed (not rejected)
        assert result.findings.by_category["foo"] == 2


# =============================================================================
# Schema Conversion Tests
# =============================================================================


class TestToFindingsExtracted:
    """Tests for ExtractedMetrics.to_findings_extracted()."""

    def test_mapping(self, sample_extracted_metrics: ExtractedMetrics) -> None:
        """Test mapping to FindingsExtracted schema model."""
        result = sample_extracted_metrics.to_findings_extracted()
        assert isinstance(result, FindingsExtracted)
        assert result.total_count == 5
        assert result.by_severity["critical"] == 1
        assert result.by_category["security"] == 1
        assert result.has_fix_count == 3
        assert result.has_location_count == 4
        assert result.has_evidence_count == 5


class TestToLinguisticFingerprint:
    """Tests for ExtractedMetrics.to_linguistic_fingerprint()."""

    def test_merge_with_deterministic(
        self,
        sample_extracted_metrics: ExtractedMetrics,
        sample_linguistic_metrics: LinguisticMetrics,
    ) -> None:
        """Test merging LLM-assessed values with deterministic values."""
        result = sample_extracted_metrics.to_linguistic_fingerprint(sample_linguistic_metrics)

        assert isinstance(result, LinguisticFingerprint)

        # Deterministic values from collector
        assert result.avg_sentence_length == 15.5
        assert result.vocabulary_richness == 0.45
        assert result.flesch_reading_ease == 55.0
        assert result.vague_terms_count == 2

        # LLM-assessed values from extraction
        assert result.formality_score == 0.85
        assert result.sentiment == "neutral"


class TestToQualitySignals:
    """Tests for ExtractedMetrics.to_quality_signals()."""

    def test_mapping(self, sample_extracted_metrics: ExtractedMetrics) -> None:
        """Test mapping to QualitySignals schema model."""
        result = sample_extracted_metrics.to_quality_signals()
        assert isinstance(result, QualitySignals)
        assert result.actionable_ratio == 0.8
        assert result.specificity_score == 0.75
        assert result.evidence_quality == 0.9
        assert result.internal_consistency == 0.95
        assert result.follows_template is True  # Default value


class TestToComplexityFlags:
    """Tests for ExtractedMetrics.to_complexity_flags()."""

    def test_mapping(self, sample_extracted_metrics: ExtractedMetrics) -> None:
        """Test mapping returns dict copy."""
        result = sample_extracted_metrics.to_complexity_flags()
        assert isinstance(result, dict)
        assert result["has_api_changes"] is True
        assert result["has_ui_changes"] is False

        # Verify it's a copy, not the original
        result["has_api_changes"] = False
        assert sample_extracted_metrics.complexity_flags["has_api_changes"] is True


# =============================================================================
# MetricsExtractionError Tests
# =============================================================================


class TestMetricsExtractionError:
    """Tests for MetricsExtractionError exception."""

    def test_inheritance(self) -> None:
        """Test exception inherits from BenchmarkingError."""
        error = MetricsExtractionError("test error")
        assert isinstance(error, BenchmarkingError)

    def test_attributes(self) -> None:
        """Test exception attributes."""
        error = MetricsExtractionError(
            "Extraction failed",
            attempts=3,
            last_error="Invalid JSON",
        )
        assert str(error) == "Extraction failed"
        assert error.attempts == 3
        assert error.last_error == "Invalid JSON"

    def test_default_attributes(self) -> None:
        """Test exception default attributes."""
        error = MetricsExtractionError("test")
        assert error.attempts == 0
        assert error.last_error is None


# =============================================================================
# Extraction Tests (using sync wrapper for simpler testing)
# =============================================================================


class TestExtractMetrics:
    """Tests for extract_metrics function (sync wrapper)."""

    def test_success(
        self,
        extraction_context: ExtractionContext,
        sample_valid_json: str,
    ) -> None:
        """Test successful extraction with mock provider."""
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_result.stdout = sample_valid_json
        mock_result.stderr = ""

        mock_provider = MagicMock()
        mock_provider.invoke.return_value = mock_result

        with patch("bmad_assist.providers.get_provider", return_value=mock_provider):
            result = extract_metrics("validator output", extraction_context)

        assert result.findings.total_count == 5
        mock_provider.invoke.assert_called_once()
        call_kwargs = mock_provider.invoke.call_args.kwargs
        assert call_kwargs["allowed_tools"] == []

    def test_retry_on_invalid_json(
        self,
        extraction_context: ExtractionContext,
        sample_valid_json: str,
    ) -> None:
        """Test retry logic when LLM returns invalid JSON first."""
        mock_result_bad = MagicMock()
        mock_result_bad.exit_code = 0
        mock_result_bad.stdout = "{invalid json}"
        mock_result_bad.stderr = ""

        mock_result_good = MagicMock()
        mock_result_good.exit_code = 0
        mock_result_good.stdout = sample_valid_json
        mock_result_good.stderr = ""

        mock_provider = MagicMock()
        mock_provider.invoke.side_effect = [mock_result_bad, mock_result_good]

        with patch("bmad_assist.providers.get_provider", return_value=mock_provider):
            result = extract_metrics("validator output", extraction_context)

        assert result.findings.total_count == 5
        assert mock_provider.invoke.call_count == 2

    def test_max_retries_exceeded(
        self,
        extraction_context: ExtractionContext,
    ) -> None:
        """Test error after max retries exceeded."""
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_result.stdout = "{invalid json}"
        mock_result.stderr = ""

        mock_provider = MagicMock()
        mock_provider.invoke.return_value = mock_result

        with (
            patch("bmad_assist.providers.get_provider", return_value=mock_provider),
            pytest.raises(MetricsExtractionError) as exc_info,
        ):
            extract_metrics("validator output", extraction_context)

        assert exc_info.value.attempts == 3
        assert "Invalid JSON" in str(exc_info.value.last_error)

    def test_provider_error_retry(
        self,
        extraction_context: ExtractionContext,
        sample_valid_json: str,
    ) -> None:
        """Test retry on provider error (non-zero exit code)."""
        mock_result_bad = MagicMock()
        mock_result_bad.exit_code = 1
        mock_result_bad.stdout = ""
        mock_result_bad.stderr = "Provider error"

        mock_result_good = MagicMock()
        mock_result_good.exit_code = 0
        mock_result_good.stdout = sample_valid_json
        mock_result_good.stderr = ""

        mock_provider = MagicMock()
        mock_provider.invoke.side_effect = [mock_result_bad, mock_result_good]

        with patch("bmad_assist.providers.get_provider", return_value=mock_provider):
            result = extract_metrics("validator output", extraction_context)

        assert result.findings.total_count == 5

    def test_allowed_tools_empty(
        self,
        extraction_context: ExtractionContext,
        sample_valid_json: str,
    ) -> None:
        """Test provider is called with allowed_tools=[] (read-only)."""
        mock_result = MagicMock()
        mock_result.exit_code = 0
        mock_result.stdout = sample_valid_json
        mock_result.stderr = ""

        mock_provider = MagicMock()
        mock_provider.invoke.return_value = mock_result

        with patch("bmad_assist.providers.get_provider", return_value=mock_provider):
            extract_metrics("validator output", extraction_context)

        call_kwargs = mock_provider.invoke.call_args.kwargs
        assert call_kwargs["allowed_tools"] == []

    # Note: test_missing_workflow_raises_error removed - no longer applicable
    # The extraction prompt is now embedded in the module, not loaded from
    # external BMAD workflow files. This makes extraction BMAD-agnostic.


# =============================================================================
# Helper Functions
# =============================================================================


def _make_valid_response() -> dict[str, Any]:
    """Create a valid response dictionary for modification in tests."""
    return {
        "findings": {
            "total_count": 0,
            "by_severity": {"critical": 0, "major": 0, "minor": 0, "nit": 0},
            "by_category": {},
            "has_fix_count": 0,
            "has_location_count": 0,
            "has_evidence_count": 0,
        },
        "complexity_flags": {
            "has_ui_changes": False,
            "has_api_changes": False,
            "has_db_changes": False,
            "has_security_impact": False,
            "requires_migration": False,
        },
        "linguistic": {
            "formality_score": 0.5,
            "sentiment": "neutral",
        },
        "quality_signals": {
            "actionable_ratio": 0.5,
            "specificity_score": 0.5,
            "evidence_quality": 0.5,
            "internal_consistency": 0.5,
        },
        "anomalies": [],
    }
