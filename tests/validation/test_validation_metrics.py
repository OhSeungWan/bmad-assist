"""Tests for deterministic validation metrics extraction.

Tests cover:
- Per-validator metrics extraction from markdown
- Aggregate metrics calculation
- Formatted output generation
"""

import pytest

from bmad_assist.validation.validation_metrics import (
    AggregateMetrics,
    ValidatorMetrics,
    calculate_aggregate_metrics,
    extract_validator_metrics,
    format_deterministic_metrics_header,
)


class TestExtractValidatorMetrics:
    """Tests for extract_validator_metrics function."""

    def test_extracts_issue_counts_from_table(self) -> None:
        """Extracts critical/enhancement/optimization counts from Issues Overview."""
        content = """
# Validation Report

## Executive Summary

### Issues Overview

| Category | Found |
|----------|-------|
| 🚨 Critical Issues | 4 |
| ⚡ Enhancements | 5 |
| ✨ Optimizations | 3 |
| 🤖 LLM Optimizations | 2 |
"""
        metrics = extract_validator_metrics(content, "Validator A")

        assert metrics.critical_count == 4
        assert metrics.enhancement_count == 5
        assert metrics.optimization_count == 3
        assert metrics.llm_optimization_count == 2
        assert metrics.total_findings == 14

    def test_extracts_score_from_table(self) -> None:
        """Extracts final score from verdict table."""
        content = """
| Final Score | Verdict |
|-------------|---------|
| **6/10** | **MAJOR REWORK** |
"""
        metrics = extract_validator_metrics(content, "Validator A")

        assert metrics.final_score == 6.0

    def test_extracts_decimal_score(self) -> None:
        """Extracts decimal scores like 8.2/10."""
        content = """
### Final Score: 8.2/10
"""
        metrics = extract_validator_metrics(content, "Validator A")

        assert metrics.final_score == 8.2

    def test_extracts_verdict(self) -> None:
        """Extracts verdict from table."""
        content = """
| Final Score | Verdict |
|-------------|---------|
| **6/10** | **MAJOR REWORK** |
"""
        metrics = extract_validator_metrics(content, "Validator A")

        assert metrics.verdict == "MAJOR REWORK"

    def test_counts_invest_violations(self) -> None:
        """Counts bullet points in INVEST Violations section."""
        content = """
### INVEST Violations

- **[5/10] Independent:** CTA target is not fully specified
- **[4/10] Negotiable:** Overly prescriptive about implementation
- **[4/10] Estimable:** Scope boundary is blurred

### Acceptance Criteria Issues
"""
        metrics = extract_validator_metrics(content, "Validator A")

        assert metrics.invest_violations == 3

    def test_handles_missing_sections(self) -> None:
        """Returns zeros for missing sections."""
        content = "# Empty report"
        metrics = extract_validator_metrics(content, "Validator A")

        assert metrics.critical_count == 0
        assert metrics.enhancement_count == 0
        assert metrics.final_score is None
        assert metrics.verdict is None

    def test_preserves_validator_id(self) -> None:
        """Preserves validator ID in output."""
        metrics = extract_validator_metrics("", "Validator B")
        assert metrics.validator_id == "Validator B"


class TestCalculateAggregateMetrics:
    """Tests for calculate_aggregate_metrics function."""

    def test_calculates_score_statistics(self) -> None:
        """Calculates min/max/avg/stdev for scores."""
        validators = [
            ValidatorMetrics("A", final_score=6.0),
            ValidatorMetrics("B", final_score=8.0),
            ValidatorMetrics("C", final_score=9.0),
        ]

        aggregate = calculate_aggregate_metrics(validators)

        assert aggregate.score_min == 6.0
        assert aggregate.score_max == 9.0
        assert abs(aggregate.score_avg - 7.67) < 0.1  # type: ignore[operator]
        assert aggregate.score_stdev is not None

    def test_sums_category_totals(self) -> None:
        """Sums findings across all validators."""
        validators = [
            ValidatorMetrics("A", critical_count=4, enhancement_count=5),
            ValidatorMetrics("B", critical_count=2, enhancement_count=3),
        ]

        aggregate = calculate_aggregate_metrics(validators)

        assert aggregate.total_critical == 6
        assert aggregate.total_enhancement == 8
        assert aggregate.total_findings == 14

    def test_counts_validators_with_findings(self) -> None:
        """Counts how many validators found issues in each category."""
        validators = [
            ValidatorMetrics("A", critical_count=4),
            ValidatorMetrics("B", critical_count=0),
            ValidatorMetrics("C", critical_count=2),
        ]

        aggregate = calculate_aggregate_metrics(validators)

        assert aggregate.validators_with_critical == 2

    def test_handles_empty_list(self) -> None:
        """Returns empty aggregate for no validators."""
        aggregate = calculate_aggregate_metrics([])

        assert aggregate.validator_count == 0
        assert aggregate.score_avg is None

    def test_handles_single_validator(self) -> None:
        """Handles single validator (no stdev possible)."""
        validators = [ValidatorMetrics("A", final_score=7.0)]

        aggregate = calculate_aggregate_metrics(validators)

        assert aggregate.validator_count == 1
        assert aggregate.score_avg == 7.0
        assert aggregate.score_stdev is None


class TestFormatDeterministicMetricsHeader:
    """Tests for format_deterministic_metrics_header function."""

    def test_includes_markers(self) -> None:
        """Output includes start/end markers."""
        aggregate = AggregateMetrics(validator_count=2)
        header = format_deterministic_metrics_header(aggregate)

        assert "<!-- DETERMINISTIC_METRICS_START -->" in header
        assert "<!-- DETERMINISTIC_METRICS_END -->" in header

    def test_includes_summary_table(self) -> None:
        """Output includes summary table with validator count."""
        aggregate = AggregateMetrics(
            validator_count=4,
            score_avg=7.5,
            total_findings=12,
        )
        header = format_deterministic_metrics_header(aggregate)

        assert "| Validators | 4 |" in header
        assert "7.5/10" in header
        assert "| Total findings | 12 |" in header

    def test_includes_category_breakdown(self) -> None:
        """Output includes findings by category table."""
        aggregate = AggregateMetrics(
            validator_count=3,
            total_critical=6,
            validators_with_critical=2,
        )
        header = format_deterministic_metrics_header(aggregate)

        assert "| 🚨 Critical | 6 | 2/3 |" in header

    def test_includes_per_validator_breakdown(self) -> None:
        """Output includes per-validator table."""
        validators = [
            ValidatorMetrics("Validator A", critical_count=4, final_score=6.0),
            ValidatorMetrics("Validator B", critical_count=2, final_score=8.0),
        ]
        aggregate = calculate_aggregate_metrics(validators)
        header = format_deterministic_metrics_header(aggregate)

        assert "| Validator A | 6.0 | 4 |" in header
        assert "| Validator B | 8.0 | 2 |" in header


class TestIntegration:
    """Integration tests with real validation report content."""

    def test_full_extraction_pipeline(self) -> None:
        """Tests full extraction from realistic content."""
        content_a = """
# 🎯 Story Context Validation Report

## Executive Summary

### 🎯 Story Quality Verdict

| Final Score | Verdict |
|-------------|---------|
| **6/10** | **MAJOR REWORK** |

### Issues Overview

| Category | Found |
|----------|-------|
| 🚨 Critical Issues | 4 |
| ⚡ Enhancements | 5 |
| ✨ Optimizations | 3 |
| 🤖 LLM Optimizations | 3 |

### INVEST Violations

- **[5/10] Independent:** Issue 1
- **[4/10] Negotiable:** Issue 2
"""
        content_b = """
# 🎯 Story Context Validation Report

## Executive Summary

### 🎯 Story Quality Verdict

| Final Score | Verdict |
|-------------|---------|
| **8/10** | **APPROVED** |

### Issues Overview

| Category | Found |
|----------|-------|
| 🚨 Critical Issues | 0 |
| ⚡ Enhancements | 3 |
| ✨ Optimizations | 2 |
| 🤖 LLM Optimizations | 4 |
"""
        # Extract individual metrics
        metrics_a = extract_validator_metrics(content_a, "Validator A")
        metrics_b = extract_validator_metrics(content_b, "Validator B")

        assert metrics_a.final_score == 6.0
        assert metrics_a.critical_count == 4
        assert metrics_a.invest_violations == 2

        assert metrics_b.final_score == 8.0
        assert metrics_b.critical_count == 0

        # Calculate aggregate
        aggregate = calculate_aggregate_metrics([metrics_a, metrics_b])

        assert aggregate.validator_count == 2
        assert aggregate.score_avg == 7.0
        assert aggregate.total_critical == 4
        assert aggregate.validators_with_critical == 1

        # Format header
        header = format_deterministic_metrics_header(aggregate)

        assert "## Validation Metrics (Deterministic)" in header
        assert "| Validators | 2 |" in header
        assert "| 🚨 Critical | 4 | 1/2 |" in header
