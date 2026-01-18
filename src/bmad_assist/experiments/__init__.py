"""Experiment framework for systematic LLM comparison.

This module provides infrastructure for running controlled, reproducible
experiments comparing LLM models, workflow variants, and configurations.

Usage:
    from bmad_assist.experiments import ConfigTemplate, ConfigRegistry, load_config_template
    from bmad_assist.experiments import LoopTemplate, LoopRegistry, load_loop_template
    from bmad_assist.experiments import PatchSetManifest, PatchSetRegistry, load_patchset_manifest
    from bmad_assist.experiments import FixtureEntry, FixtureManager

    # Load a single config template
    template = load_config_template(Path("experiments/configs/opus-solo.yaml"))

    # Use registry for discovery
    registry = ConfigRegistry(Path("experiments/configs"))
    available = registry.list()
    template = registry.get("opus-solo")

    # Load a loop template
    loop = load_loop_template(Path("experiments/loops/standard.yaml"))

    # Use registry for loop discovery
    loop_registry = LoopRegistry(Path("experiments/loops"))
    loops = loop_registry.list()
    loop = loop_registry.get("standard")

    # Load a patch-set manifest
    patchset = load_patchset_manifest(Path("experiments/patch-sets/baseline.yaml"))

    # Use registry for patch-set discovery
    patchset_registry = PatchSetRegistry(Path("experiments/patch-sets"))
    patchsets = patchset_registry.list()
    patchset = patchset_registry.get("baseline")

    # Discover fixtures from directory (auto-discovery, no registry.yaml needed)
    fixture_manager = FixtureManager(Path("experiments/fixtures"))
    fixtures = fixture_manager.list()
    fixture = fixture_manager.get("auth-service")
    fixture_path = fixture_manager.get_path("auth-service")

    # Filter fixtures (if metadata in .bmad-assist.yaml)
    quick_fixtures = fixture_manager.filter_by_tags(["quick"])
    easy_fixtures = fixture_manager.filter_by_difficulty("easy")

"""

from bmad_assist.experiments.comparison import (
    COMPARISON_METRICS,
    MAX_COMPARISON_RUNS,
    METRIC_DISPLAY_NAMES,
    ComparisonDiff,
    ComparisonGenerator,
    ComparisonReport,
    ConfigDiff,
    MetricComparison,
    RunComparison,
)
from bmad_assist.experiments.config import (
    KNOWN_PROVIDERS,
    ConfigRegistry,
    ConfigTemplate,
    ConfigTemplateProviders,
    load_config_template,
)
from bmad_assist.experiments.fixture import (
    COST_PATTERN,
    FixtureEntry,
    FixtureManager,
    FixtureRegistryManager,  # Deprecated alias for FixtureManager
    discover_fixtures,
    load_fixture_registry,  # Deprecated
    parse_cost,
)
from bmad_assist.experiments.isolation import (
    DEFAULT_TIMEOUT_SECONDS,
    PROGRESS_BYTES_INTERVAL,
    PROGRESS_FILES_INTERVAL,
    SKIP_DIRS,
    SKIP_EXTENSIONS,
    FixtureIsolator,
    IsolationResult,
)
from bmad_assist.experiments.loop import (
    KNOWN_WORKFLOWS,
    LoopRegistry,
    LoopStep,
    LoopTemplate,
    load_loop_template,
)
from bmad_assist.experiments.manifest import (
    TERMINAL_STATUSES,
    ManifestInput,
    ManifestManager,
    ManifestMetrics,
    ManifestPhaseResult,
    ManifestResolved,
    ManifestResults,
    ResolvedConfig,
    ResolvedFixture,
    ResolvedLoop,
    ResolvedPatchSet,
    RunManifest,
    build_resolved_config,
    build_resolved_fixture,
    build_resolved_loop,
    build_resolved_patchset,
)
from bmad_assist.experiments.metrics import (
    MetricsCollector,
    MetricsFile,
    PhaseMetrics,
    RunMetrics,
)
from bmad_assist.experiments.patchset import (
    PatchSetManifest,
    PatchSetRegistry,
    load_patchset_manifest,
)
from bmad_assist.experiments.prepare import (
    BenchmarkPreparer,
    PrepareResult,
    RunData,
)
from bmad_assist.experiments.runner import (
    ExperimentInput,
    ExperimentOutput,
    ExperimentRunner,
    ExperimentStatus,
)

__all__ = [
    # Config templates
    "ConfigRegistry",
    "ConfigTemplate",
    "ConfigTemplateProviders",
    "KNOWN_PROVIDERS",
    "load_config_template",
    # Loop templates
    "KNOWN_WORKFLOWS",
    "LoopRegistry",
    "LoopStep",
    "LoopTemplate",
    "load_loop_template",
    # Patch-set manifests
    "PatchSetManifest",
    "PatchSetRegistry",
    "load_patchset_manifest",
    # Fixture discovery
    "COST_PATTERN",
    "FixtureEntry",
    "FixtureManager",
    "FixtureRegistryManager",  # Deprecated alias
    "discover_fixtures",
    "load_fixture_registry",  # Deprecated
    "parse_cost",
    # Fixture isolation
    "DEFAULT_TIMEOUT_SECONDS",
    "FixtureIsolator",
    "IsolationResult",
    "PROGRESS_BYTES_INTERVAL",
    "PROGRESS_FILES_INTERVAL",
    "SKIP_DIRS",
    "SKIP_EXTENSIONS",
    # Experiment runner
    "ExperimentInput",
    "ExperimentOutput",
    "ExperimentRunner",
    "ExperimentStatus",
    # Run manifest
    "ManifestInput",
    "ManifestManager",
    "ManifestMetrics",
    "ManifestPhaseResult",
    "ManifestResolved",
    "ManifestResults",
    "ResolvedConfig",
    "ResolvedFixture",
    "ResolvedLoop",
    "ResolvedPatchSet",
    "RunManifest",
    "TERMINAL_STATUSES",
    "build_resolved_config",
    "build_resolved_fixture",
    "build_resolved_loop",
    "build_resolved_patchset",
    # Metrics
    "MetricsCollector",
    "MetricsFile",
    "PhaseMetrics",
    "RunMetrics",
    # Comparison
    "COMPARISON_METRICS",
    "ComparisonDiff",
    "ComparisonGenerator",
    "ComparisonReport",
    "ConfigDiff",
    "MAX_COMPARISON_RUNS",
    "METRIC_DISPLAY_NAMES",
    "MetricComparison",
    "RunComparison",
    # Benchmark preparation
    "BenchmarkPreparer",
    "PrepareResult",
    "RunData",
]
