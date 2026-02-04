"""Threshold checking for Deep Verify benchmarks.

This module provides threshold checking for CI integration, ensuring
accuracy metrics meet defined targets.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from bmad_assist.deep_verify.metrics.collector import (
    CorpusMetricsReport,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Threshold Types
# =============================================================================


@dataclass(frozen=True, slots=True)
class ThresholdResult:
    """Result of a threshold check.

    Attributes:
        passed: Whether the threshold was met.
        metric_name: Name of the metric checked.
        actual_value: Actual value of the metric.
        threshold_value: Threshold that was required.
        message: Human-readable result message.

    """

    passed: bool
    metric_name: str
    actual_value: float
    threshold_value: float
    message: str


@dataclass(frozen=True, slots=True)
class ThresholdConfig:
    """Configuration for benchmark thresholds.

    Attributes:
        overall_f1: Minimum required F1 score.
        domain_detection_accuracy: Minimum required domain detection accuracy.
        critical_fp_rate: Maximum allowed CRITICAL false positive rate.
        error_fp_rate: Maximum allowed ERROR false positive rate.
        warning_fp_rate: Maximum allowed WARNING false positive rate.
        per_method_f1: Minimum F1 per method ID.

    """

    overall_f1: float = 0.80
    domain_detection_accuracy: float = 0.90
    critical_fp_rate: float = 0.01
    error_fp_rate: float = 0.05
    warning_fp_rate: float = 0.15
    per_method_f1: dict[str, float] = field(
        default_factory=lambda: {
            "#153": 0.85,
            "#154": 0.80,
            "#155": 0.75,
            "#157": 0.75,
            "#201": 0.75,
            "#203": 0.75,
            "#204": 0.75,
            "#205": 0.75,
        }
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThresholdConfig:
        """Create from dictionary."""
        return cls(
            overall_f1=data.get("overall_f1", 0.80),
            domain_detection_accuracy=data.get("domain_detection_accuracy", 0.90),
            critical_fp_rate=data.get("critical_fp_rate", 0.01),
            error_fp_rate=data.get("error_fp_rate", 0.05),
            warning_fp_rate=data.get("warning_fp_rate", 0.15),
            per_method_f1=data.get("per_method_f1", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_f1": self.overall_f1,
            "domain_detection_accuracy": self.domain_detection_accuracy,
            "critical_fp_rate": self.critical_fp_rate,
            "error_fp_rate": self.error_fp_rate,
            "warning_fp_rate": self.warning_fp_rate,
            "per_method_f1": self.per_method_f1,
        }


# =============================================================================
# Threshold Checker
# =============================================================================


class ThresholdChecker:
    """Checks benchmark results against thresholds.

    Used for CI integration to fail builds when accuracy drops.
    """

    def __init__(self, config: ThresholdConfig | None = None) -> None:
        """Initialize with threshold configuration.

        Args:
            config: ThresholdConfig. If None, uses default thresholds.

        """
        self.config = config or ThresholdConfig()

    @classmethod
    def from_file(cls, path: Path) -> ThresholdChecker:
        """Load thresholds from YAML file.

        Args:
            path: Path to threshold YAML file.

        Returns:
            ThresholdChecker with loaded configuration.

        """
        with open(path) as f:
            data = yaml.safe_load(f)

        # Handle nested "thresholds" key if present
        if "thresholds" in data:
            data = data["thresholds"]

        config = ThresholdConfig.from_dict(data)
        return cls(config)

    def check(self, report: CorpusMetricsReport) -> list[ThresholdResult]:
        """Check all thresholds against a report.

        Args:
            report: CorpusMetricsReport to check.

        Returns:
            List of ThresholdResult for each check.

        """
        results: list[ThresholdResult] = []

        # Overall F1
        results.append(self._check_overall_f1(report))

        # Domain detection accuracy
        results.append(self._check_domain_detection(report))

        # Per-severity FP rates
        results.extend(self._check_severity_fp_rates(report))

        # Per-method F1
        results.extend(self._check_method_f1(report))

        return results

    def check_all_passed(self, report: CorpusMetricsReport) -> bool:
        """Check if all thresholds passed.

        Args:
            report: CorpusMetricsReport to check.

        Returns:
            True if all thresholds passed, False otherwise.

        """
        results = self.check(report)
        return all(r.passed for r in results)

    def _check_overall_f1(self, report: CorpusMetricsReport) -> ThresholdResult:
        """Check overall F1 threshold."""
        actual = report.summary.overall_f1
        threshold = self.config.overall_f1
        passed = actual >= threshold

        return ThresholdResult(
            passed=passed,
            metric_name="overall_f1",
            actual_value=actual,
            threshold_value=threshold,
            message=f"Overall F1: {actual:.1%} (required: >= {threshold:.1%}) {'✓' if passed else '✗'}",
        )

    def _check_domain_detection(self, report: CorpusMetricsReport) -> ThresholdResult:
        """Check domain detection accuracy threshold."""
        actual = report.domain_detection_metrics.accuracy
        threshold = self.config.domain_detection_accuracy
        passed = actual >= threshold

        return ThresholdResult(
            passed=passed,
            metric_name="domain_detection_accuracy",
            actual_value=actual,
            threshold_value=threshold,
            message=f"Domain Detection: {actual:.1%} (required: >= {threshold:.1%}) {'✓' if passed else '✗'}",
        )

    def _check_severity_fp_rates(self, report: CorpusMetricsReport) -> list[ThresholdResult]:
        """Check per-severity FP rate thresholds."""
        results = []

        severity_thresholds = {
            "critical": self.config.critical_fp_rate,
            "error": self.config.error_fp_rate,
            "warning": self.config.warning_fp_rate,
        }

        for sm in report.severity_metrics:
            threshold = severity_thresholds.get(sm.severity.value)
            if threshold is None:
                continue

            actual = sm.fp_rate
            passed = actual <= threshold

            results.append(
                ThresholdResult(
                    passed=passed,
                    metric_name=f"{sm.severity.value}_fp_rate",
                    actual_value=actual,
                    threshold_value=threshold,
                    message=f"{sm.severity.value.upper()} FP Rate: {actual:.1%} (required: <= {threshold:.1%}) {'✓' if passed else '✗'}",
                )
            )

        return results

    def _check_method_f1(self, report: CorpusMetricsReport) -> list[ThresholdResult]:
        """Check per-method F1 thresholds."""
        results = []

        for mm in report.method_metrics:
            threshold = self.config.per_method_f1.get(mm.category, 0.0)
            actual = mm.f1_score
            passed = actual >= threshold

            results.append(
                ThresholdResult(
                    passed=passed,
                    metric_name=f"method_{mm.category}_f1",
                    actual_value=actual,
                    threshold_value=threshold,
                    message=f"Method {mm.category} F1: {actual:.1%} (required: >= {threshold:.1%}) {'✓' if passed else '✗'}",
                )
            )

        return results

    def format_results(self, results: list[ThresholdResult]) -> str:
        """Format threshold results as human-readable text.

        Args:
            results: List of ThresholdResult.

        Returns:
            Formatted text.

        """
        lines = ["Threshold Check Results:", ""]

        for r in results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{status}] {r.message}")

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        lines.append("")
        lines.append(f"Summary: {passed}/{total} thresholds passed")

        return "\n".join(lines)
