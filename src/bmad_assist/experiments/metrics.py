"""Metrics collection and aggregation for experiment framework.

This module provides the metrics collection infrastructure for experiment runs,
including per-phase metrics collection, aggregation to run-level summaries,
and persistence to YAML files.

Usage:
    from bmad_assist.experiments import MetricsCollector, MetricsFile

    # Collect metrics from manifest
    collector = MetricsCollector(run_dir)
    metrics_file = collector.collect(manifest)
    collector.save(metrics_file)

    # Load existing metrics
    metrics = collector.load()

"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_serializer,
)

from bmad_assist.core.exceptions import ConfigError

logger = logging.getLogger(__name__)

__all__ = [
    "PhaseMetrics",
    "RunMetrics",
    "MetricsFile",
    "MetricsCollector",
]


# =============================================================================
# Metrics Data Models
# =============================================================================


class PhaseMetrics(BaseModel):
    """Metrics for a single phase execution.

    Pydantic model (not dataclass) for proper serialization when embedded
    in MetricsFile.phases list. Uses ConfigDict(frozen=True) for immutability.

    Attributes:
        phase: Workflow/phase name.
        story: Story ID if applicable.
        status: Phase outcome (completed, failed, skipped).
        duration_seconds: Phase duration in seconds.
        tokens: Total tokens used (input + output); None if not tracked.
        cost: API cost in USD; None if not tracked.
        error: Error message if failed.

    """

    model_config = ConfigDict(frozen=True)

    phase: str = Field(..., description="Workflow/phase name")
    story: str | None = Field(None, description="Story ID if applicable")
    status: Literal["completed", "failed", "skipped"] = Field(..., description="Phase outcome")
    duration_seconds: float = Field(..., description="Phase duration in seconds")
    tokens: int | None = Field(None, description="Total tokens used")
    cost: float | None = Field(None, description="API cost in USD")
    error: str | None = Field(None, description="Error message if failed")

    @classmethod
    def from_phase_result(cls, result: ManifestPhaseResult) -> PhaseMetrics:
        """Create PhaseMetrics from ManifestPhaseResult.

        Args:
            result: Phase result from manifest.

        Returns:
            PhaseMetrics instance.

        """
        return cls(
            phase=result.phase,
            story=result.story,
            status=result.status,
            duration_seconds=result.duration_seconds,
            tokens=result.tokens,
            cost=result.cost,
            error=result.error,
        )


class RunMetrics(BaseModel):
    """Aggregated metrics for an experiment run.

    All aggregates are computed from phase results. Averages use
    stories_completed as denominator, not count of phases with metrics.

    Attributes:
        total_cost: Sum of all phase costs (0.0 if all None).
        total_tokens: Sum of all phase tokens (0 if all None).
        total_duration_seconds: Sum of all phase durations.
        avg_tokens_per_phase: Average tokens per completed phase.
        avg_cost_per_phase: Average cost per completed phase.
        stories_completed: Count of completed phases.
        stories_failed: Count of failed phases.

    """

    model_config = ConfigDict(frozen=True)

    total_cost: float = Field(..., description="Sum of all phase costs")
    total_tokens: int = Field(..., description="Sum of all phase tokens")
    total_duration_seconds: float = Field(..., description="Sum of all phase durations")
    avg_tokens_per_phase: float = Field(..., description="Average tokens per completed phase")
    avg_cost_per_phase: float = Field(..., description="Average cost per completed phase")
    stories_completed: int = Field(..., description="Count of completed phases")
    stories_failed: int = Field(..., description="Count of failed phases")

    def to_manifest_metrics(self) -> ManifestMetrics:
        """Convert to ManifestMetrics for manifest update.

        Returns:
            ManifestMetrics instance with values from this RunMetrics.

        """
        # Import here to avoid circular import
        from bmad_assist.experiments.manifest import ManifestMetrics

        return ManifestMetrics(
            total_cost=self.total_cost,
            total_tokens=self.total_tokens,
            total_duration_seconds=self.total_duration_seconds,
            avg_tokens_per_phase=self.avg_tokens_per_phase,
            avg_cost_per_phase=self.avg_cost_per_phase,
        )


class MetricsFile(BaseModel):
    """Schema for metrics.yaml file.

    Contains both summary aggregates and per-phase breakdown.

    Attributes:
        run_id: Run identifier.
        collected_at: Collection timestamp.
        summary: Aggregate metrics.
        phases: Per-phase breakdown.

    """

    run_id: str = Field(..., description="Run identifier")
    collected_at: datetime = Field(..., description="Collection timestamp")
    summary: RunMetrics = Field(..., description="Aggregate metrics")
    phases: list[PhaseMetrics] = Field(..., description="Per-phase breakdown")

    @field_serializer("collected_at")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO 8601 with UTC timezone."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.isoformat()


# =============================================================================
# MetricsCollector Class
# =============================================================================


class MetricsCollector:
    """Collects and aggregates metrics from experiment runs.

    Usage:
        collector = MetricsCollector(run_dir)
        metrics_file = collector.collect(manifest)
        collector.save(metrics_file)

    """

    def __init__(self, run_dir: Path) -> None:
        """Initialize the collector.

        Args:
            run_dir: Path to the experiment run directory.

        """
        self._run_dir = run_dir
        self._metrics_path = run_dir / "metrics.yaml"

    @property
    def metrics_path(self) -> Path:
        """Return the path to the metrics file."""
        return self._metrics_path

    def collect(self, manifest: RunManifest) -> MetricsFile:
        """Collect metrics from manifest.

        Args:
            manifest: The run manifest with phase results.

        Returns:
            MetricsFile with aggregated metrics.

        """
        phases: list[PhaseMetrics] = []
        total_tokens = 0
        total_cost = 0.0
        total_duration = 0.0
        stories_completed = 0
        stories_failed = 0

        if manifest.results is not None:
            for result in manifest.results.phases:
                phase = PhaseMetrics.from_phase_result(result)
                phases.append(phase)

                # Aggregate duration (always present)
                total_duration += phase.duration_seconds

                # Aggregate tokens (skip None)
                if phase.tokens is not None:
                    total_tokens += phase.tokens

                # Aggregate cost (skip None)
                if phase.cost is not None:
                    total_cost += phase.cost

                # Count completed/failed (skip skipped)
                if phase.status == "completed":
                    stories_completed += 1
                elif phase.status == "failed":
                    stories_failed += 1

        # Calculate averages (avoid division by zero)
        avg_tokens = total_tokens / stories_completed if stories_completed > 0 else 0.0
        avg_cost = total_cost / stories_completed if stories_completed > 0 else 0.0

        summary = RunMetrics(
            total_cost=total_cost,
            total_tokens=total_tokens,
            total_duration_seconds=total_duration,
            avg_tokens_per_phase=avg_tokens,
            avg_cost_per_phase=avg_cost,
            stories_completed=stories_completed,
            stories_failed=stories_failed,
        )

        return MetricsFile(
            run_id=manifest.run_id,
            collected_at=datetime.now(UTC),
            summary=summary,
            phases=phases,
        )

    def save(self, metrics_file: MetricsFile) -> Path:
        """Save metrics to file using atomic write pattern.

        Args:
            metrics_file: Metrics to save.

        Returns:
            Path to saved file.

        Raises:
            ConfigError: If save operation fails.

        """
        temp_path = self._metrics_path.with_suffix(".yaml.tmp")

        try:
            # Ensure directory exists
            self._run_dir.mkdir(parents=True, exist_ok=True)

            # Serialize to dict
            data = metrics_file.model_dump(mode="json")

            # Write to temp file
            with temp_path.open("w", encoding="utf-8") as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    width=120,
                )

            # Atomic rename
            os.replace(temp_path, self._metrics_path)

        except Exception as e:
            # Clean up temp file on any failure
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                logger.warning("Failed to clean up temp file: %s", temp_path)
            raise ConfigError(f"Failed to save metrics: {e}") from e

        logger.info("Saved metrics to %s", self._metrics_path)
        return self._metrics_path

    def load(self) -> MetricsFile:
        """Load existing metrics file.

        Returns:
            Loaded MetricsFile.

        Raises:
            ConfigError: If file not found or invalid.

        """
        if not self._metrics_path.exists():
            raise ConfigError(f"Metrics file not found: {self._metrics_path}")

        try:
            with self._metrics_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in metrics file: {e}") from e
        except OSError as e:
            raise ConfigError(f"Cannot read metrics file: {e}") from e

        try:
            return MetricsFile.model_validate(data)
        except ValidationError as e:
            raise ConfigError(f"Metrics validation failed: {e}") from e


# Type hints for forward references (used in methods)
if TYPE_CHECKING:
    from bmad_assist.experiments.manifest import (
        ManifestMetrics,
        ManifestPhaseResult,
        RunManifest,
    )
