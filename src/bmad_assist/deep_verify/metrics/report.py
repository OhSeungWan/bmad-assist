"""Report formatting for Deep Verify benchmarks.

This module provides formatters for benchmark reports in multiple formats:
text (human-readable), JSON (machine-readable), and YAML.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from bmad_assist.deep_verify.metrics.collector import CorpusMetricsReport


class ReportFormatter:
    """Formatter for benchmark reports."""

    def __init__(self, report: CorpusMetricsReport) -> None:
        """Initialize with a metrics report.

        Args:
            report: CorpusMetricsReport to format.

        """
        self.report = report

    def format_text(self) -> str:
        """Format report as human-readable text.

        Returns:
            Formatted text report.

        """
        lines = [
            "=" * 60,
            "Deep Verify Benchmark Report",
            "=" * 60,
            "",
            "Corpus: tests/deep_verify/corpus",
            f"Artifacts evaluated: {self.report.summary.total_artifacts}",
            f"Duration: {self.report.summary.duration_seconds:.1f}s",
            "",
            "Overall Metrics:",
            f"  Precision: {self.report.summary.overall_precision:.1%}",
            f"  Recall: {self.report.summary.overall_recall:.1%}",
            f"  F1 Score: {self.report.summary.overall_f1:.1%}",
            "",
        ]

        # Per-method metrics
        if self.report.method_metrics:
            lines.extend(["Per-Method F1 Scores:", ""])
            for mm in sorted(self.report.method_metrics, key=lambda x: x.f1_score, reverse=True):
                lines.append(f"  {mm.category}: {mm.f1_score:.1%}")
            lines.append("")

        # Per-severity FP rates
        if self.report.severity_metrics:
            lines.extend(["Per-Severity FP Rates:", ""])
            targets = {
                "critical": "<1%",
                "error": "<5%",
                "warning": "<15%",
                "info": "N/A",
            }
            for sm in self.report.severity_metrics:
                target = targets.get(sm.severity.value, "N/A")
                status = "✓" if sm.meets_target else "✗"
                lines.append(
                    f"  {sm.severity.value.upper()}: {sm.fp_rate:.1%} (target: {target}) {status}"
                )
            lines.append("")

        # Domain detection
        if self.report.domain_detection_metrics:
            ddm = self.report.domain_detection_metrics
            lines.extend(
                [
                    "Domain Detection Accuracy:",
                    f"  Accuracy: {ddm.accuracy:.1%} (target: >90%)",
                    f"  Correct: {ddm.correct_domains}/{ddm.total_artifacts}",
                    f"  Partial: {ddm.partial_domains}/{ddm.total_artifacts}",
                    f"  Incorrect: {ddm.incorrect_domains}/{ddm.total_artifacts}",
                    "",
                ]
            )

        lines.append("=" * 60)

        return "\n".join(lines)

    def format_json(self) -> str:
        """Format report as JSON.

        Returns:
            JSON-formatted report.

        """
        return json.dumps(self.report.to_dict(), indent=2)

    def format_yaml(self) -> str:
        """Format report as YAML.

        Returns:
            YAML-formatted report.

        """
        return yaml.dump(self.report.to_dict(), default_flow_style=False, sort_keys=False)

    def format(self, format_type: str) -> str:
        """Format report in specified format.

        Args:
            format_type: One of "text", "json", "yaml".

        Returns:
            Formatted report string.

        Raises:
            ValueError: If format_type is invalid.

        """
        formatters = {
            "text": self.format_text,
            "json": self.format_json,
            "yaml": self.format_yaml,
        }

        if format_type not in formatters:
            raise ValueError(f"Unknown format: {format_type}. Use: text, json, yaml")

        return formatters[format_type]()

    def save(self, output_path: Path, format_type: str | None = None) -> None:
        """Save report to file.

        Args:
            output_path: Path to save report.
            format_type: Format type. If None, inferred from extension.

        """
        if format_type is None:
            # Infer from extension
            ext = output_path.suffix.lower()
            if ext == ".json":
                format_type = "json"
            elif ext in (".yml", ".yaml"):
                format_type = "yaml"
            else:
                format_type = "text"

        content = self.format(format_type)

        with open(output_path, "w") as f:
            f.write(content)
