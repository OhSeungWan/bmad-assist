"""Tests for Deep Verify validate_story integration hook.

Story 26.16: Validate Story Integration Hook
"""

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bmad_assist.deep_verify.config import DeepVerifyConfig
from bmad_assist.deep_verify.core.types import (
    ArtifactDomain,
    DeepVerifyValidationResult,
    DomainConfidence,
    Evidence,
    Finding,
    MethodId,
    Severity,
    Verdict,
    VerdictDecision,
    deserialize_validation_result,
    serialize_validation_result,
)
from bmad_assist.deep_verify.integration.validate_story_hook import (
    run_deep_verify_validation,
)
from bmad_assist.deep_verify.integration.reports import (
    _format_finding_detail,
    _format_findings_table,
    save_deep_verify_report,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Create a mock config with Deep Verify enabled."""
    config = MagicMock()
    config.deep_verify = DeepVerifyConfig(enabled=True)
    return config


@pytest.fixture
def mock_config_disabled():
    """Create a mock config with Deep Verify disabled."""
    config = MagicMock()
    config.deep_verify = DeepVerifyConfig(enabled=False)
    return config


@pytest.fixture
def mock_config_no_dv():
    """Create a mock config without Deep Verify field."""
    config = MagicMock()
    config.deep_verify = None
    return config


@pytest.fixture
def sample_finding():
    """Create a sample finding for testing."""
    return Finding(
        id="F1",
        severity=Severity.CRITICAL,
        title="SQL Injection Vulnerability",
        description="Unsanitized user input in SQL query",
        method_id=MethodId("#201"),
        pattern_id=None,
        domain=ArtifactDomain.SECURITY,
        evidence=[
            Evidence(
                quote="query = f'SELECT * FROM users WHERE id = {user_id}'",
                line_number=42,
                source="story.md",
                confidence=0.95,
            )
        ],
    )


@pytest.fixture
def sample_verdict(sample_finding):
    """Create a sample verdict for testing."""
    return Verdict(
        decision=VerdictDecision.REJECT,
        score=8.5,
        findings=[sample_finding],
        domains_detected=[
            DomainConfidence(
                domain=ArtifactDomain.SECURITY,
                confidence=0.95,
                signals=["auth", "token"],
            )
        ],
        methods_executed=[MethodId("#153"), MethodId("#201")],
        summary="REJECT verdict (score: 8.5). 1 findings: F1. Domains: security. Methods: #153, #201.",
    )


@pytest.fixture
def sample_dv_result(sample_finding):
    """Create a sample DeepVerifyValidationResult for testing."""
    return DeepVerifyValidationResult(
        findings=[sample_finding],
        domains_detected=[
            DomainConfidence(
                domain=ArtifactDomain.SECURITY,
                confidence=0.95,
                signals=["auth", "token"],
            )
        ],
        methods_executed=[MethodId("#153"), MethodId("#201")],
        verdict=VerdictDecision.REJECT,
        score=8.5,
        duration_ms=4500,
        error=None,
    )


@pytest.fixture
def temp_project_path(tmp_path):
    """Create a temporary project path."""
    return tmp_path


# =============================================================================
# run_deep_verify_validation Tests
# =============================================================================


class TestRunDeepVerifyValidation:
    """Tests for run_deep_verify_validation function."""

    @pytest.mark.asyncio
    async def test_success_case(self, mock_config, temp_project_path, sample_verdict):
        """Test successful DV validation execution."""
        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.verify = AsyncMock(return_value=sample_verdict)
            mock_engine_class.return_value = mock_engine

            result = await run_deep_verify_validation(
                artifact_text="test artifact content",
                config=mock_config,
                project_path=temp_project_path,
                epic_num=26,
                story_num=16,
                timeout=60,
            )

            assert isinstance(result, DeepVerifyValidationResult)
            assert result.verdict == VerdictDecision.REJECT
            assert result.score == 8.5
            assert len(result.findings) == 1
            assert result.findings[0].id == "F1"
            assert result.error is None

            mock_engine_class.assert_called_once()
            call_kwargs = mock_engine_class.call_args.kwargs
            assert call_kwargs["project_root"] == temp_project_path
            assert call_kwargs["config"] == mock_config.deep_verify
            assert "helper_provider_config" in call_kwargs
            mock_engine.verify.assert_called_once()

    @pytest.mark.asyncio
    async def test_disabled_in_config(self, mock_config_disabled, temp_project_path):
        """Test that DV is skipped when disabled in config."""
        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            result = await run_deep_verify_validation(
                artifact_text="test artifact content",
                config=mock_config_disabled,
                project_path=temp_project_path,
                epic_num=26,
                story_num=16,
            )

            assert isinstance(result, DeepVerifyValidationResult)
            assert result.verdict == VerdictDecision.ACCEPT
            assert result.score == 0.0
            assert len(result.findings) == 0
            assert result.error is None
            mock_engine_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_dv_config(self, mock_config_no_dv, temp_project_path):
        """Test behavior when deep_verify config is missing."""
        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            result = await run_deep_verify_validation(
                artifact_text="test artifact content",
                config=mock_config_no_dv,
                project_path=temp_project_path,
                epic_num=26,
                story_num=16,
            )

            assert isinstance(result, DeepVerifyValidationResult)
            assert result.verdict == VerdictDecision.ACCEPT
            assert result.score == 0.0
            assert len(result.findings) == 0
            assert result.error is None
            mock_engine_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_config, temp_project_path):
        """Test graceful error handling when engine fails."""
        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.verify = AsyncMock(side_effect=Exception("Engine failure"))
            mock_engine_class.return_value = mock_engine

            result = await run_deep_verify_validation(
                artifact_text="test artifact content",
                config=mock_config,
                project_path=temp_project_path,
                epic_num=26,
                story_num=16,
            )

            assert isinstance(result, DeepVerifyValidationResult)
            assert result.verdict == VerdictDecision.ACCEPT
            assert result.score == 0.0
            assert len(result.findings) == 0
            # Error format includes exception type: "Exception: Engine failure"
            assert "Engine failure" in result.error
            assert "Exception:" in result.error

    @pytest.mark.asyncio
    async def test_timeout_passed_to_engine(self, mock_config, temp_project_path, sample_verdict):
        """Test that timeout is passed to engine.verify()."""
        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.verify = AsyncMock(return_value=sample_verdict)
            mock_engine_class.return_value = mock_engine

            await run_deep_verify_validation(
                artifact_text="test artifact content",
                config=mock_config,
                project_path=temp_project_path,
                epic_num=26,
                story_num=16,
                timeout=120,
            )

            mock_engine.verify.assert_called_once()
            call_kwargs = mock_engine.verify.call_args[1]
            assert call_kwargs.get("timeout") == 120

    @pytest.mark.asyncio
    async def test_duration_tracking(self, mock_config, temp_project_path, sample_verdict):
        """Test that duration_ms is properly tracked (not hardcoded to 0)."""
        import asyncio

        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            mock_engine = MagicMock()
            # Add a small delay to simulate processing time
            async def delayed_verdict(*args, **kwargs):
                await asyncio.sleep(0.01)  # 10ms delay
                return sample_verdict

            mock_engine.verify = delayed_verdict
            mock_engine_class.return_value = mock_engine

            result = await run_deep_verify_validation(
                artifact_text="test artifact content",
                config=mock_config,
                project_path=temp_project_path,
                epic_num=26,
                story_num=16,
            )

            # Duration should be tracked (at least 10ms from the sleep)
            assert result.duration_ms >= 10, f"Expected duration >= 10ms, got {result.duration_ms}ms"

    @pytest.mark.asyncio
    async def test_error_handling_provider_error(self, mock_config, temp_project_path):
        """Test that ProviderError is caught and handled gracefully."""
        from bmad_assist.core.exceptions import ProviderError

        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.verify = AsyncMock(side_effect=ProviderError("Provider failed"))
            mock_engine_class.return_value = mock_engine

            result = await run_deep_verify_validation(
                artifact_text="test artifact content",
                config=mock_config,
                project_path=temp_project_path,
                epic_num=26,
                story_num=16,
            )

            assert isinstance(result, DeepVerifyValidationResult)
            assert result.verdict == VerdictDecision.ACCEPT
            assert result.error is not None
            assert "ProviderError" in result.error


# =============================================================================
# Cache Serialization Tests
# =============================================================================


class TestCacheSerialization:
    """Tests for DV result serialization/deserialization."""

    def test_serialize_validation_result(self, sample_dv_result):
        """Test serialization of DeepVerifyValidationResult."""
        data = serialize_validation_result(sample_dv_result)

        assert data["verdict"] == "REJECT"
        assert data["score"] == 8.5
        assert data["duration_ms"] == 4500
        assert len(data["findings"]) == 1
        assert data["findings"][0]["id"] == "F1"
        assert data["findings"][0]["severity"] == "critical"
        assert len(data["domains_detected"]) == 1
        assert data["domains_detected"][0]["domain"] == "security"
        assert data["methods_executed"] == ["#153", "#201"]

    def test_deserialize_validation_result(self, sample_dv_result):
        """Test deserialization of DeepVerifyValidationResult."""
        data = serialize_validation_result(sample_dv_result)
        result = deserialize_validation_result(data)

        assert isinstance(result, DeepVerifyValidationResult)
        assert result.verdict == VerdictDecision.REJECT
        assert result.score == 8.5
        assert result.duration_ms == 4500
        assert len(result.findings) == 1
        assert result.findings[0].id == "F1"
        assert result.findings[0].severity == Severity.CRITICAL

    def test_round_trip_serialization(self, sample_dv_result):
        """Test that serialization round-trip preserves data."""
        data = serialize_validation_result(sample_dv_result)
        result = deserialize_validation_result(data)

        assert result.verdict == sample_dv_result.verdict
        assert result.score == sample_dv_result.score
        assert result.duration_ms == sample_dv_result.duration_ms
        assert len(result.findings) == len(sample_dv_result.findings)
        assert len(result.domains_detected) == len(sample_dv_result.domains_detected)
        assert result.methods_executed == sample_dv_result.methods_executed

    def test_serialize_empty_result(self):
        """Test serialization of empty result."""
        empty_result = DeepVerifyValidationResult(
            findings=[],
            domains_detected=[],
            methods_executed=[],
            verdict=VerdictDecision.ACCEPT,
            score=0.0,
            duration_ms=0,
            error=None,
        )

        data = serialize_validation_result(empty_result)
        assert data["verdict"] == "ACCEPT"
        assert data["score"] == 0.0
        assert data["findings"] == []
        assert data["domains_detected"] == []
        assert data["methods_executed"] == []

    def test_deserialize_error_result(self):
        """Test deserialization of result with error."""
        data = {
            "findings": [],
            "domains_detected": [],
            "methods_executed": [],
            "verdict": "ACCEPT",
            "score": 0.0,
            "duration_ms": 0,
            "error": "Timeout occurred",
        }

        result = deserialize_validation_result(data)
        assert result.error == "Timeout occurred"
        assert result.verdict == VerdictDecision.ACCEPT


# =============================================================================
# Report Generation Tests
# =============================================================================


class TestReportGeneration:
    """Tests for DV report generation."""

    def test_format_findings_table(self, sample_finding):
        """Test formatting of findings table."""
        findings = [sample_finding]
        table = _format_findings_table(findings)

        assert "| ID | Severity | Title | Domain | Method |" in table
        assert "|---|---|---|---|---|" in table
        assert "F1" in table
        assert "CRITICAL" in table
        assert "SQL Injection Vulnerability" in table
        assert "security" in table
        assert "#201" in table

    def test_format_findings_table_empty(self):
        """Test formatting empty findings list."""
        table = _format_findings_table([])

        assert "No findings reported" in table

    def test_format_finding_detail(self, sample_finding):
        """Test formatting of finding detail."""
        detail = _format_finding_detail(sample_finding)

        assert "### F1: SQL Injection Vulnerability" in detail
        assert "**Severity:** CRITICAL" in detail
        assert "**Domain:** security" in detail
        assert "**Method:** #201" in detail
        assert "Unsanitized user input in SQL query" in detail
        assert "**Evidence:**" in detail
        assert "query = f'SELECT * FROM users WHERE id = {user_id}'" in detail
        assert "Line 42" in detail

    def test_save_deep_verify_report(self, temp_project_path, sample_dv_result):
        """Test saving DV report to file."""
        validations_dir = temp_project_path / "validations"
        validations_dir.mkdir(parents=True, exist_ok=True)

        report_path = save_deep_verify_report(
            result=sample_dv_result,
            epic=26,
            story=16,
            validations_dir=validations_dir,
        )

        assert report_path.exists()
        content = report_path.read_text()

        assert "# Deep Verify Report" in content
        assert "**Verdict:** REJECT" in content
        assert "**Score:** 8.5" in content
        assert "**Duration:** 4.5s" in content
        assert "**Epic:** 26" in content
        assert "**Story:** 16" in content
        assert "F1" in content
        assert "SQL Injection Vulnerability" in content

    def test_save_deep_verify_report_empty_result(self, temp_project_path):
        """Test saving empty DV report."""
        validations_dir = temp_project_path / "validations"
        validations_dir.mkdir(parents=True, exist_ok=True)

        empty_result = DeepVerifyValidationResult(
            findings=[],
            domains_detected=[],
            methods_executed=[],
            verdict=VerdictDecision.ACCEPT,
            score=0.0,
            duration_ms=1000,
            error=None,
        )

        report_path = save_deep_verify_report(
            result=empty_result,
            epic=26,
            story=16,
            validations_dir=validations_dir,
        )

        assert report_path.exists()
        content = report_path.read_text()

        assert "# Deep Verify Report" in content
        assert "**Verdict:** ACCEPT" in content
        assert "No findings reported" in content


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for DV validate_story hook."""

    @pytest.mark.asyncio
    async def test_end_to_end_with_mock_engine(self, mock_config, temp_project_path):
        """Test complete flow with mocked engine."""
        finding = Finding(
            id="F1",
            severity=Severity.ERROR,
            title="Test Issue",
            description="Test description",
            method_id=MethodId("#153"),
            domain=ArtifactDomain.API,
            evidence=[],
        )
        verdict = Verdict(
            decision=VerdictDecision.UNCERTAIN,
            score=3.0,
            findings=[finding],
            domains_detected=[DomainConfidence(domain=ArtifactDomain.API, confidence=0.8)],
            methods_executed=[MethodId("#153")],
            summary="UNCERTAIN verdict",
        )

        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.verify = AsyncMock(return_value=verdict)
            mock_engine_class.return_value = mock_engine

            result = await run_deep_verify_validation(
                artifact_text="API endpoint implementation",
                config=mock_config,
                project_path=temp_project_path,
                epic_num=26,
                story_num=16,
            )

            # Verify result can be serialized
            data = serialize_validation_result(result)
            assert data["verdict"] == "UNCERTAIN"

            # Verify result can be deserialized
            restored = deserialize_validation_result(data)
            assert restored.verdict == VerdictDecision.UNCERTAIN

    def test_blocker_detection_logic(self, sample_dv_result):
        """Test logic for detecting blockers from DV results."""
        # Test CRITICAL finding detection
        has_critical = any(
            f.severity == Severity.CRITICAL for f in sample_dv_result.findings
        )
        assert has_critical is True

        # Test verdict check
        is_reject = sample_dv_result.verdict == VerdictDecision.REJECT
        assert is_reject is True

        # Test with non-blocking result
        non_blocking_result = DeepVerifyValidationResult(
            findings=[],
            domains_detected=[],
            methods_executed=[],
            verdict=VerdictDecision.ACCEPT,
            score=-2.0,
            duration_ms=1000,
            error=None,
        )
        assert not any(f.severity == Severity.CRITICAL for f in non_blocking_result.findings)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Edge case tests for DV integration."""

    @pytest.mark.asyncio
    async def test_empty_artifact_text(self, mock_config, temp_project_path):
        """Test handling of empty artifact text."""
        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.verify = AsyncMock(
                return_value=Verdict(
                    decision=VerdictDecision.ACCEPT,
                    score=0.0,
                    findings=[],
                    domains_detected=[],
                    methods_executed=[],
                    summary="Empty artifact",
                )
            )
            mock_engine_class.return_value = mock_engine

            result = await run_deep_verify_validation(
                artifact_text="",
                config=mock_config,
                project_path=temp_project_path,
                epic_num=26,
                story_num=16,
            )

            assert result.verdict == VerdictDecision.ACCEPT
            assert len(result.findings) == 0

    @pytest.mark.asyncio
    async def test_string_epic_num(self, mock_config, temp_project_path, sample_verdict):
        """Test with string epic_num (module epic)."""
        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.verify = AsyncMock(return_value=sample_verdict)
            mock_engine_class.return_value = mock_engine

            result = await run_deep_verify_validation(
                artifact_text="test content",
                config=mock_config,
                project_path=temp_project_path,
                epic_num="testarch",
                story_num=1,
            )

            assert result is not None

    @pytest.mark.asyncio
    async def test_string_story_num(self, mock_config, temp_project_path, sample_verdict):
        """Test with string story_num."""
        with patch(
            "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
        ) as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.verify = AsyncMock(return_value=sample_verdict)
            mock_engine_class.return_value = mock_engine

            result = await run_deep_verify_validation(
                artifact_text="test content",
                config=mock_config,
                project_path=temp_project_path,
                epic_num=26,
                story_num="A",
            )

            assert result is not None

    def test_serialize_multiple_findings(self):
        """Test serialization with multiple findings."""
        findings = [
            Finding(
                id=f"F{i}",
                severity=Severity.ERROR,
                title=f"Issue {i}",
                description=f"Description {i}",
                method_id=MethodId("#153"),
                domain=ArtifactDomain.API,
                evidence=[],
            )
            for i in range(1, 4)
        ]

        result = DeepVerifyValidationResult(
            findings=findings,
            domains_detected=[DomainConfidence(domain=ArtifactDomain.API, confidence=0.8)],
            methods_executed=[MethodId("#153")],
            verdict=VerdictDecision.REJECT,
            score=6.0,
            duration_ms=5000,
        )

        data = serialize_validation_result(result)
        assert len(data["findings"]) == 3
        assert data["findings"][0]["id"] == "F1"
        assert data["findings"][1]["id"] == "F2"
        assert data["findings"][2]["id"] == "F3"


# =============================================================================
# Logging Tests
# =============================================================================


class TestLogging:
    """Tests for logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_execution(self, mock_config, temp_project_path, sample_verdict, caplog):
        """Test that execution is logged at INFO level."""
        import logging

        with caplog.at_level(logging.INFO):
            with patch(
                "bmad_assist.deep_verify.integration.validate_story_hook.DeepVerifyEngine"
            ) as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine.verify = AsyncMock(return_value=sample_verdict)
                mock_engine_class.return_value = mock_engine

                await run_deep_verify_validation(
                    artifact_text="test content",
                    config=mock_config,
                    project_path=temp_project_path,
                    epic_num=26,
                    story_num=16,
                )

        assert any("Deep Verify" in msg for msg in caplog.messages)
