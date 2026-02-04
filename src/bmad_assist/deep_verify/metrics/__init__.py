"""Deep Verify metrics collection and benchmarking module.

This module provides the infrastructure for:
- Test corpus management (labeled artifacts, golden tests)
- Metrics collection (precision, recall, F1, false positive rates)
- Benchmark execution and reporting
- CI integration with threshold checking
"""

from bmad_assist.deep_verify.metrics.collector import (
    ArtifactMetrics,
    CategoryMetrics,
    CorpusMetricsReport,
    DomainDetectionMetrics,
    ExpectedFinding,
    MetricsCollector,
    MetricsSummary,
    SeverityMetrics,
)
from bmad_assist.deep_verify.metrics.corpus_loader import (
    ArtifactLabel,
    CorpusLoader,
    CorpusManifest,
    GoldenCase,
)
from bmad_assist.deep_verify.metrics.report import ReportFormatter
from bmad_assist.deep_verify.metrics.threshold import ThresholdChecker

__all__ = [
    # Collector types
    "ArtifactMetrics",
    "CategoryMetrics",
    "CorpusMetricsReport",
    "DomainDetectionMetrics",
    "ExpectedFinding",
    "MetricsCollector",
    "MetricsSummary",
    "SeverityMetrics",
    # Corpus loader types
    "ArtifactLabel",
    "CorpusLoader",
    "CorpusManifest",
    "GoldenCase",
    # Report and threshold
    "ReportFormatter",
    "ThresholdChecker",
]
