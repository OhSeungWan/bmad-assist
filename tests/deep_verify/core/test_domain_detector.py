"""Unit tests for DomainDetector.

This module provides comprehensive test coverage for the DomainDetector class,
including LLM mocking, caching behavior, JSON parsing, and fallback detection.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bmad_assist.core.exceptions import ProviderError, ProviderTimeoutError
from bmad_assist.deep_verify.core.domain_detector import (
    DOMAIN_KEYWORDS,
    DomainDetectionItem,
    DomainDetectionResponse,
    DomainDetector,
    _extract_json,
    deserialize_domain_detection_result,
    detect_domains,
    serialize_domain_detection_result,
)
from bmad_assist.deep_verify.core.types import (
    ArtifactDomain,
    DomainConfidence,
    DomainDetectionResult,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_provider():
    """Create a mocked ClaudeSDKProvider."""
    provider = Mock()
    provider.invoke.return_value = Mock(
        stdout="",
        stderr="",
        exit_code=0,
        duration_ms=100,
        model="haiku",
        command=["sdk", "query", "haiku"],
    )
    provider.parse_output.return_value = """```json
{
    "domains": [
        {"name": "security", "confidence": 0.9, "signals": ["auth", "token"]}
    ],
    "reasoning": "Contains authentication logic",
    "ambiguity": "none"
}
```"""
    return provider


@pytest.fixture
def temp_project_root(tmp_path):
    """Create temporary project root for cache testing."""
    return tmp_path


@pytest.fixture
def detector(mock_provider, temp_project_root):
    """Create DomainDetector with mocked provider."""
    detector = DomainDetector(
        project_root=temp_project_root,
        model="haiku",
        timeout=30,
        cache_enabled=True,
    )
    detector._provider = mock_provider
    return detector


@pytest.fixture
def detector_no_cache(mock_provider, temp_project_root):
    """Create DomainDetector with caching disabled."""
    detector = DomainDetector(
        project_root=temp_project_root,
        model="haiku",
        cache_enabled=False,
    )
    detector._provider = mock_provider
    return detector


# =============================================================================
# Basic Initialization Tests
# =============================================================================


class TestDomainDetectorInitialization:
    """Tests for DomainDetector initialization."""

    def test_init_default_values(self, temp_project_root):
        """Test initialization with default values."""
        # Patch the provider at the module level where it's imported
        with patch("bmad_assist.providers.ClaudeSDKProvider") as MockProv:
            MockProv.return_value = Mock()
            detector = DomainDetector(project_root=temp_project_root)

            assert detector.project_root == temp_project_root
            assert detector.model == "haiku"
            assert detector.timeout == 30
            assert detector.cache_enabled is True
            assert detector._cache_dir.exists()

    def test_init_custom_values(self, temp_project_root):
        """Test initialization with custom values."""
        with patch("bmad_assist.providers.ClaudeSDKProvider") as MockProv:
            MockProv.return_value = Mock()
            detector = DomainDetector(
                project_root=temp_project_root,
                model="opus",
                timeout=60,
                cache_enabled=False,
            )

            assert detector.model == "opus"
            assert detector.timeout == 60
            assert detector.cache_enabled is False

    def test_repr(self, temp_project_root):
        """Test __repr__ method masks sensitive info."""
        with patch("bmad_assist.providers.ClaudeSDKProvider") as MockProv:
            MockProv.return_value = Mock()
            detector = DomainDetector(project_root=temp_project_root)
            repr_str = repr(detector)
            assert "DomainDetector" in repr_str
            assert "haiku" in repr_str
            assert "***" in repr_str  # project_root masked
            assert "enabled" in repr_str


# =============================================================================
# LLM Detection Tests
# =============================================================================


class TestDomainDetectorLLMDetection:
    """Tests for LLM-based domain detection."""

    def test_detect_security_domain(self, detector, mock_provider):
        """Should detect SECURITY domain from artifact."""
        result = detector.detect("Function to verify JWT tokens and check permissions")

        assert len(result.domains) == 1
        assert result.domains[0].domain == ArtifactDomain.SECURITY
        assert result.domains[0].confidence == 0.9
        assert "auth" in result.domains[0].signals
        assert result.ambiguity == "none"
        assert "authentication" in result.reasoning.lower()

    def test_detect_multiple_domains(self, detector, mock_provider):
        """Should detect multiple domains from artifact."""
        mock_provider.parse_output.return_value = """```json
{
    "domains": [
        {"name": "security", "confidence": 0.85, "signals": ["auth"]},
        {"name": "api", "confidence": 0.75, "signals": ["endpoint", "http"]}
    ],
    "reasoning": "Has auth and HTTP endpoints",
    "ambiguity": "low"
}
```"""

        result = detector.detect("API with JWT authentication")

        assert len(result.domains) == 2
        domains = [d.domain for d in result.domains]
        assert ArtifactDomain.SECURITY in domains
        assert ArtifactDomain.API in domains

    def test_detect_all_domains(self, detector, mock_provider):
        """Should handle up to four domains per spec."""
        mock_provider.parse_output.return_value = """```json
{
    "domains": [
        {"name": "security", "confidence": 0.8, "signals": ["auth"]},
        {"name": "storage", "confidence": 0.7, "signals": ["database"]},
        {"name": "transform", "confidence": 0.6, "signals": ["parse"]},
        {"name": "concurrency", "confidence": 0.5, "signals": ["async"]}
    ],
    "reasoning": "Complex artifact with multiple domains",
    "ambiguity": "medium"
}
```"""

        result = detector.detect("Complex system with multiple domains")

        assert len(result.domains) == 4
        domains = {d.domain for d in result.domains}
        assert ArtifactDomain.SECURITY in domains
        assert ArtifactDomain.STORAGE in domains
        assert ArtifactDomain.TRANSFORM in domains
        assert ArtifactDomain.CONCURRENCY in domains

    def test_truncate_long_input(self, detector, mock_provider):
        """Should truncate input longer than 2000 characters."""
        long_text = "x" * 5000

        detector.detect(long_text)

        # Check that invoke was called with truncated prompt
        call_args = mock_provider.invoke.call_args
        prompt = call_args[1]["prompt"]
        # The prompt should contain truncated text (2000 chars + prompt header)
        assert len(prompt) < 4500  # Significantly less than 5000 + system prompt

    def test_empty_input(self, detector):
        """Should handle empty input gracefully."""
        result = detector.detect("")

        assert len(result.domains) == 0
        assert result.ambiguity == "high"
        assert "empty" in result.reasoning.lower()

    def test_whitespace_only_input(self, detector):
        """Should handle whitespace-only input gracefully."""
        result = detector.detect("   \n\t  ")

        assert len(result.domains) == 0
        assert result.ambiguity == "high"


# =============================================================================
# JSON Parsing Tests
# =============================================================================


class TestJSONParsing:
    """Tests for JSON response parsing."""

    def test_extract_from_markdown_code_block(self, detector, mock_provider):
        """Should extract JSON from markdown code blocks."""
        mock_provider.parse_output.return_value = """Some text before
```json
{
    "domains": [{"name": "security", "confidence": 0.9, "signals": []}],
    "reasoning": "Test reasoning provided",
    "ambiguity": "none"
}
```
Some text after"""

        result = detector.detect("test")

        assert len(result.domains) == 1
        assert result.domains[0].domain == ArtifactDomain.SECURITY

    def test_extract_from_plain_json(self, detector, mock_provider):
        """Should extract plain JSON without markdown."""
        mock_provider.parse_output.return_value = """{
    "domains": [{"name": "api", "confidence": 0.8, "signals": ["http"]}],
    "reasoning": "Has HTTP endpoints",
    "ambiguity": "low"
}"""

        result = detector.detect("test")

        assert len(result.domains) == 1
        assert result.domains[0].domain == ArtifactDomain.API

    def test_extract_json_direct(self):
        """Test _extract_json helper directly."""
        # With markdown
        md_text = "```json\n{\"key\": \"value\"}\n```"
        assert _extract_json(md_text) == '{"key": "value"}'

        # Without markdown
        plain = '{"key": "value"}'
        assert _extract_json(plain) == '{"key": "value"}'

        # With extra text
        mixed = "text {\"key\": \"value\"} more"
        assert _extract_json(mixed) == '{"key": "value"}'

    def test_invalid_json_fallback(self, detector, mock_provider):
        """Should use fallback when LLM returns invalid JSON."""
        mock_provider.parse_output.return_value = "not valid json"

        result = detector.detect("verify JWT tokens with auth")

        # Should fall back to keyword detection
        assert len(result.domains) >= 1
        assert result.ambiguity == "high"  # Fallback indicator

    def test_unknown_domain_ignored(self, detector, mock_provider):
        """Should ignore unknown domains from LLM."""
        mock_provider.parse_output.return_value = """{
    "domains": [
        {"name": "security", "confidence": 0.9, "signals": []},
        {"name": "unknown_domain", "confidence": 0.5, "signals": []}
    ],
    "reasoning": "Test reasoning provided",
    "ambiguity": "none"
}"""

        result = detector.detect("test")

        # Should only have security, not unknown_domain
        assert len(result.domains) == 1
        assert result.domains[0].domain == ArtifactDomain.SECURITY


# =============================================================================
# Pydantic Response Model Tests
# =============================================================================


class TestPydanticModels:
    """Tests for Pydantic validation models."""

    def test_domain_detection_item_validation(self):
        """Test DomainDetectionItem validation."""
        item = DomainDetectionItem(
            name="SECURITY",
            confidence=0.8,
            signals=["auth", "token"],
        )
        assert item.name == "security"  # Normalized to lowercase
        assert item.confidence == 0.8

    def test_domain_detection_item_invalid_confidence(self):
        """Test confidence bounds validation."""
        with pytest.raises(Exception):  # pydantic.ValidationError
            DomainDetectionItem(name="security", confidence=1.5, signals=[])

    def test_domain_detection_response_filter_low_confidence(self):
        """Test filtering of low confidence domains."""
        response = DomainDetectionResponse(
            domains=[
                DomainDetectionItem(name="security", confidence=0.9, signals=[]),
                DomainDetectionItem(name="api", confidence=0.2, signals=[]),  # Below 0.3
                DomainDetectionItem(name="storage", confidence=0.35, signals=[]),
            ],
            reasoning="Test reasoning provided",
        )
        # Should filter out api (confidence 0.2 < 0.3)
        assert len(response.domains) == 2

    def test_domain_detection_response_invalid_ambiguity(self):
        """Test ambiguity validation defaults to none."""
        response = DomainDetectionResponse(
            domains=[DomainDetectionItem(name="security", confidence=0.9, signals=[])],
            reasoning="Test reasoning provided",
            ambiguity="invalid_value",
        )
        assert response.ambiguity == "none"


# =============================================================================
# Caching Tests
# =============================================================================


class TestCaching:
    """Tests for caching behavior."""

    def test_cache_hit(self, detector, mock_provider, temp_project_root):
        """Should return cached result on cache hit."""
        text = "verify JWT tokens"

        # First call - hits LLM
        result1 = detector.detect(text)
        assert mock_provider.invoke.call_count == 1

        # Second call - should hit cache
        result2 = detector.detect(text)
        # Invoke should not be called again
        assert mock_provider.invoke.call_count == 1

        # Results should be identical
        assert len(result1.domains) == len(result2.domains)
        assert result1.domains[0].domain == result2.domains[0].domain

    def test_cache_disabled(self, detector_no_cache, mock_provider):
        """Should not cache when cache_enabled=False."""
        text = "verify JWT tokens"

        # First call
        detector_no_cache.detect(text)
        assert mock_provider.invoke.call_count == 1

        # Second call - should still hit LLM
        detector_no_cache.detect(text)
        assert mock_provider.invoke.call_count == 2

    def test_cache_ttl_expiry(self, detector, mock_provider, temp_project_root):
        """Should expire cached results after TTL."""
        text = "verify JWT tokens"

        # Create an expired cache entry
        cache_key = detector._get_cache_key(text[:2000])
        cache_path = detector._cache_dir / f"{cache_key}.json"

        # Write old cache entry (25 hours ago)
        old_time = datetime.now(UTC) - timedelta(hours=25)
        cache_data = {
            "timestamp": old_time.isoformat(),
            "model": "haiku",
            "result": {
                "domains": [
                    {"domain": "storage", "confidence": 0.5, "signals": []}
                ],
                "reasoning": "Old cached result",
                "ambiguity": "none",
            },
        }
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache_data))

        # Should ignore expired cache and call LLM
        result = detector.detect(text)
        assert mock_provider.invoke.call_count == 1
        # Should get security, not storage
        assert result.domains[0].domain == ArtifactDomain.SECURITY

    def test_cache_different_models(self, mock_provider, temp_project_root):
        """Should have separate cache entries for different models."""
        text = "verify JWT tokens"

        # Create detector with mocked provider
        detector1 = DomainDetector(
            project_root=temp_project_root,
            model="haiku",
            cache_enabled=True,
        )
        detector1._provider = mock_provider

        # Detect with default model
        detector1.detect(text)
        assert mock_provider.invoke.call_count == 1

        # Create new detector with different model
        mock_provider2 = Mock()
        mock_provider2.invoke.return_value = Mock(
            stdout="", stderr="", exit_code=0, duration_ms=100, model="opus", command=[]
        )
        mock_provider2.parse_output.return_value = """{"domains": [{"name": "api", "confidence": 0.7, "signals": []}], "reasoning": "API endpoint detected in artifact", "ambiguity": "none"}"""

        detector2 = DomainDetector(
            project_root=temp_project_root,
            model="opus",
            cache_enabled=True,
        )
        detector2._provider = mock_provider2

        # Should not hit cache (different model)
        detector2.detect(text)
        assert mock_provider2.invoke.call_count == 1

    def test_cache_corrupted_file(self, detector, mock_provider, temp_project_root):
        """Should handle corrupted cache files gracefully."""
        text = "verify JWT tokens"

        # Create corrupted cache entry
        cache_key = detector._get_cache_key(text[:2000])
        cache_path = detector._cache_dir / f"{cache_key}.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("not valid json")

        # Should handle gracefully and call LLM
        result = detector.detect(text)
        assert mock_provider.invoke.call_count == 1
        assert len(result.domains) == 1


# =============================================================================
# Fallback Tests
# =============================================================================


class TestFallbackDetection:
    """Tests for keyword-based fallback detection."""

    def test_fallback_security_keywords(self, detector, mock_provider):
        """Should detect SECURITY via fallback keywords."""
        mock_provider.invoke.side_effect = ProviderTimeoutError("timeout")

        result = detector.detect("JWT token authentication with HMAC signature")

        assert result.ambiguity == "high"  # Fallback indicator
        assert len(result.domains) >= 1
        domains = [d.domain for d in result.domains]
        assert ArtifactDomain.SECURITY in domains

    def test_fallback_storage_keywords(self, detector, mock_provider):
        """Should detect STORAGE via fallback keywords."""
        mock_provider.invoke.side_effect = ProviderError("api error")

        result = detector.detect("SQL database query with transaction")

        assert result.ambiguity == "high"
        domains = [d.domain for d in result.domains]
        assert ArtifactDomain.STORAGE in domains

    def test_fallback_concurrency_keywords(self, detector, mock_provider):
        """Should detect CONCURRENCY via fallback keywords."""
        mock_provider.invoke.side_effect = ProviderTimeoutError("timeout")

        result = detector.detect("goroutine async worker pool with mutex")

        domains = [d.domain for d in result.domains]
        assert ArtifactDomain.CONCURRENCY in domains

    def test_fallback_api_keywords(self, detector, mock_provider):
        """Should detect API via fallback keywords."""
        mock_provider.invoke.side_effect = ProviderError("error")

        result = detector.detect("HTTP REST endpoint with webhook handler")

        domains = [d.domain for d in result.domains]
        assert ArtifactDomain.API in domains

    def test_fallback_messaging_keywords(self, detector, mock_provider):
        """Should detect MESSAGING via fallback keywords."""
        mock_provider.invoke.side_effect = ProviderTimeoutError("timeout")

        result = detector.detect("Kafka message queue pub sub with DLQ")

        domains = [d.domain for d in result.domains]
        assert ArtifactDomain.MESSAGING in domains

    def test_fallback_transform_keywords(self, detector, mock_provider):
        """Should detect TRANSFORM via fallback keywords."""
        mock_provider.invoke.side_effect = ProviderError("error")

        result = detector.detect("parse serialize JSON XML transform")

        domains = [d.domain for d in result.domains]
        assert ArtifactDomain.TRANSFORM in domains

    def test_fallback_no_keywords(self, detector, mock_provider):
        """Should return empty domains when no keywords match."""
        mock_provider.invoke.side_effect = ProviderTimeoutError("timeout")

        result = detector.detect("hello world foo bar baz")

        assert len(result.domains) == 0
        assert result.ambiguity == "high"

    def test_fallback_confidence_calculation(self, detector, mock_provider):
        """Should calculate confidence based on keyword matches."""
        mock_provider.invoke.side_effect = ProviderError("error")

        result = detector.detect("auth token jwt password hash")

        # Should have SECURITY with decent confidence
        security_domain = next(
            (d for d in result.domains if d.domain == ArtifactDomain.SECURITY), None
        )
        assert security_domain is not None
        assert 0.3 <= security_domain.confidence <= 0.9

    def test_keyword_detection_direct(self):
        """Test keyword detection logic directly."""
        # Create detector and test fallback method
        with patch("bmad_assist.providers.ClaudeSDKProvider") as MockProv:
            MockProv.return_value = Mock()
            detector = DomainDetector(project_root=Path("/tmp"), cache_enabled=False)

            result = detector._fallback_keyword_detection(
                "database SQL query with transaction"
            )

            assert len(result.domains) >= 1
            domains = {d.domain for d in result.domains}
            assert ArtifactDomain.STORAGE in domains


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_timeout_fallback(self, detector, mock_provider):
        """Should fall back to keywords on timeout."""
        mock_provider.invoke.side_effect = ProviderTimeoutError("Request timed out")

        result = detector.detect("JWT auth")

        assert result.ambiguity == "high"
        assert len(result.domains) >= 1

    def test_provider_error_fallback(self, detector, mock_provider):
        """Should fall back to keywords on provider error."""
        mock_provider.invoke.side_effect = ProviderError("API error")

        result = detector.detect("database query")

        assert result.ambiguity == "high"
        assert len(result.domains) >= 1

    def test_unexpected_error_fallback(self, detector, mock_provider):
        """Should fall back to keywords on unexpected error (e.g., JSON parsing)."""
        # Simulate a JSON parsing error by returning malformed JSON that passes
        # initial extraction but fails Pydantic validation
        mock_provider.parse_output.return_value = '{"invalid": json}'

        result = detector.detect("async worker")

        assert result.ambiguity == "high"
        assert len(result.domains) >= 1


# =============================================================================
# Serialization Tests
# =============================================================================


class TestSerialization:
    """Tests for serialization/deserialization."""

    def test_serialize_domain_detection_result(self):
        """Test serialization of DomainDetectionResult."""
        result = DomainDetectionResult(
            domains=[
                DomainConfidence(
                    domain=ArtifactDomain.SECURITY,
                    confidence=0.9,
                    signals=["auth", "token"],
                )
            ],
            reasoning="Test reasoning",
            ambiguity="low",
        )

        data = serialize_domain_detection_result(result)

        assert data["reasoning"] == "Test reasoning"
        assert data["ambiguity"] == "low"
        assert len(data["domains"]) == 1
        assert data["domains"][0]["domain"] == "security"
        assert data["domains"][0]["confidence"] == 0.9

    def test_deserialize_domain_detection_result(self):
        """Test deserialization of DomainDetectionResult."""
        data = {
            "domains": [
                {
                    "domain": "api",
                    "confidence": 0.8,
                    "signals": ["http", "endpoint"],
                }
            ],
            "reasoning": "Has HTTP endpoints detected",
            "ambiguity": "none",
        }

        result = deserialize_domain_detection_result(data)

        assert len(result.domains) == 1
        assert result.domains[0].domain == ArtifactDomain.API
        assert result.domains[0].confidence == 0.8
        assert result.reasoning == "Has HTTP endpoints detected"

    def test_roundtrip_serialization(self):
        """Test roundtrip serialization/deserialization."""
        original = DomainDetectionResult(
            domains=[
                DomainConfidence(
                    domain=ArtifactDomain.CONCURRENCY,
                    confidence=0.75,
                    signals=["async"],
                )
            ],
            reasoning="Test",
            ambiguity="medium",
        )

        data = serialize_domain_detection_result(original)
        restored = deserialize_domain_detection_result(data)

        assert restored.domains[0].domain == original.domains[0].domain
        assert restored.domains[0].confidence == original.domains[0].confidence
        assert restored.reasoning == original.reasoning
        assert restored.ambiguity == original.ambiguity


# =============================================================================
# Webhook-Relay Example Tests
# =============================================================================


class TestWebhookRelayExamples:
    """Tests based on webhook-relay examples from Epic 26."""

    def test_story_1_3_hmac_security(self, detector, mock_provider):
        """Story 1-3: HMAC security should detect SECURITY domain."""
        mock_provider.parse_output.return_value = """{
            "domains": [
                {"name": "security", "confidence": 0.95, "signals": ["hmac", "signature", "secret"]}
            ],
            "reasoning": "HMAC signature verification with signing key",
            "ambiguity": "none"
        }"""

        artifact = """
        HMAC signature verification for webhooks.
        Validates X-Hub-Signature-256 header against calculated HMAC-SHA256.
        Uses constant-time comparison to prevent timing attacks.
        """

        result = detector.detect(artifact)

        assert any(d.domain == ArtifactDomain.SECURITY for d in result.domains)

    def test_story_4_3_storage_dlq(self, detector, mock_provider):
        """Story 4-3: Storage/DLQ should detect STORAGE and MESSAGING."""
        mock_provider.parse_output.return_value = """{
            "domains": [
                {"name": "storage", "confidence": 0.85, "signals": ["sql", "query", "database"]},
                {"name": "messaging", "confidence": 0.8, "signals": ["dlq", "dead letter", "retry"]}
            ],
            "reasoning": "SQL database operations with dead letter queue handling",
            "ambiguity": "low"
        }"""

        artifact = """
        Dead letter queue processor with SQL storage.
        Inserts failed messages into DLQ table with retry count.
        Queries pending messages and processes with exponential backoff.
        """

        result = detector.detect(artifact)

        domains = {d.domain for d in result.domains}
        assert ArtifactDomain.STORAGE in domains
        assert ArtifactDomain.MESSAGING in domains

    def test_story_2_3_transform(self, detector, mock_provider):
        """Story 2-3: Data transform should detect TRANSFORM."""
        mock_provider.parse_output.return_value = """{
            "domains": [
                {"name": "transform", "confidence": 0.9, "signals": ["parse", "serialize", "json", "transform"]}
            ],
            "reasoning": "Data transformation with JSON serialization",
            "ambiguity": "none"
        }"""

        artifact = """
        Transform incoming webhook payload to internal format.
        Parse JSON, validate schema, serialize to protobuf.
        Handle CSV, XML, and YAML input formats.
        """

        result = detector.detect(artifact)

        assert any(d.domain == ArtifactDomain.TRANSFORM for d in result.domains)

    def test_story_3_4_fan_out_concurrency(self, detector, mock_provider):
        """Story 3-4: Fan-out should detect CONCURRENCY and API."""
        mock_provider.parse_output.return_value = """{
            "domains": [
                {"name": "concurrency", "confidence": 0.85, "signals": ["goroutine", "async", "concurrent"]},
                {"name": "api", "confidence": 0.75, "signals": ["http", "client"]}
            ],
            "reasoning": "Concurrent fan-out to multiple HTTP endpoints",
            "ambiguity": "low"
        }"""

        artifact = """
        Fan-out delivery to multiple webhook endpoints concurrently.
        Spawns goroutine per destination for parallel HTTP POST.
        Uses sync.WaitGroup for coordination.
        """

        result = detector.detect(artifact)

        domains = {d.domain for d in result.domains}
        assert ArtifactDomain.CONCURRENCY in domains
        assert ArtifactDomain.API in domains

    def test_story_5_2_endpoints(self, detector, mock_provider):
        """Story 5-2: API endpoints should detect API and STORAGE."""
        mock_provider.parse_output.return_value = """{
            "domains": [
                {"name": "api", "confidence": 0.9, "signals": ["endpoint", "route", "handler"]},
                {"name": "storage", "confidence": 0.7, "signals": ["db", "query"]}
            ],
            "reasoning": "HTTP REST endpoints with database persistence",
            "ambiguity": "low"
        }"""

        artifact = """
        REST API for webhook management.
        POST /webhooks creates new webhook with database storage.
        GET /webhooks lists all registered endpoints.
        """

        result = detector.detect(artifact)

        domains = {d.domain for d in result.domains}
        assert ArtifactDomain.API in domains
        assert ArtifactDomain.STORAGE in domains


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunction:
    """Tests for the detect_domains convenience function."""

    def test_detect_domains_basic(self, temp_project_root):
        """Test basic usage of detect_domains function."""
        mock_provider = Mock()
        mock_provider.invoke.return_value = Mock(
            stdout="", stderr="", exit_code=0, duration_ms=100, model="haiku", command=[]
        )
        mock_provider.parse_output.return_value = """{
            "domains": [{"name": "security", "confidence": 0.8, "signals": []}],
            "reasoning": "Test reasoning provided",
            "ambiguity": "none"
        }"""

        # Create detector with mocked provider
        detector = DomainDetector(
            project_root=temp_project_root,
            model="haiku",
        )
        detector._provider = mock_provider

        result = detector.detect("verify JWT tokens")

        assert len(result.domains) == 1
        assert result.domains[0].domain == ArtifactDomain.SECURITY

    def test_detect_domains_default_project_root(self):
        """Test detect_domains with default project root."""
        # Should use current directory
        mock_provider = Mock()
        mock_provider.invoke.return_value = Mock(
            stdout="", stderr="", exit_code=0, duration_ms=100, model="haiku", command=[]
        )
        mock_provider.parse_output.return_value = """{
            "domains": [],
            "reasoning": "Empty",
            "ambiguity": "high"
        }"""

        with patch("bmad_assist.providers.ClaudeSDKProvider") as MockProv:
            MockProv.return_value = mock_provider

            result = detect_domains("test")
            assert isinstance(result, DomainDetectionResult)


# =============================================================================
# Domain Keywords Coverage Tests
# =============================================================================


class TestDomainKeywords:
    """Tests to verify domain keywords are properly defined."""

    def test_all_domains_have_keywords(self):
        """All ArtifactDomain values should have keywords defined."""
        for domain in ArtifactDomain:
            assert domain in DOMAIN_KEYWORDS
            assert len(DOMAIN_KEYWORDS[domain]) > 0

    def test_security_keywords_coverage(self):
        """SECURITY should have relevant keywords."""
        keywords = DOMAIN_KEYWORDS[ArtifactDomain.SECURITY]
        assert "auth" in keywords
        assert "jwt" in keywords
        assert "token" in keywords
        assert "hash" in keywords

    def test_storage_keywords_coverage(self):
        """STORAGE should have relevant keywords."""
        keywords = DOMAIN_KEYWORDS[ArtifactDomain.STORAGE]
        assert "database" in keywords
        assert "sql" in keywords
        assert "query" in keywords
        assert "transaction" in keywords

    def test_concurrency_keywords_coverage(self):
        """CONCURRENCY should have relevant keywords."""
        keywords = DOMAIN_KEYWORDS[ArtifactDomain.CONCURRENCY]
        assert "async" in keywords
        assert "thread" in keywords
        assert "mutex" in keywords
        assert "lock" in keywords

    def test_api_keywords_coverage(self):
        """API should have relevant keywords."""
        keywords = DOMAIN_KEYWORDS[ArtifactDomain.API]
        assert "http" in keywords
        assert "rest" in keywords
        assert "endpoint" in keywords
        assert "api" in keywords

    def test_messaging_keywords_coverage(self):
        """MESSAGING should have relevant keywords."""
        keywords = DOMAIN_KEYWORDS[ArtifactDomain.MESSAGING]
        assert "message" in keywords
        assert "queue" in keywords
        assert "pub" in keywords
        assert "sub" in keywords

    def test_transform_keywords_coverage(self):
        """TRANSFORM should have relevant keywords."""
        keywords = DOMAIN_KEYWORDS[ArtifactDomain.TRANSFORM]
        assert "parse" in keywords
        assert "serialize" in keywords
