"""Metrics collection for Deep Verify benchmarking.

This module provides the MetricsCollector class for evaluating Deep Verify
performance against labeled test corpora, including precision, recall, F1 scores,
and per-severity false positive rates.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from bmad_assist.deep_verify.core.types import (
    ArtifactDomain,
    DomainConfidence,
    Finding,
    MethodId,
    PatternId,
    Severity,
    Verdict,
)

if TYPE_CHECKING:
    from bmad_assist.deep_verify.core.engine import DeepVerifyEngine
    from bmad_assist.deep_verify.metrics.corpus_loader import (
        ArtifactLabel,
        ExpectedDomainLabel,
        ExpectedFindingLabel,
    )

logger = logging.getLogger(__name__)


# =============================================================================
# Metrics Types
# =============================================================================


@dataclass(frozen=True, slots=True)
class ExpectedFinding:
    """Ground truth finding from corpus labels."""

    pattern_id: PatternId | None
    severity: Severity
    title: str
    description: str
    method_id: MethodId | None
    domain: ArtifactDomain | None
    line_number: int | None
    quote: str | None

    @classmethod
    def from_label(cls, label: ExpectedFindingLabel) -> ExpectedFinding:
        """Create from corpus loader ExpectedFindingLabel."""
        return cls(
            pattern_id=label.pattern_id,
            severity=label.severity,
            title=label.title,
            description=label.description,
            method_id=label.method_id,
            domain=label.domain,
            line_number=label.line_number,
            quote=label.quote,
        )


@dataclass(frozen=True, slots=True)
class ArtifactMetrics:
    """Metrics for a single artifact evaluation.

    Attributes:
        artifact_id: Unique identifier for the artifact.
        true_positives: Findings correctly identified.
        false_positives: Findings incorrectly flagged.
        false_negatives: Expected findings that were missed.
        true_negatives: Count of correct non-findings (see Dev Notes).
        domain_accuracy: 1.0 if all domains correct, else proportion.
        verdict_match: Whether actual verdict matches expected.

    """

    artifact_id: str
    true_positives: list[Finding] = field(default_factory=list)
    false_positives: list[Finding] = field(default_factory=list)
    false_negatives: list[ExpectedFinding] = field(default_factory=list)
    true_negatives: int = 0
    domain_accuracy: float = 0.0
    verdict_match: bool = False

    @property
    def precision(self) -> float:
        """Calculate precision: TP / (TP + FP)."""
        tp = len(self.true_positives)
        fp = len(self.false_positives)
        if tp + fp == 0:
            return 0.0
        return tp / (tp + fp)

    @property
    def recall(self) -> float:
        """Calculate recall: TP / (TP + FN)."""
        tp = len(self.true_positives)
        fn = len(self.false_negatives)
        if tp + fn == 0:
            return 0.0
        return tp / (tp + fn)

    @property
    def f1_score(self) -> float:
        """Calculate F1 score: 2 * (P * R) / (P + R)."""
        p = self.precision
        r = self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)


@dataclass(frozen=True, slots=True)
class CategoryMetrics:
    """Metrics aggregated by category (method, severity, or domain).

    Attributes:
        category: Category identifier (e.g., "#153", "critical", "concurrency").
        total_artifacts: Number of artifacts evaluated in this category.
        true_positives: Count of true positives.
        false_positives: Count of false positives.
        false_negatives: Count of false negatives.
        true_negatives: Count of true negatives.

    """

    category: str
    total_artifacts: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    @property
    def precision(self) -> float:
        """Calculate precision."""
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        """Calculate recall."""
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1_score(self) -> float:
        """Calculate F1 score."""
        p = self.precision
        r = self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    @property
    def accuracy(self) -> float:
        """Calculate accuracy: (TP + TN) / Total."""
        total = (
            self.true_positives + self.false_positives + self.false_negatives + self.true_negatives
        )
        if total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / total


@dataclass(frozen=True, slots=True)
class SeverityMetrics:
    """Metrics tracked per severity level.

    Attributes:
        severity: Severity level.
        false_positives: Count of false positives.
        true_positives: Count of true positives.
        fp_rate: False positive rate.
        meets_target: Whether FP rate is below target.

    """

    severity: Severity
    false_positives: int = 0
    true_positives: int = 0
    fp_rate: float = 0.0
    meets_target: bool = False


@dataclass(frozen=True, slots=True)
class DomainDetectionMetrics:
    """Metrics for domain detection accuracy.

    Attributes:
        total_artifacts: Total number of artifacts evaluated.
        correct_domains: Count with all expected domains found.
        partial_domains: Count with some domains missed.
        incorrect_domains: Count with wrong domains detected.
        accuracy: Overall accuracy (target: >90%).
        avg_confidence: Average confidence score.
        confidence_calibration: Correlation between confidence and accuracy.
        per_domain_accuracy: Accuracy per domain type.

    """

    total_artifacts: int = 0
    correct_domains: int = 0
    partial_domains: int = 0
    incorrect_domains: int = 0
    accuracy: float = 0.0
    avg_confidence: float = 0.0
    confidence_calibration: float = 0.0
    per_domain_accuracy: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MetricsSummary:
    """Summary of overall metrics.

    Attributes:
        total_artifacts: Total artifacts evaluated.
        total_findings: Total findings across all artifacts.
        overall_precision: Weighted average precision.
        overall_recall: Weighted average recall.
        overall_f1: Weighted average F1.
        duration_seconds: Total evaluation time.

    """

    total_artifacts: int = 0
    total_findings: int = 0
    overall_precision: float = 0.0
    overall_recall: float = 0.0
    overall_f1: float = 0.0
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class CorpusMetricsReport:
    """Complete metrics report for corpus evaluation.

    Attributes:
        summary: Overall metrics summary.
        artifact_metrics: Per-artifact metrics.
        method_metrics: Per-method metrics.
        severity_metrics: Per-severity metrics.
        domain_metrics: Per-domain metrics.
        domain_detection_metrics: Domain detection accuracy metrics.
        timestamp: ISO timestamp of report generation.

    """

    summary: MetricsSummary
    artifact_metrics: list[ArtifactMetrics]
    method_metrics: list[CategoryMetrics]
    severity_metrics: list[SeverityMetrics]
    domain_metrics: list[CategoryMetrics]
    domain_detection_metrics: DomainDetectionMetrics
    timestamp: str = field(
        default_factory=lambda: __import__("datetime").datetime.now().isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON/YAML serialization."""
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total_artifacts": self.summary.total_artifacts,
                "total_findings": self.summary.total_findings,
                "overall_precision": round(self.summary.overall_precision, 4),
                "overall_recall": round(self.summary.overall_recall, 4),
                "overall_f1": round(self.summary.overall_f1, 4),
                "duration_seconds": round(self.summary.duration_seconds, 2),
            },
            "method_metrics": [
                {
                    "method": m.category,
                    "precision": round(m.precision, 4),
                    "recall": round(m.recall, 4),
                    "f1_score": round(m.f1_score, 4),
                    "tp": m.true_positives,
                    "fp": m.false_positives,
                    "fn": m.false_negatives,
                }
                for m in self.method_metrics
            ],
            "severity_metrics": [
                {
                    "severity": m.severity.value,
                    "fp_rate": round(m.fp_rate, 4),
                    "fp": m.false_positives,
                    "tp": m.true_positives,
                    "meets_target": m.meets_target,
                }
                for m in self.severity_metrics
            ],
            "domain_detection": {
                "accuracy": round(self.domain_detection_metrics.accuracy, 4),
                "correct": self.domain_detection_metrics.correct_domains,
                "partial": self.domain_detection_metrics.partial_domains,
                "incorrect": self.domain_detection_metrics.incorrect_domains,
                "per_domain": self.domain_detection_metrics.per_domain_accuracy,
            },
        }


# =============================================================================
# Metrics Collector
# =============================================================================


class MetricsCollector:
    """Collects and aggregates Deep Verify metrics.

    Evaluates the Deep Verify engine against a labeled test corpus,
    calculating precision, recall, F1 scores, and false positive rates.
    """

    def __init__(self, corpus_path: Path | None = None) -> None:
        """Initialize the metrics collector.

        Args:
            corpus_path: Path to corpus directory. If None, uses default.

        """
        from bmad_assist.deep_verify.metrics.corpus_loader import CorpusLoader

        self.corpus_loader = CorpusLoader(corpus_path)
        self._artifact_results: list[ArtifactMetrics] = []

    def _findings_match(
        self,
        actual: Finding,
        expected: ExpectedFinding,
        line_tolerance: int = 3,
    ) -> bool:
        """Check if an actual finding matches an expected finding.

        Matching criteria (in order of priority):
        1. Pattern ID match (if both have pattern_id)
        2. Line number proximity (within tolerance)
        3. Quote similarity (if quotes available)

        Args:
            actual: Actual finding from verification.
            expected: Expected finding from label.
            line_tolerance: Allowed line number difference.

        Returns:
            True if findings match.

        """
        # Pattern ID match is strongest signal
        if actual.pattern_id and expected.pattern_id and actual.pattern_id == expected.pattern_id:
            return True

        # Line number proximity
        if actual.evidence and expected.line_number is not None:
            for evidence in actual.evidence:
                if (
                    evidence.line_number is not None
                    and abs(evidence.line_number - expected.line_number) <= line_tolerance
                    and actual.severity == expected.severity
                ):
                    return True

        # Quote similarity (fallback)
        if actual.evidence and expected.quote:
            for evidence in actual.evidence:
                if expected.quote in evidence.quote or evidence.quote in expected.quote:
                    return True

        return False

    def _calculate_domain_accuracy(
        self,
        actual_domains: list[DomainConfidence],
        expected_domains: list[ExpectedDomainLabel],
    ) -> float:
        """Calculate domain detection accuracy.

        Returns proportion of expected domains that were found.
        """
        if not expected_domains:
            return 1.0 if not actual_domains else 0.0

        expected_set = {d.domain for d in expected_domains}
        actual_set = {d.domain for d in actual_domains}

        if not expected_set:
            return 1.0

        correct = len(expected_set & actual_set)
        return correct / len(expected_set)

    def evaluate_artifact(
        self,
        artifact_id: str,
        verdict: Verdict,
        label: ArtifactLabel,
    ) -> ArtifactMetrics:
        """Evaluate a single artifact against its label.

        Args:
            artifact_id: Unique artifact identifier.
            verdict: Actual verification verdict.
            label: Expected label with ground truth.

        Returns:
            ArtifactMetrics with evaluation results.

        """
        # Convert expected findings
        expected_findings = [ExpectedFinding.from_label(ef) for ef in label.expected_findings]

        # Match findings
        true_positives: list[Finding] = []
        false_positives: list[Finding] = []
        false_negatives: list[ExpectedFinding] = []

        # Track which expected findings were matched
        matched_expected: set[int] = set()

        for actual in verdict.findings:
            matched = False
            for i, expected in enumerate(expected_findings):
                if i in matched_expected:
                    continue
                if self._findings_match(actual, expected):
                    true_positives.append(actual)
                    matched_expected.add(i)
                    matched = True
                    break

            if not matched:
                false_positives.append(actual)

        # Unmatched expected findings are false negatives
        for i, expected in enumerate(expected_findings):
            if i not in matched_expected:
                false_negatives.append(expected)

        # Calculate true negatives (correct non-findings)
        # TN = count of methods that correctly found nothing in domains
        # where no issues were expected (and none were found)
        true_negatives = self._calculate_true_negatives(
            verdict.findings, expected_findings, label.expected_domains
        )

        # Calculate domain accuracy
        domain_accuracy = self._calculate_domain_accuracy(
            verdict.domains_detected,
            label.expected_domains,
        )

        # Verdict match is determined by whether we have critical findings
        # In practice, verdict_match is less important than individual finding accuracy
        expected_has_critical = any(ef.severity == Severity.CRITICAL for ef in expected_findings)
        actual_has_critical = any(f.severity == Severity.CRITICAL for f in verdict.findings)
        verdict_match = expected_has_critical == actual_has_critical

        return ArtifactMetrics(
            artifact_id=artifact_id,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            true_negatives=true_negatives,
            domain_accuracy=domain_accuracy,
            verdict_match=verdict_match,
        )

    async def evaluate_corpus(
        self,
        engine: DeepVerifyEngine,
        progress_callback: Callable[[int, int], None] | None = None,
        max_concurrent: int = 4,
        filter_predicate: Callable[[ArtifactLabel], bool] | None = None,
    ) -> CorpusMetricsReport:
        """Evaluate the entire corpus asynchronously.

        Args:
            engine: DeepVerifyEngine instance to evaluate.
            progress_callback: Optional callback(current, total) for progress updates.
            max_concurrent: Maximum concurrent evaluations.
            filter_predicate: Optional filter function for artifacts.

        Returns:
            CorpusMetricsReport with aggregated results.

        """
        import time

        start_time = time.time()

        # Load all labels
        labels = self.corpus_loader.load_all_labels()
        if filter_predicate:
            labels = [label for label in labels if filter_predicate(label)]

        total = len(labels)
        completed = 0

        # Semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def evaluate_single(label: ArtifactLabel) -> ArtifactMetrics | Exception:
            async with semaphore:
                try:
                    content = self.corpus_loader.load_artifact_content(label)
                    verdict = await engine.verify(content)
                    result = self.evaluate_artifact(label.artifact_id, verdict, label)

                    nonlocal completed
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total)

                    return result
                except (OSError, ValueError, KeyError, yaml.YAMLError) as e:
                    logger.warning("Failed to evaluate %s: %s", label.artifact_id, e)
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total)
                    return e

        # Run evaluations
        tasks = [evaluate_single(label) for label in labels]
        results = await asyncio.gather(*tasks)

        # Filter out exceptions
        artifact_metrics: list[ArtifactMetrics] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Evaluation failed: %s", result)
            else:
                artifact_metrics.append(result)

        # Aggregate metrics
        duration = time.time() - start_time
        summary = self._calculate_summary(artifact_metrics, duration)
        method_metrics = self._aggregate_method_metrics(artifact_metrics)
        severity_metrics = self._aggregate_severity_metrics(artifact_metrics)
        domain_metrics = self._aggregate_domain_metrics(artifact_metrics)
        domain_detection_metrics = self._calculate_domain_detection_metrics(
            artifact_metrics, labels
        )

        return CorpusMetricsReport(
            summary=summary,
            artifact_metrics=artifact_metrics,
            method_metrics=method_metrics,
            severity_metrics=severity_metrics,
            domain_metrics=domain_metrics,
            domain_detection_metrics=domain_detection_metrics,
        )

    def _calculate_summary(
        self,
        artifact_metrics: list[ArtifactMetrics],
        duration: float,
    ) -> MetricsSummary:
        """Calculate overall summary metrics."""
        if not artifact_metrics:
            return MetricsSummary(duration_seconds=duration)

        total_tp = sum(len(am.true_positives) for am in artifact_metrics)
        total_fp = sum(len(am.false_positives) for am in artifact_metrics)
        total_fn = sum(len(am.false_negatives) for am in artifact_metrics)

        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        total_findings = sum(
            len(am.true_positives) + len(am.false_positives) for am in artifact_metrics
        )

        return MetricsSummary(
            total_artifacts=len(artifact_metrics),
            total_findings=total_findings,
            overall_precision=precision,
            overall_recall=recall,
            overall_f1=f1,
            duration_seconds=duration,
        )

    def _aggregate_method_metrics(
        self,
        artifact_metrics: list[ArtifactMetrics],
    ) -> list[CategoryMetrics]:
        """Aggregate metrics per method."""
        method_stats: dict[str, dict[str, int]] = {}

        for am in artifact_metrics:
            for tp_finding in am.true_positives:
                method_key = tp_finding.method_id
                if method_key not in method_stats:
                    method_stats[method_key] = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
                method_stats[method_key]["tp"] += 1

            for fp_finding in am.false_positives:
                method_key = fp_finding.method_id
                if method_key not in method_stats:
                    method_stats[method_key] = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
                method_stats[method_key]["fp"] += 1

            for fn_expected in am.false_negatives:
                fn_method_key: str = str(fn_expected.method_id) if fn_expected.method_id else "unknown"
                if fn_method_key not in method_stats:
                    method_stats[fn_method_key] = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
                method_stats[fn_method_key]["fn"] += 1

        return [
            CategoryMetrics(
                category=method,
                true_positives=stats["tp"],
                false_positives=stats["fp"],
                false_negatives=stats["fn"],
                true_negatives=stats["tn"],
            )
            for method, stats in sorted(method_stats.items())
        ]

    def _aggregate_severity_metrics(
        self,
        artifact_metrics: list[ArtifactMetrics],
    ) -> list[SeverityMetrics]:
        """Aggregate metrics per severity level."""
        severity_stats: dict[Severity, dict[str, int]] = {
            Severity.CRITICAL: {"tp": 0, "fp": 0},
            Severity.ERROR: {"tp": 0, "fp": 0},
            Severity.WARNING: {"tp": 0, "fp": 0},
            Severity.INFO: {"tp": 0, "fp": 0},
        }

        for am in artifact_metrics:
            for finding in am.true_positives:
                severity_stats[finding.severity]["tp"] += 1
            for finding in am.false_positives:
                severity_stats[finding.severity]["fp"] += 1

        # Targets from Epic 26
        targets = {
            Severity.CRITICAL: 0.01,
            Severity.ERROR: 0.05,
            Severity.WARNING: 0.15,
            Severity.INFO: 1.0,
        }

        return [
            SeverityMetrics(
                severity=severity,
                false_positives=stats["fp"],
                true_positives=stats["tp"],
                fp_rate=stats["fp"] / (stats["fp"] + stats["tp"])
                if (stats["fp"] + stats["tp"]) > 0
                else 0.0,
                meets_target=(
                    stats["fp"] / (stats["fp"] + stats["tp"])
                    if (stats["fp"] + stats["tp"]) > 0
                    else 0.0
                )
                <= targets[severity],
            )
            for severity, stats in severity_stats.items()
        ]

    def _aggregate_domain_metrics(
        self,
        artifact_metrics: list[ArtifactMetrics],
    ) -> list[CategoryMetrics]:
        """Aggregate metrics per domain."""
        # Domain metrics are calculated from finding domains
        domain_stats: dict[str, dict[str, int]] = {}

        for am in artifact_metrics:
            for tp_finding in am.true_positives:
                if tp_finding.domain:
                    domain = tp_finding.domain.value
                    if domain not in domain_stats:
                        domain_stats[domain] = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
                    domain_stats[domain]["tp"] += 1

            for fp_finding in am.false_positives:
                if fp_finding.domain:
                    domain = fp_finding.domain.value
                    if domain not in domain_stats:
                        domain_stats[domain] = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
                    domain_stats[domain]["fp"] += 1

            for fn_expected in am.false_negatives:
                if fn_expected.domain:
                    domain = fn_expected.domain.value
                    if domain not in domain_stats:
                        domain_stats[domain] = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
                    domain_stats[domain]["fn"] += 1

        return [
            CategoryMetrics(
                category=domain,
                true_positives=stats["tp"],
                false_positives=stats["fp"],
                false_negatives=stats["fn"],
                true_negatives=stats["tn"],
            )
            for domain, stats in sorted(domain_stats.items())
        ]

    def _calculate_domain_detection_metrics(
        self,
        artifact_metrics: list[ArtifactMetrics],
        labels: list[ArtifactLabel],
    ) -> DomainDetectionMetrics:
        """Calculate domain detection accuracy metrics."""
        if not artifact_metrics:
            return DomainDetectionMetrics()

        # Create lookup by artifact_id
        metrics_by_id = {am.artifact_id: am for am in artifact_metrics}

        correct = 0
        partial = 0
        incorrect = 0

        for label in labels:
            if label.artifact_id not in metrics_by_id:
                continue

            am = metrics_by_id[label.artifact_id]
            accuracy = am.domain_accuracy

            if accuracy >= 1.0:
                correct += 1
            elif accuracy > 0.0:
                partial += 1
            else:
                incorrect += 1

        total = correct + partial + incorrect
        accuracy = correct / total if total > 0 else 0.0

        # Calculate average confidence and per-domain accuracy
        confidences = []
        per_domain_stats: dict[str, list[bool]] = {}

        for label in labels:
            if label.artifact_id not in metrics_by_id:
                continue
            am = metrics_by_id[label.artifact_id]
            for dc in label.expected_domains:
                confidences.append(dc.confidence)
                domain = dc.domain.value
                if domain not in per_domain_stats:
                    per_domain_stats[domain] = []
                per_domain_stats[domain].append(am.domain_accuracy >= 1.0)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        per_domain_accuracy = {
            d: (sum(stats) / len(stats) if stats else 0.0) for d, stats in per_domain_stats.items()
        }

        # Calculate calibration: correlation between confidence and accuracy
        # Simple approach: confidence calibration = avg_accuracy when confidence > 0.5
        high_conf_domains = [
            am.domain_accuracy
            for label in labels
            if label.artifact_id in metrics_by_id
            for dc in label.expected_domains
            if dc.confidence > 0.5 and label.artifact_id in metrics_by_id
            for am in [metrics_by_id[label.artifact_id]]
        ]
        confidence_calibration = (
            sum(high_conf_domains) / len(high_conf_domains) if high_conf_domains else 0.0
        )

        return DomainDetectionMetrics(
            total_artifacts=total,
            correct_domains=correct,
            partial_domains=partial,
            incorrect_domains=incorrect,
            accuracy=accuracy,
            avg_confidence=avg_confidence,
            confidence_calibration=confidence_calibration,
            per_domain_accuracy=per_domain_accuracy,
        )

    def get_summary(self) -> MetricsSummary:
        """Get summary of current metrics (after evaluation).

        Returns:
            MetricsSummary from last evaluation.

        """
        if not self._artifact_results:
            return MetricsSummary()

        return self._calculate_summary(self._artifact_results, 0.0)

    def _calculate_true_negatives(
        self,
        actual_findings: list[Finding],
        expected_findings: list[ExpectedFinding],
        expected_domains: list[Any],
    ) -> int:
        """Calculate true negatives for an artifact.

        TN = count of domains where no issues were expected AND none were found.

        Args:
            actual_findings: Findings from verification.
            expected_findings: Expected findings from label.
            expected_domains: Expected domains from label.

        Returns:
            Count of true negatives.

        """
        if not expected_domains:
            return 0

        # Get domains with expected findings
        domains_with_expected_issues = {
            ef.domain for ef in expected_findings if ef.domain is not None
        }

        # Get domains with actual findings
        domains_with_actual_issues = {f.domain for f in actual_findings if f.domain is not None}

        # Count domains with no expected and no actual issues
        true_negatives = 0
        for domain_label in expected_domains:
            domain = domain_label.domain
            if (
                domain not in domains_with_expected_issues
                and domain not in domains_with_actual_issues
            ):
                true_negatives += 1

        return true_negatives
