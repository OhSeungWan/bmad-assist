"""Benchmarking module for LLM evaluation metrics.

Provides Pydantic models and utilities for collecting, storing,
and analyzing multi-LLM validation metrics.

Public API:
    MetricSource: Enum for field provenance annotation
    EvaluatorRole: Enum for evaluator role classification
    BenchmarkingError: Exception class for benchmarking errors
    source_field: Helper function for creating annotated fields
    LLMEvaluationRecord: Root model for complete evaluation record
    WorkflowInfo: Workflow identification
    StoryInfo: Story metadata
    EvaluatorInfo: Evaluator identification
    ExecutionTelemetry: Timing and resource metrics
    OutputAnalysis: Output structure analysis
    FindingsExtracted: Extracted findings counts
    ReasoningPatterns: Reasoning quality analysis
    LinguisticFingerprint: Linguistic characteristics
    QualitySignals: Quality assessment
    ConsensusData: Cross-evaluator agreement
    GroundTruth: Post-hoc feedback
    EnvironmentInfo: System environment
    PatchInfo: Patch metadata
    Amendment: Ground truth amendment

    Collector (Story 13.2):
    collect_deterministic_metrics: Main entry point for deterministic metrics
    calculate_structure_metrics: Structural analysis
    calculate_linguistic_metrics: Linguistic analysis
    calculate_reasoning_signals: Reasoning pattern detection
    CollectorContext: Context dataclass for collection
    DeterministicMetrics: Result dataclass
    StructureMetrics: Structure metrics dataclass
    LinguisticMetrics: Linguistic metrics dataclass
    ReasoningSignals: Reasoning signals dataclass

    Extraction (Story 13.3):
    extract_metrics: Sync wrapper for LLM-based metrics extraction
    extract_metrics_async: Async primary API for parallel execution
    ExtractionContext: Context dataclass for extraction
    ExtractedMetrics: Result dataclass with all LLM-extracted fields
    MetricsExtractionError: Exception for extraction failures
"""

from bmad_assist.benchmarking.collector import (
    CollectorContext,
    DeterministicMetrics,
    LinguisticMetrics,
    ReasoningSignals,
    StructureMetrics,
    calculate_linguistic_metrics,
    calculate_reasoning_signals,
    calculate_structure_metrics,
    collect_deterministic_metrics,
)
from bmad_assist.benchmarking.extraction import (
    ExtractedMetrics,
    ExtractionContext,
    MetricsExtractionError,
    extract_metrics,
    extract_metrics_async,
)
from bmad_assist.benchmarking.ground_truth import (
    CodeReviewFinding,
    GroundTruthError,
    GroundTruthUpdate,
    ValidationFinding,
    amend_ground_truth,
    calculate_precision_recall,
    populate_ground_truth,
)
from bmad_assist.benchmarking.reports import (
    ComparisonResult,
    MetricComparison,
    ModelComparisonResult,
    ModelMetrics,
    ModelTendencies,
    # Story 13.9: Model Comparison
    SeverityDistribution,
    VariantMetrics,
    compare_models,
    compare_workflow_variants,
    generate_comparison_report,
    generate_model_report_json,
    generate_model_report_markdown,
)
from bmad_assist.benchmarking.schema import (
    Amendment,
    BenchmarkingError,
    ConsensusData,
    EnvironmentInfo,
    EvaluatorInfo,
    EvaluatorRole,
    ExecutionTelemetry,
    FindingsExtracted,
    GroundTruth,
    LinguisticFingerprint,
    LLMEvaluationRecord,
    MetricSource,
    OutputAnalysis,
    PatchInfo,
    QualitySignals,
    ReasoningPatterns,
    StoryInfo,
    WorkflowInfo,
    source_field,
)
from bmad_assist.benchmarking.storage import (
    RecordFilters,
    RecordSummary,
    StorageError,
    get_records_for_story,
    list_evaluation_records,
    load_evaluation_record,
    save_evaluation_record,
)

__all__ = [
    # Enums
    "MetricSource",
    "EvaluatorRole",
    # Exception
    "BenchmarkingError",
    # Helper function
    "source_field",
    # Models - Core
    "PatchInfo",
    "WorkflowInfo",
    "StoryInfo",
    "EvaluatorInfo",
    # Models - Telemetry and Output
    "ExecutionTelemetry",
    "OutputAnalysis",
    "FindingsExtracted",
    # Models - Quality and Patterns
    "ReasoningPatterns",
    "LinguisticFingerprint",
    "QualitySignals",
    # Models - Consensus and Ground Truth
    "ConsensusData",
    "Amendment",
    "GroundTruth",
    # Models - Environment
    "EnvironmentInfo",
    # Root Model
    "LLMEvaluationRecord",
    # Collector (Story 13.2)
    "collect_deterministic_metrics",
    "calculate_structure_metrics",
    "calculate_linguistic_metrics",
    "calculate_reasoning_signals",
    "CollectorContext",
    "DeterministicMetrics",
    "StructureMetrics",
    "LinguisticMetrics",
    "ReasoningSignals",
    # Extraction (Story 13.3)
    "extract_metrics",
    "extract_metrics_async",
    "ExtractionContext",
    "ExtractedMetrics",
    "MetricsExtractionError",
    # Storage (Story 13.5)
    "save_evaluation_record",
    "load_evaluation_record",
    "list_evaluation_records",
    "get_records_for_story",
    "RecordFilters",
    "RecordSummary",
    "StorageError",
    # Ground Truth (Story 13.7)
    "populate_ground_truth",
    "amend_ground_truth",
    "calculate_precision_recall",
    "CodeReviewFinding",
    "ValidationFinding",
    "GroundTruthUpdate",
    "GroundTruthError",
    # Reports (Story 13.8)
    "compare_workflow_variants",
    "generate_comparison_report",
    "ComparisonResult",
    "VariantMetrics",
    "MetricComparison",
    # Reports (Story 13.9)
    "compare_models",
    "generate_model_report_markdown",
    "generate_model_report_json",
    "ModelComparisonResult",
    "ModelMetrics",
    "SeverityDistribution",
    "ModelTendencies",
]
