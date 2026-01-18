"""Deterministic metrics extraction from validation reports.

This module provides functions for extracting reproducible metrics from
Multi-LLM validation report markdown files. These metrics are calculated
deterministically via regex parsing, not LLM judgment.

Key features:
- Extract per-validator counts (critical/enhancement/optimization issues)
- Extract final scores from validation reports
- Calculate aggregate statistics across all validators
- Format metrics as markdown header for synthesis reports

Public API:
    extract_validator_metrics: Parse single validation report
    calculate_aggregate_metrics: Aggregate across multiple validators
    format_deterministic_metrics_header: Format for synthesis report prepend
    ValidatorMetrics: Per-validator metrics dataclass
    AggregateMetrics: Cross-validator aggregate metrics dataclass
"""

from __future__ import annotations

import logging
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# Regex Patterns for Validation Report Parsing
# =============================================================================

# Issue counts from the "Issues Overview" table
# | 🚨 Critical Issues | 4 |
CRITICAL_PATTERN = re.compile(r"\|\s*🚨\s*Critical Issues\s*\|\s*(\d+)\s*\|", re.IGNORECASE)
ENHANCEMENT_PATTERN = re.compile(r"\|\s*⚡\s*Enhancements?\s*\|\s*(\d+)\s*\|", re.IGNORECASE)
OPTIMIZATION_PATTERN = re.compile(r"\|\s*✨\s*Optimizations?\s*\|\s*(\d+)\s*\|", re.IGNORECASE)
LLM_OPTIMIZATION_PATTERN = re.compile(
    r"\|\s*🤖\s*LLM Optimizations?\s*\|\s*(\d+)\s*\|", re.IGNORECASE
)

# Final score from table or heading
# | **6/10** | **MAJOR REWORK** |
# ### Final Score: 8.2/10
SCORE_TABLE_PATTERN = re.compile(r"\|\s*\*?\*?(\d+(?:\.\d+)?)/10\*?\*?\s*\|", re.IGNORECASE)
SCORE_HEADING_PATTERN = re.compile(r"###?\s*Final Score:?\s*(\d+(?:\.\d+)?)/10", re.IGNORECASE)

# Verdict from table
# | **6/10** | **MAJOR REWORK** |
VERDICT_PATTERN = re.compile(
    r"\|\s*\*?\*?\d+(?:\.\d+)?/10\*?\*?\s*\|\s*\*?\*?([A-Z\s]+)\*?\*?\s*\|", re.IGNORECASE
)

# INVEST violations count
INVEST_VIOLATION_PATTERN = re.compile(r"###\s*INVEST Violations", re.IGNORECASE)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass(frozen=True)
class ValidatorMetrics:
    """Metrics extracted from a single validation report.

    All counts are from the Issues Overview table.
    Score is the Final Score (0-10 scale).
    """

    validator_id: str
    critical_count: int = 0
    enhancement_count: int = 0
    optimization_count: int = 0
    llm_optimization_count: int = 0
    final_score: float | None = None
    verdict: str | None = None
    invest_violations: int = 0

    @property
    def total_findings(self) -> int:
        """Total findings across all categories."""
        return (
            self.critical_count
            + self.enhancement_count
            + self.optimization_count
            + self.llm_optimization_count
        )


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all validators.

    Provides statistics and consensus indicators.
    """

    validator_count: int = 0
    validators: list[ValidatorMetrics] = field(default_factory=list)

    # Score statistics
    score_min: float | None = None
    score_max: float | None = None
    score_avg: float | None = None
    score_stdev: float | None = None

    # Category totals across all validators
    total_critical: int = 0
    total_enhancement: int = 0
    total_optimization: int = 0
    total_llm_optimization: int = 0
    total_findings: int = 0

    # Consensus indicators (how many validators found issues in each category)
    validators_with_critical: int = 0
    validators_with_enhancement: int = 0
    validators_with_optimization: int = 0

    # Verdicts
    verdicts: list[str] = field(default_factory=list)


# =============================================================================
# Extraction Functions
# =============================================================================


def extract_validator_metrics(
    content: str,
    validator_id: str,
) -> ValidatorMetrics:
    """Extract metrics from a single validation report.

    Parses the markdown content of a validation report to extract:
    - Issue counts from the Issues Overview table
    - Final score
    - Verdict
    - INVEST violations count

    Args:
        content: Markdown content of validation report.
        validator_id: Identifier for this validator (e.g., "Validator A").

    Returns:
        ValidatorMetrics with extracted values.
        Missing values default to 0 or None.

    """
    # Extract issue counts
    critical = _extract_int(CRITICAL_PATTERN, content)
    enhancement = _extract_int(ENHANCEMENT_PATTERN, content)
    optimization = _extract_int(OPTIMIZATION_PATTERN, content)
    llm_opt = _extract_int(LLM_OPTIMIZATION_PATTERN, content)

    # Extract score (try table first, then heading)
    score = _extract_float(SCORE_TABLE_PATTERN, content)
    if score is None:
        score = _extract_float(SCORE_HEADING_PATTERN, content)

    # Extract verdict
    verdict_match = VERDICT_PATTERN.search(content)
    verdict = verdict_match.group(1).strip() if verdict_match else None

    # Count INVEST violations (count bullet points after "### INVEST Violations")
    invest_violations = _count_invest_violations(content)

    return ValidatorMetrics(
        validator_id=validator_id,
        critical_count=critical,
        enhancement_count=enhancement,
        optimization_count=optimization,
        llm_optimization_count=llm_opt,
        final_score=score,
        verdict=verdict,
        invest_violations=invest_violations,
    )


def _extract_int(pattern: re.Pattern[str], content: str) -> int:
    """Extract integer from regex match, return 0 if not found."""
    match = pattern.search(content)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, IndexError):
            pass
    return 0


def _extract_float(pattern: re.Pattern[str], content: str) -> float | None:
    """Extract float from regex match, return None if not found."""
    match = pattern.search(content)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, IndexError):
            pass
    return None


def _count_invest_violations(content: str) -> int:
    """Count INVEST violation bullet points."""
    # Find "### INVEST Violations" section
    match = INVEST_VIOLATION_PATTERN.search(content)
    if not match:
        return 0

    # Get content after the heading until next section
    start = match.end()
    next_section = re.search(r"\n###?\s+", content[start:])
    if next_section:
        section_content = content[start : start + next_section.start()]
    else:
        section_content = content[start:]

    # Count lines starting with "- " (bullet points)
    violations = re.findall(r"^-\s+", section_content, re.MULTILINE)
    return len(violations)


# =============================================================================
# Aggregation Functions
# =============================================================================


def calculate_aggregate_metrics(
    validators: list[ValidatorMetrics],
) -> AggregateMetrics:
    """Calculate aggregate metrics across multiple validators.

    Computes:
    - Score statistics (min, max, avg, stdev)
    - Category totals
    - Consensus indicators

    Args:
        validators: List of ValidatorMetrics from each validator.

    Returns:
        AggregateMetrics with computed statistics.

    """
    if not validators:
        return AggregateMetrics()

    # Collect scores (excluding None)
    scores = [v.final_score for v in validators if v.final_score is not None]

    # Calculate score statistics
    score_min = min(scores) if scores else None
    score_max = max(scores) if scores else None
    score_avg = statistics.mean(scores) if scores else None
    score_stdev = statistics.stdev(scores) if len(scores) >= 2 else None

    # Sum category totals
    total_critical = sum(v.critical_count for v in validators)
    total_enhancement = sum(v.enhancement_count for v in validators)
    total_optimization = sum(v.optimization_count for v in validators)
    total_llm_optimization = sum(v.llm_optimization_count for v in validators)
    total_findings = sum(v.total_findings for v in validators)

    # Count validators with findings in each category
    validators_with_critical = sum(1 for v in validators if v.critical_count > 0)
    validators_with_enhancement = sum(1 for v in validators if v.enhancement_count > 0)
    validators_with_optimization = sum(1 for v in validators if v.optimization_count > 0)

    # Collect verdicts
    verdicts = [v.verdict for v in validators if v.verdict]

    return AggregateMetrics(
        validator_count=len(validators),
        validators=validators,
        score_min=score_min,
        score_max=score_max,
        score_avg=score_avg,
        score_stdev=score_stdev,
        total_critical=total_critical,
        total_enhancement=total_enhancement,
        total_optimization=total_optimization,
        total_llm_optimization=total_llm_optimization,
        total_findings=total_findings,
        validators_with_critical=validators_with_critical,
        validators_with_enhancement=validators_with_enhancement,
        validators_with_optimization=validators_with_optimization,
        verdicts=verdicts,
    )


# =============================================================================
# Formatting Functions
# =============================================================================


def format_deterministic_metrics_header(
    aggregate: AggregateMetrics,
) -> str:
    """Format aggregate metrics as markdown header for synthesis report.

    Creates a structured markdown section to prepend to synthesis output.
    This provides deterministic metrics calculated from validation reports.

    Args:
        aggregate: AggregateMetrics to format.

    Returns:
        Markdown string with formatted metrics.

    """
    lines = [
        "<!-- DETERMINISTIC_METRICS_START -->",
        "## Validation Metrics (Deterministic)",
        "",
        "These metrics are calculated deterministically from validator reports.",
        "",
        "### Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Validators | {aggregate.validator_count} |",
    ]

    # Score statistics
    if aggregate.score_avg is not None:
        lines.append(f"| Score (avg) | {aggregate.score_avg:.1f}/10 |")
    if aggregate.score_min is not None and aggregate.score_max is not None:
        lines.append(f"| Score (range) | {aggregate.score_min:.1f} - {aggregate.score_max:.1f} |")
    if aggregate.score_stdev is not None:
        lines.append(f"| Score (stdev) | {aggregate.score_stdev:.2f} |")

    # Helper for category rows
    vc = aggregate.validator_count
    crit = f"{aggregate.validators_with_critical}/{vc}"
    enh = f"{aggregate.validators_with_enhancement}/{vc}"
    opt = f"{aggregate.validators_with_optimization}/{vc}"

    lines.extend(
        [
            f"| Total findings | {aggregate.total_findings} |",
            "",
            "### Findings by Category",
            "",
            "| Category | Total | Validators Reporting |",
            "|----------|-------|---------------------|",
            f"| 🚨 Critical | {aggregate.total_critical} | {crit} |",
            f"| ⚡ Enhancement | {aggregate.total_enhancement} | {enh} |",
            f"| ✨ Optimization | {aggregate.total_optimization} | {opt} |",
            f"| 🤖 LLM Optimization | {aggregate.total_llm_optimization} | - |",
            "",
            "### Per-Validator Breakdown",
            "",
            "| Validator | Score | Critical | Enhancement | Optimization | LLM Opt | Total |",
            "|-----------|-------|----------|-------------|--------------|---------|-------|",
        ]
    )

    for v in aggregate.validators:
        score_str = f"{v.final_score:.1f}" if v.final_score is not None else "-"
        lines.append(
            f"| {v.validator_id} | {score_str} | {v.critical_count} | "
            f"{v.enhancement_count} | {v.optimization_count} | "
            f"{v.llm_optimization_count} | {v.total_findings} |"
        )

    # Verdicts summary
    if aggregate.verdicts:
        lines.extend(
            [
                "",
                "### Verdicts",
                "",
            ]
        )
        for i, verdict in enumerate(aggregate.verdicts):
            if i < len(aggregate.validators):
                vid = aggregate.validators[i].validator_id
            else:
                vid = f"Validator {i + 1}"
            lines.append(f"- **{vid}**: {verdict}")

    lines.extend(
        [
            "",
            "<!-- DETERMINISTIC_METRICS_END -->",
            "",
            "",  # Extra blank line for separation from synthesis content
        ]
    )

    return "\n".join(lines)


def extract_metrics_from_validation_files(
    validation_files: list[Path],
) -> AggregateMetrics:
    """Extract and aggregate metrics from validation report files.

    Convenience function that reads files, extracts per-validator metrics,
    and computes aggregate statistics.

    Args:
        validation_files: List of paths to validation report markdown files.

    Returns:
        AggregateMetrics with all computed statistics.

    """
    validators: list[ValidatorMetrics] = []

    for file_path in validation_files:
        try:
            content = file_path.read_text(encoding="utf-8")

            # Extract validator ID from filename or content
            # New format: validation-{epic}-{story}-{role_id}-{timestamp}.md
            # where role_id is single letter (a, b, c...)
            # Legacy format: validation-{epic}-{story}-{validator_id}-{timestamp}.md
            parts = file_path.stem.split("-")
            if len(parts) >= 4:
                raw_id = "-".join(parts[3:-1]) if len(parts) > 4 else parts[3]
                # Check if it's new format (single letter)
                if len(raw_id) == 1 and raw_id.isalpha():
                    # Convert single letter to display format: "a" -> "Validator A"
                    validator_id = f"Validator {raw_id.upper()}"
                else:
                    # Legacy format: "validator-a" -> "Validator A"
                    validator_id = raw_id.replace("-", " ").title()
            else:
                validator_id = file_path.stem

            metrics = extract_validator_metrics(content, validator_id)
            validators.append(metrics)

            logger.debug(
                "Extracted metrics from %s: score=%s, critical=%d, total=%d",
                file_path.name,
                metrics.final_score,
                metrics.critical_count,
                metrics.total_findings,
            )

        except Exception as e:
            logger.warning("Failed to extract metrics from %s: %s", file_path, e)

    return calculate_aggregate_metrics(validators)
