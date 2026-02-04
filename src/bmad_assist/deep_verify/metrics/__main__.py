"""CLI entry point for Deep Verify benchmarking.

Usage:
    python -m bmad_assist.deep_verify.metrics [OPTIONS]

Examples:
    # Run full benchmark
    python -m bmad_assist.deep_verify.metrics

    # Run only golden tests
    python -m bmad_assist.deep_verify.metrics --golden-only

    # Filter by language
    python -m bmad_assist.deep_verify.metrics --filter language=python

    # Output to file
    python -m bmad_assist.deep_verify.metrics --output report.json --format json

    # Check thresholds
    python -m bmad_assist.deep_verify.metrics --check-thresholds

    # Regenerate manifest
    python -m bmad_assist.deep_verify.metrics --regenerate-manifest

"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bmad_assist.deep_verify.core.engine import DeepVerifyEngine
from bmad_assist.deep_verify.metrics.collector import MetricsCollector
from bmad_assist.deep_verify.metrics.corpus_loader import CorpusLoader
from bmad_assist.deep_verify.metrics.report import ReportFormatter
from bmad_assist.deep_verify.metrics.threshold import ThresholdChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


VALID_FILTER_KEYS = {"language", "domain", "type", "source"}


def parse_filter(filter_str: str | None) -> Callable[[Any], bool] | None:
    """Parse filter string into predicate function.

    Args:
        filter_str: Filter string like "language=python" or "domain=security".

    Returns:
        Predicate function or None.

    Raises:
        ValueError: If filter key is invalid.

    """
    if not filter_str:
        return None

    parts = filter_str.split("=")
    if len(parts) != 2:
        logger.warning("Invalid filter format: %s. Use key=value.", filter_str)
        return None

    key, value = parts

    if key not in VALID_FILTER_KEYS:
        raise ValueError(
            f"Invalid filter key: {key}. Valid keys: {', '.join(sorted(VALID_FILTER_KEYS))}"
        )

    def predicate(label: Any) -> bool:
        if key == "language":
            return bool(label.language == value)
        elif key == "domain":
            return any(d.domain.value == value for d in label.expected_domains)
        elif key == "type":
            return bool(label.artifact_type == value)
        elif key == "source":
            return bool(value in label.source)
        return True

    return predicate


def progress_bar(current: int, total: int, width: int = 40) -> None:
    """Display progress bar.

    Args:
        current: Current progress.
        total: Total items.
        width: Width of progress bar.

    """
    if total == 0:
        return

    progress = current / total
    filled = int(width * progress)
    bar = "█" * filled + "░" * (width - filled)
    percent = progress * 100

    print(f"\r  Progress: [{bar}] {percent:.1f}% ({current}/{total})", end="", flush=True)

    if current >= total:
        print()  # New line when complete


async def run_benchmark(args: argparse.Namespace) -> int:
    """Run benchmark with given arguments.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 = success, 1 = failure).

    """
    corpus_path = Path(args.corpus) if args.corpus else None

    # Load corpus
    loader = CorpusLoader(corpus_path)

    # Regenerate manifest if requested
    if args.regenerate_manifest:
        logger.info("Regenerating corpus manifest...")
        manifest = loader.generate_manifest()
        loader.save_manifest(manifest)
        print(f"Manifest regenerated: {loader.corpus_path / 'manifest.yaml'}")
        print(f"  Artifacts: {manifest.artifact_count}")
        print(f"  Languages: {manifest.language_breakdown}")
        print(f"  Domains: {manifest.domain_breakdown}")
        return 0

    # Golden-only mode
    if args.golden_only:
        logger.info("Running golden test suite...")
        golden_cases = loader.load_all_golden_cases()

        if not golden_cases:
            logger.error("No golden cases found!")
            return 1

        print(f"Loaded {len(golden_cases)} golden cases")

        # Initialize engine
        project_root = Path(".")
        engine = DeepVerifyEngine(project_root=project_root)

        passed = 0
        failed = 0

        for case in golden_cases:
            # Load from golden directory, not labels directory
            content = loader.load_artifact_content(
                loader.load_label(loader.corpus_path / "golden" / f"{case.artifact_id}.yaml")
            )
            verdict = await engine.verify(content)

            # Check verdict match (within tolerance)
            from math import isclose

            decision_match = verdict.decision == case.expected_verdict.decision
            score_match = isclose(
                verdict.score, case.expected_verdict.score, abs_tol=case.tolerance.score
            )

            if decision_match and score_match:
                passed += 1
                print(f"  ✓ {case.artifact_id}")
            else:
                failed += 1
                print(f"  ✗ {case.artifact_id}")
                if not decision_match:
                    print(
                        f"    Decision: {verdict.decision} (expected: {case.expected_verdict.decision})"
                    )
                if not score_match:
                    print(
                        f"    Score: {verdict.score:.2f} (expected: {case.expected_verdict.score:.2f})"
                    )

        print(f"\nGolden tests: {passed} passed, {failed} failed")
        return 0 if failed == 0 else 1

    # Full benchmark mode
    logger.info("Running full benchmark...")

    # Initialize collector and engine
    collector = MetricsCollector(corpus_path)
    project_root = Path(".")
    engine = DeepVerifyEngine(project_root=project_root)

    # Parse filter
    filter_predicate = parse_filter(args.filter)

    # Progress callback
    progress_cb = progress_bar if args.progress else None

    # Run evaluation
    print("Evaluating corpus...")
    report = await collector.evaluate_corpus(
        engine=engine,
        progress_callback=progress_cb,
        max_concurrent=args.parallel,
        filter_predicate=filter_predicate,
    )

    # Check thresholds if requested
    if args.check_thresholds:
        threshold_path = Path("benchmark-thresholds.yaml")
        if threshold_path.exists():
            checker = ThresholdChecker.from_file(threshold_path)
        else:
            checker = ThresholdChecker()

        results = checker.check(report)
        print("\n" + checker.format_results(results))

        all_passed = all(r.passed for r in results)
        if not all_passed:
            return 1

    # Format and output report
    formatter = ReportFormatter(report)
    output = formatter.format(args.format)

    if args.output:
        output_path = Path(args.output)
        formatter.save(output_path, args.format)
        print(f"\nReport saved to: {output_path}")
    else:
        print("\n" + output)

    return 0


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.

    """
    parser = argparse.ArgumentParser(
        prog="python -m bmad_assist.deep_verify.metrics",
        description="Deep Verify benchmarking and metrics collection",
    )

    parser.add_argument(
        "--corpus",
        type=str,
        help="Path to corpus directory (default: tests/deep_verify/corpus)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for report (default: stdout)",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "yaml"],
        default="text",
        help="Report format (default: text)",
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="Filter artifacts (e.g., language=python, domain=security)",
    )
    parser.add_argument(
        "--golden-only",
        action="store_true",
        help="Run only golden test suite",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress bar",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--check-thresholds",
        action="store_true",
        help="Check results against thresholds",
    )
    parser.add_argument(
        "--regenerate-manifest",
        action="store_true",
        help="Regenerate corpus manifest from labels",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        return asyncio.run(run_benchmark(args))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        logger.exception("Benchmark failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
