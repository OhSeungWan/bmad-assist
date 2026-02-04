"""Corpus loading and validation for Deep Verify benchmarking.

This module provides types and functions for loading the labeled test corpus,
including manifest management, label validation, and golden test handling.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml

from bmad_assist.deep_verify.core.types import (
    ArtifactDomain,
    DomainConfidence,
    Finding,
    MethodId,
    PatternId,
    Severity,
    VerdictDecision,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Label Types
# =============================================================================


@dataclass(frozen=True, slots=True)
class ExpectedDomainLabel:
    """Expected domain in label file."""

    domain: ArtifactDomain
    confidence: float


@dataclass(frozen=True, slots=True)
class ExpectedFindingLabel:
    """Ground truth finding from corpus labels."""

    pattern_id: PatternId | None
    severity: Severity
    title: str
    description: str = ""
    method_id: MethodId | None = None
    domain: ArtifactDomain | None = None
    line_number: int | None = None
    quote: str | None = None


@dataclass(frozen=True, slots=True)
class KnownFalsePositive:
    """Known false positive that should NOT be flagged."""

    pattern_id: PatternId | None
    reason: str
    line_number: int | None = None


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    """Metadata for an artifact."""

    lines_of_code: int = 0
    complexity: Literal["low", "medium", "high"] = "medium"
    has_race_condition: bool = False
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ArtifactLabel:
    """Complete label for a test corpus artifact.

    Attributes:
        artifact_id: Unique identifier (dv-{NNN}).
        source: Source reference (e.g., "bmad-assist/story-X-Y" or "synthetic").
        artifact_type: Type of artifact ("code" or "spec").
        language: Programming language (go, python, etc.) or None.
        content_file: Path to artifact content file.
        expected_domains: List of expected domains with confidence.
        expected_findings: List of expected findings (ground truth).
        known_false_positives: List of known false positives.
        metadata: Additional metadata for analysis.

    """

    artifact_id: str
    source: str
    artifact_type: Literal["code", "spec"]
    language: str | None
    content_file: str
    expected_domains: list[ExpectedDomainLabel]
    expected_findings: list[ExpectedFindingLabel]
    known_false_positives: list[KnownFalsePositive]
    metadata: ArtifactMetadata

    @property
    def content_path(self) -> Path:
        """Get the content file path relative to corpus root."""
        return Path(self.content_file)


@dataclass(frozen=True, slots=True)
class GoldenExpectedVerdict:
    """Exact expected verdict for golden tests."""

    decision: VerdictDecision
    score: float
    findings: list[Finding]
    domains_detected: list[DomainConfidence]
    methods_executed: list[MethodId]


@dataclass(frozen=True, slots=True)
class GoldenTolerance:
    """Tolerance for floating-point comparisons in golden tests."""

    score: float = 0.1
    confidence: float = 0.05


@dataclass(frozen=True, slots=True)
class GoldenCase:
    """Golden test case with exact expected output."""

    artifact_id: str
    content_file: str
    expected_verdict: GoldenExpectedVerdict
    tolerance: GoldenTolerance


# =============================================================================
# Manifest Types
# =============================================================================


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    """Manifest describing the test corpus.

    Attributes:
        version: Semver for corpus format.
        created_at: ISO timestamp of manifest generation.
        artifact_count: Total number of artifacts.
        language_breakdown: Count per language.
        domain_breakdown: Count per domain.
        severity_breakdown: Count per severity.
        checksums: SHA256 checksums for artifact integrity.

    """

    version: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    artifact_count: int = 0
    language_breakdown: dict[str, int] = field(default_factory=dict)
    domain_breakdown: dict[str, int] = field(default_factory=dict)
    severity_breakdown: dict[str, int] = field(default_factory=dict)
    checksums: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            "version": self.version,
            "created_at": self.created_at,
            "artifact_count": self.artifact_count,
            "language_breakdown": self.language_breakdown,
            "domain_breakdown": self.domain_breakdown,
            "severity_breakdown": self.severity_breakdown,
            "checksums": self.checksums,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CorpusManifest:
        """Create from dictionary."""
        return cls(
            version=data.get("version", "1.0.0"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            artifact_count=data.get("artifact_count", 0),
            language_breakdown=data.get("language_breakdown", {}),
            domain_breakdown=data.get("domain_breakdown", {}),
            severity_breakdown=data.get("severity_breakdown", {}),
            checksums=data.get("checksums", {}),
        )


# =============================================================================
# Corpus Loader
# =============================================================================


class CorpusLoader:
    """Loads and validates the test corpus.

    Handles loading of artifact labels, golden cases, and manifest generation.
    """

    def __init__(self, corpus_path: Path | None = None) -> None:
        """Initialize the corpus loader.

        Args:
            corpus_path: Path to corpus directory. If None, uses default.

        """
        if corpus_path is None:
            # Default to tests/deep_verify/corpus relative to project root
            self.corpus_path = (
                Path(__file__).parent.parent.parent.parent.parent
                / "tests"
                / "deep_verify"
                / "corpus"
            )
        else:
            self.corpus_path = corpus_path

        self.labels_path = self.corpus_path / "labels"
        self.golden_path = self.corpus_path / "golden"
        self.artifacts_path = self.corpus_path / "artifacts"

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def load_label(self, label_file: Path) -> ArtifactLabel:
        """Load and validate a label file.

        Args:
            label_file: Path to label YAML file.

        Returns:
            Parsed and validated ArtifactLabel.

        Raises:
            ValueError: If label file is invalid.
            FileNotFoundError: If referenced content file doesn't exist.

        """
        with open(label_file) as f:
            data = yaml.safe_load(f)

        # Validate content file exists
        content_path = self.corpus_path / data["content_file"]
        if not content_path.exists():
            raise FileNotFoundError(f"Artifact file not found: {content_path}")

        # Parse expected domains
        expected_domains = []
        for domain_data in data.get("expected_domains", []):
            expected_domains.append(
                ExpectedDomainLabel(
                    domain=ArtifactDomain(domain_data["domain"]),
                    confidence=domain_data["confidence"],
                )
            )

        # Parse expected findings
        expected_findings = []
        for finding_data in data.get("expected_findings", []):
            pattern_id = finding_data.get("pattern_id")
            method_id = finding_data.get("method_id")
            domain_data = finding_data.get("domain")
            expected_findings.append(
                ExpectedFindingLabel(
                    pattern_id=PatternId(pattern_id) if pattern_id else None,
                    severity=Severity(finding_data["severity"]),
                    title=finding_data.get("title", ""),
                    description=finding_data.get("description", ""),
                    method_id=MethodId(method_id) if method_id else None,
                    domain=ArtifactDomain(domain_data) if domain_data else None,
                    line_number=finding_data.get("line_number"),
                    quote=finding_data.get("quote"),
                )
            )

        # Parse known false positives
        known_fps = []
        for fp_data in data.get("known_false_positives", []):
            pattern_id = fp_data.get("pattern_id")
            known_fps.append(
                KnownFalsePositive(
                    pattern_id=PatternId(pattern_id) if pattern_id else None,
                    reason=fp_data["reason"],
                    line_number=fp_data.get("line_number"),
                )
            )

        # Parse metadata
        meta_data = data.get("metadata", {})
        metadata = ArtifactMetadata(
            lines_of_code=meta_data.get("lines_of_code", 0),
            complexity=meta_data.get("complexity", "medium"),
            has_race_condition=meta_data.get("has_race_condition", False),
            custom={
                k: v
                for k, v in meta_data.items()
                if k not in ["lines_of_code", "complexity", "has_race_condition"]
            },
        )

        return ArtifactLabel(
            artifact_id=data["artifact_id"],
            source=data.get("source", ""),
            artifact_type=data.get("artifact_type", "unknown"),
            language=data.get("language"),
            content_file=data["content_file"],
            expected_domains=expected_domains,
            expected_findings=expected_findings,
            known_false_positives=known_fps,
            metadata=metadata,
        )

    def load_all_labels(self) -> list[ArtifactLabel]:
        """Load all label files from the corpus.

        Returns:
            List of all artifact labels.

        """
        labels: list[ArtifactLabel] = []
        if not self.labels_path.exists():
            logger.warning("Labels directory not found: %s", self.labels_path)
            return labels

        for label_file in sorted(self.labels_path.glob("*.yaml")):
            if label_file.name == "__init__.py":
                continue
            try:
                label = self.load_label(label_file)
                labels.append(label)
            except (ValueError, FileNotFoundError, KeyError) as e:
                logger.warning("Failed to load label %s: %s", label_file, e)

        return labels

    def load_golden_case(self, golden_file: Path) -> GoldenCase:
        """Load a golden test case.

        Args:
            golden_file: Path to golden test YAML file.

        Returns:
            Parsed GoldenCase.

        """
        with open(golden_file) as f:
            data = yaml.safe_load(f)

        # Parse expected verdict
        verdict_data = data["expected_verdict"]

        # Parse findings
        findings = []
        for finding_data in verdict_data.get("findings", []):
            evidence_data = finding_data.get("evidence", [])
            from bmad_assist.deep_verify.core.types import Evidence

            evidence = [
                Evidence(
                    quote=e["quote"],
                    line_number=e.get("line_number"),
                    source=e.get("source", ""),
                    confidence=e.get("confidence", 1.0),
                )
                for e in evidence_data
            ]

            domain_data = finding_data.get("domain")
            pattern_id_data = finding_data.get("pattern_id")

            findings.append(
                Finding(
                    id=finding_data["id"],
                    severity=Severity(finding_data["severity"]),
                    title=finding_data["title"],
                    description=finding_data.get("description", ""),
                    method_id=MethodId(finding_data["method_id"]),
                    pattern_id=PatternId(pattern_id_data) if pattern_id_data else None,
                    domain=ArtifactDomain(domain_data) if domain_data else None,
                    evidence=evidence,
                )
            )

        # Parse domains detected
        domains_detected = []
        for domain_data in verdict_data.get("domains_detected", []):
            domains_detected.append(
                DomainConfidence(
                    domain=ArtifactDomain(domain_data["domain"]),
                    confidence=domain_data["confidence"],
                    signals=domain_data.get("signals", []),
                )
            )

        expected_verdict = GoldenExpectedVerdict(
            decision=VerdictDecision(verdict_data["decision"]),
            score=verdict_data["score"],
            findings=findings,
            domains_detected=domains_detected,
            methods_executed=[MethodId(m) for m in verdict_data.get("methods_executed", [])],
        )

        # Parse tolerance
        tolerance_data = data.get("tolerance", {})
        tolerance = GoldenTolerance(
            score=tolerance_data.get("score", 0.1),
            confidence=tolerance_data.get("confidence", 0.05),
        )

        return GoldenCase(
            artifact_id=data["artifact_id"],
            content_file=data["content_file"],
            expected_verdict=expected_verdict,
            tolerance=tolerance,
        )

    def load_all_golden_cases(self) -> list[GoldenCase]:
        """Load all golden test cases.

        Returns:
            List of all golden cases.

        """
        cases: list[GoldenCase] = []
        if not self.golden_path.exists():
            logger.warning("Golden directory not found: %s", self.golden_path)
            return cases

        for golden_file in sorted(self.golden_path.glob("*.yaml")):
            if golden_file.name == "__init__.py":
                continue
            try:
                case = self.load_golden_case(golden_file)
                cases.append(case)
            except (ValueError, FileNotFoundError, KeyError) as e:
                logger.warning("Failed to load golden case %s: %s", golden_file, e)

        return cases

    def load_artifact_content(self, label: ArtifactLabel) -> str:
        """Load the content of an artifact.

        Args:
            label: Artifact label with content_file reference.

        Returns:
            Content of the artifact as string.

        """
        content_path = self.corpus_path / label.content_file
        with open(content_path) as f:
            return f.read()

    def generate_manifest(self) -> CorpusManifest:
        """Generate manifest from current labels.

        Returns:
            Generated CorpusManifest.

        """
        labels = self.load_all_labels()

        # Calculate breakdowns
        language_breakdown: dict[str, int] = {}
        domain_breakdown: dict[str, int] = {}
        severity_breakdown: dict[str, int] = {}
        checksums: dict[str, str] = {}

        for label in labels:
            # Language breakdown
            lang = label.language or "unknown"
            language_breakdown[lang] = language_breakdown.get(lang, 0) + 1

            # Domain breakdown
            for domain_label in label.expected_domains:
                domain = domain_label.domain.value
                domain_breakdown[domain] = domain_breakdown.get(domain, 0) + 1

            # Severity breakdown
            for finding in label.expected_findings:
                sev = finding.severity.value
                severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

            # Checksum
            content_path = self.corpus_path / label.content_file
            if content_path.exists():
                checksums[label.artifact_id] = self._compute_checksum(content_path)

        return CorpusManifest(
            version="1.0.0",
            created_at=datetime.now().isoformat(),
            artifact_count=len(labels),
            language_breakdown=language_breakdown,
            domain_breakdown=domain_breakdown,
            severity_breakdown=severity_breakdown,
            checksums=checksums,
        )

    def save_manifest(self, manifest: CorpusManifest) -> None:
        """Save manifest to YAML file.

        Args:
            manifest: Manifest to save.

        """
        manifest_path = self.corpus_path / "manifest.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(manifest.to_dict(), f, default_flow_style=False, sort_keys=False)

    def load_manifest(self) -> CorpusManifest | None:
        """Load manifest from YAML file.

        Returns:
            Loaded manifest or None if not found.

        """
        manifest_path = self.corpus_path / "manifest.yaml"
        if not manifest_path.exists():
            return None

        with open(manifest_path) as f:
            data = yaml.safe_load(f)

        return CorpusManifest.from_dict(data)
